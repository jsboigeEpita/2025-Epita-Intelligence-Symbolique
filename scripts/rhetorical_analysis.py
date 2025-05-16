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

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RhetoricalAnalysis")

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

def load_extracts(file_path: Path) -> List[Dict[str, Any]]:
    """
    Charge les extraits déchiffrés depuis un fichier JSON.
    
    Args:
        file_path (Path): Chemin vers le fichier JSON contenant les extraits déchiffrés
        
    Returns:
        List[Dict[str, Any]]: Liste des extraits déchiffrés
    """
    logger.info(f"Chargement des extraits depuis {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            extract_definitions = json.load(f)
        
        logger.info(f"✅ {len(extract_definitions)} sources chargées avec succès")
        return extract_definitions
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement des extraits: {e}")
        return []

def split_text_into_arguments(text: str) -> List[str]:
    """
    Divise un texte en arguments individuels.
    
    Cette fonction utilise des heuristiques simples pour diviser un texte
    en arguments individuels, en se basant sur la ponctuation et les connecteurs logiques.
    
    Args:
        text (str): Texte à diviser en arguments
        
    Returns:
        List[str]: Liste des arguments extraits
    """
    # Liste des délimiteurs d'arguments
    delimiters = [
        ". ", "! ", "? ", 
        ". \n", "! \n", "? \n",
        ".\n", "!\n", "?\n"
    ]
    
    # Remplacer les délimiteurs par un marqueur spécial
    for delimiter in delimiters:
        text = text.replace(delimiter, "|||")
    
    # Diviser le texte en utilisant le marqueur
    raw_arguments = text.split("|||")
    
    # Nettoyer les arguments
    arguments = []
    for arg in raw_arguments:
        arg = arg.strip()
        if arg and len(arg) > 10:  # Ignorer les arguments trop courts
            arguments.append(arg)
    
    return arguments

def generate_sample_text(extract_name: str, source_name: str) -> str:
    """
    Génère un texte d'exemple pour un extrait.
    
    Cette fonction est utilisée lorsque le contenu réel de l'extrait n'est pas disponible.
    
    Args:
        extract_name (str): Nom de l'extrait
        source_name (str): Nom de la source
        
    Returns:
        str: Texte d'exemple généré
    """
    # Générer un texte d'exemple basé sur le nom de l'extrait
    if "Lincoln" in extract_name or "Lincoln" in source_name:
        return """
        Nous sommes engagés dans une grande guerre civile, mettant à l'épreuve si cette nation, ou toute nation ainsi conçue et ainsi dédiée, peut perdurer.
        Nous sommes réunis sur un grand champ de bataille de cette guerre. Nous sommes venus dédier une portion de ce champ comme lieu de dernier repos pour ceux qui ont donné leur vie pour que cette nation puisse vivre.
        Il est tout à fait approprié et juste que nous le fassions. Mais, dans un sens plus large, nous ne pouvons pas dédier, nous ne pouvons pas consacrer, nous ne pouvons pas sanctifier ce sol.
        Les braves hommes, vivants et morts, qui ont lutté ici, l'ont consacré, bien au-delà de notre pauvre pouvoir d'ajouter ou de retrancher.
        """
    elif "Débat" in extract_name or "Discours" in extract_name:
        return """
        Mesdames et messieurs, je me présente devant vous aujourd'hui pour discuter d'une question d'importance nationale.
        Premièrement, nous devons considérer les principes fondamentaux qui guident notre nation.
        Deuxièmement, nous devons examiner les conséquences pratiques de ces principes dans notre vie quotidienne.
        Enfin, nous devons réfléchir à la manière dont nous pouvons avancer ensemble, en tant que nation unie, malgré nos différences.
        Je crois fermement que c'est par le dialogue et la compréhension mutuelle que nous pourrons surmonter nos défis.
        """
    else:
        return """
        L'argumentation est l'art de convaincre par le raisonnement logique et la présentation d'évidences.
        Un bon argument repose sur des prémisses solides et des inférences valides.
        Cependant, il faut être vigilant face aux sophismes qui peuvent miner la qualité d'un raisonnement.
        La cohérence argumentative est essentielle pour maintenir la crédibilité d'un discours.
        En conclusion, l'analyse rhétorique nous permet d'évaluer la qualité et l'efficacité des arguments présentés.
        """

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

def create_mock_tools():
    """
    Crée des outils d'analyse rhétorique simulés lorsque les outils réels ne sont pas disponibles.
    
    Returns:
        Dict[str, Any]: Dictionnaire contenant les outils simulés
    """
    logger.warning("Création d'outils d'analyse rhétorique simulés...")
    
    # Classe simulée pour le détecteur de sophismes contextuels
    class MockContextualFallacyDetector:
        def detect_multiple_contextual_fallacies(self, arguments, context_description):
            return {
                "argument_count": len(arguments),
                "context_description": context_description,
                "contextual_factors": {"domain": "général", "audience": "généraliste"},
                "argument_results": [{"detected_fallacies": []} for _ in arguments],
                "analysis_timestamp": datetime.now().isoformat(),
                "note": "Analyse simulée - les outils réels ne sont pas disponibles"
            }
    
    # Classe simulée pour l'évaluateur de cohérence argumentative
    class MockArgumentCoherenceEvaluator:
        def evaluate_coherence(self, arguments, context=None):
            return {
                "overall_coherence": {"score": 0.7, "level": "Bon"},
                "coherence_evaluations": {},
                "recommendations": ["Analyse simulée - les outils réels ne sont pas disponibles"],
                "context": context or "Analyse d'arguments",
                "timestamp": datetime.now().isoformat()
            }
    
    # Classe simulée pour l'analyseur sémantique d'arguments
    class MockSemanticArgumentAnalyzer:
        def analyze_multiple_arguments(self, arguments):
            return {
                "argument_count": len(arguments),
                "argument_analyses": [{"argument_index": i} for i in range(len(arguments))],
                "semantic_relations": [],
                "analysis_timestamp": datetime.now().isoformat(),
                "note": "Analyse simulée - les outils réels ne sont pas disponibles"
            }
    
    # Créer les outils simulés
    tools = {
        "fallacy_detector": MockContextualFallacyDetector(),
        "coherence_evaluator": MockArgumentCoherenceEvaluator(),
        "semantic_analyzer": MockSemanticArgumentAnalyzer()
    }
    
    logger.warning("✅ Outils d'analyse rhétorique simulés créés")
    return tools

def analyze_extracts(
    extract_definitions: List[Dict[str, Any]],
    output_file: Path
) -> None:
    """
    Analyse tous les extraits et sauvegarde les résultats.
    
    Args:
        extract_definitions (List[Dict[str, Any]]): Définitions des extraits
        output_file (Path): Chemin du fichier de sortie
    """
    logger.info("Initialisation des outils d'analyse rhétorique...")
    
    # Initialiser les outils d'analyse
    try:
        tools = {
            "fallacy_detector": ContextualFallacyDetector(),
            "coherence_evaluator": ArgumentCoherenceEvaluator(),
            "semantic_analyzer": SemanticArgumentAnalyzer()
        }
        logger.info("✅ Outils d'analyse rhétorique initialisés")
    except NameError as e:
        logger.warning(f"Erreur lors de l'initialisation des outils réels: {e}")
        tools = create_mock_tools()
    except Exception as e:
        logger.warning(f"Erreur inattendue lors de l'initialisation des outils: {e}")
        tools = create_mock_tools()
    
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
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Résultats sauvegardés dans {output_file}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde des résultats: {e}")

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
    extract_definitions = load_extracts(input_path)
    if not extract_definitions:
        logger.error("Aucun extrait n'a pu être chargé.")
        sys.exit(1)
    
    # Analyser les extraits
    analyze_extracts(extract_definitions, output_path)
    
    logger.info("Analyse rhétorique terminée avec succès.")

if __name__ == "__main__":
    main()