import time
from typing import Callable, Tuple, Any

class BenchmarkService:
    """
    Service pour mesurer et enregistrer des métriques de performance détaillées.

    Ce service permet de mesurer la latence d'exécutions de fonctions et
    d'enregistrer diverses métriques (succès, échecs, valeurs custom)
    dans une structure de données interne pour une analyse ultérieure.
    """
    def __init__(self):
        """
        Initialise le service de benchmark.
        """
        self.metrics = {}

    def record_metric(self, function_name: str, success: bool, value: float, metric_type: str):
        """
        Enregistre une métrique de performance détaillée.

        Args:
            function_name: Le nom de la fonction ou de l'opération mesurée.
            success: Un booléen indiquant si l'opération a réussi.
            value: La valeur numérique de la métrique (ex: latence, nombre d'erreurs).
            metric_type: Le type de métrique (ex: 'latency', 'error_count').
        """
        if function_name not in self.metrics:
            self.metrics[function_name] = []
        
        self.metrics[function_name].append({
            "success": success,
            "value": value,
            "metric_type": metric_type,
            "timestamp": time.time()
        })

    def measure_latency(self, func: Callable, *args, **kwargs) -> Tuple[Any, float]:
        """
        Mesure le temps d'exécution (latence) d'une fonction.
        Args:
            func: La fonction à exécuter.
            *args: Les arguments positionnels pour la fonction.
            **kwargs: Les arguments nommés pour la fonction.
        Returns:
            Un tuple contenant le résultat de la fonction et la latence en secondes.
        """
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        latency = end_time - start_time
        return result, latency