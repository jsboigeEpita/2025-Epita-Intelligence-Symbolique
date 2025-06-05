import os
import shutil
import pathlib

def remove_pycache_folders(start_path="."):
    """
    Supprime récursivement tous les dossiers __pycache__ à partir de start_path.
    """
    deleted_count = 0
    for path in pathlib.Path(start_path).rglob("__pycache__"):
        if path.is_dir():
            try:
                shutil.rmtree(path)
                print(f"Supprimé : {path}")
                deleted_count += 1
            except OSError as e:
                print(f"Erreur lors de la suppression de {path}: {e}")
    
    if deleted_count == 0:
        print("Aucun dossier __pycache__ trouvé à supprimer.")
    else:
        print(f"Suppression de {deleted_count} dossier(s) __pycache__ terminée.")

if __name__ == "__main__":
    # Exécuter depuis le répertoire courant du projet
    project_root = pathlib.Path(__file__).parent.resolve()
    print(f"Recherche des dossiers __pycache__ à partir de : {project_root}")
    remove_pycache_folders(project_root)