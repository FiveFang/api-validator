"""Pokemon workstream: PokeAPI (https://pokeapi.co/api/v2) endpoint tests.

Three contracts, per the framework's coverage expectations:

  * the ``/pokemon?limit=N`` list endpoint returns a populated, non-empty
    ``results`` array (list-count gate),
  * the ``/pokemon/{name}`` detail endpoint exposes the identity/measurement
    scalars plus the ``types``/``abilities``/``stats`` collections, and
  * a *cross-reference*: a name taken from the live list resolves at
    ``/pokemon/{name}`` and validates as a full detail object.

Test data (the limit + the named pokemon to fetch) is loaded from
``test_data/pokemon.json`` and the detail suite is parametrized over it — no
cases are inlined here. All schema checking is delegated to the validators in
``src/validators/pokemon.py``; base URL and the response-time threshold come
from the ``env``/``api_client`` fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import allure
import pytest

from src.validators.pokemon import PokemonListValidator, PokemonValidator

# Repo root = tests/pokemon/test_pokemon.py -> parents[2].
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_PATH = _REPO_ROOT / "test_data" / "pokemon.json"


def load_pokemon_data() -> dict[str, Any]:
    """Load the parametrization data from ``test_data/pokemon.json``."""
    return json.loads(_DATA_PATH.read_text())


_DATA = load_pokemon_data()
_LIST_LIMIT = _DATA["list_limit"]
_POKEMON_PARAMS = [
    pytest.param(case, id=case["name"]) for case in _DATA["pokemon"]
]


@pytest.mark.pokemon
@allure.feature("Pokemon list")
@allure.title("List endpoint returns a populated results array")
def test_pokemon_list(
    api_client: Any,
    assert_within_threshold: Any,
    env: Any,
) -> None:
    """GET /pokemon?limit=N → non-empty results and a positive total count."""
    timed = api_client.get("pokemon", params={"limit": _LIST_LIMIT})

    assert timed.status_code == 200, f"expected 200, got {timed.status_code}"
    assert_within_threshold(timed, what="pokemon list")

    payload = timed.json()

    # Envelope schema (count:int, results:list of {name,url}) is enforced here.
    PokemonListValidator().validate(payload)

    results = payload["results"]
    assert payload["count"] > 0, f"expected a positive total count, got {payload['count']}"
    # List-count gate sourced from YAML, never hardcoded.
    assert len(results) >= env.min_results_count, (
        f"expected at least {env.min_results_count} results, got {len(results)}"
    )
    # The request asked for a page of _LIST_LIMIT; the API must not over-deliver.
    assert len(results) <= _LIST_LIMIT, (
        f"requested limit={_LIST_LIMIT} but got {len(results)} results"
    )


@pytest.mark.pokemon
@allure.feature("Pokemon detail")
@allure.title("Detail schema for {case[name]}")
@pytest.mark.parametrize("case", _POKEMON_PARAMS)
def test_pokemon_detail(
    case: dict[str, Any],
    api_client: Any,
    assert_within_threshold: Any,
) -> None:
    """GET /pokemon/{name} → validate id, name, height, weight, types,
    abilities and stats are present and correctly typed."""
    name = case["name"]
    timed = api_client.get(f"pokemon/{name}")

    assert timed.status_code == 200, f"{name}: expected 200, got {timed.status_code}"
    assert_within_threshold(timed, what=f"pokemon detail for {name}")

    payload = timed.json()

    # Presence + type of the scalars and the types/abilities/stats collections
    # is enforced by the validator.
    PokemonValidator().validate(payload)

    # Identity sanity: the API echoes the requested name and the documented id.
    assert payload["name"] == name, (
        f"requested {name!r} but payload name is {payload['name']!r}"
    )
    assert payload["id"] == case["expected_id"], (
        f"{name}: expected id {case['expected_id']}, got {payload['id']}"
    )


@pytest.mark.pokemon
@allure.feature("Pokemon detail")
@allure.title("A name from the list resolves at /pokemon/{name}")
def test_list_name_resolves_to_detail(
    api_client: Any,
    assert_within_threshold: Any,
) -> None:
    """Cross-reference: take a name from the live list and fetch its detail.

    This ties the two endpoints together — proving the list's ``name`` values
    are valid lookup keys for the detail endpoint, not just opaque labels.
    """
    list_timed = api_client.get("pokemon", params={"limit": _LIST_LIMIT})
    assert list_timed.status_code == 200, (
        f"list: expected 200, got {list_timed.status_code}"
    )
    assert_within_threshold(list_timed, what="pokemon list")

    list_payload = list_timed.json()
    list_validator = PokemonListValidator()
    list_validator.validate(list_payload)

    names = list_validator.names(list_payload)
    assert names, "list returned no names to cross-reference"
    name = names[0]

    detail_timed = api_client.get(f"pokemon/{name}")
    assert detail_timed.status_code == 200, (
        f"{name}: expected 200 from detail, got {detail_timed.status_code}"
    )
    assert_within_threshold(detail_timed, what=f"pokemon detail for {name}")

    detail_payload = detail_timed.json()
    PokemonValidator().validate(detail_payload)
    assert detail_payload["name"] == name, (
        f"list name {name!r} resolved to detail name {detail_payload['name']!r}"
    )
