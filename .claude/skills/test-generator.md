# Skill: test-generator

Generate **declarative test specs** for an endpoint in *this* framework's
spec-driven layout. Tests here are not Python — they are YAML checks in
`test_specs/<environment>.yaml`, executed by the single generic runner
(`tests/test_spec_runner.py`). This skill emits spec checks (not a pytest file),
reusing the framework's fixtures, validators, and gate.

## Inputs
- `environment`: `countries` | `weather` (must exist in `config/environments.yaml`)
- `endpoint_path`: path relative to the environment `base_url`, e.g. `region/europe`
- `method`: HTTP method (currently `GET`; the runner/client are GET-only)
- `response_fields` **or** a sample JSON response: what the response should contain
- `cases` (optional): a `test_data/*.json` file to parametrize from
- `rules` (optional): min counts, value ranges, cross-references, pagination

## Output
One or more `checks:` entries appended to `test_specs/<environment>.yaml` that:
1. Set `request.path` (and `params`), and `expect_status` (the explicit status
   assertion — default `200`). The response-time gate is applied automatically
   by the runner; no per-check wiring needed.
2. **Delegate schema/type checks to a validator** referenced by class name
   (`validator: <Name>`); if none exists, call `validator-generator` first. Use
   `unwrap` to point the validator at a nested object/list and `validate`
   (`single`/`each`/`first`) to choose how.
3. Add **declarative assertions** (`asserts:`) from the vocabulary in
   `src/spec/asserts.py` (`equals`, `gt/gte/lt/lte`, `length_gte`, `approx`+`tol`,
   `type`, `non_empty`, `contains`) rather than inline Python.
4. Generate **positive** checks (valid request → schema, counts, gate) **and
   negative** checks (e.g. an unknown resource → `expect_status: 404`).
5. For data-driven cases, set `cases: <file>` + `case_id:` and reference
   `${case.*}` — never inline test data.
6. For **list/collection** endpoints, use `paginate:` and assert
   `length_gte: "${env.min_results_count}"` (keeps the gate YAML-driven).
7. For **cross-references**, use a multi-step `steps:` flow with `save:` and
   `${vars.*}`; put any procedural rule in a named `custom:` check
   (`src/spec/custom_checks.py`).

## Rules to honor
- `.claude/rules/testing-standards.md`, `code-style.md`, `framework-rules.md`
  (parametrize from JSON; schema checks via `src/validators/`; thresholds from
  YAML; the gate is enforced centrally by the runner).
- Spec format reference: `docs/dsl-spec.md`.

## Example invocation
> Generate a `countries` spec for `GET names.common/{country}` validating
> `names, capitals, population, currencies, languages, region` via
> `CountryValidator`, with a positive case (germany) and a negative case
> (a nonexistent name → 404).

## Skeleton produced
```yaml
# appended to test_specs/<environment>.yaml
checks:
  - name: <what this asserts>
    request:
      path: <endpoint_path>
      params: { <k>: <v> }
    expect_status: 200
    validator: <Validator>        # optional; from src/validators/
    unwrap: "$.data.objects"      # optional
    validate: first               # single | each | first
    asserts:
      - { path: "$.population", type: int }
      - { path: "$.data.objects", length_gte: "${env.min_results_count}" }

  - name: <negative — unknown resource>
    request: { path: <endpoint_path>/<bogus> }
    expect_status: 404
```
