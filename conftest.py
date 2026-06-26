"""Top-level pytest configuration: the API-agnostic environment layer.

Responsibilities:
  * Define the ``--env`` CLI flag (any configured environment, or ``all``).
  * Deselect tests whose environment marker doesn't match ``--env``.
  * Provide the ``env`` fixture that injects the right base_url + thresholds,
    resolved from a test's marker — so test code never hardcodes config.
  * Provide the shared ``api_client`` fixture and the response-time gate.
  * Tag each result with its environment for per-environment Allure sections.

Everything here is API-agnostic and environment-count-agnostic: the set of
environments is derived from ``config/environments.yaml``, so adding an API
(YAML entry + marker + suite) requires no change to this core.
"""

from __future__ import annotations

import pytest

from src.client import APIClient
from src.config_loader import Environment, load_environments

# Environment names are derived from config — never hardcoded — so the framework
# scales to any number of APIs. Each name is both a valid ``--env`` value and the
# marker a test in that environment must carry.
ENV_NAMES = tuple(load_environments().keys())

# Sentinel ``--env`` value meaning "run every environment" (also the default).
RUN_ALL = "all"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env",
        action="store",
        default=RUN_ALL,
        choices=[*ENV_NAMES, RUN_ALL],
        help=(
            "Which environment's tests to run: "
            f"{', '.join(ENV_NAMES)}, or '{RUN_ALL}' (default, runs every environment)."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    for name in ENV_NAMES:
        config.addinivalue_line(
            "markers", f"{name}: test targets the '{name}' environment"
        )


def _marker_of(item: pytest.Item) -> str | None:
    """Return the single environment marker on a test, if any."""
    for name in ENV_NAMES:
        if item.get_closest_marker(name):
            return name
    return None


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Implement the ``--env`` flag by deselecting non-matching tests."""
    selected_env = config.getoption("--env")
    if selected_env == RUN_ALL:
        return

    selected, deselected = [], []
    for item in items:
        if _marker_of(item) == selected_env:
            selected.append(item)
        else:
            deselected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


@pytest.fixture(scope="session")
def environments() -> dict[str, Environment]:
    """All configured environments, loaded once per session from YAML."""
    return load_environments()


@pytest.fixture
def env(request: pytest.FixtureRequest, environments: dict[str, Environment]) -> Environment:
    """Inject the Environment config matching the requesting test's marker.

    Resolving from the marker (not a global) is what lets a single ``pytest``
    run drive both environments with the correct base_url/thresholds each.
    """
    marker = _marker_of(request.node)
    if marker is None:
        raise pytest.UsageError(
            f"Test {request.node.nodeid} must carry one of the environment "
            f"markers: {ENV_NAMES}"
        )
    if marker not in environments:
        raise pytest.UsageError(f"No configuration for environment '{marker}'")

    environment = environments[marker]

    # Group this test under its environment in the Allure report. Done before
    # any skip so skipped tests still appear under the right environment section.
    try:
        import allure

        allure.dynamic.parent_suite(environment.name)
        allure.dynamic.label("environment", environment.name)
    except ImportError:  # allure-pytest optional at import time
        pass

    # If this environment requires a Bearer token but none was supplied, skip
    # rather than fail — keeps CI green until a key is configured. Set the env
    # var named by `auth_token_env` in config (e.g. RESTCOUNTRIES_API_KEY).
    if environment.requires_auth and not environment.auth_token:
        pytest.skip(
            f"[{environment.name}] requires an API token; set the configured "
            f"auth_token_env variable to a valid key to run this suite."
        )

    return environment


@pytest.fixture(scope="session")
def _client_cache() -> dict[str, APIClient]:
    """Session-scoped cache of one warmed client per environment.

    Pooling connections per environment (rather than a fresh session per test)
    amortises the DNS/TLS handshake, so the response-time gate reflects real API
    latency. Clients are closed at session teardown.
    """
    cache: dict[str, APIClient] = {}
    yield cache
    for client in cache.values():
        client.close()


@pytest.fixture
def api_client(env: Environment, _client_cache: dict[str, APIClient]) -> APIClient:
    """A connection-pooled client bound to the test's environment.

    Created and warmed once per environment, then reused across that
    environment's tests.
    """
    client = _client_cache.get(env.name)
    if client is None:
        client = APIClient(env)
        client.warm_up()
        _client_cache[env.name] = client
    return client


@pytest.fixture
def assert_within_threshold(env: Environment):
    """Return a helper that fails the test if a request breached the gate.

    The threshold is read from the Environment (YAML), never hardcoded.
    """

    def _assert(timed_response, *, what: str = "request") -> None:
        assert timed_response.elapsed_seconds <= env.max_response_time, (
            f"[{env.name}] {what} took {timed_response.elapsed_seconds:.3f}s, "
            f"exceeding max_response_time={env.max_response_time}s"
        )

    return _assert
