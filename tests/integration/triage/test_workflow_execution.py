# -*- coding: utf-8 -*-
"""
Test d'intégration de bout en bout pour la validation de l'exécution de workflows,
de la gestion des erreurs, et du framework de benchmark via la nouvelle architecture de services.

Ce test a pour objectif de valider plusieurs aspects fondamentaux de l'architecture :
1.  **Chargement de Plugins :** Construit le registre de plugins directement depuis
    les manifestes JSON des fixtures (le mécanisme de découverte automatique a été
    retiré — #2099 ; les fixtures restent la donnée du test, lues par json+importlib).
2.  **Orchestration de Services :** Assure que l'`OrchestrationService` peut recevoir
    des requêtes, identifier le plugin et la capacité cibles, et exécuter la
    logique métier correspondante.
3.  **Exécution de Workflow :** Simule un workflow simple en enchaînant les appels à
    plusieurs plugins, validant que les données peuvent transiter correctement
    entre les étapes.
4.  **Benchmarking :** Confirme que le `BenchmarkService` peut exécuter des suites de
    tests complètes sur les capacités des plugins, mesurer avec précision les
    performances (latence, succès/échec), et agréger les résultats.
5.  **Gestion des Erreurs :** Valide que l'orchestrateur intercepte correctement
    les exceptions levées par un plugin, retourne une réponse d'erreur structurée
    et enregistre l'échec dans les métriques de benchmark.

Les scénarios de test utilisent des plugins factices (`prefixer`, `suffixer`, `chaotic`)
pour construire des chaînes de traitement prédictibles, y compris des scénarios d'échec
et des campagnes de benchmark complètes.
"""

import json
import unittest
import os
import sys
import importlib.util
from typing import Dict, Any

# Ajouter le répertoire racine du projet au sys.path pour permettre les imports absolus
# Cela simule l'exécution depuis la racine du projet.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from argumentation_analysis.plugin_framework.core.services.orchestration_service import (
    OrchestrationService,
)
from argumentation_analysis.plugin_framework.benchmarking.benchmark_service import (
    BenchmarkService,
)
from argumentation_analysis.plugin_framework.core.contracts import OrchestrationRequest


