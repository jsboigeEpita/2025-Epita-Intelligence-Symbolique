#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests RÉELS pour les stratégies d'argumentation - TOUTES LES STRATÉGIES AUTHENTIQUES.
Validation complète des 3 stratégies sophistiquées du système.
"""

import unittest
import asyncio
import os
import sys
import pytest
import pytest_asyncio
from pathlib import Path
from typing import List


# Fixture pour gérer la variable d'environnement sans polluer les autres tests
@pytest.fixture(scope="module", autouse=True)
def _manage_real_jpype_env():
    """Gère la variable USE_REAL_JPYPE pour ce module uniquement."""
    original_value = os.environ.get("USE_REAL_JPYPE")
    os.environ["USE_REAL_JPYPE"] = "true"
    yield
    # Restauration après tous les tests du module
    if original_value is None:
        os.environ.pop("USE_REAL_JPYPE", None)
    else:
        os.environ["USE_REAL_JPYPE"] = original_value


try:
    # IMPORTS CORRIGÉS avec les bons chemins
    from argumentation_analysis.core.strategies import (
        SimpleTerminationStrategy,
        DelegatingSelectionStrategy,
        BalancedParticipationStrategy,
    )
    from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

    print(
        "OK SUCCES : Toutes les strategies importees avec succes depuis argumentation_analysis.core.strategies"
    )
except ImportError as e:
    print(f"[ERREUR] ERREUR D'IMPORT CRITIQUE: {e}")
    print(
        "[ATTENTION]  Vérifiez que les modules sont bien dans argumentation_analysis.core"
    )


class RealAgent:
    """Agent simple RÉEL pour les tests d'intégration avec Semantic Kernel."""

    def __init__(self, name, role="agent"):
        self.name = name
        self.role = role
        self.id = name

    def __str__(self):
        return f"RealAgent({self.name}, {self.role})"


class RealChatMessage:
    """Message de chat RÉEL compatible Semantic Kernel pour les tests."""

    def __init__(self, content, role="assistant", author_name=None):
        self.content = content
        self.role = role
        self.author_name = author_name or "system"
        self.name = self.author_name  # Alias pour compatibilité
        self.timestamp = "2025-06-07T12:00:00"

    def __str__(self):
        return f"RealMessage({self.author_name}: {self.content})"


@pytest.fixture
def simple_termination_fixture():
    """Fixture pour initialiser SUT pour TestRealSimpleTerminationStrategy."""
    state = RhetoricalAnalysisState("Texte de test pour terminaison.")
    strategy = SimpleTerminationStrategy(state, max_steps=5)
    agent = RealAgent("test_agent", "analyste")
    history = []
    return {"state": state, "strategy": strategy, "agent": agent, "history": history}


class TestRealSimpleTerminationStrategy:
    """Tests RÉELS pour SimpleTerminationStrategy (style pytest)."""

    def test_initialization_real(self, simple_termination_fixture):
        """Teste l'initialisation de SimpleTerminationStrategy."""
        strategy = simple_termination_fixture["strategy"]
        state = simple_termination_fixture["state"]
        assert strategy is not None
        assert strategy._max_steps == 5
        assert isinstance(state, RhetoricalAnalysisState)
        print("[OK] Test initialisation SimpleTerminationStrategy réussi")

    def test_should_terminate_max_steps_real(self, simple_termination_fixture):
        """Teste la terminaison basée sur le nombre maximum d'étapes."""
        strategy = simple_termination_fixture["strategy"]
        agent = simple_termination_fixture["agent"]
        history = simple_termination_fixture["history"]

        async def run_test():
            for i in range(4):
                result = await strategy.should_terminate(agent, history)
                assert not result, f"Ne devrait pas terminer au tour {i+1}"

            # Le 5e appel devrait déclencher la terminaison
            result = await strategy.should_terminate(agent, history)
            assert result, "Devrait terminer après max_steps"

        asyncio.run(run_test())
        print("[OK] Test terminaison max steps réussi")

    def test_should_terminate_conclusion_real(self, simple_termination_fixture):
        """Teste la terminaison basée sur une conclusion finale."""
        strategy = simple_termination_fixture["strategy"]
        state = simple_termination_fixture["state"]
        agent = simple_termination_fixture["agent"]
        history = simple_termination_fixture["history"]

        state.final_conclusion = "Conclusion de test atteinte"

        async def run_test():
            return await strategy.should_terminate(agent, history)

        result = asyncio.run(run_test())
        assert result, "Devrait terminer avec conclusion finale"
        print("[OK] Test terminaison par conclusion réussi")


