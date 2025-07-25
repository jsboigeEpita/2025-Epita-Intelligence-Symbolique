# -*- coding: utf-8 -*-
"""
Script de diagnostic pour le crash de la JVM lié à l'ordre d'importation.

Ce script permet de vérifier de manière isolée l'impact de l'ordre d'importation
des bibliothèques `jpype` et `torch` sur la stabilité de la JVM, en utilisant
l'environnement de test `pytest` pour être au plus proche des conditions réelles.

Il exécute deux tests ciblés depuis `tests/debug/test_import_order.py`
dans des sous-processus séparés :
1.  `test_import_jpype_first` (connu pour causer un crash).
2.  `test_import_torch_first` (connu pour être stable).

Ceci permet de confirmer le diagnostic sans faire crasher le processus principal.
"""
import subprocess
import sys
import os
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _run_pytest_process(test_node_id):
    """Exécute un nœud de test pytest spécifique dans un sous-processus."""
    python_executable = sys.executable
    # Remonte de 4 niveaux pour atteindre la racine du projet depuis scripts/tools/debugging
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    
    logging.info(f"--- Lancement de pytest pour le test : {test_node_id} ---")
    logging.info(f"Project root: {project_root}")

    try:
        command = [
            python_executable,
            "-m",
            "pytest",
            "-s", # Pour voir les prints
            "-v",
            str(test_node_id) # Cible le test spécifique
        ]
        
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
            cwd=project_root # Exécuter depuis la racine du projet
        )

        logging.info(f"Pytest pour '{test_node_id}' terminé avec le code de retour : {process.returncode}")
        
        if process.stdout:
            logging.info(f"Sortie standard de '{test_node_id}':\n{process.stdout.strip()}")
        if process.stderr:
            logging.warning(f"Sortie d'erreur de '{test_node_id}':\n{process.stderr.strip()}")

        return process.returncode
    except subprocess.TimeoutExpired:
        logging.error(f"Le test '{test_node_id}' a dépassé le temps imparti et a été terminé.")
        return -1
    except Exception as e:
        logging.error(f"Une erreur est survenue en lançant le test '{test_node_id}': {e}", exc_info=True)
        return -2

def main():
    """Point d'entrée principal du script de diagnostic."""
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    test_file = "tests/debug/test_import_order.py"
    full_test_path = project_root / test_file

    if not full_test_path.exists():
        logging.error(f"Fichier de test introuvable : {full_test_path}")
        logging.error("Veuillez vous assurer que ce fichier existe avant de lancer le diagnostic.")
        return

    logging.info("="*50)
    logging.info("  Diagnostic du Crash JVM via Pytest (Ordre d'Importation)")
    logging.info("="*50)
    
    # Test 1: Ordre incorrect (jpype puis torch)
    logging.info(f"\n>>> ÉTAPE 1: Test de l'ordre d'importation incorrect via {test_file}::test_import_jpype_first")
    logging.info("ATTENDU: Pytest devrait crasher ou le test devrait échouer (xfail).")
    # Le test est marqué xfail, donc un succès pour pytest signifie que le test a échoué comme prévu.
    return_code_bad = _run_pytest_process(f"{test_file}::test_import_jpype_first")
    
    # Pytest retourne 0 si le test xfail échoue comme prévu.
    # Un vrai crash retournerait un code négatif ou > 1.
    if return_code_bad != 0:
        logging.info(f"RÉSULTAT: SUCCÈS du diagnostic. Le comportement attendu (crash/xfail) a été observé (code: {return_code_bad}).")
    else:
        # Si le code est 0, cela signifie que le test xfail a réussi, ce qui est un échec pour nous.
        logging.warning(f"RÉSULTAT: ÉCHEC du diagnostic. Le test xfail a réussi, le crash n'a pas eu lieu (code: {return_code_bad}).")

    # Test 2: Ordre correct (torch puis jpype)
    logging.info(f"\n>>> ÉTAPE 2: Test de l'ordre d'importation correct via {test_file}::test_import_torch_first")
    logging.info("ATTENDU: Pytest devrait se terminer avec succès (code de retour 0).")
    return_code_good = _run_pytest_process(f"{test_file}::test_import_torch_first")

    if return_code_good == 0:
        logging.info("RÉSULTAT: SUCCÈS du diagnostic. L'ordre d'importation correct est stable.")
    else:
        logging.warning(f"RÉSULTAT: ÉCHEC du diagnostic. L'ordre d'importation correct a échoué (code: {return_code_good}).")

    logging.info("\n" + "="*50)
    logging.info("                 Synthèse du Diagnostic")
    logging.info("="*50)
    
    # Le diagnostic est bon si le mauvais test ne retourne pas 0 et le bon test retourne 0.
    test_bad_ok = return_code_bad != 0
    test_good_ok = return_code_good == 0
    
    logging.info(f"Reproduction du crash/xfail (jpype -> torch): {'OUI' if test_bad_ok else 'NON'}")
    logging.info(f"Stabilité de l'ordre correct (torch -> jpype): {'OUI' if test_good_ok else 'NON'}")
    
    if test_bad_ok and test_good_ok:
        logging.info("\nCONCLUSION: Le diagnostic est confirmé. Le crash est bien causé par l'importation de `jpype` avant `torch`.")
    else:
        logging.error("\nCONCLUSION: Le diagnostic n'a pas pu être confirmé. Le comportement du système a peut-être changé ou le conflit est plus subtil.")

if __name__ == "__main__":
    main()