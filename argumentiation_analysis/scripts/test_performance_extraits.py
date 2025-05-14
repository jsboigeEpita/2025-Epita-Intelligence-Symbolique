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

# Ajouter le répertoire racine au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
root_dir = parent_dir
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestPerformanceExtraits")

# Créer un répertoire pour les résultats
RESULTS_DIR = Path(root_dir) / RESULTS_DIR / "performance_tests"
RESULTS_DIR.mkdir(exist_ok=True, parents=True)

# Chemins des extraits à tester
EXTRAITS_PATHS = [
    Path(root_dir.parent) / "examples" / "exemple_sophisme.txt",
    Path(root_dir) / "tests" / "test_data" / "source_texts" / "no_markers" / "texte_sans_marqueurs.txt",
    Path(root_dir) / "tests" / "test_data" / "source_texts" / "partial_markers" / "article_scientifique.txt",
    Path(root_dir) / "tests" / "test_data" / "source_texts" / "with_markers" / "discours_politique.txt",
    Path(root_dir) / "tests" / "test_data" / "source_texts" / "with_markers" / "discours_avec_template.txt"
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
    from argumentiation_analysis.agents.informal.informal_definitions import setup_informal_kernel
    
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
    
    # Mesurer le temps d'exécution
    start_time = time.time()
    
    # Mettre à jour le texte brut dans l'état
    state_manager.state["raw_text"] = texte
    
    # Appeler la fonction d'identification des arguments
    arguments = {"input": texte}
    result = await kernel.invoke("InformalAnalyzer", "semantic_IdentifyArguments", arguments)
    
    # Calculer le temps d'exécution
    execution_time = time.time() - start_time
    
    # Enregistrer les arguments identifiés
    arg_ids = []
    for line in result.strip().split('\n'):
        if line.strip():
            arg_id = state_manager.add_identified_argument(line.strip())
            arg_ids.append(arg_id)
    
    logger.info(f"Arguments identifiés: {len(arg_ids)} en {execution_time:.2f} secondes")
    return arg_ids, execution_time

async def test_explore_fallacy_hierarchy(kernel, root_pk="0"):
    """
    Teste la fonction d'exploration de la hiérarchie des sophismes.
    """
    logger.info(f"Test d'exploration de la hiérarchie des sophismes (PK={root_pk})...")
    
    # Mesurer le temps d'exécution
    start_time = time.time()
    
    # Appeler la fonction d'exploration de la hiérarchie
    arguments = {"current_pk_str": root_pk}
    result = await kernel.invoke("InformalAnalyzer", "explore_fallacy_hierarchy", arguments)
    
    # Calculer le temps d'exécution
    execution_time = time.time() - start_time
    
    # Analyser le résultat JSON
    try:
        hierarchy = json.loads(result)
        logger.info(f"Hiérarchie des sophismes explorée en {execution_time:.2f} secondes")
        return hierarchy, execution_time
    except json.JSONDecodeError:
        logger.error("Erreur de décodage JSON dans le résultat de explore_fallacy_hierarchy")
        return None, execution_time

async def test_get_fallacy_details(kernel, fallacy_pk):
    """
    Teste la fonction de récupération des détails d'un sophisme.
    """
    logger.info(f"Test de récupération des détails du sophisme (PK={fallacy_pk})...")
    
    # Mesurer le temps d'exécution
    start_time = time.time()
    
    # Appeler la fonction de récupération des détails
    arguments = {"fallacy_pk_str": str(fallacy_pk)}
    result = await kernel.invoke("InformalAnalyzer", "get_fallacy_details", arguments)
    
    # Calculer le temps d'exécution
    execution_time = time.time() - start_time
    
    # Analyser le résultat JSON
    try:
        details = json.loads(result)
        logger.info(f"Détails du sophisme récupérés en {execution_time:.2f} secondes")
        return details, execution_time
    except json.JSONDecodeError:
        logger.error("Erreur de décodage JSON dans le résultat de get_fallacy_details")
        return None, execution_time

async def test_attribute_fallacy(kernel, state_manager, fallacy_pk, arg_id):
    """
    Teste la fonction d'attribution d'un sophisme à un argument.
    """
    logger.info(f"Test d'attribution du sophisme PK={fallacy_pk} à l'argument {arg_id}...")
    
    # Mesurer le temps d'exécution
    start_time = time.time()
    
    # Récupérer les détails du sophisme
    fallacy_details, _ = await test_get_fallacy_details(kernel, fallacy_pk)
    
    if fallacy_details.get("error"):
        logger.error(f"Erreur lors de la récupération des détails du sophisme: {fallacy_details['error']}")
        return None, time.time() - start_time
    
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
    
    # Calculer le temps d'exécution
    execution_time = time.time() - start_time
    
    logger.info(f"Sophisme attribué avec l'ID: {fallacy_id} en {execution_time:.2f} secondes")
    return fallacy_id, execution_time

async def test_analyze_fallacies(kernel, state_manager, arg_id):
    """
    Teste la fonction d'analyse des sophismes dans un argument.
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
    arguments = {"input": argument["description"]}
    result = await kernel.invoke("InformalAnalyzer", "semantic_AnalyzeFallacies", arguments)
    
    # Calculer le temps d'exécution
    execution_time = time.time() - start_time
    
    # Analyser le résultat
    fallacy_ids = []
    for line in result.strip().split('\n'):
        if line.strip():
            # Format attendu: "Type de sophisme: Justification"
            parts = line.split(':', 1)
            if len(parts) == 2:
                fallacy_type = parts[0].strip()
                justification = parts[1].strip()
                fallacy_id = state_manager.add_identified_fallacy(
                    fallacy_type=fallacy_type,
                    justification=justification,
                    target_argument_id=arg_id
                )
                fallacy_ids.append(fallacy_id)
    
    logger.info(f"Sophismes identifiés: {len(fallacy_ids)} en {execution_time:.2f} secondes")
    return fallacy_ids, execution_time

async def load_extrait(path):
    """
    Charge un extrait de texte à partir d'un fichier.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraire l'ID et la description à partir du nom de fichier
        extrait_id = path.stem
        description = path.name
        
        return {
            "id": extrait_id,
            "description": description,
            "path": str(path),
            "texte": content
        }
    except Exception as e:
        logger.error(f"Erreur lors du chargement de l'extrait {path}: {e}")
        return None

async def run_performance_test(extrait):
    """
    Exécute un test complet de performance sur un extrait donné.
    """
    logger.info(f"=== Test de performance sur l'extrait '{extrait['id']}' ===")
    
    # Initialiser l'environnement
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # Création du Service LLM
    from argumentiation_analysis.core.llm_service import create_llm_service

from argumentiation_analysis.paths import RESULTS_DIR

    llm_service = create_llm_service()
    
    if not llm_service:
        logger.error("❌ Impossible de créer le service LLM.")
        return None
    
    # Configurer l'agent Informel
    kernel, state_manager = await setup_informal_agent(llm_service)
    
    # Résultats pour enregistrer les performances
    results = {
        "extrait": extrait,
        "timestamp": datetime.now().isoformat(),
        "performances": {
            "identification_arguments": {
                "temps_execution": 0,
                "nombre_arguments": 0
            },
            "exploration_hierarchie": {
                "temps_execution": 0
            },
            "analyse_sophismes": {
                "temps_execution": 0,
                "nombre_sophismes": 0
            },
            "temps_total": 0
        },
        "resultats": {
            "arguments": [],
            "sophismes": [],
            "hierarchie": None,
            "etat_final": None
        }
    }
    
    # Mesurer le temps total d'exécution
    start_time_total = time.time()
    
    # Test d'identification des arguments
    arg_ids, temps_identification = await test_identify_arguments(kernel, state_manager, extrait["texte"])
    results["performances"]["identification_arguments"]["temps_execution"] = temps_identification
    results["performances"]["identification_arguments"]["nombre_arguments"] = len(arg_ids)
    
    # Explorer la hiérarchie des sophismes
    hierarchy, temps_exploration = await test_explore_fallacy_hierarchy(kernel, "0")
    results["performances"]["exploration_hierarchie"]["temps_execution"] = temps_exploration
    
    # Pour chaque argument, analyser les sophismes
    temps_analyse_total = 0
    nombre_sophismes_total = 0
    
    for arg_id in arg_ids:
        fallacy_ids, temps_analyse = await test_analyze_fallacies(kernel, state_manager, arg_id)
        temps_analyse_total += temps_analyse
        nombre_sophismes_total += len(fallacy_ids)
        
        results["resultats"]["sophismes"].extend([{
            "fallacy_id": fallacy_id,
            "arg_id": arg_id
        } for fallacy_id in fallacy_ids])
    
    results["performances"]["analyse_sophismes"]["temps_execution"] = temps_analyse_total
    results["performances"]["analyse_sophismes"]["nombre_sophismes"] = nombre_sophismes_total
    
    # Calculer le temps total d'exécution
    results["performances"]["temps_total"] = time.time() - start_time_total
    
    # Enregistrer l'état final
    results["resultats"]["arguments"] = state_manager.state["identified_arguments"]
    results["resultats"]["hierarchie"] = hierarchy
    results["resultats"]["etat_final"] = json.loads(state_manager.get_current_state_snapshot())
    
    # Sauvegarder les résultats
    results_path = RESULTS_DIR / f"results_{extrait['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Résultats sauvegardés dans {results_path}")
    return results

