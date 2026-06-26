"""Weather workstream: Open-Meteo ``forecast`` endpoint tests.

Test data (the city list) is loaded from ``test_data/cities.json`` and the
suite is parametrized over it — no test data is inlined here. All response
schema/range checking is delegated to :class:`ForecastValidator`; base URL and
the response-time threshold come from the ``env``/``api_client`` fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import allure
import pytest

from src.validators.weather import ForecastValidator

# Repo root = tests/weather/test_weather.py -> parents[2].
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CITIES_PATH = _REPO_ROOT / "test_data" / "cities.json"

# Open-Meteo snaps requested coordinates to its grid, so the echoed
# latitude/longitude can differ from the request by a fraction of a degree.
_COORD_TOLERANCE_DEG = 1.0


def load_cities() -> list[dict[str, Any]]:
    """Load the parametrization city list from ``test_data/cities.json``."""
    return json.loads(_CITIES_PATH.read_text())


_CITIES = load_cities()
_CITY_PARAMS = [pytest.param(city, id=city["name"]) for city in _CITIES]


@pytest.mark.weather
@allure.feature("Weather forecast")
@allure.title("Forecast schema and sanity for {city[name]}")
@pytest.mark.parametrize("city", _CITY_PARAMS)
def test_city_forecast(
    city: dict[str, Any],
    api_client: Any,
    assert_within_threshold: Any,
) -> None:
    """GET a city's hourly forecast and validate shape, timing, and coords."""
    timed = api_client.get(
        "forecast",
        params={
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "hourly": "temperature_2m",
            "timezone": "auto",
        },
    )

    assert timed.status_code == 200, (
        f"{city['name']}: expected 200, got {timed.status_code}"
    )
    assert_within_threshold(timed, what=f"forecast for {city['name']}")

    payload = timed.json()

    # Schema, hourly count > 0, temperature range, and timezone presence are
    # all enforced by the validator.
    ForecastValidator().validate(payload)

    # Open-Meteo snaps to its grid; require the echoed coordinates to be close
    # to what we requested (loose tolerance).
    assert abs(payload["latitude"] - city["latitude"]) <= _COORD_TOLERANCE_DEG, (
        f"{city['name']}: latitude {payload['latitude']} far from "
        f"requested {city['latitude']}"
    )
    assert abs(payload["longitude"] - city["longitude"]) <= _COORD_TOLERANCE_DEG, (
        f"{city['name']}: longitude {payload['longitude']} far from "
        f"requested {city['longitude']}"
    )


@pytest.mark.weather
@allure.feature("Weather forecast")
@allure.title("Resolved timezone is a non-empty string for {city[name]}")
@pytest.mark.parametrize("city", _CITY_PARAMS)
def test_city_timezone_present(
    city: dict[str, Any],
    api_client: Any,
    assert_within_threshold: Any,
) -> None:
    """``timezone=auto`` should resolve to a non-empty IANA timezone string."""
    timed = api_client.get(
        "forecast",
        params={
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "hourly": "temperature_2m",
            "timezone": "auto",
        },
    )

    assert timed.status_code == 200
    assert_within_threshold(timed, what=f"forecast for {city['name']}")

    payload = timed.json()
    timezone = payload.get("timezone")
    assert isinstance(timezone, str) and timezone, (
        f"{city['name']}: expected non-empty timezone string, got {timezone!r}"
    )
