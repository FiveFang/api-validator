# Plan: Prompt-driven onboarding of private / intranet APIs from OpenAPI

**Status:** Plan (not implemented). Branch: `check-extensibility`.
**Scope:** Design only — no code, skills, or config changed by this document.

## Problem

Today the framework onboards a new API in one of two ways (see README, "Adding a
new API"):

1. **Public API** — Claude probes the live endpoints to learn the response
   shape, then generates a validator + suite and runs `pytest --env <name>`
   until green.
2. **Manual** — the user pastes a sample JSON response or lists fields, and
   Claude generates from that.

Both assume Claude can either reach the API or be handed a representative
payload, and both assume Claude can **run the suite live** to verify. Neither
holds for a **private / intranet API**: Claude can't reach the host, and can't
run the live suite. But for such APIs the user almost always has an **OpenAPI /
Swagger** document — which is a *richer* shape source than a probed sample.

This plan defines a prompt-driven flow for that case.

## Decisions locked (from design discussion)

- **Primary shape source: OpenAPI / Swagger.** Richest single source — paths,
  methods, response schemas, `required`, types, `enum`/`min`/`max`/`format`,
  `securitySchemes`, `servers`, examples. Spec-driven generation is *higher
  fidelity* than probing because these are declared, not inferred.
- **Verification model: hand-off.** Claude generates and verifies **offline**;
  the live `pytest --env <name>` run is the user's responsibility (their machine
  or an intranet CI runner). No live-run loop, no new mocking dependency.
- **Input is a single prompt with the Swagger URL** (plus optional operation
  selection). Claude derives the env entry — the user does not hand-edit
  `config/environments.yaml` or paste base URLs / auth wiring.
- **The manifest is an _output_, not an input.** Claude emits a structured
  coverage record (which spec, which operations automated / already-covered /
  skipped / blocked). It doubles as the dedup index for incremental re-runs.
- **Propose checkpoint** before generating, because the run mutates shared
  config and can emit many files autonomously.
- **Shared-config writes are staged, then merged once at the end** (see below),
  so `config/environments.yaml` is never left half-written.

## The flow (end to end)

User prompt, e.g.:

> "Automate `https://intranet/api/orders/swagger.json` — just the `/orders/*`
> endpoints."

Claude drives:

