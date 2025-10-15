import argumentation_analysis.core.environment
import json
from pathlib import Path

# Définir les chemins des fichiers
input_config_path = Path("_temp/config_fr_corrected.json")
output_config_path = Path("_temp/config_lemonde_deleted.json")
source_name_to_remove = "article_lemonde_elections_europeennes_2024"

# S'assurer que le répertoire de sortie existe
output_config_path.parent.mkdir(parents=True, exist_ok=True)

# Charger les données depuis le fichier d'entrée
data = load_json_from_file(input_config_path)

if data is None:
    # load_json_from_file logue déjà l'erreur
    exit(1)

# Filtrer les données en utilisant la fonction utilitaire
# Déterminer si la liste est à la racine ou sous une clé "sources"
list_key = None
if isinstance(data, dict) and "sources" in data and isinstance(data["sources"], list):
    list_key = "sources"
elif not isinstance(data, list):  # Si ce n'est ni une liste ni un dict avec "sources"
    print(
        f"Erreur : La structure des données dans '{input_config_path}' n'est pas une liste de sources attendue ou un dictionnaire avec une clé 'sources'."
    )
    # Sauvegarder les données originales si on ne sait pas comment filtrer
    if save_json_to_file(data, output_config_path):
        print(
            f"Données originales sauvegardées dans '{output_config_path}' car la structure n'a pas pu être filtrée."
        )
    else:
        print(
            f"Erreur lors de la sauvegarde des données originales dans '{output_config_path}'."
        )
    exit(1)

updated_data, items_removed = filter_list_in_json_data(
    json_data=data,
    filter_key="source_name",
    filter_value_to_remove=source_name_to_remove,
    list_path_key=list_key,
)

# Sauvegarder la liste filtrée dans le fichier de sortie
if save_json_to_file(updated_data, output_config_path):
    if items_removed > 0:
        print(
            f"{items_removed} instance(s) de la source '{source_name_to_remove}' ont été supprimées."
        )
    else:
        print(
            f"La source '{source_name_to_remove}' n'a pas été trouvée ou aucune modification n'était nécessaire."
        )
    print(
        f"La configuration mise à jour a été sauvegardée dans : '{output_config_path}'"
    )
else:
    # save_json_to_file logue déjà l'erreur
    exit(1)
