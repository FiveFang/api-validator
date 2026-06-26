# Code Style

Python style rules specific to the api-validator framework. These go beyond
generic PEP 8 and encode this framework's conventions.

## Validators
- **All schema/type validation lives in `src/validators/`.** Never inline
  `assert "field" in payload` or ad-hoc type checks inside a test.
- Every validator **extends `BaseValidator`** (`src/validators/base.py`) and
  declares its contract via the `required_fields` and `field_types` class
  attributes. Endpoint-specific business rules go in `validate_custom` or in
  small, explicitly named helper methods (e.g. `is_positive_population`).
- Validators raise `ValidationError` (a subclass of `AssertionError`) so a
  schema breach surfaces as a normal test failure.

## Type hints
- **Type hints are required** on all functions, fixtures, and public methods.
- Modules use `from __future__ import annotations` so annotations stay cheap and
  forward-referenceable.

## Configuration access
- Read configuration only through `Environment` objects from
  `src/config_loader.py`. Do not call `os.environ` or open YAML directly from
  tests or validators.
- `Environment` is a frozen dataclass — treat it as immutable.

## HTTP
- All HTTP goes through `APIClient` (`src/client.py`). Tests never call
  `requests` directly. The client owns base-URL joining, auth headers, timeouts,
  and timing.

## Docstrings & comments
- Every module, validator class, and non-trivial fixture has a docstring
  explaining its role in the framework.
- Comments explain *why* (design intent), not *what* the line literally does.
