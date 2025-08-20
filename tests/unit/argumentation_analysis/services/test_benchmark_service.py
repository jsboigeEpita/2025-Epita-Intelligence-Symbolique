import time
import pytest
from argumentation_analysis.services.benchmark_service import BenchmarkService

# Durée de la pause pour la fonction factice (en secondes)
SLEEP_DURATION = 0.1

def dummy_function():
    """Une fonction simple qui attend une durée fixe."""
    time.sleep(SLEEP_DURATION)
    return "done"

def test_measure_latency_records_correct_time():
    """
    Vérifie que BenchmarkService.measure_latency mesure et enregistre
    correctement le temps d'exécution d'une fonction.
    """
    # 1. Arrange
    benchmark_service = BenchmarkService()
    
    # 2. Act
    result, latency = benchmark_service.measure_latency(dummy_function)
    
    # 3. Assert
    assert result == "done"
    # Vérifie que la latence est dans une marge de tolérance raisonnable
    # (par exemple, 50% de la durée attendue)
    assert latency >= SLEEP_DURATION
    assert latency < SLEEP_DURATION * 1.5 