"""The assertion vocabulary for the spec engine.

Each assertion in a spec is a small dict carrying a ``path`` plus one operator
key (and, for ``approx``, a ``tol``). This is the declarative replacement for
hand-written ``assert`` lines: it covers the comparisons the existing suites
need (equality, ordering, list length against the YAML threshold, numeric
tolerance, type/non-empty checks) while keeping failures readable.
"""

from __future__ import annotations

from typing import Any

from .resolver import get_path, interpolate, SpecError

# Names usable in a ``type`` assertion, mapped to the Python type(s) checked.
_TYPES: dict[str, type | tuple[type, ...]] = {
    "str": str,
    "int": int,
    "float": float,
    "number": (int, float),
    "list": list,
    "dict": dict,
    "bool": bool,
}

# Keys on an assertion dict that are modifiers, not operators.
_MODIFIERS = {"path", "tol"}


def apply_assertion(payload: Any, assertion: dict, context: dict) -> None:
    """Evaluate one assertion against ``payload``; raise ``AssertionError`` on failure.

    The ``path`` is resolved against the response, every other key is treated as
    an operator whose expected value is first interpolated from ``context`` (so
    ``equals: "${case.expected_id}"`` and ``length_gte: "${env.min_results_count}"``
    work).
    """
    if "path" not in assertion:
        raise SpecError(f"assertion missing 'path': {assertion}")
    path = assertion["path"]
    actual = get_path(payload, path)

    ops = [k for k in assertion if k not in _MODIFIERS]
    if not ops:
        raise SpecError(f"assertion on '{path}' has no operator: {assertion}")

    for op in ops:
        expected = interpolate(assertion[op], context)
        _check(op, path, actual, expected, assertion, context)


def _check(op, path, actual, expected, assertion, context) -> None:
    if op == "equals":
        if actual != expected:
            _fail(path, f"expected == {expected!r}, got {actual!r}")
    elif op == "not_equals":
        if actual == expected:
            _fail(path, f"expected != {expected!r}, got {actual!r}")
    elif op == "gt":
        if not actual > expected:
            _fail(path, f"expected > {expected}, got {actual}")
    elif op == "gte":
        if not actual >= expected:
            _fail(path, f"expected >= {expected}, got {actual}")
    elif op == "lt":
        if not actual < expected:
            _fail(path, f"expected < {expected}, got {actual}")
    elif op == "lte":
        if not actual <= expected:
            _fail(path, f"expected <= {expected}, got {actual}")
    elif op in ("length_gte", "length_gt"):
        n = _length(path, actual)
        if op == "length_gte" and not n >= expected:
            _fail(path, f"length {n} < required {expected}")
        if op == "length_gt" and not n > expected:
            _fail(path, f"length {n} <= required {expected}")
    elif op == "approx":
        tol = interpolate(assertion.get("tol", 0), context)
        if not isinstance(actual, (int, float)):
            _fail(path, f"approx needs a number, got {actual!r}")
        if abs(actual - expected) > tol:
            _fail(path, f"{actual} not within {tol} of {expected}")
    elif op == "type":
        expected_type = _TYPES.get(expected)
        if expected_type is None:
            raise SpecError(f"unknown type '{expected}' for path '{path}'")
        if not isinstance(actual, expected_type):
            _fail(path, f"expected type {expected}, got {type(actual).__name__}")
    elif op == "non_empty":
        if expected and (actual is None or not hasattr(actual, "__len__") or len(actual) == 0):
            _fail(path, f"expected non-empty, got {actual!r}")
    elif op == "contains":
        try:
            present = expected in actual
        except TypeError:
            present = False
        if not present:
            _fail(path, f"expected to contain {expected!r}, got {actual!r}")
    else:
        raise SpecError(f"unknown assertion op '{op}' on path '{path}'")


def _length(path: str, actual: Any) -> int:
    if not hasattr(actual, "__len__"):
        raise SpecError(f"path '{path}': value has no length: {actual!r}")
    return len(actual)


def _fail(path: str, message: str) -> None:
    raise AssertionError(f"[spec assert] {path}: {message}")
