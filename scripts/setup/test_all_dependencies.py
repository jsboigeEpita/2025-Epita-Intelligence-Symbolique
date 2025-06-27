#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script amélioré pour vérifier que toutes les dépendances sont correctement installées et fonctionnelles.

Ce script teste toutes les dépendances nécessaires pour le projet, y compris numpy, pandas, jpype,
cryptography, pytest et leurs plugins.
"""
import argumentation_analysis.core.environment

import sys
import os
import logging
import importlib
import subprocess
import platform
from pathlib import Path

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root_path_setup = Path(__file__).resolve().parent.parent.parent
if str(project_root_path_setup) not in sys.path:
    sys.path.insert(0, str(project_root_path_setup))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("test_all_dependencies")

# Liste des dépendances à tester
DEPENDENCIES = [
    # Dépendances principales
    {"name": "numpy", "min_version": "1.24.0"},
    {"name": "pandas", "min_version": "2.0.0"},
    {"name": "matplotlib", "min_version": "3.5.0"},
    {"name": "jpype", "min_version": "1.4.0", "import_name": "jpype"},
    {"name": "cryptography", "min_version": "37.0.0"},
    {"name": "cffi", "min_version": "1.15.0"},
    
    # Dépendances pour l'intégration Java
    {"name": "psutil", "min_version": "5.9.0"},
    
    # Dépendances pour le traitement de texte
    {"name": "tika", "min_version": "1.24.0", "import_name": "tika"},
    {"name": "jina", "min_version": "3.0.0"},
    
    # Dépendances pour les tests
    {"name": "pytest", "min_version": "7.0.0"},
    {"name": "pytest_asyncio", "min_version": "0.18.0", "import_name": "pytest_asyncio"},
    {"name": "pytest_cov", "min_version": "3.0.0", "import_name": "pytest_cov"},
    
    # Dépendances pour l'analyse de données
    {"name": "sklearn", "min_version": "1.0.0", "import_name": "scikit-learn"},
    {"name": "networkx", "min_version": "2.6.0"},
    
    # Dépendances pour l'IA et le ML
    {"name": "torch", "min_version": "2.0.0"},
    {"name": "transformers", "min_version": "4.20.0"},
    
    # Dépendances pour l'interface utilisateur
    {"name": "jupyter", "min_version": "1.0.0"},
    {"name": "notebook", "min_version": "6.4.0"},
    {"name": "jupyter_ui_poll", "min_version": "0.2.0"},
    {"name": "ipywidgets", "min_version": "7.7.0"}
]

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
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la commande {cmd}: {e}")
        return -1, "", str(e)

def compare_versions(version1, version2):
    """
    Compare deux versions de packages.
    
    Args:
        version1: Première version à comparer
        version2: Deuxième version à comparer
        
    Returns:
        -1 si version1 < version2, 0 si version1 == version2, 1 si version1 > version2
    """
    v1_parts = [int(x) for x in version1.split('.')]
    v2_parts = [int(x) for x in version2.split('.')]
    
    for i in range(min(len(v1_parts), len(v2_parts))):
        if v1_parts[i] < v2_parts[i]:
            return -1
        elif v1_parts[i] > v2_parts[i]:
            return 1
    
    if len(v1_parts) < len(v2_parts):
        return -1
    elif len(v1_parts) > len(v2_parts):
        return 1
    else:
        return 0

def test_dependency(dependency):
    """
    Teste une dépendance spécifique.
    
    Args:
        dependency: Dictionnaire contenant les informations sur la dépendance
        
    Returns:
        True si la dépendance est correctement installée et fonctionnelle, False sinon
    """
    name = dependency["name"]
    min_version = dependency.get("min_version")
    import_name = dependency.get("import_name", name)
    
    try:
        logger.info(f"Vérification de {name}...")
        
        # Essayer d'importer le module
        module = importlib.import_module(import_name)
        
        # Obtenir la version du module
        version = getattr(module, "__version__", "unknown")
        
        logger.info(f"{name} version: {version}")
        
        # Vérifier la version minimale si spécifiée
        if min_version and version != "unknown":
            if compare_versions(version, min_version) < 0:
                logger.warning(f"La version de {name} ({version}) est inférieure à la version minimale requise ({min_version}).")
                return False
        
        # Effectuer des tests spécifiques pour certaines dépendances
        if name == "numpy":
            test_numpy(module)
        elif name == "pandas":
            test_pandas(module)
        elif name == "jpype":
            test_jpype(module)
        elif name == "cryptography":
            test_cryptography(module)
        elif name == "pytest":
            test_pytest(module)
        
        logger.info(f"{name} est correctement installé et fonctionnel.")
        return True
    except ImportError as e:
        logger.error(f"Erreur d'importation de {name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors du test de {name}: {e}")
        return False

def test_numpy(np):
    """
    Teste les fonctionnalités de base de numpy.
    
    Args:
        np: Module numpy importé
    """
    # Tester quelques fonctionnalités de base
    arr = np.array([1, 2, 3, 4, 5])
    mean = np.mean(arr)
    sum_val = np.sum(arr)
    
    logger.info(f"numpy array: {arr}")
    logger.info(f"numpy mean: {mean}")
    logger.info(f"numpy sum: {sum_val}")

def test_pandas(pd):
    """
    Teste les fonctionnalités de base de pandas.
    
    Args:
        pd: Module pandas importé
    """
    # Tester quelques fonctionnalités de base
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    mean = df.mean()
    sum_val = df.sum()
    
    logger.info(f"pandas DataFrame:\n{df}")
    logger.info(f"pandas mean:\n{mean}")
    logger.info(f"pandas sum:\n{sum_val}")

def test_jpype(jpype):
    """
    Teste les fonctionnalités de base de jpype.
    
    Args:
        jpype: Module jpype importé
    """
    # Tester quelques fonctionnalités de base (sans initialiser la JVM)
    logger.info(f"jpype.isJVMStarted(): {jpype.isJVMStarted()}")
    logger.info(f"jpype.getDefaultJVMPath(): {jpype.getDefaultJVMPath()}")

def test_cryptography(crypto):
    """
    Teste les fonctionnalités de base de cryptography.
    
    Args:
        crypto: Module cryptography importé
    """
    # Tester quelques fonctionnalités de base
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    f = Fernet(key)
    token = f.encrypt(b"test message")
    decrypted = f.decrypt(token)
    
    logger.info(f"cryptography key: {key}")
    logger.info(f"cryptography token: {token}")
    logger.info(f"cryptography decrypted: {decrypted}")

def test_pytest(pytest):
    """
    Teste les fonctionnalités de base de pytest.
    
    Args:
        pytest: Module pytest importé
    """
    # Vérifier que les plugins sont installés
    plugins = pytest.config.getini("plugins") if hasattr(pytest, "config") else []
    logger.info(f"pytest plugins: {plugins}")

def check_build_tools():
    """
    Vérifie si Visual Studio Build Tools est installé.
    
    Returns:
        True si Visual Studio Build Tools est installé, False sinon
    """
    # Vérifier si on est sous Windows
    if platform.system() != "Windows":
        logger.info("Système non-Windows détecté, pas besoin de Visual Studio Build Tools.")
        return True
    
    # Vérifier si vswhere.exe existe
    program_files = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    vswhere_path = os.path.join(program_files, "Microsoft Visual Studio", "Installer", "vswhere.exe")
    
    if not os.path.exists(vswhere_path):
        logger.warning("Visual Studio Build Tools ne semble pas être installé (vswhere.exe non trouvé).")
        return False
    
    # Exécuter vswhere pour trouver les Build Tools
    cmd = [vswhere_path, "-products", "Microsoft.VisualStudio.Product.BuildTools",
           "-requires", "Microsoft.VisualCpp.Tools.Host.x86", "-latest", "-property", "installationPath"]
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode != 0 or not stdout.strip():
        logger.warning("Visual Studio Build Tools avec les outils C++ ne semble pas être installé.")
        return False
    
    logger.info(f"Visual Studio Build Tools trouvé à: {stdout.strip()}")
    return True

def test_all_dependencies():
    # Vérifier si Visual Studio Build Tools est installé
    build_tools_installed = check_build_tools()
    if not build_tools_installed:
        logger.warning("Les outils de compilation C++ ne sont pas installés, ce qui peut causer des problèmes lors de l'installation de numpy, pandas et jpype.")
        logger.warning("Pour installer les outils de compilation, exécutez le script install_build_tools.ps1")
        logger.warning("Pour plus d'informations, consultez le fichier README_INSTALLATION_OUTILS_COMPILATION.md")
    else:
        logger.info("Visual Studio Build Tools est installé, les extensions C++ pourront être compilées.")
    """
    Teste toutes les dépendances.
    
    Returns:
        True si toutes les dépendances sont correctement installées et fonctionnelles, False sinon
    """
    all_ok = True
    results = {}
    
    for dependency in DEPENDENCIES:
        name = dependency["name"]
        results[name] = test_dependency(dependency)
        all_ok = all_ok and results[name]
    
    # Afficher un résumé
    logger.info("\nRésumé des tests de dépendances:")
    logger.info("-" * 40)
    
    for name, ok in results.items():
        status = "OK" if ok else "ÉCHEC"
        logger.info(f"{name}: {status}")
    
    logger.info("-" * 40)
    
    if all_ok:
        logger.info("Toutes les dépendances sont correctement installées et fonctionnelles.")
    else:
        logger.error("Certaines dépendances ne sont pas correctement installées ou fonctionnelles.")
    
    return all_ok

def test_project_imports():
    """
    Teste les importations des modules du projet.
    
    Returns:
        True si toutes les importations ont réussi, False sinon
    """
    try:
        logger.info("\nTest des importations des modules du projet:")
        logger.info("-" * 40)
        
        # Liste des modules du projet à tester
        project_modules = [
            "argumentation_analysis",
            "argumentation_analysis.core",
            "argumentation_analysis.agents",
            "argumentation_analysis.services",
            "argumentation_analysis.ui",
            "argumentation_analysis.utils",
            "argumentation_analysis.orchestration"
        ]
        
        all_ok = True
        
        for module_name in project_modules:
            try:
                logger.info(f"Importation de {module_name}...")
                module = importlib.import_module(module_name)
                logger.info(f"Importation de {module_name} réussie.")
            except ImportError as e:
                logger.error(f"Erreur d'importation de {module_name}: {e}")
                all_ok = False
            except Exception as e:
                logger.error(f"Erreur lors de l'importation de {module_name}: {e}")
                all_ok = False
        
        logger.info("-" * 40)
        
        if all_ok:
            logger.info("Toutes les importations des modules du projet ont réussi.")
        else:
            logger.error("Certaines importations des modules du projet ont échoué.")
        
        return all_ok
    except Exception as e:
        logger.error(f"Erreur lors du test des importations des modules du projet: {e}")
        return False

if __name__ == "__main__":
    logger.info("Vérification des dépendances...")
    
    dependencies_ok = test_all_dependencies()
    project_imports_ok = test_project_imports()
    
    if dependencies_ok and project_imports_ok:
        logger.info("Toutes les dépendances sont correctement installées et fonctionnelles.")
        logger.info("Vous pouvez exécuter les tests avec la commande: pytest")
        sys.exit(0)
    else:
        logger.error("Certaines dépendances ne sont pas correctement installées ou fonctionnelles.")
        
        # Vérifier si Visual Studio Build Tools est installé
        build_tools_installed = check_build_tools()
        if not build_tools_installed:
            logger.error("Les outils de compilation C++ ne sont pas installés, ce qui est probablement la cause des problèmes.")
            logger.error("Exécutez d'abord le script install_build_tools.ps1 pour installer les outils de compilation.")
            logger.error("Puis exécutez le script fix_all_dependencies.py pour résoudre les problèmes.")
        else:
            logger.error("Exécutez le script fix_all_dependencies.py pour résoudre les problèmes.")
        
        sys.exit(1)