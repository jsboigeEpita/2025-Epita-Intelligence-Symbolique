#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal pour exécuter l'orchestration complète et analyser les résultats.

Ce script:
1. Exécute le test d'orchestration complète avec tous les agents
2. Analyse la trace générée
3. Produit un rapport détaillé
"""

import os
import sys
import asyncio
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire racine au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
root_dir = parent_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RunCompleteTestAndAnalysis")

async def run_orchestration_test():
    """
    Exécute le test d'orchestration complète.
    
    Returns:
        Le chemin vers la trace générée, ou None en cas d'erreur
    """
    logger.info("Exécution du test d'orchestration complète...")
    
    try:
        # Exécuter le script de test d'orchestration
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(parent_dir / "test_scripts" / "orchestration" / "test_orchestration_complete.py"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Erreur lors de l'exécution du test d'orchestration: {stderr.decode()}")
            return None
        
        # Analyser la sortie pour trouver le chemin de la trace
        stdout_text = stdout.decode()
        logger.info(stdout_text)
        
        # Chercher la ligne contenant le chemin de la trace
        trace_path = None
        for line in stdout_text.split('\n'):
            if "Trace complète sauvegardée dans" in line:
                # Extraire le chemin de la trace
                trace_path = line.split("Trace complète sauvegardée dans")[-1].strip()
                break
        
        if not trace_path:
            logger.warning("Impossible de trouver le chemin de la trace dans la sortie.")
            # Chercher le fichier de trace le plus récent
            traces_dir = Path(parent_dir) / "execution_traces" / "orchestration"
            if traces_dir.exists():
                trace_files = list(traces_dir.glob("trace_complete_*.json"))
                if trace_files:
                    trace_path = str(max(trace_files, key=lambda p: p.stat().st_mtime))
                    logger.info(f"Utilisation de la trace la plus récente: {trace_path}")
        
        return trace_path
    
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du test d'orchestration: {e}")
        return None

async def run_trace_analysis(trace_path):
    """
    Exécute l'analyse de la trace.
    
    Args:
        trace_path: Chemin vers le fichier de trace
        
    Returns:
        Le chemin vers le rapport généré, ou None en cas d'erreur
    """
    if not trace_path:
        logger.error("Aucun chemin de trace fourni pour l'analyse.")
        return None
    
    logger.info(f"Analyse de la trace {trace_path}...")
    
    try:
        # Exécuter le script d'analyse
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(parent_dir / "analysis_scripts" / "orchestration" / "analyse_trace_orchestration.py"), trace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Erreur lors de l'analyse de la trace: {stderr.decode()}")
            return None
        
        # Analyser la sortie pour trouver le chemin du rapport
        stdout_text = stdout.decode()
        logger.info(stdout_text)
        
        # Chercher la ligne contenant le chemin du rapport
        report_path = None
        for line in stdout_text.split('\n'):
            if "Rapport détaillé sauvegardé dans" in line:
                # Extraire le chemin du rapport
                report_path = line.split("Rapport détaillé sauvegardé dans")[-1].strip()
                break
        
        if not report_path:
            logger.warning("Impossible de trouver le chemin du rapport dans la sortie.")
            # Chercher le fichier de rapport le plus récent
            output_dir_path = Path(parent_dir) / "documentation" / "reports" / "orchestration"
            if output_dir_path.exists():
                report_files = list(output_dir_path.glob("rapport_analyse_orchestration_*.md"))
                if report_files:
                    report_path = str(max(report_files, key=lambda p: p.stat().st_mtime))
                    logger.info(f"Utilisation du rapport le plus récent: {report_path}")
        
        return report_path
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de la trace: {e}")
        return None

async def open_report(report_path):
    """
    Ouvre le rapport dans l'application par défaut.
    
    Args:
        report_path: Chemin vers le fichier de rapport
    """
    if not report_path:
        logger.error("Aucun chemin de rapport fourni pour l'ouverture.")
        return
    
    logger.info(f"Ouverture du rapport {report_path}...")
    
    try:
        # Détecter le système d'exploitation
        import platform
        system = platform.system()
        
        if system == "Windows":
            os.startfile(report_path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", report_path])
        else:  # Linux et autres
            subprocess.run(["xdg-open", report_path])
        
        logger.info("Rapport ouvert avec succès.")
    
    except Exception as e:
        logger.error(f"Erreur lors de l'ouverture du rapport: {e}")

async def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage du processus complet de test et d'analyse...")
    
    # Étape 1: Exécuter le test d'orchestration
    trace_path = await run_orchestration_test()
    
    if not trace_path:
        logger.error("Impossible de continuer sans trace d'orchestration.")
        return
    
    # Étape 2: Analyser la trace
    report_path = await run_trace_analysis(trace_path)
    
    if not report_path:
        logger.error("Impossible de générer le rapport d'analyse.")
        return
    
    # Étape 3: Ouvrir le rapport
    await open_report(report_path)
    
    logger.info("Processus complet de test et d'analyse terminé avec succès.")
    logger.info(f"Trace: {trace_path}")
    logger.info(f"Rapport: {report_path}")

if __name__ == "__main__":
    asyncio.run(main())