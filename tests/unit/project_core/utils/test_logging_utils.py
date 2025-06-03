# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires de logging de project_core.
"""
import pytest
import logging
from unittest.mock import patch, MagicMock

from project_core.utils.logging_utils import setup_logging

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
    for handler in original_handlers: # Réappliquer les handlers originaux
        logging.root.addHandler(handler)


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

@patch('logging.StreamHandler') # Mocker StreamHandler pour vérifier son utilisation
def test_setup_logging_configures_handler_and_formatter(mock_stream_handler_class, caplog):
    """
    Teste que setup_logging configure correctement le StreamHandler et le formateur.
    """
    # Créer une instance mock pour le handler qui sera retournée par la classe mockée
    mock_handler_instance = MagicMock()
    mock_stream_handler_class.return_value = mock_handler_instance

    setup_logging(log_level_str="DEBUG")
    
    # Vérifier que StreamHandler a été instancié (avec sys.stdout)
    # Note: sys.stdout est l'argument par défaut, donc on peut juste vérifier l'appel
    mock_stream_handler_class.assert_called_once() 
    # On pourrait être plus précis si on mockait sys.stdout:
    # mock_stream_handler_class.assert_called_once_with(sys.stdout)

    # Vérifier que le handler a été ajouté au logger racine
    # logging.basicConfig ajoute le handler, donc on vérifie que le root logger a des handlers
    # et que notre mock_handler_instance (ou un handler de type StreamHandler) en fait partie.
    # C'est un peu indirect car basicConfig fait le travail.
    # On peut vérifier que le root logger a au moins un handler.
    assert len(logging.getLogger().handlers) > 0, "Le logger racine devrait avoir au moins un handler."
    
    # Vérifier le formateur en logguant un message et en inspectant le format du caplog
    # C'est un test plus d'intégration pour le format.
    # Le format est '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
    # La date est '%H:%M:%S'
    with caplog.at_level(logging.INFO):
        logging.getLogger("test_logger").info("Test message for format.")
    
    assert len(caplog.records) == 1
    log_record = caplog.records[0]
    
    # Exemple de vérification du format (peut être fragile si le format exact change)
    # On s'attend à quelque chose comme "12:34:56 [INFO] [test_logger] Test message for format."
    # On peut utiliser des regex pour plus de flexibilité.
    import re
    # Regex pour HH:MM:SS [LEVEL] [LOGGER_NAME] Message
    log_pattern = re.compile(r"^\d{2}:\d{2}:\d{2} \[INFO\] \[test_logger\] Test message for format\.$")
    # Note: Le format de l'heure dépend de l'exécution, donc on ne peut pas le fixer.
    # On vérifie la structure générale.
    # Le message loggué par setup_logging lui-même sera aussi capturé si le niveau est INFO.
    # On se concentre sur le message que l'on vient de logger.
    
    # Le message de setup_logging est "Logging configuré avec le niveau DEBUG."
    # Le message de notre test est "Test message for format."
    # On cherche le dernier message qui correspond à notre test.
    
    found_test_message = False
    for record in caplog.records:
        if record.name == "test_logger" and record.message == "Test message for format.":
            # Le format du message est appliqué par le handler au moment de l'émission.
            # caplog.text contient les messages formatés.
            # On cherche notre message formaté dans caplog.text
            formatted_message_found = any(
                log_pattern.match(line) for line in caplog.text.splitlines() if "Test message for format." in line
            )
            assert formatted_message_found, "Le format du message de log ne correspond pas à l'attendu."
            found_test_message = True
            break
    assert found_test_message, "Le message de test spécifique n'a pas été trouvé dans les logs."


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


def test_setup_logging_removes_existing_handlers(mocker):
    """
    Teste que setup_logging supprime les handlers existants du logger racine
    avant d'en configurer de nouveaux, pour éviter la duplication de logs.
    """
    root_logger = logging.getLogger()
    
    # Ajouter un handler factice
    dummy_handler = logging.StreamHandler()
    root_logger.addHandler(dummy_handler)
    assert dummy_handler in root_logger.handlers, "Le handler factice devrait être dans les handlers du root."
    
    # Mocker logging.basicConfig pour ne pas ajouter de nouveaux handlers pendant ce test spécifique
    # et se concentrer sur la suppression.
    # Cependant, setup_logging utilise basicConfig qui gère les handlers.
    # On va plutôt vérifier le nombre de handlers avant et après, et leur type.
    
    # On espère que setup_logging va enlever dummy_handler et ajouter son propre StreamHandler.
    # Pour isoler la suppression, on peut mocker `root_logger.removeHandler`.
    mock_remove_handler = mocker.patch.object(root_logger, 'removeHandler')
    mock_has_handlers = mocker.patch.object(root_logger, 'hasHandlers', return_value=True)
    # Simuler que root_logger.handlers contient notre dummy_handler
    # Ceci est un peu délicat car on modifie l'état interne de logging.
    # Une approche plus propre est de laisser setup_logging s'exécuter et de vérifier l'état après.

    # Réinitialiser le logger racine à un état plus contrôlé pour ce test.
    # Enlever tous les handlers potentiels ajoutés par d'autres tests ou la config pytest.
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    
    # Ajouter notre handler factice
    root_logger.addHandler(dummy_handler)
    initial_handler_count = len(root_logger.handlers)
    assert initial_handler_count == 1, "Devrait y avoir 1 handler initialement."
    
    setup_logging("INFO") # Exécuter la fonction à tester
    
    # Après setup_logging, dummy_handler devrait avoir été retiré,
    # et un nouveau StreamHandler (celui de basicConfig) ajouté.
    # Le nombre de handlers devrait toujours être 1 (celui de basicConfig).
    # Et ce handler ne devrait pas être notre dummy_handler.
    
    final_handlers = root_logger.handlers
    assert len(final_handlers) == 1, "Devrait y avoir 1 handler après setup_logging."
    assert dummy_handler not in final_handlers, "Le handler factice initial aurait dû être retiré."
    assert isinstance(final_handlers[0], logging.StreamHandler), "Le handler final devrait être un StreamHandler."

    # Nettoyage explicite pour ce test si la fixture autouse ne suffit pas
    # (normalement, elle devrait suffire).
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)