#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester les performances de l'agent d'analyse rhétorique sur différents extraits de discours.

Ce script permet de:
1. Charger plusieurs extraits de texte spécifiés
2. Tester l'agent Informel sur chaque extrait
3. Mesurer les performances (temps d'exécution, précision, etc.)
4. Collecter les résultats de l'analyse rhétorique produite
5. Enregistrer les résultats dans un format structuré pour analyse ultérieure
6. Créer un rapport de synthèse des résultats d'exécution pour chaque extrait
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pytest
from semantic_kernel.functions import KernelArguments

# Ajouter le répertoire racine au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
root_dir = parent_dir
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TestPerformanceExtraits")

# Créer un répertoire pour les résultats
RESULTS_BASE_DIR = Path(root_dir) / "results"
RESULTS_DIR = RESULTS_BASE_DIR / "performance_tests"
RESULTS_DIR.mkdir(exist_ok=True, parents=True)

# Chemins des extraits à tester (laissés vides car les fichiers sont manquants)
EXTRAITS_PATHS = []


# Charger les textes pour les tests paramétrés
def load_all_extraits_for_test():
    """Charge tous les extraits de texte définis dans EXTRAITS_PATHS."""
    textes = []
    for path in EXTRAITS_PATHS:
        try:
            with open(path, "r", encoding="utf-8") as f:
                textes.append(f.read())
        except Exception as e:
            logger.warning(f"Impossible de charger l'extrait {path}: {e}")
    # S_assurer qu_au moins un texte est disponible pour éviter les erreurs de test
    if not textes:
        textes.append("Ceci est un texte de secours. Les chats sont des liquides.")
    return textes


TEXTES_POUR_TEST = load_all_extraits_for_test()


class StateManagerMock:
    """
    Mock du StateManager pour les tests isolés.
    """

    def __init__(self):
        """Initialise le StateManagerMock avec un état vide et des compteurs."""
        self.state: Dict[str, Any] = {
            "raw_text": "",
            "identified_arguments": [],
            "identified_fallacies": [],
            "answers": [],
        }
        self.arg_id_counter: int = 1
        self.fallacy_id_counter: int = 1
        self.answer_id_counter: int = 1

    def get_current_state_snapshot(self, summarize: bool = True) -> str:
        """Retourne un snapshot JSON de l'état actuel.

        :param summarize: Non utilisé actuellement dans ce mock.
        :type summarize: bool
        :return: Une chaîne JSON représentant l'état.
        :rtype: str
        """
        return json.dumps(self.state, indent=2)

    def add_identified_argument(self, description: str) -> str:
        """Ajoute un argument identifié à l'état.

        :param description: La description de l'argument.
        :type description: str
        :return: L'ID de l'argument ajouté.
        :rtype: str
        """
        arg_id = f"arg_{self.arg_id_counter}"
        self.arg_id_counter += 1
        self.state["identified_arguments"].append(
            {
                "id": arg_id,
                "description": description,
                "timestamp": datetime.now().isoformat(),
            }
        )
        return arg_id

    def add_identified_fallacy(
        self, fallacy_type: str, justification: str, target_argument_id: str
    ) -> str:
        """Ajoute un sophisme identifié à l'état.

        :param fallacy_type: Le type de sophisme.
        :type fallacy_type: str
        :param justification: La justification de l'identification du sophisme.
        :type justification: str
        :param target_argument_id: L'ID de l'argument auquel ce sophisme est lié.
        :type target_argument_id: str
        :return: L'ID du sophisme ajouté.
        :rtype: str
        """
        fallacy_id = f"fallacy_{self.fallacy_id_counter}"
        self.fallacy_id_counter += 1
        self.state["identified_fallacies"].append(
            {
                "id": fallacy_id,
                "fallacy_type": fallacy_type,
                "justification": justification,
                "target_argument_id": target_argument_id,
                "timestamp": datetime.now().isoformat(),
            }
        )
        return fallacy_id

    def add_answer(
        self, task_id: str, answer_text: str, source_ids: Optional[List[str]] = None
    ) -> str:
        """Ajoute une réponse à l'état.

        :param task_id: L'ID de la tâche associée à la réponse.
        :type task_id: str
        :param answer_text: Le texte de la réponse.
        :type answer_text: str
        :param source_ids: Liste optionnelle des IDs sources pour la réponse.
        :type source_ids: Optional[List[str]]
        :return: L'ID de la réponse ajoutée.
        :rtype: str
        """
        answer_id = f"answer_{self.answer_id_counter}"
        self.answer_id_counter += 1
        self.state["answers"].append(
            {
                "id": answer_id,
                "task_id": task_id,
                "text": answer_text,
                "source_ids": source_ids or [],
                "timestamp": datetime.now().isoformat(),
            }
        )
        return answer_id


async def setup_informal_agent(llm_service: Any) -> Tuple[Any, StateManagerMock]:
    """
    Configure et retourne l'agent Informel (Kernel Semantic Kernel) pour les tests.

    Initialise un Kernel Semantic Kernel, y ajoute le service LLM fourni,
    configure les plugins pour l'analyse informelle et ajoute un StateManagerMock.

    :param llm_service: L'instance du service LLM à utiliser.
    :type llm_service: Any
    :return: Un tuple contenant le Kernel configuré et l'instance du StateManagerMock.
    :rtype: Tuple[Any, StateManagerMock]
    """
    from semantic_kernel import Kernel
    from argumentation_analysis.agents.informal.informal_definitions import (
        setup_informal_kernel,
    )

    # Créer un nouveau kernel
    kernel = Kernel()

    # Ajouter le service LLM au kernel
    kernel.add_service(llm_service)

    # Configurer le kernel pour l'agent Informel
    setup_informal_kernel(kernel, llm_service)

    # Ajouter le StateManager mock
    state_manager = StateManagerMock()
    kernel.add_plugin(state_manager, plugin_name="StateManager")

    return kernel, state_manager


@pytest.mark.parametrize("texte", TEXTES_POUR_TEST)
@pytest.mark.asyncio
async def test_identify_arguments(
    kernel: Any, state_manager: StateManagerMock, texte: str
) -> Tuple[List[str], float]:
    """
    Teste la fonction d'identification des arguments de l'agent Informel.

    Invoque la fonction 'semantic_IdentifyArguments' du plugin 'InformalAnalyzer'
    sur le texte fourni, mesure le temps d'exécution et enregistre les arguments
    identifiés dans le StateManagerMock.

    :param kernel: Le Kernel Semantic Kernel configuré.
    :type kernel: Any
    :param state_manager: L'instance du StateManagerMock.
    :type state_manager: StateManagerMock
    :param texte: Le texte à analyser pour identifier les arguments.
    :type texte: str
    :return: Un tuple contenant la liste des IDs des arguments identifiés et
             le temps d'exécution en secondes.
    :rtype: Tuple[List[str], float]
    """
    logger.info("Test d'identification des arguments...")

    # Mesurer le temps d'exécution
    start_time = time.time()

    # Mettre à jour le texte brut dans l'état
    state_manager.state["raw_text"] = texte

    # Appeler la fonction d'identification des arguments
    arguments = KernelArguments(input=texte)
    result = await kernel.invoke(
        plugin_name="InformalAnalyzer",
        function_name="semantic_IdentifyArguments",
        arguments=arguments,
    )

    # Calculer le temps d'exécution
    execution_time = time.time() - start_time

    # Enregistrer les arguments identifiés
    arg_ids = []
    for line in str(result).strip().split("\n"):
        if line.strip():
            arg_id = state_manager.add_identified_argument(line.strip())
            arg_ids.append(arg_id)

    logger.info(
        f"Arguments identifiés: {len(arg_ids)} en {execution_time:.2f} secondes"
    )
    return arg_ids, execution_time


@pytest.mark.asyncio
async def test_explore_fallacy_hierarchy(
    kernel: Any, root_pk: str = "0"
) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Teste la fonction d'exploration de la hiérarchie des sophismes de l'agent Informel.

    Invoque la fonction 'explore_fallacy_hierarchy' du plugin 'InformalAnalyzer'
    et mesure le temps d'exécution.

    :param kernel: Le Kernel Semantic Kernel configuré.
    :type kernel: Any
    :param root_pk: La clé primaire (PK) du nœud racine de la hiérarchie à explorer.
    :type root_pk: str
    :return: Un tuple contenant la hiérarchie des sophismes (dictionnaire) ou None
             en cas d'erreur de décodage JSON, et le temps d'exécution en secondes.
    :rtype: Tuple[Optional[Dict[str, Any]], float]
    """
    logger.info(f"Test d'exploration de la hiérarchie des sophismes (PK={root_pk})...")

    # Mesurer le temps d'exécution
    start_time = time.time()

    # Appeler la fonction d'exploration de la hiérarchie
    arguments = KernelArguments(current_pk_str=root_pk)
    result = await kernel.invoke(
        plugin_name="InformalAnalyzer",
        function_name="explore_fallacy_hierarchy",
        arguments=arguments,
    )

    # Calculer le temps d'exécution
    execution_time = time.time() - start_time

    # Analyser le résultat JSON
    try:
        hierarchy = json.loads(str(result))
        logger.info(
            f"Hiérarchie des sophismes explorée en {execution_time:.2f} secondes"
        )
        return hierarchy, execution_time
    except json.JSONDecodeError:
        logger.error(
            "Erreur de décodage JSON dans le résultat de explore_fallacy_hierarchy"
        )
        return None, execution_time


@pytest.mark.parametrize("fallacy_pk", [0, 1, 13])
@pytest.mark.asyncio
async def test_get_fallacy_details(
    kernel: Any, fallacy_pk: Any
) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Teste la fonction de récupération des détails d'un sophisme de l'agent Informel.

    Invoque la fonction 'get_fallacy_details' du plugin 'InformalAnalyzer'
    et mesure le temps d'exécution.

    :param kernel: Le Kernel Semantic Kernel configuré.
    :type kernel: Any
    :param fallacy_pk: La clé primaire (PK) du sophisme dont les détails sont demandés.
    :type fallacy_pk: Any
    :return: Un tuple contenant les détails du sophisme (dictionnaire) ou None
             en cas d'erreur de décodage JSON, et le temps d'exécution en secondes.
    :rtype: Tuple[Optional[Dict[str, Any]], float]
    """
    logger.info(f"Test de récupération des détails du sophisme (PK={fallacy_pk})...")

    # Mesurer le temps d'exécution
    start_time = time.time()

    # Appeler la fonction de récupération des détails
    arguments = KernelArguments(fallacy_pk_str=str(fallacy_pk))
    result = await kernel.invoke(
        plugin_name="InformalAnalyzer",
        function_name="get_fallacy_details",
        arguments=arguments,
    )

    # Calculer le temps d'exécution
    execution_time = time.time() - start_time

    # Analyser le résultat JSON
    try:
        details = json.loads(str(result))
        logger.info(f"Détails du sophisme récupérés en {execution_time:.2f} secondes")
        return details, execution_time
    except json.JSONDecodeError:
        logger.error("Erreur de décodage JSON dans le résultat de get_fallacy_details")
        return None, execution_time


@pytest.mark.skip(
    reason="Nécessite de chaîner les fixtures pour obtenir un arg_id valide. À implémenter."
)
async def test_attribute_fallacy(
    kernel: Any, state_manager: StateManagerMock, fallacy_pk: Any, arg_id: str
) -> Tuple[Optional[str], float]:
    """
    Teste l'attribution d'un sophisme à un argument via le StateManagerMock.

    Récupère d'abord les détails du sophisme, puis l'ajoute à l'état via
    `state_manager.add_identified_fallacy`. Mesure le temps d'exécution.

    :param kernel: Le Kernel Semantic Kernel configuré (utilisé pour `test_get_fallacy_details`).
    :type kernel: Any
    :param state_manager: L'instance du StateManagerMock.
    :type state_manager: StateManagerMock
    :param fallacy_pk: La clé primaire (PK) du sophisme à attribuer.
    :type fallacy_pk: Any
    :param arg_id: L'ID de l'argument auquel attribuer le sophisme.
    :type arg_id: str
    :return: Un tuple contenant l'ID du sophisme attribué ou None en cas d'erreur,
             et le temps d'exécution en secondes.
    :rtype: Tuple[Optional[str], float]
    """
    logger.info(
        f"Test d'attribution du sophisme PK={fallacy_pk} à l'argument {arg_id}..."
    )

    # Mesurer le temps d'exécution
    start_time = time.time()

    # Récupérer les détails du sophisme
    fallacy_details, _ = await test_get_fallacy_details(kernel, fallacy_pk)

    if fallacy_details.get("error"):
        logger.error(
            f"Erreur lors de la récupération des détails du sophisme: {fallacy_details['error']}"
        )
        return None, time.time() - start_time

    # Déterminer le label du sophisme
    fallacy_label = (
        fallacy_details.get("nom_vulgarisé")
        or fallacy_details.get("text_fr")
        or f"Sophisme {fallacy_pk}"
    )

    # Générer une justification
    justification = f"Ce sophisme de type '{fallacy_label}' est identifié dans l'argument car il présente les caractéristiques typiques de ce type de raisonnement fallacieux."

    # Attribuer le sophisme à l'argument
    fallacy_id = state_manager.add_identified_fallacy(
        fallacy_type=fallacy_label,
        justification=justification,
        target_argument_id=arg_id,
    )

    # Calculer le temps d'exécution
    execution_time = time.time() - start_time

    logger.info(
        f"Sophisme attribué avec l'ID: {fallacy_id} en {execution_time:.2f} secondes"
    )
    return fallacy_id, execution_time


@pytest.mark.skip(
    reason="Nécessite de chaîner les fixtures pour obtenir un arg_id valide. À implémenter."
)
async def test_analyze_fallacies(
    kernel: Any, state_manager: StateManagerMock, arg_id: str
) -> Tuple[List[str], float]:
    """
    Teste la fonction d'analyse des sophismes dans un argument de l'agent Informel.

    Invoque la fonction 'semantic_AnalyzeFallacies' du plugin 'InformalAnalyzer'
    sur la description de l'argument fourni, mesure le temps d'exécution et
    enregistre les sophismes identifiés dans le StateManagerMock.

    :param kernel: Le Kernel Semantic Kernel configuré.
    :type kernel: Any
    :param state_manager: L'instance du StateManagerMock.
    :type state_manager: StateManagerMock
    :param arg_id: L'ID de l'argument à analyser pour les sophismes.
    :type arg_id: str
    :return: Un tuple contenant la liste des IDs des sophismes identifiés et
             le temps d'exécution en secondes.
    :rtype: Tuple[List[str], float]
    """
    logger.info(f"Test d'analyse des sophismes pour l'argument {arg_id}...")

    # Mesurer le temps d'exécution
    start_time = time.time()

    # Trouver l'argument dans l'état
    argument = None
    for arg in state_manager.state["identified_arguments"]:
        if arg["id"] == arg_id:
            argument = arg
            break

    if not argument:
        logger.error(f"Argument {arg_id} non trouvé dans l'état")
        return [], time.time() - start_time

    # Appeler la fonction d'analyse des sophismes
    arguments = KernelArguments(input=argument["description"])
    result = await kernel.invoke(
        plugin_name="InformalAnalyzer",
        function_name="semantic_AnalyzeFallacies",
        arguments=arguments,
    )

    # Calculer le temps d'exécution
    execution_time = time.time() - start_time

    # Analyser le résultat
    fallacy_ids = []
    for line in str(result).strip().split("\n"):
        if line.strip():
            # Format attendu: "Type de sophisme: Justification"
            parts = line.split(":", 1)
            if len(parts) == 2:
                fallacy_type = parts[0].strip()
                justification = parts[1].strip()
                fallacy_id = state_manager.add_identified_fallacy(
                    fallacy_type=fallacy_type,
                    justification=justification,
                    target_argument_id=arg_id,
                )
                fallacy_ids.append(fallacy_id)

    logger.info(
        f"Sophismes identifiés: {len(fallacy_ids)} en {execution_time:.2f} secondes"
    )
    return fallacy_ids, execution_time


# Le code `main` et les fonctions associées (`load_extrait`, `run_performance_test`, `generate_performance_report`)
# sont supprimés car ce fichier est maintenant un module de test Pytest et non un script autonome.
# Pytest découvrira et exécutera les fonctions `test_*` automatiquement.
