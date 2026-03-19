import json
import shutil
from pathlib import Path
from datetime import datetime

# Définition des chemins source et destination
SOURCE_DIR = Path("_temp/git_archeology_cache")
DEST_DIR = Path("docs/commits_audit")

def migrate_commit_cache():
    """
    Migre les fichiers de cache d'audit Git du répertoire temporaire
    vers le répertoire de documentation permanent, en les renommant
    pour un tri chronologique.
    """
    # S'assurer que le répertoire de destination existe
    try:
        DEST_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Répertoire de destination '{DEST_DIR}' assuré d'exister.")
    except OSError as e:
        print(f"Erreur lors de la création du répertoire de destination '{DEST_DIR}': {e}")
        return

    # Vérifier si le répertoire source existe
    if not SOURCE_DIR.exists() or not SOURCE_DIR.is_dir():
        print(f"Erreur : Le répertoire source '{SOURCE_DIR}' n'existe pas ou n'est pas un répertoire.")
        return

    print(f"Début de la migration des fichiers de '{SOURCE_DIR}' vers '{DEST_DIR}'...")
    migrated_files = 0

    # Itérer sur tous les fichiers .json dans le répertoire source
    for file_path in SOURCE_DIR.glob("*.json"):
        try:
            # Lire le contenu JSON du fichier
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extraire la date de l'auteur
            author_date_str = data.get("date")
            if not author_date_str:
                print(f"Avertissement : Champ 'date' manquant dans '{file_path.name}'. Fichier ignoré.")
                continue

            # Extraire le hash du commit du nom de fichier
            commit_hash = file_path.stem

            # Parser la date ISO 8601 et la formater
            # La méthode fromisoformat gère les fuseaux horaires
            dt_object = datetime.fromisoformat(author_date_str)
            formatted_date = dt_object.strftime("%Y-%m-%d-%H-%M-%S")

            # Construire le nouveau nom de fichier
            new_filename = f"{formatted_date}-{commit_hash}.json"
            new_filepath = DEST_DIR / new_filename

            # Déplacer et renommer le fichier
            shutil.move(file_path, new_filepath)
            migrated_files += 1

        except json.JSONDecodeError:
            print(f"Avertissement : Fichier JSON malformé '{file_path.name}'. Fichier ignoré.")
        except ValueError:
            print(f"Avertissement : Format de date invalide pour '{author_date_str}' dans '{file_path.name}'. Fichier ignoré.")
        except Exception as e:
            print(f"Une erreur inattendue est survenue lors du traitement de '{file_path.name}': {e}")

    print(f"\nMigration terminée. {migrated_files} fichier(s) déplacé(s) avec succès.")

if __name__ == "__main__":
    migrate_commit_cache()