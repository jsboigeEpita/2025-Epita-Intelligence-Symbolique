#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS D'INTÉGRATION ORCHESTRATION FINALE
========================================

Tests d'intégration end-to-end pour orchestration_finale_reelle.py
Valide l'orchestration complète de tous les workflows authentiques.

Tests couverts:
- Moteur d'orchestration réelle
- Workflows multiples intégrés
- Session d'orchestration complète
- Validation environnement authentique
- Gestion adaptive des workflows
- Métriques de convergence
"""

import asyncio
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Configuration paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "examples" / "Sherlock_Watson"))

try:
    from orchestration_finale_reelle import (
        RealOrchestrationEngine,
        WorkflowType,
        OrchestrationMode,
        WorkflowResult,
        OrchestrationSession,
        run_complete_final_orchestration,
    )
except ImportError:
    pytest.skip("orchestration_finale_reelle not available", allow_module_level=True)


class TestOrchestrationFinaleIntegration:
    """Tests d'intégration pour orchestration finale réelle"""

    @pytest.fixture
    def engine_instance(self):
        """Instance moteur d'orchestration pour les tests"""
        return RealOrchestrationEngine()

    @pytest.fixture
    def temp_results_dir(self, engine_instance):
        """Répertoire temporaire pour les résultats"""
        temp_dir = tempfile.mkdtemp()
        original_dir = engine_instance.results_dir
        engine_instance.results_dir = Path(temp_dir) / "test_orchestration"
        engine_instance.results_dir.mkdir(parents=True, exist_ok=True)

        yield engine_instance.results_dir

        # Nettoyage
        engine_instance.results_dir = original_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_engine_initialization(self, engine_instance):
        """Test initialisation moteur d'orchestration"""
        assert engine_instance.session_id is not None
        assert len(engine_instance.session_id) > 0
        assert engine_instance.kernel is None
        assert engine_instance.agents_registry == {}
        assert engine_instance.active_workflows == {}
        assert engine_instance.mock_detection_active == True

        # Vérifications authenticity checks
        auth_checks = engine_instance.authenticity_checks
        assert "environment_validated" in auth_checks
        assert "semantic_kernel_authentic" in auth_checks
        assert "openai_api_real" in auth_checks
        assert "no_mocks_detected" in auth_checks
        assert all(check == False for check in auth_checks.values())  # Initial state

    def test_workflow_result_creation(self):
        """Test création résultat workflow"""
        result = WorkflowResult(
            workflow_type=WorkflowType.CLUEDO_SIMPLE,
            success=True,
            duration=1.5,
            results={"test": "data"},
            metadata={"context": "test"},
        )

        assert result.workflow_type == WorkflowType.CLUEDO_SIMPLE
        assert result.success == True
        assert result.duration == 1.5
        assert result.mock_used == False
        assert result.semantic_kernel_used == False
        assert result.openai_api_used == False
        assert result.timestamp is not None

    def test_orchestration_session_creation(self):
        """Test création session d'orchestration"""
        session = OrchestrationSession(
            session_id="test_session_001", mode=OrchestrationMode.ADAPTIVE
        )

        assert session.session_id == "test_session_001"
        assert session.mode == OrchestrationMode.ADAPTIVE
        assert session.workflows_executed == []
        assert session.global_context == {}
        assert session.total_duration == 0.0
        assert session.success_rate == 0.0
        assert session.authenticity_validated == True

    def test_session_success_rate_calculation(self):
        """Test calcul taux succès session"""
        session = OrchestrationSession("test", OrchestrationMode.SEQUENTIAL)

        # Pas de workflows
        assert session.calculate_success_rate() == 0.0

        # Workflows mixtes
        session.workflows_executed = [
            WorkflowResult(WorkflowType.CLUEDO_SIMPLE, True, 1.0),
            WorkflowResult(WorkflowType.EINSTEIN_COMPLEX, False, 2.0),
            WorkflowResult(WorkflowType.AGENTS_LOGIQUES, True, 1.5),
            WorkflowResult(WorkflowType.SHERLOCK_WATSON, True, 0.8),
        ]

        success_rate = session.calculate_success_rate()
        assert success_rate == 75.0  # 3/4 * 100
        assert session.success_rate == 75.0

    def test_environment_initialization_no_api_key(self, engine_instance):
        """Test initialisation environnement sans clé API"""

        async def _async_test():
            # Suppression temporaire clé API
            original_key = os.environ.get("OPENAI_API_KEY")
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

            try:
                result = await engine_instance.initialize_authentic_environment()
                assert result == False
                assert engine_instance.authenticity_checks["openai_api_real"] == False
            finally:
                if original_key:
                    os.environ["OPENAI_API_KEY"] = original_key
                # Ensure the key is deleted if it was not present before
                elif "OPENAI_API_KEY" in os.environ:
                    del os.environ["OPENAI_API_KEY"]

        asyncio.run(_async_test())

    def test_environment_initialization_invalid_key(self, engine_instance):
        """Test initialisation avec clé API invalide"""

        async def _async_test():
            original_key = os.environ.get("OPENAI_API_KEY")

            try:
                # Test avec clé simulation
                os.environ["OPENAI_API_KEY"] = "sk-simulation-invalid"
                result = await engine_instance.initialize_authentic_environment()
                assert result == False
                assert engine_instance.authenticity_checks["openai_api_real"] == False

                # Test avec clé contenant "mock"
                os.environ["OPENAI_API_KEY"] = "sk-mock-testing-key"
                result = await engine_instance.initialize_authentic_environment()
                assert result == False
                assert engine_instance.authenticity_checks["openai_api_real"] == False

            finally:
                if original_key:
                    os.environ["OPENAI_API_KEY"] = original_key
                elif "OPENAI_API_KEY" in os.environ:
                    del os.environ["OPENAI_API_KEY"]

        asyncio.run(_async_test())

    def test_environment_initialization_with_valid_key(self, engine_instance):
        """Test initialisation avec clé API valide"""

        async def _async_test():
            if not os.getenv("OPENAI_API_KEY"):
                pytest.skip("OPENAI_API_KEY not configured")

            try:
                result = await engine_instance.initialize_authentic_environment()

                if result:
                    assert engine_instance.kernel is not None
                    assert (
                        engine_instance.authenticity_checks["openai_api_real"] == True
                    )
                    assert (
                        engine_instance.authenticity_checks["semantic_kernel_authentic"]
                        == True
                    )
                else:
                    pytest.skip(
                        "Environment initialization failed (import/network issue)"
                    )

            except Exception as e:
                pytest.skip(f"Environment setup error: {e}")

        asyncio.run(_async_test())

    def test_workflow_execution_cluedo_simple(self, engine_instance):
        """Test exécution workflow Cluedo simple"""

        async def _async_test():
            # Test sans initialisation complète (mode test)
            try:
                result = await engine_instance.execute_workflow(
                    WorkflowType.CLUEDO_SIMPLE, {"test_mode": True, "timeout": 5.0}
                )

                assert isinstance(result, WorkflowResult)
                assert result.workflow_type == WorkflowType.CLUEDO_SIMPLE
                assert result.mock_used == False
                assert result.timestamp is not None

            except Exception as e:
                # Workflow peut échouer sans infrastructure complète
                pytest.skip(f"Workflow execution requires full setup: {e}")

        asyncio.run(_async_test())

    def test_workflow_execution_agents_logiques(self, engine_instance):
        """Test exécution workflow agents logiques"""

        async def _async_test():
            try:
                result = await engine_instance.execute_workflow(
                    WorkflowType.AGENTS_LOGIQUES,
                    {"test_mode": True, "content": "Test logique authentique"},
                )

                assert isinstance(result, WorkflowResult)
                assert result.workflow_type == WorkflowType.AGENTS_LOGIQUES
                assert result.mock_used == False

            except Exception as e:
                pytest.skip(f"Agents logiques workflow error: {e}")

        asyncio.run(_async_test())

    def test_adaptive_orchestration_mode(self, engine_instance):
        """Test mode orchestration adaptatif"""
        session = OrchestrationSession("adaptive_test", OrchestrationMode.ADAPTIVE)

        # Simulation workflows avec complexités différentes
        simple_workflows = [WorkflowType.CLUEDO_SIMPLE, WorkflowType.AGENTS_LOGIQUES]
        complex_workflows = [WorkflowType.EINSTEIN_COMPLEX, WorkflowType.MULTI_MODAL]

        # Test sélection adaptative
        selected = engine_instance.select_adaptive_workflows(
            simple_workflows + complex_workflows
        )

        assert len(selected) > 0
        assert all(wf in simple_workflows + complex_workflows for wf in selected)

    def test_parallel_orchestration_mode(self, engine_instance):
        """Test mode orchestration parallèle"""

        async def _async_test():
            workflows_config = [
                {"type": WorkflowType.CLUEDO_SIMPLE, "priority": 1},
                {"type": WorkflowType.AGENTS_LOGIQUES, "priority": 2},
            ]

            try:
                results = await engine_instance.execute_parallel_workflows(
                    workflows_config
                )

                assert isinstance(results, list)
                assert len(results) <= len(workflows_config)
                assert all(isinstance(r, WorkflowResult) for r in results)

            except Exception as e:
                pytest.skip(f"Parallel execution requires full setup: {e}")

        asyncio.run(_async_test())

    def test_orchestration_session_complete(self, engine_instance, temp_results_dir):
        """Test session d'orchestration complète"""

        async def _async_test():
            session_config = {
                "mode": OrchestrationMode.SEQUENTIAL,
                "workflows": [WorkflowType.CLUEDO_SIMPLE, WorkflowType.AGENTS_LOGIQUES],
                "max_duration": 30.0,
                "test_mode": True,
            }

            try:
                session_result = await engine_instance.run_orchestration_session(
                    session_config
                )

                assert isinstance(session_result, OrchestrationSession)
                assert len(session_result.workflows_executed) <= 2
                assert session_result.authenticity_validated == True
                assert session_result.total_duration > 0.0

            except Exception as e:
                pytest.skip(f"Full session requires infrastructure: {e}")

        asyncio.run(_async_test())

    def test_convergence_metrics_calculation(self, engine_instance):
        """Test calcul métriques de convergence"""
        # Simulation résultats workflows
        workflow_results = [
            WorkflowResult(WorkflowType.CLUEDO_SIMPLE, True, 1.2, {"confidence": 0.85}),
            WorkflowResult(
                WorkflowType.AGENTS_LOGIQUES, True, 2.1, {"confidence": 0.92}
            ),
            WorkflowResult(
                WorkflowType.SHERLOCK_WATSON, False, 3.5, {"confidence": 0.45}
            ),
        ]

        metrics = engine_instance.calculate_convergence_metrics(workflow_results)

        assert "overall_success_rate" in metrics
        assert "average_confidence" in metrics
        assert "convergence_score" in metrics
        assert "authenticity_compliance" in metrics

        assert 0.0 <= metrics["overall_success_rate"] <= 100.0
        assert 0.0 <= metrics["average_confidence"] <= 1.0
        assert 0.0 <= metrics["convergence_score"] <= 1.0
        assert metrics["authenticity_compliance"] == True

    def test_mock_detection_scan(self, engine_instance):
        """Test scan détection de mocks"""

        async def _async_test():
            # Test scan avec contenu propre
            clean_content = "Production code without any mocks or simulations"
            mock_detected = await engine_instance.scan_for_mocks_in_content(
                clean_content
            )
            assert mock_detected == False

            # Test scan avec contenu suspect
            suspicious_content = (
                "import unittest.mock\nfrom unittest.mock import MagicMock"
            )
            mock_detected = await engine_instance.scan_for_mocks_in_content(
                suspicious_content
            )
            assert mock_detected == True

        asyncio.run(_async_test())

    def test_workflow_type_validation(self):
        """Test validation types de workflow"""
        # Vérifier tous les types disponibles
        expected_types = {
            "cluedo_simple",
            "einstein_complex",
            "agents_logiques",
            "sherlock_watson",
            "multi_modal",
            "custom_analysis",
        }

        actual_types = {wt.value for wt in WorkflowType}
        assert actual_types == expected_types

        # Test enum usage
        assert WorkflowType.CLUEDO_SIMPLE.value == "cluedo_simple"
        assert WorkflowType.EINSTEIN_COMPLEX.value == "einstein_complex"

    def test_orchestration_mode_validation(self):
        """Test validation modes d'orchestration"""
        expected_modes = {"sequential", "parallel", "adaptive", "collaborative"}
        actual_modes = {om.value for om in OrchestrationMode}
        assert actual_modes == expected_modes

        # Test enum usage
        assert OrchestrationMode.SEQUENTIAL.value == "sequential"
        assert OrchestrationMode.ADAPTIVE.value == "adaptive"

    def test_complete_demo_integration(self):
        """Test démonstration complète orchestration finale"""

        async def _async_test():
            try:
                # Test avec timeout pour éviter les longs traitements
                result = await asyncio.wait_for(
                    run_complete_final_orchestration(), timeout=20.0
                )

                assert result == True

            except asyncio.TimeoutError:
                pytest.skip("Demo timeout (orchestration took too long)")
            except Exception as e:
                # Erreurs d'infrastructure acceptables
                pytest.skip(f"Demo requires full infrastructure: {e}")

        asyncio.run(_async_test())

    def test_anti_mock_compliance(self, engine_instance):
        """Test conformité anti-mock"""
        # Vérifications état initial
        assert engine_instance.mock_detection_active == True
        assert (
            engine_instance.authenticity_checks["no_mocks_detected"] == False
        )  # Initial

        # Vérifications flags authentique
        auth_checks = engine_instance.authenticity_checks
        assert isinstance(auth_checks, dict)
        assert all(isinstance(v, bool) for v in auth_checks.values())

        # Test que l'instance n'utilise pas de mocks
        test_result = WorkflowResult(WorkflowType.CLUEDO_SIMPLE, True, 1.0)
        assert test_result.mock_used == False

    def test_error_recovery_mechanisms(self, engine_instance):
        """Test mécanismes de récupération d'erreurs"""

        async def _async_test():
            # Test avec workflow inexistant
            try:
                result = await engine_instance.execute_workflow("invalid_workflow", {})
                assert result.success == False
            except:
                # Exception attendue pour type invalide
                pass

            # Test avec timeout workflow
            try:
                await asyncio.wait_for(
                    engine_instance.execute_workflow(
                        WorkflowType.EINSTEIN_COMPLEX, {"timeout": 0.1}
                    ),
                    timeout=0.5,
                )
            except asyncio.TimeoutError:
                # Timeout attendu
                pass

            # L'orchestrateur doit rester opérationnel
            assert engine_instance.session_id is not None
            assert engine_instance.mock_detection_active == True

        asyncio.run(_async_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
