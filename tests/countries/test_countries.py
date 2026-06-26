"""COUNTRIES workstream: tests against the REST Countries v5 API.

Requires a Bearer token via the RESTCOUNTRIES_TOKEN env var (free tier:
500 req/mo). Without it, these tests are skipped by the ``env`` fixture so CI
stays green. The endpoint paths (``region/{x}``, ``name/{x}``, ``all``) carry
over from v3.1 per the official migration guide ("replace the version in the
URL with /v5").


Every test:
  * carries the ``@pytest.mark.countries`` marker (drives ``--env`` selection
    and resolves the countries Environment via the ``env`` fixture),
  * uses the shared ``api_client`` fixture (base_url is injected — never
    hardcoded here), and
  * calls ``assert_within_threshold`` after each request so the YAML-driven
    response-time gate is enforced.

Schema/type assertions are delegated to :class:`CountryValidator`; tests never
inline ``assert "field" in payload`` checks.
"""

from __future__ import annotations

from typing import Any

import allure
import pytest

from src.validators.country import CountryValidator

# Test-intrinsic constant: Europe is documented to contain well over 40
# countries, so a healthy ``region/europe`` response must exceed this floor.
# (This is a property of the data under test, not an environment threshold,
# so it lives here rather than in config.)
MIN_EUROPE_COUNTRIES = 40


def _as_list(payload: Any) -> list[dict[str, Any]]:
    """Normalise a REST Countries response into a list of country dicts.

    REST Countries usually returns a JSON array, but be resilient: if a single
    object comes back, wrap it so callers can index/iterate uniformly.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise AssertionError(
        f"Expected a list or object from the API, got {type(payload).__name__}"
    )


@allure.feature("Countries")
@allure.title("Europe region returns more than the minimum number of countries")
@pytest.mark.countries
def test_region_europe_has_enough_countries(api_client, assert_within_threshold) -> None:
    response = api_client.get("region/europe")
    assert response.status_code == 200, (
        f"Expected 200 from region/europe, got {response.status_code}"
    )
    assert_within_threshold(response, what="GET region/europe")

    results = _as_list(response.json())
    assert len(results) > MIN_EUROPE_COUNTRIES, (
        f"Expected more than {MIN_EUROPE_COUNTRIES} European countries, "
        f"got {len(results)}"
    )


@allure.feature("Countries")
@allure.title("Germany record matches the country schema contract")
@pytest.mark.countries
def test_germany_schema(api_client, assert_within_threshold) -> None:
    response = api_client.get("name/germany")
    assert response.status_code == 200, (
        f"Expected 200 from name/germany, got {response.status_code}"
    )
    assert_within_threshold(response, what="GET name/germany")

    results = _as_list(response.json())
    assert results, "name/germany returned no results"

    germany = results[0]
    # Delegate presence + type checking to the validator (no inline schema
    # asserts): confirms name, capital, population, currencies, languages.
    CountryValidator().validate(germany)


@allure.feature("Countries")
@allure.title("Every country in /all has a positive population")
@pytest.mark.countries
def test_all_countries_have_population(api_client, assert_within_threshold) -> None:
    response = api_client.get("all", params={"fields": "name,population"})
    assert response.status_code == 200, (
        f"Expected 200 from /all, got {response.status_code}"
    )
    assert_within_threshold(response, what="GET all?fields=name,population")

    countries = _as_list(response.json())
    assert countries, "/all returned no countries"

    for country in countries:
        # Identify the offending country by its common name for a clear message.
        try:
            label = CountryValidator.common_name(country)
        except AssertionError:
            label = repr(country)[:120]
        assert CountryValidator.is_positive_population(country), (
            f"Country {label!r} has non-positive or missing population: "
            f"{country.get('population')!r}"
        )


@allure.feature("Countries")
@allure.title("A country found by name appears within its own region")
@pytest.mark.countries
def test_name_search_country_appears_in_region(api_client, assert_within_threshold) -> None:
    # 1) Find the country by name and read its region + common name.
    name_response = api_client.get("name/germany")
    assert name_response.status_code == 200, (
        f"Expected 200 from name/germany, got {name_response.status_code}"
    )
    assert_within_threshold(name_response, what="GET name/germany")

    matches = _as_list(name_response.json())
    assert matches, "name/germany returned no results"
    country = matches[0]

    common = CountryValidator.common_name(country)
    region = country.get("region")
    assert isinstance(region, str) and region, (
        f"Expected a region string for {common!r}, got {region!r}"
    )

    # 2) The same country must appear among that region's countries.
    region_response = api_client.get(f"region/{region.lower()}")
    assert region_response.status_code == 200, (
        f"Expected 200 from region/{region.lower()}, got {region_response.status_code}"
    )
    assert_within_threshold(region_response, what=f"GET region/{region.lower()}")

    region_countries = _as_list(region_response.json())
    region_common_names = {
        CountryValidator.common_name(c)
        for c in region_countries
        if isinstance(c.get("name"), dict) and isinstance(c["name"].get("common"), str)
    }
    assert common in region_common_names, (
        f"{common!r} (region {region!r}) did not appear among the "
        f"{len(region_common_names)} countries returned for region/{region.lower()}"
    )
