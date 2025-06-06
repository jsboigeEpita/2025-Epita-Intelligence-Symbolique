# -*- coding: utf-8 -*-
"""
Sous-script de démonstration pour les fonctionnalités avancées.

Ce script contient les démonstrations pour :
1. L'analyse rhétorique sur un exemple de texte clair.
2. L'analyse rhétorique sur des données chiffrées.
3. La génération d'un rapport complet.
4. Une interaction de base avec la bibliothèque Tweety via JPype.
"""
import logging
import sys
import os
import json
import time
import asyncio
from pathlib import Path
from typing import Union, Dict, Any
from unittest.mock import patch, MagicMock

# Configuration de l'environnement et des imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configuration du logger
logger = logging.getLogger("demo_advanced_features")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Imports du projet
try:
    from argumentation_analysis.core.bootstrap import initialize_project_environment, ProjectContext
    from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
    import jpype
    logger.info("Modules du projet et JPype importés avec succès.")
except ImportError as e:
    logger.critical(f"Impossible d'importer les modules nécessaires : {e}. Arrêt du script.")
    sys.exit(1)


def demonstrate_clear_text_analysis(project_context: ProjectContext):
    """Analyse un fichier texte clair pour y détecter des sophismes."""
    logger.info("\n--- Démonstration : Analyse de Texte Clair ---")
    
    if not project_context.informal_agent:
        logger.error("InformalAgent non initialisé. Abandon.")
        return

    example_file_path = project_root / "examples" / "exemple_sophisme.txt"
    
    try:
        if not example_file_path.is_file():
            logger.warning(f"Fichier d'exemple '{example_file_path}' non trouvé. Création d'un fichier par défaut.")
            default_content = "L'argument de mon adversaire est ridicule, il doit être idiot. De plus, tout le monde sait que j'ai raison."
            example_file_path.parent.mkdir(parents=True, exist_ok=True)
            example_file_path.write_text(default_content, encoding="utf-8")
        
        text_content = example_file_path.read_text(encoding="utf-8")
        logger.info(f"Contenu du fichier (premiers 200 caractères) :\n{text_content[:200]}...")

        agent_instance = project_context.informal_agent
        logger.info(f"Utilisation de InformalAgent (type: {type(agent_instance).__name__}) pour l'analyse.")
        
        analysis_results = asyncio.run(agent_instance.analyze_fallacies(text_content))
        
        logger.info("Résultats de l'analyse des sophismes (texte clair) :")
        analysis_results_json = json.dumps(analysis_results, indent=4, ensure_ascii=False)
        for line in analysis_results_json.splitlines():
            logger.info(line)

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du texte clair : {e}", exc_info=True)


def demonstrate_encrypted_data_analysis(project_context: ProjectContext) -> Union[str, None]:
    """Déchiffre et analyse le premier extrait de données trouvé."""
    logger.info("\n--- Démonstration : Analyse de Données Chiffrées ---")

    if not all([project_context.crypto_service, project_context.definition_service, project_context.informal_agent]):
        logger.error("Un ou plusieurs services (Crypto, Definition, InformalAgent) ne sont pas initialisés. Abandon.")
        return None

    try:
        extract_definitions_obj = project_context.definition_service.load_definitions()
        
        extracts_to_process = []
        if hasattr(extract_definitions_obj, 'extracts'):
            extracts_to_process = extract_definitions_obj.extracts
        elif hasattr(extract_definitions_obj, 'sources') and extract_definitions_obj.sources:
            extracts_to_process = extract_definitions_obj.sources[0].extracts
        
        if not extracts_to_process:
            logger.warning("Aucun extrait trouvé à analyser.")
            return None

        selected_extract = extracts_to_process[0]
        extract_id = getattr(selected_extract, 'id', 'N/A')
        text_content_extract = getattr(selected_extract, 'full_text', '')
        
        logger.info(f"Analyse de l'extrait déchiffré (ID: {extract_id})...")
        
        real_analysis_data = asyncio.run(project_context.informal_agent.analyze_fallacies(text_content_extract))
        
        structured_result = {
            "extract_id": extract_id,
            "analysis_details": real_analysis_data
        }
        
        logger.info("Résultat de l'analyse de l'extrait déchiffré :")
        logger.info(json.dumps(structured_result, indent=4, ensure_ascii=False))

        results_dir = project_root / "results"
        results_dir.mkdir(exist_ok=True)
        analysis_output_path = results_dir / "analysis_encrypted_extract_demo.json"
        analysis_output_path.write_text(json.dumps([structured_result], indent=4, ensure_ascii=False), encoding="utf-8")
        
        logger.info(f"Résultat sauvegardé dans : {analysis_output_path.resolve()}")
        return str(analysis_output_path.resolve())

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des données chiffrées : {e}", exc_info=True)
        return None


