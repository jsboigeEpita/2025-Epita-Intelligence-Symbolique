#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester l'agent Informel de manière isolée sur plusieurs extraits de texte.

Ce script permet de:
1. Charger plusieurs extraits de texte contenant des arguments et potentiellement des sophismes
2. Tester l'agent Informel sur chaque extrait
3. Générer des traces conversationnelles détaillées
4. Analyser les performances de l'agent
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire racine au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
root_dir = parent_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestInformalAgent")

# Créer un répertoire pour les traces
TRACES_DIR = Path(parent_dir.parent) / "execution_traces" / "informal"
TRACES_DIR.mkdir(exist_ok=True, parents=True)

# Extraits de texte pour les tests
EXTRAITS = [
    {
        "id": "kremlin_extrait_1",
        "description": "Extrait du discours du Kremlin sur le contexte historique",
        "texte": """
        Je commence par le fait que l'Ukraine moderne a été entièrement créée par la Russie, plus précisément par la Russie bolchevique et communiste. Ce processus a commencé pratiquement immédiatement après la révolution de 1917, et Lénine et ses compagnons l'ont fait d'une manière très rude pour la Russie elle-même – par la séparation, par l'arrachement de parties de ses propres territoires historiques. Bien sûr, personne n'a demandé à des millions de personnes qui y vivaient ce qu'elles en pensaient.
        """
    },
    {
        "id": "kremlin_extrait_2",
        "description": "Extrait du discours du Kremlin sur l'OTAN",
        "texte": """
        En décembre 2021, nous avons à nouveau proposé aux États-Unis et à leurs alliés de s'entendre sur des mesures de sécurité et de désarmement. Mais notre proposition a été rejetée. Les États-Unis n'ont pas changé leur position. Ils ne sont pas prêts à coopérer avec la Russie dans ce domaine, mais poursuivent leurs propres objectifs et ne tiennent pas compte de nos intérêts.
        
        Et bien sûr, dans cette situation, nous nous demandons : que faire ensuite, à quoi s'attendre ? Nous savons bien d'après l'histoire comment, dans les années 1940 et au début des années 1941, l'Union soviétique a essayé par tous les moyens d'empêcher le début de la guerre ou au moins de retarder son déclenchement. Pour ce faire, elle a essayé, entre autres, de ne pas provoquer un agresseur potentiel, n'a pas déployé ou a retardé le déploiement des formations les plus nécessaires et urgentes. Et les premières étapes de la guerre ont été tragiques.
        
        La deuxième frappe, même dans les conditions les plus difficiles de 1941, a été portée avec une force et une puissance sans précédent. La Grande Guerre patriotique est devenue un énorme fardeau pour notre peuple, avec d'innombrables tragédies et pertes irréparables, des épreuves terribles. Mais notre peuple a fait preuve d'un courage et d'une abnégation sans précédent pour défendre sa patrie.
        """
    },
    {
        "id": "kremlin_extrait_3",
        "description": "Extrait du discours du Kremlin sur le gouvernement ukrainien",
        "texte": """
        Quant à ceux qui ont pris et gardent le pouvoir à Kiev, nous exigeons qu'ils cessent immédiatement les hostilités. Sinon, toute la responsabilité de la poursuite de l'effusion de sang reposera entièrement sur la conscience du régime qui gouverne le territoire de l'Ukraine.
        
        En annonçant les décisions prises aujourd'hui, je suis confiant dans le soutien des citoyens de Russie et de toutes les forces patriotiques du pays.
        """
    }
]

