"""Validator for REST Countries (v5) country objects.

v5 returns each country wrapped under ``{"data": {"objects": [ ... ]}}`` (the
test layer unwraps that). Each country object is deeply nested; this validator
captures the schema contract the COUNTRIES suite relies on. Field names/shapes
differ from the retired v3.1 API — notably:

    names        -> dict   (e.g. {"common": "Germany", "official": "...", ...})
    capitals     -> list   (list of capital objects; was ``capital``: list[str])
    population   -> int
    currencies   -> list   (list of {code, name, symbol}; was a dict in v3.1)
    languages    -> list   (list of language objects; was a dict in v3.1)
    region       -> str    (e.g. "Europe")

Per the framework rules, schema-presence and type checks live here (extending
:class:`BaseValidator`) rather than as inline ``assert "x" in payload`` checks in
the tests. The validator is intentionally *general*: presence + types only.
Endpoint-specific business rules (e.g. "an inhabited country has a positive
population") are enforced by the test that needs them, using the small helpers
exposed below.
"""

from __future__ import annotations

from typing import Any, Mapping

from .base import BaseValidator, ValidationError


class CountryValidator(BaseValidator):
    """Presence + type contract for a single REST Countries v5 country object."""

    required_fields = [
        "names",
        "capitals",
        "population",
        "currencies",
        "languages",
        "region",
    ]

    field_types = {
        "names": dict,
        "capitals": list,
        "population": int,
        "currencies": list,
        "languages": list,
        "region": str,
    }

    def validate_custom(self, payload: Mapping[str, Any]) -> None:
        """Intentionally a no-op.

        The validator stays general (schema presence + types). Endpoint-specific
        rules such as "population > 0 for inhabited countries" are enforced where
        they belong — see :meth:`is_positive_population` / :meth:`has_capital` and
        the ``/all`` test — so this validator can be reused across endpoints
        without imposing rules that only make sense for part of the dataset.
        """

    @classmethod
    def common_name(cls, payload: Mapping[str, Any]) -> str:
        """Safely extract ``payload["names"]["common"]``.

        Used by the cross-reference test to match a country across endpoints.
        Raises :class:`ValidationError` if the common name is missing or not a
        string, so a malformed payload fails loudly rather than yielding ``None``.
        """
        names = payload.get("names") if isinstance(payload, Mapping) else None
        if isinstance(names, Mapping):
            common = names.get("common")
            if isinstance(common, str) and common:
                return common
        raise ValidationError(
            f"Could not extract names.common from payload: {payload!r:.200}"
        )

    @classmethod
    def has_capital(cls, payload: Mapping[str, Any]) -> bool:
        """Return True iff the country lists at least one capital.

        v5 includes uninhabited territories (e.g. Bouvet Island) with an empty
        ``capitals`` list and population 0; this distinguishes them.
        """
        capitals = payload.get("capitals") if isinstance(payload, Mapping) else None
        return isinstance(capitals, list) and len(capitals) > 0

    @classmethod
    def is_positive_population(cls, payload: Mapping[str, Any]) -> bool:
        """Return True iff ``population`` is present and a positive int (>0)."""
        population = payload.get("population") if isinstance(payload, Mapping) else None
        return isinstance(population, int) and population > 0

    @classmethod
    def is_valid_population(cls, payload: Mapping[str, Any]) -> bool:
        """Return True iff ``population`` is a non-negative int (>=0).

        Uninhabited territories legitimately report 0, so non-negativity is the
        universal data-quality rule; ``is_positive_population`` is the stricter
        rule for inhabited countries.
        """
        population = payload.get("population") if isinstance(payload, Mapping) else None
        return isinstance(population, int) and population >= 0
