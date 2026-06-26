"""A concrete :class:`BaseReporter`: a per-environment pass/fail/skip summary.

This is the framework's working implementation of the ``BaseReporter`` contract
(framework rule: every reporter extends ``BaseReporter`` and implements
``record`` / ``summary``). It plugs in *alongside* Allure: the top-level
``conftest.py`` records each test's outcome — resolved to its environment from
the test marker — and prints :meth:`summary` at the end of the session, giving a
per-environment breakdown in the terminal and the CI job output.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict

from .base import BaseReporter

# Outcomes we track, in display order.
_OUTCOMES = ("passed", "failed", "skipped")


class EnvironmentSummaryReporter(BaseReporter):
    """Accumulate per-environment outcome counts and render a summary."""

    def __init__(self) -> None:
        # environment -> outcome -> count
        self._counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record(self, environment: str, name: str, outcome: str, **details: Any) -> None:
        """Record one test outcome (``passed`` / ``failed`` / ``skipped``)."""
        self._counts[environment][outcome] += 1

    def summary(self) -> str:
        """Render a per-environment breakdown, plus a totals line."""
        if not self._counts:
            return "No test outcomes recorded."

        lines = []
        totals: Dict[str, int] = defaultdict(int)
        for environment in sorted(self._counts):
            counts = self._counts[environment]
            parts = [f"{counts.get(o, 0)} {o}" for o in _OUTCOMES]
            for o in _OUTCOMES:
                totals[o] += counts.get(o, 0)
            lines.append(f"  {environment}: " + ", ".join(parts))

        total_parts = [f"{totals[o]} {o}" for o in _OUTCOMES]
        lines.append("  TOTAL: " + ", ".join(total_parts))
        return "\n".join(lines)
