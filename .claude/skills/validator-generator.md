# Skill: validator-generator

Given a sample JSON response, generate a typed validator class for **this**
framework that extends `BaseValidator`.

## Inputs
- `name`: validator name, e.g. `CountryValidator`
- `module`: target file under `src/validators/`, e.g. `country.py`
- `sample_json`: a representative response object (or one element of a list
  response)
- `required_fields` (optional): override which fields are mandatory; defaults to
  every top-level key present and non-null in the sample
- `custom_rules` (optional): per-field business rules, e.g. "population > 0",
  "temperature within -80..60"

## Output
A file `src/validators/<module>` containing a class
`class <name>(BaseValidator)` that:
1. Extends `BaseValidator` (`src/validators/base.py`).
2. Declares `required_fields: list[str]` — the fields that must be present and
   non-null.
3. Declares `field_types: dict[str, type | tuple[type, ...]]` inferred from the
   sample JSON (map JSON object→`dict`, array→`list`, number→`(int, float)`,
   string→`str`, bool→`bool`).
4. Implements `validate_custom(payload)` for any `custom_rules` (range checks,
   non-empty arrays, cross-field consistency). Raise `ValidationError` with a
   clear message on failure.
5. Exposes small typed helper methods for values tests need to extract safely
   (e.g. `common_name(payload) -> str`), raising `ValidationError` on malformed
   input rather than returning `None`.
6. Has a module docstring describing the schema contract and full type hints.

## Type-inference table
| JSON value      | Python type used in `field_types` |
|-----------------|-----------------------------------|
| object `{...}`  | `dict`                            |
| array `[...]`   | `list`                            |
| number          | `(int, float)`                    |
| integer-only    | `int`                             |
| string          | `str`                             |
| boolean         | `bool`                            |

## Rules to honor
- `.claude/rules/code-style.md` (validators in `src/validators/`, type hints,
  no inline asserts) and `framework-rules.md`.

## Example
> Given a sample Open-Meteo forecast response, generate `ForecastValidator` in
> `weather.py` requiring `latitude, longitude, timezone, hourly`, with a custom
> rule that every `hourly.temperature_2m` is within -80..60°C and the arrays are
> non-empty.

## Skeleton produced
```python
"""<name>: schema contract for <API> responses."""
from __future__ import annotations

from typing import Any, Mapping

from .base import BaseValidator, ValidationError


class <name>(BaseValidator):
    required_fields = [<fields>]
    field_types = {<field>: <type>, ...}

    def validate_custom(self, payload: Mapping[str, Any]) -> None:
        ...  # range / non-empty / cross-field checks; raise ValidationError
```
