---
description: Generate (or regenerate) tests for an environment; if it isn't declared in config yet, help add it first.
argument-hint: "[env-name] (prompts if omitted)"
---

Generate pytest tests for an environment in the **api-validator** framework,
following `.claude/rules/` and reusing the skills.

## Step 1 — Identify the environment (and check it's declared)
Read the target env from `$ARGUMENTS` (ask if omitted). Then check
`config/environments.yaml`:

- **If the environment IS already declared** → go to Step 2.
- **If it is NOT declared**, ask:
  > "`<name>` isn't in `config/environments.yaml` yet. Do you want to (a) **add a
  > new environment** now, or (b) point me at an **existing** one instead?"
  - **(a) add a new one** → run the full onboarding flow (the `/pa-add-api` steps:
    gather details → confirm → declare the environment → validator → tests), then
    **circle back to Step 2 here**.
  - **(b) existing** → ask for the correct env name and restart Step 1.

Never generate tests for an environment with no config entry — the suite would
collect **zero tests**.

## Step 2 — Ensure a validator exists
If `src/validators/<name>.py` is missing, use **validator-generator** first
(schema/type checks must live in a validator, never inline in a test).

## Step 3 — Generate the tests
Use **test-generator** for the endpoints the user names: `@pytest.mark.<name>`,
shared fixtures, validator-delegated schema, explicit status assertions, the
response-time gate, JSON-parametrized cases, and positive **plus** negative tests.

## Step 4 — Run
`pytest --env <name> -v` (source `.env` if the env needs a token); iterate to
green and report.
