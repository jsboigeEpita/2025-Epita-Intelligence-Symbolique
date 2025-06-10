#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests pour le Comprehensive Workflow Processor
=============================================

Tests unitaires et d'intégration pour le processeur de workflow complet,
couvrant tous les modes d'exécution et configurations.

Date: 10/06/2025
Objectif: Validation complète du troisième script consolidé
"""

import os
import sys
import json
import asyncio
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Ajout du chemin du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configuration du logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestComprehensiveWorkflow")

# Import du module à tester
try:
    from scripts.consolidated.comprehensive_workflow_processor import (
        ComprehensiveWorkflowProcessor,
        WorkflowConfig,
        WorkflowResults,
        WorkflowMode,
        ProcessingEnvironment,
        ReportFormat,
        CorpusManager,
        PipelineEngine,
        ValidationSuite,
        TestOrchestrator,
        ResultsAggregator,
        parse_arguments,
        main_async
    )
    PROCESSOR_AVAILABLE = True
    logger.info("✅ Import du processeur de workflow réussi")
except ImportError as e:
    logger.error(f"❌ Erreur d'import: {e}")
    PROCESSOR_AVAILABLE = False

class TestWorkflowConfig(unittest.TestCase):
    """Tests pour la configuration du workflow."""
    
    def setUp(self):
        """Initialisation des tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """Nettoyage après les tests."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    def test_config_creation_default(self):
        """Test de création de configuration par défaut."""
        config = WorkflowConfig()
        
        self.assertEqual(config.mode, WorkflowMode.FULL)
        self.assertEqual(config.environment, ProcessingEnvironment.DEV)
        self.assertEqual(config.parallel_workers, 4)
        self.assertTrue(config.enable_monitoring)
        self.assertTrue(config.enable_decryption)
        self.assertEqual(len(config.corpus_files), 0)
        self.assertIsNotNone(config.encryption_passphrase)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    def test_config_creation_custom(self):
        """Test de création de configuration personnalisée."""
        config = WorkflowConfig(
            mode=WorkflowMode.TESTING_ONLY,
            environment=ProcessingEnvironment.PROD,
            parallel_workers=8,
            corpus_files=["test1.enc", "test2.enc"],
            output_dir=self.temp_dir
        )
        
        self.assertEqual(config.mode, WorkflowMode.TESTING_ONLY)
        self.assertEqual(config.environment, ProcessingEnvironment.PROD)
        self.assertEqual(config.parallel_workers, 8)
        self.assertEqual(len(config.corpus_files), 2)
        self.assertEqual(config.output_dir, self.temp_dir)
        self.assertTrue(config.output_dir.exists())
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    def test_config_validation(self):
        """Test de validation de configuration."""
        # Test avec répertoire de sortie inexistant
        non_existent_dir = self.temp_dir / "non_existent"
        config = WorkflowConfig(output_dir=non_existent_dir)
        
        # Le répertoire doit être créé automatiquement
        self.assertTrue(config.output_dir.exists())

class TestWorkflowResults(unittest.TestCase):
    """Tests pour les résultats du workflow."""
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    def test_results_initialization(self):
        """Test d'initialisation des résultats."""
        start_time = datetime.now()
        results = WorkflowResults(start_time=start_time)
        
        self.assertEqual(results.start_time, start_time)
        self.assertIsNone(results.end_time)
        self.assertIsNone(results.duration)
        self.assertEqual(results.status, "running")
        self.assertEqual(results.total_processed, 0)
        self.assertEqual(results.success_count, 0)
        self.assertEqual(results.error_count, 0)
        self.assertEqual(len(results.warnings), 0)
        self.assertEqual(len(results.errors), 0)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    def test_results_finalization(self):
        """Test de finalisation des résultats."""
        start_time = datetime.now()
        results = WorkflowResults(start_time=start_time)
        
        # Simulation de quelques données
        results.analysis_results = {"test1": "result1", "test2": "result2"}
        results.test_results = {"test_suite": "passed"}
        results.success_count = 2
        
        # Finalisation
        results.finalize("completed")
        
        self.assertIsNotNone(results.end_time)
        self.assertIsNotNone(results.duration)
        self.assertEqual(results.status, "completed")
        self.assertEqual(results.total_processed, 3)  # 2 analysis + 1 test

