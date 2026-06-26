"""Validators for PokeAPI (https://pokeapi.co/api/v2) responses.

Framework rule: response-schema rules live here (extending
:class:`BaseValidator`), never as inline asserts in the test module. PokeAPI is
a read-only, no-auth REST API; this module captures the two shapes the POKEMON
suite relies on:

  * the paginated *list* envelope returned by ``/pokemon?limit=N``
    (``count`` + a ``results`` array of ``{name, url}`` stubs), and
  * a single *detail* object returned by ``/pokemon/{name}``.

The detail object is large; :class:`PokemonValidator` asserts only the fields
the suite contracts on — the scalar ``id``/``name``/``height``/``weight`` and
the ``types``/``abilities``/``stats`` collections — and drills into each
collection's nested ``{name}`` references so a schema breach surfaces as a
normal test failure.
"""

from __future__ import annotations

from typing import Any, Mapping

from .base import BaseValidator, ValidationError


class PokemonListValidator(BaseValidator):
    """Presence + type contract for the ``/pokemon?limit=N`` list envelope."""

    required_fields = ["count", "results"]
    field_types = {
        "count": int,
        "results": list,
    }

    def validate_custom(self, payload: Mapping[str, Any]) -> None:
        """Each entry in ``results`` must be a ``{name, url}`` stub."""
        results = payload["results"]
        for index, entry in enumerate(results):
            if not isinstance(entry, Mapping):
                raise ValidationError(f"results[{index}] is not an object: {entry!r}")
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                raise ValidationError(
                    f"results[{index}]['name'] must be a non-empty string, "
                    f"got {name!r}"
                )
            if not isinstance(entry.get("url"), str):
                raise ValidationError(f"results[{index}] missing string 'url'")

    def names(self, payload: Mapping[str, Any]) -> list[str]:
        """Return the list of pokemon names from a validated list envelope."""
        return [entry["name"] for entry in payload["results"]]


class PokemonValidator(BaseValidator):
    """Presence + type contract for a single ``/pokemon/{name}`` detail object.

    The scalar identity/measurement fields are checked by the base class via the
    class attributes; the nested ``types``/``abilities``/``stats`` collections
    are checked in :meth:`validate_custom` because each is a list of objects
    wrapping a named reference rather than a flat scalar.
    """

    required_fields = [
        "id",
        "name",
        "height",
        "weight",
        "types",
        "abilities",
        "stats",
    ]
    field_types = {
        "id": int,
        "name": str,
        "height": int,
        "weight": int,
        "types": list,
        "abilities": list,
        "stats": list,
    }

    def validate_custom(self, payload: Mapping[str, Any]) -> None:
        """Validate the three nested collections are non-empty and well-shaped.

        PokeAPI nests each reference under a sub-key (``type``/``ability``/
        ``stat``) carrying a ``{name, url}`` object; every pokemon has at least
        one type, ability, and stat, so each list must be non-empty.
        """
        self._check_named_collection(payload["types"], field="types", key="type")
        self._check_named_collection(
            payload["abilities"], field="abilities", key="ability"
        )
        self._check_named_collection(payload["stats"], field="stats", key="stat")

    @staticmethod
    def _check_named_collection(
        items: Any, *, field: str, key: str
    ) -> None:
        """Assert ``items`` is a non-empty list of ``{<key>: {name: str}}``."""
        if not isinstance(items, list):
            raise ValidationError(f"'{field}' must be a list, got {type(items).__name__}")
        if not items:
            raise ValidationError(f"'{field}' must be non-empty")
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                raise ValidationError(f"{field}[{index}] is not an object: {item!r}")
            ref = item.get(key)
            if not isinstance(ref, Mapping):
                raise ValidationError(
                    f"{field}[{index}]['{key}'] must be an object, got {ref!r}"
                )
            name = ref.get("name")
            if not isinstance(name, str) or not name:
                raise ValidationError(
                    f"{field}[{index}]['{key}']['name'] must be a non-empty "
                    f"string, got {name!r}"
                )
