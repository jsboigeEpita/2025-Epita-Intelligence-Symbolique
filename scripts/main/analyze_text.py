#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script CLI principal pour l'analyse de texte argumentatif.

Ce script fournit une interface en ligne de commande pour analyser des textes
et détecter les sophismes en utilisant le système d'analyse argumentative.
"""

import os
import sys
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Ajouter le répertoire racine du projet au chemin Python
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Imports du projet
try:
    from config.unified_config import get_config, get_test_config
    from argumentation_analysis.core.utils.text_utils import clean_text, truncate_text
    from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
except ImportError as e:
    print(f"Erreur d'import: {e}")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("analyze_text")


def setup_argument_parser() -> argparse.ArgumentParser:
    """
    Configure l'analyseur d'arguments de ligne de commande.
    
    Returns:
        ArgumentParser configuré
    """
    parser = argparse.ArgumentParser(
        description="Analyse de texte argumentatif et détection de sophismes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python scripts/main/analyze_text.py "Ce produit est excellent car tout le monde l'achète"
  python scripts/main/analyze_text.py --file input.txt --output results.json
  python scripts/main/analyze_text.py --text "Argument" --context "politique" --mock
        """
    )
    
    # Arguments principaux
    parser.add_argument(
        "text",
        nargs="?",
        help="Texte à analyser (optionnel si --file est utilisé)"
    )
    
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Fichier contenant le texte à analyser"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Fichier de sortie pour les résultats (JSON)"
    )
    
    parser.add_argument(
        "--context", "-c",
        type=str,
        default="général",
        help="Contexte d'analyse (politique, scientifique, commercial, etc.)"
    )
    
    # Options de configuration
    parser.add_argument(
        "--mock", "-m",
        action="store_true",
        help="Utiliser le mode mock pour les tests et démonstrations"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affichage verbeux"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mode debug avec logs détaillés"
    )
    
    parser.add_argument(
        "--format",
        choices=["json", "text", "table"],
        default="text",
        help="Format de sortie (défaut: text)"
    )
    
    parser.add_argument(
        "--max-length",
        type=int,
        default=5000,
        help="Longueur maximale du texte à analyser (défaut: 5000)"
    )
    
    return parser