class TestCorpusManager(unittest.TestCase):
    """Tests pour le gestionnaire de corpus."""
    
    def setUp(self):
        """Initialisation des tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = WorkflowConfig(
            corpus_files=[],
            encryption_passphrase="test_passphrase",
            output_dir=self.temp_dir
        ) if PROCESSOR_AVAILABLE else None
    
    def tearDown(self):
        """Nettoyage après les tests."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_corpus_manager_initialization(self):
        """Test d'initialisation du gestionnaire de corpus."""
        manager = CorpusManager(self.config)
        
        self.assertEqual(manager.config, self.config)
        self.assertIsNotNone(manager.logger)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_load_corpus_no_files(self):
        """Test de chargement sans fichiers de corpus."""
        manager = CorpusManager(self.config)
        results = await manager.load_corpus_data()
        
        self.assertEqual(results["status"], "success")
        self.assertEqual(len(results["loaded_files"]), 0)
        self.assertEqual(len(results["errors"]), 0)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_load_corpus_nonexistent_file(self):
        """Test de chargement avec fichier inexistant."""
        self.config.corpus_files = ["nonexistent.enc"]
        manager = CorpusManager(self.config)
        results = await manager.load_corpus_data()
        
        self.assertEqual(results["status"], "success")
        self.assertEqual(len(results["loaded_files"]), 0)
        self.assertGreater(len(results["errors"]), 0)
        self.assertIn("Fichier corpus non trouvé", results["errors"][0])

class TestPipelineEngine(unittest.TestCase):
    """Tests pour le moteur de pipeline."""
    
    def setUp(self):
        """Initialisation des tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = WorkflowConfig(output_dir=self.temp_dir) if PROCESSOR_AVAILABLE else None
    
    def tearDown(self):
        """Nettoyage après les tests."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_pipeline_engine_initialization(self):
        """Test d'initialisation du moteur de pipeline."""
        engine = PipelineEngine(self.config)
        
        self.assertEqual(engine.config, self.config)
        self.assertIsNotNone(engine.logger)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_run_analysis_pipeline_empty_corpus(self):
        """Test d'exécution du pipeline avec corpus vide."""
        engine = PipelineEngine(self.config)
        corpus_data = {"loaded_files": []}
        
        results = await engine.run_analysis_pipeline(corpus_data)
        
        self.assertEqual(results["status"], "success")
        self.assertEqual(len(results["analyses"]), 0)
        self.assertIsInstance(results["errors"], list)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_run_analysis_pipeline_with_content(self):
        """Test d'exécution du pipeline avec contenu."""
        engine = PipelineEngine(self.config)
        corpus_data = {
            "loaded_files": [
                {
                    "file": "test.enc",
                    "definitions_count": 1,
                    "definitions": [
                        {"content": "Ceci est un texte de test pour l'analyse."}
                    ]
                }
            ]
        }
        
        # Mock des dépendances pour éviter les erreurs d'import
        with patch('scripts.consolidated.comprehensive_workflow_processor.UnifiedConfig') as mock_config, \
             patch('scripts.consolidated.comprehensive_workflow_processor.InformalAnalysisAgent') as mock_agent:
            
            # Configuration du mock agent
            mock_agent_instance = AsyncMock()
            mock_agent_instance.setup_agent_components.return_value = True
            mock_agent_instance.analyze.return_value = {
                "fallacies": [],
                "rhetoric_elements": [],
                "confidence": 0.8
            }
            mock_agent.return_value = mock_agent_instance
            
            results = await engine.run_analysis_pipeline(corpus_data)
            
            self.assertEqual(results["status"], "success")
            self.assertGreaterEqual(len(results["analyses"]), 0)

class TestValidationSuite(unittest.TestCase):
    """Tests pour la suite de validation."""
    
    def setUp(self):
        """Initialisation des tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = WorkflowConfig(
            output_dir=self.temp_dir,
            enable_api_tests=False,  # Désactiver les tests API par défaut
            enable_system_validation=False  # Désactiver les tests système par défaut
        ) if PROCESSOR_AVAILABLE else None
    
    def tearDown(self):
        """Nettoyage après les tests."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_validation_suite_initialization(self):
        """Test d'initialisation de la suite de validation."""
        suite = ValidationSuite(self.config)
        
        self.assertEqual(suite.config, self.config)
        self.assertIsNotNone(suite.logger)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_comprehensive_validation_minimal(self):
        """Test de validation comprehensive minimale."""
        suite = ValidationSuite(self.config)
        results = await suite.run_comprehensive_validation()
        
        self.assertEqual(results["status"], "success")
        self.assertIn("authenticity_check", results)
        self.assertIn("system_tests", results)
        self.assertIn("api_tests", results)
        self.assertIsInstance(results["errors"], list)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_authenticity_check(self):
        """Test de vérification d'authenticité."""
        suite = ValidationSuite(self.config)
        
        # Test avec module de détection disponible (mock)
        with patch('scripts.consolidated.comprehensive_workflow_processor.MockDetector') as mock_detector_class:
            mock_detector = Mock()
            mock_report = Mock()
            mock_report.authenticity_score = 0.9
            mock_report.total_mocks_detected = 2
            mock_report.critical_mocks = []
            mock_detector.scan_project.return_value = mock_report
            mock_detector_class.return_value = mock_detector
            
            with patch('scripts.consolidated.comprehensive_workflow_processor.AuthenticityReport'):
                results = await suite._run_authenticity_check()
                
                self.assertEqual(results["status"], "success")
                self.assertEqual(results["authenticity_score"], 0.9)
                self.assertEqual(results["total_mocks_detected"], 2)
                self.assertTrue(results["passed"])

