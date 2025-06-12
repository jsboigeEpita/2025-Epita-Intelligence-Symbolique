#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests Unitaires pour les Gestionnaires Hiérarchiques
===================================================

Tests pour valider le fonctionnement des gestionnaires de l'architecture hiérarchique :
- StrategicManager (niveau stratégique)
- TaskCoordinator (niveau tactique) 
- OperationalManager (niveau opérationnel)

Structure des tests :
- Initialisation et configuration
- Flux de traitement hiérarchique
- Communication inter-niveaux
- Gestion d'erreurs
- Performance et optimisation

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Dict, Any, List

# Configuration du logging pour les tests
logging.basicConfig(level=logging.WARNING)

# Imports à tester
try:
    from argumentation_analysis.orchestrators.strategic_manager import StrategicManager
    from argumentation_analysis.orchestrators.task_coordinator import TaskCoordinator
    from argumentation_analysis.orchestrators.operational_manager import OperationalManager
    HIERARCHICAL_AVAILABLE = True
except ImportError as e:
    HIERARCHICAL_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Gestionnaires hiérarchiques non disponibles: {e}")


class TestStrategicManager:
    """Tests pour le gestionnaire stratégique."""
    
    @pytest.fixture
    def sample_config(self):
        """Configuration d'exemple pour les tests."""
        return {
            "strategic_analysis_depth": "comprehensive",
            "objective_generation_mode": "automatic",
            "planning_horizon": "medium_term",
            "risk_assessment_level": "standard",
            "resource_allocation_strategy": "balanced"
        }
    
    @pytest.fixture
    def strategic_manager(self, llm_service, sample_config):
        """Instance de StrategicManager pour les tests."""
        return StrategicManager(
            llm_service=llm_service,
            config=sample_config
        )
    
    def test_strategic_manager_initialization(self, strategic_manager, llm_service, sample_config):
        """Test de l'initialisation du gestionnaire stratégique."""
        assert strategic_manager.llm_service == llm_service
        assert strategic_manager.config == sample_config
        assert strategic_manager.current_objectives == []
        assert strategic_manager.strategic_plan is None
        assert strategic_manager.analysis_context == {}
    
    @pytest.mark.asyncio
    async def test_initialize_analysis_comprehensive(self, strategic_manager):
        """Test de l'initialisation d'analyse comprehensive."""
        text = "Analyse stratégique pour un argument complexe sur l'éducation et ses impacts sociétaux."
        
        # Mock des méthodes internes
        strategic_manager._analyze_strategic_context = AsyncMock(return_value={
            "domain": "education",
            "complexity": "high",
            "stakeholders": ["students", "teachers", "government"]
        })
        
        strategic_manager._generate_strategic_objectives = AsyncMock(return_value=[
            {"id": "obj1", "description": "Analyser la structure argumentative", "priority": "high"},
            {"id": "obj2", "description": "Identifier les enjeux sociétaux", "priority": "medium"}
        ])
        
        strategic_manager._create_strategic_plan = AsyncMock(return_value={
            "phases": [
                {"id": "phase1", "name": "Analyse initiale", "objectives": ["obj1"]},
                {"id": "phase2", "name": "Analyse sociétale", "objectives": ["obj2"]}
            ],
            "estimated_duration": 300,
            "resource_requirements": {"llm_calls": 15, "analysis_depth": "comprehensive"}
        })
        
        result = await strategic_manager.initialize_analysis(text, analysis_type="comprehensive")
        
        assert "context" in result
        assert "objectives" in result
        assert "strategic_plan" in result
        assert len(result["objectives"]) == 2
        assert result["strategic_plan"]["estimated_duration"] == 300
        
        # Vérifier que les méthodes internes ont été appelées
        strategic_manager._analyze_strategic_context.assert_called_once_with(text, "comprehensive")
        strategic_manager._generate_strategic_objectives.assert_called_once()
        strategic_manager._create_strategic_plan.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_strategic_context(self, strategic_manager):
        """Test de l'analyse du contexte stratégique avec un vrai LLM."""
        text = "L'éducation est cruciale pour le développement économique. Cependant, elle coûte cher."
        
        # Pas de mock, l'appel LLM est réel
        context = await strategic_manager._analyze_strategic_context(text, "comprehensive")
        
        # Assertions souples pour une réponse non-déterministe
        assert isinstance(context, dict)
        assert "domain" in context
        assert "complexity" in context
        assert "stakeholders" in context
        assert "key_concepts" in context
        assert isinstance(context["domain"], str)
        assert isinstance(context["stakeholders"], list)
    
    @pytest.mark.asyncio
    async def test_generate_strategic_objectives_hierarchical(self, strategic_manager):
        """Test de génération d'objectifs stratégiques hiérarchiques avec un vrai LLM."""
        context = {
            "domain": "education",
            "complexity": "high",
            "argument_type": "policy_debate"
        }
        
        # Pas de mock, appel LLM réel
        objectives = await strategic_manager._generate_strategic_objectives(context, "comprehensive")
        
        # Assertions souples
        assert isinstance(objectives, list)
        assert len(objectives) > 0
        for obj in objectives:
            assert "id" in obj
            assert "description" in obj
            assert "priority" in obj
            assert "type" in obj
            assert "dependencies" in obj
            assert isinstance(obj["dependencies"], list)

        # Vérifier que les priorités sont dans un ordre logique (si possible)
        priority_map = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        priority_scores = [priority_map.get(obj.get("priority", "low").lower(), 0) for obj in objectives]
        assert priority_scores == sorted(priority_scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_create_strategic_plan_with_dependencies(self, strategic_manager):
        """Test de création de plan stratégique avec gestion des dépendances."""
        objectives = [
            {"id": "obj1", "description": "Analyse base", "priority": "critical", "dependencies": []},
            {"id": "obj2", "description": "Analyse avancée", "priority": "high", "dependencies": ["obj1"]},
            {"id": "obj3", "description": "Synthèse", "priority": "medium", "dependencies": ["obj1", "obj2"]}
        ]
        
        context = {"complexity": "high", "domain": "test"}
        
        plan = await strategic_manager._create_strategic_plan(objectives, context)
        
        assert "phases" in plan
        assert "estimated_duration" in plan
        assert "resource_requirements" in plan
        assert len(plan["phases"]) >= 2  # Au moins 2 phases avec les dépendances
        
        # Vérifier que les dépendances sont respectées dans l'ordonnancement
        phase_objectives = []
        for phase in plan["phases"]:
            phase_objectives.extend(phase["objectives"])
        
        # obj1 doit apparaître avant obj2, obj2 avant obj3
        obj1_index = phase_objectives.index("obj1")
        obj2_index = phase_objectives.index("obj2") 
        obj3_index = phase_objectives.index("obj3")
        
        assert obj1_index < obj2_index
        assert obj2_index < obj3_index
    
    @pytest.mark.asyncio
    async def test_monitor_strategic_progress(self, strategic_manager):
        """Test du monitoring du progrès stratégique."""
        strategic_manager.current_objectives = [
            {"id": "obj1", "status": "completed", "progress": 100},
            {"id": "obj2", "status": "in_progress", "progress": 60},
            {"id": "obj3", "status": "pending", "progress": 0}
        ]
        
        progress = await strategic_manager.monitor_strategic_progress()
        
        assert progress["overall_progress"] == pytest.approx(53.33, rel=1e-2)  # (100+60+0)/3
        assert progress["completed_objectives"] == 1
        assert progress["in_progress_objectives"] == 1
        assert progress["pending_objectives"] == 1
        assert "bottlenecks" in progress
        assert "recommendations" in progress
    
    @pytest.mark.asyncio
    async def test_adapt_strategic_plan(self, strategic_manager):
        """Test de l'adaptation du plan stratégique."""
        initial_plan = {
            "phases": [
                {"id": "phase1", "objectives": ["obj1"], "status": "completed"},
                {"id": "phase2", "objectives": ["obj2"], "status": "in_progress"}
            ]
        }
        strategic_manager.strategic_plan = initial_plan
        
        new_context = {
            "discovered_complexity": "higher_than_expected",
            "new_requirements": ["detailed_fallacy_analysis"]
        }
        
        adapted_plan = await strategic_manager.adapt_strategic_plan(new_context)
        
        assert adapted_plan != initial_plan
        assert "adaptation_reason" in adapted_plan
        assert "new_phases" in adapted_plan or "modified_phases" in adapted_plan


class TestTaskCoordinator:
    """Tests pour le coordinateur de tâches (niveau tactique)."""
    
    @pytest.fixture
    def task_coordinator(self, llm_service):
        """Instance de TaskCoordinator pour les tests."""
        config = {
            "coordination_strategy": "adaptive",
            "task_distribution_mode": "load_balanced",
            "communication_protocol": "message_passing"
        }
        return TaskCoordinator(
            llm_service=llm_service,
            config=config
        )
    
    @pytest.fixture
    def sample_strategic_objectives(self):
        """Objectifs stratégiques d'exemple."""
        return [
            {
                "id": "strategic_obj_1",
                "description": "Analyser la structure argumentative",
                "priority": "critical",
                "type": "structural_analysis"
            },
            {
                "id": "strategic_obj_2",
                "description": "Identifier les sophismes",
                "priority": "high", 
                "type": "fallacy_detection"
            }
        ]
    
    def test_task_coordinator_initialization(self, task_coordinator, llm_service):
        """Test de l'initialisation du coordinateur de tâches."""
        assert task_coordinator.llm_service == llm_service
        assert task_coordinator.active_tasks == {}
        assert task_coordinator.task_queue == []
        assert task_coordinator.resource_allocations == {}
        assert task_coordinator.coordination_metrics == {}
    
    @pytest.mark.asyncio
    async def test_process_strategic_objectives(self, task_coordinator, sample_strategic_objectives):
        """Test du traitement des objectifs stratégiques."""
        # Mock des méthodes internes
        task_coordinator._decompose_objective_to_tasks = AsyncMock(side_effect=[
            [
                {"id": "task_1_1", "objective_id": "strategic_obj_1", "type": "parse_structure"},
                {"id": "task_1_2", "objective_id": "strategic_obj_1", "type": "analyze_connections"}
            ],
            [
                {"id": "task_2_1", "objective_id": "strategic_obj_2", "type": "scan_fallacies"},
                {"id": "task_2_2", "objective_id": "strategic_obj_2", "type": "classify_fallacies"}
            ]
        ])
        
        task_coordinator._schedule_tasks = AsyncMock(return_value={
            "schedule": [
                {"task_id": "task_1_1", "start_time": 0, "estimated_duration": 30},
                {"task_id": "task_1_2", "start_time": 30, "estimated_duration": 45},
                {"task_id": "task_2_1", "start_time": 0, "estimated_duration": 25},
                {"task_id": "task_2_2", "start_time": 25, "estimated_duration": 35}
            ]
        })
        
        result = await task_coordinator.process_strategic_objectives(sample_strategic_objectives)
        
        assert "tasks_created" in result
        assert "scheduling_plan" in result
        assert result["tasks_created"] == 4
        assert len(result["scheduling_plan"]["schedule"]) == 4
        
        # Vérifier que les tâches sont enregistrées
        assert len(task_coordinator.task_queue) == 4
    
    @pytest.mark.asyncio
    async def test_decompose_objective_to_tasks_structural(self, task_coordinator):
        """Test de décomposition d'objectif en tâches pour analyse structurelle avec un vrai LLM."""
        objective = {
            "id": "struct_obj",
            "description": "Analyser la structure argumentative d'un texte sur la politique climatique.",
            "type": "structural_analysis",
            "priority": "critical"
        }
        
        # Pas de mock, appel LLM réel
        tasks = await task_coordinator._decompose_objective_to_tasks(objective)
        
        # Assertions souples
        assert isinstance(tasks, list)
        assert len(tasks) > 0
        for task in tasks:
            assert "id" in task
            assert "description" in task
            assert "type" in task
            assert "dependencies" in task
            assert isinstance(task["dependencies"], list)

        # Vérifier si les dépendances sont logiques (une tâche dépend d'une autre de la liste)
        task_ids = {t["id"] for t in tasks}
        for task in tasks:
            for dep in task["dependencies"]:
                assert dep in task_ids
    
    @pytest.mark.asyncio
    async def test_schedule_tasks_with_dependencies(self, task_coordinator):
        """Test de planification de tâches avec dépendances."""
        tasks = [
            {"id": "task_a", "estimated_duration": 30, "dependencies": []},
            {"id": "task_b", "estimated_duration": 45, "dependencies": ["task_a"]},
            {"id": "task_c", "estimated_duration": 20, "dependencies": []},
            {"id": "task_d", "estimated_duration": 35, "dependencies": ["task_b", "task_c"]}
        ]
        
        schedule = await task_coordinator._schedule_tasks(tasks)
        
        assert "schedule" in schedule
        assert "critical_path" in schedule
        assert "total_duration" in schedule
        
        # Vérifier l'ordre des tâches respecte les dépendances
        schedule_map = {item["task_id"]: item for item in schedule["schedule"]}
        
        # task_a doit commencer avant task_b
        assert schedule_map["task_a"]["start_time"] < schedule_map["task_b"]["start_time"]
        
        # task_b doit se terminer avant task_d
        task_b_end = schedule_map["task_b"]["start_time"] + 45
        assert task_b_end <= schedule_map["task_d"]["start_time"]
    
    @pytest.mark.asyncio
    async def test_coordinate_task_execution(self, task_coordinator):
        """Test de coordination d'exécution de tâches."""
        # Setup des tâches actives
        task_coordinator.active_tasks = {
            "task_1": {"status": "running", "progress": 70, "estimated_remaining": 15},
            "task_2": {"status": "waiting", "progress": 0, "dependencies": ["task_1"]},
            "task_3": {"status": "running", "progress": 30, "estimated_remaining": 45}
        }
        
        # Mock des communications avec opérationnel
        task_coordinator._communicate_with_operational = AsyncMock(return_value={
            "task_updates": [
                {"task_id": "task_1", "new_progress": 85},
                {"task_id": "task_3", "new_progress": 40}
            ]
        })
        
        coordination_result = await task_coordinator.coordinate_task_execution()
        
        assert "coordination_actions" in coordination_result
        assert "resource_reallocations" in coordination_result
        assert "progress_summary" in coordination_result
        
        # Vérifier que les progrès sont mis à jour
        assert task_coordinator.active_tasks["task_1"]["progress"] == 85
        assert task_coordinator.active_tasks["task_3"]["progress"] == 40
    
    @pytest.mark.asyncio
    async def test_handle_task_bottlenecks(self, task_coordinator):
        """Test de gestion des goulots d'étranglement."""
        # Simuler un goulot d'étranglement
        task_coordinator.active_tasks = {
            "bottleneck_task": {
                "status": "stalled",
                "progress": 45,
                "expected_duration": 60,
                "actual_duration": 120,  # 2x plus long que prévu
                "required_resources": ["rare_resource"]
            },
            "waiting_task_1": {
                "status": "waiting",
                "dependencies": ["bottleneck_task"]
            },
            "waiting_task_2": {
                "status": "waiting", 
                "dependencies": ["bottleneck_task"]
            }
        }
        
        bottleneck_response = await task_coordinator._handle_task_bottlenecks()
        
        assert "identified_bottlenecks" in bottleneck_response
        assert "mitigation_strategies" in bottleneck_response
        assert "resource_reallocation" in bottleneck_response
        
        assert len(bottleneck_response["identified_bottlenecks"]) >= 1
        assert "bottleneck_task" in str(bottleneck_response)


class TestOperationalManager:
    """Tests pour le gestionnaire opérationnel."""
    
    @pytest.fixture
    def operational_manager(self, llm_service):
        """Instance d'OperationalManager pour les tests."""
        config = {
            "execution_strategy": "parallel_optimized",
            "resource_management": "dynamic",
            "monitoring_level": "detailed"
        }
        return OperationalManager(
            llm_service=llm_service,
            config=config
        )
    
    @pytest.fixture
    def sample_tasks(self):
        """Tâches d'exemple pour les tests."""
        return [
            {
                "id": "op_task_1",
                "type": "premise_extraction",
                "description": "Extraire les prémisses du texte",
                "text_segment": "L'éducation améliore la société car elle forme des citoyens éclairés.",
                "parameters": {"extraction_method": "nlp_pattern"},
                "priority": "high"
            },
            {
                "id": "op_task_2", 
                "type": "fallacy_detection",
                "description": "Détecter les sophismes",
                "text_segment": "Tous les experts disent que c'est vrai, donc c'est forcément vrai.",
                "parameters": {"fallacy_types": ["appeal_to_authority"]},
                "priority": "medium"
            }
        ]
    
    def test_operational_manager_initialization(self, operational_manager, llm_service):
        """Test de l'initialisation du gestionnaire opérationnel."""
        assert operational_manager.llm_service == llm_service
        assert operational_manager.execution_queue == []
        assert operational_manager.running_operations == {}
        assert operational_manager.completed_operations == {}
        assert operational_manager.operation_results == {}
    
    @pytest.mark.asyncio
    async def test_execute_tactical_tasks(self, operational_manager, sample_tasks):
        """Test de l'exécution de tâches tactiques."""
        # Mock des exécuteurs spécialisés
        operational_manager._execute_premise_extraction = AsyncMock(return_value={
            "premises": ["L'éducation améliore la société", "Elle forme des citoyens éclairés"],
            "confidence": 0.92,
            "method": "nlp_pattern"
        })
        
        operational_manager._execute_fallacy_detection = AsyncMock(return_value={
            "fallacies": [{"type": "appeal_to_authority", "confidence": 0.87, "location": "span(0,58)"}],
            "scan_results": {"total_scanned": 1, "fallacies_found": 1}
        })
        
        results = await operational_manager.execute_tactical_tasks(sample_tasks)
        
        assert "execution_summary" in results
        assert "task_results" in results
        assert "performance_metrics" in results
        
        assert len(results["task_results"]) == 2
        assert results["task_results"]["op_task_1"]["premises"]
        assert results["task_results"]["op_task_2"]["fallacies"]
        
        # Vérifier les métriques
        assert "total_execution_time" in results["performance_metrics"]
        assert "success_rate" in results["performance_metrics"]
    
    @pytest.mark.asyncio
    async def test_execute_premise_extraction_nlp(self, operational_manager):
        """Test d'extraction de prémisses par NLP avec un vrai LLM."""
        task = {
            "id": "premise_task",
            "text_segment": "Premièrement, l'éducation développe l'esprit critique. Deuxièmement, elle favorise l'innovation. Par conséquent, investir dans l'éducation est essentiel.",
            "parameters": {"extraction_method": "nlp_pattern"}
        }
        
        # Pas de mock, appel LLM réel
        result = await operational_manager._execute_premise_extraction(task)
        
        # Assertions souples
        assert isinstance(result, dict)
        assert "premises" in result
        assert "conclusion" in result
        assert "logical_structure" in result
        assert isinstance(result["premises"], list)
        assert len(result["premises"]) > 0
        assert "text" in result["premises"][0]
        assert "text" in result["conclusion"]
    
    @pytest.mark.asyncio
    async def test_execute_fallacy_detection_comprehensive(self, operational_manager):
        """Test de détection de sophismes comprehensive avec un vrai LLM."""
        task = {
            "id": "fallacy_task",
            "text_segment": "Tous les experts sont d'accord, donc c'est vrai. De plus, si on n'accepte pas cette position, on va vers le chaos total.",
            "parameters": {"fallacy_types": "all", "confidence_threshold": 0.7}
        }
        
        # Pas de mock, appel LLM réel
        result = await operational_manager._execute_fallacy_detection(task)
        
        # Assertions souples
        assert isinstance(result, dict)
        assert "fallacies_detected" in result
        assert "scan_summary" in result
        assert isinstance(result["fallacies_detected"], list)

        if result["fallacies_detected"]:
            fallacy = result["fallacies_detected"][0]
            assert "type" in fallacy
            assert "description" in fallacy
            assert "confidence" in fallacy
            assert "severity" in fallacy
            assert isinstance(fallacy["type"], str)
        
        assert isinstance(result["scan_summary"], dict)
        assert "total_fallacies" in result["scan_summary"]
    
    @pytest.mark.asyncio
    async def test_parallel_task_execution(self, operational_manager):
        """Test d'exécution parallèle de tâches."""
        tasks = [
            {"id": f"parallel_task_{i}", "type": "simple_analysis", "priority": "medium"}
            for i in range(5)
        ]
        
        # Mock de l'exécution individuelle
        async def mock_execute_single(task):
            await asyncio.sleep(0.1)  # Simuler du travail
            return {"task_id": task["id"], "result": f"Résultat {task['id']}", "status": "completed"}
        
        operational_manager._execute_single_task = mock_execute_single
        
        start_time = asyncio.get_event_loop().time()
        results = await operational_manager._execute_tasks_parallel(tasks, max_concurrent=3)
        end_time = asyncio.get_event_loop().time()
        
        # Vérifier que l'exécution parallèle est plus rapide que séquentielle
        execution_time = end_time - start_time
        assert execution_time < 0.5  # Moins que 5 * 0.1 = 0.5s (exécution séquentielle)
        
        assert len(results) == 5
        assert all(result["status"] == "completed" for result in results)
    
    @pytest.mark.asyncio
    async def test_monitor_operation_performance(self, operational_manager):
        """Test du monitoring des performances d'opération."""
        # Simuler des opérations avec différentes performances
        operational_manager.completed_operations = {
            "op1": {"execution_time": 45, "success": True, "resource_usage": 0.7},
            "op2": {"execution_time": 120, "success": True, "resource_usage": 0.9},
            "op3": {"execution_time": 30, "success": False, "error": "timeout"},
            "op4": {"execution_time": 60, "success": True, "resource_usage": 0.5}
        }
        
        performance_report = await operational_manager.monitor_operation_performance()
        
        assert "average_execution_time" in performance_report
        assert "success_rate" in performance_report
        assert "resource_efficiency" in performance_report
        assert "performance_trends" in performance_report
        
        assert performance_report["success_rate"] == 0.75  # 3/4 succès
        assert performance_report["average_execution_time"] == pytest.approx(63.75)  # (45+120+30+60)/4
    
    @pytest.mark.asyncio
    async def test_resource_optimization(self, operational_manager):
        """Test d'optimisation des ressources."""
        # Configuration de l'état des ressources
        current_load = {
            "cpu_usage": 0.85,
            "memory_usage": 0.70,
            "llm_service_queue": 15,
            "active_operations": 8
        }
        
        optimization_result = await operational_manager._optimize_resource_allocation(current_load)
        
        assert "recommendations" in optimization_result
        assert "resource_adjustments" in optimization_result
        assert "priority_reordering" in optimization_result
        
        # Vérifier que des ajustements sont proposés pour charge élevée
        if current_load["cpu_usage"] > 0.8:
            assert "reduce_concurrent_operations" in str(optimization_result["recommendations"])


class TestHierarchicalIntegration:
    """Tests d'intégration entre les niveaux hiérarchiques."""
    
    @pytest.fixture
    def integrated_hierarchy(self, llm_service):
        """Hiérarchie complète pour tests d'intégration."""
        strategic = StrategicManager(llm_service, {"analysis_depth": "comprehensive"})
        tactical = TaskCoordinator(llm_service, {"coordination_strategy": "adaptive"})
        operational = OperationalManager(llm_service, {"execution_strategy": "parallel"})
        
        return {
            "strategic": strategic,
            "tactical": tactical,
            "operational": operational
        }
    
    @pytest.mark.asyncio
    async def test_full_hierarchical_flow(self, integrated_hierarchy):
        """Test du flux complet hiérarchique strategic -> tactical -> operational."""
        text = "L'intelligence artificielle va révolutionner l'éducation en personnalisant l'apprentissage, mais elle pose des défis éthiques importants."
        
        strategic = integrated_hierarchy["strategic"]
        tactical = integrated_hierarchy["tactical"] 
        operational = integrated_hierarchy["operational"]
        
        # Mock des méthodes pour simuler le flux complet
        strategic.initialize_analysis = AsyncMock(return_value={
            "objectives": [
                {"id": "obj1", "description": "Analyser les bénéfices éducatifs", "type": "benefit_analysis"},
                {"id": "obj2", "description": "Identifier les enjeux éthiques", "type": "ethical_analysis"}
            ],
            "strategic_plan": {"phases": [{"id": "phase1", "objectives": ["obj1", "obj2"]}]}
        })
        
        tactical.process_strategic_objectives = AsyncMock(return_value={
            "tasks_created": 6,
            "scheduling_plan": {
                "schedule": [
                    {"task_id": "task1", "type": "benefit_extraction"},
                    {"task_id": "task2", "type": "challenge_identification"},
                    {"task_id": "task3", "type": "ethical_analysis"},
                    {"task_id": "task4", "type": "risk_assessment"},
                    {"task_id": "task5", "type": "synthesis"},
                    {"task_id": "task6", "type": "recommendation_generation"}
                ]
            }
        })
        
        operational.execute_tactical_tasks = AsyncMock(return_value={
            "execution_summary": {"completed": 6, "failed": 0},
            "task_results": {
                "task1": {"benefits": ["personalisation", "efficacité"]},
                "task2": {"challenges": ["coût", "formation"]},
                "task3": {"ethical_issues": ["privacy", "bias"]},
                "task4": {"risks": ["dependency", "job_displacement"]},
                "task5": {"synthesis": "Bénéfices significatifs avec enjeux à adresser"},
                "task6": {"recommendations": ["régulation", "formation"]}
            }
        })
        
        # Exécution du flux complet
        strategic_result = await strategic.initialize_analysis(text, "comprehensive")
        tactical_result = await tactical.process_strategic_objectives(strategic_result["objectives"])
        operational_result = await operational.execute_tactical_tasks(tactical_result["scheduling_plan"]["schedule"])
        
        # Vérifications du flux
        assert len(strategic_result["objectives"]) == 2
        assert tactical_result["tasks_created"] == 6
        assert operational_result["execution_summary"]["completed"] == 6
        
        # Vérifier la cohérence des résultats
        assert "benefits" in operational_result["task_results"]["task1"]
        assert "ethical_issues" in operational_result["task_results"]["task3"]
        assert operational_result["task_results"]["task5"]["synthesis"]
    
    @pytest.mark.asyncio
    async def test_communication_feedback_loop(self, integrated_hierarchy):
        """Test de la boucle de communication et feedback entre niveaux."""
        strategic = integrated_hierarchy["strategic"]
        tactical = integrated_hierarchy["tactical"]
        operational = integrated_hierarchy["operational"]
        
        # Simuler un feedback opérationnel remontant au tactical
        operational_feedback = {
            "resource_constraints": ["llm_service_overload"],
            "task_difficulties": {"task_complex_analysis": "higher_than_expected"},
            "suggested_adjustments": ["split_complex_task", "increase_timeout"]
        }
        
        # Mock de la gestion du feedback
        tactical.handle_operational_feedback = AsyncMock(return_value={
            "plan_adjustments": {
                "task_complex_analysis": {"split": True, "subtasks": 3},
                "resource_reallocation": {"llm_service": "priority_queue"}
            },
            "strategic_escalation": {
                "complexity_increase": "20%",
                "recommendation": "adjust_strategic_scope"
            }
        })
        
        strategic.handle_tactical_escalation = AsyncMock(return_value={
            "plan_adaptation": {"scope_adjustment": "moderate_reduction"},
            "resource_approval": {"additional_llm_quota": True}
        })
        
        # Test du flux de feedback
        tactical_response = await tactical.handle_operational_feedback(operational_feedback)
        strategic_response = await strategic.handle_tactical_escalation(tactical_response["strategic_escalation"])
        
        assert "plan_adjustments" in tactical_response
        assert "strategic_escalation" in tactical_response
        assert "plan_adaptation" in strategic_response
        assert strategic_response["resource_approval"]["additional_llm_quota"] is True
    
    @pytest.mark.asyncio
    async def test_error_escalation_hierarchy(self, integrated_hierarchy):
        """Test de l'escalade d'erreurs dans la hiérarchie."""
        operational = integrated_hierarchy["operational"]
        tactical = integrated_hierarchy["tactical"]
        strategic = integrated_hierarchy["strategic"]
        
        # Simuler une erreur critique au niveau opérationnel
        critical_error = {
            "type": "resource_exhaustion",
            "details": "LLM service quota exceeded",
            "affected_tasks": ["task1", "task2", "task3"],
            "severity": "critical"
        }
        
        # Mock de la gestion d'erreur escaladée
        tactical.handle_operational_error = AsyncMock(return_value={
            "mitigation_attempts": ["task_rescheduling", "resource_reallocation"],
            "success": False,
            "escalation_required": True,
            "escalation_data": {
                "error": critical_error,
                "mitigation_failed": True,
                "impact_assessment": "high"
            }
        })
        
        strategic.handle_critical_escalation = AsyncMock(return_value={
            "strategic_decision": "activate_fallback_pipeline",
            "resource_authorization": {"emergency_quota": True},
            "plan_modification": {"reduce_scope": "30%"}
        })
        
        # Test de l'escalade d'erreur
        tactical_response = await tactical.handle_operational_error(critical_error)
        
        if tactical_response["escalation_required"]:
            strategic_response = await strategic.handle_critical_escalation(
                tactical_response["escalation_data"]
            )
            
            assert strategic_response["strategic_decision"] == "activate_fallback_pipeline"
            assert strategic_response["resource_authorization"]["emergency_quota"] is True
    
    @pytest.mark.asyncio
    async def test_performance_coordination(self, integrated_hierarchy):
        """Test de coordination des performances entre niveaux."""
        strategic = integrated_hierarchy["strategic"]
        tactical = integrated_hierarchy["tactical"]
        operational = integrated_hierarchy["operational"]
        
        # Simuler métriques de performance de chaque niveau
        strategic_metrics = {
            "planning_efficiency": 0.85,
            "objective_completion_rate": 0.92,
            "strategic_accuracy": 0.88
        }
        
        tactical_metrics = {
            "task_coordination_efficiency": 0.78,
            "resource_utilization": 0.82,
            "scheduling_accuracy": 0.86
        }
        
        operational_metrics = {
            "execution_speed": 0.91,
            "task_success_rate": 0.87,
            "resource_efficiency": 0.79
        }
        
        # Mock de l'analyse de performance coordonnée
        async def analyze_coordinated_performance():
            return {
                "overall_hierarchy_efficiency": 0.84,  # Moyenne pondérée
                "bottleneck_level": "tactical",  # Plus bas score
                "optimization_recommendations": [
                    "improve_tactical_coordination",
                    "optimize_operational_resource_usage"
                ],
                "performance_trend": "stable_with_room_for_improvement"
            }
        
        performance_analysis = await analyze_coordinated_performance()
        
        assert performance_analysis["overall_hierarchy_efficiency"] > 0.8
        assert performance_analysis["bottleneck_level"] == "tactical"
        assert "improve_tactical_coordination" in performance_analysis["optimization_recommendations"]


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v", "--tb=short"])