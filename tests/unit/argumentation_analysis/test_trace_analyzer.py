import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

"""
Tests unitaires pour TraceAnalyzer.

Ce module teste toutes les fonctionnalités de l'analyseur de traces,
y compris l'extraction de métadonnées, l'analyse des flows d'orchestration,
le suivi d'évolution d'état et la génération de rapports.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Import du module à tester
from argumentation_analysis.reporting.trace_analyzer import (
    TraceAnalyzer,
    ExtractMetadata,
    OrchestrationFlow,
    StateEvolution,
    QueryResults,
    InformalExploration,
    analyze_latest_traces,
    quick_metadata_extract,
)


class TestDataClasses:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-5-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests pour les dataclasses utilisées par TraceAnalyzer."""

    def test_extract_metadata(self):
        """Test de la dataclass ExtractMetadata."""
        metadata = ExtractMetadata(
            source_file="test_file.txt",
            content_length=1500,
            content_type="encrypted_corpus",
            complexity_level="medium",
            analysis_timestamp="2023-01-01T12:00:00",
            encoding_info="utf-8",
            source_origin="political_speech",
        )

        assert metadata.source_file == "test_file.txt"
        assert metadata.content_length == 1500
        assert metadata.content_type == "encrypted_corpus"
        assert metadata.complexity_level == "medium"
        assert metadata.analysis_timestamp == "2023-01-01T12:00:00"
        assert metadata.encoding_info == "utf-8"
        assert metadata.source_origin == "political_speech"

    def test_orchestration_flow(self):
        """Test de la dataclass OrchestrationFlow."""
        flow = OrchestrationFlow(
            agents_called=[
                "SynthesisAgent",
                "LogicAgent_propositional",
                "InformalAgent",
            ],
            sequence_order=[("Step_1", "Initialization"), ("Step_2", "Analysis")],
            coordination_messages=["Orchestration started", "Agents synchronized"],
            total_execution_time=250.5,
            success_status="success",
        )

        assert len(flow.agents_called) == 3
        assert "SynthesisAgent" in flow.agents_called
        assert len(flow.sequence_order) == 2
        assert flow.sequence_order[0] == ("Step_1", "Initialization")
        assert "Orchestration started" in flow.coordination_messages
        assert flow.total_execution_time == 250.5
        assert flow.success_status == "success"

    def test_state_evolution(self):
        """Test de la dataclass StateEvolution."""
        evolution = StateEvolution(
            shared_state_changes=[{"type": "update", "description": "State updated"}],
            belief_state_construction=[
                {"phase": "construction", "details": "Building belief state"}
            ],
            progressive_enrichment=["Analysis PL simulée", "Analysis FOL simulée"],
            state_transitions=[
                ("Initialisation", "Configuration"),
                ("Analyse", "Synthèse"),
            ],
        )

        assert len(evolution.shared_state_changes) == 1
        assert evolution.shared_state_changes[0]["type"] == "update"
        assert len(evolution.belief_state_construction) == 1
        assert len(evolution.progressive_enrichment) == 2
        assert len(evolution.state_transitions) == 2
        assert evolution.state_transitions[0] == ("Initialisation", "Configuration")

    def test_query_results(self):
        """Test de la dataclass QueryResults."""
        results = QueryResults(
            formalizations=[{"formula": "p => q", "type": "extracted_formula"}],
            inference_queries=["p", "q"],
            validation_results=[
                {"query": "p", "result": "ACCEPTED", "confidence": 0.9}
            ],
            logic_types_used=["propositional", "modal"],
            knowledge_base_status="consistent",
        )

        assert len(results.formalizations) == 1
        assert results.formalizations[0]["formula"] == "p => q"
        assert "p" in results.inference_queries
        assert len(results.validation_results) == 1
        assert results.validation_results[0]["confidence"] == 0.9
        assert "propositional" in results.logic_types_used
        assert results.knowledge_base_status == "consistent"

    def test_informal_exploration(self):
        """Test de la dataclass InformalExploration."""
        exploration = InformalExploration(
            taxonomy_path=["Analyse générale", "Catégorisation", "Analyse spécifique"],
            fallacy_detection=[
                {"type": "ad_hominem", "confidence": 0.8, "severity": "high"}
            ],
            rhetorical_patterns=["structure argumentative", "pattern émotionnel"],
            severity_analysis=[{"severity_level": "high", "count": 2}],
        )

        assert len(exploration.taxonomy_path) == 3
        assert "Analyse générale" in exploration.taxonomy_path
        assert len(exploration.fallacy_detection) == 1
        assert exploration.fallacy_detection[0]["type"] == "ad_hominem"
        assert "structure argumentative" in exploration.rhetorical_patterns
        assert exploration.severity_analysis[0]["count"] == 2


