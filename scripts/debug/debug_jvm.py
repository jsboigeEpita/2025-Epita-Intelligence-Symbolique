#!/usr/bin/env python3
"""Script de diagnostic JVM pour identifier le problème d'initialisation"""

import os
import sys
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Ajout du chemin du projet
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

def diagnose_java_environment():
    """Diagnostic de l'environnement Java"""
    logger.info("=== DIAGNOSTIC ENVIRONNEMENT JAVA ===")
    
    # Variables d'environnement Java
    java_home = os.environ.get('JAVA_HOME')
    logger.info(f"JAVA_HOME: {java_home}")
    
    path = os.environ.get('PATH', '')
    java_paths = [p for p in path.split(os.pathsep) if 'java' in p.lower()]
    logger.info(f"Chemins Java dans PATH: {java_paths}")
    
    # JDK portable detecté
    portable_jdk_path = PROJECT_ROOT / "libs/portable_jdk/jdk-17.0.11+9"
    logger.info(f"JDK portable existe: {portable_jdk_path.exists()}")
    logger.info(f"Chemin JDK portable: {portable_jdk_path}")
    
    # Vérification jvm.dll
    jvm_dll_path = portable_jdk_path / "bin" / "server" / "jvm.dll"
    logger.info(f"jvm.dll existe: {jvm_dll_path.exists()}")
    logger.info(f"Chemin jvm.dll: {jvm_dll_path}")
    
    return portable_jdk_path, jvm_dll_path

def test_jpype_detection():
    """Test de détection JPype"""
    logger.info("\n=== TEST DETECTION JPYPE ===")
    
    try:
        import jpype
        logger.info(f"JPype version: {jpype.__version__}")
        
        # Test getDefaultJVMPath
        try:
            default_jvm_path = jpype.getDefaultJVMPath()
            logger.info(f"getDefaultJVMPath(): {default_jvm_path}")
        except Exception as e:
            logger.error(f"getDefaultJVMPath() failed: {e}")
        
        # Test isJVMStarted
        logger.info(f"isJVMStarted(): {jpype.isJVMStarted()}")
        
        return True
    except ImportError as e:
        logger.error(f"Impossible d'importer JPype: {e}")
        return False

def test_jvm_startup(jvm_dll_path):
    """Test de démarrage JVM"""
    logger.info(f"\n=== TEST DEMARRAGE JVM avec {jvm_dll_path} ===")
    
    try:
        import jpype
        
        if jpype.isJVMStarted():
            logger.info("JVM déjà démarrée, arrêt d'abord")
            jpype.shutdownJVM()
        
        # Test 1: Démarrage automatique
        logger.info("Test 1: Démarrage automatique")
        try:
            jpype.startJVM(convertStrings=False)
            logger.info("SUCCESS: Démarrage automatique réussi")
            jpype.shutdownJVM()
        except Exception as e:
            logger.error(f"ECHEC démarrage automatique: {e}")
        
        # Test 2: Démarrage avec chemin explicite
        logger.info(f"Test 2: Démarrage avec chemin explicite: {jvm_dll_path}")
        try:
            jpype.startJVM(str(jvm_dll_path), convertStrings=False)
            logger.info("SUCCESS: Démarrage avec chemin explicite réussi")
            jpype.shutdownJVM()
        except Exception as e:
            logger.error(f"ECHEC démarrage avec chemin explicite: {e}")
            
    except ImportError:
        logger.error("JPype non disponible")

def set_java_environment(portable_jdk_path):
    """Définit les variables d'environnement Java"""
    logger.info(f"\n=== CONFIGURATION ENVIRONNEMENT JAVA ===")
    
    # Set JAVA_HOME
    java_home = str(portable_jdk_path)
    os.environ['JAVA_HOME'] = java_home
    logger.info(f"JAVA_HOME défini sur: {java_home}")
    
    # Ajouter bin au PATH
    java_bin = str(portable_jdk_path / "bin")
    current_path = os.environ.get('PATH', '')
    if java_bin not in current_path:
        os.environ['PATH'] = f"{java_bin}{os.pathsep}{current_path}"
        logger.info(f"Ajouté au PATH: {java_bin}")

def main():
    """Fonction principale de diagnostic"""
    logger.info("Début du diagnostic JVM")
    
    # Diagnostic environnement
    portable_jdk_path, jvm_dll_path = diagnose_java_environment()
    
    # Configuration environnement
    set_java_environment(portable_jdk_path)
    
    # Test JPype
    if not test_jpype_detection():
        return False
        
    # Test démarrage JVM
    test_jvm_startup(jvm_dll_path)
    
    logger.info("\nDiagnostic terminé")
    return True

if __name__ == "__main__":
    main()