# utils/system_utils.py
import sys
import importlib
import subprocess
import logging

logger = logging.getLogger("Utils.System")
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); logger.addHandler(handler); logger.setLevel(logging.INFO)


def check_and_install(package_import_name: str, package_install_name: str):
    """Vérifie si un package est importable, sinon tente de l'installer."""
    try:
        importlib.import_module(package_import_name)
        logger.info(f"✔️ Dépendance '{package_import_name}' trouvée.")
        return True
    except ImportError:
        logger.warning(f"⚠️ Dépendance '{package_import_name}' manquante (package: {package_install_name}). Tentative d'installation...")
        try:
            # Utilisation de -q pour une sortie moins verbeuse, --disable-pip-version-check pour éviter les warnings
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", package_install_name])
            logger.info(f"✅ {package_install_name} installé avec succès.")
            # Recharger les modules ou invalider les caches peut être nécessaire dans certains environnements
            importlib.invalidate_caches()
            importlib.import_module(package_import_name) # Re-tester l'import
            logger.info(f"✔️ {package_import_name} trouvé après installation.")
            return True
        except Exception as e:
            logger.error(f"❌ Échec de l'installation/import de {package_install_name}: {e}")
            logger.warning("‼️ Un redémarrage du noyau (Kernel -> Restart Kernel) peut être nécessaire si l'import échoue toujours.")
            return False

# Optionnel : Log de chargement
module_logger = logging.getLogger(__name__)
module_logger.debug("Module utils.system_utils chargé.")