class StateManagerMock:
    """
    Mock du StateManager pour les tests isolés.
    """
    def __init__(self):
        self.state = {
            "raw_text": "",
            "identified_arguments": [],
            "identified_fallacies": [],
            "answers": []
        }
        self.arg_id_counter = 1
        self.fallacy_id_counter = 1
        self.answer_id_counter = 1
    
    def get_current_state_snapshot(self, summarize=True):
        """Retourne un snapshot de l'état actuel."""
        return json.dumps(self.state, indent=2)
    
    def add_identified_argument(self, description):
        """Ajoute un argument identifié à l'état."""
        arg_id = f"arg_{self.arg_id_counter}"
        self.arg_id_counter += 1
        self.state["identified_arguments"].append({
            "id": arg_id,
            "description": description,
            "timestamp": datetime.now().isoformat()
        })
        return arg_id
    
    def add_identified_fallacy(self, fallacy_type, justification, target_argument_id):
        """Ajoute un sophisme identifié à l'état."""
        fallacy_id = f"fallacy_{self.fallacy_id_counter}"
        self.fallacy_id_counter += 1
        self.state["identified_fallacies"].append({
            "id": fallacy_id,
            "fallacy_type": fallacy_type,
            "justification": justification,
            "target_argument_id": target_argument_id,
            "timestamp": datetime.now().isoformat()
        })
        return fallacy_id
    
    def add_answer(self, task_id, answer_text, source_ids=None):
        """Ajoute une réponse à l'état."""
        answer_id = f"answer_{self.answer_id_counter}"
        self.answer_id_counter += 1
        self.state["answers"].append({
            "id": answer_id,
            "task_id": task_id,
            "text": answer_text,
            "source_ids": source_ids or [],
            "timestamp": datetime.now().isoformat()
        })
        return answer_id

async def setup_informal_agent(llm_service):
    """
    Configure et retourne l'agent Informel pour les tests.
    """
    from semantic_kernel import Kernel
    from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
    
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

async def test_identify_arguments(kernel, state_manager, texte):
    """
    Teste la fonction d'identification des arguments.
    """
    logger.info("Test d'identification des arguments...")
    
    # Mettre à jour le texte brut dans l'état
    state_manager.state["raw_text"] = texte
    
    # Appeler la fonction d'identification des arguments
    # Correction pour compatibilité avec la version actuelle de Semantic Kernel
    arguments = {"input": texte}
    result = await kernel.invoke("InformalAnalyzer", "semantic_IdentifyArguments", arguments)
    
    # Enregistrer les arguments identifiés
    arg_ids = []
    for line in result.strip().split('\n'):
        if line.strip():
            arg_id = state_manager.add_identified_argument(line.strip())
            arg_ids.append(arg_id)
    
    logger.info(f"Arguments identifiés: {len(arg_ids)}")
    return arg_ids

async def test_explore_fallacy_hierarchy(kernel, root_pk="0"):
    """
    Teste la fonction d'exploration de la hiérarchie des sophismes.
    """
    logger.info(f"Test d'exploration de la hiérarchie des sophismes (PK={root_pk})...")
    
    # Appeler la fonction d'exploration de la hiérarchie
    arguments = {"current_pk_str": root_pk}
    result = await kernel.invoke("InformalAnalyzer", "explore_fallacy_hierarchy", arguments)
    
    # Analyser le résultat JSON
    try:
        hierarchy = json.loads(result)
        return hierarchy
    except json.JSONDecodeError:
        logger.error("Erreur de décodage JSON dans le résultat de explore_fallacy_hierarchy")
        return None

async def test_get_fallacy_details(kernel, fallacy_pk):
    """
    Teste la fonction de récupération des détails d'un sophisme.
    """
    logger.info(f"Test de récupération des détails du sophisme (PK={fallacy_pk})...")
    
    # Appeler la fonction de récupération des détails
    arguments = {"fallacy_pk_str": str(fallacy_pk)}
    result = await kernel.invoke("InformalAnalyzer", "get_fallacy_details", arguments)
    
    # Analyser le résultat JSON
    try:
        details = json.loads(result)
        return details
    except json.JSONDecodeError:
        logger.error("Erreur de décodage JSON dans le résultat de get_fallacy_details")
        return None

