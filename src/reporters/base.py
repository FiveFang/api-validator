"""Reporter base class.

Framework rule: every reporter must extend :class:`BaseReporter`. The primary
reporting path is Allure (via ``allure-pytest``), but this base lets the
framework attach extra, environment-aware summaries in a uniform way.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseReporter(ABC):
    """Contract for anything that records or summarises test outcomes."""

    @abstractmethod
    def record(self, environment: str, name: str, outcome: str, **details: Any) -> None:
        """Record a single test outcome for the given environment."""

    @abstractmethod
    def summary(self) -> str:
        """Return a human-readable summary across all recorded outcomes."""