class TestTestOrchestrator(unittest.TestCase):
    """Tests pour l'orchestrateur de tests."""
    
    def setUp(self):
        """Initialisation des tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = WorkflowConfig(
            output_dir=self.temp_dir,
            performance_iterations=2  # Réduire pour les tests
        ) if PROCESSOR_AVAILABLE else None
    
    def tearDown(self):
        """Nettoyage après les tests."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_orchestrator_initialization(self):
        """Test d'initialisation de l'orchestrateur."""
        orchestrator = TestOrchestrator(self.config)
        
        self.assertEqual(orchestrator.config, self.config)
        self.assertIsNotNone(orchestrator.logger)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_performance_tests(self):
        """Test d'exécution des tests de performance."""
        orchestrator = TestOrchestrator(self.config)
        
        # Mock des dépendances pour éviter les erreurs d'import
        with patch('scripts.consolidated.comprehensive_workflow_processor.UnifiedConfig'), \
             patch('scripts.consolidated.comprehensive_workflow_processor.InformalAnalysisAgent'):
            
            results = await orchestrator.run_performance_tests()
            
            self.assertEqual(results["status"], "success")
            self.assertEqual(results["iterations"], 2)
            self.assertIn("tests", results)
            self.assertIn("summary", results)
            self.assertIsInstance(results["errors"], list)

class TestResultsAggregator(unittest.TestCase):
    """Tests pour l'agrégateur de résultats."""
    
    def setUp(self):
        """Initialisation des tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = WorkflowConfig(
            output_dir=self.temp_dir,
            report_formats=[ReportFormat.JSON, ReportFormat.MARKDOWN]
        ) if PROCESSOR_AVAILABLE else None
    
    def tearDown(self):
        """Nettoyage après les tests."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_aggregator_initialization(self):
        """Test d'initialisation de l'agrégateur."""
        aggregator = ResultsAggregator(self.config)
        
        self.assertEqual(aggregator.config, self.config)
        self.assertIsNotNone(aggregator.logger)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_generate_comprehensive_report(self):
        """Test de génération de rapport complet."""
        aggregator = ResultsAggregator(self.config)
        
        # Création de résultats de test
        start_time = datetime.now()
        results = WorkflowResults(start_time=start_time)
        results.analysis_results = {"test_analysis": "completed"}
        results.success_count = 1
        results.finalize("completed")
        
        report_files = await aggregator.generate_comprehensive_report(results)
        
        self.assertIsInstance(report_files, dict)
        self.assertIn("json", report_files)
        self.assertIn("markdown", report_files)
        
        # Vérifier que les fichiers ont été créés
        for file_path in report_files.values():
            self.assertTrue(Path(file_path).exists())

class TestComprehensiveWorkflowProcessor(unittest.TestCase):
    """Tests pour le processeur principal."""
    
    def setUp(self):
        """Initialisation des tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = WorkflowConfig(
            mode=WorkflowMode.TESTING_ONLY,
            output_dir=self.temp_dir,
            enable_decryption=False,  # Désactiver pour simplifier les tests
            enable_api_tests=False,
            enable_system_validation=False,
            report_formats=[ReportFormat.JSON]
        ) if PROCESSOR_AVAILABLE else None
    
    def tearDown(self):
        """Nettoyage après les tests."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    def test_processor_initialization(self):
        """Test d'initialisation du processeur."""
        processor = ComprehensiveWorkflowProcessor(self.config)
        
        self.assertEqual(processor.config, self.config)
        self.assertIsNotNone(processor.corpus_manager)
        self.assertIsNotNone(processor.pipeline_engine)
        self.assertIsNotNone(processor.validation_suite)
        self.assertIsNotNone(processor.test_orchestrator)
        self.assertIsNotNone(processor.results_aggregator)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_run_comprehensive_workflow_testing_mode(self):
        """Test d'exécution du workflow en mode test."""
        processor = ComprehensiveWorkflowProcessor(self.config)
        
        # Mock des méthodes pour éviter les dépendances externes
        with patch.object(processor.validation_suite, 'run_comprehensive_validation') as mock_validation:
            mock_validation.return_value = {
                "status": "success",
                "authenticity_check": {"passed": True},
                "system_tests": {"passed": 2, "failed": 0},
                "api_tests": {"api_available": False},
                "errors": []
            }
            
            results = await processor.run_comprehensive_workflow()
            
            self.assertIsInstance(results, WorkflowResults)
            self.assertIn(results.status, ["completed", "completed_with_errors"])
            self.assertIsNotNone(results.end_time)
            self.assertIsNotNone(results.duration)

