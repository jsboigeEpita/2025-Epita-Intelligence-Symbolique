"""Garde #2345 — `query_oracle_dataset` et `execute_oracle_query` rendent la même réponse.

Les deux fonctions kernel portaient chacune une copie du même corps (parse JSON,
validation du type, appel au manager, mise en forme). Les copies avaient divergé :
sur une requête autorisée qui révèle quelque chose, `execute_oracle_query` taisait
`revealed_information`. Un LLM qui passait par ce nom ne voyait donc jamais ce que
l'Oracle venait de révéler, alors que la docstring et le README du module les
déclaraient « fonctionnellement identiques ».

Les deux noms restent exposés au kernel (arbitrage #2137 : un `@kernel_function`
est appelé par le LLM à l'exécution, un grep vide ne prouve pas l'absence
d'appelant). Ce qui est gardé ici, c'est qu'ils ne peuvent plus répondre
différemment : même sortie sur toute la matrice (autorisé avec révélation,
autorisé sans, refusé, JSON invalide, type invalide, erreur du manager).

Né rouge sur `main` : la ligne « autorisé avec révélation » diffère.

Privacy : identifiants opaques (`item_alpha`, `agent_a`), aucune donnée du dataset
chiffré.
"""

import pytest
from semantic_kernel.kernel import Kernel
from unittest.mock import AsyncMock, Mock

from argumentation_analysis.agents.core.oracle.dataset_access_manager import (
    DatasetAccessManager,
)
from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleTools
from argumentation_analysis.agents.core.oracle.permissions import (
    OracleResponse,
    QueryType,
)

_TWINS = ("query_oracle_dataset", "execute_oracle_query")
_VALID_PARAMS = '{"item": "item_alpha"}'


def _response(authorized: bool, revealed=None) -> OracleResponse:
    return OracleResponse(
        authorized=authorized,
        message="OK" if authorized else "refus",
        data={"item": "item_alpha"} if authorized else None,
        query_type=QueryType.CARD_INQUIRY,
        revealed_information=list(revealed or []),
        agent_name="agent_a",
    )


def _tools(side_effect=None, return_value=None) -> OracleTools:
    manager = Mock(spec=DatasetAccessManager)
    manager.execute_oracle_query = AsyncMock(
        return_value=return_value, side_effect=side_effect
    )
    return OracleTools(manager, agent_name="agent_a")


async def _both(tools: OracleTools, query_type: str, params: str):
    return [await getattr(tools, name)(query_type, params) for name in _TWINS]


_CASES = {
    "authorized_with_revelation": (
        dict(return_value=_response(True, ["item_alpha"])),
        QueryType.CARD_INQUIRY.value,
        _VALID_PARAMS,
    ),
    "authorized_without_revelation": (
        dict(return_value=_response(True)),
        QueryType.CARD_INQUIRY.value,
        _VALID_PARAMS,
    ),
    "denied": (
        dict(return_value=_response(False)),
        QueryType.CARD_INQUIRY.value,
        _VALID_PARAMS,
    ),
    "invalid_json": (
        dict(return_value=_response(True)),
        QueryType.CARD_INQUIRY.value,
        "{pas du json",
    ),
    "manager_error": (
        dict(side_effect=RuntimeError("panne_manager")),
        QueryType.CARD_INQUIRY.value,
        _VALID_PARAMS,
    ),
}


class TestTwinsAnswerAlike:
    @pytest.mark.parametrize("case", sorted(_CASES))
    async def test_same_answer(self, case):
        manager_kwargs, query_type, params = _CASES[case]
        first, second = await _both(_tools(**manager_kwargs), query_type, params)
        assert first == second

    async def test_revelation_reaches_the_llm_through_both_names(self):
        """La ligne qui était née rouge : `execute_oracle_query` taisait la révélation."""
        tools = _tools(return_value=_response(True, ["item_alpha"]))
        for answer in await _both(tools, QueryType.CARD_INQUIRY.value, _VALID_PARAMS):
            assert "item_alpha" in answer

    @pytest.mark.parametrize("name", _TWINS)
    async def test_invalid_query_type_raises_alike(self, name):
        tools = _tools(return_value=_response(True))
        with pytest.raises(ValueError, match="Type de requête invalide: pas_un_type"):
            await getattr(tools, name)("pas_un_type", _VALID_PARAMS)

    async def test_each_name_reaches_the_manager_once(self):
        """Non-vacuité : les deux noms exécutent réellement la requête."""
        tools = _tools(return_value=_response(True))
        await _both(tools, QueryType.CARD_INQUIRY.value, _VALID_PARAMS)
        assert tools.dataset_manager.execute_oracle_query.await_count == len(_TWINS)


class TestBothNamesStayExposed:
    """Arbitrage #2137 : la consolidation ne retire aucun nom du kernel."""

    def test_both_names_are_kernel_functions(self):
        kernel = Kernel()
        plugin = kernel.add_plugin(_tools(return_value=None), plugin_name="oracle")
        assert set(_TWINS) <= set(plugin.functions)
