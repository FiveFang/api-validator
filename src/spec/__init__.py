"""Declarative test-spec engine — the API-agnostic test layer.

Tests for an environment are expressed as YAML *specs* in ``test_specs/`` and
executed by a single generic runner (``tests/test_spec_runner.py``), so adding
or testing an API needs no per-API Python test code — only a spec + a validator.

The engine reuses the framework core unchanged: the ``env`` / ``api_client`` /
``assert_within_threshold`` fixtures, the ``--env`` selection machinery, and the
per-environment Allure grouping. Schema validation still lives in
``src/validators/`` (referenced by name from a spec); only the *test logic* moves
from hand-written Python into data.
"""
