# Declarative test specs (the API-agnostic test layer)

This framework can express an environment's tests as **YAML specs** executed by a
single generic runner — so the *tests themselves* are API-agnostic, not just the
core. Adding coverage for an API becomes "a spec + a validator", with no per-API
Python test code.

> Status: **first cut.** The `weather` environment is fully spec-driven
> (`test_specs/weather.yaml`); `countries` still uses hand-written Python tests
> (`tests/countries/`) pending engine features it needs — pagination, response
> chaining, and a custom-rule escape hatch (see *Not yet supported*).

## How it fits the existing core

The engine reuses the framework core unchanged:

- One generic test (`tests/test_spec_runner.py`) is parametrized — one case per
  check — with the environment marker attached per case
  (`pytest.param(..., marks=pytest.mark.<env>)`).
- So the `env` fixture resolves config from that marker, `--env` selection
  deselects non-matching cases, the `assert_within_threshold` gate applies, and
  each case is grouped under its environment in Allure — all as before.
- Schema validation still lives in `src/validators/`; a spec references a
  validator **by class name**, resolved via auto-discovery
  (`src/spec/registry.py`) — no name→class table to maintain.

## Spec format

`test_specs/<env>.yaml`:

```yaml
environment: weather          # or inferred from the filename stem
checks:
  - name: Forecast schema and sanity
    cases: cities.json        # optional: expand one check per row of test_data/cities.json
    case_id: name             # which case field labels the test id
    request:
      path: forecast          # appended to the env base_url by APIClient
      params:                 # ${case.*} / ${env.*} tokens are interpolated
        latitude: "${case.latitude}"
        longitude: "${case.longitude}"
        hourly: temperature_2m
        timezone: auto
    expect_status: 200        # default 200
    validator: ForecastValidator   # optional; resolved from src/validators/
    validate: single          # single (object) | each (list) | first (list[0])
    unwrap: "$.data.objects"  # optional path to what the validator sees
    asserts:
      - { path: "$.latitude",      approx: "${case.latitude}", tol: 1.0 }
      - { path: "$.hourly.time",   length_gte: "${env.min_results_count}" }
      - { path: "$.timezone",      type: str }
      - { path: "$.timezone",      non_empty: true }
```

### Paths (`src/spec/resolver.py`)
Dotted, with a leading `$.`/`$` for the root: `"$.hourly.time"`,
`"data.objects.0"`. Objects index by key, lists by integer.

### Interpolation
`${case.x}` reads the per-case JSON row; `${env.x}` reads the frozen
`Environment` (e.g. `${env.min_results_count}`). A string that is *exactly* one
token preserves type (a float stays a float).

### Assertion vocabulary (`src/spec/asserts.py`)
`equals`, `not_equals`, `gt`/`gte`/`lt`/`lte`, `length_gte`/`length_gt`,
`approx` (+ `tol`), `type` (`str`/`int`/`float`/`number`/`list`/`dict`/`bool`),
`non_empty`, `contains`. Each assertion is `{ path, <op>: <value> }`; the value
is interpolated, so `length_gte: "${env.min_results_count}"` keeps the gate
YAML-driven.

## Running

```bash
pytest --env weather         # runs the spec-driven weather suite
pytest                       # weather (specs) + countries (Python) together
```

## Not yet supported (next steps to convert `countries`)
- **Pagination** — a `paginate: { style: offset, page_size: 25, param: offset }`
  descriptor so the runner walks all pages (countries' `/all`, `region/*`).
- **Response chaining** — capture a value from one response and feed it into the
  next request (`save:` + `${vars.*}`) for cross-reference checks.
- **Custom-rule escape hatch** — a named Python predicate for rules too complex
  to express as data (e.g. "a country *with a capital* must have population > 0").
- **Non-GET methods** — the core `APIClient` is GET-only.

These are deliberately staged; the engine is structured so each is an additive
feature, not a rewrite.
