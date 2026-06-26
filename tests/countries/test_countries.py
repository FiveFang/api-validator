"""COUNTRIES workstream: tests against the REST Countries v5 API.

Requires a Bearer token via the RESTCOUNTRIES_API_KEY env var (free tier:
500 req/mo). Without it, these tests are skipped by the ``env`` fixture so CI
stays green.

v5 specifics handled here:
  * Responses are wrapped: ``{"data": {"objects": [ ... ]}}`` — unwrapped by
    ``_objects`` below.
  * Collections are paginated by an ``offset`` query param, 25 items/page —
    walked by ``_paginate`` (which enforces the response-time gate per page).
  * Endpoints: ``names.common/{name}``, ``region/{region}``, and the base path
    (``""``) for "all".

Schema/type assertions are delegated to :class:`CountryValidator`; tests never
inline ``assert "field" in payload`` checks.
"""

from __future__ import annotations

from typing import Any

import allure
import pytest

from src.validators.country import CountryValidator

# Test-intrinsic constant: Europe is documented to contain well over 40
# countries (v5 returns 54), so a healthy paginated ``region/europe`` walk must
# exceed this floor. This is a property of the data under test, not an
# environment threshold, so it lives here rather than in config.
MIN_EUROPE_COUNTRIES = 40

# v5 fixes the page size at 25 and pages via an ``offset`` query parameter.
_PAGE_SIZE = 25


def _paginate(
    api_client: Any,
    assert_within_threshold: Any,
    path: str,
    *,
    response_fields: str | None = None,
) -> list[dict[str, Any]]:
    """Walk every page of a v5 collection via ``offset``, returning all objects.

    Enforces the response-time gate on each page request so the YAML threshold
    is checked for the whole walk, not just the first call.
    """
    collected: list[dict[str, Any]] = []
    offset = 0
    while True:
        params: dict[str, Any] = {"offset": offset}
        if response_fields:
            params["response_fields"] = response_fields
        response = api_client.get(path, params=params)
        assert response.status_code == 200, (
            f"Expected 200 from '{path or '<base>'}' at offset {offset}, "
            f"got {response.status_code}"
        )
        assert_within_threshold(response, what=f"GET {path or '<all>'} offset={offset}")

        page = CountryValidator.unwrap_objects(response.json())
        collected.extend(page)
        if len(page) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE
    return collected


@allure.feature("Countries")
@allure.title("Europe region returns more than the minimum number of countries")
@pytest.mark.countries
def test_region_europe_has_enough_countries(api_client, assert_within_threshold) -> None:
    countries = _paginate(
        api_client, assert_within_threshold, "region/europe",
        response_fields="names.common",
    )
    assert len(countries) > MIN_EUROPE_COUNTRIES, (
        f"Expected more than {MIN_EUROPE_COUNTRIES} European countries, "
        f"got {len(countries)}"
    )


@allure.feature("Countries")
@allure.title("Germany record matches the country schema contract")
@pytest.mark.countries
def test_germany_schema(env, api_client, assert_within_threshold) -> None:
    response = api_client.get("names.common/germany")
    assert response.status_code == 200, (
        f"Expected 200 from names.common/germany, got {response.status_code}"
    )
    assert_within_threshold(response, what="GET names.common/germany")

    results = CountryValidator.unwrap_objects(response.json())
    # YAML-driven floor: a name lookup must return at least min_results_count.
    assert len(results) >= env.min_results_count, (
        f"names.common/germany returned {len(results)} results, "
        f"below min_results_count={env.min_results_count}"
    )

    germany = results[0]
    # Delegate presence + type checking to the validator (no inline schema
    # asserts): confirms names, capitals, population, currencies, languages, region.
    CountryValidator().validate(germany)


@allure.feature("Countries")
@allure.title("Every inhabited country has a positive population")
@pytest.mark.countries
def test_all_countries_have_population(env, api_client, assert_within_threshold) -> None:
    # The base path is the "all" collection. Limit fields to keep payloads small.
    countries = _paginate(
        api_client, assert_within_threshold, "",
        response_fields="names.common,population,capitals",
    )
    # YAML-driven floor for this list endpoint (sourced from config, not hardcoded).
    assert len(countries) >= env.min_results_count, (
        f"/all returned {len(countries)} countries, "
        f"below min_results_count={env.min_results_count}"
    )

    for country in countries:
        label = country.get("names", {}).get("common", repr(country)[:80])
        # Universal data-quality rule: population is a non-negative integer.
        assert CountryValidator.is_valid_population(country), (
            f"Country {label!r} has an invalid population: "
            f"{country.get('population')!r}"
        )
        # Consistency rule: any country with a capital is inhabited (>0).
        # v5 includes uninhabited territories (e.g. Bouvet Island) that have an
        # empty capital list and population 0 — those are legitimately excluded.
        if CountryValidator.has_capital(country):
            assert CountryValidator.is_positive_population(country), (
                f"Country {label!r} has a capital but non-positive population: "
                f"{country.get('population')!r}"
            )


@allure.feature("Countries")
@allure.title("A country found by name appears within its own region")
@pytest.mark.countries
def test_name_search_country_appears_in_region(api_client, assert_within_threshold) -> None:
    # 1) Find the country by name and read its region + common name.
    name_response = api_client.get("names.common/germany")
    assert name_response.status_code == 200, (
        f"Expected 200 from names.common/germany, got {name_response.status_code}"
    )
    assert_within_threshold(name_response, what="GET names.common/germany")

    matches = CountryValidator.unwrap_objects(name_response.json())
    assert matches, "names.common/germany returned no results"
    country = matches[0]

    common = CountryValidator.common_name(country)
    region = country.get("region")
    assert isinstance(region, str) and region, (
        f"Expected a region string for {common!r}, got {region!r}"
    )

    # 2) The same country must appear among that region's countries (paginated).
    region_countries = _paginate(
        api_client, assert_within_threshold, f"region/{region.lower()}",
        response_fields="names.common",
    )
    region_common_names = {
        CountryValidator.common_name(c)
        for c in region_countries
        if isinstance(c.get("names"), dict) and isinstance(c["names"].get("common"), str)
    }
    assert common in region_common_names, (
        f"{common!r} (region {region!r}) did not appear among the "
        f"{len(region_common_names)} countries returned for region/{region.lower()}"
    )