1. **Fetch + parse the spec.** Resolve `$ref`s. If the Swagger URL is itself
   behind the intranet wall and unreachable, Claude says so and asks for the
   exported spec file — the pipeline is identical after that. (URL if I can
   reach it, file if I can't.)
2. **Derive the env entry.**
   - `base_url` ← `servers[]` (prompt the user only if multiple servers and the
     choice is ambiguous).
   - auth ← `securitySchemes`: `http`/`bearer` maps to `auth_token_env`;
     `apiKey`/`oauth2`/`mutualTLS` are flagged (see core-change fences).
   - thresholds (`max_response_time`, `min_results_count`) are **not in any
     spec** — they are operational SLOs. Default them and flag the defaults for
     tuning rather than blocking on a question.
3. **Select + diff operations.** Resolve the requested subset (by `tag`, path
   glob, or `operationId`; default = all `200`-returning GETs). Subtract what
   the existing coverage manifest / suite already covers → generate only the
   gap. Flag operations whose schema drifted since the last run.
4. **Generate** validator(s) in `src/validators/<env>.py`, `test_data/<env>.json`
   from spec `examples`, and the marked suite in `tests/<env>/test_<env>.py`.
5. **Verify offline** (replaces the live "run until green" loop):
   - `pytest --collect-only --env <env>` — imports + collection succeed (no
     network).
   - Run each generated validator **directly against the spec's example
     payload** — a pure-Python check that the schema/logic is internally
     consistent.
6. **Hand off.** Report what was generated, that offline checks passed, the
   defaulted thresholds, and the single command for the user to run on their
   network: `pytest --env <env>`.

## OpenAPI → framework mapping

| OpenAPI element | Framework artifact |
|---|---|
| `servers[].url` | `Environment.base_url` |
| `securitySchemes` (bearer) | `auth_token_env` + Bearer header (existing client) |
| `securitySchemes` (apiKey / oauth2 / mTLS) | **blocked** — flag, needs core auth work |
| `paths.{path}` + method | which operations get tests; `GET` → `api_client.get` |
| non-`GET` method | **blocked** — client is GET-only today (core change) |
| `responses.200…schema` | validator `required_fields` + `field_types` |
| `required: [...]` | `required_fields` (declared, not inferred) |
| `enum` / `minimum` / `maximum` / `minItems` / `format` | `validate_custom` rules |
| `$ref` → `components.schemas` | nested validator or flattened nested checks |
| `parameters` (path/query) | test params, cross-reference cases |
| documented `4xx` responses | negative tests (expected status from the spec) |
| `examples` | `test_data/<env>.json` parametrization + offline fixtures |

## The coverage manifest (output)

A machine-readable record per spec, e.g. `config/coverage/<env>.yaml`, plus a
human summary in the reply. It is **both** the report and the memory that makes
step 3's "already automated" detectable instead of guessed — `operationId` is
the stable key.

```yaml
spec: https://intranet/api/orders/swagger.json
spec_version: 1.4.0           # from info.version — drift detection on re-run
env: orders
base_url: https://intranet/api/orders          # from servers
auth: { scheme: bearer, env_var: ORDERS_API_KEY }   # from securitySchemes
thresholds: { max_response_time: 2.0, min_results_count: 1 }   # DEFAULTS — tune me
offline_checks: passed
handoff_command: pytest --env orders
operations:
  - operationId: getOrders
    op: GET /orders
    status: automated          # automated | already-covered | skipped | blocked
    test: tests/orders/test_orders.py::test_get_orders
    validator: src/validators/orders.py:OrdersValidator
    coverage: [schema, status, gate, negative-404]
    live_verified: false       # only the user's live run can flip this
  - operationId: createOrder
    op: POST /orders
    status: blocked
    reason: non-GET method; client is GET-only (core change required)
```

`status` captures everything at a glance: automated, already-covered, skipped,
or **blocked** behind a core-change fence. `spec_version` enables drift
detection — re-run after a spec bump and only changed operations regenerate.
`live_verified` starts `false` for every operation and is the user's to confirm.

## Propose checkpoint

Because a single prompt now mutates **shared `config/environments.yaml`** and can
emit many files, Claude prints a plan **before** generating and proceeds on
confirmation:

> env `orders`: 7 ops to automate, 3 already covered, 2 blocked (POST),
> thresholds defaulted (2.0s / 1). Proceed?

For a small or explicitly-scoped selection Claude may proceed without the
checkpoint; the checkpoint is for bulk / shared-config-mutating runs.

## Shared-config staging & merge

`config/environments.yaml` is read by `src/config_loader.load_environments()`
and is the single runtime source of every env. To keep it safe under
multi-operation / multi-env generation:

- **Stage, don't edit in place.** Proposed env entries are written to a separate
  temporary staging file (e.g. `config/environments.staged.yaml`, or a scratch
  path) as the run proceeds — never directly into `config/environments.yaml`.
- **Merge once, at the end.** After offline verification passes and the propose
  checkpoint is confirmed, all staged entries are merged into
  `config/environments.yaml` in a single atomic write — producing one clean,
  reviewable diff.
- **Abort = no-op on shared config.** If the run fails or is rejected midway,
  `config/environments.yaml` is untouched and the staging file is discarded.
  This treats the config write as a transaction: the live config never sits in a
  half-written state, and a single session onboarding several specs/envs lands
  as one merge rather than N interleaved edits.

This preserves the existing loader contract (one `environments.yaml` with an
`environments:` block) — the staging file is transient and never read at
runtime.

## Core-change fences (flag-and-ask, do not silently cross)

These violate the framework's "config + validator + suite, core untouched" rule
(`.claude/rules/framework-rules.md`) and must surface as `blocked` in the
manifest, not be worked around:

- **Non-GET methods.** `APIClient` exposes only `.get`. POST/PUT/DELETE need a
  client extension.
- **Non-Bearer auth.** The client sends only `Authorization: Bearer`. apiKey
  headers, OAuth2 flows, or mTLS (common on intranets) need client work.
- **Multi-file / per-env config layout.** `load_environments()` reads a single
  `environments.yaml`. Splitting it (e.g. `config/environments/<env>.yaml`)
  would change the loader. The staging approach above deliberately avoids this.

## Skill / doc changes this implies (for the implementation PR)

- `validator-generator`: accept an `openapi_path`/`openapi_url` input alongside
  `sample_json`, precedence spec > example.
- `test-generator`: derive endpoints from the spec; emit the offline-verify step
  and hand-off note instead of a live-run loop.
- New `openapi-importer` skill orchestrating the whole flow: fetch → derive env
  → diff against manifest → generate gap → stage config → offline verify →
  merge on confirm → emit manifest.
- README: new "Adding a private / intranet API (Claude can't reach it)" section.

## Out of scope (future)

- Offline smoke mode with recorded-response mocks (responses/respx/VCR) — was
  considered and deferred in favor of hand-off.
- Non-OpenAPI contract formats (Pact, WSDL, Postman) — the example-pair path
  already roughly covers ad-hoc captures.
- Auto-tuning thresholds from observed latency (needs live data the user owns).
