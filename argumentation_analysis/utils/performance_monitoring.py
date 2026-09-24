#!/usr/bin/env python3
"""
Performance Monitoring Utilities

Ce module fournit des outils pour monitorer la performance des fonctions critiques,
notamment via des décorateurs et des gestionnaires de contexte.
"""

import inspect
import time
import logging
import json
from functools import wraps
import os

# Logger de performance : il n'écrit que dans son fichier, jamais vers le root.
performance_logger = logging.getLogger("performance_monitor")
performance_logger.setLevel(logging.INFO)
performance_logger.propagate = False

log_dir = "logs"
log_file = os.path.join(log_dir, "oracle_performance.log")


def _ensure_file_handler():
    """Ouvre ``logs/oracle_performance.log`` à la première mesure.

    Le faire à l'import créait ``logs/`` dans le répertoire courant de tout
    processus qui importait ``argumentation_analysis.utils`` (#2346). Comme
    avant, un logger qui a déjà un handler est laissé tel quel.
    """
    if performance_logger.handlers:
        return
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    # Formatter pour le log structuré en JSON
    file_handler.setFormatter(
        logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "function": "%(funcName)s", "message": %(message)s}'
        )
    )
    performance_logger.addHandler(file_handler)


def monitor_performance(log_args: bool = False):
    """
    Décorateur pour mesurer et logger le temps d'exécution d'une fonction.

    Args:
        log_args (bool): Si True, loggue les arguments de la fonction.
                         À utiliser avec prudence pour ne pas exposer de données sensibles.
    """

    def _emit(func, start_time, args, kwargs):
        execution_time = time.perf_counter() - start_time

        log_data = {
            "execution_time_ms": round(execution_time * 1000, 2),
            "function_name": func.__qualname__,
        }

        if log_args:
            # Conversion prudente des arguments en string
            try:
                args_repr = [repr(a) for a in args]
                kwargs_repr = {k: repr(v) for k, v in kwargs.items()}
                log_data["arguments"] = {
                    "args": args_repr,
                    "kwargs": kwargs_repr,
                }
            except Exception:
                log_data["arguments"] = "Could not serialize arguments"

        _ensure_file_handler()
        performance_logger.info(json.dumps(log_data))

    def decorator(func):
        if inspect.iscoroutinefunction(func):
            # Sans cette branche, le wrapper synchrone mesurerait la *création*
            # de la coroutine (~0 ms) au lieu de son exécution, et
            # `inspect.iscoroutinefunction` répondrait False sur la fonction
            # décorée (#2340).
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    _emit(func, start_time, args, kwargs)

            return async_wrapper

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                _emit(func, start_time, args, kwargs)

        return wrapper

    return decorator
