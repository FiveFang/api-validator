"""Validator registry — resolve a validator class by name for the spec engine.

A spec references the schema validator it needs by class name
(``validator: ForecastValidator``). To keep the engine API-agnostic, the
registry is built by *discovering* every :class:`BaseValidator` subclass under
``src/validators/`` rather than hardcoding a name->class table. Adding a new
API's validator therefore needs no change here.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Dict, Type

from src.validators import base as _base
from src.validators.base import BaseValidator


def _discover() -> Dict[str, Type[BaseValidator]]:
    """Import every ``src.validators`` module and collect validator classes."""
    package = importlib.import_module("src.validators")
    found: Dict[str, Type[BaseValidator]] = {}
    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"src.validators.{module_info.name}")
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseValidator) and obj is not BaseValidator:
                found[name] = obj
    return found


_REGISTRY: Dict[str, Type[BaseValidator]] = _discover()


def get_validator(name: str) -> BaseValidator:
    """Return a fresh validator instance for ``name`` (e.g. ``ForecastValidator``)."""
    cls = _REGISTRY.get(name)
    if cls is None:
        known = ", ".join(sorted(_REGISTRY)) or "<none>"
        raise KeyError(f"Unknown validator '{name}'. Known validators: {known}")
    return cls()
