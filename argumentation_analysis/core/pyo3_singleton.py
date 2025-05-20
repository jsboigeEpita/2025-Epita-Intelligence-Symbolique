"""
Module de gestion des singletons pour les modules PyO3.

Ce module fournit un mécanisme pour initialiser et accéder aux modules PyO3
de manière à ce qu'ils ne soient chargés qu'une seule fois, évitant ainsi
les problèmes de multiples initialisations.
"""

import logging
import importlib
import sys
from typing import Dict, Any, Optional, Callable

# Configuration du logger
logger = logging.getLogger("Orchestration.PyO3")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Dictionnaire pour stocker les instances de modules PyO3
_pyo3_modules: Dict[str, Any] = {}
_initialized: bool = False

def initialize_pyo3() -> bool:
    """
    Initialise l'environnement PyO3 global.
    
    Cette fonction doit être appelée avant d'utiliser des modules PyO3.
    Elle configure l'environnement nécessaire pour tous les modules PyO3.
    
    Returns:
        bool: True si l'initialisation a réussi, False sinon.
    """
    global _initialized
    
    if _initialized:
        logger.info("Environnement PyO3 déjà initialisé.")
        return True
    
    try:
        logger.info("Initialisation de l'environnement PyO3...")
        # Ici, vous pouvez ajouter du code pour initialiser l'environnement PyO3 global
        # Par exemple, configurer des chemins, des variables d'environnement, etc.
        
        _initialized = True
        logger.info("✅ Environnement PyO3 initialisé avec succès.")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation de l'environnement PyO3: {e}", exc_info=True)
        return False

def get_pyo3_module(module_name: str, init_func: Optional[Callable] = None) -> Optional[Any]:
    """
    Récupère une instance d'un module PyO3, en l'initialisant si nécessaire.
    
    Cette fonction implémente le pattern singleton pour les modules PyO3.
    Si le module a déjà été chargé, elle retourne l'instance existante.
    Sinon, elle tente de charger le module et de l'initialiser.
    
    Args:
        module_name (str): Nom du module PyO3 à charger.
        init_func (Callable, optional): Fonction d'initialisation à appeler après le chargement du module.
    
    Returns:
        Optional[Any]: L'instance du module PyO3, ou None en cas d'erreur.
    """
    global _pyo3_modules
    
    # Vérifier si le module est déjà chargé
    if module_name in _pyo3_modules:
        logger.debug(f"Module PyO3 '{module_name}' déjà chargé, réutilisation de l'instance existante.")
        return _pyo3_modules[module_name]
    
    # S'assurer que l'environnement PyO3 est initialisé
    if not _initialized and not initialize_pyo3():
        logger.error(f"❌ Impossible de charger le module PyO3 '{module_name}' car l'environnement PyO3 n'est pas initialisé.")
        return None
    
    # Tenter de charger le module
    try:
        logger.info(f"Chargement du module PyO3 '{module_name}'...")
        module = importlib.import_module(module_name)
        
        # Appeler la fonction d'initialisation si fournie
        if init_func is not None:
            logger.debug(f"Initialisation du module PyO3 '{module_name}'...")
            init_func(module)
        
        # Stocker l'instance dans le dictionnaire
        _pyo3_modules[module_name] = module
        logger.info(f"✅ Module PyO3 '{module_name}' chargé avec succès.")
        return module
    except ImportError as e:
        logger.error(f"❌ Erreur lors du chargement du module PyO3 '{module_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors du chargement du module PyO3 '{module_name}': {e}", exc_info=True)
        return None

def unload_pyo3_module(module_name: str) -> bool:
    """
    Décharge un module PyO3 précédemment chargé.
    
    Cette fonction est utile pour les tests ou pour libérer des ressources.
    
    Args:
        module_name (str): Nom du module PyO3 à décharger.
    
    Returns:
        bool: True si le module a été déchargé avec succès, False sinon.
    """
    global _pyo3_modules
    
    if module_name not in _pyo3_modules:
        logger.warning(f"Module PyO3 '{module_name}' non chargé, impossible de le décharger.")
        return False
    
    try:
        # Supprimer le module du dictionnaire
        del _pyo3_modules[module_name]
        
        # Supprimer le module de sys.modules si présent
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        logger.info(f"✅ Module PyO3 '{module_name}' déchargé avec succès.")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors du déchargement du module PyO3 '{module_name}': {e}", exc_info=True)
        return False

def reset_pyo3_environment() -> bool:
    """
    Réinitialise complètement l'environnement PyO3.
    
    Cette fonction décharge tous les modules PyO3 et réinitialise l'état du singleton.
    Utile pour les tests ou pour réinitialiser l'environnement après une erreur.
    
    Returns:
        bool: True si la réinitialisation a réussi, False sinon.
    """
    global _pyo3_modules, _initialized
    
    try:
        # Décharger tous les modules
        for module_name in list(_pyo3_modules.keys()):
            unload_pyo3_module(module_name)
        
        # Réinitialiser l'état
        _pyo3_modules = {}
        _initialized = False
        
        logger.info("✅ Environnement PyO3 réinitialisé avec succès.")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur lors de la réinitialisation de l'environnement PyO3: {e}", exc_info=True)
        return False

# Exemple d'utilisation:
# from argumentation_analysis.core.pyo3_singleton import get_pyo3_module
# my_rust_module = get_pyo3_module("my_rust_module")
# if my_rust_module:
#     result = my_rust_module.some_function()