class TestTraceAnalyzer:
    """Tests pour la classe TraceAnalyzer."""

    @pytest.fixture
    def trace_analyzer(self, tmpdir):
        """Fixture pour une instance de TraceAnalyzer utilisant un répertoire temporaire."""
        return TraceAnalyzer(str(tmpdir))

    @pytest.fixture
    def sample_conversation_log(self):
        """Fixture avec un exemple de log de conversation."""
        return (
            "[INFO] 2023-01-01 12:00:00 - Début de l'analyse\n"
            "[INFO] Fichier source analysé : /path/to/source.txt\n"
            "[INFO] Longueur du texte: 1500 caractères\n"
            "[INFO] Horodatage de l'analyse : 2023-01-01T12:00:00\n"
            "[INFO] SynthesisAgent - Orchestration des analyses\n"
            "[INFO] [ETAPE 1/3] Démarrage des analyses logiques formelles\n"
            "[INFO] Analyse PL simulée: Structure logique basique détectée\n"
            "[INFO] [ETAPE 2/3] Démarrage de l'analyse informelle, terminée en 120.5ms\n"
            "[INFO] [ETAPE 3/3] Unification des résultats\n"
            "[INFO] Analyse terminée avec succès en 250.5ms\n"
        )

    @pytest.fixture
    def sample_report_json(self):
        """Fixture avec un exemple de rapport JSON."""
        return {
            "statistics": {
                "text_length": 1500,
                "formulas_count": 3,
                "fallacies_count": 2,
            },
            "metadata": {
                "timestamp": "2023-01-01T12:00:00",
                "source_type": "encrypted_corpus",
            },
            "formal_analysis": {
                "logic_types": ["propositional", "modal"],
                "knowledge_base": {
                    "status": "consistent",
                    "formulas": ["p => q", "[]p"],
                },
                "inference_results": {
                    "queries": ["p", "q"],
                    "results": [
                        {"query": "p", "result": "ACCEPTED", "confidence": 0.9}
                    ],
                },
            },
            "informal_analysis": {
                "fallacies_detected": [
                    {"type": "ad_hominem", "confidence": 0.8, "severity": "high"}
                ],
                "severity_distribution": {"high": 1, "medium": 0, "low": 0},
            },
        }

    def test_init_trace_analyzer(self):
        """Test l'initialisation du TraceAnalyzer."""
        analyzer = TraceAnalyzer("./custom_logs")

        assert analyzer.logs_directory == "./custom_logs"
        assert analyzer.conversation_log_file is None
        assert analyzer.report_json_file is None
        assert analyzer.raw_conversation_data is None
        assert analyzer.raw_report_data is None

    def test_init_trace_analyzer_default_directory(self):
        """Test l'initialisation avec répertoire par défaut."""
        analyzer = TraceAnalyzer()

        assert analyzer.logs_directory == "./logs"

    def test_load_traces_success(
        self, trace_analyzer, sample_conversation_log, sample_report_json
    ):
        """Test le chargement réussi des traces."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer des fichiers de test
            conv_file = os.path.join(temp_dir, "conversation.log")
            report_file = os.path.join(temp_dir, "report.json")

            with open(conv_file, "w", encoding="utf-8") as f:
                f.write(sample_conversation_log)

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(sample_report_json, f)

            # Tester le chargement
            success = trace_analyzer.load_traces(conv_file, report_file)

            assert success == True
            assert trace_analyzer.raw_conversation_data == sample_conversation_log
            assert trace_analyzer.raw_report_data == sample_report_json
            assert trace_analyzer.conversation_log_file == conv_file
            assert trace_analyzer.report_json_file == report_file

    def test_load_traces_partial_success(self, trace_analyzer, sample_conversation_log):
        """Test le chargement avec seulement un fichier disponible."""
        with tempfile.TemporaryDirectory() as temp_dir:
            conv_file = os.path.join(temp_dir, "conversation.log")

            with open(conv_file, "w", encoding="utf-8") as f:
                f.write(sample_conversation_log)

            # Fichier JSON inexistant
            report_file = os.path.join(temp_dir, "nonexistent.json")

            trace_analyzer.logs_directory = temp_dir
            success = trace_analyzer.load_traces(conv_file, report_file)

            assert success is True  # Au moins un fichier chargé
            assert trace_analyzer.raw_conversation_data == sample_conversation_log
            assert trace_analyzer.raw_report_data is None

    def test_load_traces_no_files(self, trace_analyzer):
        """Test le chargement sans fichiers disponibles."""
        success = trace_analyzer.load_traces(
            "/nonexistent/path", "/another/nonexistent/path"
        )

        assert success == False
        assert trace_analyzer.raw_conversation_data is None
        assert trace_analyzer.raw_report_data is None

    def test_load_traces_auto_detection(self, trace_analyzer):
        """Test la détection automatique des fichiers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_analyzer.logs_directory = temp_dir

            # Créer des fichiers de test avec des noms par défaut
            log_file_path = os.path.join(temp_dir, "test_conversation.log")
            json_file_path = os.path.join(temp_dir, "test_report.json")

            with open(log_file_path, "w") as f:
                f.write("log data")
            with open(json_file_path, "w") as f:
                json.dump({"key": "value"}, f)

            # Patcher os.listdir pour retourner les fichiers que nous avons créés
            with patch(
                "os.listdir", return_value=["test_conversation.log", "test_report.json"]
            ):
                success = trace_analyzer.load_traces()

                assert success is True
                assert trace_analyzer.raw_conversation_data == "log data"
                assert trace_analyzer.raw_report_data == {"key": "value"}
                assert trace_analyzer.conversation_log_file == log_file_path
                assert trace_analyzer.report_json_file == json_file_path

    def test_load_traces_exception_handling(self, trace_analyzer):
        """Test la gestion d'exception lors du chargement."""
        with patch("builtins.open", side_effect=Exception("File error")):
            success = trace_analyzer.load_traces()

            assert success == False

    def test_extract_metadata_from_conversation(
        self, trace_analyzer, sample_conversation_log
    ):
        """Test l'extraction de métadonnées depuis le log de conversation."""
        trace_analyzer.raw_conversation_data = sample_conversation_log

        metadata = trace_analyzer.extract_metadata()

        assert metadata.source_file == "/path/to/source.txt"
        assert metadata.content_length == 1500
        assert metadata.analysis_timestamp == "2023-01-01T12:00:00"
        assert metadata.complexity_level == "medium"  # 1500 est 'medium' pas 'complex'
        assert metadata.content_type == "encrypted_corpus"

    def test_extract_metadata_from_json(self, trace_analyzer, sample_report_json):
        """Test l'extraction de métadonnées depuis le rapport JSON."""
        trace_analyzer.raw_report_data = sample_report_json

        metadata = trace_analyzer.extract_metadata()

        assert metadata.content_length == 1500
        assert metadata.analysis_timestamp == "2023-01-01T12:00:00"
        assert metadata.source_origin == "encrypted_corpus"
        assert metadata.complexity_level == "medium"  # 1500 chars

    def test_extract_metadata_combined_sources(
        self, trace_analyzer, sample_conversation_log, sample_report_json
    ):
        """Test l'extraction avec sources combinées (priorité au JSON)."""
        trace_analyzer.raw_conversation_data = sample_conversation_log
        trace_analyzer.raw_report_data = sample_report_json

        metadata = trace_analyzer.extract_metadata()

        # Le JSON devrait avoir priorité pour content_length
        assert metadata.content_length == 1500  # Du JSON
        assert metadata.source_file == "/path/to/source.txt"  # Du log
        assert metadata.source_origin == "encrypted_corpus"  # Du JSON

    def test_extract_metadata_complexity_levels(self, trace_analyzer):
        """Test la déduction des niveaux de complexité."""
        # Test simple (<500 chars)
        trace_analyzer.raw_conversation_data = "Longueur du texte: 400 caractères"
        metadata = trace_analyzer.extract_metadata()
        assert metadata.complexity_level == "simple"

        # Test medium (500-2000 chars)
        trace_analyzer.raw_conversation_data = "Longueur du texte: 1000 caractères"
        metadata = trace_analyzer.extract_metadata()
        assert metadata.complexity_level == "medium"

        # Test complex (>2000 chars)
        trace_analyzer.raw_conversation_data = "Longueur du texte: 3000 caractères"
        metadata = trace_analyzer.extract_metadata()
        assert metadata.complexity_level == "complex"

    def test_extract_metadata_content_types(self, trace_analyzer):
        """Test la déduction des types de contenu."""
        # Test fallback text
        trace_analyzer.raw_conversation_data = (
            "Fichier source analysé : fallback_text.txt"
        )
        metadata = trace_analyzer.extract_metadata()
        assert metadata.content_type == "fallback_text"

        # Test encrypted corpus
        trace_analyzer.raw_conversation_data = (
            "Fichier source analysé : corpus_data.txt"
        )
        metadata = trace_analyzer.extract_metadata()
        assert metadata.content_type == "encrypted_corpus"

    def test_analyze_orchestration_flow(self, trace_analyzer, sample_conversation_log):
        """Test l'analyse du flow d'orchestration."""
        trace_analyzer.raw_conversation_data = sample_conversation_log

        flow = trace_analyzer.analyze_orchestration_flow()

        assert "SynthesisAgent" in flow.agents_called
        assert len(flow.sequence_order) >= 1
        assert any(
            "Démarrage des analyses logiques" in step[1] for step in flow.sequence_order
        )
        assert flow.total_execution_time == 250.5
        assert flow.success_status == "success"
        assert "Orchestration des analyses" in " ".join(flow.coordination_messages)

    def test_analyze_orchestration_flow_agents_detection(self, trace_analyzer):
        """Test la détection des agents dans les logs."""
        log_with_agents = """
        [INFO] SynthesisAgent initialized
        [INFO] a lancé LogicAgent_propositional
        [INFO] agent logique: modal processing
        [INFO] ExtractAgent completed
        [INFO] InformalAgent analyzing
        """
        trace_analyzer.raw_conversation_data = log_with_agents

        flow = trace_analyzer.analyze_orchestration_flow()

        expected_agents = [
            "SynthesisAgent",
            "LogicAgent_propositional",
            "LogicAgent_modal",
            "ExtractAgent",
            "InformalAgent",
        ]
        assert set(expected_agents) == set(flow.agents_called)

    def test_analyze_orchestration_flow_status_detection(self, trace_analyzer):
        """Test la détection du statut d'exécution."""
        # Test succès
        trace_analyzer.raw_conversation_data = "analyse terminée avec succès"
        flow = trace_analyzer.analyze_orchestration_flow()
        assert flow.success_status == "success"

        # Test échec
        trace_analyzer.raw_conversation_data = "une erreur est survenue"
        flow = trace_analyzer.analyze_orchestration_flow()
        assert flow.success_status == "partial_failure"

        # Test neutre
        trace_analyzer.raw_conversation_data = "processus terminé"
        flow = trace_analyzer.analyze_orchestration_flow()
        assert flow.success_status == "completed"

    def test_track_state_evolution(self, trace_analyzer):
        """Test le suivi de l'évolution d'état."""
        log_with_states = """
        [INFO] Début du traitement
        [INFO] Shared state initialized
        [INFO] État partagé mis à jour
        [INFO] Belief state construction started
        [INFO] Construction progressive terminée
        [INFO] Enrichissement des données
        [INFO] Évolution vers phase suivante
        [INFO] Traitement Fin
        """
        trace_analyzer.raw_conversation_data = log_with_states

        evolution = trace_analyzer.track_state_evolution()

        assert len(evolution.shared_state_changes) > 0
        assert len(evolution.belief_state_construction) > 0
        assert len(evolution.belief_state_construction) > 0

        # Vérifier les transitions d'état détectées
        assert len(evolution.state_transitions) > 0, "Aucune transition d'état détectée"

    def test_track_state_evolution_enrichment_patterns(self, trace_analyzer):
        """Test la détection des patterns d'enrichissement."""
        log_with_enrichment = """
        [INFO] Analyse PL simulée
        [INFO] Simulation FOL
        [INFO] Démarrage de l'analyse modale
        """
        trace_analyzer.raw_conversation_data = log_with_enrichment

        evolution = trace_analyzer.track_state_evolution()

        enrichments = evolution.progressive_enrichment

        # We need to check for the exact match now
        assert "Analyse PL simulée" in enrichments
        assert "Simulation FOL" in enrichments
        assert "Démarrage de l'analyse modale" in enrichments

    def test_extract_query_results_from_json(self, trace_analyzer, sample_report_json):
        """Test l'extraction des résultats de requêtes depuis JSON."""
        trace_analyzer.raw_report_data = sample_report_json

        results = trace_analyzer.extract_query_results()

        assert "propositional" in results.logic_types_used
        assert "modal" in results.logic_types_used
        assert results.knowledge_base_status == "consistent"
        assert len(results.formalizations) >= 1
        assert "p => q" in [f["formula"] for f in results.formalizations]
        assert "p" in results.inference_queries
        assert len(results.validation_results) >= 1
        assert results.validation_results[0]["confidence"] == 0.9

    def test_extract_query_results_from_conversation(self, trace_analyzer):
        """Test l'extraction des résultats depuis le log de conversation."""
        log_with_queries = """
        [INFO] Utilisation de la logique propositionnelle
        [INFO] Création de la KB : succès
        [INFO] Requête générée: p => q
        [INFO] Inférence exécutée: résultat positif
        [INFO] Validation effectuée avec succès
        """
        trace_analyzer.raw_conversation_data = log_with_queries

        results = trace_analyzer.extract_query_results()

        assert "propositionnelle" in results.logic_types_used
        assert results.knowledge_base_status == "succès"
        assert len(results.inference_queries) > 0

    def test_analyze_informal_exploration_from_json(
        self, trace_analyzer, sample_report_json
    ):
        """Test l'analyse de l'exploration informelle depuis JSON."""
        trace_analyzer.raw_report_data = sample_report_json

        exploration = trace_analyzer.analyze_informal_exploration()

        assert len(exploration.fallacy_detection) >= 1
        fallacy = exploration.fallacy_detection[0]
        assert fallacy["type"] == "ad_hominem"
        assert fallacy["confidence"] == 0.8
        assert fallacy["severity"] == "high"

        assert len(exploration.severity_analysis) >= 1
        severity = exploration.severity_analysis[0]
        assert severity["severity_level"] == "high"
        assert severity["count"] == 1

    def test_analyze_informal_exploration_from_conversation(self, trace_analyzer):
        """Test l'analyse de l'exploration depuis le log de conversation."""
        log_with_informal = """
        [INFO] Analyse générale démarrée
        [INFO] Catégorisation des éléments
        [INFO] Analyse spécifique en cours
        [INFO] Structure argumentative détectée
        [INFO] Pattern émotionnel identifié
        [INFO] 3 sophismes détectés
        """
        trace_analyzer.raw_conversation_data = log_with_informal

        exploration = trace_analyzer.analyze_informal_exploration()

        expected_taxonomy = ["Analyse générale", "Catégorisation", "Analyse spécifique"]
        for step in expected_taxonomy:
            assert step in exploration.taxonomy_path

        assert any(
            "structure argumentative" in p.lower()
            for p in exploration.rhetorical_patterns
        )

        # Vérifier la détection de sophismes
        assert len(exploration.fallacy_detection) > 0
        assert exploration.fallacy_detection[0]["total_detected"] == 3

    def test_generate_comprehensive_report(
        self, trace_analyzer, sample_conversation_log, sample_report_json
    ):
        """Test la génération de rapport complet."""
        trace_analyzer.raw_conversation_data = sample_conversation_log
        trace_analyzer.raw_report_data = sample_report_json

        report = trace_analyzer.generate_comprehensive_report()

        # Vérifier la structure du rapport
        assert "RAPPORT DE SYNTHÈSE DES TRACES D'EXÉCUTION" in report
        assert "MÉTADONNÉES DE L'EXTRAIT ANALYSÉ" in report
        assert "FLOW D'ORCHESTRATION" in report
        assert "ÉVOLUTION DES ÉTATS" in report
        assert "REQUÊTES ET INFÉRENCES" in report
        assert "EXPLORATION TAXONOMIQUE INFORMELLE" in report
        assert "SYNTHÈSE ET CONCLUSIONS" in report

        # Vérifier que les données sont incluses
        assert "1500 caractères" in report
        assert "250.5" in report
        assert "SynthesisAgent" in report
        assert "propositional" in report or "modal" in report

    def test_generate_comprehensive_report_sections(
        self, trace_analyzer, sample_conversation_log, sample_report_json
    ):
        """Test des sections spécifiques du rapport."""
        trace_analyzer.raw_conversation_data = sample_conversation_log
        trace_analyzer.raw_report_data = sample_report_json

        report = trace_analyzer.generate_comprehensive_report()

        # Section métadonnées
        assert "Fichier source:" in report
        assert "Longueur du contenu:" in report
        assert "Niveau de complexité:" in report

        # Section orchestration
        assert "Statut d'exécution:" in report
        assert "Temps d'exécution total:" in report
        assert "Agents impliqués:" in report

        # Section requêtes
        assert "Types de logique utilisés:" in report
        assert "Statut base de connaissances:" in report

        # Section conclusions
        assert "Richesse des traces:" in report
        assert "Évaluation globale:" in report
        assert "Recommandations pour amélioration:" in report

    def test_generate_comprehensive_report_recommendations(self, trace_analyzer):
        """Test la génération de recommandations."""
        # Log minimal pour déclencher des recommandations
        minimal_log = "[INFO] Analyse terminée"
        trace_analyzer.raw_conversation_data = minimal_log

        # JSON minimal
        minimal_json = {
            "formal_analysis": {"logic_types": []},
            "informal_analysis": {"fallacies_detected": []},
        }
        trace_analyzer.raw_report_data = minimal_json

        report = trace_analyzer.generate_comprehensive_report()

        # Vérifier que des recommandations sont générées
        assert "Recommandations pour amélioration:" in report
        recommendations_section = report.split("Recommandations pour amélioration:")[1]

        # Devrait contenir au moins une recommandation
        assert "- " in recommendations_section

    def test_generate_comprehensive_report_error_handling(self, trace_analyzer):
        """Test la gestion d'erreur lors de la génération de rapport."""
        # Pas de données chargées
        with patch.object(
            trace_analyzer, "extract_metadata", side_effect=Exception("Test error")
        ):
            report = trace_analyzer.generate_comprehensive_report()

            assert "Erreur lors de la génération du rapport" in report
            assert "Test error" in report


