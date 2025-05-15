"""
Package de données de test pour les outils d'analyse rhétorique.

Ce package contient les jeux de données de test utilisés pour valider
le fonctionnement des outils d'analyse rhétorique améliorés.
"""

from .rhetorical_test_dataset import (
    RHETORICAL_TEST_DATASET,
    PERFORMANCE_TEST_DATASET,
    FALLACY_MAPPING,
    CONTEXT_MAPPING,
    get_test_text,
    get_performance_test_data,
    get_fallacy_info,
    get_context_info
)

__all__ = [
    'RHETORICAL_TEST_DATASET',
    'PERFORMANCE_TEST_DATASET',
    'FALLACY_MAPPING',
    'CONTEXT_MAPPING',
    'get_test_text',
    'get_performance_test_data',
    'get_fallacy_info',
    'get_context_info'
]