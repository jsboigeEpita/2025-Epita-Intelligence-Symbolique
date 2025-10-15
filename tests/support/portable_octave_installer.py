import os
import pathlib
import logging
import shutil
import zipfile
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)
# Assurer une configuration minimale du logger si ce module est utilisé seul
if not logger.handlers and not logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Configuration pour Octave Portable
OCTAVE_VERSION_MAJOR_MINOR = "10.1.0"  # Adapter si une autre version est ciblée
OCTAVE_ARCH = "w64"  # Pour Windows 64-bit
OCTAVE_ZIP_NAME = f"octave-{OCTAVE_VERSION_MAJOR_MINOR}-{OCTAVE_ARCH}.zip"
# Lien direct vers le ZIP (plus stable que ftpmirror qui peut rediriger)
OCTAVE_DOWNLOAD_URL = f"https://ftp.gnu.org/gnu/octave/windows/{OCTAVE_ZIP_NAME}"
# Le répertoire racine attendu après extraction (peut varier légèrement, ex: octave-10.1.0-w64)
# Nous le déterminerons dynamiquement ou chercherons un nom commun.
# Le nom du répertoire extrait est généralement le nom du zip sans l'extension .zip
OCTAVE_EXTRACTED_DIR_NAME = f"octave-{OCTAVE_VERSION_MAJOR_MINOR}-{OCTAVE_ARCH}"