class TestUtilityFunctions:
    """Tests pour les fonctions utilitaires."""

    @pytest.fixture
    def mock_analyzer_class(self, mocker):
        """Fixture pour mocker la classe TraceAnalyzer."""
        return mocker.patch(
            "argumentation_analysis.reporting.trace_analyzer.TraceAnalyzer"
        )

    def test_analyze_latest_traces_success(self, mock_analyzer_class):
        """Test de l'analyse des dernières traces."""
        # Mock de l'instance d'analyzer
        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.load_traces.return_value = True
        mock_analyzer.generate_comprehensive_report.return_value = "Test report"

        result = analyze_latest_traces("./test_logs")

        assert result == "Test report"
        mock_analyzer_class.assert_called_once_with("./test_logs")
        mock_analyzer.load_traces.assert_called()
        mock_analyzer.generate_comprehensive_report.assert_called()

    def test_analyze_latest_traces_failure(self, mock_analyzer_class):
        """Test de l'analyse avec échec de chargement."""
        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.load_traces.return_value = False

        result = analyze_latest_traces("./test_logs")

        assert result == "Erreur: Impossible de charger les traces"
        mock_analyzer.generate_comprehensive_report.assert_not_called()

    def test_quick_metadata_extract(self, mock_analyzer_class):
        """Test de l'extraction rapide de métadonnées."""
        mock_metadata = ExtractMetadata(
            source_file="test.txt",
            content_length=1000,
            content_type="test",
            complexity_level="medium",
            analysis_timestamp="2023-01-01T12:00:00",
        )

        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.extract_metadata.return_value = mock_metadata

        result = quick_metadata_extract("./test_logs")

        assert result == mock_metadata
        mock_analyzer_class.assert_called_once_with("./test_logs")
        mock_analyzer.load_traces.assert_called()
        mock_analyzer.extract_metadata.assert_called()


