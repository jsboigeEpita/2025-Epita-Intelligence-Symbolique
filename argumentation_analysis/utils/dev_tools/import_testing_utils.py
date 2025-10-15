# -*- coding: utf-8 -*-
"""
Utilitaires pour tester l'importation de modules Python,
que ce soit par nom de module ou par chemin de fichier.
"""

import logging
import importlib
import sys
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def test_module_import_by_name(module_name: str) -> Tuple[bool, str]:
    """
    Teste l'importation d'un module par son nom (ex: 'my_package.my_module')
    et retourne un booléen indiquant le succès et un message.

    Args:
        module_name (str): Le nom complet du module à importer.

    Returns:
        Tuple[bool, str]: Un tuple contenant:
            - True si l'importation a réussi, False sinon.
            - Un message décrivant le résultat.
    """
    if not module_name or not isinstance(module_name, str):
        msg = "Nom de module invalide fourni pour le test d'importation."
        logger.error(msg)
        return False, f"✗ {msg}"
    try:
        importlib.import_module(module_name)
        success_msg = f"✓ Module '{module_name}' importé avec succès par nom."
        logger.debug(success_msg)
        return True, success_msg
    except ImportError as e_import:
        error_msg = f"✗ Erreur d'importation (ImportError) pour le module '{module_name}': {e_import}"
        logger.warning(error_msg)
        return False, error_msg
    except Exception as e_general:
        error_msg = f"✗ Erreur inattendue lors de l'importation du module '{module_name}': {e_general}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def test_module_import_by_path(
    module_file_path: Path, module_name_override: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Teste l'importation d'un module Python à partir de son chemin de fichier.

    Ajoute temporairement le répertoire parent du module à sys.path pour permettre
    l'importation, puis le retire.

    Args:
        module_file_path (Path): Le chemin d'accès au fichier .py du module.
        module_name_override (Optional[str]): Nom à utiliser pour l'importation si différent
                                             du nom de fichier (sans .py).
                                             Utile pour les __init__.py (importer le package).

    Returns:
        Tuple[bool, str]: Un tuple contenant:
            - True si l'importation a réussi, False sinon.
            - Un message décrivant le résultat.
    """
    if (
        not isinstance(module_file_path, Path)
        or not module_file_path.is_file()
        or module_file_path.suffix != ".py"
    ):
        msg = f"Chemin de module invalide fourni: {module_file_path}. Doit être un fichier .py existant."
        logger.error(msg)
        return False, f"✗ {msg}"

    module_dir = module_file_path.parent.resolve()

    if module_name_override:
        actual_module_name = module_name_override
    elif module_file_path.name == "__init__.py":
        actual_module_name = module_dir.name  # Importer le nom du package
    else:
        actual_module_name = module_file_path.stem  # Nom du fichier sans .py

    original_sys_path = list(sys.path)
    path_inserted = False

    try:
        if str(module_dir) not in sys.path:
            sys.path.insert(0, str(module_dir))
            path_inserted = True
            logger.debug(
                f"Temporairement ajouté '{module_dir}' à sys.path pour importer '{actual_module_name}'."
            )

        importlib.import_module(actual_module_name)
        success_msg = f"✓ Module '{actual_module_name}' (depuis {module_file_path}) importé avec succès par chemin."
        logger.debug(success_msg)
        return True, success_msg
    except ImportError as e_import:
        error_msg = f"✗ Erreur d'importation (ImportError) pour '{actual_module_name}' (depuis {module_file_path}): {e_import}"
        logger.warning(error_msg)
        return False, error_msg
    except Exception as e_general:
        error_msg = f"✗ Erreur inattendue lors de l'importation de '{actual_module_name}' (depuis {module_file_path}): {e_general}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
    finally:
        # Restaurer sys.path
        if path_inserted and str(module_dir) in sys.path:
            # Ne retirer que si on l'a effectivement ajouté et qu'il est toujours là au début.
            # C'est une précaution, car import_module pourrait modifier sys.path.
            try:
                sys.path.remove(str(module_dir))
                logger.debug(f"'{module_dir}' retiré de sys.path.")
            except ValueError:
                logger.warning(
                    f"Tentative de retirer '{module_dir}' de sys.path, mais non trouvé. sys.path actuel: {sys.path}"
                )
        elif str(module_dir) not in original_sys_path and str(module_dir) in sys.path:
            # Si le chemin n'était pas là à l'origine mais y est maintenant (et qu'on ne l'a pas inséré nous-mêmes)
            # il vaut mieux le laisser pour ne pas casser quelque chose d'autre.
            logger.debug(
                f"Le chemin '{module_dir}' semble avoir été ajouté à sys.path par une autre opération, non retiré par cet utilitaire."
            )


# Alias pour la compatibilité avec l'ancien nom utilisé dans certains scripts
test_import = test_module_import_by_name
