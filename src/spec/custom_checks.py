"""Named custom checks — the escape hatch for rules too complex to express as data.

Most expectations are declarable as assertions in a spec. A few are genuinely
procedural (conditional per-item rules, cross-endpoint membership) — those live
here as small named Python functions and are referenced from a spec via
``custom: [name]``. Each function receives the step's ``result`` (a single
payload, or the collected list for a paginated step) and the runtime ``context``
(``case`` / ``env`` / ``vars``), and raises ``AssertionError`` on failure.

Keeping these few hooks here (not in the test modules) preserves the "tests are
data" property: a spec stays declarative and only *names* the rule it needs.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from src.validators.country import CountryValidator


def countries_population_rules(result: Any, context: dict) -> None:
    """Every country has a valid population; inhabited ones (with a capital) > 0.

    Mirrors the original ``/all`` test: population is a non-negative int for all,
    and strictly positive for any country that has a capital (v5 includes
    uninhabited territories with population 0 and no capital).
    """
    for country in result:
        label = country.get("names", {}).get("common", repr(country)[:60])
        if not CountryValidator.is_valid_population(country):
            raise AssertionError(
                f"{label!r} has an invalid population: {country.get('population')!r}"
            )
        if CountryValidator.has_capital(country) and not CountryValidator.is_positive_population(country):
            raise AssertionError(
                f"{label!r} has a capital but non-positive population: "
                f"{country.get('population')!r}"
            )


def country_appears_in_region(result: Any, context: dict) -> None:
    """The saved common name (from a prior step) appears among ``result``.

    Backs the cross-reference flow: a country found by name must also show up in
    its own region's paginated results. Reads ``${vars.common}`` captured by the
    first step.
    """
    target = context.get("vars", {}).get("common")
    if not target:
        raise AssertionError("country_appears_in_region: no 'common' captured in vars")
    names = {
        CountryValidator.common_name(c)
        for c in result
        if isinstance(c.get("names"), dict) and isinstance(c["names"].get("common"), str)
    }
    if target not in names:
        raise AssertionError(
            f"{target!r} did not appear among the {len(names)} countries returned "
            f"for its region"
        )


_CUSTOM_CHECKS: Dict[str, Callable[[Any, dict], None]] = {
    "countries_population_rules": countries_population_rules,
    "country_appears_in_region": country_appears_in_region,
}


def get_custom_check(name: str) -> Callable[[Any, dict], None]:
    """Return the registered custom-check function for ``name``."""
    fn = _CUSTOM_CHECKS.get(name)
    if fn is None:
        known = ", ".join(sorted(_CUSTOM_CHECKS)) or "<none>"
        raise KeyError(f"Unknown custom check '{name}'. Known: {known}")
    return fn
