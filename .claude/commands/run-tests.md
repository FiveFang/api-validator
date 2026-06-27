---
description: Run the pytest suite for one environment (or all), handling .env token sourcing. Read-only — never edits code.
argument-hint: "[countries | weather | all] (prompts if omitted)"
---

Run the **api-validator** test suite. This command only runs tests — never edit
source, config, or specs.

1. **Target.** Read the env from `$ARGUMENTS`. If empty, ask: "Which environment —
   `countries`, `weather`, or `all`?"
2. **Token sourcing.** If the target is `countries` (or `all`) and
   `RESTCOUNTRIES_API_KEY` is not already set, source the gitignored `.env` first
   (the framework does NOT auto-load it):
   `set -a && source ./.env && set +a`
   If there is no `.env` and no key, note that the countries suite will **skip**
   (not fail).
3. **Run.**
   - `all` → `pytest -q`
   - a specific env → `pytest --env <env> -q`
   Add `-v` if the user asked for detail.
4. **Report.** Summarize passed/failed/skipped per environment (the run prints a
   per-environment summary), and surface any failure's assertion message verbatim.
