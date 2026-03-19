import argparse
import logging
import os

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

def rename_files_in_directory(path, dry_run=False):
    """
    Parcourt un répertoire, trouve les fichiers .json et les renomme
    avec un préfixe numérique sur 4 chiffres.
    """
    if not os.path.isdir(path):
        logging.error(f"Le chemin '{path}' n'est pas un répertoire valide.")
        return

    files_to_rename = sorted([f for f in os.listdir(path) if f.endswith('.json')])

    for index, filename in enumerate(files_to_rename, 1):
        new_name = f"{index:04d}_{filename}"
        old_path = os.path.join(path, filename)
        new_path = os.path.join(path, new_name)

        if dry_run:
            logging.info(f"DRY-RUN: Renommerait '{filename}' en '{new_name}'")
        else:
            try:
                os.rename(old_path, new_path)
                logging.info(f"Renommé '{filename}' en '{new_name}'")
            except OSError as e:
                logging.error(f"Erreur en renommant le fichier '{filename}': {e}")

def main():
    """
    Fonction principale pour parser les arguments et lancer le renommage.
    """
    parser = argparse.ArgumentParser(description="Renomme les fichiers de commit avec un préfixe numérique.")
    parser.add_argument('--path', required=True, help="Chemin vers le répertoire des fichiers de commit.")
    parser.add_argument('--dry-run', action='store_true', help="Affiche les changements sans les appliquer.")
    
    args = parser.parse_args()
    
    rename_files_in_directory(args.path, args.dry_run)

if __name__ == '__main__':
    main()