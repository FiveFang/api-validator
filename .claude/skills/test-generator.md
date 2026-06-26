# Skill: test-generator

Generate a complete pytest test file for an endpoint in **this** framework,
following its rules and reusing its fixtures.

## Inputs
- `environment`: `countries` | `weather` (must exist in `config/environments.yaml`)
- `endpoint_path`: path relative to the environment `base_url`, e.g. `region/europe`
- `method`: HTTP method (currently `GET`; the client exposes `.get`)
- `response_fields`: the fields the response is expected to contain
- `cases` (optional): name of a `test_data/*.json` file to parametrize from

## Output
A file at `tests/<environment>/test_<name>.py` that:
1. Has a module docstring and `from __future__ import annotations`.
2. Marks every test with `@pytest.mark.<environment>`.
3. Uses the shared fixtures — `api_client`, `env`, `assert_within_threshold` —
   and **never** hardcodes the base URL or thresholds.
4. Calls `api_client.<method>(endpoint_path, params=...)`, asserts the status
   code, then calls `assert_within_threshold(response, what="...")`.
5. Delegates all schema/type checks to a validator in `src/validators/` (calls
   `validator-generator` first if one does not exist). No inline schema asserts.
6. Generates **positive** tests (valid request → valid schema, counts, gate) and
   **negative** tests (e.g. unknown resource → non-2xx, or empty/garbage input
   handled gracefully).
7. If `cases` is given, loads them with a `load_*()` helper and parametrizes via
   `pytest.param(..., id=<case name>)` — never inline data.
8. Adds Allure decorators: `@allure.feature(<Environment>)`, `@allure.title(...)`.

## Rules to honor
- `.claude/rules/testing-standards.md`, `code-style.md`, `framework-rules.md`.

## Example invocation
> Generate a countries test for `GET name/{country}` returning
> `name, capital, population, currencies, languages`, with positive
> (germany) and negative (a nonexistent name → 404) cases.

## Skeleton produced
```python
"""<Environment> suite: <endpoint> tests."""
from __future__ import annotations

import allure
import pytest

from src.validators.<env_module> import <Validator>


@allure.feature("<Environment>")
@allure.title("<what this asserts>")
@pytest.mark.<environment>
def test_<name>(api_client, assert_within_threshold) -> None:
    response = api_client.get("<endpoint_path>", params={...})
    assert response.status_code == 200
    assert_within_threshold(response, what="GET <endpoint_path>")
    <Validator>().validate(response.json()[0])
```
