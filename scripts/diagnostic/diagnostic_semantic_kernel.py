#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de diagnostic pour la régression Semantic Kernel critique.
Diagnostique la version, les imports disponibles et identifie les problèmes.
"""

import sys
import os
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("diagnostic_semantic_kernel")

def test_semantic_kernel_basic():
    """Teste l'import de base de semantic_kernel"""
    try:
        import semantic_kernel
        logger.info(f"✓ semantic_kernel importé avec succès")
        logger.info(f"  Version: {semantic_kernel.__version__}")
        logger.info(f"  Chemin: {semantic_kernel.__file__}")
        return True, semantic_kernel.__version__
    except ImportError as e:
        logger.error(f"✗ Échec import semantic_kernel: {e}")
        return False, None
    except Exception as e:
        logger.error(f"✗ Erreur lors de l'import semantic_kernel: {e}")
        return False, None

def test_author_role():
    """Teste spécifiquement l'import de AuthorRole"""
    try:
        from semantic_kernel.contents import AuthorRole
        logger.info(f"✓ AuthorRole importé avec succès: {AuthorRole}")
        return True
    except ImportError as e:
        logger.error(f"✗ Échec import AuthorRole: {e}")
        logger.error("  RÉGRESSION CRITIQUE CONFIRMÉE: AuthorRole manquant!")
        return False
    except Exception as e:
        logger.error(f"✗ Erreur lors de l'import AuthorRole: {e}")
        return False

def test_semantic_kernel_contents():
    """Teste tous les imports du module contents"""
    try:
        import semantic_kernel.contents as contents
        logger.info(f"✓ Module semantic_kernel.contents importé")
        
        # Lister tous les attributs disponibles
        available_attrs = [attr for attr in dir(contents) if not attr.startswith('_')]
        logger.info(f"  Attributs disponibles: {sorted(available_attrs)}")
        
        # Vérifier les imports critiques
        critical_imports = ['AuthorRole', 'ChatMessageContent', 'TextContent']
        missing_imports = []
        
        for imp in critical_imports:
            if hasattr(contents, imp):
                logger.info(f"  ✓ {imp} disponible")
            else:
                logger.error(f"  ✗ {imp} MANQUANT")
                missing_imports.append(imp)
        
        return len(missing_imports) == 0, missing_imports
        
    except ImportError as e:
        logger.error(f"✗ Échec import semantic_kernel.contents: {e}")
        return False, []
    except Exception as e:
        logger.error(f"✗ Erreur lors du test contents: {e}")
        return False, []

def test_agents_import():
    """Teste l'import des agents"""
    try:
        from semantic_kernel import agents
        logger.info(f"✓ Module agents importé avec succès")
        return True
    except ImportError as e:
        logger.error(f"✗ Échec import agents: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Erreur lors de l'import agents: {e}")
        return False

def analyze_installed_packages():
    """Analyse les packages installés liés à semantic-kernel"""
    try:
        import subprocess
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            sk_packages = [line for line in lines if 'semantic' in line.lower() or 'kernel' in line.lower()]
            
            logger.info("Packages liés à semantic-kernel installés:")
            for pkg in sk_packages:
                logger.info(f"  {pkg}")
            
            return sk_packages
        else:
            logger.error(f"Erreur lors de l'exécution de pip list: {result.stderr}")
            return []
            
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des packages: {e}")
        return []

def get_version_history():
    """Obtient l'historique des versions disponibles"""
    try:
        import subprocess
        result = subprocess.run([sys.executable, '-m', 'pip', 'index', 'versions', 'semantic-kernel'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Versions disponibles de semantic-kernel:")
            logger.info(result.stdout)
        else:
            # Essayer une autre méthode
            result = subprocess.run([sys.executable, '-m', 'pip', 'search', 'semantic-kernel'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Informations sur semantic-kernel:")
                logger.info(result.stdout)
            else:
                logger.warning("Impossible d'obtenir les versions disponibles")
                
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des versions: {e}")

def main():
    """Exécute le diagnostic complet"""
    logger.info("=== DIAGNOSTIC RÉGRESSION SEMANTIC KERNEL ===")
    
    # Test 1: Import de base
    sk_ok, version = test_semantic_kernel_basic()
    if not sk_ok:
        logger.error("ARRÊT: Impossible d'importer semantic_kernel")
        return False
    
    # Test 2: Test AuthorRole spécifique
    author_role_ok = test_author_role()
    
    # Test 3: Test contents complet
    contents_ok, missing = test_semantic_kernel_contents()
    
    # Test 4: Test agents
    agents_ok = test_agents_import()
    
    # Analyse des packages
    packages = analyze_installed_packages()
    
    # Historique des versions
    get_version_history()
    
    # Résumé
    logger.info("\n=== RÉSUMÉ DIAGNOSTIC ===")
    logger.info(f"Version actuelle: {version}")
    logger.info(f"Import de base: {'✓' if sk_ok else '✗'}")
    logger.info(f"AuthorRole disponible: {'✓' if author_role_ok else '✗'}")
    logger.info(f"Contents complet: {'✓' if contents_ok else '✗'}")
    logger.info(f"Agents disponible: {'✓' if agents_ok else '✗'}")
    
    if missing:
        logger.error(f"Imports manquants: {missing}")
    
    # Déterminer si critique
    is_critical = not author_role_ok
    if is_critical:
        logger.error("🚨 RÉGRESSION CRITIQUE CONFIRMÉE!")
        logger.error("   AuthorRole manquant - 688+ tests bloqués")
        logger.error("   Action requise: Correction urgente de la version")
    else:
        logger.info("✓ Pas de régression critique détectée")
    
    return not is_critical

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)