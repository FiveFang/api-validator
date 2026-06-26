# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

`api-validator` — a multi-environment, YAML-driven API consistency test
framework. The same API-agnostic core runs against two independent environments:
`countries` (REST Countries v5, token-gated) and `weather` (Open-Meteo, no auth).
See `README.md` for full setup and usage.

## Architecture (key boundaries)

- **API-agnostic core** — `src/` + `conftest.py`. Never imports from `tests/`.
  - `src/config_loader.py` — YAML → frozen `Environment` objects.
  - `src/client.py` — `APIClient` (pooled, timed, optional Bearer auth).
  - `src/validators/` — `BaseValidator` + per-API validators.
  - `src/reporters/base.py` — `BaseReporter` contract (Allure is primary).
  - `src/spec/` — the declarative-spec engine (resolver, asserts, registry,
    loader, runner, custom_checks).
  - `conftest.py` — `--env` flag, `env` fixture, `assert_within_threshold` gate.
- **API-agnostic tests** — there are no per-API test modules. Each environment's
  tests are declarative YAML specs in `test_specs/<env>.yaml`, executed by the
  single generic runner `tests/test_spec_runner.py`, which applies the
  `@pytest.mark.<env>` marker per case. See `docs/dsl-spec.md`.
- **Config** — `config/environments.yaml` is the only source of base URLs and
  thresholds. `test_data/` holds parametrization data.

## Project rules

Authoritative rules live in `.claude/rules/` and **must** be followed:
- `testing-standards.md` — parametrize from JSON; every endpoint needs a schema
  test; thresholds from YAML; always call `assert_within_threshold`.
- `code-style.md` — validators in `src/validators/`, type hints, no inline asserts.
- `framework-rules.md` — reporters extend `BaseReporter`; tests never import other
  tests; all config in `config/`.

Skills for generating new tests/validators are in `.claude/skills/`.

## Conventions

- **Session logging:** After meaningful work, append an entry to `CLAUDE_LOG.md`
  using the existing format.

## Build / Test / Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                  # all environments (default)
pytest --env weather    # one environment
export RESTCOUNTRIES_API_KEY=...   # enables the countries suite (v5)
```
