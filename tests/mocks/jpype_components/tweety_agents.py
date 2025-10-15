# tests/mocks/jpype_components/tweety_agents.py
"""
Ce module gère la configuration des mocks pour les classes d'agents Tweety.
"""
import logging
import sys
from unittest.mock import MagicMock
import typing

# Importation relative pour MockJClassCore et potentiellement d'autres utilitaires
if typing.TYPE_CHECKING:
    from .jclass_core import (
        MockJClassCore,
    )  # Pour les type hints, évite l'import circulaire au runtime

# Logger spécifique pour ce module
tweety_agents_logger = logging.getLogger(__name__)
if not tweety_agents_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[MOCK TWEETY AGENTS LOG] %(asctime)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    tweety_agents_logger.addHandler(handler)
tweety_agents_logger.setLevel(logging.INFO)  # Ou logging.DEBUG pour plus de détails

tweety_agents_logger.info("tweety_agents.py mock component loading.")

# Dictionnaire pour stocker les configurations spécifiques des classes d'agents
# Clé: nom complet de la classe Java (ex: "org.tweetyproject.agents.ArgumentationAgent")
# Valeur: une fonction qui configure l'instance MockJClassCore
_agent_class_configs = {}


def configure_tweety_agent_class(jclass_core_instance: "MockJClassCore"):
    """
    Configure une instance MockJClassCore pour une classe d'agent Tweety spécifique.
    Cette fonction est appelée par MockJClassCore lors de l'instanciation d'une classe
    qui correspond à un agent connu.
    """
    class_name = jclass_core_instance.class_name
    tweety_agents_logger.debug(f"Attempting to configure agent class: {class_name}")

    if class_name in _agent_class_configs:
        config_func = _agent_class_configs[class_name]
        tweety_agents_logger.info(
            f"Applying specific configuration for agent class: {class_name}"
        )
        config_func(jclass_core_instance)
    else:
        tweety_agents_logger.debug(
            f"No specific agent configuration found for {class_name}. Applying default mock behavior."
        )
        # Comportement par défaut si aucune configuration spécifique n'est trouvée
        # Peut-être juste un MagicMock pour tous les attributs non définis.
        # MockJClassCore gère déjà un comportement de mock par défaut.


# --- Fonctions de configuration spécifiques pour chaque classe d'agent ---
# Exemple pour ArgumentationAgent (à adapter/compléter)
def _configure_ArgumentationAgent(jclass_instance: "MockJClassCore"):
    """Configure le mock pour org.tweetyproject.agents.ArgumentationAgent."""
    tweety_agents_logger.debug(
        f"Configuring MockJClassCore for ArgumentationAgent: {jclass_instance.class_name}"
    )
    # Exemple: mocker une méthode spécifique
    # jclass_instance.someMethod = MagicMock(return_value="mocked_value_from_agent")

    # Si ArgumentationAgent a des constructeurs spécifiques à mocker:
    # def mock_constructor(*args, **kwargs):
    #     instance_mock = MagicMock()
    #     # configurer l'instance mockée ici
    #     tweety_agents_logger.debug(f"ArgumentationAgent mock constructor called with args: {args}, kwargs: {kwargs}")
    #     return instance_mock
    # jclass_instance.constructor_mock = mock_constructor # MockJClassCore utilisera cela

    # Pour l'instant, on ne fait rien de spécifique, MockJClassCore fournira un MagicMock par défaut
    pass


def _configure_OpponentModel(jclass_instance: "MockJClassCore"):
    """Configure le mock pour org.tweetyproject.agents.OpponentModel."""
    tweety_agents_logger.debug(
        f"Configuring MockJClassCore for OpponentModel: {jclass_instance.class_name}"
    )
    pass  # Ajouter la logique de mock spécifique ici


def _configure_PersuasionProtocol(jclass_instance: "MockJClassCore"):
    """Configure le mock pour org.tweetyproject.agents.PersuasionProtocol."""
    tweety_agents_logger.debug(
        f"Configuring MockJClassCore for PersuasionProtocol: {jclass_instance.class_name}"
    )
    pass  # Ajouter la logique de mock spécifique ici


def _configure_Dialogue(jclass_instance: "MockJClassCore"):
    """Configure le mock pour org.tweetyproject.agents.dialogues.Dialogue."""
    tweety_agents_logger.debug(
        f"Configuring mock for Dialogue: {jclass_instance.class_name}"
    )

    def dialogue_constructor(*args, **kwargs):
        instance_mock = MagicMock()
        instance_mock.class_name = "org.tweetyproject.agents.dialogues.Dialogue"

        participants = []
        instance_mock.getParticipants = MagicMock(return_value=participants)

        def dialogue_add_participant(agent, position):
            tweety_agents_logger.debug(
                f"[Dialogue.addParticipant] Ajout de l'agent {getattr(agent, 'getName', lambda: 'N/A')()} avec position {getattr(position, 'name', 'N/A')}"
            )
            participants.append(agent)
            return True

        instance_mock.addParticipant = MagicMock(side_effect=dialogue_add_participant)

        if args and len(args) == 1:
            protocol_arg = args[0]
            instance_mock._protocol = protocol_arg
            instance_mock.getProtocol = MagicMock(return_value=instance_mock._protocol)
            tweety_agents_logger.debug(
                f"[MOCK Dialogue] Protocole initial stocké: {getattr(protocol_arg, 'class_name', 'N/A')}"
            )

        def dialogue_run():
            jclass_provider = jclass_instance.jclass_provider_func
            DialogueResult = jclass_provider(
                "org.tweetyproject.agents.dialogues.DialogueResult"
            )
            dialogue_result_mock = DialogueResult()
            dialogue_result_mock.class_name = (
                "org.tweetyproject.agents.dialogues.DialogueResult"
            )
            tweety_agents_logger.debug(
                f"[Dialogue.run] Exécution simulée, retour d'un mock DialogueResult."
            )
            return dialogue_result_mock

        instance_mock.run = MagicMock(side_effect=dialogue_run)
        tweety_agents_logger.debug(f"[MOCK Dialogue] Méthode run configurée.")

        return instance_mock

    jclass_instance.constructor_mock = dialogue_constructor


# Enregistrement des configurateurs
# Les noms de classes doivent correspondre exactement à ceux utilisés par Tweety.
_agent_class_configs[
    "org.tweetyproject.agents.ArgumentationAgent"
] = _configure_ArgumentationAgent
_agent_class_configs[
    "org.tweetyproject.agents.OpponentModel"
] = _configure_OpponentModel
_agent_class_configs[
    "org.tweetyproject.agents.PersuasionProtocol"
] = _configure_PersuasionProtocol
_agent_class_configs[
    "org.tweetyproject.agents.dialogues.Dialogue"
] = _configure_Dialogue
# Ajouter d'autres classes d'agents ici au besoin

tweety_agents_logger.info(
    f"Tweety agent class configurators registered: {list(_agent_class_configs.keys())}"
)

# Il faudra aussi potentiellement modifier jclass_core.py pour qu'il appelle
# cette fonction configure_tweety_agent_class, सिमिलairement à ce qui est fait pour les reasoners.
