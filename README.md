# api-validator

[![CI](https://github.com/FiveFang/api-validator/actions/workflows/ci.yml/badge.svg)](https://github.com/FiveFang/api-validator/actions/workflows/ci.yml)

📊 **Live Allure report:** https://fivefang.github.io/api-validator/
(published to GitHub Pages on every push to `main`, with accumulating trend history)

A multi-environment, **YAML-driven** API consistency test framework. The same
API-agnostic infrastructure (HTTP client, validators, response-time gate,
reporting) runs against two independent "environments":

| Environment | API | Auth |
| --- | --- | --- |
| `countries` | [REST Countries v5](https://restcountries.com) | Bearer token (free tier) |
| `weather` | [Open-Meteo](https://open-meteo.com) `forecast` | none |

Environment configuration — base URLs and quality-gate thresholds — lives
entirely in `config/environments.yaml`. Test code is environment-agnostic and
never hardcodes URLs or thresholds.

## Layout
```
config/environments.yaml     # base URLs + thresholds (single source of truth)
test_data/cities.json        # parametrization data for the weather suite
src/
  config_loader.py           # YAML -> immutable Environment objects
  client.py                  # APIClient (pooled, timed, optional Bearer auth)
  validators/                # BaseValidator + Country/Forecast validators
  reporters/base.py          # BaseReporter contract
conftest.py                  # --env flag, env fixture, response-time gate
tests/countries/, tests/weather/
.claude/rules/, .claude/skills/   # Claude Code project rules & skills
.github/workflows/ci.yml     # CI: run suite, enforce gate, upload Allure report
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### REST Countries v5 token (for the `countries` suite)
REST Countries retired its free, no-auth v3.1 API; v5 requires a Bearer token
(free tier: 500 requests/month, no card) on the `api.restcountries.com` host.
Create a key, then either export it or drop it in a gitignored `.env`:
```bash
export RESTCOUNTRIES_API_KEY="your_v5_key"
# or:  echo 'RESTCOUNTRIES_API_KEY=your_v5_key' > .env  && set -a; . ./.env; set +a
```
If the token is **not** set, the countries suite is **skipped** (not failed), so
the pipeline stays green. The weather suite needs no auth.

v5 differs from v3.1: responses are wrapped in `{"data": {"objects": [...]}}`,
collections paginate via an `offset` query param (25/page), and endpoints are
`names.common/{name}`, `region/{region}`, and the base path for "all". Fields
were renamed (`name`→`names`, `capital`→`capitals`, and `currencies`/`languages`
are now lists) — the validator and tests are calibrated to this shape.

## Running tests
```bash
pytest                  # all environments (default; same as --env all)
pytest --env weather    # weather only
pytest --env countries  # countries only (requires RESTCOUNTRIES_API_KEY)
```

### Allure report (per-environment sections)
```bash
pytest --alluredir=allure-results
allure serve allure-results          # requires the Allure CLI
```
Each test is grouped under its environment (`countries` / `weather`) via an
Allure *parent suite* label, so the report has a clear section per environment.

The latest report is published automatically to GitHub Pages:
**https://fivefang.github.io/api-validator/**

## Interpreting results
- **Passed** — endpoint returned the expected status, the response matched the
  validator's schema/range contract, and the request completed within the
  `max_response_time` threshold for that environment.
- **Failed** — a schema/type/range violation, an unexpected status, **or** a
  response-time breach of the YAML threshold (the quality gate). Any failure
  fails the CI pipeline.
- **Skipped** — the environment requires a token that isn't configured (e.g.
  `RESTCOUNTRIES_API_KEY`).

## How it works
- **Environment abstraction.** `config_loader.py` parses YAML into frozen
  `Environment` objects. The top-level `conftest.py` `env` fixture resolves each
  test's environment from its `@pytest.mark.<env>` marker and injects base URL +
  thresholds + auth. The `--env` flag selects suites by deselecting non-matching
  markers in `pytest_collection_modifyitems`.
- **Reuse across APIs.** Both suites share one `APIClient`, one `BaseValidator`
  hierarchy, and one `assert_within_threshold` gate. Adding an API = config entry
  + a validator + a test suite; the core is untouched.
- **Quality gate.** `assert_within_threshold` reads `max_response_time` from the
  environment, so the gate is YAML-driven, never hardcoded. The client pools and
  warms connections per environment so the gate measures steady-state API
  latency, not one-off DNS/TLS setup.

## CI
`.github/workflows/ci.yml` triggers on push to any branch (and PRs): sets up
Python, installs dependencies, runs the full suite, **fails on any test failure
or quality-gate breach**, prints a test summary to the job output, and uploads
the Allure report (and JUnit XML) as artifacts. Set a `RESTCOUNTRIES_API_KEY`
repository secret to enable the countries suite in CI.

## Design decisions & assumptions
- **"Zero hardcoded values"** is interpreted as *environment/config* values
  (base URLs, response-time and result-count thresholds) living only in YAML.
  Values intrinsic to a specific assertion (Europe has > 40 countries;
  temperature is physically within −80..60 °C; hourly entries > 0) are kept as
  named, commented constants in the test/validator — they are properties of the
  data under test, not deployment config.
- **REST Countries v5 + token.** The assignment named v3.1 as "free, no auth",
  but that API is now deprecated and returns a stub. v5 (token-gated, on
  `api.restcountries.com`) is used instead; the framework is token-driven and
  skips gracefully without a key. The validator and tests are calibrated to the
  v5 response shape (wrapped `data.objects`, `offset` pagination, renamed
  fields). Note v5 includes uninhabited territories (e.g. Bouvet Island) with
  population 0, so the "/all" test asserts a positive population only for
  countries that have a capital.
- **Open-Meteo** returns grid-snapped coordinates and resolves `timezone=auto`
  to a real IANA name; tests allow a 1° coordinate tolerance accordingly.
- **Test status philosophy.** The `--env` flag *deselects* the non-matching
  environment's tests during collection (via `pytest_deselected` in
  `conftest.py`), so a targeted run reports e.g. `10 passed, 4 deselected` —
  deselected tests are excluded from the run rather than executed-and-skipped.
  `Skipped` is reserved for a distinct case: an environment that requires an
  auth token (e.g. `countries` without `RESTCOUNTRIES_API_KEY`) is skipped at
  runtime so CI stays green. Both are intentional and non-failing; the default
  `pytest` run (no `--env`) executes every environment.
