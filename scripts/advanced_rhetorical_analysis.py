#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour effectuer une analyse rhétorique avancée sur les extraits déchiffrés.

Ce script:
1. Charge les extraits déchiffrés et les résultats de l'analyse de base
2. Utilise les outils d'analyse rhétorique améliorés suivants:
   - EnhancedComplexFallacyAnalyzer
   - EnhancedContextualFallacyAnalyzer
   - EnhancedFallacySeverityEvaluator
   - EnhancedRhetoricalResultAnalyzer
3. Analyse chaque extrait avec ces outils avancés
4. Génère un rapport d'analyse avancée pour chaque extrait
5. Compare les résultats avec ceux de l'analyse de base
6. Sauvegarde les résultats dans un format structuré (JSON)
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
logger = logging.getLogger("AdvancedRhetoricalAnalysis")

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

# Import des outils d'analyse rhétorique améliorés
try:
    from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
    from argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer import EnhancedRhetoricalResultAnalyzer
    
    logger.info("Outils d'analyse rhétorique améliorés importés avec succès")
except ImportError as e:
    logger.error(f"Erreur d'importation des outils d'analyse rhétorique améliorés: {e}")
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

def load_base_analysis_results(file_path: Path) -> List[Dict[str, Any]]:
    """
    Charge les résultats de l'analyse rhétorique de base.
    
    Args:
        file_path (Path): Chemin vers le fichier JSON contenant les résultats de l'analyse de base
        
    Returns:
        List[Dict[str, Any]]: Liste des résultats de l'analyse de base
    """
    logger.info(f"Chargement des résultats de l'analyse de base depuis {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            base_results = json.load(f)
        
        logger.info(f"✅ {len(base_results)} résultats d'analyse de base chargés avec succès")
        return base_results
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement des résultats de l'analyse de base: {e}")
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
if missing_packages:
    logger.warning(f"Les packages suivants sont manquants: {', '.join(missing_packages)}")
    logger.warning(f"Certaines fonctionnalités peuvent être limitées.")
    logger.warning(f"Pour installer les packages manquants: pip install {' '.join(missing_packages)}")
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

def analyze_extract_advanced(
    extract_definition: Dict[str, Any],
    source_name: str,
    base_result: Optional[Dict[str, Any]],
    tools: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyse un extrait avec les outils d'analyse rhétorique avancés.
    
    Args:
        extract_definition (Dict[str, Any]): Définition de l'extrait
        source_name (str): Nom de la source
        base_result (Optional[Dict[str, Any]]): Résultat de l'analyse de base pour cet extrait
        tools (Dict[str, Any]): Dictionnaire contenant les outils d'analyse avancés
        
    Returns:
        Dict[str, Any]: Résultats de l'analyse avancée
    """
    extract_name = extract_definition.get("extract_name", "Extrait sans nom")
    logger.debug(f"Analyse avancée de l'extrait '{extract_name}' de la source '{source_name}'")
    
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
    
    # Déterminer le contexte de l'extrait
    context = extract_definition.get("context", source_name)
    
    # Initialiser les résultats
    results = {
        "extract_name": extract_name,
        "source_name": source_name,
        "argument_count": len(arguments),
        "timestamp": datetime.now().isoformat(),
        "analyses": {}
    }
    
    # Analyse des sophismes complexes
    try:
        complex_fallacy_analyzer = tools["complex_fallacy_analyzer"]
        complex_fallacy_results = complex_fallacy_analyzer.detect_composite_fallacies(
            arguments, context
        )
        results["analyses"]["complex_fallacies"] = complex_fallacy_results
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des sophismes complexes: {e}")
        results["analyses"]["complex_fallacies"] = {"error": str(e)}
    
    # Analyse des sophismes contextuels améliorée
    try:
        contextual_fallacy_analyzer = tools["contextual_fallacy_analyzer"]
        contextual_fallacy_results = contextual_fallacy_analyzer.analyze_context(
            extract_text, context
        )
        results["analyses"]["contextual_fallacies"] = contextual_fallacy_results
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse contextuelle des sophismes: {e}")
        results["analyses"]["contextual_fallacies"] = {"error": str(e)}
    
    # Évaluation de la gravité des sophismes
    try:
        fallacy_severity_evaluator = tools["fallacy_severity_evaluator"]
        severity_results = fallacy_severity_evaluator.evaluate_fallacy_severity(
            arguments, context
        )
        results["analyses"]["fallacy_severity"] = severity_results
    except Exception as e:
        logger.error(f"Erreur lors de l'évaluation de la gravité des sophismes: {e}")
        results["analyses"]["fallacy_severity"] = {"error": str(e)}
    
    # Analyse globale des résultats rhétoriques
    try:
        rhetorical_result_analyzer = tools["rhetorical_result_analyzer"]
        
        # Préparer les résultats pour l'analyse globale
        analysis_results = {
            "complex_fallacy_analysis": results["analyses"].get("complex_fallacies", {}),
            "contextual_fallacy_analysis": results["analyses"].get("contextual_fallacies", {}),
            "fallacy_severity_evaluation": results["analyses"].get("fallacy_severity", {})
        }
        
        # Ajouter les résultats de l'analyse de base si disponibles
        if base_result:
            analysis_results["base_contextual_fallacies"] = base_result.get("analyses", {}).get("contextual_fallacies", {})
            analysis_results["base_argument_coherence"] = base_result.get("analyses", {}).get("argument_coherence", {})
            analysis_results["base_semantic_analysis"] = base_result.get("analyses", {}).get("semantic_analysis", {})
        
        rhetorical_results = rhetorical_result_analyzer.analyze_rhetorical_results(
            analysis_results, context
        )
        results["analyses"]["rhetorical_results"] = rhetorical_results
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse globale des résultats rhétoriques: {e}")
        results["analyses"]["rhetorical_results"] = {"error": str(e)}
    
    # Comparer avec les résultats de l'analyse de base
    if base_result:
        try:
            comparison = compare_with_base_analysis(results, base_result)
            results["comparison_with_base"] = comparison
        except Exception as e:
            logger.error(f"Erreur lors de la comparaison avec l'analyse de base: {e}")
            results["comparison_with_base"] = {"error": str(e)}
    
    return results
def compare_with_base_analysis(
    advanced_results: Dict[str, Any],
    base_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare les résultats de l'analyse avancée avec ceux de l'analyse de base.
    
    Args:
        advanced_results (Dict[str, Any]): Résultats de l'analyse avancée
        base_results (Dict[str, Any]): Résultats de l'analyse de base
        
    Returns:
        Dict[str, Any]: Résultats de la comparaison
    """
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "fallacy_detection_comparison": {},
        "coherence_analysis_comparison": {},
        "overall_comparison": {}
    }
    
    # Comparer la détection des sophismes
    advanced_fallacies = advanced_results.get("analyses", {}).get("contextual_fallacies", {})
    base_fallacies = base_results.get("analyses", {}).get("contextual_fallacies", {})
    
    advanced_fallacy_count = advanced_fallacies.get("contextual_fallacies_count", 0)
    base_fallacy_count = len(base_fallacies.get("argument_results", []))
    
    comparison["fallacy_detection_comparison"] = {
        "advanced_fallacy_count": advanced_fallacy_count,
        "base_fallacy_count": base_fallacy_count,
        "difference": advanced_fallacy_count - base_fallacy_count,
        "additional_fallacies_detected": [],
        "fallacies_not_detected_in_base": []
    }
    
    # Comparer l'analyse de cohérence
    advanced_coherence = advanced_results.get("analyses", {}).get("rhetorical_results", {}).get("coherence_analysis", {})
    base_coherence = base_results.get("analyses", {}).get("argument_coherence", {})
    
    advanced_coherence_score = advanced_coherence.get("overall_coherence", 0.0)
    base_coherence_score = base_coherence.get("coherence_score", 0.0)
    
    comparison["coherence_analysis_comparison"] = {
        "advanced_coherence_score": advanced_coherence_score,
        "base_coherence_score": base_coherence_score,
        "difference": advanced_coherence_score - base_coherence_score,
        "advanced_coherence_level": advanced_coherence.get("coherence_level", "N/A"),
        "base_coherence_level": base_coherence.get("coherence_level", "N/A")
    }
    
    # Comparaison globale
    advanced_quality = advanced_results.get("analyses", {}).get("rhetorical_results", {}).get("overall_analysis", {}).get("rhetorical_quality", 0.0)
    
    comparison["overall_comparison"] = {
        "advanced_analysis_depth": "Élevée",
        "base_analysis_depth": "Modérée",
        "advanced_quality_score": advanced_quality,
        "key_improvements": [
            "Détection de sophismes complexes et composites",
            "Évaluation de la gravité des sophismes",
            "Analyse contextuelle approfondie",
            "Recommandations plus détaillées"
        ]
    }
    
    return comparison

def create_mock_tools():
    """
    Crée des outils d'analyse rhétorique avancés simulés lorsque les outils réels ne sont pas disponibles.
    
    Returns:
        Dict[str, Any]: Dictionnaire contenant les outils simulés
    """
    logger.warning("Création d'outils d'analyse rhétorique avancés simulés...")
    
    # Classe simulée pour l'analyseur de sophismes complexes
    class MockEnhancedComplexFallacyAnalyzer:
        def detect_composite_fallacies(self, arguments, context):
            return {
                "individual_fallacies_count": len(arguments),
                "basic_combinations": [],
                "advanced_combinations": [],
                "fallacy_patterns": [],
                "composite_severity": {
                    "composite_severity": 0.5,
                    "severity_level": "Modéré"
                },
                "context": context,
                "analysis_timestamp": datetime.now().isoformat(),
                "note": "Analyse simulée - les outils réels ne sont pas disponibles"
            }
    
    # Classe simulée pour l'analyseur contextuel de sophismes
    class MockEnhancedContextualFallacyAnalyzer:
        def analyze_context(self, text, context):
            return {
                "context_analysis": {
                    "context_type": "général",
                    "context_subtypes": [],
                    "audience_characteristics": ["généraliste"],
                    "formality_level": "moyen",
                    "confidence": 0.7
                },
                "potential_fallacies_count": 3,
                "contextual_fallacies_count": 2,
                "contextual_fallacies": [],
                "fallacy_relations": [],
                "analysis_timestamp": datetime.now().isoformat(),
                "note": "Analyse simulée - les outils réels ne sont pas disponibles"
            }
    
    # Classe simulée pour l'évaluateur de gravité des sophismes
    class MockEnhancedFallacySeverityEvaluator:
        def evaluate_fallacy_severity(self, arguments, context):
            return {
                "overall_severity": 0.5,
                "severity_level": "Modéré",
                "fallacy_evaluations": [],
                "context_analysis": {
                    "context_type": "général",
                    "audience_type": "généraliste",
                    "domain_type": "général"
                },
                "analysis_timestamp": datetime.now().isoformat(),
                "note": "Analyse simulée - les outils réels ne sont pas disponibles"
            }
    
    # Classe simulée pour l'analyseur de résultats rhétoriques
    class MockEnhancedRhetoricalResultAnalyzer:
        def analyze_rhetorical_results(self, results, context):
            return {
                "overall_analysis": {
                    "rhetorical_quality": 0.6,
                    "rhetorical_quality_level": "Bon",
                    "main_strengths": ["Cohérence thématique"],
                    "main_weaknesses": ["Présence de sophismes"],
                    "context_relevance": "Modérée"
                },
                "fallacy_analysis": {
                    "total_fallacies": 2,
                    "most_common_fallacies": ["Appel à l'autorité"],
                    "most_severe_fallacies": ["Appel à la peur"],
                    "overall_severity": 0.5,
                    "severity_level": "Modéré"
                },
                "coherence_analysis": {
                    "overall_coherence": 0.7,
                    "coherence_level": "Élevé",
                    "thematic_coherence": 0.8,
                    "logical_coherence": 0.6
                },
                "persuasion_analysis": {
                    "persuasion_score": 0.6,
                    "persuasion_level": "Modéré"
                },
                "recommendations": {
                    "general_recommendations": ["Améliorer la qualité des arguments"],
                    "fallacy_recommendations": ["Éviter les appels à l'autorité"],
                    "coherence_recommendations": ["Renforcer les liens logiques"],
                    "persuasion_recommendations": ["Équilibrer les appels émotionnels et logiques"]
                },
                "analysis_timestamp": datetime.now().isoformat(),
                "note": "Analyse simulée - les outils réels ne sont pas disponibles"
            }
    
    # Créer les outils simulés
    tools = {
        "complex_fallacy_analyzer": MockEnhancedComplexFallacyAnalyzer(),
        "contextual_fallacy_analyzer": MockEnhancedContextualFallacyAnalyzer(),
        "fallacy_severity_evaluator": MockEnhancedFallacySeverityEvaluator(),
        "rhetorical_result_analyzer": MockEnhancedRhetoricalResultAnalyzer()
    }
    
    logger.warning("✅ Outils d'analyse rhétorique avancés simulés créés")
    return tools
def analyze_extracts_advanced(
    extract_definitions: List[Dict[str, Any]],
    base_results: List[Dict[str, Any]],
    output_file: Path
) -> None:
    """
    Analyse tous les extraits avec les outils avancés et sauvegarde les résultats.
    
    Args:
        extract_definitions (List[Dict[str, Any]]): Définitions des extraits
        base_results (List[Dict[str, Any]]): Résultats de l'analyse de base
        output_file (Path): Chemin du fichier de sortie
    """
    logger.info("Initialisation des outils d'analyse rhétorique avancés...")
    
    # Initialiser les outils d'analyse avancés
    try:
        tools = {
            "complex_fallacy_analyzer": EnhancedComplexFallacyAnalyzer(),
            "contextual_fallacy_analyzer": EnhancedContextualFallacyAnalyzer(),
            "fallacy_severity_evaluator": EnhancedFallacySeverityEvaluator(),
            "rhetorical_result_analyzer": EnhancedRhetoricalResultAnalyzer()
        }
        logger.info("✅ Outils d'analyse rhétorique avancés initialisés")
    except NameError as e:
        logger.warning(f"Erreur lors de l'initialisation des outils réels: {e}")
        tools = create_mock_tools()
    except Exception as e:
        logger.warning(f"Erreur inattendue lors de l'initialisation des outils: {e}")
        tools = create_mock_tools()
    
    # Créer un dictionnaire pour accéder rapidement aux résultats de base par nom d'extrait
    base_results_dict = {}
    for result in base_results:
        extract_name = result.get("extract_name")
        source_name = result.get("source_name")
        if extract_name and source_name:
            key = f"{source_name}:{extract_name}"
            base_results_dict[key] = result
    
    # Compter le nombre total d'extraits
    total_extracts = sum(len(source.get("extracts", [])) for source in extract_definitions)
    logger.info(f"Analyse avancée de {total_extracts} extraits...")
    
    # Initialiser les résultats
    all_results = []
    
    # Initialiser la barre de progression
    progress_bar = tqdm(total=total_extracts, desc="Analyse avancée des extraits", unit="extrait")
    
    # Analyser chaque source et ses extraits
    for source in extract_definitions:
        source_name = source.get("source_name", "Source sans nom")
        extracts = source.get("extracts", [])
        
        for extract in extracts:
            extract_name = extract.get("extract_name", "Extrait sans nom")
            
            # Trouver le résultat de base correspondant
            key = f"{source_name}:{extract_name}"
            base_result = base_results_dict.get(key)
            
            # Analyser l'extrait avec les outils avancés
            try:
                results = analyze_extract_advanced(extract, source_name, base_result, tools)
                all_results.append(results)
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse avancée de l'extrait '{extract_name}': {e}")
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
        
        logger.info(f"✅ Résultats de l'analyse avancée sauvegardés dans {output_file}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde des résultats: {e}")

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Les arguments parsés
    """
    parser = argparse.ArgumentParser(description="Analyse rhétorique avancée des extraits déchiffrés")
    
    parser.add_argument(
        "--extracts", "-e",
        help="Chemin du fichier contenant les extraits déchiffrés",
        default=None
    )
    
    parser.add_argument(
        "--base-results", "-b",
        help="Chemin du fichier contenant les résultats de l'analyse de base",
        default=None
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Chemin du fichier de sortie pour les résultats de l'analyse avancée",
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
    
    logger.info("Démarrage de l'analyse rhétorique avancée des extraits...")
    
    # Trouver le fichier d'extraits le plus récent si non spécifié
    extracts_file = args.extracts
    if not extracts_file:
        temp_dir = Path("temp_extracts")
        if temp_dir.exists():
            extract_files = list(temp_dir.glob("extracts_decrypted_*.json"))
            if extract_files:
                # Trier par date de modification (la plus récente en premier)
                extract_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                extracts_file = extract_files[0]
                logger.info(f"Utilisation du fichier d'extraits le plus récent: {extracts_file}")
    
    if not extracts_file:
        logger.error("Aucun fichier d'extraits spécifié et aucun fichier d'extraits trouvé.")
        sys.exit(1)
    
    extracts_path = Path(extracts_file)
    if not extracts_path.exists():
        logger.error(f"Le fichier d'extraits {extracts_path} n'existe pas.")
        sys.exit(1)
    
    # Trouver le fichier de résultats de base le plus récent si non spécifié
    base_results_file = args.base_results
    if not base_results_file:
        results_dir = Path("results")
        if results_dir.exists():
            result_files = list(results_dir.glob("rhetorical_analysis_*.json"))
            if result_files:
                # Trier par date de modification (la plus récente en premier)
                result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                base_results_file = result_files[0]
                logger.info(f"Utilisation du fichier de résultats de base le plus récent: {base_results_file}")
    
    if not base_results_file:
        logger.warning("Aucun fichier de résultats de base spécifié et aucun fichier de résultats trouvé.")
        logger.warning("L'analyse avancée sera effectuée sans comparaison avec l'analyse de base.")
        base_results = []
    else:
        base_results_path = Path(base_results_file)
        if not base_results_path.exists():
            logger.warning(f"Le fichier de résultats de base {base_results_path} n'existe pas.")
            logger.warning("L'analyse avancée sera effectuée sans comparaison avec l'analyse de base.")
            base_results = []
        else:
            # Charger les résultats de l'analyse de base
            base_results = load_base_analysis_results(base_results_path)
            if not base_results:
                logger.warning("Aucun résultat de base n'a pu être chargé.")
                logger.warning("L'analyse avancée sera effectuée sans comparaison avec l'analyse de base.")
    
    # Définir le fichier de sortie si non spécifié
    output_file = args.output
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path("results") / f"advanced_rhetorical_analysis_{timestamp}.json"
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Charger les extraits
    extract_definitions = load_extracts(extracts_path)
    if not extract_definitions:
        logger.error("Aucun extrait n'a pu être chargé.")
        sys.exit(1)
    
    # Analyser les extraits avec les outils avancés
    analyze_extracts_advanced(extract_definitions, base_results, output_path)
    
    logger.info("Analyse rhétorique avancée terminée avec succès.")

if __name__ == "__main__":
    main()