#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Workflow Processor - Script Consolidé #3
=====================================================

Processeur de workflows complets pour l'analyse rhétorique avec :
- Orchestration bout-en-bout : déchiffrement → analyse → validation → rapport
- Tests intégrés et validation système complète
- Support batch pour traitement de volumes importants
- Pipeline parallélisé avec optimisation des performances
- Validation système (tests système et API) et monitoring avancé

Architecture consolidée de 6 scripts sources majeurs :
- run_full_python_analysis_workflow.py (workflow + déchiffrement)
- run_all_new_component_tests.py (orchestrateur de tests)
- test_unified_authentic_system.py (validation système)
- run_performance_tests.py (tests de performance)
- test_simple_unified_pipeline.py (pipeline unifié)
- test_sophismes_detection.py (tests API REST)

Date: 10/06/2025
Objectif: Consolidation 42→3 scripts avec workflow complet et validation
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
import tempfile
import subprocess
import concurrent.futures
import requests
import pytest
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import traceback

# Configuration du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Configuration du logging avec support UTF-8. La reconfiguration console
# (detach + writer UTF-8) vivait ici au niveau import : elle mutait les flux
# globaux de N'IMPORTE QUEL processus important ce module — le premier test
# qui l'importait tuait le terminal writer de pytest (« underlying buffer
# has been detached », #2390). Elle est désormais posée par le chemin CLI
# (`main`), seul endroit qui en a besoin.
if sys.platform == "win32":

    def _configure_windows_console() -> None:
        import codecs

        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

else:

    def _configure_windows_console() -> None:  # no-op hors Windows
        return None


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ComprehensiveWorkflow")

# === ENUMS ET CONFIGURATIONS ===


class WorkflowMode(Enum):
    """Modes d'exécution du workflow."""

    FULL = "full"  # Workflow complet
    ANALYSIS_ONLY = "analysis_only"  # Analyse uniquement
    TESTING_ONLY = "testing_only"  # Tests uniquement
    VALIDATION_ONLY = "validation"  # Validation uniquement
    PERFORMANCE = "performance"  # Tests de performance
    BATCH = "batch"  # Traitement par lots


class ProcessingEnvironment(Enum):
    """Environnements de traitement."""

    DEV = "development"
    TEST = "testing"
    PROD = "production"


