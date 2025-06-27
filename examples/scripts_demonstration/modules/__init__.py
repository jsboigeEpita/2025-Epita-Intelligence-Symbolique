"""
Modules de démonstration EPITA - Intelligence Symbolique
=======================================================

Ce package contient tous les modules de démonstration pour la validation 
complète du système d'intelligence symbolique EPITA.

Modules disponibles :
- custom_data_processor : Traitement de données personnalisées
- demo_agents_logiques : Démonstrations des agents logiques
- demo_cas_usage : Cas d'usage pratiques
- demo_integrations : Intégrations système  
- demo_outils_utils : Outils et utilitaires
- demo_services_core : Services core du système
- demo_tests_validation : Validation et tests
- demo_utils : Utilitaires de démonstration
- test_elimination_mocks_validation : Tests d'élimination des mocks
- test_final_validation_ascii : Validation finale ASCII
"""

__version__ = "2.0.0"
__author__ = "EPITA Intelligence Symbolique"

# Liste des modules disponibles (import à la demande pour éviter les problèmes circulaires)
__all__ = [
    'custom_data_processor',
    'demo_agents_logiques',
    'demo_cas_usage',
    'demo_integrations',
    'demo_outils_utils',
    'demo_services_core',
    'demo_tests_validation',
    'demo_utils',
    'test_elimination_mocks_validation',
    'test_final_validation_ascii'
]

# Import des modules principaux de façon sécurisée
def _safe_import(module_name):
    """Import sécurisé d'un module"""
    try:
        return __import__(f'modules.{module_name}', fromlist=[module_name])
    except ImportError:
        return None

def get_available_demos():
    """
    Retourne la liste des démonstrations disponibles
    """
    return __all__

def validate_all_modules():
    """
    Valide que tous les modules peuvent être importés
    """
    results = {}
    for module_name in __all__:
        try:
            __import__(f'modules.{module_name}', fromlist=[module_name])
            results[module_name] = True
        except Exception as e:
            results[module_name] = False
            print(f"Erreur import {module_name}: {e}")
    
    return results