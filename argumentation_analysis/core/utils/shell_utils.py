# -*- coding: utf-8 -*-
"""
Utilitaires pour l'exécution de commandes shell et l'interaction avec le système.
"""

import logging
import subprocess
from typing import List, Tuple, Optional, Union, Dict  # Ajout de Union et Optional
from pathlib import Path  # Ajout pour cwd

logger = logging.getLogger(__name__)


def run_shell_command(
    command: Union[str, List[str]],
    description: Optional[str] = None,
    capture_output: bool = True,
    text_output: bool = True,
    shell_mode: bool = False,  # Par défaut, False pour la sécurité (si command est une liste)
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    """
    Exécute une commande shell et loggue sa sortie.

    Args:
        command (Union[str, List[str]]): La commande à exécuter. Peut être une chaîne
                                         (si shell_mode=True) ou une liste d'arguments.
        description (Optional[str]): Une description de la commande pour le logging.
                                     Si None, une description par défaut sera générée.
        capture_output (bool): Si True, capture stdout et stderr.
        text_output (bool): Si True, décode stdout et stderr en texte (utf-8).
        shell_mode (bool): Si True, exécute la commande via le shell système.
                           Attention: peut être un risque de sécurité si la commande
                           provient d'une source non fiable. Préférer False avec une
                           liste d'arguments lorsque c'est possible.
        cwd (Optional[Path]): Répertoire de travail pour l'exécution de la commande.
        env (Optional[Dict[str,str]]): Variables d'environnement à définir pour la commande.

    Returns:
        Tuple[int, str, str]: Un tuple contenant:
            - Le code de retour de la commande.
            - La sortie standard (stdout) décodée (si capture_output et text_output).
            - La sortie d'erreur (stderr) décodée (si capture_output et text_output).
            Les chaînes de sortie seront vides si capture_output est False.
    """
    if description is None:
        if isinstance(command, list):
            desc_cmd = " ".join(command)
        else:
            desc_cmd = command
        description = f"Exécution de la commande: {desc_cmd[:70]}{'...' if len(desc_cmd) > 70 else ''}"

    logger.info(f"--- {description} ---")
    if isinstance(command, list):
        logger.info(f"Commande: {' '.join(command)}")
    else:
        logger.info(f"Commande: {command}")
    if cwd:
        logger.info(f"Répertoire de travail: {cwd}")

    stdout_str = ""
    stderr_str = ""

    try:
        # subprocess.run attend une liste d'arguments par défaut (shell=False)
        # Si command est une chaîne et shell=False, elle est traitée comme le nom de l'exécutable.
        # Si shell=True, command peut être une chaîne.
        process_args = {
            "capture_output": capture_output,
            "text": text_output,  # Décode la sortie en texte si True
            "shell": shell_mode,
            "cwd": str(cwd) if cwd else None,  # subprocess.run attend str pour cwd
            "env": env,
        }
        if text_output:  # encoding n'est pertinent que si text=True
            process_args["encoding"] = "utf-8"
            process_args["errors"] = "replace"  # Gérer les erreurs de décodage

        result = subprocess.run(command, **process_args)  # type: ignore

        if result.stdout:
            stdout_str = (
                result.stdout.strip()
                if isinstance(result.stdout, str)
                else result.stdout.decode("utf-8", "replace").strip()
            )
            # Logguer chaque ligne peut être verbeux, donc on logue un résumé.
            # Les appelants peuvent logguer la sortie complète s'ils le souhaitent.
            logger.debug(
                f"Stdout (aperçu):\n{stdout_str[:500]}{'...' if len(stdout_str) > 500 else ''}"
            )

        if result.stderr:
            stderr_str = (
                result.stderr.strip()
                if isinstance(result.stderr, str)
                else result.stderr.decode("utf-8", "replace").strip()
            )
            logger.warning(
                f"Stderr (aperçu):\n{stderr_str[:500]}{'...' if len(stderr_str) > 500 else ''}"
            )

        if result.returncode == 0:
            logger.info(
                f"[OK] {description} terminé avec succès (code: {result.returncode})."
            )
        else:
            logger.error(f"❌ {description} a échoué (code: {result.returncode}).")

        return result.returncode, stdout_str, stderr_str

    except FileNotFoundError:
        logger.error(
            f"❌ Erreur lors de l'exécution de '{description}': Commande ou exécutable non trouvé."
        )
        return (
            -1,
            "",
            "Commande non trouvée",
        )  # Code de retour personnalisé pour cette erreur
    except Exception as e:
        logger.error(
            f"❌ Erreur inattendue lors de l'exécution de '{description}': {e}",
            exc_info=True,
        )
        return -1, "", str(e)  # Code de retour personnalisé
