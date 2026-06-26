"""Execute one declarative check against the live API, reusing the core fixtures.

A check is either a **single request** (``request:``) or a **multi-step flow**
(``steps:``) that threads captured values between requests. Each request may be
**paginated** (walking offset pages into one collected list). Every step runs the
same pipeline: request(s) → status assert → response-time gate → optional schema
validation (via a named ``src/validators/`` validator) → declarative assertions →
optional named custom checks. ``save:`` captures values into ``vars`` for later
steps to interpolate as ``${vars.*}``.

Timing/threshold enforcement still flows through the shared
``assert_within_threshold`` gate; schema checks still go through
``src/validators/``. Only the test *logic* is data.
"""

from __future__ import annotations

from typing import Any

from .asserts import apply_assertion
from .custom_checks import get_custom_check
from .loader import Check
from .registry import get_validator
from .resolver import get_path, interpolate, SpecError


def run_check(
    check: Check,
    env: Any,
    api_client: Any,
    assert_within_threshold: Any,
) -> None:
    """Run ``check`` (single request or multi-step flow) and enforce its expectations."""
    context: dict[str, Any] = {"case": check.case or {}, "env": env, "vars": {}}
    spec = check.spec

    steps = spec.get("steps")
    if steps is None:
        # A single-request check is just a one-step flow.
        steps = [spec]

    for index, step in enumerate(steps):
        label = check.label if len(steps) == 1 else f"{check.label} (step {index + 1})"
        _run_step(step, label, context, env, api_client, assert_within_threshold)


def _run_step(
    step: dict[str, Any],
    label: str,
    context: dict[str, Any],
    env: Any,
    api_client: Any,
    assert_within_threshold: Any,
) -> None:
    """Execute one step: request(s), validate, assert, custom checks, and saves."""
    result = _execute_request(step, label, context, api_client, assert_within_threshold)

    _validate(step, label, result)

    for assertion in step.get("asserts", []):
        apply_assertion(result, assertion, context)

    for name in step.get("custom", []):
        get_custom_check(name)(result, context)

    for var, path in (step.get("save") or {}).items():
        context["vars"][var] = get_path(result, path)


def _execute_request(
    step: dict[str, Any],
    label: str,
    context: dict[str, Any],
    api_client: Any,
    assert_within_threshold: Any,
) -> Any:
    """Perform the step's request(s) and return the result.

    Returns the full JSON payload for a normal request, or the concatenated list
    of objects across all pages for a paginated request. Status and the
    response-time gate are enforced on every HTTP call (including each page).
    """
    request = step.get("request") or {}
    method = str(request.get("method", "get")).lower()
    if method != "get":
        # The core APIClient is GET-only; non-GET is a known extension point.
        raise SpecError(f"{label}: only GET is supported (got '{method}')")

    path = interpolate(request.get("path", ""), context)
    base_params = interpolate(request.get("params") or {}, context)
    base_params = {k: v for k, v in base_params.items() if v is not None}
    expect_status = step.get("expect_status", 200)

    paginate = request.get("paginate")
    if not paginate:
        timed = api_client.get(path, params=base_params or None)
        _assert_call(timed, label, expect_status, assert_within_threshold)
        return timed.json()

    return _paginate(
        path, base_params, paginate, label, expect_status,
        api_client, assert_within_threshold,
    )


def _paginate(
    path: str,
    base_params: dict[str, Any],
    paginate: dict[str, Any],
    label: str,
    expect_status: int,
    api_client: Any,
    assert_within_threshold: Any,
) -> list[Any]:
    """Walk every page of an offset-paginated collection, returning all objects."""
    style = paginate.get("style", "offset")
    if style != "offset":
        raise SpecError(f"{label}: unsupported pagination style '{style}'")
    param = paginate.get("param", "offset")
    page_size = int(paginate.get("page_size", 25))
    unwrap = paginate.get("unwrap", "$")

    collected: list[Any] = []
    offset = 0
    while True:
        params = {**base_params, param: offset}
        timed = api_client.get(path, params=params)
        _assert_call(
            timed, f"{label} ({param}={offset})", expect_status, assert_within_threshold
        )
        page = get_path(timed.json(), unwrap)
        if not isinstance(page, list):
            raise SpecError(f"{label}: paginate unwrap '{unwrap}' did not yield a list")
        collected.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return collected


def _assert_call(timed: Any, what: str, expect_status: int, gate: Any) -> None:
    assert timed.status_code == expect_status, (
        f"{what}: expected status {expect_status}, got {timed.status_code}"
    )
    gate(timed, what=what)


def _validate(step: dict[str, Any], label: str, result: Any) -> None:
    """Apply the named validator (if any) to the unwrapped target.

    ``unwrap`` selects what gets validated (default: the whole result).
    ``validate`` chooses how: ``single`` (the object), ``each`` (every item of a
    list), or ``first`` (the first item of a list).
    """
    validator_name = step.get("validator")
    if not validator_name:
        return

    target = get_path(result, step["unwrap"]) if step.get("unwrap") else result
    mode = step.get("validate", "single")
    validator = get_validator(validator_name)

    if mode == "single":
        validator.validate(target)
    elif mode == "each":
        validator.validate_many(target)
    elif mode == "first":
        if not isinstance(target, list) or not target:
            raise SpecError(
                f"{label}: validate 'first' needs a non-empty list, got {target!r:.80}"
            )
        validator.validate(target[0])
    else:
        raise SpecError(f"{label}: unknown validate mode '{mode}'")
