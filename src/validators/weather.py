"""Validator for the Open-Meteo ``forecast`` endpoint response.

Framework rule: response-schema rules live here (extending
:class:`BaseValidator`), never as inline asserts in the test module. The test
delegates all shape/range checking to :class:`ForecastValidator`.

The validator confirms the top-level forecast envelope (coordinates, resolved
timezone, hourly block) and then drills into the ``hourly`` block to ensure the
parallel ``time`` / ``temperature_2m`` arrays are present, non-empty, and that
every temperature reading is physically plausible.
"""

from __future__ import annotations

from typing import Any, Mapping

from .base import BaseValidator, ValidationError

# Documented physical-plausibility bounds for near-surface (2 m) air
# temperature in degrees Celsius. The coldest reliably recorded surface air
# temperature on Earth is ~-89C (Vostok, Antarctica) and the hottest ~57C
# (Death Valley); these bounds sit just outside that envelope so a real reading
# never trips them, while a unit/parse error (e.g. Kelvin leaking through, or a
# null sentinel) does.
TEMP_MIN_C = -80.0
TEMP_MAX_C = 60.0


class ForecastValidator(BaseValidator):
    """Schema + sanity validator for an Open-Meteo forecast payload.

    Required top-level fields and their expected types are declared as class
    attributes so :class:`BaseValidator` handles presence/type checking; the
    forecast-specific cross-field rules live in :meth:`validate_custom`.
    """

    required_fields = ["latitude", "longitude", "timezone", "hourly"]
    field_types = {
        "latitude": (int, float),
        "longitude": (int, float),
        "timezone": str,
        "hourly": dict,
    }

    def validate_custom(self, payload: Mapping[str, Any]) -> None:
        """Validate the ``hourly`` block: arrays present, non-empty, in range."""
        hourly = payload["hourly"]

        times = hourly.get("time")
        temps = hourly.get("temperature_2m")

        if not isinstance(times, list):
            raise ValidationError("hourly['time'] must be a list")
        if not isinstance(temps, list):
            raise ValidationError("hourly['temperature_2m'] must be a list")

        if self.hourly_count(payload) <= 0:
            raise ValidationError("hourly block is empty (no time entries)")

        if len(times) != len(temps):
            raise ValidationError(
                f"hourly time/temperature_2m length mismatch: "
                f"{len(times)} != {len(temps)}"
            )

        for index, temp in enumerate(temps):
            if temp is None or not isinstance(temp, (int, float)):
                raise ValidationError(
                    f"temperature_2m[{index}] is not a number: {temp!r}"
                )
            if not (TEMP_MIN_C <= temp <= TEMP_MAX_C):
                raise ValidationError(
                    f"temperature_2m[{index}]={temp} outside plausible range "
                    f"[{TEMP_MIN_C}, {TEMP_MAX_C}]"
                )

    def hourly_count(self, payload: Mapping[str, Any]) -> int:
        """Return the number of hourly entries (length of the time array)."""
        hourly = payload.get("hourly")
        if not isinstance(hourly, Mapping):
            return 0
        times = hourly.get("time")
        return len(times) if isinstance(times, list) else 0
