---
description: Run the pytest suite for one environment (or all), capture an Allure report, and open it locally. Read-only — never edits code.
argument-hint: "[countries | weather | all] (prompts if omitted)"
---

Run the **api-validator** test suite. This command only runs tests — never edit
source, config, or specs.

> **Local-only command.** This is a developer convenience invoked by hand in
> Claude Code; it never runs in CI. CI builds and publishes its own Allure report
> from `.github/workflows/ci.yml` on GitHub's runners, so nothing here affects CI.
> `allure-results/` and `allure-report/` are gitignored, so the local artifacts
> below are never committed.

1. **Target.** Read the env from `$ARGUMENTS`. If empty, ask: "Which environment —
   `countries`, `weather`, or `all`?"
2. **Token sourcing.** If the target is `countries` (or `all`) and
   `RESTCOUNTRIES_API_KEY` is not already set, source the gitignored `.env` first
   (the framework does NOT auto-load it):
   `set -a && source ./.env && set +a`
   If there is no `.env` and no key, note that the countries suite will **skip**
   (not fail).
3. **Run** (write Allure results to a fresh local dir so the report reflects just
   this run):
   - Clear stale results first: `rm -rf allure-results allure-report`
   - `all` → `pytest -q --alluredir=allure-results`
   - a specific env → `pytest --env <env> -q --alluredir=allure-results`
   Add `-v` if the user asked for detail. (To *combine* several envs into one
   report, skip the `rm` and run each env into the same `allure-results` dir.)
4. **Build & open the Allure report** (local view of this run):
   - If the `allure` CLI is on PATH (`command -v allure`), build a self-contained
     report and open it:
     `allure generate allure-results -o allure-report --clean --single-file`
     then `open allure-report/index.html` (macOS).
     The `--single-file` bundle opens straight from `file://` — no server needed.
     `allure serve allure-results` is the alternative for a quick auto-opening
     live view (it deletes its temp results on exit).
   - If `allure` is **not** installed, skip this step, say so, and suggest
     `brew install allure` — do **not** fail the command over a missing viewer.
5. **Report.** Summarize passed/failed/skipped per environment (the run prints a
   per-environment summary), surface any failure's assertion message verbatim,
   and state where the report was written (`allure-report/index.html`).
