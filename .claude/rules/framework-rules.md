# Framework Architecture Rules

Architecture constraints for the api-validator framework. These define the
module boundaries that keep the framework API-agnostic and reusable across
environments.

## Layering
- The framework is split into an **API-agnostic core** (`src/`, `conftest.py`)
  and **environment-specific suites** (`tests/<env>/`). The core must never
  import from `tests/`.
- The same core (client, validators base, config loader, fixtures, gate) serves
  every environment. Adding a new API means adding config + a validator + a test
  suite — never editing the core's contracts.

## Configuration
- **All configuration lives in `config/` — never hardcoded.** Base URLs,
  thresholds, and auth-token env-var names belong in
  `config/environments.yaml`, loaded through `src/config_loader.py`.
- Secrets (API tokens) are resolved from environment variables named in config,
  never committed.

## Reporters
- **Every reporter must extend `BaseReporter`** (`src/reporters/base.py`) and
  implement `record()` and `summary()`. Primary reporting is Allure via
  `allure-pytest`; custom summaries plug in through `BaseReporter`.
- **Allure environment sections:** The framework must dynamically group tests in
  the Allure report by their environment, producing a separate section per
  environment. This grouping is applied centrally — not per test — by the `env`
  fixture in the top-level `conftest.py`, which resolves the environment from the
  test's marker and calls `allure.dynamic.parent_suite(env.name)` (the Suites-tab
  section) plus `allure.dynamic.label("environment", env.name)`. Tests must not
  set their own `parent_suite`/`environment` labels; environment grouping is the
  fixture's responsibility.
- Tests *may* still use `@allure.feature(...)`/`@allure.title(...)` for
  human-readable, test-area labelling (e.g. "Weather forecast") — these describe
  *what* a test covers and are complementary to, not a substitute for, the
  fixture-driven environment grouping above.

## Validators
- All validators extend `BaseValidator` and live in `src/validators/`
  (one module per API). See `code-style.md`.

## Tests
- **Test files must not import from other test files.** Shared helpers belong in
  `src/` or in fixtures in the top-level `conftest.py`.
- Each test carries exactly one environment marker; environment selection is
  implemented centrally in `conftest.py` (`pytest_collection_modifyitems`), not
  per-suite.

## Environment fixture
- The single source of per-test environment config is the `env` fixture in the
  top-level `conftest.py`. It resolves config from the test's marker and injects
  base URL + thresholds + auth. Suites must depend on `env` / `api_client` and
  never construct their own clients or read config directly.