async def test_attribute_fallacy(kernel, state_manager, fallacy_pk, arg_id):
    """
    Teste la fonction d'attribution d'un sophisme à un argument.
    """
    logger.info(f"Test d'attribution du sophisme PK={fallacy_pk} à l'argument {arg_id}...")
    
    # Récupérer les détails du sophisme
    fallacy_details = await test_get_fallacy_details(kernel, fallacy_pk)
    
    if fallacy_details.get("error"):
        logger.error(f"Erreur lors de la récupération des détails du sophisme: {fallacy_details['error']}")
        return None
    
    # Déterminer le label du sophisme
    fallacy_label = fallacy_details.get("nom_vulgarisé") or fallacy_details.get("text_fr") or f"Sophisme {fallacy_pk}"
    
    # Générer une justification
    justification = f"Ce sophisme de type '{fallacy_label}' est identifié dans l'argument car il présente les caractéristiques typiques de ce type de raisonnement fallacieux."
    
    # Attribuer le sophisme à l'argument
    fallacy_id = state_manager.add_identified_fallacy(
        fallacy_type=fallacy_label,
        justification=justification,
        target_argument_id=arg_id
    )
    
    logger.info(f"Sophisme attribué avec l'ID: {fallacy_id}")
    return fallacy_id

async def run_informal_agent_test(extrait):
    """
    Exécute un test complet de l'agent Informel sur un extrait donné.
    """
    logger.info(f"=== Test de l'agent Informel sur l'extrait '{extrait['id']}' ===")
    
    # Initialiser l'environnement
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # Création du Service LLM
    from argumentation_analysis.core.llm_service import create_llm_service
    llm_service = create_llm_service()
    
    if not llm_service:
        logger.error("❌ Impossible de créer le service LLM.")
        return None
    
    # Configurer l'agent Informel
    kernel, state_manager = await setup_informal_agent(llm_service)
    
    # Trace pour enregistrer les résultats
    trace = {
        "extrait": extrait,
        "timestamp": datetime.now().isoformat(),
        "resultats": {
            "arguments": [],
            "sophismes": [],
            "hierarchie": None,
            "etat_final": None
        }
    }
    
    # Test d'identification des arguments
    arg_ids = await test_identify_arguments(kernel, state_manager, extrait["texte"])
    
    # Explorer la hiérarchie des sophismes
    hierarchy = await test_explore_fallacy_hierarchy(kernel, "0")
    
    # Pour chaque argument, tenter d'attribuer un sophisme
    for arg_id in arg_ids:
        # Trouver un sophisme approprié (pour cet exemple, nous utilisons le premier sophisme de la hiérarchie)
        if hierarchy and "children" in hierarchy and hierarchy["children"]:
            fallacy_pk = hierarchy["children"][0]["pk"]
            fallacy_id = await test_attribute_fallacy(kernel, state_manager, fallacy_pk, arg_id)
            if fallacy_id:
                trace["resultats"]["sophismes"].append({
                    "fallacy_id": fallacy_id,
                    "fallacy_pk": fallacy_pk,
                    "arg_id": arg_id
                })
    
    # Enregistrer l'état final
    trace["resultats"]["arguments"] = state_manager.state["identified_arguments"]
    trace["resultats"]["hierarchie"] = hierarchy
    trace["resultats"]["etat_final"] = json.loads(state_manager.get_current_state_snapshot())
    
    # Sauvegarder la trace
    trace_path = TRACES_DIR / f"trace_{extrait['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Trace sauvegardée dans {trace_path}")
    return trace

async def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage des tests de l'agent Informel...")
    
    results = []
    for extrait in EXTRAITS:
        try:
            result = await run_informal_agent_test(extrait)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Erreur lors du test sur l'extrait '{extrait['id']}': {e}", exc_info=True)
    
    # Générer un rapport de synthèse
    rapport = {
        "timestamp": datetime.now().isoformat(),
        "nombre_extraits_testes": len(EXTRAITS),
        "nombre_extraits_reussis": len(results),
        "resultats_par_extrait": [
            {
                "id": r["extrait"]["id"],
                "nombre_arguments": len(r["resultats"]["arguments"]),
                "nombre_sophismes": len(r["resultats"]["sophismes"])
            }
            for r in results
        ]
    }
    
    rapport_path = TRACES_DIR / f"rapport_synthese_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(rapport_path, "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Rapport de synthèse sauvegardé dans {rapport_path}")
    logger.info("Tests de l'agent Informel terminés.")

if __name__ == "__main__":
    asyncio.run(main())