import time
from typing import List, Dict, Any
from argumentation_analysis.plugin_framework.core.contracts import BenchmarkResult, BenchmarkSuiteResult
from argumentation_analysis.plugin_framework.core.services.orchestration_service import (
    OrchestrationService,
)
from argumentation_analysis.plugin_framework.core.contracts import OrchestrationRequest


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
        self.custom_metrics: Dict[str, List[Any]] = {}

    def record_metric(self, metric_type: str, value: Any):
        """
        Enregistre une métrique personnalisée pendant l'exécution d'un benchmark.
        Les métriques sont stockées temporairement et associées à la prochaine
        exécution de `run_suite`.

        Args:
            metric_type: Le nom de la métrique (ex: 'input_tokens').
            value: La valeur de la métrique.
        """
        if metric_type not in self.custom_metrics:
            self.custom_metrics[metric_type] = []
        self.custom_metrics[metric_type].append(value)

    def _clear_metrics(self):
        """Réinitialise les métriques personnalisées."""
        self.custom_metrics = {}

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
        self._clear_metrics()
        individual_results: List[BenchmarkResult] = []
        successful_durations: List[float] = []

        target = f"{plugin_name}.{capability_name}"

        for i, request_payload in enumerate(requests):
            request = OrchestrationRequest(
                mode="direct_plugin_call",
                target=target,
                payload=request_payload,
                session_id=None,
            )

            start_time = time.perf_counter()
            response = self.orchestration_service.handle_request(request)
            end_time = time.perf_counter()

            duration_ms = (end_time - start_time) * 1000
            is_success = response.status == "success"

            if is_success:
                successful_durations.append(duration_ms)

            # Associer les métriques enregistrées à ce résultat
            run_metrics = {}
            for key, values in self.custom_metrics.items():
                if i < len(values):
                    run_metrics[key] = values[i]

            result = BenchmarkResult(
                request_id=f"benchmark-run-{len(individual_results) + 1}",
                is_success=is_success,
                duration_ms=duration_ms,
                output=response.result,
                error=response.error_message,
                custom_metrics=run_metrics,
            )
            individual_results.append(result)

        total_runs = len(requests)
        successful_runs = len(successful_durations)
        failed_runs = total_runs - successful_runs

        avg_duration = (
            sum(successful_durations) / successful_runs if successful_runs > 0 else 0
        )
        min_duration = min(successful_durations) if successful_runs > 0 else 0
        max_duration = max(successful_durations) if successful_runs > 0 else 0
        total_duration = sum(r.duration_ms for r in individual_results)

        # Agréger les métriques personnalisées
        aggregated_metrics: Dict[str, Any] = {}
        for res in individual_results:
            for key, value in res.custom_metrics.items():
                if key not in aggregated_metrics:
                    aggregated_metrics[key] = []
                aggregated_metrics[key].append(value)

        # Calculer la somme pour les métriques numériques
        for key, values in aggregated_metrics.items():
            if all(isinstance(v, (int, float)) for v in values):
                aggregated_metrics[key] = sum(values)

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
            aggregated_custom_metrics=aggregated_metrics,
        )