@pytest.fixture
def delegating_selection_fixture():
    """Fixture pour initialiser SUT pour TestRealDelegatingSelectionStrategy."""
    state = RhetoricalAnalysisState("Test délégation sélection")
    agents = [
        RealAgent("ProjectManagerAgent", "manager"),
        RealAgent("AnalystAgent", "analyst"),
        RealAgent("CriticAgent", "critic"),
    ]
    strategy = DelegatingSelectionStrategy(
        agents, state, default_agent_name="ProjectManagerAgent"
    )
    history = []
    return {"state": state, "strategy": strategy, "agents": agents, "history": history}


class TestRealDelegatingSelectionStrategy:
    """Tests RÉELS pour DelegatingSelectionStrategy (style pytest)."""

    def test_initialization_real(self, delegating_selection_fixture):
        """Teste l'initialisation de DelegatingSelectionStrategy."""
        strategy = delegating_selection_fixture["strategy"]
        assert strategy is not None
        assert len(strategy._agents_map) == 3
        assert strategy._default_agent_name == "ProjectManagerAgent"
        print("[OK] Test initialisation DelegatingSelectionStrategy réussi")

    def test_next_agent_default_real(self, delegating_selection_fixture):
        """Teste la sélection par défaut sans désignation."""
        strategy = delegating_selection_fixture["strategy"]
        agents = delegating_selection_fixture["agents"]

        async def run_test():
            return await strategy.next(agents, [])

        selected = asyncio.run(run_test())
        assert selected.name == "ProjectManagerAgent"
        print("[OK] Test sélection agent par défaut réussi")

    def test_next_agent_with_designation_real(self, delegating_selection_fixture):
        """Teste la sélection avec désignation explicite via l'état."""
        strategy = delegating_selection_fixture["strategy"]
        state = delegating_selection_fixture["state"]
        agents = delegating_selection_fixture["agents"]
        history = delegating_selection_fixture["history"]

        state.designate_next_agent("AnalystAgent")

        async def run_test():
            return await strategy.next(agents, history)

        selected = asyncio.run(run_test())
        assert selected.name == "AnalystAgent"
        print("[OK] Test sélection avec désignation explicite réussi")


@pytest.fixture
def balanced_participation_fixture():
    """Fixture pour initialiser SUT pour TestRealBalancedParticipationStrategy."""
    state = RhetoricalAnalysisState("Test équilibrage participation")
    agents = [
        RealAgent("ProjectManagerAgent", "manager"),
        RealAgent("AnalystAgent", "analyst"),
        RealAgent("CriticAgent", "critic"),
    ]
    target_participation = {
        "ProjectManagerAgent": 0.5,
        "AnalystAgent": 0.3,
        "CriticAgent": 0.2,
    }
    strategy = BalancedParticipationStrategy(
        agents,
        state,
        default_agent_name="ProjectManagerAgent",
        target_participation=target_participation,
    )
    history = []
    return {"state": state, "strategy": strategy, "agents": agents, "history": history}


class TestRealBalancedParticipationStrategy:
    """Tests RÉELS pour BalancedParticipationStrategy (style pytest)."""

    def test_initialization_real(self, balanced_participation_fixture):
        """Teste l'initialisation de BalancedParticipationStrategy."""
        strategy = balanced_participation_fixture["strategy"]
        assert strategy is not None
        assert len(strategy._agents_map) == 3
        assert strategy._target_participation["ProjectManagerAgent"] == 0.5
        print("[OK] Test initialisation BalancedParticipationStrategy réussi")

    def test_balanced_selection_real(self, balanced_participation_fixture):
        """Teste l'équilibrage de la participation sur plusieurs tours."""
        strategy = balanced_participation_fixture["strategy"]
        agents = balanced_participation_fixture["agents"]
        history = balanced_participation_fixture["history"]

        async def run_test():
            selections = []
            for turn in range(10):
                selected = await strategy.next(agents, history)
                selections.append(selected.name)
                message = RealChatMessage(
                    f"Message tour {turn+1}", "assistant", selected.name
                )
                history.append(message)
            return selections

        selections = asyncio.run(run_test())

        pm_count = selections.count("ProjectManagerAgent")
        analyst_count = selections.count("AnalystAgent")
        critic_count = selections.count("CriticAgent")

        print(
            f"   Participations après 10 tours: PM={pm_count}, Analyst={analyst_count}, Critic={critic_count}"
        )
        assert pm_count >= analyst_count
        assert pm_count >= critic_count
        print("[OK] Test équilibrage participation réussi")

    def test_explicit_designation_override_real(self, balanced_participation_fixture):
        """Teste que la désignation explicite prime sur l'équilibrage."""
        s = balanced_participation_fixture
        s["state"].designate_next_agent("CriticAgent")

        async def run_test():
            return await s["strategy"].next(s["agents"], s["history"])

        selected = asyncio.run(run_test())
        assert selected.name == "CriticAgent"
        print("[OK] Test priorité désignation explicite réussi")


