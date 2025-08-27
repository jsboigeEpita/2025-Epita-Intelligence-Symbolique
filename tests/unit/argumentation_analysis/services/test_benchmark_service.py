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

@patch('time.sleep', return_value=None)
@patch('time.perf_counter', side_effect=[1000.0, 1000.0 + SLEEP_DURATION])
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