def load_text_from_file(file_path: str) -> str:
    """
    Charge le texte depuis un fichier.
    
    Args:
        file_path: Chemin vers le fichier
        
    Returns:
        Contenu du fichier
        
    Raises:
        FileNotFoundError: Si le fichier n'existe pas
        UnicodeDecodeError: Si le fichier ne peut pas être décodé
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé: {file_path}")
        raise
    except UnicodeDecodeError:
        # Essayer avec un encodage différent
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Impossible de lire le fichier {file_path}: {e}")
            raise


def create_mock_analysis(text: str, context: str) -> Dict[str, Any]:
    """
    Crée une analyse mock pour les tests et démonstrations.
    
    Args:
        text: Texte à analyser
        context: Contexte d'analyse
        
    Returns:
        Résultats d'analyse mock
    """
    # Analyse simplifiée pour les mocks
    word_count = len(text.split())
    
    # Détection basique de mots-clés de sophismes
    mock_fallacies = []
    if "tout le monde" in text.lower():
        mock_fallacies.append({
            "type": "Appel à la popularité",
            "confidence": 0.8,
            "description": "Utilisation de la popularité comme argument",
            "text_fragment": "tout le monde"
        })
    
    if "expert" in text.lower() or "étude" in text.lower():
        mock_fallacies.append({
            "type": "Appel à l'autorité",
            "confidence": 0.7,
            "description": "Référence à une autorité sans justification",
            "text_fragment": "expert/étude"
        })
    
    return {
        "mode": "mock",
        "text_length": len(text),
        "word_count": word_count,
        "context": context,
        "fallacies_detected": len(mock_fallacies),
        "fallacies": mock_fallacies,
        "analysis_time": 0.1,
        "confidence_score": 0.75 if mock_fallacies else 0.9
    }


def analyze_text_real(text: str, context: str, config) -> Dict[str, Any]:
    """
    Effectue une analyse réelle du texte.
    
    Args:
        text: Texte à analyser
        context: Contexte d'analyse
        config: Configuration du système
        
    Returns:
        Résultats d'analyse
    """
    import time
    start_time = time.time()
    
    try:
        # Initialiser l'analyseur contextuel
        analyzer = ContextualFallacyAnalyzer()
        
        # Effectuer l'analyse
        results = analyzer.analyze_context(text, context)
        
        # Calculer le temps d'analyse
        analysis_time = time.time() - start_time
        
        # Formater les résultats
        formatted_results = {
            "mode": "real",
            "text_length": len(text),
            "word_count": len(text.split()),
            "context": context,
            "context_type": results.get("context_type", "inconnu"),
            "fallacies_detected": results.get("contextual_fallacies_count", 0),
            "fallacies": results.get("contextual_fallacies", []),
            "analysis_time": round(analysis_time, 3),
            "potential_fallacies": results.get("potential_fallacies_count", 0)
        }
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        # Retourner une analyse de base en cas d'erreur
        return {
            "mode": "fallback",
            "text_length": len(text),
            "word_count": len(text.split()),
            "context": context,
            "error": str(e),
            "fallacies_detected": 0,
            "fallacies": [],
            "analysis_time": time.time() - start_time
        }


def format_results(results: Dict[str, Any], output_format: str) -> str:
    """
    Formate les résultats selon le format demandé.
    
    Args:
        results: Résultats d'analyse
        output_format: Format de sortie (json, text, table)
        
    Returns:
        Résultats formatés
    """
    if output_format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    elif output_format == "table":
        output = []
        output.append("=" * 60)
        output.append("RÉSULTATS D'ANALYSE DE TEXTE")
        output.append("=" * 60)
        output.append(f"Mode d'analyse    : {results.get('mode', 'inconnu')}")
        output.append(f"Longueur du texte : {results.get('text_length', 0)} caractères")
        output.append(f"Nombre de mots    : {results.get('word_count', 0)}")
        output.append(f"Contexte          : {results.get('context', 'non spécifié')}")
        output.append(f"Sophismes détectés: {results.get('fallacies_detected', 0)}")
        output.append(f"Temps d'analyse   : {results.get('analysis_time', 0):.3f}s")
        
        if results.get('fallacies'):
            output.append("\nSOPHISMES DÉTECTÉS:")
            output.append("-" * 40)
            for i, fallacy in enumerate(results['fallacies'], 1):
                output.append(f"{i}. {fallacy.get('fallacy_type', fallacy.get('type', 'Inconnu'))}")
                output.append(f"   Confiance: {fallacy.get('confidence', 0):.2f}")
                if 'description' in fallacy:
                    output.append(f"   Description: {fallacy['description']}")
                if 'text_fragment' in fallacy:
                    output.append(f"   Fragment: '{fallacy['text_fragment']}'")
                output.append("")
        
        return "\n".join(output)
    
    else:  # format text
        output = []
        output.append(f"Analyse terminée en {results.get('analysis_time', 0):.3f}s")
        output.append(f"Texte analysé: {results.get('word_count', 0)} mots, contexte '{results.get('context', 'général')}'")
        
        fallacy_count = results.get('fallacies_detected', 0)
        if fallacy_count > 0:
            output.append(f"\n🚨 {fallacy_count} sophisme(s) détecté(s):")
            for fallacy in results.get('fallacies', []):
                fallacy_type = fallacy.get('fallacy_type', fallacy.get('type', 'Inconnu'))
                confidence = fallacy.get('confidence', 0)
                output.append(f"  • {fallacy_type} (confiance: {confidence:.0%})")
        else:
            output.append("\n✅ Aucun sophisme détecté")
        
        return "\n".join(output)


def save_results(results: Dict[str, Any], output_file: str):
    """
    Sauvegarde les résultats dans un fichier.
    
    Args:
        results: Résultats à sauvegarder
        output_file: Chemin du fichier de sortie
    """
    try:
        # Créer le répertoire parent si nécessaire
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder en JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Résultats sauvegardés dans {output_file}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde: {e}")


def main():
    """Fonction principale du script."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Configuration du logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Mode debug activé")
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    # Obtenir le texte à analyser
    text = None
    if args.file:
        try:
            text = load_text_from_file(args.file)
            logger.info(f"Texte chargé depuis {args.file} ({len(text)} caractères)")
        except Exception as e:
            print(f"Erreur lors du chargement du fichier: {e}")
            sys.exit(1)
    elif args.text:
        text = args.text
    else:
        print("Erreur: Vous devez fournir soit un texte soit un fichier à analyser.")
        parser.print_help()
        sys.exit(1)
    
    # Nettoyer et tronquer le texte
    text = clean_text(text)
    if len(text) > args.max_length:
        text = truncate_text(text, args.max_length)
        logger.warning(f"Texte tronqué à {args.max_length} caractères")
    
    if not text.strip():
        print("Erreur: Le texte à analyser est vide.")
        sys.exit(1)
    
    # Configuration du système
    if args.mock:
        logger.info("Mode mock activé")
        config = get_test_config()
    else:
        config = get_config()
    
    # Effectuer l'analyse
    logger.info("Début de l'analyse...")
    
    if args.mock or config.is_testing_mode():
        results = create_mock_analysis(text, args.context)
    else:
        results = analyze_text_real(text, args.context, config)
    
    # Formater et afficher les résultats
    formatted_output = format_results(results, args.format)
    print(formatted_output)
    
    # Sauvegarder si demandé
    if args.output:
        save_results(results, args.output)
    
    # Code de sortie basé sur les résultats
    if results.get('error'):
        sys.exit(1)
    elif results.get('fallacies_detected', 0) > 0:
        sys.exit(2)  # Sophismes détectés
    else:
        sys.exit(0)  # Succès


if __name__ == "__main__":
    main()