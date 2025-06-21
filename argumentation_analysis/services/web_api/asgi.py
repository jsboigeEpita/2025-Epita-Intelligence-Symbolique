import logging
import asyncio
from contextlib import asynccontextmanager
from starlette.applications import Starlette
from starlette.middleware.wsgi import WSGIMiddleware
import concurrent.futures

# --- Configuration du Logging ---
logger = logging.getLogger(__name__)

# --- Imports depuis notre application ---
# Ces imports doivent être légers. L'initialisation lourde est maintenant déplacée.
from argumentation_analysis.services.web_api.app import create_app, initialize_heavy_dependencies

# Variable globale pour contenir l'application WSGI (Flask)
# Elle sera initialisée pendant le lifespan de Starlette.
flask_app_instance = None

@asynccontextmanager
async def lifespan(app: Starlette):
    """
    Manage the startup and shutdown logic for the ASGI application.
    """
    global flask_app_instance
    logger.info("ASGI lifespan startup...")

    # --- Démarrage des dépendances lourdes dans un thread séparé ---
    # JPype et d'autres initialisations peuvent être bloquantes.
    # Les exécuter dans un executor évite de bloquer la boucle d'événements asyncio.
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        logger.info("Submitting heavy initialization to thread pool...")
        await loop.run_in_executor(pool, initialize_heavy_dependencies)
        logger.info("Heavy initialization finished.")

    # --- Création de l'application Flask ---
    # Maintenant que la JVM est prête, on peut créer l'app Flask qui dépend des services.
    logger.info("Creating Flask app instance...")
    flask_app_instance = create_app()
    logger.info("Flask app instance created.")

    # Wrapper l'app Flask dans le middleware pour la rendre compatible ASGI
    # et la monter dans l'application Starlette principale.
    app.mount("/", WSGIMiddleware(flask_app_instance))
    
    logger.info("ASGI startup complete. Application is ready.")
    yield
    # --- Code d'arrêt (si nécessaire) ---
    logger.info("ASGI lifespan shutdown...")


# --- Point d'entrée principal de l'application ASGI ---
# Créer l'application Starlette avec le gestionnaire de cycle de vie.
app = Starlette(lifespan=lifespan)