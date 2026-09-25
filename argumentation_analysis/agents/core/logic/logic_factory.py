from typing import List

# argumentation_analysis/agents/core/logic/logic_factory.py
"""
Factory pour créer les agents logiques appropriés.
"""

import logging
from typing import Dict, Optional, Any, Type

from semantic_kernel import Kernel

from ..abc.agent_bases import BaseLogicAgent
from .propositional_logic_agent import PropositionalLogicAgent
from .fol_logic_agent import FOLLogicAgent
from .modal_logic_agent import ModalLogicAgent

# Configuration du logger
logger = logging.getLogger("Orchestration.LogicAgentFactory")


class LogicAgentFactory:
    """
    Factory pour créer les agents logiques appropriés.

    Cette classe permet de créer des instances d'agents logiques
    en fonction du type de logique spécifié.
    """

    # Mapping des types de logique vers les classes d'agents
    _agent_classes: Dict[str, Type[BaseLogicAgent]] = {
        "propositional": PropositionalLogicAgent,
        "first_order": FOLLogicAgent,
        "fol": FOLLogicAgent,
        "modal": ModalLogicAgent,
    }

    @classmethod
    def create_agent(
        cls, logic_type: str, kernel: Kernel, llm_service: Optional[Any] = None
    ) -> BaseLogicAgent:
        """
        Crée une instance d'un agent logique basé sur le type de logique spécifié.

        Recherche la classe d'agent correspondante dans `_agent_classes`, l'instancie
        avec le `kernel` fourni, et configure ses composants avec `llm_service` si présent.

        :param logic_type: Le type de logique pour lequel créer l'agent
                           (par exemple, "propositional", "first_order", "modal").
                           La casse est ignorée et les espaces sont supprimés.
        :type logic_type: str
        :param kernel: L'instance du `semantic_kernel.Kernel` à passer à l'agent.
        :type kernel: Kernel
        :param llm_service: Le service LLM optionnel à utiliser pour configurer
                            les composants de l'agent.
        :type llm_service: Optional[Any]
        :return: Une instance de la sous-classe `BaseLogicAgent` correspondante.
        :rtype: BaseLogicAgent
        :raises ValueError: si `logic_type` n'est pas un type que cette fabrique
                            sait instancier — le message nomme ceux qu'elle sait.
        :raises TypeError: si `llm_service` n'est pas un objet service (#2441).
        :raises Exception: l'exception du constructeur, telle quelle. Depuis
                           #2649 elle sort d'ici avec son type et son message :
                           les constructeurs lèvent (`SemanticSetupError` depuis
                           #2632/#2650, une erreur de bridge pour FOL), et
                           l'avaler en `None` privait les appelants de la cause,
                           qui ne survivait que dans une ligne de log.
        """
        logger.info(f"Création d'un agent logique de type '{logic_type}'")

        # Normaliser le type de logique
        logic_type = logic_type.lower().strip()
        logger.debug(f"Normalized logic type: {logic_type}")

        # #2649 : un type non supporté lève au lieu de rendre `None`. Le
        # message nomme ce que cette fabrique sait réellement instancier —
        # les clés de `_agent_classes`, pas `_handler_types` (ces derniers
        # n'ont pas d'agent : `create_agent` les refuserait aussi).
        if logic_type not in cls._agent_classes:
            raise ValueError(
                f"LogicAgentFactory.create_agent: unsupported logic_type "
                f"{logic_type!r}. This factory instantiates: "
                f"{', '.join(sorted(cls._agent_classes))}."
            )

        # #2441 — the third parameter is the LLM service, read for its
        # ``service_id``. A service id passed as a ``str`` used to be dropped
        # without a trace (the agent silently got its default id). Refused
        # here, outside the instantiation, so the caller sees why.
        if llm_service is not None and not hasattr(llm_service, "service_id"):
            raise TypeError(
                f"LogicAgentFactory.create_agent: llm_service must be a service "
                f"object with a service_id, got {type(llm_service).__name__}"
                + (f" {llm_service!r}" if isinstance(llm_service, str) else "")
                + ". Pass the service, not its id."
            )

        # Créer l'instance de l'agent
        agent_class = cls._agent_classes[logic_type]

        # Préparer les arguments pour le constructeur de l'agent
        agent_args = {
            "kernel": kernel,
            "agent_name": f"{logic_type.capitalize()}Agent",
        }
        if llm_service is not None:
            agent_args["service_id"] = llm_service.service_id

        # #2649 : pas de `try`/`except` ici. Le constructeur enregistre ses
        # fonctions sémantiques et résout les settings de son service (#2632) :
        # un échec est un défaut du code appelant, l'exception sort nommée.
        agent = agent_class(**agent_args)

        logger.info(f"Agent logique de type '{logic_type}' créé avec succès")
        return agent

    @classmethod
    def register_agent_class(
        cls, logic_type: str, agent_class: Type[BaseLogicAgent]
    ) -> None:
        """
        Enregistre une nouvelle classe d'agent pour un type de logique spécifique.

        Permet d'étendre dynamiquement les types d'agents logiques que la factory peut créer.

        :param logic_type: Le nom du type de logique (sera normalisé en minuscules et sans espaces).
        :type logic_type: str
        :param agent_class: La classe de l'agent (doit hériter de `BaseLogicAgent`).
        :type agent_class: Type[BaseLogicAgent]
        :return: None
        :rtype: None
        """
        logger.info(
            f"Enregistrement de la classe d'agent '{agent_class.__name__}' pour le type de logique '{logic_type}'"
        )
        cls._agent_classes[logic_type.lower().strip()] = agent_class

    # Handler-only types (no full agent, but handler available via TweetyBridge)
    _handler_types: List[str] = [
        "description_logic",
        "dl",
        "conditional_logic",
        "cl",
        "sat",
    ]

    @classmethod
    def get_supported_logic_types(cls) -> List[str]:
        """
        Retourne la liste des types de logique actuellement supportés par la factory.
        Includes both full agent types and handler-only types.

        :return: Une liste des noms des types de logique enregistrés.
        :rtype: List[str]
        """
        return list(cls._agent_classes.keys()) + cls._handler_types
