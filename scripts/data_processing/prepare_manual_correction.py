import project_core.core_from_scripts.auto_env
import json
import pathlib
import argparse
# Ajout du chemin pour importer depuis project_core/argumentation_analysis, si ce script est exécuté directement
import sys
from pathlib import Path as PlPath # Pour éviter conflit avec import pathlib
sys.path.insert(0, str(PlPath(__file__).resolve().parent.parent.parent))
from argumentation_analysis.utils.correction_utils import prepare_manual_correction_data # Ajout de l'import

# La fonction prepare_manual_correction a été déplacée vers argumentation_analysis.utils.correction_utils
# et renommée en prepare_manual_correction_data.
# Le script principal ci-dessous l'appelle directement.
# L'ancien bloc try/except de la fonction originale est supprimé car la logique est dans l'utilitaire.
    
if __name__ == "__main__":
        parser = argparse.ArgumentParser(description="Prépare les informations pour la correction manuelle d'un extrait.")
        parser.add_argument("config_file", help="Chemin vers le fichier de configuration JSON des sources.")
        parser.add_argument("source_id", help="ID de la source à traiter.")
        parser.add_argument("extract_name", help="Nom de l'extrait à traiter.")
        parser.add_argument("output_file", help="Chemin vers le fichier de sortie pour les informations de débogage.")
        
        args = parser.parse_args()
        
        # Convertir les chemins en objets Path pour la nouvelle fonction
        config_path = pathlib.Path(args.config_file)
        output_path = pathlib.Path(args.output_file)
    
        # Appeler la fonction importée
        correction_data = prepare_manual_correction_data(
            config_path,
            args.source_id,
            args.extract_name,
            output_path
        )
        
        if correction_data:
            print(f"INFO: Données de correction préparées. Marqueur Début: {repr(correction_data.get('current_start_marker'))}")
            print(f"INFO: Marqueur Fin: {repr(correction_data.get('current_end_marker'))}")
            if not correction_data.get("source_full_text"):
                print(f"ATTENTION: Le full_text pour la source {args.source_id} est manquant dans les données retournées.")
        else:
            print(f"ERREUR: Échec de la préparation des données de correction pour source '{args.source_id}', extrait '{args.extract_name}'. Voir logs pour détails.")