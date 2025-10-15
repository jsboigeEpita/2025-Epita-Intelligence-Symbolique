# -*- coding: utf-8 -*-
"""
Utilitaires pour la sauvegarde de fichiers dans différents formats.
"""
import json
from pathlib import Path
from typing import Any, Optional, List, Dict
import logging
from datetime import datetime

# Logger spécifique pour ce module
savers_logger = logging.getLogger("App.ProjectCore.FileSavers")
if not savers_logger.handlers and not savers_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    savers_logger.addHandler(handler)
    savers_logger.setLevel(logging.INFO)


def save_json_file(file_path: Path, data: Any, indent: int = 4) -> bool:
    """
    Sauvegarde des données Python dans un fichier JSON.
    Crée les répertoires parents si nécessaire.
    """
    savers_logger.info(
        f"Tentative de sauvegarde des données JSON dans {file_path} avec une indentation de {indent}"
    )
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        savers_logger.debug(
            f"Répertoire parent {file_path.parent} pour la sauvegarde JSON vérifié/créé."
        )

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        savers_logger.info(
            f"[OK] Données JSON sauvegardées avec succès dans {file_path}"
        )
        return True
    except IOError as e:
        savers_logger.error(
            f"❌ Erreur d'E/S lors de la sauvegarde du fichier JSON {file_path}: {e}",
            exc_info=True,
        )
        return False
    except TypeError as e:
        savers_logger.error(
            f"❌ Erreur de type lors de la sérialisation JSON pour le fichier {file_path} (données non sérialisables?): {e}",
            exc_info=True,
        )
        return False
    except Exception as e:
        savers_logger.error(
            f"❌ Erreur inattendue lors de la sauvegarde du fichier JSON {file_path}: {e}",
            exc_info=True,
        )
        return False


def save_text_file(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """
    Sauvegarde du contenu textuel dans un fichier.
    Crée les répertoires parents si nécessaire.
    """
    savers_logger.info(
        f"Tentative de sauvegarde du contenu dans {file_path} avec l'encodage {encoding}"
    )
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        savers_logger.debug(
            f"Répertoire parent {file_path.parent} pour la sauvegarde vérifié/créé."
        )

        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        savers_logger.info(f"[OK] Contenu sauvegardé avec succès dans {file_path}")
        return True
    except IOError as e:
        savers_logger.error(
            f"❌ Erreur d'E/S lors de la sauvegarde du fichier {file_path}: {e}",
            exc_info=True,
        )
        return False
    except UnicodeEncodeError as e:
        savers_logger.error(
            f"❌ Erreur d'encodage Unicode lors de la sauvegarde du fichier {file_path} avec l'encodage {encoding}: {e}",
            exc_info=True,
        )
        return False
    except Exception as e:
        savers_logger.error(
            f"❌ Erreur inattendue lors de la sauvegarde du fichier {file_path}: {e}",
            exc_info=True,
        )
        return False


def save_temp_extracts_json(
    extract_definitions: List[Dict[str, Any]],
    base_temp_dir_name: str = "temp_extracts",
    filename_prefix: str = "extracts_decrypted_",
) -> Optional[Path]:
    """
    Sauvegarde les définitions d'extraits dans un fichier JSON temporaire avec horodatage.
    """
    if not isinstance(extract_definitions, list):
        savers_logger.error(
            "Les définitions d'extraits fournies ne sont pas une liste."
        )
        return None

    try:
        current_temp_dir = Path.cwd() / base_temp_dir_name
        current_temp_dir.mkdir(parents=True, exist_ok=True)
        savers_logger.debug(
            f"Répertoire temporaire pour les extraits: {current_temp_dir.resolve()}"
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file_path = current_temp_dir / f"{filename_prefix}{timestamp}.json"

        if save_json_file(
            temp_file_path, extract_definitions, indent=2
        ):  # Appel à la fonction de ce module
            savers_logger.info(
                f"[OK] Définitions d'extraits sauvegardées avec succès dans {temp_file_path.resolve()}"
            )
            return temp_file_path
        else:
            savers_logger.error(
                f"Échec de la sauvegarde des extraits temporaires dans {temp_file_path} via save_json_file."
            )
            return None

    except Exception as e:
        savers_logger.error(
            f"❌ Erreur inattendue lors de la création ou sauvegarde du fichier d'extraits temporaire: {e}",
            exc_info=True,
        )
        return None


savers_logger.info("Utilitaires de sauvegarde de fichiers (FileSavers) définis.")
