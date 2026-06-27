---
description: Onboard a new API as a new environment — gather details, wire config, generate validator + tests, run them green.
argument-hint: "[env-name] (optional; prompts for the rest)"
---

You are onboarding a new API into the **api-validator** framework as a new
environment, end to end. Follow the project rules in `.claude/rules/` and reuse
the existing skills — do not reinvent them.

## Step 1 — Gather the details (ask; never assume)
From `$ARGUMENTS` take the env name if given. Prompt for anything missing, one
concise question at a time:
- **Environment name** — lowercase; becomes the `--env` value and the `@pytest.mark.<name>` marker.
- **Base URL**.
- **Endpoints to test** + method (GET only today). For each, what a valid response contains — ideally a **sample JSON response** (best: types are inferred from it).
- **Auth?** If a token is needed, the **env-var name** to read it from (never paste the secret).
- **Thresholds** — `max_response_time` (seconds) and `min_results_count` (default 1). If unsure, propose sane defaults and say which are defaults.

If the API is public and reachable, offer to **probe it yourself** to learn the
shape instead of asking for sample JSON.

## Step 2 — Confirm the plan
Summarize what you'll create (config entry, validator, test module, any test_data)
and ask the user to confirm before writing files.

## Step 3 — Declare the environment
Add an entry under `environments:` in `config/environments.yaml` with `base_url`,
`max_response_time`, `min_results_count`, and `auth_token_env` **only if** auth is
needed. Do not touch the selection machinery — `--env <name>` and the marker are
derived from config automatically.

## Step 4 — Generate the validator
Use the **validator-generator** skill to create `src/validators/<name>.py`
(extends `BaseValidator`; `required_fields` / `field_types`; business rules in
`validate_custom`).

## Step 5 — Generate the tests
Use the **test-generator** skill to create `tests/<name>/test_<name>.py`: marked
`@pytest.mark.<name>`, uses the shared `api_client` / `env` /
`assert_within_threshold` fixtures, delegates schema checks to the validator,
asserts status codes, calls the gate, parametrizes data-driven cases from
`test_data/*.json`, and includes positive **and** negative cases.

## Step 6 — Run and iterate
Run `pytest --env <name> -v` (source `.env` first if the API needs a token).
Iterate until green; report the result.

## Step 7 — Log it
Append a short `CLAUDE_LOG.md` entry describing what was onboarded.
