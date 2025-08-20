import time
from typing import Callable, Tuple, Any

class BenchmarkService:
    """
    Un service simple pour mesurer les performances de fonctions.
    """
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