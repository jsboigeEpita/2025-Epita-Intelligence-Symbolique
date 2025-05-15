#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple d'utilisation des outils d'analyse rhétorique améliorés.

Ce script montre comment utiliser les outils d'analyse rhétorique améliorés
dans le cadre de l'architecture hiérarchique à trois niveaux.
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configurer le chemin d'accès aux modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Importer les modules nécessaires
from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState

from argumentation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface

from argumentation_analysis.orchestration.hierarchical.operational.agent_registry import OperationalAgentRegistry
from argumentation_analysis.orchestration.hierarchical.operational.feedback_mechanism import FeedbackManager

from argumentation_analysis.paths import RESULTS_DIR


# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RhetoricalAnalysisExample")


async def run_rhetorical_analysis_example():
    """
    Exécute un exemple d'analyse rhétorique avec les outils améliorés.
    """
    logger.info("Démarrage de l'exemple d'analyse rhétorique...")
    
    # Créer les états pour chaque niveau
    strategic_state = StrategicState()
    tactical_state = TacticalState()
    operational_state = OperationalState()
    
    # Créer les interfaces entre les niveaux
    strategic_tactical_interface = StrategicTacticalInterface(
        strategic_state=strategic_state,
        tactical_state=tactical_state
    )
    
    tactical_operational_interface = TacticalOperationalInterface(
        tactical_state=tactical_state,
        operational_state=operational_state
    )
    
    # Créer le registre des agents opérationnels
    agent_registry = OperationalAgentRegistry(operational_state=operational_state)
    
    # Créer le gestionnaire de feedback
    feedback_manager = FeedbackManager(operational_state=operational_state)
    
    # Définir un texte d'exemple à analyser
    example_text = """
    Le réchauffement climatique est un mythe créé par les scientifiques pour obtenir des financements.
    Regardez, il a neigé l'hiver dernier, ce qui prouve que le climat ne se réchauffe pas.
    De plus, des milliers de scientifiques ont signé une pétition contre cette théorie.
    Si nous réduisons les émissions de carbone, l'économie s'effondrera et des millions de personnes perdront leur emploi.
    Voulez-vous être responsable de la misère de tant de familles?
    Les écologistes sont des extrémistes qui veulent nous ramener à l'âge de pierre.
    """
    
    # Définir l'objectif global
    strategic_state.add_global_objective({
        "id": "obj-1",
        "description": "Analyser les sophismes dans le texte sur le réchauffement climatique",
        "priority": "high"
    })
    
    # Mettre à jour le plan stratégique
    strategic_state.update_strategic_plan({
        "phases": [
            {
                "id": "phase-1",
                "name": "Analyse des sophismes",
                "description": "Identifier et analyser les sophismes dans le texte"
            },
            {
                "id": "phase-2",
                "name": "Évaluation de la cohérence",
                "description": "Évaluer la cohérence des arguments"
            },
            {
                "id": "phase-3",
                "name": "Visualisation des résultats",
                "description": "Visualiser les résultats de l'analyse"
            }
        ]
    })
    
    # Créer une tâche tactique
    tactical_state.add_task({
        "id": "task-1",
        "description": "Identifier les sophismes dans le texte",
        "objective_id": "obj-1",
        "estimated_duration": "medium",
        "priority": "high",
        "required_capabilities": ["complex_fallacy_analysis", "contextual_fallacy_analysis"]
    })
    
    # Traduire la tâche tactique en tâche opérationnelle
    operational_task = tactical_operational_interface.translate_task({
        "id": "task-1",
        "description": "Identifier les sophismes dans le texte",
        "objective_id": "obj-1",
        "estimated_duration": "medium",
        "priority": "high",
        "required_capabilities": ["complex_fallacy_analysis", "contextual_fallacy_analysis"]
    })
    
    logger.info(f"Tâche opérationnelle créée: {operational_task['id']}")
    
    # Initialiser l'agent rhétorique
    rhetorical_agent = await agent_registry.get_agent("rhetorical")
    
    if not rhetorical_agent:
        logger.error("Impossible d'initialiser l'agent rhétorique.")
        return
    
    logger.info("Agent rhétorique initialisé avec succès.")
    
    # Préparer la tâche pour l'agent rhétorique
    rhetorical_task = {
        "id": operational_task["id"],
        "tactical_task_id": operational_task["tactical_task_id"],
        "description": operational_task["description"],
        "techniques": [
            {
                "name": "complex_fallacy_analysis",
                "parameters": {
                    "context": "politique",
                    "confidence_threshold": 0.7,
                    "include_composite_fallacies": True
                }
            },
            {
                "name": "contextual_fallacy_analysis",
                "parameters": {
                    "context": "environnemental",
                    "consider_domain": True,
                    "consider_audience": True
                }
            }
        ],
        "text_extracts": [
            {
                "id": "extract-1",
                "source": "example",
                "content": example_text,
                "relevance": "high"
            }
        ],
        "required_capabilities": ["complex_fallacy_analysis", "contextual_fallacy_analysis"]
    }
    
    # Traiter la tâche avec l'agent rhétorique
    logger.info("Traitement de la tâche avec l'agent rhétorique...")
    result = await rhetorical_agent.process_task(rhetorical_task)
    
    # Afficher les résultats
    logger.info(f"Statut du traitement: {result['status']}")
    
    if result['status'] == "completed" or result['status'] == "completed_with_issues":
        # Extraire les résultats
        outputs = result.get("outputs", {}).get(RESULTS_DIR, [])
        
        logger.info(f"Nombre de résultats: {len(outputs)}")
        
        # Afficher les résultats de l'analyse des sophismes complexes
        complex_fallacy_results = [output for output in outputs if output.get("type") == "complex_fallacy_analysis"]
        if complex_fallacy_results:
            logger.info("Résultats de l'analyse des sophismes complexes:")
            for result in complex_fallacy_results:
                analysis_results = result.get("analysis_results", {})
                logger.info(f"  - Sophismes individuels: {analysis_results.get('individual_fallacies_count', 0)}")
                logger.info(f"  - Combinaisons de base: {len(analysis_results.get('basic_combinations', []))}")
                logger.info(f"  - Combinaisons avancées: {len(analysis_results.get('advanced_combinations', []))}")
        
        # Afficher les résultats de l'analyse des sophismes contextuels
        contextual_fallacy_results = [output for output in outputs if output.get("type") == "contextual_fallacy_analysis"]
        if contextual_fallacy_results:
            logger.info("Résultats de l'analyse des sophismes contextuels:")
            for result in contextual_fallacy_results:
                analysis_results = result.get("analysis_results", {})
                logger.info(f"  - Sophismes identifiés: {len(analysis_results.get('identified_fallacies', []))}")
                logger.info(f"  - Facteurs contextuels: {analysis_results.get('context_factors', {})}")
        
        # Ajouter un feedback positif
        feedback_manager.collect_feedback(
            level="operational",
            tool_type="complex_fallacy_analysis",
            result_id=result["id"],
            feedback_type="positive",
            feedback_content={
                "comment": "Analyse détaillée et pertinente des sophismes complexes",
                "accuracy": 0.9,
                "usefulness": 0.8
            },
            source="user"
        )
        
        # Générer un rapport de feedback
        feedback_report = feedback_manager.generate_feedback_report(level="operational")
        logger.info(f"Rapport de feedback généré: {len(feedback_report)} entrées")
        
        # Mettre à jour l'état tactique avec les résultats
        for output in outputs:
            if output.get("type") == "complex_fallacy_analysis":
                tactical_state.add_rhetorical_analysis_result(
                    task_id="task-1",
                    result_type="complex_fallacy_analyses",
                    result=output.get("analysis_results", {})
                )
            elif output.get("type") == "contextual_fallacy_analysis":
                tactical_state.add_rhetorical_analysis_result(
                    task_id="task-1",
                    result_type="contextual_fallacy_analyses",
                    result=output.get("analysis_results", {})
                )
        
        # Mettre à jour l'état stratégique avec un résumé des résultats
        strategic_state.update_rhetorical_analysis_summary({
            "complex_fallacy_summary": {
                "total_fallacies": sum(len(output.get("analysis_results", {}).get("individual_fallacies", [])) 
                                    for output in complex_fallacy_results),
                "severity_level": "high",
                "main_fallacy_types": ["Appel à l'émotion", "Faux dilemme", "Généralisation hâtive"]
            },
            "contextual_fallacy_summary": {
                "total_fallacies": sum(len(output.get("analysis_results", {}).get("identified_fallacies", [])) 
                                    for output in contextual_fallacy_results),
                "context_relevance": "high",
                "main_context_factors": ["Politique", "Environnement", "Économie"]
            }
        })
        
        # Définir la conclusion finale
        strategic_state.set_final_conclusion(
            "Le texte contient plusieurs sophismes complexes et contextuels, notamment des appels à l'émotion, "
            "des faux dilemmes et des généralisations hâtives. Ces sophismes sont particulièrement problématiques "
            "dans le contexte environnemental et politique du débat sur le réchauffement climatique."
        )
    
    else:
        logger.error(f"Erreur lors du traitement de la tâche: {result.get('issues', [])}")
    
    logger.info("Exemple d'analyse rhétorique terminé.")


if __name__ == "__main__":
    asyncio.run(run_rhetorical_analysis_example())