@pytest.fixture
def strategies_integration_fixture():
    """Fixture pour initialiser SUT pour TestRealStrategiesIntegration."""
    state = RhetoricalAnalysisState("Integration test complet")
    agents = [
        RealAgent("ProjectManagerAgent", "manager"),
        RealAgent("AnalystAgent", "analyst"),
        RealAgent("CriticAgent", "critic"),
    ]
    termination_strategy = SimpleTerminationStrategy(state, max_steps=8)
    balanced_strategy = BalancedParticipationStrategy(
        agents, state, "ProjectManagerAgent"
    )
    history = []
    # Note: selection_strategy n'est pas utilisé dans le test, donc on ne le retourne pas.
    return {
        "state": state,
        "agents": agents,
        "history": history,
        "termination_strategy": termination_strategy,
        "balanced_strategy": balanced_strategy,
    }


class TestRealStrategiesIntegration:
    """Tests d'intégration complets utilisant les 3 stratégies (style pytest)."""

    def test_full_conversation_with_all_strategies_real(
        self, strategies_integration_fixture
    ):
        """Simulation complète avec les 3 stratégies en interaction."""
        fx = strategies_integration_fixture

        async def run_test():
            turn = 0
            conversation_ended = False

            while not conversation_ended and turn < 10:
                turn += 1
                selected_agent = await fx["balanced_strategy"].next(
                    fx["agents"], fx["history"]
                )
                message = RealChatMessage(
                    f"Réponse tour {turn} de {selected_agent.role}",
                    "assistant",
                    selected_agent.name,
                )
                fx["history"].append(message)
                conversation_ended = await fx["termination_strategy"].should_terminate(
                    selected_agent, fx["history"]
                )
                print(
                    f"   Tour {turn}: Agent={selected_agent.name}, Terminé={conversation_ended}"
                )
            return turn

        turn = asyncio.run(run_test())

        assert len(fx["history"]) > 0, "Au moins un message généré"
        assert turn == 8, "La conversation doit se terminer exactement au 8ème tour"

        print("[OK] INTÉGRATION COMPLÈTE : Toutes les stratégies fonctionnent ensemble")


