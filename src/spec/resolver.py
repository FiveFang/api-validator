"""Path resolution and ``${...}`` interpolation for the spec engine.

Two small primitives let the YAML DSL stay declarative without a heavyweight
JSONPath dependency:

* :func:`get_path` reads a value out of a response by a dotted path
  (``"$.hourly.time"``, ``"data.objects.0"``) — the declarative replacement for
  hand-written response digging.
* :func:`interpolate` substitutes ``${case.x}`` / ``${env.x}`` tokens from a
  runtime context, so a spec can refer to per-case data (loaded from JSON) and
  to the environment config (e.g. ``${env.min_results_count}``).
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"\$\{([^}]+)\}")
_WHOLE = re.compile(r"^\$\{([^}]+)\}$")


class SpecError(AssertionError):
    """Raised when a spec is malformed or a path/token cannot be resolved.

    Subclasses ``AssertionError`` so a broken spec surfaces as a test failure
    rather than an opaque error, consistent with :class:`ValidationError`.
    """


def get_path(obj: Any, path: str) -> Any:
    """Resolve a dotted ``path`` against ``obj`` (objects by key, lists by index).

    A leading ``$.`` or a bare ``$`` denotes the root. Raises :class:`SpecError`
    with a precise message if any segment is missing or out of range, so a
    contract drift fails loudly.
    """
    clean = path.strip()
    if clean in ("$", ""):
        return obj
    if clean.startswith("$."):
        clean = clean[2:]

    cur = obj
    for seg in clean.split("."):
        if isinstance(cur, dict):
            if seg not in cur:
                raise SpecError(f"path '{path}': key '{seg}' not present")
            cur = cur[seg]
        elif isinstance(cur, list):
            try:
                idx = int(seg)
            except ValueError:
                raise SpecError(f"path '{path}': '{seg}' is not a list index")
            if not -len(cur) <= idx < len(cur):
                raise SpecError(
                    f"path '{path}': index {idx} out of range (len {len(cur)})"
                )
            cur = cur[idx]
        else:
            raise SpecError(
                f"path '{path}': cannot descend into "
                f"{type(cur).__name__} at segment '{seg}'"
            )
    return cur


def _lookup(context: dict, expr: str) -> Any:
    """Walk ``context`` by a dotted ``expr``; supports dict keys and attributes.

    Attribute access lets ``${env.min_results_count}`` read off the frozen
    :class:`Environment` dataclass while ``${case.latitude}`` reads a dict.
    """
    cur: Any = context
    for seg in expr.strip().split("."):
        if isinstance(cur, dict):
            if seg not in cur:
                raise SpecError(f"interpolation '${{{expr}}}': '{seg}' not found")
            cur = cur[seg]
        elif hasattr(cur, seg):
            cur = getattr(cur, seg)
        else:
            raise SpecError(f"interpolation '${{{expr}}}': cannot resolve '{seg}'")
    return cur


def interpolate(value: Any, context: dict) -> Any:
    """Substitute ``${...}`` tokens in ``value`` using ``context`` (recursively).

    A string that is *exactly* one token (``"${case.latitude}"``) returns the
    raw resolved value so types are preserved (a float stays a float); a token
    embedded in a larger string is stringified.
    """
    if isinstance(value, str):
        whole = _WHOLE.match(value)
        if whole:
            return _lookup(context, whole.group(1))
        return _TOKEN.sub(lambda m: str(_lookup(context, m.group(1))), value)
    if isinstance(value, dict):
        return {k: interpolate(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [interpolate(v, context) for v in value]
    return value
