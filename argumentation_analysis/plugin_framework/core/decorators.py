import functools
import tiktoken
from argumentation_analysis.plugin_framework.benchmarking.benchmark_service import (
    BenchmarkService,
)


def track_tokens(benchmark_service: BenchmarkService):
    """
    Décorateur pour suivre la consommation de tokens d'une fonction.

    Ce décorateur inspecte les arguments d'entrée et la valeur de retour
    de la fonction décorée, recherche des chaînes de caractères, les tokenize
    en utilisant l'encodeur 'cl100k_base' de tiktoken, et enregistre le
    nombre de tokens via le BenchmarkService fourni.

    Args:
        benchmark_service: L'instance du service de benchmark à utiliser
                           pour enregistrer les métriques.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            encoding = tiktoken.get_encoding("cl100k_base")

            # Tokenize input
            input_tokens = 0
            # Inspecte les arguments positionnels
            for arg in args:
                if isinstance(arg, str):
                    input_tokens += len(encoding.encode(arg))
                # Si l'argument est un dictionnaire (cas du payload), on cherche des valeurs string
                elif isinstance(arg, dict):
                    for value in arg.values():
                        if isinstance(value, str):
                            input_tokens += len(encoding.encode(value))

            # Inspecte les arguments nommés
            for key, value in kwargs.items():
                if isinstance(value, str):
                    input_tokens += len(encoding.encode(value))
                elif isinstance(value, dict):
                    for v in value.values():
                        if isinstance(v, str):
                            input_tokens += len(encoding.encode(v))

            benchmark_service.record_metric("input_tokens", input_tokens)

            # Exécute la fonction originale
            result = func(*args, **kwargs)

            # Tokenize output
            output_tokens = 0
            if isinstance(result, str):
                output_tokens = len(encoding.encode(result))
            # Si le résultat est un dictionnaire, on cherche des valeurs string
            elif isinstance(result, dict):
                for value in result.values():
                    if isinstance(value, str):
                        output_tokens += len(encoding.encode(value))

            benchmark_service.record_metric("output_tokens", output_tokens)

            return result

        return wrapper

    return decorator