class TestCD1534AgentGroupChatConstruction:
    """CD #1534 — AgentGroupChat must ACCEPT our strategy instances.

    Pre-CD #1534, core/strategies.py imported SelectionStrategy/TerminationStrategy
    from the LOCAL orchestration.base stub (BaseModel+ABC), not from Semantic Kernel.
    AgentGroupChat.selection_strategy is type-annotated to SK's SelectionStrategy, so
    Pydantic's model_type validator rejected our instances -> the conversational mode
    caught the ValidationError, logged a WARNING, and silently fell back to round-robin
    forever (anti-#1019 violation: a construction failure disguised as a working mode).

    These tests lock the fix: our strategies MUST be real SK subclasses so
    AgentGroupChat construction succeeds. If a future change re-points the import at
    a non-SK base, these tests fail LOUD instead of the mode silently degrading.
    """

    def test_delegating_selection_is_real_sk_selection(
        self, delegating_selection_fixture
    ):
        """DelegatingSelectionStrategy must inherit SK's real SelectionStrategy."""
        from semantic_kernel.agents.strategies.selection.selection_strategy import (
            SelectionStrategy as SKSelection,
        )

        strategy = delegating_selection_fixture["strategy"]
        assert isinstance(
            strategy, SKSelection
        ), "DelegatingSelectionStrategy must be a real SK SelectionStrategy (CD #1534)"

    def test_simple_termination_is_real_sk_termination(
        self, simple_termination_fixture
    ):
        """SimpleTerminationStrategy must inherit SK's real TerminationStrategy."""
        from semantic_kernel.agents.strategies.termination.termination_strategy import (
            TerminationStrategy as SKTermination,
        )

        assert isinstance(
            simple_termination_fixture["strategy"], SKTermination
        ), "SimpleTerminationStrategy must be a real SK TerminationStrategy (CD #1534)"

    def test_agent_group_chat_accepts_our_selection_strategy(
        self, delegating_selection_fixture
    ):
        """AgentGroupChat(selection_strategy=<our instance>) must construct.

        This is the exact gate that failed pre-CD #1534 (model_type ValidationError).
        Empty agents list: we validate only the selection_strategy field, which is
        the field that rejected our stub-subclass.
        """
        from semantic_kernel.agents.group_chat.agent_group_chat import AgentGroupChat

        strategy = delegating_selection_fixture["strategy"]
        # Must NOT raise. Pre-CD #1534 this raised:
        #   ValidationError: Input should be a valid dictionary or instance of SelectionStrategy
        chat = AgentGroupChat(agents=[], selection_strategy=strategy)
        assert chat is not None
        print("[OK] AgentGroupChat accepte DelegatingSelectionStrategy (CD #1534)")

    def test_agent_group_chat_rejects_stub_subclass(self):
        """Regression guard: a non-SK subclass is still rejected.

        Ensures the gate is real (not accidentally widened) — a stub BaseModel+ABC
        subclass must STILL be rejected by AgentGroupChat's validator.
        """
        from abc import ABC
        from pydantic import BaseModel
        from semantic_kernel.agents.group_chat.agent_group_chat import AgentGroupChat

        class StubSelection(BaseModel, ABC):
            class Config:
                arbitrary_types_allowed = True

        class FakeStubStrategy(StubSelection):
            async def next(self, agents, history):
                return agents[0] if agents else None

        with pytest.raises(Exception):
            AgentGroupChat(agents=[], selection_strategy=FakeStubStrategy())

    def test_run_phase_logs_loud_on_construction_failure(self, caplog):
        """CD #1534 DoD #3: a construction failure must surface as an ERROR log
        (loud), NOT a silent WARNING. We inject a raising AgentGroupChat at its
        source; _run_phase must emit an ERROR naming the construction failure
        (anti-#1019). It may still fall back to round-robin (preserving the
        merged C1 contract that injects a failing AgentGroupChat to force the
        round-robin path), but the ERROR must be visible — that visibility is
        the "loud" of DoD #3. A hard raise was rejected as scope-creep.
        """
        import logging
        from unittest.mock import MagicMock, patch
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )

        fake_agent = MagicMock()
        fake_agent.name = "FakeAgent"
        fake_state = MagicMock()

        async def run():
            await _run_phase(
                [fake_agent],
                "CD #1534 loud-failure probe",
                max_turns=1,
                phase_name="Extraction & Detection",
                state=fake_state,
                enable_growth_validation=False,
            )

        # Patch AgentGroupChat AT ITS SOURCE so the local
        # `from ...agent_group_chat import AgentGroupChat` in _run_phase resolves
        # to a mock whose construction raises. This is the construction-failure
        # path that must surface LOUD (ERROR), not silently fall back.
        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            side_effect=RuntimeError("construction boom (CD #1534 test)"),
        ):
            with caplog.at_level(
                logging.ERROR,
                logger="argumentation_analysis.orchestration.conversational_orchestrator",
            ):
                try:
                    asyncio.run(run())
                except Exception:
                    # The round-robin fallback may itself raise on the MagicMock
                    # agent (no real invoke/get_response) — that is orthogonal to
                    # the construction-failure ERROR we assert here. We care only
                    # that the ERROR was emitted BEFORE the fallback ran.
                    pass

        error_msgs = [r.message for r in caplog.records if r.levelno >= logging.ERROR]
        assert any(
            "CONSTRUCTION failed" in m and "CD #1534" in m for m in error_msgs
        ), f"Expected ERROR log naming construction failure, got: {error_msgs}"
        print(
            "[OK] _run_phase logs ERROR loud on construction failure (CD #1534 DoD #3)"
        )
