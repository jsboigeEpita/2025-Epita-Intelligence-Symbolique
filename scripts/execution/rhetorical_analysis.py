#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour effectuer une analyse rhétorique de base sur les extraits déchiffrés.

Ce script:
1. Charge les extraits déchiffrés générés par le script decrypt_extracts.py
2. Utilise les outils d'analyse rhétorique de base suivants:
   - ContextualFallacyDetector
   - ArgumentCoherenceEvaluator
   - SemanticArgumentAnalyzer
3. Analyse chaque extrait avec ces outils
4. Génère un rapport d'analyse pour chaque extrait
5. Sauvegarde les résultats dans un format structuré (JSON)

Note: Si le contenu textuel des extraits n'est pas disponible dans le fichier JSON,
le script génère des textes d'exemple pour permettre l'analyse.
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from tqdm import tqdm

from argumentation_analysis.utils.text_processing import split_text_into_arguments, generate_sample_text
from argumentation_analysis.utils.core_utils.file_utils import load_json_data, save_json_data
# Importer les mocks centralisés
from argumentation_analysis.mocks.analysis_tools import (
    MockContextualFallacyDetector,
    MockArgumentCoherenceEvaluator,
    MockSemanticArgumentAnalyzer as CentralizedMockSemanticArgumentAnalyzer # Alias pour éviter conflit
)


# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RhetoricalAnalysis")

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent)) # MODIFIÉ: Remonter à la racine

# Vérifier les dépendances requises
required_packages = ["networkx", "numpy", "tqdm"]
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    logger.warning(f"Les packages suivants sont manquants: {', '.join(missing_packages)}")
    logger.warning(f"Certaines fonctionnalités peuvent être limitées.")
    logger.warning(f"Pour installer les packages manquants: pip install {' '.join(missing_packages)}")

# Import des outils d'analyse rhétorique
try:
    from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector
    from argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import ArgumentCoherenceEvaluator
    from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import SemanticArgumentAnalyzer
    
    # Correction du problème avec DATA_DIR dans SemanticArgumentAnalyzer
    # Monkey patch pour remplacer DATA_DIR par "data" dans le dictionnaire des composants Toulmin
    original_define_toulmin_components = SemanticArgumentAnalyzer._define_toulmin_components
    
    def patched_define_toulmin_components(self):
        components = original_define_toulmin_components(self)
        if "DATA_DIR" in components:
            components["data"] = components.pop("DATA_DIR")
        return components
    
    SemanticArgumentAnalyzer._define_toulmin_components = patched_define_toulmin_components
    
    logger.info("Outils d'analyse rhétorique importés avec succès")
except ImportError as e:
    logger.error(f"Erreur d'importation des outils d'analyse rhétorique: {e}")
    logger.error("Assurez-vous que le package argumentation_analysis est installé ou accessible.")
    sys.exit(1)
except Exception as e:
    logger.error(f"Erreur inattendue lors de l'initialisation: {e}")
    sys.exit(1)

# Les fonctions load_extracts, split_text_into_arguments, et generate_sample_text
# ont été déplacées vers des modules utilitaires.

