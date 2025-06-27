import uvicorn
import os
from pathlib import Path
import asyncio
import sys

# Le nom du fichier sentinelle, partagé avec le script de test
SERVER_READY_SENTINEL = "SERVER_READY.tmp"
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Ajouter la racine du projet au PYTHONPATH
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """
    Démarre le serveur web uvicorn pour les tests E2E.
    Utilise un fichier sentinelle pour signaler que le serveur est prêt.
    """
    # S'assurer que le répertoire du sentinel existe
    sentinel_path = PROJECT_ROOT / SERVER_READY_SENTINEL
    
    # Supprimer l'ancien fichier sentinelle s'il existe
    if sentinel_path.exists():
        sentinel_path.unlink()

    # Créer le fichier sentinelle pour signaler que le serveur est prêt
    sentinel_path.touch()

    try:
        uvicorn.run(
            "interface_web.app:app",
            host="127.0.0.1",
            port=8000,
            log_level="info",
            reload=False
        )
    except Exception as e:
        # En cas d'erreur de démarrage, écrire l'erreur dans un fichier
        # pour que le processus parent puisse la lire.
        with open("server_startup_error.log", "w") as f:
            f.write(str(e))
        # S'assurer que le fichier sentinelle n'existe pas si le démarrage a échoué
        if sentinel_path.exists():
            sentinel_path.unlink()
        raise

if __name__ == "__main__":
    # Définir la variable d'environnement pour contourner la vérification de l'environnement
    os.environ['E2E_TEST_RUNNING'] = 'true' 
    main()