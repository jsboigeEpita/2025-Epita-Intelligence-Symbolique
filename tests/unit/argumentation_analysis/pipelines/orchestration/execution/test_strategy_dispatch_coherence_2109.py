"""Gardes de cohérence producteur/dispatcher des stratégies d'orchestration (#2109).

Défaut historique : ``select_orchestration_strategy`` peut calculer des valeurs
que ``engine.py`` ne sait pas dispatcher — elles tombaient silencieusement dans
``execute_hybrid_orchestration`` (``else`` catch-all). Le contrat est désormais :

- toute valeur calculée par le producteur mais absente de la table de dispatch
  lève ``ValueError`` au moment de la sélection (jamais de repli silencieux) ;
- la table de dispatch du moteur (``STRATEGY_EXECUTORS``) et l'ensemble
  ``DISPATCHABLE_STRATEGIES`` du producteur sont exactement égaux — le garde
  rougit dans les deux sens de dérive.

Le contrôle positif (TestPositiveControlDriftReddens) prouve que l'instrument
mesure : une valeur neuve injectée d'un seul côté doit faire rougir le garde.
"""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


def _ensure_importable():
    """Même garde DLL torch que test_execution_strategies.py (WinError 182)."""
    if "torch" not in sys.modules:
        try:
            import torch  # noqa: F401
        except (OSError, ImportError):
            sys.modules["torch"] = MagicMock()


_ensure_importable()

from argumentation_analysis.pipelines.orchestration.config.enums import (  # noqa: E402
    AnalysisType,
    OrchestrationMode,
)
from argumentation_analysis.pipelines.orchestration.execution import (  # noqa: E402
    engine as engine_module,
    strategies as strategies_module,
)


def _make_config(
    orchestration_mode_enum=OrchestrationMode.AUTO_SELECT,
    analysis_type=AnalysisType.COMPREHENSIVE,
    auto_select_orchestrator=True,
    enable_hierarchical=True,
):
    cfg = MagicMock()
    cfg.orchestration_mode_enum = orchestration_mode_enum
    cfg.analysis_type = analysis_type
    cfg.auto_select_orchestrator = auto_select_orchestrator
    cfg.enable_hierarchical = enable_hierarchical
    return cfg


def _make_pipeline(config):
    pipe = MagicMock()
    pipe.config = config
    return pipe


def _assert_coherence():
    """Le cœur du garde : table de dispatch == ensemble dispatchable."""
    executors = getattr(engine_module, "STRATEGY_EXECUTORS", None)
    dispatchable = getattr(strategies_module, "DISPATCHABLE_STRATEGIES", None)
    assert executors is not None, (
        "engine.STRATEGY_EXECUTORS doit exister et être la table de dispatch "
        "explicite (#2109)"
    )
    assert dispatchable is not None, (
        "strategies.DISPATCHABLE_STRATEGIES doit exister et être l'ensemble des "
        "valeurs dispatchables (#2109)"
    )
    assert set(executors) == set(dispatchable), (
        "Dérive producteur/dispatcher : "
        f"présents d'un seul côté : {sorted(set(executors) ^ set(dispatchable))}. "
        "Toute valeur productible doit être dispatchable, et réciproquement (#2109)."
    )


class TestDispatchCoherence:
    """La table de dispatch et l'ensemble dispatchable coïncident, fil par fil."""

    def test_engine_dispatch_table_equals_dispatchable_strategies(self):
        _assert_coherence()

    def test_each_strategy_wired_to_its_named_executor(self):
        """Set-égalité ne suffit pas : chaque clé doit pointer SON exécuteur."""
        executors = getattr(engine_module, "STRATEGY_EXECUTORS", None)
        assert executors is not None, "engine.STRATEGY_EXECUTORS doit exister (#2109)"
        assert (
            executors["hierarchical_full"]
            is strategies_module.execute_hierarchical_full_orchestration
        )
        assert (
            executors["specialized_direct"]
            is strategies_module.execute_specialized_orchestration
        )
        assert executors["fallback"] is strategies_module.execute_fallback_orchestration
        assert executors["hybrid"] is strategies_module.execute_hybrid_orchestration


class TestEngineDispatchBehavior:
    """Le dispatcher ne route plus l'inconnu vers l'hybride."""

    @pytest.mark.asyncio
    async def test_unknown_strategy_is_loud_not_silent_hybrid(self, monkeypatch):
        """Une valeur hors table doit produire une erreur NOMMÉE, pas un
        exécution hybride silencieuse qui se terminerait en status=success."""
        pipeline = MagicMock()
        pipeline.initialized = True
        pipeline.orchestration_trace = []
        pipeline._trace_orchestration = MagicMock()
        pipeline.config = MagicMock()
        pipeline.config.orchestration_mode_enum.value = "strategic_only"
        pipeline.config.save_orchestration_trace = False

        async def _bogus_select(p, text, custom_config=None):
            return "strategic_only"

        monkeypatch.setattr(
            engine_module, "select_orchestration_strategy", _bogus_select
        )
        monkeypatch.setattr(
            engine_module,
            "post_process_orchestration_results",
            AsyncMock(side_effect=lambda pipeline, results: results),
        )

        results = await engine_module.analyze_text_orchestrated(pipeline, "text")

        assert results["status"] == "error", (
            "Une stratégie non dispatchable doit terminer en erreur, pas en "
            "success après un repli silencieux vers hybrid (#2109)"
        )
        assert "strategic_only" in results["error"]


class TestPositiveControlDriftReddens:
    """Contrôle positif : le garde doit rougir sur une valeur neuve non aiguillée.

    Simule les deux dérives possibles (valeur ajoutée d'un seul côté de
    l'égalité) et vérifie que le garde les détecte — preuve que l'instrument
    mesure, pas qu'il rend la même valeur sur toute population.
    """

    def test_sixth_value_on_producer_side_reddens(self, monkeypatch):
        _, dispatchable = (
            getattr(engine_module, "STRATEGY_EXECUTORS", None),
            getattr(strategies_module, "DISPATCHABLE_STRATEGIES", None),
        )
        assert (
            dispatchable is not None
        ), "contrôle positif inopérant tant que le fix n'existe pas (#2109)"
        drifted = frozenset(set(dispatchable) | {"sixth_value"})
        monkeypatch.setattr(
            strategies_module, "DISPATCHABLE_STRATEGIES", drifted, raising=False
        )
        with pytest.raises(AssertionError):
            _assert_coherence()

    def test_sixth_value_on_engine_side_reddens(self, monkeypatch):
        executors = getattr(engine_module, "STRATEGY_EXECUTORS", None)
        assert (
            executors is not None
        ), "contrôle positif inopérant tant que le fix n'existe pas (#2109)"
        drifted = dict(executors)
        drifted["sixth_value"] = drifted["hybrid"]
        monkeypatch.setattr(engine_module, "STRATEGY_EXECUTORS", drifted, raising=False)
        with pytest.raises(AssertionError):
            _assert_coherence()

    def test_real_state_is_coherent(self):
        """Vert sur l'état réel — c'est lui qui prouve que les contrôles
        positifs ci-dessus distinguent dérive et cohérence."""
        _assert_coherence()
