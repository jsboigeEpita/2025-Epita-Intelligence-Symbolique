import asyncio
import uvicorn
import os
from multiprocessing import Process

# Le même nom de fichier sentinelle que dans conftest.py
SERVER_READY_SENTINEL = "SERVER_READY.tmp"

async def run_backend_server():
    """Démarre le serveur backend uvicorn."""
    # Note: Le chemin est relatif au répertoire de travail au moment de l'exécution
    config = uvicorn.Config(
        "interface_web.backend.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )
    server = uvicorn.Server(config)
    print("[ServerScript] Backend server started.")
    await server.serve()

async def run_frontend_server():
    """Démarre le serveur de développement du frontend."""
    # Ceci est un exemple simple. Adaptez si votre frontend a une commande de démarrage différente.
    # Pour un frontend Dash, le démarrage se fait généralement via le même processus Python
    # que le backend. Si vous utilisez un serveur de dev distinct (par ex. npm),
    # vous devrez utiliser asyncio.create_subprocess_exec ici.
    # Dans notre cas, Dash est servi par la même app.
    # Cette fonction est donc un placeholder si un serveur distinct était nécessaire.
    await asyncio.sleep(1) # Simule le démarrage
    print("[ServerScript] Frontend logic running (if any).")


async def main():
    """
    Fonction principale pour démarrer les serveurs et créer le fichier sentinelle.
    """
    print("[ServerScript] Starting servers...")
    
    # Lancer le backend. Pour une app Dash, il sert aussi le frontend.
    server_task = asyncio.create_task(run_backend_server())

    # Laisser un peu de temps au serveur pour démarrer
    await asyncio.sleep(5) 
    
    # Créer le fichier sentinelle pour signaler que les serveurs sont prêts
    with open(SERVER_READY_SENTINEL, "w") as f:
        f.write("ready")
    print(f"[ServerScript] Sentinel file '{SERVER_READY_SENTINEL}' created.")
    print("[ServerScript] Servers are ready and running.")
    
    # Attendre que la tâche du serveur se termine (ce qui n'arrivera jamais
    # à moins d'une erreur ou d'une interruption externe).
    await server_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[ServerScript] Shutting down...")