class TestTraceAnalyzerIntegration:
    """Tests d'intégration pour TraceAnalyzer."""

    def test_full_analysis_workflow(self):
        """Test du workflow complet d'analyse de traces."""
        # Créer des données de test complètes
        conversation_log = """
        [INFO] 2023-01-01 12:00:00 - Début de l'analyse rhétorique
        [INFO] Fichier source analysé : /corpus/political_speech_001.txt
        [INFO] Longueur du texte: 2500 caractères
        [INFO] Horodatage de l'analyse : 2023-01-01T12:00:00
        [INFO] SynthesisAgent - Orchestration des analyses formelles et informelles
        [INFO] [ETAPE 1/4] Chargement des sources
        [INFO] [ETAPE 2/4] Démarrage des analyses logiques formelles
        [INFO] LogicAgent_propositional - Analyse PL simulée
        [INFO] LogicAgent_first_order - Analyse FOL simulée
        [INFO] LogicAgent_modal - Analyse ML simulée
        [INFO] [ETAPE 3/4] Démarrage de l'analyse informelle
        [INFO] InformalAgent - Analyse rhétorique simulée
        [INFO] Détection de sophismes: 2 sophismes identifiés
        [INFO] [ETAPE 4/4] Unification des résultats d'analyses
        [INFO] Orchestration des analyses terminée
        [INFO] analyse terminée avec succès. Temps total: 425.8ms.
        [INFO] Shared state updated: belief_state_enriched
        [INFO] Évolution vers phase de rapport
        """

        report_json = {
            "statistics": {
                "text_length": 2500,
                "formulas_count": 5,
                "fallacies_count": 2,
            },
            "metadata": {
                "timestamp": "2023-01-01T12:00:00",
                "source_type": "encrypted_corpus",
            },
            "formal_analysis": {
                "logic_types": ["propositional", "first_order", "modal"],
                "knowledge_base": {
                    "status": "consistent",
                    "formulas": ["p => q", "[]p", "forall x P(x)", "p && q", "<>r"],
                },
                "inference_results": {
                    "queries": ["p", "q", "[]p", "forall x P(x)"],
                    "results": [
                        {"query": "p", "result": "ACCEPTED", "confidence": 0.95},
                        {"query": "[]p", "result": "ACCEPTED", "confidence": 0.88},
                        {
                            "query": "forall x P(x)",
                            "result": "REJECTED",
                            "confidence": 0.75,
                        },
                    ],
                },
            },
            "informal_analysis": {
                "fallacies_detected": [
                    {
                        "type": "ad_hominem",
                        "confidence": 0.85,
                        "location": "paragraph 2",
                        "severity": "high",
                    },
                    {
                        "type": "strawman",
                        "confidence": 0.72,
                        "location": "paragraph 4",
                        "severity": "medium",
                    },
                ],
                "severity_distribution": {"high": 1, "medium": 1, "low": 0},
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer les fichiers de test
            conv_file = os.path.join(temp_dir, "conversation.log")
            report_file = os.path.join(temp_dir, "report.json")

            with open(conv_file, "w", encoding="utf-8") as f:
                f.write(conversation_log)

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_json, f)

            # Analyser avec TraceAnalyzer
            analyzer = TraceAnalyzer(temp_dir)
            success = analyzer.load_traces(conv_file, report_file)

            assert success == True

            # Test de toutes les méthodes d'extraction
            metadata = analyzer.extract_metadata()
            assert metadata.content_length == 2500
            assert metadata.complexity_level == "complex"
            assert metadata.source_file == "/corpus/political_speech_001.txt"

            orchestration = analyzer.analyze_orchestration_flow()
            assert "SynthesisAgent" in orchestration.agents_called
            assert (
                len(orchestration.agents_called) >= 3
            )  # SynthesisAgent, LogicAgent, InformalAgent
            assert (
                orchestration.total_execution_time == 425.8
            ), "Le temps d'exécution total est incorrect"
            assert orchestration.success_status == "success"

            state_evolution = analyzer.track_state_evolution()
            assert len(state_evolution.progressive_enrichment) > 0
            assert len(state_evolution.state_transitions) > 0

            query_results = analyzer.extract_query_results()
            assert len(query_results.logic_types_used) == 3
            assert query_results.knowledge_base_status == "consistent"
            assert len(query_results.validation_results) == 3

            informal_exploration = analyzer.analyze_informal_exploration()
            assert len(informal_exploration.fallacy_detection) == 2
            assert len(informal_exploration.severity_analysis) >= 1

            # Test du rapport complet
            full_report = analyzer.generate_comprehensive_report()

            # Vérifications du contenu du rapport
            assert "2500 caractères" in full_report
            assert "425.8 ms" in full_report
            assert "ad_hominem" in full_report
            assert (
                "propositional" in full_report
                or "first_order" in full_report
                or "modal" in full_report
            )
            assert "✅" in full_report  # Statut de succès
            assert len(full_report.split("\n")) > 50  # Rapport substantiel

    def test_edge_cases_and_robustness(self):
        """Test de la robustesse avec des cas limites."""
        analyzer = TraceAnalyzer()

        # Test avec données vides
        analyzer.raw_conversation_data = ""
        analyzer.raw_report_data = {}

        # Toutes les méthodes doivent fonctionner sans erreur
        metadata = analyzer.extract_metadata()
        assert metadata.content_length == 0
        assert metadata.complexity_level == "unknown"

        orchestration = analyzer.analyze_orchestration_flow()
        assert len(orchestration.agents_called) == 0
        assert orchestration.total_execution_time == 0.0

        state_evolution = analyzer.track_state_evolution()
        assert len(state_evolution.shared_state_changes) == 0

        query_results = analyzer.extract_query_results()
        assert len(query_results.logic_types_used) == 0

        informal_exploration = analyzer.analyze_informal_exploration()
        assert len(informal_exploration.fallacy_detection) == 0

        # Le rapport doit toujours être générés même avec des données vides
        report = analyzer.generate_comprehensive_report()
        assert "RAPPORT DE SYNTHÈSE" in report
        assert "Recommandations pour amélioration:" in report

    def test_large_data_handling(self):
        """Test de la gestion de données volumineuses."""
        # Créer des logs volumineux
        large_log = "\n".join(
            [f"[INFO] Log line {i} with some content" for i in range(1000)]
        )

        large_json = {
            "formal_analysis": {
                "logic_types": ["propositional"] * 10,
                "knowledge_base": {"formulas": [f"formula_{i}" for i in range(100)]},
                "inference_results": {
                    "results": [
                        {"query": f"q_{i}", "result": "ACCEPTED"} for i in range(50)
                    ]
                },
            },
            "informal_analysis": {
                "fallacies_detected": [{"type": f"fallacy_{i}"} for i in range(20)]
            },
        }

        analyzer = TraceAnalyzer()
        analyzer.raw_conversation_data = large_log
        analyzer.raw_report_data = large_json

        # Test que l'analyse fonctionne avec des données volumineuses
        report = analyzer.generate_comprehensive_report()

        assert len(report) > 1000  # Rapport substantiel
        assert "RAPPORT DE SYNTHÈSE" in report
        assert "100" in report  # Nombre de formules
        assert "20" in report  # Nombre de sophismes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
