#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utilitaires système pour l'exécution de commandes et la gestion des processus.

Ce module fournit des fonctions pour interagir avec le système d'exploitation,
notamment pour exécuter des commandes shell de manière sécurisée et contrôlée,
en capturant leurs sorties et codes de retour.
"""

import subprocess
import logging
import shlex
from pathlib import Path
from typing import Optional, Tuple, Dict

# Configuration initiale du logger pour ce module.
# Il est préférable que l'application configure le logging de manière centralisée.
# Ceci est un fallback si aucune configuration n'est fournie par l'application.
logger = logging.getLogger(__name__)
if not logger.hasHandlers():  # Vérifie si des handlers sont déjà attachés
    logging.basicConfig(
        level=logging.INFO,  # Niveau par défaut, peut être surchargé par la config applicative
        format="%(asctime)s [%(levelname)s] [%(name)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_shell_command(
    command: str,
    work_dir: Optional[Path] = None,
    timeout_seconds: int = 60,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    """
    Exécute une commande shell, capture sa sortie, son erreur et son code de retour.

    La fonction gère les timeouts, les commandes non trouvées et d'autres exceptions
    d'exécution, en retournant des codes de retour spécifiques et les sorties
    disponibles plutôt que de lever directement les exceptions.

    :param command: La commande shell complète à exécuter.
    :type command: str
    :param work_dir: Le répertoire de travail optionnel pour l'exécution de la commande.
                     Si None, le répertoire de travail actuel du processus est utilisé.
    :type work_dir: Optional[Path], optional
    :param timeout_seconds: Le délai d'attente maximal en secondes pour la commande.
    :type timeout_seconds: int, optional
    :param env: Un dictionnaire optionnel de variables d'environnement.
    :type env: Optional[Dict[str, str]], optional
    :return: Un tuple contenant :
             - `return_code` (int): Le code de retour de la commande.
               Des valeurs négatives spécifiques sont utilisées pour les erreurs internes
               (ex: -9 pour timeout, -10 pour commande non trouvée).
             - `stdout_str` (str): La sortie standard (stdout) de la commande,
               décodée en UTF-8 et nettoyée (strip).
             - `stderr_str` (str): La sortie d'erreur (stderr) de la commande,
               décodée en UTF-8 et nettoyée (strip).
    :rtype: Tuple[int, str, str]

    Comportement en cas d'erreur :
        - `subprocess.TimeoutExpired`: Loggue une erreur, retourne le code -9.
        - `FileNotFoundError`: Loggue une erreur, retourne le code -10.
        - Autres `Exception`: Loggue une erreur, retourne le code -11.
        Dans tous les cas d'erreur, stdout et stderr sont retournés s'ils ont pu être capturés.
    """
    if work_dir:
        logger.info(
            f"Exécution de la commande : '{command}' dans le répertoire '{work_dir}' avec un timeout de {timeout_seconds}s."
        )
    else:
        logger.info(
            f"Exécution de la commande : '{command}' avec un timeout de {timeout_seconds}s."
        )

    try:
        # shlex.split est crucial pour gérer correctement les commandes avec des arguments
        # contenant des espaces ou nécessitant une interprétation de type shell.
        process = subprocess.run(
            shlex.split(command),
            cwd=work_dir,  # Peut être None, subprocess.run gère cela.
            capture_output=True,
            text=True,  # Décode stdout/stderr en str (UTF-8 par défaut)
            timeout=timeout_seconds,
            check=False,  # Important: ne pas lever CalledProcessError pour gérer nous-mêmes
            env=env,
        )
        stdout_str = process.stdout.strip() if process.stdout else ""
        stderr_str = process.stderr.strip() if process.stderr else ""
        return_code = process.returncode

        logger.info(
            f"Commande '{command}' terminée avec le code de retour : {return_code}."
        )
        if stdout_str:
            # Logguer en DEBUG car stdout peut être très volumineux
            logger.debug(f"Stdout:\n{stdout_str}")
        if stderr_str:
            # Logguer en DEBUG pour la même raison
            logger.debug(f"Stderr:\n{stderr_str}")

        return return_code, stdout_str, stderr_str

    except subprocess.TimeoutExpired as e:
        logger.error(
            f"La commande '{command}' a expiré après {timeout_seconds} secondes."
        )
        # e.stdout et e.stderr sont des bytes, il faut les décoder.
        stdout_str = (
            e.stdout.decode("utf-8", errors="replace").strip() if e.stdout else ""
        )
        stderr_str = (
            e.stderr.decode("utf-8", errors="replace").strip() if e.stderr else ""
        )
        logger.debug(f"Stdout (avant timeout):\n{stdout_str}")
        logger.debug(f"Stderr (avant timeout):\n{stderr_str}")
        return -9, stdout_str, stderr_str  # Code de retour spécifique pour timeout

    except FileNotFoundError:
        # Cette exception est levée si la commande elle-même n'est pas trouvée.
        cmd_name = shlex.split(command)[0]
        logger.error(
            f"Erreur : La commande ou l'exécutable '{cmd_name}' n'a pas été trouvé."
        )
        return -10, "", f"Commande non trouvée: {cmd_name}"  # Code spécifique

    except Exception as e:
        # Capturer toute autre exception imprévue durant subprocess.run ou la gestion des sorties.
        logger.error(
            f"Une erreur inattendue est survenue lors de l'exécution de '{command}': {type(e).__name__} - {e}"
        )
        # Tenter de récupérer stdout/stderr si l'exception les contient (rare pour Exception générique)
        stdout_bytes = getattr(e, "stdout", None)
        stderr_bytes = getattr(e, "stderr", None)

        stdout_str = (
            stdout_bytes.decode("utf-8", errors="replace").strip()
            if isinstance(stdout_bytes, bytes)
            else ""
        )
        stderr_str = (
            stderr_bytes.decode("utf-8", errors="replace").strip()
            if isinstance(stderr_bytes, bytes)
            else str(e)
        )

        logger.debug(f"Stdout (sur erreur inattendue):\n{stdout_str}")
        logger.debug(f"Stderr (sur erreur inattendue):\n{stderr_str}")
        return (
            -11,
            stdout_str,
            stderr_str,
        )  # Code de retour générique pour autres erreurs


if __name__ == "__main__":
    import sys  # Déplacé ici pour être au début du bloc de test

    # Section de test pour la fonction run_shell_command
    logger.info("Test de la fonction run_shell_command...")

    # Test 1: Commande simple qui réussit
    logger.info("\n--- Test 1: Commande simple (echo) ---")
    ret_code, out, err = run_shell_command("echo Hello World")
    logger.info(f"Code retour: {ret_code}, Sortie: '{out}', Erreur: '{err}'")
    assert ret_code == 0, f"Test 1 Échoué: Code retour attendu 0, obtenu {ret_code}"
    assert (
        out == "Hello World"
    ), f"Test 1 Échoué: Sortie attendue 'Hello World', obtenue '{out}'"
    assert err == "", f"Test 1 Échoué: Erreur attendue '', obtenue '{err}'"

    # Test 2: Commande avec erreur
    logger.info(
        "\n--- Test 2: Commande avec erreur (script Python qui sort avec 1) ---"
    )
    python_executable = Path(sys.executable).name  # python, python.exe, python3 etc.
    cmd_erreur = f'{python_executable} -c "import sys; sys.exit(1)"'
    ret_code, out, err = run_shell_command(cmd_erreur)
    logger.info(f"Code retour: {ret_code}, Sortie: '{out}', Erreur: '{err}'")
    assert ret_code == 1, f"Test 2 Échoué: Code retour attendu 1, obtenu {ret_code}"

    # Test 3: Commande avec timeout
    logger.info("\n--- Test 3: Commande avec timeout (sleep) ---")
    cmd_timeout = f'{python_executable} -c "import time; time.sleep(5)"'
    ret_code, out, err = run_shell_command(cmd_timeout, timeout_seconds=2)
    logger.info(f"Code retour: {ret_code}, Sortie: '{out}', Erreur: '{err}'")
    assert (
        ret_code == -9
    ), f"Test 3 Échoué: Code retour attendu -9 (timeout), obtenu {ret_code}"

    # Test 4: Commande dans un répertoire de travail spécifique
    logger.info("\n--- Test 4: Commande dans un répertoire de travail spécifique ---")
    temp_dir_name = "temp_test_dir_run_shell_system_utils"  # Nom plus spécifique
    temp_dir = Path(temp_dir_name)
    if not temp_dir.exists():
        temp_dir.mkdir(parents=True, exist_ok=True)

    test_file_in_temp_dir = "cwd_test_system.txt"
    path_to_test_file_str = str(temp_dir / test_file_in_temp_dir).replace(
        "\\", "/"
    )  # Pour la chaîne de commande

    cmd_workdir = f"{python_executable} -c \"import os; f=open('{path_to_test_file_str}', 'w'); f.write(os.getcwd()); f.close()\""

    ret_code, out, err = run_shell_command(cmd_workdir, work_dir=temp_dir)
    logger.info(f"Code retour: {ret_code}, Sortie: '{out}', Erreur: '{err}'")
    assert ret_code == 0, f"Test 4 Échoué: Code retour attendu 0, obtenu {ret_code}"

    file_content = ""
    full_test_file_path = temp_dir / test_file_in_temp_dir
    if full_test_file_path.exists():
        with open(full_test_file_path, "r") as f:
            file_content = f.read()
        full_test_file_path.unlink()

    if temp_dir.exists():
        try:
            # Tentative de suppression du répertoire, échouera s'il n'est pas vide.
            # Pour un nettoyage plus robuste, shutil.rmtree pourrait être utilisé avec prudence.
            temp_dir.rmdir()
        except OSError as e:
            logger.warning(
                f"N'a pas pu supprimer {temp_dir}: {e}. Nettoyage manuel peut être requis."
            )

    logger.info(f"Contenu du fichier {test_file_in_temp_dir}: '{file_content}'")
    logger.info(f"Répertoire de travail attendu (résolu): '{str(temp_dir.resolve())}'")
    assert file_content == str(
        temp_dir.resolve()
    ), f"Test 4 Échoué: Contenu du fichier CWD ('{file_content}') ne correspond pas au CWD attendu ('{str(temp_dir.resolve())}')"

    # Test 5: Commande non trouvée
    logger.info("\n--- Test 5: Commande non trouvée ---")
    non_existent_cmd = "commande_vraiment_introuvable_0xDEADBEEF"
    ret_code, out, err = run_shell_command(non_existent_cmd)
    logger.info(f"Code retour: {ret_code}, Sortie: '{out}', Erreur: '{err}'")
    assert (
        ret_code == -10
    ), f"Test 5 Échoué: Code retour attendu -10 (non trouvée), obtenu {ret_code}"
    assert (
        non_existent_cmd in err
    ), f"Test 5 Échoué: Nom de commande attendu dans stderr, obtenu '{err}'"

    logger.info("\nTous les tests pour run_shell_command sont terminés.")
