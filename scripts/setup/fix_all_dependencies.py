#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script amélioré pour résoudre tous les problèmes de dépendances pour les tests.

Ce script installe toutes les dépendances nécessaires à partir de requirements-test.txt
et gère spécifiquement les problèmes connus avec certaines bibliothèques.
"""

import argumentation_analysis.core.environment

import subprocess
import sys
import os
import logging
import platform
import tempfile
import venv
import shutil
import ctypes
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fix_all_dependencies")

# Chemin vers le fichier requirements-test.txt
REQUIREMENTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "requirements-test.txt",
)


def run_command(cmd, cwd=None):
    """
    Exécute une commande shell et retourne le résultat.

    Args:
        cmd: Liste de chaînes représentant la commande et ses arguments
        cwd: Répertoire de travail pour l'exécution de la commande

    Returns:
        Tuple (returncode, stdout, stderr)
    """
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la commande {cmd}: {e}")
        return -1, "", str(e)


def install_package(package, version=None, upgrade=False, force_reinstall=False):
    """
    Installe un package Python avec pip.

    Args:
        package: Nom du package à installer
        version: Version spécifique à installer (optionnel)
        upgrade: Mettre à jour le package si déjà installé
        force_reinstall: Forcer la réinstallation même si déjà installé

    Returns:
        True si l'installation a réussi, False sinon
    """
    try:
        if version:
            package_spec = f"{package}=={version}"
        else:
            package_spec = package

        cmd = [sys.executable, "-m", "pip", "install"]

        if upgrade:
            cmd.append("--upgrade")

        if force_reinstall:
            cmd.append("--force-reinstall")

        cmd.append(package_spec)

        logger.info(f"Installation de {package_spec}...")
        returncode, stdout, stderr = run_command(cmd)

        if returncode == 0:
            logger.info(f"{package_spec} installé avec succès.")
            return True
        else:
            logger.error(f"Erreur lors de l'installation de {package_spec}: {stderr}")
            return False
    except Exception as e:
        logger.error(f"Exception lors de l'installation de {package}: {e}")
        return False


def install_from_requirements(requirements_file):
    """
    Installe les packages à partir d'un fichier requirements.

    Args:
        requirements_file: Chemin vers le fichier requirements

    Returns:
        True si l'installation a réussi, False sinon
    """
    try:
        logger.info(f"Installation des dépendances à partir de {requirements_file}...")
        cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_file]
        returncode, stdout, stderr = run_command(cmd)

        if returncode == 0:
            logger.info("Dépendances installées avec succès.")
            return True
        else:
            logger.error(f"Erreur lors de l'installation des dépendances: {stderr}")
            return False
    except Exception as e:
        logger.error(f"Exception lors de l'installation des dépendances: {e}")
        return False


def fix_numpy():
    """
    Résout les problèmes d'importation de numpy.

    Returns:
        True si la résolution a réussi, False sinon
    """
    # Désinstaller numpy s'il est déjà installé
    run_command([sys.executable, "-m", "pip", "uninstall", "-y", "numpy"])

    # Installer une version spécifique de numpy connue pour être compatible
    return install_package("numpy", "1.24.3", force_reinstall=True)


def fix_pandas():
    """
    Résout les problèmes d'importation de pandas.

    Returns:
        True si la résolution a réussi, False sinon
    """
    # Désinstaller pandas s'il est déjà installé
    run_command([sys.executable, "-m", "pip", "uninstall", "-y", "pandas"])

    # Installer une version spécifique de pandas connue pour être compatible
    return install_package("pandas", "2.0.3", force_reinstall=True)


def fix_jpype():
    """
    Résout les problèmes d'importation de jpype.

    Returns:
        True si la résolution a réussi, False sinon
    """
    # Désinstaller jpype s'il est déjà installé
    run_command([sys.executable, "-m", "pip", "uninstall", "-y", "JPype1"])

    # Installer une version spécifique de jpype connue pour être compatible
    return install_package("JPype1", "1.4.1", force_reinstall=True)


def fix_cryptography():
    """
    Résout les problèmes d'importation de cryptography.

    Returns:
        True si la résolution a réussi, False sinon
    """
    # Désinstaller cryptography s'il est déjà installé
    run_command([sys.executable, "-m", "pip", "uninstall", "-y", "cryptography"])

    # Installer les dépendances de cryptography
    install_package("setuptools", upgrade=True)
    install_package("wheel", upgrade=True)
    install_package("cffi", upgrade=True)

    # Installer cryptography
    return install_package("cryptography", "37.0.0", force_reinstall=True)


def fix_pytest_and_plugins():
    """
    Résout les problèmes avec pytest et ses plugins.

    Returns:
        True si la résolution a réussi, False sinon
    """
    # Désinstaller pytest et ses plugins s'ils sont déjà installés
    run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "uninstall",
            "-y",
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
        ]
    )

    # Installer pytest et ses plugins
    success = install_package("pytest", "7.4.0", force_reinstall=True)
    success = success and install_package(
        "pytest-asyncio", "0.21.1", force_reinstall=True
    )
    success = success and install_package("pytest-cov", "4.1.0", force_reinstall=True)

    return success


def create_test_venv():
    """
    Crée un environnement virtuel temporaire pour tester les installations.

    Returns:
        Chemin vers l'environnement virtuel créé ou None en cas d'échec
    """
    try:
        # Créer un répertoire temporaire
        temp_dir = tempfile.mkdtemp(prefix="test_venv_")
        logger.info(
            f"Création d'un environnement virtuel temporaire dans {temp_dir}..."
        )

        # Créer l'environnement virtuel
        venv.create(temp_dir, with_pip=True)

        logger.info("Environnement virtuel créé avec succès.")
        return temp_dir
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'environnement virtuel: {e}")
        return None


def test_installation_in_venv(venv_path):
    """
    Teste l'installation des dépendances dans un environnement virtuel.

    Args:
        venv_path: Chemin vers l'environnement virtuel

    Returns:
        True si les tests ont réussi, False sinon
    """
    try:
        # Déterminer le chemin vers l'exécutable Python dans l'environnement virtuel
        if platform.system() == "Windows":
            python_exe = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            python_exe = os.path.join(venv_path, "bin", "python")

        # Installer pip dans l'environnement virtuel
        logger.info("Installation de pip dans l'environnement virtuel...")
        cmd = [python_exe, "-m", "ensurepip"]
        run_command(cmd)

        # Mettre à jour pip
        logger.info("Mise à jour de pip dans l'environnement virtuel...")
        cmd = [python_exe, "-m", "pip", "install", "--upgrade", "pip"]
        run_command(cmd)

        # Installer les dépendances dans l'environnement virtuel
        logger.info("Installation des dépendances dans l'environnement virtuel...")
        cmd = [python_exe, "-m", "pip", "install", "-r", REQUIREMENTS_FILE]
        returncode, stdout, stderr = run_command(cmd)

        if returncode != 0:
            logger.error(
                f"Erreur lors de l'installation des dépendances dans l'environnement virtuel: {stderr}"
            )
            return False

        # Tester l'importation des modules problématiques
        logger.info("Test de l'importation des modules problématiques...")

        # Test de numpy
        cmd = [python_exe, "-c", "import numpy; print(numpy.__version__)"]
        returncode, stdout, stderr = run_command(cmd)
        if returncode != 0:
            logger.error(f"Erreur lors de l'importation de numpy: {stderr}")
            return False
        logger.info(f"numpy version: {stdout.strip()}")

        # Test de pandas
        cmd = [python_exe, "-c", "import pandas; print(pandas.__version__)"]
        returncode, stdout, stderr = run_command(cmd)
        if returncode != 0:
            logger.error(f"Erreur lors de l'importation de pandas: {stderr}")
            return False
        logger.info(f"pandas version: {stdout.strip()}")

        # Test de jpype
        cmd = [python_exe, "-c", "import jpype; print(jpype.__version__)"]
        returncode, stdout, stderr = run_command(cmd)
        if returncode != 0:
            logger.error(f"Erreur lors de l'importation de jpype: {stderr}")
            return False
        logger.info(f"jpype version: {stdout.strip()}")

        # Test de cryptography
        cmd = [python_exe, "-c", "import cryptography; print(cryptography.__version__)"]
        returncode, stdout, stderr = run_command(cmd)
        if returncode != 0:
            logger.error(f"Erreur lors de l'importation de cryptography: {stderr}")
            return False
        logger.info(f"cryptography version: {stdout.strip()}")

        # Test de pytest
        cmd = [python_exe, "-c", "import pytest; print(pytest.__version__)"]
        returncode, stdout, stderr = run_command(cmd)
        if returncode != 0:
            logger.error(f"Erreur lors de l'importation de pytest: {stderr}")
            return False
        logger.info(f"pytest version: {stdout.strip()}")

        logger.info(
            "Tous les tests d'importation ont réussi dans l'environnement virtuel."
        )
        return True
    except Exception as e:
        logger.error(f"Erreur lors des tests dans l'environnement virtuel: {e}")
        return False
    finally:
        # Supprimer l'environnement virtuel
        try:
            logger.info(f"Suppression de l'environnement virtuel {venv_path}...")
            shutil.rmtree(venv_path)
        except Exception as e:
            logger.warning(
                f"Erreur lors de la suppression de l'environnement virtuel: {e}"
            )


def check_build_tools():
    """
    Vérifie si Visual Studio Build Tools ou Visual Studio avec outils C++ est installé.

    Returns:
        True si Visual Studio Build Tools ou Visual Studio avec outils C++ est installé, False sinon
    """
    # Vérifier si on est sous Windows
    if platform.system() != "Windows":
        logger.info(
            "Système non-Windows détecté, pas besoin de Visual Studio Build Tools."
        )
        return True

    # Vérifier si vswhere.exe existe
    program_files = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    vswhere_path = os.path.join(
        program_files, "Microsoft Visual Studio", "Installer", "vswhere.exe"
    )

    if not os.path.exists(vswhere_path):
        logger.warning(
            "Visual Studio ne semble pas être installé (vswhere.exe non trouvé)."
        )
        return False

    # Rechercher d'abord Visual Studio Community/Professional/Enterprise avec les outils C++
    cmd = [
        vswhere_path,
        "-products",
        "*",
        "-requires",
        "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "-latest",
        "-property",
        "installationPath",
    ]
    returncode, stdout, stderr = run_command(cmd)

    if returncode == 0 and stdout.strip():
        logger.info(f"Visual Studio avec outils C++ trouvé à: {stdout.strip()}")
        return True

    # Si Visual Studio n'est pas trouvé, rechercher les Build Tools autonomes
    cmd = [
        vswhere_path,
        "-products",
        "Microsoft.VisualStudio.Product.BuildTools",
        "-requires",
        "Microsoft.VisualCpp.Tools.Host.x86",
        "-latest",
        "-property",
        "installationPath",
    ]
    returncode, stdout, stderr = run_command(cmd)

    if returncode != 0 or not stdout.strip():
        logger.warning(
            "Ni Visual Studio ni Visual Studio Build Tools avec les outils C++ ne semblent être installés."
        )
        return False

    logger.info(f"Visual Studio Build Tools trouvé à: {stdout.strip()}")
    return True


def fix_all_dependencies():
    """
    Résout tous les problèmes de dépendances.

    Returns:
        True si toutes les résolutions ont réussi, False sinon
    """
    success = True

    # Vérifier si Visual Studio Build Tools est installé
    build_tools_installed = check_build_tools()
    if not build_tools_installed:
        logger.warning(
            "Les outils de compilation C++ ne sont pas installés, ce qui peut causer des problèmes lors de l'installation de numpy, pandas et jpype."
        )
        logger.info(
            "Veuillez installer Visual Studio Build Tools 2022 avec les composants 'Développement Desktop en C++' depuis https://aka.ms/vs/17/release/vs_BuildTools.exe"
        )
    else:
        logger.info(
            "Visual Studio Build Tools est installé, les extensions C++ pourront être compilées."
        )

    # Mettre à jour pip
    logger.info("Mise à jour de pip...")
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

    # Installer setuptools et wheel
    logger.info("Installation de setuptools et wheel...")
    install_package("setuptools", upgrade=True)
    install_package("wheel", upgrade=True)

    # Configurer l'environnement pour utiliser les outils de compilation
    if build_tools_installed:
        logger.info(
            "Configuration de l'environnement pour utiliser les outils de compilation..."
        )
        os.environ["DISTUTILS_USE_SDK"] = "1"

    # Résoudre les problèmes de numpy
    logger.info("Résolution des problèmes de numpy...")
    if not fix_numpy():
        success = False
        logger.error(
            "Échec de l'installation de numpy. Vérifiez que Visual Studio Build Tools est correctement installé."
        )

    # Résoudre les problèmes de pandas
    logger.info("Résolution des problèmes de pandas...")
    if not fix_pandas():
        success = False
        logger.error(
            "Échec de l'installation de pandas. Vérifiez que Visual Studio Build Tools est correctement installé."
        )

    # Résoudre les problèmes de jpype
    logger.info("Résolution des problèmes de jpype...")
    if not fix_jpype():
        success = False
        logger.error(
            "Échec de l'installation de jpype. Vérifiez que Visual Studio Build Tools est correctement installé."
        )

    # Résoudre les problèmes de cryptography
    logger.info("Résolution des problèmes de cryptography...")
    if not fix_cryptography():
        success = False

    # Résoudre les problèmes de pytest et ses plugins
    logger.info("Résolution des problèmes de pytest et ses plugins...")
    if not fix_pytest_and_plugins():
        success = False

    # Installer les autres dépendances à partir du fichier requirements-test.txt
    logger.info("Installation des autres dépendances...")
    if not install_from_requirements(REQUIREMENTS_FILE):
        success = False

    # Tester les installations dans un environnement virtuel
    logger.info("Test des installations dans un environnement virtuel...")
    venv_path = create_test_venv()
    if venv_path:
        if not test_installation_in_venv(venv_path):
            logger.warning("Les tests dans l'environnement virtuel ont échoué.")
            # Ne pas considérer cela comme un échec global, car l'environnement principal peut fonctionner

    return success


if __name__ == "__main__":
    logger.info("Résolution de tous les problèmes de dépendances pour les tests...")

    if fix_all_dependencies():
        logger.info("Tous les problèmes de dépendances ont été résolus avec succès.")
        sys.exit(0)
    else:
        logger.error("Certains problèmes de dépendances n'ont pas pu être résolus.")
        sys.exit(1)
