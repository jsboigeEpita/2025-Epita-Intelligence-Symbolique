"""Garde #2340 — les kernel_functions Oracle attendent réellement le dataset manager.

Contexte mesuré (audit 2026-09-21) : quatre surfaces exposées au kernel appelaient
une méthode `async def` du `DatasetAccessManager` **sans `await`**. Le résultat
n'était pas une réponse Oracle mais une **coroutine** :

- `OracleTools.validate_query_permission` — `check_permission` (async) non attendue ;
  une coroutine étant toujours *truthy*, la fonction répondait « autorisé » même
  sur un refus ;
- `OracleTools.execute_authorized_query` — `execute_oracle_query` (async) non attendue ;
  `response.authorized` levait `AttributeError`, avalée par le `except` générique ;
- `OracleBaseAgent.process_oracle_request` — même appel non attendu ;
- `MoriartyTools.provide_game_clue` — `request_clue` (async) non attendue.

Ces tests sont *nés rouges* sur `main` avec le symptôme réel (coroutine / mauvaise
réponse / `RuntimeWarning: coroutine ... was never awaited`), pas avec un ImportError.

Privacy : aucune donnée du dataset chiffré ici. Les valeurs sont des identifiants
opaques (`item_alpha`, `agent_a`) ; le jeu Cluedo de ce module est synthétique.
"""

import inspect

import pytest
from semantic_kernel.kernel import Kernel
from unittest.mock import AsyncMock, Mock

from argumentation_analysis.agents.core.oracle.dataset_access_manager import (
    CluedoDatasetManager,
    DatasetAccessManager,
)
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import (
    MoriartyTools,
)
from argumentation_analysis.agents.core.oracle.oracle_base_agent import (
    OracleBaseAgent,
    OracleTools,
)
from argumentation_analysis.agents.core.oracle.permissions import (
    OracleResponse,
    QueryType,
)


def _authorized_response() -> OracleResponse:
    return OracleResponse(
        authorized=True,
        message="OK",
        data={"item": "item_alpha"},
        query_type=QueryType.CARD_INQUIRY,
        revealed_information=["item_alpha"],
        agent_name="agent_a",
    )


def _denied_response() -> OracleResponse:
    return OracleResponse(
        authorized=False,
        message="refus",
        query_type=QueryType.CARD_INQUIRY,
        agent_name="agent_a",
    )


@pytest.fixture
def async_dataset_manager() -> DatasetAccessManager:
    """Stub minimal dont les méthodes async le sont vraiment (AsyncMock)."""
    manager = Mock(spec=DatasetAccessManager)
    manager.execute_oracle_query = AsyncMock(return_value=_authorized_response())
    manager.check_permission = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def oracle_tools(async_dataset_manager: DatasetAccessManager) -> OracleTools:
    return OracleTools(async_dataset_manager, agent_name="agent_a")


async def _resolve(value):
    """Attend la valeur si elle est attendable.

    Le test ne présuppose pas la signature : sur `main` la fonction est `def` et
    renvoie déjà une `str` (d'erreur), après correctif elle est `async def`. Dans
    les deux cas l'assertion porte sur la **chaîne finale**, donc sur le
    comportement, jamais sur la forme du symptôme.
    """
    if inspect.isawaitable(value):
        return await value
    return value


class TestExecuteAuthorizedQueryIsAwaited:
    """#2340 — le coeur de l'issue."""

    async def test_authorized_query_returns_the_oracle_result(self, oracle_tools):
        result = await _resolve(
            oracle_tools.execute_authorized_query(
                agent_name="agent_a",
                query_type="card_inquiry",
                query_params='{"card": "item_alpha"}',
            )
        )

        assert result.startswith("Requête exécutée avec succès"), result
        assert "coroutine" not in result, result
        oracle_tools.dataset_manager.execute_oracle_query.assert_awaited_once()

    async def test_denied_query_is_reported_as_denied(
        self, oracle_tools, async_dataset_manager
    ):
        async_dataset_manager.execute_oracle_query.return_value = _denied_response()

        result = await _resolve(
            oracle_tools.execute_authorized_query(
                agent_name="agent_a",
                query_type="card_inquiry",
                query_params="{}",
            )
        )

        assert result.startswith("Requête refusée"), result

    async def test_manager_coroutine_is_awaited_not_merely_called(self, oracle_tools):
        """Forme déterministe du `RuntimeWarning: coroutine ... was never awaited`.

        Le warning CPython n'est émis qu'au ramassage de la coroutine — sur `main`
        celle-ci est retenue par le `LogRecord` du `except ... exc_info=True`, donc
        le warning tombe au *teardown*, hors de tout `catch_warnings`. Un test qui
        l'attendrait passerait à tort. `assert_awaited_once` porte exactement la
        même propriété, sans dépendre du GC : sur `main` l'appel est **effectué**
        mais jamais **attendu**.
        """
        await _resolve(
            oracle_tools.execute_authorized_query(
                agent_name="agent_a",
                query_type="card_inquiry",
                query_params="{}",
            )
        )

        oracle_tools.dataset_manager.execute_oracle_query.assert_called_once()
        oracle_tools.dataset_manager.execute_oracle_query.assert_awaited_once()