class TestWorkflowExecution(unittest.TestCase):
    """
    Cette suite de tests valide la chaîne complète :
    registre (construit directement) -> OrchestrationService -> BenchmarkService.
    Elle charge des plugins de test, exécute un workflow simple qui les
    enchaîne, et valide les résultats et les métriques de performance.
    """

    def setUp(self):
        """
        Initialise l'environnement de test avant chaque exécution.
        Charge les plugins de test et instancie les services nécessaires.
        """
        self.plugins_path = os.path.join(project_root, "tests", "fixtures", "plugins")

        # 1. Charger les plugins depuis leurs manifestes (json + importlib, sans chargeur)
        self.plugin_registry: Dict[str, Any] = {}
        for plugin_dir in sorted(os.listdir(self.plugins_path)):
            manifest_path = os.path.join(
                self.plugins_path, plugin_dir, "plugin_manifest.json"
            )
            if not os.path.isfile(manifest_path):
                continue
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)

            plugin_name = manifest["plugin_name"]
            entry_point = manifest["entry_point"]
            class_name = manifest["class_name"]

            # Charger dynamiquement la classe du plugin
            module_path = os.path.join(os.path.dirname(manifest_path), entry_point)

            spec = importlib.util.spec_from_file_location(plugin_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                plugin_class = getattr(module, class_name)
                self.plugin_registry[plugin_name] = plugin_class()

        # 2. Initialiser les services avec les plugins chargés
        self.orchestration_service = OrchestrationService(
            plugin_registry=self.plugin_registry
        )
        self.benchmark_service = BenchmarkService(
            orchestration_service=self.orchestration_service
        )

    def test_simple_workflow_execution_and_benchmarking(self):
        """
        Valide l'exécution d'un workflow simple (prefixer -> suffixer) et
        vérifie que le résultat est correct et que les métriques de benchmark
        sont collectées.
        """
        # 1. Définition du Workflow et des données d'entrée
        initial_text = "workflow"

        # Étape 1: Appeler le plugin 'prefixer'
        prefix_request = OrchestrationRequest(
            mode="direct_plugin_call",
            target="prefixer.add_prefix",
            payload={"text": initial_text},
        )
        prefix_response = self.orchestration_service.handle_request(prefix_request)

        # Assertion de l'étape 1
        self.assertEqual(prefix_response.status, "success")
        self.assertIsNotNone(prefix_response.result)
        prefixed_text = prefix_response.result.get("processed_text")
        self.assertEqual(prefixed_text, "pre_workflow")

        # Étape 2: Appeler le plugin 'suffixer' avec le résultat de l'étape 1
        suffix_request = OrchestrationRequest(
            mode="direct_plugin_call",
            target="suffixer.add_suffix",
            payload={"text": prefixed_text},
        )
        suffix_response = self.orchestration_service.handle_request(suffix_request)

        # Assertion de l'étape 2 (résultat final du workflow)
        self.assertEqual(suffix_response.status, "success")
        self.assertIsNotNone(suffix_response.result)
        final_text = suffix_response.result.get("processed_text")
        self.assertEqual(final_text, "pre_workflow_suf")

        # 2. Validation du BenchmarkService
        # Exécuter une suite de benchmarks sur le plugin 'prefixer'
        benchmark_requests = [
            {"payload": {"text": "test1"}},
            {"payload": {"text": "test2", "prefix": "custom_"}},
        ]

        suite_result = self.benchmark_service.run_suite(
            plugin_name="prefixer",
            capability_name="add_prefix",
            requests=[req["payload"] for req in benchmark_requests],
        )

        # Assertions sur les résultats du benchmark
        self.assertEqual(suite_result.plugin_name, "prefixer")
        self.assertEqual(suite_result.capability_name, "add_prefix")
        self.assertEqual(suite_result.total_runs, 2)
        self.assertEqual(suite_result.successful_runs, 2)
        self.assertEqual(suite_result.failed_runs, 0)
        self.assertTrue(suite_result.average_duration_ms > 0)

        # Vérifier que les sorties sont correctes dans les résultats individuels
        self.assertEqual(
            suite_result.results[0].output.get("processed_text"), "pre_test1"
        )
        self.assertEqual(
            suite_result.results[1].output.get("processed_text"), "custom_test2"
        )

    def test_workflow_with_error_handling(self):
        """
        Valide la robustesse de l'orchestrateur face à une erreur levée par un plugin.
        Ce test vérifie que l'erreur est correctement interceptée, formatée dans la
        réponse, et qu'une métrique d'échec est enregistrée par le BenchmarkService.
        """
        # 1. Définir une requête qui doit provoquer une erreur
        error_request_payload = {"fail": True}

        # 2. Exécuter la requête via le BenchmarkService pour capturer les métriques
        suite_result = self.benchmark_service.run_suite(
            plugin_name="chaotic",
            capability_name="process_or_fail",
            requests=[error_request_payload],
        )

        # 3. Valider la réponse de l'orchestrateur encapsulée dans le résultat du benchmark
        self.assertEqual(suite_result.total_runs, 1)
        self.assertEqual(suite_result.failed_runs, 1)
        self.assertEqual(suite_result.successful_runs, 0)

        # Récupérer le résultat individuel qui contient la réponse de l'orchestrateur
        error_result = suite_result.results[0]

        self.assertFalse(error_result.is_success)
        self.assertIsNone(error_result.output)
        self.assertIsNotNone(error_result.error)

        # Vérifier que le message d'erreur de la ValueError est bien présent
        self.assertIn(
            "Échec intentionnel simulé par le ChaoticPlugin.", error_result.error
        )

        # 4. Valider directement la réponse de l'OrchestrationService
        error_request = OrchestrationRequest(
            mode="direct_plugin_call",
            target="chaotic.process_or_fail",
            payload=error_request_payload,
        )
        error_response = self.orchestration_service.handle_request(error_request)

        self.assertEqual(error_response.status, "error")
        self.assertIsNone(error_response.result)
        self.assertIsNotNone(error_response.error_message)
        self.assertIn(
            "Échec intentionnel simulé par le ChaoticPlugin.",
            error_response.error_message,
        )

    def test_full_benchmark_suite_execution(self):
        """
        Valide la robustesse et l'exhaustivité du BenchmarkService en exécutant
        une suite de tests complète avec des charges utiles variées.
        Ce test vérifie que toutes les métriques agrégées et les résultats
        individuels sont corrects.
        """
        # 1. Définir une liste de charges utiles variées pour le plugin 'prefixer'
        payloads = [
            {"text": "chaîne normale"},
            {"text": ""},  # Chaîne vide
            {"text": "une chaîne beaucoup plus longue pour tester la variabilité"},
            {"text": "!@#$%^&*()_+-=[]{}|;':,./<>?"},  # Caractères spéciaux
            {"text": "dernier test", "prefix": "special_"},
        ]

        # 2. Utiliser run_suite pour exécuter le benchmark complet
        suite_result = self.benchmark_service.run_suite(
            plugin_name="prefixer", capability_name="add_prefix", requests=payloads
        )

        # 3. Assertions sur le résultat global de la suite (BenchmarkSuiteResult)
        self.assertEqual(suite_result.total_runs, len(payloads))
        self.assertEqual(suite_result.successful_runs, len(payloads))
        self.assertEqual(suite_result.failed_runs, 0)
        self.assertIsInstance(suite_result.average_duration_ms, float)
        self.assertTrue(suite_result.average_duration_ms >= 0)
        self.assertEqual(len(suite_result.results), len(payloads))

        # 4. Assertions sur les résultats individuels
        expected_outputs = [
            "pre_chaîne normale",
            "pre_",
            "pre_une chaîne beaucoup plus longue pour tester la variabilité",
            "pre_!@#$%^&*()_+-=[]{}|;':,./<>?",
            "special_dernier test",
        ]

        for i, result in enumerate(suite_result.results):
            self.assertTrue(result.is_success)
            self.assertIsNone(result.error)
            self.assertIsNotNone(result.output)
            self.assertEqual(result.output.get("processed_text"), expected_outputs[i])


if __name__ == "__main__":
    unittest.main()
