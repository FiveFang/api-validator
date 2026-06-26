# Framework Architecture Rules

Architecture constraints for the api-validator framework. These define the
module boundaries that keep the framework API-agnostic and reusable across
environments.

## Layering
- The framework is split into an **API-agnostic core** (`src/`, `conftest.py`)
  and **environment-specific suites** (`tests/<env>/`). The core must never
  import from `tests/`.
- The same core (client, validators base, config loader, fixtures, gate) serves
  every environment. Adding a new API means adding config + a validator + a test
  suite — never editing the core's contracts.

## Configuration
- **All configuration lives in `config/` — never hardcoded.** Base URLs,
  thresholds, and auth-token env-var names belong in
  `config/environments.yaml`, loaded through `src/config_loader.py`.
- Secrets (API tokens) are resolved from environment variables named in config,
  never committed.

## Reporters
- **Every reporter must extend `BaseReporter`** (`src/reporters/base.py`) and
  implement `record()` and `summary()`. Primary reporting is Allure via
  `allure-pytest`; custom summaries plug in through `BaseReporter`.

## Validators
- All validators extend `BaseValidator` and live in `src/validators/`
  (one module per API). See `code-style.md`.

## Tests
- **Test files must not import from other test files.** Shared helpers belong in
  `src/` or in fixtures in the top-level `conftest.py`.
- Each test carries exactly one environment marker; environment selection is
  implemented centrally in `conftest.py` (`pytest_collection_modifyitems`), not
  per-suite.

## Environment fixture
- The single source of per-test environment config is the `env` fixture in the
  top-level `conftest.py`. It resolves config from the test's marker and injects
  base URL + thresholds + auth. Suites must depend on `env` / `api_client` and
  never construct their own clients or read config directly.
