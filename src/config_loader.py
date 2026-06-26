"""Loads multi-environment configuration from YAML.

All base URLs and thresholds live in ``config/environments.yaml``. Nothing in
the test suite should hardcode these values; they flow through the immutable
``Environment`` objects produced here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import yaml

# Resolve config relative to the repo root so tests work from any CWD.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG_PATH = _REPO_ROOT / "config" / "environments.yaml"


@dataclass(frozen=True)
class Environment:
    """Immutable, API-agnostic view of one environment's configuration.

    Frozen on purpose: a test must never mutate shared config and leak that
    change into another test (this would break ``--env both`` isolation).
    """

    name: str
    base_url: str
    max_response_time: float
    min_results_count: int
    # Bearer token for APIs that require auth (e.g. REST Countries v5).
    # Resolved from the env var named by `auth_token_env`. None => no auth header
    # is sent and the suite is skipped (see conftest).
    auth_token: str | None = None
    # Whether this environment declared `auth_token_env` (i.e. requires a token).
    requires_auth: bool = False


def load_environments(config_path: Path | str | None = None) -> Dict[str, Environment]:
    """Parse the YAML config into a mapping of name -> :class:`Environment`."""
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Environment config not found: {path}")

    raw = yaml.safe_load(path.read_text()) or {}
    environments = raw.get("environments")
    if not environments:
        raise ValueError(f"No 'environments' section found in {path}")

    result: Dict[str, Environment] = {}
    for name, cfg in environments.items():
        try:
            auth_token_env = cfg.get("auth_token_env")
            requires_auth = bool(auth_token_env)
            # Resolve the Bearer token from the environment at load time so a
            # token rotation just needs an env-var change, never a code change.
            auth_token = os.environ.get(auth_token_env) if auth_token_env else None

            result[name] = Environment(
                name=name,
                base_url=str(cfg["base_url"]).rstrip("/"),
                max_response_time=float(cfg["max_response_time"]),
                min_results_count=int(cfg["min_results_count"]),
                auth_token=auth_token or None,
                requires_auth=requires_auth,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid config for environment '{name}': {exc}") from exc

    return result
