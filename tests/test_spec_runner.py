"""Generic, API-agnostic test driver for declarative specs.

This is the DSL entry point: a *single* test function drives every
environment's checks, loaded from ``test_specs/*.yaml`` — no per-API Python test
code. The environment marker is attached per parametrized case
(``pytest.param(..., marks=pytest.mark.<env>)``), so the framework core works
unchanged: the ``env`` fixture resolves config from that marker, ``--env``
selection deselects non-matching cases, the response-time gate applies, and each
case is grouped under its environment in the Allure report.

Adding coverage for an API means adding a spec (and a validator) — never editing
this file.
"""

from __future__ import annotations

from typing import Any

import allure
import pytest

from src.spec.loader import load_all_checks
from src.spec.runner import run_check


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize the generic runner with one marked case per declarative check."""
    if "spec_check" not in metafunc.fixturenames:
        return
    params = [
        pytest.param(check, id=check.test_id, marks=getattr(pytest.mark, check.env))
        for check in load_all_checks()
    ]
    metafunc.parametrize("spec_check", params)


def test_spec(
    spec_check: Any,
    env: Any,
    api_client: Any,
    assert_within_threshold: Any,
) -> None:
    """Execute one declarative check, reusing the core env/client/gate fixtures."""
    allure.dynamic.title(spec_check.label)
    run_check(spec_check, env, api_client, assert_within_threshold)
