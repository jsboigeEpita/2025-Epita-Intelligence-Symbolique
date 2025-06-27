
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires de logging de project_core.
"""
import pytest
import logging
from unittest.mock import MagicMock, patch

import sys # Ajout pour sys.stdout dans le test modifié

from argumentation_analysis.core.utils.logging_utils import setup_logging

# Liste des niveaux de log valides pour les tests paramétrés
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

@pytest.fixture(autouse=True)
def reset_logging_state():
    """
    Fixture pour réinitialiser l'état du logging avant et après chaque test.
    Ceci est crucial car l'état du logging est global.
    """
    # Sauvegarder l'état initial
    original_handlers = logging.root.handlers[:]
    original_level = logging.root.level
    
    # Sauvegarder les niveaux des loggers spécifiques qui sont modifiés
    libraries_to_quiet = ["httpx", "openai", "requests", "urllib3", "semantic_kernel.connectors.ai"]
    project_specific_loggers = ["Orchestration", "semantic_kernel.agents"]
    all_specific_loggers = libraries_to_quiet + project_specific_loggers
    
    original_specific_levels = {name: logging.getLogger(name).level for name in all_specific_loggers}

    yield # Le test s'exécute ici

    # Restaurer l'état initial
    logging.root.handlers = original_handlers
    logging.root.setLevel(original_level)
    for name, level in original_specific_levels.items():
        logging.getLogger(name).setLevel(level)
    
    # S'assurer qu'il n'y a pas de handlers dupliqués si un test échoue avant le nettoyage
    # Cela peut être redondant avec la restauration ci-dessus mais assure une propreté maximale.
    current_handlers = logging.root.handlers[:]
    for handler in current_handlers:
        logging.root.removeHandler(handler)
    # Réappliquer les handlers originaux seulement s'ils ne sont pas déjà là pour éviter les doublons
    # ou s'assurer que la liste est identique à original_handlers.
    # Une manière simple est de vider et de rajouter.
    # (Déjà fait ci-dessus, mais si on veut être exact sur la restauration)
    # current_handlers_after_removal = logging.root.handlers[:] # Devrait être vide
    for handler_orig in original_handlers:
        if handler_orig not in logging.root.handlers: # Évite d'ajouter si déjà restauré par ex.
             logging.root.addHandler(handler_orig)


@pytest.mark.parametrize("level_str", VALID_LOG_LEVELS)
def test_setup_logging_valid_levels(level_str):
    """
    Teste setup_logging avec des niveaux de log valides.
    Vérifie que le niveau du logger racine est correctement défini.
    """
    setup_logging(log_level_str=level_str)
    expected_level = getattr(logging, level_str)
    assert logging.getLogger().getEffectiveLevel() == expected_level, \
        f"Le niveau du logger racine devrait être {level_str}"

def test_setup_logging_invalid_level_defaults_to_info(caplog):
    """
    Teste setup_logging avec un niveau de log invalide.
    Vérifie qu'un avertissement est loggué et que le niveau par défaut (INFO) est utilisé.
    """
    with caplog.at_level(logging.WARNING): # Capturer les logs de niveau WARNING et plus
        setup_logging(log_level_str="INVALID_LEVEL")
    
    assert logging.getLogger().getEffectiveLevel() == logging.INFO, \
        "Le niveau du logger racine devrait être INFO par défaut pour un niveau invalide."
    
    assert "Niveau de log invalide: INVALID_LEVEL. Utilisation du niveau INFO par défaut." in caplog.text, \
        "Un avertissement pour niveau invalide aurait dû être loggué."

@patch('logging.StreamHandler')
def test_setup_logging_configures_handler_and_formatter(mock_stream_handler_class, caplog):
    """
    Teste que setup_logging configure correctement le StreamHandler et le formateur.
    """
    # Créer une instance mock pour le handler qui sera retournée par la classe mockée
    mock_handler_instance = MagicMock()
    mock_stream_handler_class.return_value = mock_handler_instance

    # S'assurer que le handler mocké a un attribut 'level' de type int,
    # car la bibliothèque logging le compare avec record.levelno (int).
    # Le niveau du handler sera configuré par basicConfig au niveau du logger racine.
    mock_handler_instance.level = logging.DEBUG # Correspond au log_level_str passé à setup_logging
    # S'assurer que basicConfig tentera de définir un formateur
    mock_handler_instance.formatter = None 

    setup_logging(log_level_str="DEBUG")
    
    # Vérifier que StreamHandler a été instancié (avec sys.stdout)
    mock_stream_handler_class.assert_called_once_with(sys.stdout)

    # Vérifier que le handler a été ajouté au logger racine
    assert mock_handler_instance in logging.getLogger().handlers, \
        "L'instance mockée du StreamHandler aurait dû être ajoutée au logger racine."
    
    # Vérifier que setFormatter a été appelé sur le handler mocké
    mock_handler_instance.setFormatter.assert_called_once()
    
    formatter_arg = mock_handler_instance.setFormatter.call_args[0][0]
    assert isinstance(formatter_arg, logging.Formatter), "L'argument de setFormatter devrait être un logging.Formatter"
    
    expected_format_str = '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
    expected_date_fmt_str = '%H:%M:%S'

    actual_format_str = formatter_arg._style._fmt if hasattr(formatter_arg, '_style') else formatter_arg._fmt
    
    assert actual_format_str == expected_format_str, \
        f"Le format du formateur est incorrect. Attendu: '{expected_format_str}', Obtenu: '{actual_format_str}'"
    assert formatter_arg.datefmt == expected_date_fmt_str, \
        f"Le format de date du formateur est incorrect. Attendu: '{expected_date_fmt_str}', Obtenu: '{formatter_arg.datefmt}'"


def test_setup_logging_quiets_third_party_libraries():
    """
    Teste que setup_logging réduit la verbosité des bibliothèques tierces spécifiées.
    Leur niveau doit être WARNING.
    """
    setup_logging(log_level_str="DEBUG") # Niveau global DEBUG
    
    libraries_to_quiet = ["httpx", "openai", "requests", "urllib3", "semantic_kernel.connectors.ai"]
    for lib_name in libraries_to_quiet:
        assert logging.getLogger(lib_name).getEffectiveLevel() == logging.WARNING, \
            f"Le logger de la bibliothèque '{lib_name}' devrait être à WARNING."

def test_setup_logging_project_specific_loggers_inherit_level():
    """
    Teste que les loggers spécifiques au projet héritent du niveau de log global.
    """
    setup_logging(log_level_str="DEBUG")
    project_specific_loggers = ["Orchestration", "semantic_kernel.agents"]
    for logger_name in project_specific_loggers:
        assert logging.getLogger(logger_name).getEffectiveLevel() == logging.DEBUG, \
            f"Le logger spécifique au projet '{logger_name}' devrait hériter du niveau DEBUG."

    # Changer le niveau global et revérifier
    setup_logging(log_level_str="ERROR")
    for logger_name in project_specific_loggers:
        assert logging.getLogger(logger_name).getEffectiveLevel() == logging.ERROR, \
            f"Le logger spécifique au projet '{logger_name}' devrait hériter du niveau ERROR."


def test_setup_logging_removes_existing_handlers(): # mocker n'est plus nécessaire ici
    """
    Teste que setup_logging (avec force=True dans basicConfig) supprime les handlers 
    existants du logger racine avant d'en configurer de nouveaux.
    """
    root_logger = logging.getLogger()

    # 1. Nettoyer tous les handlers existants pour un état de départ propre
    while root_logger.handlers:
        root_logger.removeHandler(root_logger.handlers[0])
    assert not root_logger.handlers, "Le logger racine devrait être sans handlers au début du test."

    # 2. Ajouter un handler factice
    dummy_handler = logging.StreamHandler(sys.stderr) # Utiliser stderr pour le distinguer
    dummy_handler.set_name("dummy_handler_for_test")
    root_logger.addHandler(dummy_handler)
    assert dummy_handler in root_logger.handlers, "Le handler factice devrait être présent."
    assert len(root_logger.handlers) == 1, "Il ne devrait y avoir que le dummy_handler."

    # 3. Appeler setup_logging
    setup_logging("INFO") # Utilise basicConfig(force=True)

    # 4. Vérifier l'état des handlers
    # Le dummy_handler devrait avoir été retiré par force=True
    assert dummy_handler not in root_logger.handlers, \
        "Le handler factice initial aurait dû être retiré par basicConfig(force=True)."
    
    # Il devrait y avoir au moins un handler (celui configuré par basicConfig)
    assert len(root_logger.handlers) >= 1, \
        "Le logger racine devrait avoir au moins un handler après setup_logging."
        
    # Vérifier que le nouveau handler est un StreamHandler pointant vers sys.stdout
    found_new_handler = False
    for h in root_logger.handlers:
        if isinstance(h, logging.StreamHandler) and getattr(h, 'stream', None) == sys.stdout:
            found_new_handler = True
            break
    assert found_new_handler, \
        "Un nouveau StreamHandler pointant vers sys.stdout aurait dû être ajouté par basicConfig."

    # Nettoyage final (la fixture autouse s'en charge aussi, mais pour être sûr)
    while root_logger.handlers:
        root_logger.removeHandler(root_logger.handlers[0])