class ReportFormat(Enum):
    """Formats de rapport supportés."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    COMPREHENSIVE = "comprehensive"  # Tous les formats


@dataclass
class WorkflowConfig:
    """Configuration complète du workflow."""

    # Configuration générale
    mode: WorkflowMode = WorkflowMode.FULL
    environment: ProcessingEnvironment = ProcessingEnvironment.DEV
    parallel_workers: int = 4
    enable_monitoring: bool = True

    # Configuration de l'analyse
    enable_decryption: bool = True
    corpus_files: List[str] = field(default_factory=list)
    encryption_passphrase: Optional[str] = None
    analysis_modes: List[str] = field(
        default_factory=lambda: ["fallacies", "rhetoric", "logic"]
    )

    # Configuration des tests
    test_timeout: int = 120
    enable_api_tests: bool = True
    api_base_url: str = "http://localhost:5000"
    performance_iterations: int = 3

    # Configuration de la validation
    enable_system_validation: bool = True

    # Configuration des rapports
    output_dir: Path = Path("results/comprehensive_workflow")
    report_formats: List[ReportFormat] = field(
        default_factory=lambda: [ReportFormat.JSON, ReportFormat.MARKDOWN]
    )
    include_metrics: bool = True

    def __post_init__(self):
        """Validation et normalisation de la configuration."""
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not self.encryption_passphrase:
            self.encryption_passphrase = os.getenv(
                "TEXT_CONFIG_PASSPHRASE", "epita_ia_symb_2025_temp_key"
            )


@dataclass
class WorkflowResults:
    """Résultats consolidés du workflow."""

    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[timedelta] = None
    status: str = "running"

    # Résultats par composant
    decryption_results: Dict[str, Any] = field(default_factory=dict)
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    performance_results: Dict[str, Any] = field(default_factory=dict)

    # Métriques globales
    total_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def finalize(self, status: str = "completed"):
        """Finalise les résultats."""
        self.end_time = datetime.now()
        self.duration = self.end_time - self.start_time
        self.status = status

        # Calcul des métriques finales
        self.total_processed = (
            len(self.analysis_results)
            + len(self.test_results)
            + len(self.validation_results)
        )


# === GESTIONNAIRE DE CORPUS ===


class CorpusManager:
    """Gestionnaire de corpus avec déchiffrement automatique."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.CorpusManager")

    async def load_corpus_data(self) -> Dict[str, Any]:
        """Charge et déchiffre les données de corpus."""
        self.logger.info("🔓 Démarrage du chargement de corpus")
        results = {"status": "success", "loaded_files": [], "errors": []}

        try:
            # Import dynamique pour éviter les erreurs de dépendances
            from argumentation_analysis.core.io_manager import load_extract_definitions
            from argumentation_analysis.core.utils.crypto_utils import (
                derive_encryption_key,
            )

            # Dérivation de la clé de chiffrement
            encryption_key = derive_encryption_key(self.config.encryption_passphrase)

            # Traitement de chaque fichier de corpus
            for corpus_file in self.config.corpus_files:
                corpus_path = Path(corpus_file)

                if not corpus_path.exists():
                    error_msg = f"Fichier corpus non trouvé: {corpus_path}"
                    self.logger.warning(error_msg)
                    results["errors"].append(error_msg)
                    continue

                self.logger.info(f"📂 Chargement: {corpus_path}")

                # Chargement et déchiffrement
                if corpus_path.suffix in [".yml", ".yaml"]:
                    with open(corpus_path, "r", encoding="utf-8") as f:
                        definitions = yaml.safe_load(f)
                else:
                    definitions = load_extract_definitions(
                        config_file=corpus_path, b64_derived_key=encryption_key
                    )

                if definitions:
                    results["loaded_files"].append(
                        {
                            "file": str(corpus_path),
                            "definitions_count": len(definitions),
                            "definitions": definitions,
                        }
                    )
                    self.logger.info(
                        f"✅ Chargé: {len(definitions)} définitions de {corpus_path}"
                    )
                else:
                    error_msg = f"Échec du déchiffrement: {corpus_path}"
                    results["errors"].append(error_msg)
                    self.logger.error(error_msg)

            self.logger.info(
                f"🎯 Corpus chargé: {len(results['loaded_files'])} fichiers"
            )

        except ImportError as e:
            error_msg = f"Modules de déchiffrement non disponibles: {e}"
            self.logger.error(error_msg)
            results["status"] = "error"
            results["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"Erreur lors du chargement de corpus: {e}"
            self.logger.error(error_msg, exc_info=True)
            results["status"] = "error"
            results["errors"].append(error_msg)

        return results


# === MOTEUR DE PIPELINE ===

ANALYSIS_SERVICE_ID = "processor_analysis_llm"


def _make_analysis_kernel() -> Tuple[Any, str]:
    """Kernel d'analyse avec son service LLM (#2390).

    Le chemin canonique : le service est créé par ``create_llm_service``
    (le résolveur de route unique depuis #2352), l'agent est construit
    contre ce kernel — jamais nu. Les tests substituent ce seam par un
    service factice qui archive les prompts rendus.
    """
    import semantic_kernel as sk

    from argumentation_analysis.core.llm_service import create_llm_service

    kernel = sk.Kernel()
    kernel.add_service(create_llm_service(service_id=ANALYSIS_SERVICE_ID))
    return kernel, ANALYSIS_SERVICE_ID


def _construct_analysis_agent() -> Any:
    """Construction unique de l'agent d'analyse (kernel du seam #2390).

    Le scénario de performance ``pipeline_initialization`` chronomètre cette
    construction (#2510) : c'est l'initialisation réelle que chaque analyse
    exécute. Un seul site de construction dans le module — la garde #2390
    l'exige.
    """
    from argumentation_analysis.agents.core.informal.informal_agent import (
        InformalAnalysisAgent,
    )

    kernel, service_id = _make_analysis_kernel()
    agent = InformalAnalysisAgent(kernel=kernel, agent_name="ProcessorInformalAgent")
    agent.setup_agent_components(llm_service_id=service_id)
    return agent


class PipelineEngine:
    """Moteur d'analyse avec orchestration avancée."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.PipelineEngine")

    async def run_analysis_pipeline(
        self, corpus_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Exécute le pipeline d'analyse complet."""
        self.logger.info("🧮 Démarrage du pipeline d'analyse")
        results = {"status": "success", "analyses": [], "errors": []}

        try:
            # Traitement parallèle des données. #2390 : l'UnifiedConfig
            # fabriquée ici ne servait qu'à alimenter un appel qui ne la
            # lisait pas — la route LLM est résolue par _make_analysis_kernel.
            if corpus_data["loaded_files"]:
                analysis_tasks = []

                for file_data in corpus_data["loaded_files"]:
                    for definition in file_data["definitions"]:
                        if "content" in definition:
                            task = self._analyze_text_content(definition["content"])
                            analysis_tasks.append(task)

                # Exécution parallèle avec limite de workers
                if analysis_tasks:
                    semaphore = asyncio.Semaphore(self.config.parallel_workers)
                    limited_tasks = [
                        self._run_with_semaphore(semaphore, task)
                        for task in analysis_tasks
                    ]

                    analysis_results = await asyncio.gather(
                        *limited_tasks, return_exceptions=True
                    )

                    # Traitement des résultats
                    for i, result in enumerate(analysis_results):
                        if isinstance(result, Exception):
                            error_msg = f"Erreur analyse {i}: {result}"
                            self.logger.error(error_msg)
                            results["errors"].append(error_msg)
                        else:
                            results["analyses"].append(result)

            self.logger.info(
                f"✅ Pipeline terminé: {len(results['analyses'])} analyses"
            )

        except Exception as e:
            error_msg = f"Erreur pipeline d'analyse: {e}"
            self.logger.error(error_msg, exc_info=True)
            results["status"] = "error"
            results["errors"].append(error_msg)

        return results

    async def _run_with_semaphore(self, semaphore: asyncio.Semaphore, task):
        """Exécute une tâche avec limitation de concurrence."""
        async with semaphore:
            return await task

    async def _analyze_text_content(
        self, content: str, config: Any = None
    ) -> Dict[str, Any]:
        """Analyse un contenu textuel par le kernel d'analyse (#2390).

        ``config`` est conservé pour le contrat d'appel historique ; la
        construction ne le consulte pas — la route LLM vient de
        l'environnement via ``_make_analysis_kernel``, pas d'une
        configuration sérialisée. Avant #2390, cette méthode empilait quatre
        défauts dont chacun masquait les suivants : un kwarg ``config``
        inexistant (le constructeur exige ``kernel``), un
        ``setup_agent_components()`` sans son ``llm_service_id`` obligatoire,
        un ``await`` sur cette méthode sync, et un ``analyze`` qui n'existe
        pas sur l'agent.
        """
        try:
            agent = _construct_analysis_agent()

            # Exécution de l'analyse
            analysis_result = await agent.analyze_text(
                content[:1000]
            )  # Limite pour performance

            # L'agent remonte un échec (appel LLM levé, réponse non-JSON)
            # dans le champ ``error`` de premier niveau (contrat #2485) :
            # le publier ``success`` reviendrait à dire qu'une analyse qui
            # n'a pas eu lieu a réussi.
            analysis_error = analysis_result.get("error")
            if analysis_error:
                return {
                    "content_preview": (
                        content[:200] + "..." if len(content) > 200 else content
                    ),
                    "analysis": analysis_result,
                    "error": str(analysis_error),
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                }

            return {
                "content_preview": (
                    content[:200] + "..." if len(content) > 200 else content
                ),
                "analysis": analysis_result,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
            }

        except Exception as e:
            return {
                "content_preview": (
                    content[:200] + "..." if len(content) > 200 else content
                ),
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "error",
            }


# === SUITE DE VALIDATION ===


class ValidationSuite:
    """Suite de validation système : tests système et tests API."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.ValidationSuite")

    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Exécute une validation complète du système."""
        self.logger.info("🔍 Démarrage de la validation système")
        results = {
            "status": "success",
            "system_tests": {},
            "api_tests": {},
            "errors": [],
        }

        try:
            # 1. Tests système
            if self.config.enable_system_validation:
                system_results = await self._run_system_tests()
                results["system_tests"] = system_results

            # 2. Tests API
            if self.config.enable_api_tests:
                api_results = await self._run_api_tests()
                results["api_tests"] = api_results

            self.logger.info("✅ Validation système terminée")

        except Exception as e:
            error_msg = f"Erreur validation système: {e}"
            self.logger.error(error_msg, exc_info=True)
            results["status"] = "error"
            results["errors"].append(error_msg)

        return results

    async def _run_system_tests(self) -> Dict[str, Any]:
        """Exécute les tests système."""
        test_files = [
            "test_conversation_integration.py",
            "demo_authentic_system.py",
            "test_intelligent_modal_correction.py",
            "test_modal_correction_validation.py",
            "test_final_modal_correction_demo.py",
            "test_advanced_rhetorical_enhanced.py",
            "test_rhetorical_demo_integration.py",
            "test_micro_orchestration.py",
        ]

        results = {"tests": {}, "passed": 0, "failed": 0, "skipped": 0}

        for test_file in test_files:
            test_path = PROJECT_ROOT / "scripts" / "testing" / test_file

            if not test_path.exists():
                results["tests"][test_file] = {
                    "status": "skipped",
                    "reason": "file_not_found",
                }
                results["skipped"] += 1
                continue

            try:
                start_time = time.time()
                result = subprocess.run(
                    [sys.executable, str(test_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.config.test_timeout,
                    cwd=PROJECT_ROOT,
                )
                duration = time.time() - start_time

                status = "passed" if result.returncode == 0 else "failed"
                results["tests"][test_file] = {
                    "status": status,
                    "duration": duration,
                    "returncode": result.returncode,
                    "output": (
                        result.stdout[-500:] if result.stdout else ""
                    ),  # Dernières 500 chars
                    "error": result.stderr[-500:] if result.stderr else "",
                }

                if status == "passed":
                    results["passed"] += 1
                else:
                    results["failed"] += 1

            except subprocess.TimeoutExpired:
                results["tests"][test_file] = {
                    "status": "timeout",
                    "duration": self.config.test_timeout,
                    "error": f"Test timeout after {self.config.test_timeout}s",
                }
                results["failed"] += 1
            except Exception as e:
                results["tests"][test_file] = {"status": "error", "error": str(e)}
                results["failed"] += 1

        return results

    async def _run_api_tests(self) -> Dict[str, Any]:
        """Exécute les tests d'API REST."""
        results = {"tests": {}, "api_available": False}

        # Test de disponibilité de l'API
        try:
            response = requests.get(f"{self.config.api_base_url}/api/health", timeout=5)
            results["api_available"] = response.status_code in [200, 404]
        except requests.exceptions.ConnectionError:
            results["api_available"] = False
            results["error"] = "API non accessible"
            return results

        if not results["api_available"]:
            return results

        # Tests de sophismes
        test_cases = [
            {
                "name": "pente_glissante",
                "text": "Si on autorise les gens à conduire à 85 km/h, bientôt ils voudront conduire à 200 km/h.",
                "expected_fallacies": True,
            },
            {
                "name": "homme_de_paille",
                "text": "Les écologistes veulent qu'on retourne à l'âge de pierre.",
                "expected_fallacies": True,
            },
            {
                "name": "texte_neutre",
                "text": "Il fait beau aujourd'hui et les oiseaux chantent.",
                "expected_fallacies": False,
            },
        ]

        for test_case in test_cases:
            try:
                response = requests.post(
                    f"{self.config.api_base_url}/api/fallacies",
                    json={"text": test_case["text"]},
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )

                if response.status_code == 200:
                    data = response.json()
                    fallacies_detected = len(data.get("fallacies", [])) > 0

                    results["tests"][test_case["name"]] = {
                        "status": "passed",
                        "fallacies_detected": fallacies_detected,
                        "fallacies_count": len(data.get("fallacies", [])),
                        "expected": test_case["expected_fallacies"],
                        "response_time": response.elapsed.total_seconds(),
                    }
                else:
                    results["tests"][test_case["name"]] = {
                        "status": "failed",
                        "error": f"HTTP {response.status_code}",
                        "response": response.text[:200],
                    }

            except Exception as e:
                results["tests"][test_case["name"]] = {
                    "status": "error",
                    "error": str(e),
                }

        return results


# === ORCHESTRATEUR DE TESTS ===


class TestOrchestrator:
    """Orchestrateur master pour tous les tests."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.TestOrchestrator")

    async def run_performance_tests(self) -> Dict[str, Any]:
        """Exécute les tests de performance."""
        self.logger.info("⚡ Démarrage des tests de performance")
        results = {
            "status": "success",
            "iterations": self.config.performance_iterations,
            "tests": {},
            "summary": {},
            "errors": [],
        }

        try:
            # Tests de performance par composant. #2510 : chaque scénario
            # chronomètre une opération réelle du processeur. Le scénario
            # « validation_suite » est retiré : la validation est une phase à
            # part entière du workflow (suites de tests en sous-processus +
            # appels HTTP), la chronométrer ici la rejouerait au lieu de
            # mesurer le processeur. Le résumé nomme les scénarios : un
            # retrait se voit, ``total_scenarios`` ne rétrécit pas
            # silencieusement.
            test_scenarios = [
                ("text_analysis", self._performance_text_analysis),
                ("pipeline_initialization", self._performance_pipeline_init),
            ]

            for test_name, test_func in test_scenarios:
                self.logger.info(f"🔄 Test performance: {test_name}")

                durations = []
                errors = []

                for iteration in range(self.config.performance_iterations):
                    try:
                        start_time = time.time()
                        await test_func()
                        duration = time.time() - start_time
                        durations.append(duration)

                    except Exception as e:
                        error_msg = f"Iteration {iteration + 1}: {e}"
                        errors.append(error_msg)
                        self.logger.warning(error_msg)

                if durations:
                    results["tests"][test_name] = {
                        "iterations": len(durations),
                        "avg_duration": sum(durations) / len(durations),
                        "min_duration": min(durations),
                        "max_duration": max(durations),
                        "total_duration": sum(durations),
                        "errors": errors,
                        "success_rate": len(durations)
                        / self.config.performance_iterations,
                    }
                else:
                    results["tests"][test_name] = {"status": "failed", "errors": errors}

            # Calcul du résumé
            total_tests = len(results["tests"])
            successful_tests = sum(
                1 for test in results["tests"].values() if "avg_duration" in test
            )

            results["summary"] = {
                "scenarios": [name for name, _ in test_scenarios],
                "total_scenarios": total_tests,
                "successful_scenarios": successful_tests,
                "success_rate": (
                    successful_tests / total_tests if total_tests > 0 else 0
                ),
                "total_iterations": self.config.performance_iterations * total_tests,
            }

            self.logger.info(
                f"✅ Tests de performance terminés: {successful_tests}/{total_tests} réussis"
            )

        except Exception as e:
            error_msg = f"Erreur tests de performance: {e}"
            self.logger.error(error_msg, exc_info=True)
            results["status"] = "error"
            results["errors"].append(error_msg)

        return results

    async def _performance_text_analysis(self):
        """Test de performance d'analyse de texte (#2390 : un seul chemin).

        Le scénario emprunte la construction du ``PipelineEngine`` — plus de
        copie locale. La copie portait son propre premier défaut
        (``MockLevel.MINIMAL``, membre inexistant : ``AttributeError`` que
        l'``except ImportError`` ne rattrapait pas — le scénario levait au
        lieu de mesurer). Un échec d'analyse est nommé, pas avalé.
        """
        engine = PipelineEngine(self.config)
        result = await engine._analyze_text_content(
            "Ceci est un texte de test pour l'analyse de performance."
        )
        if result.get("status") != "success":
            raise RuntimeError(
                f"analyse de performance en erreur: {result.get('error')}"
            )

    async def _performance_pipeline_init(self):
        """Test de performance d'initialisation de pipeline (#2510).

        Chronomètre l'initialisation réelle du pipeline d'analyse : kernel
        du seam canonique, agent informel, setup. L'ancien corps
        chronométrait un sommeil (une constante publiée comme mesure) ; sa
        branche ``except ImportError`` exécutait le même sommeil — un
        succès fabriqué pour une opération qui n'a pas tourné.
        """
        _construct_analysis_agent()


# === AGRÉGATEUR DE RÉSULTATS ===


class ResultsAggregator:
    """Agrégateur et générateur de rapports."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.ResultsAggregator")

    async def generate_comprehensive_report(
        self, results: WorkflowResults
    ) -> Dict[str, str]:
        """Génère des rapports dans tous les formats demandés."""
        self.logger.info("📊 Génération des rapports consolidés")
        report_files = {}

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for report_format in self.config.report_formats:
                if report_format == ReportFormat.JSON:
                    file_path = await self._generate_json_report(results, timestamp)
                    report_files["json"] = str(file_path)

                elif report_format == ReportFormat.MARKDOWN:
                    file_path = await self._generate_markdown_report(results, timestamp)
                    report_files["markdown"] = str(file_path)

                elif report_format == ReportFormat.HTML:
                    file_path = await self._generate_html_report(results, timestamp)
                    report_files["html"] = str(file_path)

                elif report_format == ReportFormat.COMPREHENSIVE:
                    # Générer tous les formats
                    json_file = await self._generate_json_report(results, timestamp)
                    md_file = await self._generate_markdown_report(results, timestamp)
                    html_file = await self._generate_html_report(results, timestamp)

                    report_files.update(
                        {
                            "json": str(json_file),
                            "markdown": str(md_file),
                            "html": str(html_file),
                        }
                    )

            self.logger.info(f"✅ Rapports générés: {list(report_files.keys())}")

        except Exception as e:
            error_msg = f"Erreur génération rapports: {e}"
            self.logger.error(error_msg, exc_info=True)

        return report_files

    async def _generate_json_report(
        self, results: WorkflowResults, timestamp: str
    ) -> Path:
        """Génère un rapport JSON détaillé."""
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "workflow_version": "3.0.0",
                "environment": self.config.environment.value,
                "mode": self.config.mode.value,
            },
            "execution_summary": {
                "start_time": results.start_time.isoformat(),
                "end_time": results.end_time.isoformat() if results.end_time else None,
                "duration_seconds": (
                    results.duration.total_seconds() if results.duration else None
                ),
                "status": results.status,
                "total_processed": results.total_processed,
                "success_count": results.success_count,
                "error_count": results.error_count,
            },
            "results": {
                "decryption": results.decryption_results,
                "analysis": results.analysis_results,
                "testing": results.test_results,
                "validation": results.validation_results,
                "performance": results.performance_results,
            },
            "warnings": results.warnings,
            "errors": results.errors,
        }

        file_path = (
            self.config.output_dir / f"comprehensive_workflow_report_{timestamp}.json"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

        return file_path

    async def _generate_markdown_report(
        self, results: WorkflowResults, timestamp: str
    ) -> Path:
        """Génère un rapport Markdown."""
        md_content = f"""# 🚀 Rapport de Workflow Complet

**Date**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}  
**Mode**: {self.config.mode.value}  
**Environnement**: {self.config.environment.value}  
**Durée**: {results.duration.total_seconds():.2f}s  
**Statut**: {results.status}  

## 📊 Résumé Exécutif

- **Total traité**: {results.total_processed}
- **Succès**: {results.success_count}
- **Erreurs**: {results.error_count}
- **Taux de réussite**: {(results.success_count / max(results.total_processed, 1) * 100):.1f}%

## 🔓 Déchiffrement de Corpus

"""

        if results.decryption_results:
            if results.decryption_results.get("status") == "success":
                md_content += f"✅ **Succès** - {len(results.decryption_results.get('loaded_files', []))} fichiers chargés\n\n"

                for file_info in results.decryption_results.get("loaded_files", []):
                    md_content += f"- `{file_info['file']}`: {file_info['definitions_count']} définitions\n"
            else:
                md_content += "❌ **Échec du déchiffrement**\n\n"
                for error in results.decryption_results.get("errors", []):
                    md_content += f"- ⚠️ {error}\n"
        else:
            md_content += "_Aucun déchiffrement demandé_\n"

        md_content += "\n## 🧮 Analyse Pipeline\n\n"

        if results.analysis_results:
            if results.analysis_results.get("status") == "success":
                analyses_count = len(results.analysis_results.get("analyses", []))
                md_content += f"✅ **{analyses_count} analyses réalisées**\n\n"
            else:
                md_content += "❌ **Échec du pipeline d'analyse**\n\n"
        else:
            md_content += "_Aucune analyse demandée_\n"

        md_content += "\n## 🔍 Validation Système\n\n"

        if results.validation_results:
            val_res = results.validation_results

            # Tests système
            sys_tests = val_res.get("system_tests", {})
            if sys_tests:
                passed = sys_tests.get("passed", 0)
                failed = sys_tests.get("failed", 0)
                total = passed + failed
                md_content += f"**Tests Système**: {passed}/{total} réussis\n\n"

            # Tests API
            api_tests = val_res.get("api_tests", {})
            if api_tests.get("api_available"):
                api_test_count = len(api_tests.get("tests", {}))
                md_content += f"**Tests API**: {api_test_count} tests exécutés\n\n"
        else:
            md_content += "_Aucune validation demandée_\n"

        md_content += "\n## ⚡ Performance\n\n"

        if results.performance_results:
            perf_res = results.performance_results
            summary = perf_res.get("summary", {})

            if summary:
                success_rate = summary.get("success_rate", 0)
                total_scenarios = summary.get("total_scenarios", 0)
                md_content += f"**Taux de réussite**: {success_rate:.1%}\n"
                md_content += f"**Scénarios testés**: {total_scenarios}\n\n"

                for test_name, test_data in perf_res.get("tests", {}).items():
                    if "avg_duration" in test_data:
                        avg_dur = test_data["avg_duration"]
                        md_content += f"- `{test_name}`: {avg_dur:.3f}s (moyenne)\n"
        else:
            md_content += "_Aucun test de performance demandé_\n"

        if results.warnings:
            md_content += "\n## ⚠️ Avertissements\n\n"
            for warning in results.warnings:
                md_content += f"- {warning}\n"

        if results.errors:
            md_content += "\n## ❌ Erreurs\n\n"
            for error in results.errors:
                md_content += f"- {error}\n"

        md_content += (
            f"\n---\n\n_Rapport généré par Comprehensive Workflow Processor v3.0.0_\n"
        )

        file_path = (
            self.config.output_dir / f"comprehensive_workflow_report_{timestamp}.md"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return file_path

    async def _generate_html_report(
        self, results: WorkflowResults, timestamp: str
    ) -> Path:
        """Génère un rapport HTML avec style."""
        html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Workflow Complet - {timestamp}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .status-success {{ color: #10b981; }}
        .status-error {{ color: #ef4444; }}
        .status-warning {{ color: #f59e0b; }}
        .metric-card {{ background: #f8fafc; border: 1px solid #e2e8f0; 
                       border-radius: 8px; padding: 20px; margin: 10px 0; }}
        .metric-value {{ font-size: 2em; font-weight: bold; }}
        .progress-bar {{ background: #e2e8f0; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ background: #10b981; height: 20px; transition: width 0.3s; }}
        pre {{ background: #1f2937; color: #f9fafb; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Rapport de Workflow Complet</h1>
        <p><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        <p><strong>Mode:</strong> {self.config.mode.value} | <strong>Environnement:</strong> {self.config.environment.value}</p>
        <p><strong>Durée:</strong> {results.duration.total_seconds():.2f}s | <strong>Statut:</strong> <span class="status-{results.status}">{results.status}</span></p>
    </div>
    
    <div class="grid">
        <div class="metric-card">
            <h3>📊 Métriques Globales</h3>
            <div class="metric-value">{results.total_processed}</div>
            <p>Total traité</p>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {(results.success_count / max(results.total_processed, 1) * 100):.0f}%"></div>
            </div>
            <p>Taux de réussite: {(results.success_count / max(results.total_processed, 1) * 100):.1f}%</p>
        </div>
        
        <div class="metric-card">
            <h3>🔓 Déchiffrement</h3>
            {"✅ Succès" if results.decryption_results.get("status") == "success" else "❌ Échec" if results.decryption_results else "➖ Non demandé"}
            <p>{len(results.decryption_results.get('loaded_files', []))} fichiers chargés</p>
        </div>
        
        <div class="metric-card">
            <h3>🧮 Analyse</h3>
            {"✅ Succès" if results.analysis_results.get("status") == "success" else "❌ Échec" if results.analysis_results else "➖ Non demandé"}
            <p>{len(results.analysis_results.get('analyses', []))} analyses réalisées</p>
        </div>
        
        <div class="metric-card">
            <h3>🔍 Validation</h3>
            {"✅ Système validé" if results.validation_results else "➖ Non demandé"}
        </div>
    </div>

    <div class="metric-card">
        <h3>📝 Détails Complets</h3>
        <pre>{json.dumps({
            "decryption": results.decryption_results,
            "analysis": results.analysis_results,
            "validation": results.validation_results,
            "performance": results.performance_results
        }, indent=2, ensure_ascii=False, default=str)}</pre>
    </div>

    <footer style="text-align: center; margin-top: 50px; color: #6b7280;">
        <p><em>Rapport généré par Comprehensive Workflow Processor v3.0.0</em></p>
    </footer>
</body>
</html>"""

        file_path = (
            self.config.output_dir / f"comprehensive_workflow_report_{timestamp}.html"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return file_path


# === PROCESSEUR PRINCIPAL ===


class ComprehensiveWorkflowProcessor:
    """Processeur principal orchestrant tous les workflows."""

    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.ComprehensiveWorkflowProcessor")

        # Initialisation des composants
        self.corpus_manager = CorpusManager(config)
        self.pipeline_engine = PipelineEngine(config)
        self.validation_suite = ValidationSuite(config)
        self.test_orchestrator = TestOrchestrator(config)
        self.results_aggregator = ResultsAggregator(config)

    async def run_comprehensive_workflow(self) -> WorkflowResults:
        """Exécute un workflow complet selon la configuration."""
        self.logger.info(
            f"🚀 Démarrage du workflow comprehensive ({self.config.mode.value})"
        )

        results = WorkflowResults(start_time=datetime.now())

        try:
            # 1. Phase de déchiffrement (si activée)
            if self.config.enable_decryption and self.config.corpus_files:
                if self.config.mode in [WorkflowMode.FULL, WorkflowMode.ANALYSIS_ONLY]:
                    self.logger.info("Phase 1: Déchiffrement de corpus")
                    decryption_results = await self.corpus_manager.load_corpus_data()
                    results.decryption_results = decryption_results

                    if decryption_results.get("status") == "error":
                        results.warnings.append("Échec du déchiffrement de corpus")

            # 2. Phase d'analyse (si demandée)
            if self.config.mode in [WorkflowMode.FULL, WorkflowMode.ANALYSIS_ONLY]:
                self.logger.info("Phase 2: Pipeline d'analyse")
                if self.config.enable_decryption:
                    corpus_data = results.decryption_results or {"loaded_files": []}
                else:
                    corpus_data = {"loaded_files": []}
                    for corpus_file in self.config.corpus_files:
                        corpus_path = Path(corpus_file)
                        if corpus_path.suffix in [".yml", ".yaml"]:
                            with open(corpus_path, "r", encoding="utf-8") as f:
                                definitions = yaml.safe_load(f)
                                corpus_data["loaded_files"].append(
                                    {
                                        "file": str(corpus_path),
                                        "definitions_count": len(definitions),
                                        "definitions": definitions,
                                    }
                                )

                analysis_results = await self.pipeline_engine.run_analysis_pipeline(
                    corpus_data
                )
                results.analysis_results = analysis_results

                if analysis_results.get("status") == "error":
                    results.errors.extend(analysis_results.get("errors", []))

            # 3. Phase de tests (si demandée)
            if self.config.mode in [WorkflowMode.FULL, WorkflowMode.TESTING_ONLY]:
                self.logger.info("Phase 3: Orchestration de tests")
                test_results = (
                    await self.validation_suite.run_comprehensive_validation()
                )
                results.test_results = test_results

                if test_results.get("status") == "error":
                    results.errors.extend(test_results.get("errors", []))

            # 4. Phase de validation (si demandée)
            if self.config.mode in [WorkflowMode.FULL, WorkflowMode.VALIDATION_ONLY]:
                self.logger.info("Phase 4: Validation système")
                validation_results = (
                    await self.validation_suite.run_comprehensive_validation()
                )
                results.validation_results = validation_results

                if validation_results.get("status") == "error":
                    results.errors.extend(validation_results.get("errors", []))

            # 5. Phase de performance (si demandée)
            if self.config.mode in [WorkflowMode.FULL, WorkflowMode.PERFORMANCE]:
                self.logger.info("Phase 5: Tests de performance")
                performance_results = (
                    await self.test_orchestrator.run_performance_tests()
                )
                results.performance_results = performance_results

                if performance_results.get("status") == "error":
                    results.errors.extend(performance_results.get("errors", []))

            # 6. Finalisation des résultats
            results.finalize(
                "completed" if not results.errors else "completed_with_errors"
            )

            # 7. Génération des rapports
            if self.config.report_formats:
                self.logger.info("Phase 6: Génération des rapports")
                report_files = (
                    await self.results_aggregator.generate_comprehensive_report(results)
                )
                self.logger.info(f"📊 Rapports générés: {list(report_files.keys())}")

                for format_name, file_path in report_files.items():
                    self.logger.info(f"  📄 {format_name.upper()}: {file_path}")

            # 8. Résumé final
            self._log_execution_summary(results)

        except Exception as e:
            error_msg = f"Erreur critique dans le workflow: {e}"
            self.logger.error(error_msg, exc_info=True)
            results.errors.append(error_msg)
            results.finalize("failed")

        return results

    def _log_execution_summary(self, results: WorkflowResults):
        """Affiche un résumé de l'exécution."""
        self.logger.info("=" * 70)
        self.logger.info("🎯 RÉSUMÉ DU WORKFLOW COMPREHENSIVE")
        self.logger.info("=" * 70)
        self.logger.info(f"⏱️  Durée totale: {results.duration.total_seconds():.2f}s")
        self.logger.info(f"📊 Total traité: {results.total_processed}")
        self.logger.info(f"✅ Succès: {results.success_count}")
        self.logger.info(f"❌ Erreurs: {results.error_count}")
        self.logger.info(
            f"📈 Taux de réussite: {(results.success_count / max(results.total_processed, 1) * 100):.1f}%"
        )
        self.logger.info(f"🎭 Statut final: {results.status}")

        if results.warnings:
            self.logger.info(f"⚠️  Avertissements: {len(results.warnings)}")

        if results.errors:
            self.logger.info(f"🚨 Erreurs: {len(results.errors)}")
            for error in results.errors[:3]:  # Afficher les 3 premières erreurs
                self.logger.info(f"   • {error}")
            if len(results.errors) > 3:
                self.logger.info(f"   ... et {len(results.errors) - 3} autres erreurs")

        self.logger.info("=" * 70)


# === CONFIGURATION CLI ===


def create_parser() -> argparse.ArgumentParser:
    """Crée le parser d'arguments CLI."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Workflow Processor - Orchestrateur master pour workflows complets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:

  # Workflow complet avec déchiffrement
  python comprehensive_workflow_processor.py --mode full --corpus tests/extract_sources_backup.enc

  # Tests uniquement avec validation API
  python comprehensive_workflow_processor.py --mode testing_only --enable-api-tests

  # Tests de performance en parallèle
  python comprehensive_workflow_processor.py --mode performance --workers 8 --iterations 5

  # Traitement par lots avec rapports complets
  python comprehensive_workflow_processor.py --mode batch --output-dir results/batch_analysis --format comprehensive

Modes disponibles: full, analysis_only, testing_only, validation, performance, batch
Environnements: development, testing, production
        """,
    )

    # Configuration générale
    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        choices=[mode.value for mode in WorkflowMode],
        default=WorkflowMode.FULL.value,
        help="Mode d'exécution du workflow (défaut: full)",
    )

    parser.add_argument(
        "--environment",
        "-e",
        type=str,
        choices=[env.value for env in ProcessingEnvironment],
        default=ProcessingEnvironment.DEV.value,
        help="Environnement de traitement (défaut: development)",
    )

    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=4,
        help="Nombre de workers parallèles (défaut: 4)",
    )

    # Configuration corpus et déchiffrement
    parser.add_argument(
        "--corpus",
        "-c",
        action="append",
        help="Fichier(s) de corpus à traiter (peut être utilisé plusieurs fois)",
    )

    parser.add_argument(
        "--passphrase",
        "-p",
        type=str,
        help="Passphrase de déchiffrement (défaut: variable d'environnement)",
    )

    parser.add_argument(
        "--no-decryption",
        action="store_true",
        help="Désactiver le déchiffrement de corpus",
    )

    # Configuration des tests
    parser.add_argument(
        "--test-timeout",
        type=int,
        default=120,
        help="Timeout pour les tests en secondes (défaut: 120)",
    )

    parser.add_argument(
        "--enable-api-tests", action="store_true", help="Activer les tests d'API REST"
    )

    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:5000",
        help="URL de base pour les tests d'API (défaut: http://localhost:5000)",
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Nombre d'itérations pour les tests de performance (défaut: 3)",
    )

    # Configuration validation
    parser.add_argument(
        "--disable-system-validation",
        action="store_true",
        help="Désactiver la validation système",
    )

    # Configuration des rapports
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="results/comprehensive_workflow",
        help="Répertoire de sortie (défaut: results/comprehensive_workflow)",
    )

    parser.add_argument(
        "--format",
        "-f",
        action="append",
        choices=[fmt.value for fmt in ReportFormat],
        help="Format(s) de rapport (peut être utilisé plusieurs fois)",
    )

    parser.add_argument(
        "--no-reports", action="store_true", help="Désactiver la génération de rapports"
    )

    # Options de debugging
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")

    parser.add_argument(
        "--debug", action="store_true", help="Mode debug avec traces détaillées"
    )

    parser.add_argument(
        "--disable-monitoring", action="store_true", help="Désactiver le monitoring"
    )

    return parser


def parse_arguments(args: Optional[List[str]] = None) -> WorkflowConfig:
    """Parse les arguments et crée la configuration."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # Configuration du logging selon le niveau demandé
    if parsed_args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Mode debug activé")
    elif parsed_args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.info("Mode verbeux activé")

    # Construction de la configuration
    config = WorkflowConfig(
        # Configuration générale
        mode=WorkflowMode(parsed_args.mode),
        environment=ProcessingEnvironment(parsed_args.environment),
        parallel_workers=parsed_args.workers,
        enable_monitoring=not parsed_args.disable_monitoring,
        # Configuration corpus
        enable_decryption=not parsed_args.no_decryption,
        corpus_files=parsed_args.corpus or [],
        encryption_passphrase=parsed_args.passphrase,
        # Configuration tests
        test_timeout=parsed_args.test_timeout,
        enable_api_tests=parsed_args.enable_api_tests,
        api_base_url=parsed_args.api_url,
        performance_iterations=parsed_args.iterations,
        # Configuration validation
        enable_system_validation=not parsed_args.disable_system_validation,
        # Configuration rapports
        output_dir=Path(parsed_args.output_dir),
        report_formats=(
            [ReportFormat(fmt) for fmt in (parsed_args.format or ["json", "markdown"])]
            if not parsed_args.no_reports
            else []
        ),
        include_metrics=True,
    )

    return config


# === POINT D'ENTRÉE PRINCIPAL ===


async def main_async(config: WorkflowConfig) -> int:
    """Fonction principale asynchrone."""
    try:
        logger.info("🚀 Démarrage du Comprehensive Workflow Processor v3.0.0")
        logger.info(
            f"📋 Configuration: {config.mode.value} | {config.environment.value}"
        )

        # Création et exécution du processeur
        processor = ComprehensiveWorkflowProcessor(config)
        results = await processor.run_comprehensive_workflow()

        # Détermination du code de retour
        if results.status == "completed":
            logger.info("🎉 Workflow terminé avec succès")
            return 0
        elif results.status == "completed_with_errors":
            logger.warning("⚠️ Workflow terminé avec des erreurs")
            return 1
        else:
            logger.error("❌ Workflow échoué")
            return 2

    except KeyboardInterrupt:
        logger.info("⏹️ Workflow interrompu par l'utilisateur")
        return 130
    except Exception as e:
        logger.error(f"💥 Erreur critique: {e}", exc_info=True)
        return 1


def main() -> int:
    """Point d'entrée principal synchrone."""
    try:
        _configure_windows_console()
        config = parse_arguments()
        return asyncio.run(main_async(config))
    except Exception as e:
        logger.error(f"💥 Erreur lors de l'initialisation: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
