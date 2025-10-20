import uvicorn
import logging
from pathlib import Path

import sys

# Ajoute le répertoire racine du projet au PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
# Configure logging to a file
log_dir = Path(__file__).parent.parent / "_e2e_logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "backend_launcher.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def start_server():
    """Lances the Uvicorn server."""
    logger.info("Attempting to start Uvicorn server for E2E tests...")
    try:
        uvicorn.run(
            "argumentation_analysis.services.web_api.app:app",
            host="0.0.0.0",
            port=8095,
            log_level="debug",
        )
        logger.info("Uvicorn server shut down gracefully.")
    except Exception:
        logger.critical("Failed to start Uvicorn server.", exc_info=True)
        # Re-raise the exception to allow programmatic control
        raise


if __name__ == "__main__":
    start_server()