def analyze_extract(
    extract_definition: Dict[str, Any],
    source_name: str,
    tools: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyse un extrait avec les outils d'analyse rhétorique.
    
    Args:
        extract_definition (Dict[str, Any]): Définition de l'extrait
        source_name (str): Nom de la source
        tools (Dict[str, Any]): Dictionnaire contenant les outils d'analyse
        
    Returns:
        Dict[str, Any]: Résultats de l'analyse
    """
    extract_name = extract_definition.get("extract_name", "Extrait sans nom")
    logger.debug(f"Analyse de l'extrait '{extract_name}' de la source '{source_name}'")
    
    # Vérifier si l'extrait contient du texte
    extract_text = extract_definition.get("extract_text")
    
    # Si le texte n'est pas disponible, générer un exemple
    if not extract_text:
        logger.warning(f"Texte non disponible pour l'extrait '{extract_name}'. Utilisation d'un texte d'exemple.")
        extract_text = generate_sample_text(extract_name, source_name)
    
    # Diviser l'extrait en arguments
    arguments = split_text_into_arguments(extract_text)
    
    # Si aucun argument n'a été trouvé, utiliser l'extrait entier comme un seul argument
    if not arguments:
        arguments = [extract_text]
    
    # Initialiser les résultats
    results = {
        "extract_name": extract_name,
        "source_name": source_name,
        "argument_count": len(arguments),
        "timestamp": datetime.now().isoformat(),
        "analyses": {}
    }
    
    # Analyse des sophismes contextuels
    try:
        fallacy_detector = tools["fallacy_detector"]
        context_description = f"Extrait '{extract_name}' de la source '{source_name}'"
        fallacy_results = fallacy_detector.detect_multiple_contextual_fallacies(
            arguments, context_description
        )
        results["analyses"]["contextual_fallacies"] = fallacy_results
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des sophismes contextuels: {e}")
        results["analyses"]["contextual_fallacies"] = {"error": str(e)}
    
    # Analyse de la cohérence argumentative
    try:
        coherence_evaluator = tools["coherence_evaluator"]
        coherence_results = coherence_evaluator.evaluate_coherence(
            arguments, f"Extrait '{extract_name}'"
        )
        results["analyses"]["argument_coherence"] = coherence_results
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de la cohérence argumentative: {e}")
        results["analyses"]["argument_coherence"] = {"error": str(e)}
    
    # Analyse sémantique des arguments
    try:
        semantic_analyzer = tools["semantic_analyzer"]
        semantic_results = semantic_analyzer.analyze_multiple_arguments(arguments)
        results["analyses"]["semantic_analysis"] = semantic_results
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse sémantique des arguments: {e}")
        results["analyses"]["semantic_analysis"] = {"error": str(e)}
    
    return results

# La fonction create_mock_tools est supprimée car nous utilisons les mocks centralisés.

def analyze_extracts(
    extract_definitions: List[Dict[str, Any]],
    output_file: Path,
    use_mocks: bool = False  # Nouveau paramètre pour utiliser les mocks
) -> None:
    """
    Analyse tous les extraits et sauvegarde les résultats.
    
    Args:
        extract_definitions (List[Dict[str, Any]]): Définitions des extraits
        output_file (Path): Chemin du fichier de sortie
        use_mocks (bool): Si True, utilise les outils d'analyse simulés.
    """
    logger.info("Initialisation des outils d'analyse rhétorique...")
    
    if use_mocks:
        logger.warning("Utilisation des outils d'analyse rhétorique simulés (centralisés).")
        tools = {
            "fallacy_detector": MockContextualFallacyDetector(),
            "coherence_evaluator": MockArgumentCoherenceEvaluator(),
            "semantic_analyzer": CentralizedMockSemanticArgumentAnalyzer()
        }
        logger.info("✅ Outils d'analyse rhétorique simulés (centralisés) initialisés")
    else:
        # Initialiser les outils d'analyse réels
        try:
            tools = {
                "fallacy_detector": ContextualFallacyDetector(),
                "coherence_evaluator": ArgumentCoherenceEvaluator(),
                "semantic_analyzer": SemanticArgumentAnalyzer()
            }
            logger.info("✅ Outils d'analyse rhétorique réels initialisés")
        except NameError as e:
            logger.error(f"Erreur lors de l'initialisation des outils réels (NameError): {e}")
            logger.error("Les outils réels n'ont pas pu être importés. Vérifiez les dépendances et la configuration.")
            logger.warning("Passage à l'utilisation des mocks centralisés comme solution de repli.")
            tools = {
                "fallacy_detector": MockContextualFallacyDetector(),
                "coherence_evaluator": MockArgumentCoherenceEvaluator(),
                "semantic_analyzer": CentralizedMockSemanticArgumentAnalyzer()
            }
            logger.info("✅ Outils d'analyse rhétorique simulés (centralisés) initialisés comme solution de repli.")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'initialisation des outils réels: {e}")
            logger.warning("Passage à l'utilisation des mocks centralisés comme solution de repli.")
            tools = {
                "fallacy_detector": MockContextualFallacyDetector(),
                "coherence_evaluator": MockArgumentCoherenceEvaluator(),
                "semantic_analyzer": CentralizedMockSemanticArgumentAnalyzer()
            }
            logger.info("✅ Outils d'analyse rhétorique simulés (centralisés) initialisés comme solution de repli.")
    
    # Compter le nombre total d'extraits
    total_extracts = sum(len(source.get("extracts", [])) for source in extract_definitions)
    logger.info(f"Analyse de {total_extracts} extraits...")
    
    # Initialiser les résultats
    all_results = []
    
    # Initialiser la barre de progression
    progress_bar = tqdm(total=total_extracts, desc="Analyse des extraits", unit="extrait")
    
    # Analyser chaque source et ses extraits
    for source in extract_definitions:
        source_name = source.get("source_name", "Source sans nom")
        extracts = source.get("extracts", [])
        
        for extract in extracts:
            extract_name = extract.get("extract_name", "Extrait sans nom")
            
            # Analyser l'extrait
            try:
                results = analyze_extract(extract, source_name, tools)
                all_results.append(results)
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse de l'extrait '{extract_name}': {e}")
                all_results.append({
                    "extract_name": extract_name,
                    "source_name": source_name,
                    "error": str(e)
                })
            
            # Mettre à jour la barre de progression
            progress_bar.update(1)
    
    # Fermer la barre de progression
    progress_bar.close()
    
    # Sauvegarder les résultats
    if save_json_data(all_results, output_file):
        logger.info(f"✅ Résultats sauvegardés dans {output_file}")
    else:
        logger.error(f"❌ Erreur lors de la sauvegarde des résultats dans {output_file}")

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Les arguments parsés
    """
    parser = argparse.ArgumentParser(description="Analyse rhétorique des extraits déchiffrés")
    
    parser.add_argument(
        "--input", "-i",
        help="Chemin du fichier d'entrée contenant les extraits déchiffrés",
        default=None
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Chemin du fichier de sortie pour les résultats de l'analyse",
        default=None
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affiche des informations de débogage supplémentaires"
    )
    
    parser.add_argument(
        "--use-mocks",
        action="store_true",
        help="Utilise les outils d'analyse rhétorique simulés (mocks) au lieu des outils réels."
    )
    
    return parser.parse_args()

def main():
    """Fonction principale du script."""
    # Analyser les arguments
    args = parse_arguments()
    
    # Configurer le niveau de logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé")
    
    logger.info("Démarrage de l'analyse rhétorique des extraits...")
    
    # Trouver le fichier d'entrée le plus récent si non spécifié
    input_file = args.input
    if not input_file:
        temp_dir = Path("temp_extracts")
        if temp_dir.exists():
            extract_files = list(temp_dir.glob("extracts_decrypted_*.json"))
            if extract_files:
                # Trier par date de modification (la plus récente en premier)
                extract_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                input_file = extract_files[0]
                logger.info(f"Utilisation du fichier d'extraits le plus récent: {input_file}")
    
    if not input_file:
        logger.error("Aucun fichier d'entrée spécifié et aucun fichier d'extraits trouvé.")
        sys.exit(1)
    
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"Le fichier d'entrée {input_path} n'existe pas.")
        sys.exit(1)
    
    # Définir le fichier de sortie si non spécifié
    output_file = args.output
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path("results") / f"rhetorical_analysis_{timestamp}.json"
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Charger les extraits
    extract_definitions = load_json_data(input_path) # Utilisation de la fonction importée
    if extract_definitions is None: # load_json_data retourne None en cas d'erreur
        logger.error("Aucun extrait n'a pu être chargé ou le format du fichier est incorrect.")
        sys.exit(1)
    
    # Analyser les extraits
    analyze_extracts(extract_definitions, output_path, args.use_mocks) # Passer l'argument use_mocks
    
    logger.info("Analyse rhétorique terminée avec succès.")

if __name__ == "__main__":
    main()