def demonstrate_report_generation(analysis_json_path: str):
    """Génère un rapport à partir d'un fichier de résultats d'analyse."""
    logger.info(f"\n--- Démonstration : Génération de Rapport ---")
    
    if not analysis_json_path:
        logger.warning("Chemin du fichier d'analyse non fourni. Abandon de la génération du rapport.")
        return

    # Cette fonction est un placeholder. La logique de génération de rapport
    # est complexe et dépend d'un autre script qui est appelé par l'orchestrateur principal.
    # Ici, nous nous contentons de mentionner que l'étape a été atteinte.
    logger.info("La génération de rapport est normalement gérée par un script dédié.")
    logger.info(f"Le fichier de résultats à utiliser serait : {analysis_json_path}")
    logger.info("Dans une exécution complète, le script 'generate_comprehensive_report.py' serait appelé ici.")


def demonstrate_tweety_interaction(project_context: ProjectContext):
    """Montre une interaction de base avec Tweety pour parser une formule logique."""
    logger.info("\n--- Démonstration : Interaction avec Tweety ---")
    
    if not project_context.jvm_initialized:
        logger.warning("JVM non initialisée. Abandon de l'interaction avec Tweety.")
        return

    try:
        if jpype.isJVMStarted():
            PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
            parser_instance = PlParser()
            logger.info(f"Instance de PlParser créée avec succès : {parser_instance}")
            
            formula_str = "a && b"
            parsed_formula = parser_instance.parseFormula(formula_str)
            logger.info(f"Formule '{formula_str}' parsée en : {parsed_formula.toString()}")
            
            atoms_set = parsed_formula.getAtoms()
            py_atoms_list = [str(atom) for atom in atoms_set]
            logger.info(f"Atomes extraits de la formule : {py_atoms_list}")
        else:
            logger.warning("La JVM est marquée comme non démarrée par JPype.")
            
    except Exception as e:
        logger.error(f"Erreur lors de l'interaction avec Tweety : {e}", exc_info=True)


def demonstrate_tactical_orchestration():
    """Simule la décomposition d'objectifs stratégiques par le coordinateur tactique."""
    logger.info("\n--- Démonstration : Orchestration Tactique Avancée ---")
    logger.info("Simulation de la décomposition d'un objectif stratégique en tâches opérationnelles.")

    try:
        # Création d'un mock pour le coordinateur tactique et ses dépendances
        mock_coordinator = MagicMock()
        mock_coordinator.process_strategic_objectives.return_value = {
            "status": "SUCCESS",
            "tasks_created": 4,
            "dependencies_established": True
        }

        objectives = [{
            "id": "obj-demo-1",
            "description": "Analyser la rhétorique et les sophismes d'un discours politique.",
            "priority": "high",
            "type": "comprehensive_analysis"
        }]

        logger.info(f"Envoi de l'objectif stratégique : '{objectives[0]['description']}'")
        
        # Appel de la méthode (mockée)
        result = mock_coordinator.process_strategic_objectives(objectives)

        logger.info("Le coordinateur tactique a traité l'objectif.")
        logger.info(f"Résultat (simulé) : {result}")
        logger.info("Cette simulation montre comment un objectif de haut niveau est reçu et traité pour créer un plan d'action détaillé.")

    except Exception as e:
        logger.error(f"Erreur lors de la démonstration de l'orchestration tactique : {e}", exc_info=True)


def demonstrate_complex_fallacy_analysis():
    """Simule l'analyse de sophismes complexes et composés."""
    logger.info("\n--- Démonstration : Analyse de Sophismes Complexes ---")
    logger.info("Simulation de la détection de schémas de sophismes avancés.")

    try:
        # Création d'un mock pour l'analyseur de sophismes complexes
        mock_analyzer = MagicMock()
        mock_analyzer.detect_composite_fallacies.return_value = {
            "individual_fallacies_count": 2,
            "basic_combinations": [{"combination_type": "ad_hominem_straw_man", "severity": 0.85}],
            "advanced_combinations": [{"combination_name": "circular_reasoning_with_appeal_to_authority", "severity": 0.9}],
            "overall_fallaciousness_score": 0.88
        }

        test_arguments = ["Argument 1: ...", "Argument 2: ..."]
        test_context = {"source": "Discours politique", "topic": "Réforme économique"}

        logger.info("Analyse d'un texte pour les sophismes composés...")
        
        # Appel de la méthode (mockée)
        result = mock_analyzer.detect_composite_fallacies(test_arguments, test_context)

        logger.info("Résultats de l'analyse des sophismes complexes (simulés) :")
        logger.info(json.dumps(result, indent=4, ensure_ascii=False))
        logger.info("Cette simulation illustre la capacité du système à identifier des relations complexes entre sophismes, allant au-delà d'une simple liste.")

    except Exception as e:
        logger.error(f"Erreur lors de la démonstration de l'analyse de sophismes complexes : {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("=== Début du sous-script de démonstration des fonctionnalités avancées ===")
    
    project_context = initialize_project_environment(root_path_str=str(project_root))
    
    if not project_context:
        logger.critical("Échec de l'initialisation du contexte du projet. Arrêt.")
        sys.exit(1)
        
    # Exécuter les démonstrations
    demonstrate_clear_text_analysis(project_context)
    analysis_file = demonstrate_encrypted_data_analysis(project_context)
    demonstrate_report_generation(analysis_file)
    demonstrate_tweety_interaction(project_context)
    demonstrate_tactical_orchestration()
    demonstrate_complex_fallacy_analysis()
    
    logger.info("=== Fin du sous-script de démonstration des fonctionnalités avancées ===")