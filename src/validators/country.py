"""Validator for REST Countries (v5) country objects.

REST Countries returns rich, nested country records. This validator captures
the schema contract the COUNTRIES suite relies on. NOTE: v5 changed some field
names/structure from v3.1; these required fields reflect the documented core
contract and may need a one-line calibration against a live v5 response once a
valid RESTCOUNTRIES_TOKEN is configured:

    name        -> dict   (e.g. {"common": "Germany", "official": "..."} )
    capital     -> list   (e.g. ["Berlin"])
    population   -> int
    currencies  -> dict   (keyed by currency code)
    languages   -> dict   (keyed by language code)

Per the framework rules, schema-presence and type checks live here (extending
:class:`BaseValidator`) rather than as inline ``assert "x" in payload`` checks
in the tests. The validator is intentionally *general*: it asserts presence and
types only. Endpoint-specific business rules (e.g. "every country in /all has a
positive population") are enforced by the test that needs them, with the small
helpers exposed below.
"""

from __future__ import annotations

from typing import Any, Mapping

from .base import BaseValidator, ValidationError


class CountryValidator(BaseValidator):
    """Presence + type contract for a single REST Countries country object.

    Subclasses :class:`BaseValidator`, so calling :meth:`validate` checks that
    every required field is present and non-null and that each field has the
    expected JSON-decoded Python type. :meth:`validate_many` applies the same
    contract across a list of country objects.
    """

    required_fields = ["name", "capital", "population", "currencies", "languages"]

    field_types = {
        "name": dict,
        "capital": list,
        "population": int,
        "currencies": dict,
        "languages": dict,
    }

    def validate_custom(self, payload: Mapping[str, Any]) -> None:
        """Intentionally a no-op.

        The validator stays general (schema presence + types). Endpoint-specific
        rules such as ``population > 0`` are enforced where they belong — see
        :meth:`is_positive_population` and the ``/all`` test — so this validator
        can be reused for endpoints (e.g. name searches) without imposing rules
        that only make sense for the full dataset.
        """

    @classmethod
    def common_name(cls, payload: Mapping[str, Any]) -> str:
        """Safely extract ``payload["name"]["common"]``.

        Used by the cross-reference test to match a country across endpoints.
        Raises :class:`ValidationError` (an ``AssertionError``) if the common
        name is missing or not a string, so a malformed payload fails loudly
        rather than silently producing ``None``.
        """
        name = payload.get("name") if isinstance(payload, Mapping) else None
        if isinstance(name, Mapping):
            common = name.get("common")
            if isinstance(common, str) and common:
                return common
        raise ValidationError(
            f"Could not extract name.common from payload: {payload!r:.200}"
        )

    @classmethod
    def is_positive_population(cls, payload: Mapping[str, Any]) -> bool:
        """Return True iff ``population`` is present and a positive int (>0)."""
        population = payload.get("population") if isinstance(payload, Mapping) else None
        return isinstance(population, int) and population > 0
