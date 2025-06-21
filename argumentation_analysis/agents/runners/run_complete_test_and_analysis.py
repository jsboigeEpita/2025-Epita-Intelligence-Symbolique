#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Orchestrateur de haut niveau pour un cycle complet de test, analyse et rapport.

Ce script sert de point d'entrée principal pour exécuter un scénario de test
de bout en bout. Il s'agit d'un "chef d'orchestre" qui ne réalise aucune
analyse lui-même, mais qui lance d'autres scripts spécialisés dans un pipeline
asynchrone en trois étapes :

1.  **Exécution :** Lance le test d'orchestration complet des agents, qui produit
    un fichier de "trace" (généralement JSON) détaillant chaque étape de
    l'exécution.
2.  **Analyse :** Prend le fichier de trace généré et le passe à un script
    d'analyse qui produit un rapport lisible (généralement en Markdown).
3.  **Ouverture :** Ouvre automatiquement le rapport final avec l'application
    par défaut du système d'exploitation.
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

async def run_orchestration_test() -> Optional[str]:
    """
    Lance le script de test d'orchestration et récupère le chemin du fichier de trace.

    Cette fonction exécute `test_orchestration_complete.py` en tant que sous-processus.
    Elle analyse ensuite la sortie standard (stdout) du script pour trouver la ligne
    indiquant où la trace a été sauvegardée.

    En cas d'échec de la capture depuis stdout, elle implémente une logique de
    repli robuste qui cherche le fichier de trace le plus récent dans le
    répertoire de traces attendu.

    Returns:
        Optional[str]: Le chemin d'accès au fichier de trace généré, ou None si
        l'exécution ou la recherche du fichier a échoué.
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

async def run_trace_analysis(trace_path: str) -> Optional[str]:
    """
    Lance le script d'analyse de trace et récupère le chemin du rapport.

    Cette fonction prend le chemin d'un fichier de trace en entrée et exécute
    le script `analyse_trace_orchestration.py` avec ce chemin comme argument.
    Elle analyse ensuite la sortie du script pour trouver où le rapport final
    a été sauvegardé.

    Comme pour `run_orchestration_test`, elle dispose d'une logique de repli pour
    trouver le rapport le plus récent si l'analyse de la sortie standard échoue.

    Args:
        trace_path (str): Le chemin d'accès au fichier de trace à analyser.

    Returns:
        Optional[str]: Le chemin d'accès au rapport généré, ou None en cas d'erreur.
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

async def open_report(report_path: str):
    """
    Ouvre le fichier de rapport spécifié avec l'application par défaut du système.

    Cette fonction utilitaire est multi-plateforme et utilise la commande
    appropriée pour ouvrir un fichier (`os.startfile` pour Windows, `open` pour
    macOS, `xdg-open` pour Linux).

    Args:
        report_path (str): Le chemin d'accès au fichier de rapport à ouvrir.
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
    Point d'entrée principal du script qui exécute le pipeline complet.
    """
    logger.info("Démarrage du processus complet de test et d'analyse...")
    
    # Étape 1: Exécute le test d'orchestration pour générer une trace.
    trace_path = await run_orchestration_test()
    if not trace_path:
        logger.error("Abandon : Impossible de continuer sans trace d'orchestration.")
        return
    
    # Étape 2: Analyse la trace générée pour produire un rapport.
    report_path = await run_trace_analysis(trace_path)
    if not report_path:
        logger.error("Abandon : Impossible de générer le rapport d'analyse.")
        return
    
    # Étape 3: Ouvre le rapport final pour l'utilisateur.
    await open_report(report_path)
    
    logger.info("Processus complet de test et d'analyse terminé avec succès.")
    logger.info(f"Fichier de trace généré : {trace_path}")
    logger.info(f"Rapport d'analyse généré : {report_path}")

if __name__ == "__main__":
    asyncio.run(main())