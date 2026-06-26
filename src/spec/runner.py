"""Execute one declarative check against the live API, reusing the core fixtures.

This is the engine's heart: it turns a :class:`Check` into the same sequence the
hand-written tests performed — request, status assert, response-time gate,
optional schema validation via a named validator, and a list of declarative
assertions — but driven entirely by data. Timing/threshold enforcement still
flows through the shared ``assert_within_threshold`` gate; schema checks still go
through ``src/validators/``.
"""

from __future__ import annotations

from typing import Any

from .asserts import apply_assertion
from .loader import Check
from .registry import get_validator
from .resolver import get_path, interpolate, SpecError


def run_check(
    check: Check,
    env: Any,
    api_client: Any,
    assert_within_threshold: Any,
) -> None:
    """Run ``check`` against ``api_client`` and enforce all of its expectations."""
    spec = check.spec
    context = {"case": check.case or {}, "env": env}

    request = spec.get("request") or {}
    method = str(request.get("method", "get")).lower()
    if method != "get":
        # The core APIClient is GET-only; non-GET is a known extension point.
        raise SpecError(f"{check.label}: only GET is supported (got '{method}')")

    path = interpolate(request.get("path", ""), context)
    params = interpolate(request.get("params") or {}, context)
    params = {k: v for k, v in params.items() if v is not None}

    timed = api_client.get(path, params=params or None)

    expect_status = spec.get("expect_status", 200)
    assert timed.status_code == expect_status, (
        f"{check.label}: expected status {expect_status}, got {timed.status_code}"
    )
    assert_within_threshold(timed, what=check.label)

    payload = timed.json()

    _validate(check, spec, payload)

    for assertion in spec.get("asserts", []):
        apply_assertion(payload, assertion, context)


def _validate(check: Check, spec: dict[str, Any], payload: Any) -> None:
    """Apply the named validator (if any) to the unwrapped target.

    ``unwrap`` selects what gets validated (default: the whole payload).
    ``validate`` chooses how: ``single`` (the object), ``each`` (every item of a
    list), or ``first`` (the first item of a list).
    """
    validator_name = spec.get("validator")
    if not validator_name:
        return

    target = get_path(payload, spec["unwrap"]) if spec.get("unwrap") else payload
    mode = spec.get("validate", "single")
    validator = get_validator(validator_name)

    if mode == "single":
        validator.validate(target)
    elif mode == "each":
        validator.validate_many(target)
    elif mode == "first":
        if not isinstance(target, list) or not target:
            raise SpecError(
                f"{check.label}: validate 'first' needs a non-empty list, got {target!r:.80}"
            )
        validator.validate(target[0])
    else:
        raise SpecError(f"{check.label}: unknown validate mode '{mode}'")
