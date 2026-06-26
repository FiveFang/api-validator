"""API-agnostic HTTP client shared by every environment's test suite.

The client is deliberately thin: it prepends the environment ``base_url``,
issues the request, and records how long it took. Response-time *assertions*
live in the shared gate helper (conftest) so that the threshold stays
YAML-driven rather than baked into the client.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from .config_loader import Environment


@dataclass(frozen=True)
class TimedResponse:
    """A completed HTTP response plus the wall-clock seconds it took."""

    response: requests.Response
    elapsed_seconds: float

    @property
    def status_code(self) -> int:
        return self.response.status_code

    def json(self) -> Any:
        return self.response.json()


class APIClient:
    """Minimal GET client bound to a single :class:`Environment`.

    One client instance per environment keeps state (the requests session)
    isolated between the ``countries`` and ``weather`` suites.
    """

    def __init__(self, env: Environment, *, timeout: float | None = None) -> None:
        self._env = env
        # Give a hard timeout headroom above the gate so a hang surfaces as a
        # threshold failure rather than blocking the run indefinitely.
        self._timeout = timeout if timeout is not None else env.max_response_time * 5
        self._session = requests.Session()
        # Attach a Bearer token if the environment requires auth (e.g. REST
        # Countries v5). The token comes from config (resolved from an env var),
        # never hardcoded here.
        if env.auth_token:
            self._session.headers["Authorization"] = f"Bearer {env.auth_token}"

    @property
    def base_url(self) -> str:
        return self._env.base_url

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> TimedResponse:
        """GET ``base_url + path`` and return the response with its timing."""
        url = f"{self._env.base_url}/{path.lstrip('/')}"
        response = self._session.get(url, params=params, timeout=self._timeout)
        # requests measures elapsed for us; convert timedelta to seconds.
        return TimedResponse(response=response, elapsed_seconds=response.elapsed.total_seconds())

    def warm_up(self) -> None:
        """Establish the connection pool with one untimed request.

        The first request to a host pays a one-off DNS + TLS handshake cost
        (can be several seconds on cold networks). Warming the pooled session
        once up front means the response-time gate measures steady-state API
        latency rather than that one-time setup. Errors are ignored — the only
        goal is to open the connection.
        """
        try:
            self._session.get(self._env.base_url, timeout=self._timeout)
        except requests.RequestException:
            pass

    def close(self) -> None:
        self._session.close()