class TestArgumentParsing(unittest.TestCase):
    """Tests pour l'analyse des arguments CLI."""
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    def test_parse_arguments_default(self):
        """Test d'analyse des arguments par défaut."""
        config = parse_arguments([])
        
        self.assertEqual(config.mode, WorkflowMode.FULL)
        self.assertEqual(config.environment, ProcessingEnvironment.DEV)
        self.assertEqual(config.parallel_workers, 4)
        self.assertTrue(config.enable_monitoring)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    def test_parse_arguments_custom(self):
        """Test d'analyse des arguments personnalisés."""
        args = [
            '--mode', 'performance',
            '--environment', 'production',
            '--workers', '8',
            '--corpus', 'test1.enc',
            '--corpus', 'test2.enc',
            '--enable-api-tests',
            '--iterations', '5',
            '--format', 'json',
            '--format', 'markdown'
        ]
        
        config = parse_arguments(args)
        
        self.assertEqual(config.mode, WorkflowMode.PERFORMANCE)
        self.assertEqual(config.environment, ProcessingEnvironment.PROD)
        self.assertEqual(config.parallel_workers, 8)
        self.assertEqual(len(config.corpus_files), 2)
        self.assertTrue(config.enable_api_tests)
        self.assertEqual(config.performance_iterations, 5)
        self.assertEqual(len(config.report_formats), 2)

class TestIntegration(unittest.TestCase):
    """Tests d'intégration bout-en-bout."""
    
    def setUp(self):
        """Initialisation des tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Nettoyage après les tests."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(PROCESSOR_AVAILABLE, "Module processor non disponible")
    async def test_end_to_end_minimal_workflow(self):
        """Test d'intégration bout-en-bout minimal."""
        # Configuration minimale pour éviter les dépendances externes
        config = WorkflowConfig(
            mode=WorkflowMode.VALIDATION_ONLY,
            environment=ProcessingEnvironment.DEV,
            output_dir=self.temp_dir,
            enable_decryption=False,
            enable_api_tests=False,
            enable_system_validation=False,
            mock_detection=False,
            report_formats=[ReportFormat.JSON]
        )
        
        # Mock du main_async pour éviter les erreurs de dépendances
        with patch('scripts.consolidated.comprehensive_workflow_processor.ComprehensiveWorkflowProcessor') as mock_processor_class:
            mock_processor = Mock()
            mock_results = WorkflowResults(start_time=datetime.now())
            mock_results.finalize("completed")
            mock_processor.run_comprehensive_workflow.return_value = mock_results
            mock_processor_class.return_value = mock_processor
            
            exit_code = await main_async(config)
            
            self.assertEqual(exit_code, 0)
            mock_processor.run_comprehensive_workflow.assert_called_once()

# === RUNNER PRINCIPAL ===

def run_async_test(test_func):
    """Helper pour exécuter des tests asynchrones."""
    return asyncio.run(test_func())

def run_all_tests():
    """Exécute tous les tests."""
    logger.info("🧪 Démarrage des tests du Comprehensive Workflow Processor")
    
    if not PROCESSOR_AVAILABLE:
        logger.error("❌ Module processor non disponible - tests ignorés")
        return False
    
    # Créer la suite de tests
    test_suite = unittest.TestSuite()
    
    # Ajouter les classes de tests
    test_classes = [
        TestWorkflowConfig,
        TestWorkflowResults,
        TestCorpusManager,
        TestPipelineEngine,
        TestValidationSuite,
        TestTestOrchestrator,
        TestResultsAggregator,
        TestComprehensiveWorkflowProcessor,
        TestArgumentParsing,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Rapport final
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    
    logger.info("="*70)
    logger.info("📊 RÉSULTATS DES TESTS")
    logger.info("="*70)
    logger.info(f"Total des tests: {total_tests}")
    logger.info(f"✅ Réussis: {total_tests - failures - errors}")
    logger.info(f"❌ Échecs: {failures}")
    logger.info(f"💥 Erreurs: {errors}")
    logger.info(f"⏭️ Ignorés: {skipped}")
    logger.info(f"📈 Taux de réussite: {((total_tests - failures - errors) / max(total_tests, 1) * 100):.1f}%")
    logger.info("="*70)
    
    if failures > 0:
        logger.info("❌ ÉCHECS:")
        for test, traceback in result.failures:
            logger.info(f"  • {test}")
    
    if errors > 0:
        logger.info("💥 ERREURS:")
        for test, traceback in result.errors:
            logger.info(f"  • {test}")
    
    return failures == 0 and errors == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)