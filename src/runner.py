"""Shared endpoint-check helper used by every environment's test suite.

Extracts the three-line sequence that every test repeats — GET, assert status,
assert latency — into one call. Callers receive the response and payload back
so they can apply their own suite-specific assertions (min-count gates,
cross-reference logic, coordinate tolerances, schema validation, etc.).

This keeps the common contract-verification steps in one place while leaving
each suite free to express its own domain rules.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.client import APIClient, TimedResponse
    from src.validators.base import BaseValidator


def run_endpoint_check(
    api_client: APIClient,
    assert_within_threshold: Any,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    validator: BaseValidator | None = None,
    expected_status: int = 200,
    what: str | None = None,
) -> tuple[TimedResponse, Any]:
    """GET *path*, assert status and latency, optionally validate the payload.

    Parameters
    ----------
    api_client:
        The environment-scoped client injected by the ``api_client`` fixture.
    assert_within_threshold:
        The shared gate fixture from ``conftest.py``.
    path:
        Relative path appended to the environment's base URL.
    params:
        Optional query-string parameters.
    validator:
        If provided, ``validator.validate(payload)`` is called after the
        status/latency checks.  Pass ``None`` to skip schema validation and
        do it yourself (e.g. when the payload needs unwrapping first).
    expected_status:
        HTTP status code the test expects (default 200).
    what:
        Human-readable label used in assertion failure messages and the
        threshold-gate annotation (e.g. ``"GET names.common/germany"``).

    Returns
    -------
    (response, payload)
        ``response`` is the :class:`~src.client.TimedResponse`; ``payload``
        is ``response.json()``.  Both are returned so callers can apply
        suite-specific assertions without making another HTTP call.
    """
    response: TimedResponse = api_client.get(path, params=params or {})
    label = what or f"GET {path}"

    assert response.status_code == expected_status, (
        f"{label}: expected HTTP {expected_status}, got {response.status_code}"
    )
    assert_within_threshold(response, what=label)

    payload = response.json()
    if validator is not None:
        validator.validate(payload)
    return response, payload