class TestPermissionCheckIsAwaited:
    """Frère du même défaut : une coroutine est *truthy*, donc tout est autorisé."""

    async def test_denied_permission_is_reported_as_denied(
        self, oracle_tools, async_dataset_manager
    ):
        async_dataset_manager.check_permission = AsyncMock(return_value=False)

        result = await _resolve(
            oracle_tools.validate_query_permission(
                agent_name="agent_a", query_type="card_inquiry"
            )
        )

        assert "NON autorisé" in result, result

    async def test_granted_permission_is_reported_as_granted(self, oracle_tools):
        result = await _resolve(
            oracle_tools.validate_query_permission(
                agent_name="agent_a", query_type="card_inquiry"
            )
        )

        assert "NON autorisé" not in result, result
        assert "autorisé" in result, result


class TestProcessOracleRequestIsAwaited:
    """Point d'entrée agent-à-agent, déclaré `async` par `interfaces.py:26`."""

    @pytest.fixture
    def oracle_agent(self, async_dataset_manager) -> OracleBaseAgent:
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

        kernel = Kernel()
        kernel.add_service(
            OpenAIChatCompletion(
                service_id="default", ai_model_id="gpt-4", api_key="test-key"
            )
        )
        return OracleBaseAgent(
            kernel=kernel,
            dataset_manager=async_dataset_manager,
            agent_name="agent_a",
        )

    async def test_returns_a_real_oracle_response(self, oracle_agent):
        response = await _resolve(
            oracle_agent.process_oracle_request(
                requesting_agent="agent_b",
                query_type=QueryType.CARD_INQUIRY,
                query_params={"card": "item_alpha"},
            )
        )

        assert isinstance(response, OracleResponse)
        assert response.authorized is True, response.message
        assert "coroutine" not in response.message, response.message
        assert oracle_agent.access_log[-1]["authorized"] is True

    async def test_revealed_information_reaches_the_agent_state(self, oracle_agent):
        await _resolve(
            oracle_agent.process_oracle_request(
                requesting_agent="agent_b",
                query_type=QueryType.CARD_INQUIRY,
                query_params={},
            )
        )

        assert "item_alpha" in oracle_agent.revealed_information


class TestProvideGameClueIsAwaited:
    """`MoriartyTools.provide_game_clue` appelle `request_clue`, lui aussi async."""

    @pytest.fixture
    def moriarty_tools(self) -> MoriartyTools:
        manager = Mock(spec=CluedoDatasetManager)
        manager.dataset = Mock()
        manager.request_clue = AsyncMock(
            return_value=OracleResponse(
                authorized=True,
                message="OK",
                data={"clue": "clue_alpha"},
                query_type=QueryType.CLUE_REQUEST,
            )
        )
        return MoriartyTools(manager)

    async def test_clue_is_delivered(self, moriarty_tools):
        result = await _resolve(moriarty_tools.provide_game_clue("agent_b"))

        assert "clue_alpha" in result, result
        moriarty_tools.dataset_manager.request_clue.assert_awaited_once()


class TestKernelSurfaceIsCoroutineBased:
    """Garde structurel : ces surfaces DOIVENT rester des coroutines.

    Contrôle de non-vacuité : les fonctions qui n'atteignent aucune méthode async
    du manager (`get_available_query_types`, `reveal_information_controlled`)
    restent synchrones — l'assertion distingue donc bien les deux populations.
    """

    @pytest.mark.parametrize(
        "name",
        [
            "validate_query_permission",
            "execute_authorized_query",
            "query_oracle_dataset",
            "execute_oracle_query",
            "check_agent_permission",
            "validate_agent_permissions",
        ],
    )
    def test_manager_touching_tools_are_async(self, name):
        assert inspect.iscoroutinefunction(getattr(OracleTools, name)), name

    @pytest.mark.parametrize(
        "name",
        ["get_available_query_types", "reveal_information_controlled"],
    )
    def test_pure_tools_stay_sync(self, name):
        assert not inspect.iscoroutinefunction(getattr(OracleTools, name)), name

    def test_process_oracle_request_matches_its_declared_interface(self):
        from argumentation_analysis.agents.core.oracle.interfaces import (
            OracleAgentInterface,
        )

        assert inspect.iscoroutinefunction(
            OracleAgentInterface.process_oracle_request
        ), "prémisse du test : l'interface déclare bien la méthode async"
        assert inspect.iscoroutinefunction(OracleBaseAgent.process_oracle_request)