def _download_file(url: str, dest_path: pathlib.Path) -> bool:
    """Télécharge un fichier depuis une URL vers dest_path."""
    logger.info(f"Téléchargement de {url} vers {dest_path}...")
    try:
        hdr = {"User-Agent": "Mozilla/5.0"}  # User-agent simple
        req = urllib.request.Request(url, headers=hdr)
        with urllib.request.urlopen(req) as response, open(dest_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
        logger.info(f"Téléchargement réussi: {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Échec du téléchargement de {url}: {e}", exc_info=True)
        if dest_path.exists():
            dest_path.unlink()  # Supprimer le fichier partiel
        return False


def _extract_zip(
    zip_path: pathlib.Path, extract_to_dir: pathlib.Path
) -> Optional[pathlib.Path]:
    """Extrait une archive ZIP et retourne le chemin du premier répertoire de haut niveau trouvé."""
    logger.info(f"Extraction de '{zip_path}' vers '{extract_to_dir}'...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Obtenir le nom du répertoire racine dans le zip, s'il y en a un seul
            # Souvent, les archives zip ont un seul dossier racine.
            top_level_dirs = list(
                set(item.split("/")[0] for item in zip_ref.namelist() if "/" in item)
            )

            zip_ref.extractall(extract_to_dir)
        logger.info(f"Extraction réussie dans '{extract_to_dir}'.")

        if top_level_dirs and len(top_level_dirs) == 1:
            extracted_root_name = top_level_dirs[0]
            if (extract_to_dir / extracted_root_name).is_dir():
                logger.info(
                    f"Répertoire racine de l'archive détecté: {extracted_root_name}"
                )
                return extract_to_dir / extracted_root_name

        # Fallback: si le nom du répertoire extrait correspond au nom attendu
        expected_extracted_path = extract_to_dir / OCTAVE_EXTRACTED_DIR_NAME
        if expected_extracted_path.is_dir():
            logger.info(
                f"Répertoire racine attendu '{OCTAVE_EXTRACTED_DIR_NAME}' trouvé après extraction."
            )
            return expected_extracted_path

        logger.warning(
            f"Impossible de déterminer le répertoire racine exact après extraction dans '{extract_to_dir}'. "
            f"Vérifiez le contenu. Top-level dirs détectés dans le zip: {top_level_dirs}"
        )
        return extract_to_dir  # Retourne le répertoire parent si le sous-répertoire n'est pas clair

    except FileNotFoundError:
        logger.error(
            f"L'archive ZIP '{zip_path}' n'a pas été trouvée pour l'extraction."
        )
        return None
    except zipfile.BadZipFile:
        logger.error(f"L'archive ZIP '{zip_path}' est corrompue.")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction de '{zip_path}': {e}", exc_info=True)
        return None


def ensure_portable_octave(project_root_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """
    S'assure que Octave portable est disponible, le télécharge et l'extrait si nécessaire.
    Retourne le chemin vers le répertoire 'mingw64/bin' d'Octave portable, ou None si échec.
    """
    portable_octave_parent_dir = project_root_dir / "libs" / "portable_octave"
    temp_dir = project_root_dir / "libs" / "_temp"
    octave_zip_path = temp_dir / OCTAVE_ZIP_NAME

    # Le chemin attendu vers le répertoire bin d'Octave
    # Ex: portable_octave/octave-10.1.0-w64/mingw64/bin
    # Nous devons d'abord trouver le répertoire racine d'Octave (ex: octave-10.1.0-w64)

    octave_root_install_dir = portable_octave_parent_dir / OCTAVE_EXTRACTED_DIR_NAME
    octave_bin_path = octave_root_install_dir / "mingw64" / "bin"

    if octave_bin_path.is_dir() and (octave_bin_path / "octave-cli.exe").is_file():
        logger.info(f"Octave portable déjà trouvé et semble valide: {octave_bin_path}")
        return octave_bin_path

    logger.info(
        f"Octave portable non trouvé à {octave_bin_path}. Tentative de mise en place..."
    )
    portable_octave_parent_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Vérifier si l'archive ZIP existe déjà
    if not octave_zip_path.is_file():
        logger.info(
            f"Archive ZIP d'Octave '{OCTAVE_ZIP_NAME}' non trouvée dans '{temp_dir}'. Téléchargement..."
        )
        if not _download_file(OCTAVE_DOWNLOAD_URL, octave_zip_path):
            return None  # Échec du téléchargement
    else:
        logger.info(f"Archive ZIP d'Octave '{octave_zip_path}' trouvée.")

    # 2. Extraire l'archive
    # Supprimer l'ancien répertoire d'installation s'il existe pour une extraction propre
    if octave_root_install_dir.exists():
        logger.info(
            f"Suppression de l'ancien répertoire d'installation Octave: {octave_root_install_dir}"
        )
        try:
            shutil.rmtree(octave_root_install_dir)
        except Exception as e_rm:
            logger.error(
                f"Impossible de supprimer l'ancien répertoire {octave_root_install_dir}: {e_rm}"
            )
            # Continuer quand même, l'extraction pourrait écraser ou échouer proprement.

    extracted_octave_base = _extract_zip(octave_zip_path, portable_octave_parent_dir)

    if not extracted_octave_base or not extracted_octave_base.is_dir():
        logger.error(
            f"Échec de l'extraction d'Octave ou répertoire de base non trouvé."
        )
        return None

    # Mettre à jour octave_bin_path avec le chemin réellement extrait
    # Si _extract_zip retourne le parent_dir, on suppose que le nom est OCTAVE_EXTRACTED_DIR_NAME
    if (
        extracted_octave_base.name != OCTAVE_EXTRACTED_DIR_NAME
        and (extracted_octave_base / OCTAVE_EXTRACTED_DIR_NAME).is_dir()
    ):
        # Cas où _extract_zip a retourné le parent et le dossier est dedans
        octave_root_install_dir_final = (
            extracted_octave_base / OCTAVE_EXTRACTED_DIR_NAME
        )
    elif extracted_octave_base.name == OCTAVE_EXTRACTED_DIR_NAME:
        octave_root_install_dir_final = extracted_octave_base
    else:  # Si le nom du répertoire extrait n'est pas celui attendu, on essaie de le trouver
        found_octave_dir = None
        for item in portable_octave_parent_dir.iterdir():
            if (
                item.is_dir()
                and item.name.startswith("octave-")
                and item.name.endswith(OCTAVE_ARCH)
            ):
                found_octave_dir = item
                break
        if found_octave_dir:
            octave_root_install_dir_final = found_octave_dir
            logger.info(
                f"Répertoire Octave détecté après extraction: {octave_root_install_dir_final}"
            )
        else:
            logger.error(
                f"Impossible de localiser le répertoire racine d'Octave après extraction dans {portable_octave_parent_dir}"
            )
            return None

    octave_bin_path_final = octave_root_install_dir_final / "mingw64" / "bin"

    if (
        octave_bin_path_final.is_dir()
        and (octave_bin_path_final / "octave-cli.exe").is_file()
    ):
        logger.info(
            f"Octave portable mis en place avec succès. Chemin binaire: {octave_bin_path_final}"
        )
        return octave_bin_path_final
    else:
        logger.error(
            f"Octave portable semble extrait mais le répertoire bin '{octave_bin_path_final}' ou 'octave-cli.exe' est invalide/manquant."
        )
        return None


if __name__ == "__main__":
    # Pour tester ce module directement
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    script_dir = pathlib.Path(__file__).parent.resolve()
    project_root = (
        script_dir.parent.parent
    )  # Remonter de tests/utils à la racine du projet

    logger.info(f"Racine du projet détectée: {project_root}")

    # Le répertoire racine est passé, la fonction `ensure_portable_octave`
    # gérera elle-même la création des sous-répertoires nécessaires dans `libs/`.
    octave_bin = ensure_portable_octave(project_root)
    if octave_bin:
        logger.info(f"Test réussi: Chemin binaire Octave: {octave_bin}")
        # Essayer d'exécuter octave-cli --version
        octave_cli_exe = octave_bin / "octave-cli.exe"
        if octave_cli_exe.is_file():
            import subprocess

            try:
                result = subprocess.run(
                    [str(octave_cli_exe), "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
                logger.info(f"Octave CLI version output:\n{result.stdout}")
            except Exception as e_cli:
                logger.error(
                    f"Erreur lors de l'exécution de octave-cli --version: {e_cli}"
                )
        else:
            logger.error(f"octave-cli.exe non trouvé à {octave_cli_exe}")
    else:
        logger.error(
            "Test échoué: Impossible d'assurer la disponibilité d'Octave portable."
        )
