"""Load declarative test specs and expand data-driven cases into checks.

A spec file is ``test_specs/<env>.yaml`` with a top-level ``environment`` (or the
filename stem) and a list of ``checks``. A check that names a ``cases`` file is
expanded into one :class:`Check` per row of that ``test_data/*.json`` file
(parametrization stays JSON-driven, per the testing standards); a check without
``cases`` becomes a single :class:`Check`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .resolver import SpecError

# src/spec/loader.py -> parents[2] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPECS_DIR = _REPO_ROOT / "test_specs"
_DATA_DIR = _REPO_ROOT / "test_data"


@dataclass(frozen=True)
class Check:
    """One executable check: an environment, a label, an optional case, the spec."""

    env: str
    label: str
    case: dict[str, Any] | None
    spec: dict[str, Any]

    @property
    def test_id(self) -> str:
        return self.label


def _load_cases(filename: str) -> list[dict[str, Any]]:
    """Load a parametrization data file from ``test_data/`` (a JSON list)."""
    path = _DATA_DIR / filename
    if not path.exists():
        raise SpecError(f"cases file not found: test_data/{filename}")
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise SpecError(f"cases file 'test_data/{filename}' must be a JSON list")
    return data


def load_all_checks(specs_dir: Path | None = None) -> list[Check]:
    """Load every ``test_specs/*.yaml`` and expand into a flat list of checks."""
    directory = specs_dir or _SPECS_DIR
    checks: list[Check] = []
    if not directory.exists():
        return checks

    for spec_path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(spec_path.read_text()) or {}
        env = data.get("environment") or spec_path.stem
        for raw in data.get("checks", []):
            name = raw.get("name", "check")
            if "cases" in raw:
                case_id = raw.get("case_id")
                for index, case in enumerate(_load_cases(raw["cases"])):
                    label_key = case.get(case_id) if case_id else index
                    checks.append(
                        Check(env=env, label=f"{name} [{label_key}]", case=case, spec=raw)
                    )
            else:
                checks.append(Check(env=env, label=name, case=None, spec=raw))
    return checks
