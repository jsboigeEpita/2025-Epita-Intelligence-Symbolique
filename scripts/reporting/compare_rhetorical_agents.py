import project_core.core_from_scripts.auto_env
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour comparer les performances des différents agents spécialistes d'analyse rhétorique.
Ce script utilise les utilitaires de argumentation_analysis.utils.reporting_utils.
"""

import sys
import logging
import argparse
from pathlib import Path

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from argumentation_analysis.utils.reporting_utils import (
        load_results_from_json,
        generate_performance_metrics_for_agents,
        generate_performance_visualizations,
        generate_markdown_performance_report
    )
    # Configurer le logger du module importé pour qu'il soit aussi verbeux que celui-ci
    utils_logger = logging.getLogger("argumentation_analysis.utils.reporting_utils")
    # Le logger de ce script sera configuré dans main()
except ImportError as e:
    print(f"Erreur critique: Impossible d'importer les modules nécessaires: {e}", file=sys.stderr)
    print("Assurez-vous que le PYTHONPATH est correctement configuré et que le projet est installé.", file=sys.stderr)
    sys.exit(1)

# Configuration du logging pour ce script
logger = logging.getLogger("CompareRhetoricalAgentsScript")
# Le niveau sera défini dans main() en fonction des arguments

def parse_arguments() -> argparse.Namespace:
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Comparaison des performances des agents d'analyse rhétorique.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--base-results", "-b", type=Path,
        help="Chemin du fichier JSON contenant les résultats de l'analyse de base.",
        default=project_root / "results" / "rhetorical_analysis_base.json" # Exemple de défaut
    )
    parser.add_argument(
        "--advanced-results", "-a", type=Path,
        help="Chemin du fichier JSON contenant les résultats de l'analyse avancée.",
        default=project_root / "results" / "advanced_rhetorical_analysis.json" # Exemple de défaut
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path,
        help="Répertoire de sortie pour les visualisations et le rapport.",
        default=project_root / "results" / "performance_comparison"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Affiche des informations de débogage supplémentaires."
    )
    return parser.parse_args()

def main():
    """Fonction principale du script."""
    args = parse_arguments()

    # Configuration du logging basée sur l'argument verbose
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    logger.setLevel(log_level)
    if 'utils_logger' in globals(): # S'assurer que l'import a réussi
        utils_logger.setLevel(log_level) # Aligner le logger de l'utilitaire

    logger.info("Démarrage de la comparaison des performances des agents d'analyse rhétorique...")
    logger.debug(f"Arguments de la ligne de commande: {args}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Répertoire de sortie: {args.output_dir.resolve()}")

    # Charger les résultats
    logger.info(f"Chargement des résultats de base depuis: {args.base_results}")
    base_results = load_results_from_json(args.base_results)
    if not base_results:
        logger.error(f"Aucun résultat de base n'a pu être chargé depuis {args.base_results}. Arrêt.")
        sys.exit(1)

    logger.info(f"Chargement des résultats avancés depuis: {args.advanced_results}")
    advanced_results = load_results_from_json(args.advanced_results)
    if not advanced_results:
        logger.error(f"Aucun résultat avancé n'a pu être chargé depuis {args.advanced_results}. Arrêt.")
        sys.exit(1)

    # Générer les métriques de performance
    logger.info("Génération des métriques de performance...")
    metrics = generate_performance_metrics_for_agents(base_results, advanced_results)
    if not metrics:
        logger.error("Échec de la génération des métriques de performance. Arrêt.")
        sys.exit(1)
    logger.debug(f"Métriques générées: {metrics}")

    # Générer les visualisations
    logger.info("Génération des visualisations...")
    generated_visuals = generate_performance_visualizations(metrics, args.output_dir)
    if generated_visuals:
        logger.info(f"Visualisations générées : {', '.join(generated_visuals)}")
    else:
        logger.info("Aucune visualisation générée (ou bibliothèques manquantes).")
        
    # Préparer les résumés pour le rapport Markdown
    base_summary = {
        "count": len(base_results),
        "sources": sorted(list(set(r.get("source_name", "Inconnue") for r in base_results)))
    }
    advanced_summary = {
        "count": len(advanced_results),
        "sources": sorted(list(set(r.get("source_name", "Inconnue") for r in advanced_results)))
    }

    # Générer le rapport Markdown
    logger.info("Génération du rapport Markdown...")
    report_file_path = args.output_dir / "rapport_comparaison_performance_agents.md"
    generate_markdown_performance_report(metrics, base_summary, advanced_summary, report_file_path)
    
    logger.info(f"✅ Comparaison des performances terminée. Résultats sauvegardés dans {args.output_dir.resolve()}")

if __name__ == "__main__":
    main()