async def generate_performance_report(results):
    """
    Génère un rapport de performance basé sur les résultats des tests.
    """
    logger.info("Génération du rapport de performance...")
    
    # Créer le rapport
    report = {
        "titre": "Rapport de Performance - Analyse Rhétorique",
        "date": datetime.now().isoformat(),
        "nombre_extraits_testes": len(results),
        "resultats_par_extrait": [
            {
                "id": r["extrait"]["id"],
                "description": r["extrait"]["description"],
                "performances": {
                    "temps_total": r["performances"]["temps_total"],
                    "nombre_arguments": r["performances"]["identification_arguments"]["nombre_arguments"],
                    "nombre_sophismes": r["performances"]["analyse_sophismes"]["nombre_sophismes"],
                    "temps_identification_arguments": r["performances"]["identification_arguments"]["temps_execution"],
                    "temps_analyse_sophismes": r["performances"]["analyse_sophismes"]["temps_execution"]
                }
            }
            for r in results
        ],
        "performances_moyennes": {
            "temps_total": sum(r["performances"]["temps_total"] for r in results) / len(results),
            "nombre_arguments": sum(r["performances"]["identification_arguments"]["nombre_arguments"] for r in results) / len(results),
            "nombre_sophismes": sum(r["performances"]["analyse_sophismes"]["nombre_sophismes"] for r in results) / len(results),
            "temps_identification_arguments": sum(r["performances"]["identification_arguments"]["temps_execution"] for r in results) / len(results),
            "temps_analyse_sophismes": sum(r["performances"]["analyse_sophismes"]["temps_execution"] for r in results) / len(results)
        }
    }
    
    # Sauvegarder le rapport au format JSON
    report_path = RESULTS_DIR / f"rapport_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Créer une version markdown du rapport pour une meilleure lisibilité
    md_report = f"""# {report['titre']}

## Informations Générales
- **Date d'exécution:** {datetime.fromisoformat(report['date']).strftime('%d/%m/%Y %H:%M:%S')}
- **Nombre d'extraits testés:** {report['nombre_extraits_testes']}

## Performances Moyennes
- **Temps total moyen:** {report['performances_moyennes']['temps_total']:.2f} secondes
- **Nombre moyen d'arguments identifiés:** {report['performances_moyennes']['nombre_arguments']:.2f}
- **Nombre moyen de sophismes identifiés:** {report['performances_moyennes']['nombre_sophismes']:.2f}
- **Temps moyen d'identification des arguments:** {report['performances_moyennes']['temps_identification_arguments']:.2f} secondes
- **Temps moyen d'analyse des sophismes:** {report['performances_moyennes']['temps_analyse_sophismes']:.2f} secondes

## Résultats par Extrait

{chr(10).join([f"""### {r['id']}
- **Description:** {r['description']}
- **Temps total:** {r['performances']['temps_total']:.2f} secondes
- **Nombre d'arguments identifiés:** {r['performances']['nombre_arguments']}
- **Nombre de sophismes identifiés:** {r['performances']['nombre_sophismes']}
- **Temps d'identification des arguments:** {r['performances']['temps_identification_arguments']:.2f} secondes
- **Temps d'analyse des sophismes:** {r['performances']['temps_analyse_sophismes']:.2f} secondes
""" for r in report['resultats_par_extrait']])}

## Conclusion
Ce rapport a été généré automatiquement après l'exécution des tests de performance sur les extraits spécifiés. Une analyse manuelle plus approfondie est recommandée pour évaluer la qualité de l'analyse rhétorique produite.
"""
    
    md_report_path = RESULTS_DIR / f"rapport_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    
    logger.info(f"Rapport de performance sauvegardé dans {md_report_path}")
    return md_report_path

async def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage des tests de performance...")
    
    # Charger les extraits
    extraits = []
    for path in EXTRAITS_PATHS:
        extrait = await load_extrait(path)
        if extrait:
            extraits.append(extrait)
    
    logger.info(f"Extraits chargés: {len(extraits)}")
    
    # Exécuter les tests de performance sur chaque extrait
    results = []
    for extrait in extraits:
        try:
            result = await run_performance_test(extrait)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Erreur lors du test sur l'extrait '{extrait['id']}': {e}", exc_info=True)
    
    # Générer le rapport de performance
    if results:
        report_path = await generate_performance_report(results)
        logger.info(f"Rapport de performance généré: {report_path}")
    else:
        logger.warning("Aucun résultat de test disponible pour générer le rapport.")
    
    logger.info("Tests de performance terminés.")

if __name__ == "__main__":
    asyncio.run(main())