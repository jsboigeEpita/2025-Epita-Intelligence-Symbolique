import time
from typing import List, Dict, Any
from src.core.contracts import BenchmarkResult, BenchmarkSuiteResult
from src.core.services.orchestration_service import OrchestrationService, OrchestrationRequest

class BenchmarkService:
    """
    Le cœur logique du framework de benchmarking.
    Prend en charge l'exécution de suites de tests pour les capacités des plugins
    et la collecte de métriques de performance.
    """

    def __init__(self, orchestration_service: OrchestrationService):
        """
        Initialise le service avec une instance du service d'orchestration.

        Args:
            orchestration_service: Le service qui gère l'exécution des plugins.
        """
        self.orchestration_service = orchestration_service

    def run_suite(
        self,
        plugin_name: str,
        capability_name: str,
        requests: List[Dict[str, Any]],
    ) -> BenchmarkSuiteResult:
        """
        Exécute une suite de tests pour une capacité de plugin spécifique.

        Args:
            plugin_name: Le nom du plugin à tester.
            capability_name: Le nom de la capacité à invoquer.
            requests: Une liste de dictionnaires, chaque dictionnaire contenant
                      le 'payload' pour une exécution.

        Returns:
            Un objet BenchmarkSuiteResult avec les résultats agrégés.
        """
        individual_results: List[BenchmarkResult] = []
        successful_durations: List[float] = []
        
        # Le plan spécifie un target au format "plugin_name.capability_name"
        # mais la méthode `run_suite` reçoit ces deux informations séparément.
        # Pour le moment, nous les utilisons comme prévu par la signature de la méthode.
        target = f"{plugin_name}.{capability_name}"

        for request_payload in requests:
            # Création de la requête d'orchestration
            request = OrchestrationRequest(
                mode="direct_plugin_call", # Le mode est fixé pour le benchmark
                target=target,
                payload=request_payload,
                session_id=None # Pas de gestion de session pour ce benchmark
            )
            
            start_time = time.perf_counter()
            response = self.orchestration_service.handle_request(request)
            end_time = time.perf_counter()

            duration_ms = (end_time - start_time) * 1000
            is_success = response.status == "success"

            if is_success:
                successful_durations.append(duration_ms)

            result = BenchmarkResult(
                request_id=f"benchmark-run-{len(individual_results) + 1}", # ID de requête temporaire
                is_success=is_success,
                duration_ms=duration_ms,
                output=response.result,
                error=response.error_message,
            )
            individual_results.append(result)
        
        # Calcul des statistiques agrégées
        total_runs = len(requests)
        successful_runs = len(successful_durations)
        failed_runs = total_runs - successful_runs
        
        # Eviter la division par zéro si aucune exécution n'a réussi
        avg_duration = sum(successful_durations) / successful_runs if successful_runs > 0 else 0
        min_duration = min(successful_durations) if successful_runs > 0 else 0
        max_duration = max(successful_durations) if successful_runs > 0 else 0
        total_duration = sum(r.duration_ms for r in individual_results)

        return BenchmarkSuiteResult(
            plugin_name=plugin_name,
            capability_name=capability_name,
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            total_duration_ms=total_duration,
            average_duration_ms=avg_duration,
            min_duration_ms=min_duration,
            max_duration_ms=max_duration,
            results=individual_results,
        )