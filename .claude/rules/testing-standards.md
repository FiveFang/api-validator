# Testing Standards

Project testing conventions for the api-validator framework. These are
non-negotiable rules for any test added to this repo.

## Data & parametrization
- **Parametrize from JSON, never inline test data.** Multi-case tests (e.g. the
  weather cities) must load their cases from `test_data/*.json` via a
  `load_*()` helper. Do not hardcode lists of cases in the test module.
- Test data files live in `test_data/` and are committed to the repo.

## Coverage expectations
- **Every endpoint needs a schema-validation test.** Any new endpoint must have
  at least one test that validates the response shape through a validator in
  `src/validators/` (see `code-style.md`).
- Each endpoint test must assert the HTTP status code explicitly.
- List endpoints assert a minimum result count (sourced from
  `Environment.min_results_count` where it represents a config threshold).

## Thresholds & config
- **No hardcoded URLs or thresholds in tests.** Base URLs and the
  response-time / result-count gates come from `config/environments.yaml`,
  injected via the `env` / `api_client` fixtures.
- **Every test must call `assert_within_threshold`** after each request so the
  YAML-driven response-time gate is enforced uniformly.
- Values that are *intrinsic properties of the data under test* (e.g. "Europe
  has > 40 countries", "temperature is within -80..60°C") are allowed as named
  module-level constants with an explanatory comment — they are not environment
  config and must not be moved to YAML.

## Markers & selection
- Every test carries exactly one environment marker: `@pytest.mark.countries`
  or `@pytest.mark.weather`. The marker drives `--env` selection and resolves
  the correct `Environment` for the test.

## Isolation
- Tests are read-only against live APIs and must not depend on execution order
  or on state mutated by another test.
- A test must never mutate shared config (`Environment` is frozen) — doing so
  would break `--env both` isolation across environments.
