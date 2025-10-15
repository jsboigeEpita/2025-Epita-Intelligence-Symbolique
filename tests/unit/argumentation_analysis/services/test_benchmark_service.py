import time
import pytest
from unittest.mock import patch
from argumentation_analysis.services.benchmark_service import BenchmarkService

# Durée de la pause pour la fonction factice (en secondes)
SLEEP_DURATION = 0.1


def dummy_function():
    """Une fonction simple qui attend une durée fixe."""
    time.sleep(SLEEP_DURATION)
    return "done"


@patch("time.sleep", return_value=None)
@patch("time.perf_counter", side_effect=[1000.0, 1000.0 + SLEEP_DURATION])
def test_measure_latency_records_correct_time(mock_perf_counter, mock_sleep):
    """
    Vérifie que BenchmarkService.measure_latency mesure et enregistre
    correctement le temps d'exécution d'une fonction, en utilisant des mocks
    pour stabiliser le test.
    """
    # 1. Arrange
    benchmark_service = BenchmarkService()

    # 2. Act
    result, latency = benchmark_service.measure_latency(dummy_function)

    # 3. Assert
    assert result == "done"
    mock_sleep.assert_called_once_with(SLEEP_DURATION)
    # Vérifie que la latence calculée correspond exactement à la durée simulée
    assert latency == pytest.approx(SLEEP_DURATION)


def test_record_metrics():
    """
    Vérifie que le BenchmarkService enregistre correctement différentes métriques.
    """
    # 1. Arrange
    benchmark_service = BenchmarkService()
    function_name = "test_function"

    # 2. Act
    benchmark_service.record_metric(
        function_name, success=True, value=0.123, metric_type="latency"
    )
    benchmark_service.record_metric(
        function_name, success=True, value=0.125, metric_type="latency"
    )
    benchmark_service.record_metric(
        function_name, success=False, value=1, metric_type="error_count"
    )

    # 3. Assert
    assert function_name in benchmark_service.metrics
    metrics_list = benchmark_service.metrics[function_name]

    assert len(metrics_list) == 3

    # Vérification de la première métrique de latence
    assert metrics_list[0]["success"] is True
    assert metrics_list[0]["value"] == 0.123
    assert metrics_list[0]["metric_type"] == "latency"

    # Vérification de la deuxième métrique de latence
    assert metrics_list[1]["success"] is True
    assert metrics_list[1]["value"] == 0.125
    assert metrics_list[1]["metric_type"] == "latency"

    # Vérification de la métrique d'erreur
    assert metrics_list[2]["success"] is False
    assert metrics_list[2]["value"] == 1
    assert metrics_list[2]["metric_type"] == "error_count"
