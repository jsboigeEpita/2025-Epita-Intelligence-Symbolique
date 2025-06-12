"""
Script pour analyser l'utilisation des répertoires config/ et data/ dans le code,
en utilisant l'utilitaire de project_core.
"""

import project_core.core_from_scripts.auto_env
import sys
import os
import json
import argparse
import re
import logging

# Ajuster le PYTHONPATH pour trouver project_core si le script est exécuté directement
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.abspath(os.path.join(script_dir, '..', '..')) # MODIFIÉ: Remonter à la racine du projet
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

try:
    from argumentation_analysis.utils.dev_tools.code_validation import analyze_directory_references
    # Configurer le logger du module importé si nécessaire, ou utiliser le logger local
    core_logger = logging.getLogger("project_core.dev_utils.code_validation")
    if not core_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        core_logger.addHandler(handler)
    core_logger.setLevel(logging.INFO) # Assurer un output visible

except ImportError as e:
    print(f"Erreur d'importation: {e}", file=sys.stderr)
    print("Assurez-vous que le PYTHONPATH est correctement configuré ou que le projet est installé.", file=sys.stderr)
    sys.exit(1)

# Configuration du logging pour ce script
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s: %(message)s',
    datefmt='%H:%M:%S'
)

def main():
    parser = argparse.ArgumentParser(description="Analyse des références aux répertoires dans le code.")
    parser.add_argument(
        '--dir',
        type=str,
        default=str(Path(project_root_dir) / 'src' / 'argumentation_analysis'), # MODIFIÉ: Cible src/argumentation_analysis
        help="Répertoire racine à analyser (par défaut: src/argumentation_analysis dans la racine du projet)."
    )
    parser.add_argument(
        '--output', 
        type=str, 
        default=os.path.join(project_root_dir, 'results', 'directory_usage_report.json'),
        help="Fichier de sortie pour le rapport JSON (par défaut: results/directory_usage_report.json)."
    )
    parser.add_argument(
        '--patterns',
        type=str,
        default='config/:data/', # Clés séparées par :, motifs regex associés implicitement
        help="Liste de motifs de répertoires à rechercher, séparés par des deux-points (ex: 'config/:data/')."
    )
    args = parser.parse_args()

    # Créer le répertoire de sortie s'il n'existe pas
    output_dir = os.path.dirname(args.output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Répertoire de sortie créé : {output_dir}")

    # Utiliser la fonction centralisée pour convertir la chaîne de motifs
    default_patterns_for_script = {
        "config_refs": "config/", # La fonction s'occupera de re.escape et re.compile
        "data_refs": "data/"
    }
    patterns_to_search = parse_colon_separated_string_to_regex_dict(
        patterns_string=args.patterns,
        default_patterns=default_patterns_for_script,
        key_suffix="_refs", # Conserver le suffixe original du script
        escape_pattern=True # Comportement original du script
    )

    if not patterns_to_search:
        # Cela ne devrait pas arriver si default_patterns est fourni et correct,
        # mais par sécurité, on logue si le dictionnaire est vide.
        logger.error("Aucun motif à rechercher, même après application des valeurs par défaut. Vérifier la logique de parsing_utils ou les motifs par défaut.")
        # On pourrait choisir de s'arrêter ici ou de continuer avec un dictionnaire vide.
        # Pour l'instant, on continue, la boucle d'analyse ne fera rien.
    
    logger.info(f"Analyse des références aux motifs {list(patterns_to_search.keys())} dans {args.dir}...")
    
    # Utiliser la fonction de project_core
    # Note: la fonction utilitaire logge déjà beaucoup, donc ce script peut se concentrer sur le rapport final.
    results = analyze_directory_references(args.dir, patterns_to_search)
    
    logger.info("\n--- Résumé de l'Analyse d'Utilisation des Répertoires ---")
    for pattern_name, data in results.items():
        logger.info(f"\nMotif '{pattern_name}':")
        logger.info(f"  Nombre total de références: {data['count']}")
        logger.info(f"  Nombre de fichiers contenant des références: {len(data['files'])}")
        
        if data["examples"]:
            logger.info("  Exemples (jusqu'à 5):")
            for example in data["examples"]:
                # Afficher le chemin relatif par rapport à project_root_dir pour la lisibilité
                try:
                    relative_file_path = os.path.relpath(example['file'], project_root_dir)
                except ValueError: # Peut arriver si les chemins sont sur des lecteurs différents (peu probable ici)
                    relative_file_path = example['file']
                logger.info(f"    {relative_file_path} (ligne {example['line']}): {example['content']}")
    
    # Générer un rapport JSON
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"\nRapport JSON généré avec succès : {args.output}")
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport JSON : {e}", exc_info=True)
        sys.exit(1)
        
    logger.info("Analyse terminée.")

if __name__ == "__main__":
    main()