# Declarative test specs (the API-agnostic test layer)

This framework can express an environment's tests as **YAML specs** executed by a
single generic runner — so the *tests themselves* are API-agnostic, not just the
core. Adding coverage for an API becomes "a spec + a validator", with no per-API
Python test code.

> Status: **both environments fully spec-driven.** `weather`
> (`test_specs/weather.yaml`) and `countries` (`test_specs/countries.yaml`) run
> through the single generic runner — `tests/` now contains only
> `test_spec_runner.py`, no per-API test modules. The engine supports offset
> pagination, multi-step response chaining, and a custom-rule escape hatch.

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

Filters: `${vars.region|lower}` (also `|upper`, `|strip`).

### Assertion vocabulary (`src/spec/asserts.py`)
`equals`, `not_equals`, `gt`/`gte`/`lt`/`lte`, `length_gte`/`length_gt`,
`approx` (+ `tol`), `type` (`str`/`int`/`float`/`number`/`list`/`dict`/`bool`),
`non_empty`, `contains`. Each assertion is `{ path, <op>: <value> }`; the value
is interpolated, so `length_gte: "${env.min_results_count}"` keeps the gate
YAML-driven.

### Pagination
Add a `paginate` block to a request to walk an offset-paged collection; the
result the check operates on becomes the concatenated list of all pages:

```yaml
request:
  path: region/europe
  params: { response_fields: names.common }
  paginate: { style: offset, param: offset, page_size: 25, unwrap: "$.data.objects" }
asserts:
  - { path: "$", length_gt: 40 }     # "$" is the collected list
```

### Multi-step flows + chaining
A check with `steps` runs each step in order, threading captured values. `save`
extracts from a step's result into `vars`, which later steps interpolate:

```yaml
steps:
  - request: { path: names.common/germany }
    save: { common: "$.data.objects.0.names.common", region: "$.data.objects.0.region" }
  - request:
      path: "region/${vars.region|lower}"
      paginate: { style: offset, param: offset, page_size: 25, unwrap: "$.data.objects" }
    custom: [country_appears_in_region]
```

### Custom-rule escape hatch (`src/spec/custom_checks.py`)
For rules too procedural to express as data (conditional per-item invariants,
cross-endpoint membership), a step lists `custom: [name]`; each named function
receives the step result + context and raises `AssertionError` on failure. This
keeps specs declarative while still allowing the occasional complex rule.

## Running

```bash
pytest --env weather         # runs the spec-driven weather suite
pytest                       # weather (specs) + countries (Python) together
```

## Not yet supported
- **Non-GET methods** — the core `APIClient` is GET-only (a known core
  extension point, flagged rather than worked around).
- **Cursor/page-number pagination** — only `style: offset` is implemented;
  other styles are additive.
