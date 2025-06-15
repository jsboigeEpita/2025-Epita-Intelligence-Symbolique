#!/usr/bin/env python3
"""
Performance Monitoring Utilities

Ce module fournit des outils pour monitorer la performance des fonctions critiques,
notamment via des décorateurs et des gestionnaires de contexte.
"""

import time
import logging
import json
from functools import wraps
import os

# Configuration du logger pour la performance
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, "oracle_performance.log")

# Crée un logger spécifique pour la performance
performance_logger = logging.getLogger("performance_monitor")
performance_logger.setLevel(logging.INFO)

# Empêche la propagation des logs au logger root pour éviter les doublons
performance_logger.propagate = False

# Handler pour écrire dans le fichier de log de performance
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)

# Formatter pour le log structuré en JSON
formatter = logging.Formatter('{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "function": "%(funcName)s", "message": %(message)s}')
file_handler.setFormatter(formatter)

# Ajoute le handler uniquement si aucun n'est déjà configuré
if not performance_logger.handlers:
    performance_logger.addHandler(file_handler)

def monitor_performance(log_args: bool = False):
    """
    Décorateur pour mesurer et logger le temps d'exécution d'une fonction.

    Args:
        log_args (bool): Si True, loggue les arguments de la fonction.
                         À utiliser avec prudence pour ne pas exposer de données sensibles.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                
                log_data = {
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "function_name": func.__qualname__
                }

                if log_args:
                    # Conversion prudente des arguments en string
                    try:
                        args_repr = [repr(a) for a in args]
                        kwargs_repr = {k: repr(v) for k, v in kwargs.items()}
                        log_data["arguments"] = {"args": args_repr, "kwargs": kwargs_repr}
                    except Exception:
                        log_data["arguments"] = "Could not serialize arguments"

                performance_logger.info(json.dumps(log_data))
        return wrapper
    return decorator