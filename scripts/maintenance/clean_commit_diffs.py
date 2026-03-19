import os
import json
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_diffs_in_file(file_path):
    """
    Ouvre un fichier JSON, supprime la clé 'diff' de chaque objet dans la liste
    'files_changed', et sauvegarde les modifications.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        changes_made = False
        if 'files_changed' in data and isinstance(data['files_changed'], list):
            for file_change in data['files_changed']:
                if isinstance(file_change, dict) and 'diff' in file_change:
                    del file_change['diff']
                    changes_made = True
            
            if changes_made:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                logging.info(f"Nettoyé: {file_path}")
            else:
                logging.info(f"Aucun 'diff' à nettoyer dans: {file_path}")
        else:
            logging.warning(f"Clé 'files_changed' non trouvée ou invalide dans {file_path}")

    except json.JSONDecodeError:
        logging.error(f"Erreur de décodage JSON dans {file_path}")
    except Exception as e:
        logging.error(f"Erreur inattendue lors du traitement de {file_path}: {e}")

def main():
    """
    Fonction principale pour parcourir le répertoire et nettoyer les fichiers.
    """
    commit_dir = Path('docs/commits_audit')
    if not commit_dir.is_dir():
        logging.error(f"Le répertoire {commit_dir} n'existe pas.")
        return

    json_files = list(commit_dir.glob('*.json'))
    logging.info(f"Trouvé {len(json_files)} fichiers JSON à nettoyer.")

    for file_path in json_files:
        clean_diffs_in_file(file_path)

    logging.info("Nettoyage terminé.")

if __name__ == "__main__":
    main()