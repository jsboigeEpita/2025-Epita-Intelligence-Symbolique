# -*- coding: utf-8 -*-
# core/jvm_setup.py
import os
import argumentation_analysis.core.dll_guard  # noqa: F401 — must precede jpype import on Windows

try:
    import jpype
    import jpype.imports

    _JPYPE_AVAILABLE = True
except ImportError:
    # #1697: honest-absent contract. A bare ``import jpype`` here made every
    # module that imports jvm_setup (tweety_initializer → the logic agents →
    # logic/__init__) unimportable in a jpype-less env, so neither the MCP
    # server nor the web API could boot degraded. Binding ``jpype`` to None
    # keeps ``is_jvm_started()`` honest (its ``except Exception`` already
    # returns False) and lets ``initialize_jvm()`` report failure instead of
    # crashing the import.
    jpype = None  # type: ignore[assignment]
    _JPYPE_AVAILABLE = False
import logging
import threading
import platform
import re
import requests
import shutil
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import List, Optional, Dict
from tqdm.auto import tqdm

from argumentation_analysis.core import tweety_assembly


class JVMStartupTimeoutError(TimeoutError):
    """Exception raised when JVM startup exceeds the configured timeout."""

    pass


# Default timeout for JVM startup (can be overridden via settings)
DEFAULT_JVM_STARTUP_TIMEOUT_SECONDS = 60

# --- Configuration initiale du Logger ---
# Il est crucial de configurer le logger au tout début.
# Si le logger parent est déjà configuré, ces lignes n'auront pas d'effet
# mais garantissent que le logging est actif si ce module est importé en premier.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Orchestration.JPype.Setup")
try:
    from argumentation_analysis.config.settings import settings
except ImportError as e:
    logger.critical(
        f"CRASH POTENTIEL: Échec de l'importation de 'settings'. Erreur: {e}",
        exc_info=True,
    )
    raise

# Verrou global pour rendre l'initialisation de la JVM thread-safe
_jvm_lock = threading.Lock()

# Registry of detected external solver paths, populated by
# ``_configure_external_tools``. Keys: "clingo" (binary dir), "eprover" (binary
# path), "spass" (binary path). Logic handlers read this to instantiate the
# corresponding Tweety reasoner with the correct constructor argument (#1196).
EXTERNAL_TOOL_PATHS: dict[str, str] = {}

# --- Gestion d'état de la JVM ---
_JVM_INITIALIZED_THIS_SESSION = False
_JVM_WAS_SHUTDOWN = False
_SESSION_FIXTURE_OWNS_JVM = False


def get_project_root_robust() -> Path:
    """
    Trouve la racine du projet en remontant depuis l'emplacement de ce fichier.
    """
    current_path = Path(__file__).resolve()
    # Dans la structure actuelle, le chemin est argumentation_analysis/core/jvm_setup.py,
    # donc il faut remonter de 2 niveaux pour atteindre la racine du projet.
    project_root = current_path.parents[2]
    return project_root


try:
    PROJ_ROOT = get_project_root_robust()
    LIBS_DIR = PROJ_ROOT / settings.jvm.tweety_libs_dir
    TWEETY_VERSION = settings.jvm.tweety_version
    TWEETY_JAR_FILENAME = (
        f"org.tweetyproject.tweety-full-{TWEETY_VERSION}-with-dependencies.jar"
    )
    MIN_JAVA_VERSION = settings.jvm.min_java_version
    JDK_VERSION = settings.jvm.jdk_version
    JDK_BUILD = settings.jvm.jdk_build
    JDK_URL_TEMPLATE = settings.jvm.jdk_url_template
    EXT_TOOLS_DIR = PROJ_ROOT / settings.jvm.ext_tools_dir
    CLINGO_VERSION = settings.jvm.clingo_version
except Exception as e:
    logger.critical(
        f"CRASH POTENTIEL: Échec lors de la lecture de 'settings' pour définir les constantes globales. Erreur: {e}",
        exc_info=True,
    )
    raise


class TqdmUpTo(tqdm):
    """Provides `update_to(block_num, block_size, total_size)`."""

    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def get_os_arch_for_jdk() -> Dict[str, str]:
    system = platform.system().lower()
    arch = platform.machine().lower()
    os_map = {"windows": "windows", "linux": "linux", "darwin": "mac"}
    arch_map = {
        "amd64": "x64",
        "x86_64": "x64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }
    if system not in os_map:
        raise OSError(
            f"Système d'exploitation non supporté pour le JDK portable : {platform.system()}"
        )
    if arch not in arch_map:
        raise OSError(f"Architecture non supportée pour le JDK portable : {arch}")
    return {"os": os_map[system], "arch": arch_map[arch]}


def download_file(url: str, dest_path: Path, description: Optional[str] = None):
    if description is None:
        description = dest_path.name
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            logger.debug(f"Fichier '{dest_path.name}' déjà présent et non vide. Skip.")
            return True, False
        logger.info(f"Tentative de téléchargement: {url} vers {dest_path}")
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(
            url, stream=True, timeout=30, headers=headers, allow_redirects=True
        )
        if response.status_code == 404:
            logger.error(f"❌ Fichier non trouvé (404) à l'URL: {url}")
            return False, False
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        with TqdmUpTo(
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            total=total_size,
            miniters=1,
            desc=description[:40],
        ) as t:
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        t.update(len(chunk))
        if dest_path.exists() and dest_path.stat().st_size > 0:
            if total_size != 0 and dest_path.stat().st_size != total_size:
                logger.warning(
                    f"⚠️ Taille du fichier téléchargé '{dest_path.name}' ({dest_path.stat().st_size}) "
                    f"ne correspond pas à la taille attendue ({total_size})."
                )
            logger.info(f" -> Téléchargement de '{dest_path.name}' réussi.")
            return True, True
        else:
            logger.error(
                f"❓ Téléchargement de '{dest_path.name}' semblait terminé mais fichier vide ou absent."
            )
            if dest_path.exists():
                dest_path.unlink(missing_ok=True)
            return False, False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Échec connexion/téléchargement pour '{dest_path.name}': {e}")
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        return False, False
    except Exception as e_other:
        logger.error(
            f"❌ Erreur inattendue pendant téléchargement de '{dest_path.name}': {e_other}",
            exc_info=True,
        )
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        return False, False


def download_tweety_jars(
    version: str = TWEETY_VERSION, target_dir: Optional[Path] = None
) -> bool:
    """Ensure a usable Tweety classpath exists in ``target_dir``.

    #1874: the historical source ``https://tweetyproject.org/builds/{version}/``
    was removed upstream and now 404s, so this used to leave ``libs/tweety/``
    empty on a fresh runner -- the JVM then refused to start and the whole suite
    reported skips. What disappeared is the **fat-jar packaging**, not the
    library: Maven Central carries ``org.tweetyproject:*`` from 1.18 to 1.31.

    Order of preference:

    1. an existing classpath (a cached ``*-with-dependencies.jar``, or an already
       assembled directory) -- nothing to do;
    2. the legacy fat jar, still tried so a machine whose mirror survives keeps
       its fast path and byte-identical artifact;
    3. an assembly of the dependency closure from Maven Central.

    Failure is loud and named. A partial classpath is worse than none: the JVM
    starts, every Tweety import fails, and the run reports skips instead of an
    error -- exactly the silent shape #1873 had to build a guard against.
    """
    logger.info(
        f"--- Démarrage de la vérification/téléchargement des JARs Tweety v{version} ---"
    )
    target_dir_path = Path(target_dir) if target_dir else LIBS_DIR
    target_dir_path.mkdir(parents=True, exist_ok=True)

    # `version`, not settings: this function takes the version as an argument and
    # callers (tests included) pass one that differs from the configured default.
    # Gating on settings would answer a question nobody asked.
    if tweety_assembly.is_already_assembled(target_dir_path, version=version):
        logger.info(
            "Classpath Tweety %s déjà présent dans %s (%d jar(s) de module). Rien à faire.",
            version,
            target_dir_path,
            tweety_assembly.count_module_jars(target_dir_path, version=version),
        )
        logger.info("--- Fin de la vérification/téléchargement des JARs Tweety ---")
        return True

    jar_filename = f"org.tweetyproject.tweety-full-{version}-with-dependencies.jar"
    jar_target_path = target_dir_path / jar_filename
    jar_url = f"https://tweetyproject.org/builds/{version}/{jar_filename}"
    logger.info(
        "JAR fat '%s' absent. Tentative sur le canal historique %s",
        jar_filename,
        jar_url,
    )
    legacy_ok = False
    try:
        response = requests.head(jar_url, timeout=10, allow_redirects=True)
        legacy_ok = response.status_code == 200
    except requests.RequestException as e:
        logger.info("Canal historique injoignable (%s).", e)
    if legacy_ok:
        success, _ = download_file(jar_url, jar_target_path, description=jar_filename)
        if success:
            logger.info(f"JAR '{jar_filename}' téléchargé avec succès.")
            logger.info("--- Fin de la vérification/téléchargement des JARs Tweety ---")
            return True
        logger.warning(
            "Le canal historique a répondu 200 mais le téléchargement a échoué; "
            "bascule sur l'assemblage Maven."
        )
    else:
        logger.info(
            "Canal historique indisponible (#1874: /builds/ supprimé en amont). "
            "Bascule sur l'assemblage depuis Maven Central."
        )

    try:
        pins = tweety_assembly.parse_pin_spec(settings.jvm.tweety_pinned_modules)
        excludes = tweety_assembly.parse_exclude_spec(
            settings.jvm.tweety_excluded_modules
        )
        count = tweety_assembly.assemble(
            version, target_dir_path, pins=pins, excludes=excludes
        )
    except (tweety_assembly.AssemblyError, ValueError) as e:
        logger.error("Approvisionnement Tweety %s impossible: %s", version, e)
        logger.info("--- Fin de la vérification/téléchargement des JARs Tweety ---")
        return False

    logger.info("Assemblage Tweety %s réussi: %d jars de module.", version, count)
    logger.info("--- Fin de la vérification/téléchargement des JARs Tweety ---")
    return True


def download_clingo(version: str = None, target_dir: Optional[Path] = None) -> bool:
    """
    Download Clingo ASP solver binary for the current platform.
    Inspired by CoursIA download_tweety_tools.py.

    Clingo is needed by Tweety's ClingoSolver.setPathToClingo() for ASP reasoning.
    The Python `clingo` package is separate and doesn't provide the standalone binary
    that Tweety's Java code expects.
    """
    version = version or CLINGO_VERSION
    clingo_dir = (target_dir or EXT_TOOLS_DIR) / "clingo"
    clingo_dir.mkdir(parents=True, exist_ok=True)

    exe_suffix = ".exe" if platform.system() == "Windows" else ""
    clingo_exe = clingo_dir / f"clingo{exe_suffix}"

    if clingo_exe.exists():
        logger.info(f"Clingo binary already present: {clingo_exe}")
        return True

    # Check if available in system PATH
    system_clingo = shutil.which("clingo") or shutil.which("clingo.exe")
    if system_clingo:
        logger.info(f"Clingo found in system PATH: {system_clingo}")
        return True

    logger.info(f"Downloading Clingo {version} for {platform.system()}...")
    base_url = f"https://github.com/potassco/clingo/releases/download/v{version}"

    if platform.system() == "Windows":
        archive_name = f"clingo-{version}-win64.zip"
        archive_url = f"{base_url}/{archive_name}"
        archive_path = clingo_dir / archive_name

        success, _ = download_file(
            archive_url, archive_path, description=f"Clingo {version}"
        )
        if not success:
            logger.error(f"Failed to download Clingo from {archive_url}")
            return False

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(clingo_dir)
            # Find and move clingo.exe to the expected location
            for exe in clingo_dir.rglob("clingo.exe"):
                if exe != clingo_exe:
                    shutil.move(str(exe), str(clingo_exe))
                    break
            archive_path.unlink(missing_ok=True)
            # Clean up extracted subdirectories
            for d in clingo_dir.glob(f"clingo-{version}*"):
                if d.is_dir():
                    shutil.rmtree(d, ignore_errors=True)
            logger.info(f"Clingo installed: {clingo_exe}")
            return True
        except Exception as e:
            logger.error(f"Error extracting Clingo: {e}")
            return False

    elif platform.system() == "Linux":
        import tarfile

        archive_name = f"clingo-{version}-linux-x86_64.tar.gz"
        archive_url = f"{base_url}/{archive_name}"
        archive_path = clingo_dir / archive_name

        success, _ = download_file(
            archive_url, archive_path, description=f"Clingo {version}"
        )
        if not success:
            return False

        try:
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(clingo_dir)
            for exe in clingo_dir.rglob("clingo"):
                if exe != clingo_exe and exe.is_file():
                    shutil.move(str(exe), str(clingo_exe))
                    os.chmod(str(clingo_exe), 0o755)
                    break
            archive_path.unlink(missing_ok=True)
            for d in clingo_dir.glob(f"clingo-{version}*"):
                if d.is_dir():
                    shutil.rmtree(d, ignore_errors=True)
            logger.info(f"Clingo installed: {clingo_exe}")
            return True
        except Exception as e:
            logger.error(f"Error extracting Clingo: {e}")
            return False
    else:
        logger.warning(
            f"Automatic Clingo download not available for {platform.system()}"
        )
        return False


def download_external_tools() -> Dict[str, bool]:
    """
    Download all external tools needed by Tweety reasoners.
    Inspired by CoursIA download_tweety_tools.py.

    Returns a dict of {tool_name: success_bool}.
    """
    results = {}

    # 1. Tweety JAR
    results["tweety_jar"] = download_tweety_jars()

    # 2. Clingo (ASP solver)
    results["clingo"] = download_clingo()

    # 3. EProver — check presence only (manual install, already committed)
    eprover_path = (
        EXT_TOOLS_DIR
        / "EProver"
        / ("eprover.exe" if platform.system() == "Windows" else "eprover")
    )
    results["eprover"] = eprover_path.exists()
    if results["eprover"]:
        logger.info(f"EProver found: {eprover_path}")
    else:
        logger.warning(
            f"EProver not found at {eprover_path} — install manually from https://eprover.org/"
        )

    # 4. SPASS — check presence only (manual install on Windows)
    spass_path = (
        EXT_TOOLS_DIR
        / "spass"
        / ("SPASS.exe" if platform.system() == "Windows" else "SPASS")
    )
    results["spass"] = spass_path.exists()
    if results["spass"]:
        logger.info(f"SPASS found: {spass_path}")
    else:
        logger.warning(
            f"SPASS not found at {spass_path} — install manually from https://www.spass-prover.org/"
        )

    # Summary
    ok = [k for k, v in results.items() if v]
    nok = [k for k, v in results.items() if not v]
    logger.info(f"External tools check: {len(ok)}/{len(results)} OK")
    if nok:
        logger.warning(f"  Missing/failed: {nok}")

    return results


def unzip_file(zip_path: Path, dest_dir: Path):
    logger.info(f"Décompression de {zip_path} vers {dest_dir}...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            file_list = zip_ref.namelist()
            top_level_contents = {Path(f).parts[0] for f in file_list}
            if len(file_list) > 0 and len(top_level_contents) == 1:
                single_root_dir_in_zip_name = top_level_contents.pop()
                if all(
                    f.startswith(single_root_dir_in_zip_name + os.sep)
                    or f == single_root_dir_in_zip_name
                    for f in file_list
                    if f
                ):
                    temp_extract_dir = dest_dir.parent / (
                        dest_dir.name + "_temp_extract_strip"
                    )
                    if temp_extract_dir.exists():
                        shutil.rmtree(temp_extract_dir)
                    temp_extract_dir.mkdir(parents=True, exist_ok=True)
                    zip_ref.extractall(temp_extract_dir)
                    source_dir_to_move_from = (
                        temp_extract_dir / single_root_dir_in_zip_name
                    )
                    if dest_dir.resolve() != source_dir_to_move_from.resolve():
                        for item in dest_dir.iterdir():
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                    else:
                        logger.warning(
                            "Le répertoire de destination est le même que le répertoire source temporaire."
                        )
                    for item in source_dir_to_move_from.iterdir():
                        shutil.move(str(item), str(dest_dir / item.name))
                    shutil.rmtree(temp_extract_dir)
                    logger.info(
                        f"Contenu de '{single_root_dir_in_zip_name}' extrait et déplacé vers '{dest_dir}'."
                    )
                else:
                    zip_ref.extractall(dest_dir)
                    logger.info(
                        "Extraction standard effectuée (pas de strip de dossier racine)."
                    )
            else:
                zip_ref.extractall(dest_dir)
                logger.info(
                    "Extraction standard effectuée (contenu à la racine ou multiple)."
                )
        if zip_path.exists():
            zip_path.unlink()
        logger.info("Décompression terminée.")
    except (zipfile.BadZipFile, IOError, shutil.Error) as e:
        logger.error(
            f"Erreur lors de la décompression de {zip_path}: {e}", exc_info=True
        )
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
            dest_dir.mkdir(parents=True, exist_ok=True)
        raise


PORTABLE_JDK_DIR_NAME = "portable_jdk"
TEMP_DIR_NAME = "_temp_jdk_download"


def get_project_root() -> Path:
    return PROJ_ROOT


def is_valid_jdk(path: Path) -> bool:
    if not path.is_dir():
        return False
    java_exe = path / "bin" / ("java.exe" if platform.system() == "Windows" else "java")
    if not java_exe.is_file():
        logger.debug(
            f"Validation JDK: 'java' non trouvé ou n'est pas un fichier dans {path / 'bin'}"
        )
        return False
    try:
        result = subprocess.run(
            [str(java_exe), "-version"], capture_output=True, text=True, check=False
        )
        version_output = result.stderr if result.stderr else result.stdout
        if not version_output:
            logger.warning(
                f"Impossible d'obtenir la sortie de version pour le JDK à {path}. stderr: {result.stderr}, stdout: {result.stdout}"
            )
            return False
        version_pattern = r'version "(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:_(\d+))?.*"'
        match = None
        for line in version_output.splitlines():
            match = re.search(version_pattern, line)
            if match:
                break
        if not match:
            logger.warning(
                f"Impossible de parser la chaîne de version du JDK à '{path}'. Sortie: {version_output.strip()}"
            )
            return False
        major_version_str = match.group(1)
        minor_version_str = match.group(2)
        major_version = int(major_version_str)
        if major_version == 1 and minor_version_str:
            major_version = int(minor_version_str)
        try:
            raw_version_detail = match.group(0).split('"')[1]
        except IndexError:
            logger.error(
                f"Impossible d'extraire le numéro de version de '{match.group(0)}'."
            )
            raw_version_detail = "FORMAT_INCONNU"
        version_details_str = raw_version_detail.replace("\\", "\\\\")
        if major_version >= MIN_JAVA_VERSION:
            logger.info(
                f"Version Java détectée à '{path}': \"{version_details_str}\" (Majeure: {major_version}) -> Valide."
            )
            return True
        else:
            logger.warning(
                f"Version Java détectée à '{path}': \"{version_details_str}\" (Majeure: {major_version}) -> INVALIDE (minimum requis: {MIN_JAVA_VERSION})."
            )
            return False
    except FileNotFoundError:
        logger.error(f"Exécutable Java non trouvé à {java_exe}.")
        return False
    except Exception as e:
        logger.error(
            f"Erreur lors de la validation du JDK à {path}: {e}", exc_info=True
        )
        return False


def find_existing_jdk() -> Optional[Path]:
    logger.debug(
        "Recherche d'un JDK portable pré-existant valide (JAVA_HOME est ignoré)."
    )
    project_r = get_project_root()
    portable_jdk_dir = project_r / PORTABLE_JDK_DIR_NAME
    if portable_jdk_dir.is_dir():
        if is_valid_jdk(portable_jdk_dir):
            logger.info(f"JDK portable validé directement dans : {portable_jdk_dir}")
            return portable_jdk_dir
        for item in portable_jdk_dir.iterdir():
            if item.is_dir() and item.name.startswith("jdk-"):
                if is_valid_jdk(item):
                    logger.info(f"JDK portable validé dans sous-dossier : {item}")
                    return item
    logger.info(
        "Aucun JDK pré-existant valide trouvé. Le téléchargement va être tenté."
    )
    return None


def find_valid_java_home() -> Optional[str]:
    logger.info("Recherche d'un environnement Java valide...")
    existing_jdk_path = find_existing_jdk()
    if existing_jdk_path:
        logger.info(
            f"[SUCCESS] Utilisation du JDK existant validé: '{existing_jdk_path}'"
        )
        return str(existing_jdk_path.resolve())
    logger.info(
        "Aucun JDK valide existant. Tentative d'installation d'un JDK portable."
    )
    project_r = get_project_root()
    portable_jdk_install_dir = project_r / PORTABLE_JDK_DIR_NAME
    temp_download_dir = project_r / TEMP_DIR_NAME
    try:
        portable_jdk_install_dir.mkdir(parents=True, exist_ok=True)
        temp_download_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Impossible de créer les répertoires pour JDK portable: {e}")
        return None
    os_arch_info = get_os_arch_for_jdk()
    jdk_major_for_url = JDK_VERSION.split(".")[0]
    generic_zip_name = f"portable_jdk_{JDK_VERSION}_{JDK_BUILD}_{os_arch_info['os']}_{os_arch_info['arch']}.zip"
    jdk_zip_target_path = temp_download_dir / generic_zip_name
    jdk_url = JDK_URL_TEMPLATE.format(
        maj_v=jdk_major_for_url,
        v=JDK_VERSION,
        b=JDK_BUILD,
        arch=os_arch_info["arch"],
        os=os_arch_info["os"],
        b_flat=JDK_BUILD,
    )
    logger.info(f"URL du JDK portable construite: {jdk_url}")
    logger.info(
        f"Téléchargement du JDK portable depuis {jdk_url} vers {jdk_zip_target_path}..."
    )
    downloaded_ok, _ = download_file(
        jdk_url, jdk_zip_target_path, description=f"JDK {JDK_VERSION}+{JDK_BUILD}"
    )
    if not downloaded_ok or not jdk_zip_target_path.exists():
        logger.error(f"Échec du téléchargement du JDK portable.")
        return None
    logger.info(f"Décompression du JDK portable...")
    try:
        unzip_file(jdk_zip_target_path, portable_jdk_install_dir)
        final_jdk_path = None
        if is_valid_jdk(portable_jdk_install_dir):
            final_jdk_path = portable_jdk_install_dir
        else:
            for item in portable_jdk_install_dir.iterdir():
                if (
                    item.is_dir()
                    and item.name.startswith("jdk-")
                    and is_valid_jdk(item)
                ):
                    final_jdk_path = item
                    break
        if final_jdk_path:
            logger.info(
                f"[SUCCESS] JDK portable installé et validé: '{final_jdk_path}'"
            )
            return str(final_jdk_path.resolve())
        else:
            logger.error(
                f"L'extraction du JDK dans '{portable_jdk_install_dir}' n'a pas produit une installation valide."
            )
            return None
    except Exception as e_unzip:
        logger.error(
            f"Erreur lors de la décompression ou validation du JDK portable: {e_unzip}",
            exc_info=True,
        )
        if jdk_zip_target_path.exists():
            jdk_zip_target_path.unlink(missing_ok=True)
        return None


def get_jvm_options() -> List[str]:
    """
    Retourne une liste d'options JVM optimisées.

    Mission D3.2: Réactivation options mémoire pour stabiliser tests JPype/Tweety
    """
    options = [
        f"-Xms{settings.jvm.min_heap_size}",  # Réactivé: nécessaire pour tests Tweety
        f"-Xmx{settings.jvm.max_heap_size}",  # Réactivé: évite OutOfMemoryError
        "-Dfile.encoding=UTF-8",
        # "-Djava.awt.headless=true" # NOTE: Désactivé car identifié comme cause de crash (voir docs)
    ]

    # Add native library path for SAT solvers (Lingeling, MiniSat, PicoSAT)
    native_libs_dir = PROJ_ROOT / settings.jvm.native_libs_dir
    if native_libs_dir.exists():
        options.append(f"-Djava.library.path={native_libs_dir.resolve()}")
        logger.info(f"Native SAT libraries path: {native_libs_dir.resolve()}")

    logger.info(f"Options JVM configurées (Mission D3.2): {options}")
    return options


def _configure_external_tools():
    """
    Auto-detect and configure external reasoning tools for Tweety.

    Detects and records the path of each external solver into the module-level
    ``EXTERNAL_TOOL_PATHS`` registry, which the logic handlers read at
    instantiation time to build the corresponding Tweety reasoner.

    Detected tools:
    - Clingo (ASP solver) → directory of the binary, for ClingoSolver
    - SPASS (Modal logic prover) → binary path, for SPASSMlReasoner
    - EProver (FOL prover) → binary path, for EFOLReasoner
    - Python SAT tools (sat_solver.py, marco.py, maxsat_solver.py) — detection only

    Pattern from CoursIA tweety_init.py (issue #27).

    #1196 (verify-the-verification, FB-39): the previous version called the
    legacy *static* API ``EFOLReasoner.setPathToEProver`` /
    ``ClingoSolver.setPathToClingo`` / ``SPASSMlReasoner.setPathToSpass`` —
    but in the current Tweety build (1.28+) these are **instance** methods,
    so every call raised ``AttributeError`` and was silently swallowed by
    the surrounding ``except Exception: logger.debug(...)``. Result: no
    external solver was ever wired, yet the pipeline reported the configured
    solver name as if it were active (formal theater). The registry pattern
    below removes the dead call and exposes the detected path so handlers
    instantiate the reasoner with the correct constructor argument.
    """
    if not jpype.isJVMStarted():
        return

    tools_found = {}
    exe_suffix = ".exe" if platform.system() == "Windows" else ""

    # Clingo — ASP solver (Tweety expects the DIRECTORY containing the binary)
    for candidate in [
        shutil.which("clingo"),
        str(EXT_TOOLS_DIR / f"clingo/clingo{exe_suffix}"),
    ]:
        if candidate and Path(candidate).exists():
            tools_found["clingo"] = str(Path(candidate).parent.resolve())
            break
    else:
        # Try auto-downloading Clingo if not found
        if download_clingo():
            clingo_path = EXT_TOOLS_DIR / f"clingo/clingo{exe_suffix}"
            if clingo_path.exists():
                tools_found["clingo"] = str(clingo_path.parent.resolve())

    # SPASS — Modal logic theorem prover.
    # #1234: Tweety 1.29's SPASSMlReasoner emits the DFG special-formulae logic
    # token as ``EML`` (uppercase); SPASS 3.9's parser requires ``eml``
    # (lowercase) → "got 'EML', expected special type (eml)", SPASS aborts and
    # the modal axis cannot decide. This is a Tweety↔SPASS delivery-contract
    # version mismatch — the modal analogue of the eprover #1204 regression.
    # The EML→eml adapter (scripts/solvers/spass_eml_adapter.sh) rewrites only
    # that keyword case in the DFG temp file and forwards to the real SPASS,
    # which performs ALL modal reasoning (EML→FOL translation + saturation).
    # Prefer the adapter when present so Tweety's DFG is accepted; otherwise
    # register the raw binary (modal SPASS then fails honestly on the EML
    # mismatch — #1019, no fabrication).
    adapter_name = (
        "spass_eml_adapter.bat"
        if platform.system() == "Windows"
        else "spass_eml_adapter.sh"
    )
    for candidate in [
        str(EXT_TOOLS_DIR / f"spass/{adapter_name}"),
        shutil.which("SPASS"),
        str(EXT_TOOLS_DIR / f"spass/SPASS{exe_suffix}"),
    ]:
        if candidate and Path(candidate).exists():
            tools_found["spass"] = str(Path(candidate).resolve())
            break

    # EProver — FOL theorem prover
    for candidate in [
        shutil.which("eprover"),
        str(EXT_TOOLS_DIR / f"EProver/eprover{exe_suffix}"),
    ]:
        if candidate and Path(candidate).exists():
            tools_found["eprover"] = str(Path(candidate).resolve())
            break

    # Python SAT tools (detection only, not Java-wired)
    python_tools = {}
    for tool_name, filename in [
        ("sat_solver", "sat_solver.py"),
        ("marco", "marco.py"),
        ("maxsat_solver", "maxsat_solver.py"),
    ]:
        tool_path = EXT_TOOLS_DIR / filename
        if tool_path.exists():
            python_tools[tool_name] = str(tool_path.resolve())

    if not tools_found and not python_tools:
        logger.info("No external reasoning tools detected.")
        return

    if tools_found:
        logger.info(f"External Java tools detected: {list(tools_found.keys())}")
    if python_tools:
        logger.info(f"External Python tools detected: {list(python_tools.keys())}")

    # Record detected tool paths in the module-level registry. Logic handlers
    # (FOLHandler, ModalHandler, ASP) read these paths when they instantiate
    # the corresponding Tweety reasoner — passing the path as the constructor
    # argument, which is the only supported wiring in Tweety 1.28+.
    for tool_name, path in tools_found.items():
        EXTERNAL_TOOL_PATHS[tool_name] = path
        logger.info(f"  {tool_name} path registered: {path}")


def _build_tweety_classpath(tweety_libs_dir: Path) -> list[str]:
    """Ordered classpath of the Tweety jars present in ``tweety_libs_dir``.

    #1874 Piège 2: the old preemption key ``"full"`` also matched the Maven
    ``copy-dependencies`` thin aggregator ``org.tweetyproject.tweety-full-1.29.jar``
    (1918 bytes, **0 class**). A ``copy-dependencies`` layout deposits that thin jar
    *alongside* the ~150 real module jars; the preemption kept the thin one and threw
    the rest away, and ``startJVM`` then "booted" a JVM whose classpath held no Tweety
    class at all — success that decided nothing.

    A genuine fat jar in this ecosystem is always named ``*-with-dependencies.jar``
    (see ``TWEETY_JAR_FILENAME``); the thin aggregator is not. Keying the single-jar
    fast-path on that real fat name separates the two layouts: a fat jar (possibly
    several cached versions) resolves to the latest single jar; anything else is a
    multi-jar assembly and is loaded in full.
    """
    all_jars = sorted(tweety_libs_dir.glob("*.jar"), key=lambda p: p.name)
    uber_jars = [jar for jar in all_jars if "with-dependencies" in jar.name.lower()]
    if uber_jars:
        # Sort to pick the latest version (alphabetical = version order for tweety jars)
        return [str(sorted(uber_jars)[-1].resolve())]
    jar_entries = [str(jar.resolve()) for jar in all_jars]
    if not jar_entries:
        logger.critical(f"Aucun JAR trouvé dans {tweety_libs_dir}. Arrêt.")
    return jar_entries


def initialize_jvm(force_restart=False, session_fixture_owns_jvm=False) -> bool:
    """
    Démarre la JVM avec le CLASSPATH configuré, en s'assurant qu'elle n'est démarrée qu'une seule fois.
    La logique est thread-safe.
    """
    global _JVM_INITIALIZED_THIS_SESSION, _SESSION_FIXTURE_OWNS_JVM, _JVM_WAS_SHUTDOWN

    if jpype is None:  # #1697: honest-absent — report failure, do not crash
        logger.error(
            "jpype is not installed — the JVM cannot be started (#1697). "
            "Degraded boot: callers must render a degraded/unhealthy state."
        )
        return False

    with _jvm_lock:
        _SESSION_FIXTURE_OWNS_JVM = session_fixture_owns_jvm
        logger.info("=" * 50)
        logger.info(
            f"Tentative d'initialisation de la JVM (force_restart={force_restart}, session_owner={session_fixture_owns_jvm})"
        )

        if jpype.isJVMStarted():
            if not force_restart:
                logger.info("La JVM est déjà démarrée. Aucune action n'est nécessaire.")
                return True
            else:
                logger.warning(
                    "Forçage du redémarrage de la JVM. Arrêt de la JVM actuelle..."
                )
                shutdown_jvm(
                    called_by_session_fixture=True
                )  # On simule l'appel par la fixture pour permettre l'arrêt

        if _JVM_WAS_SHUTDOWN and not force_restart:
            logger.critical(
                "NON SUPPORTÉ: Tentative de ré-initialisation après un arrêt complet de la JVM sans forçage."
            )
            return False

        # Remise à zéro de l'état d'arrêt si on force le redémarrage
        _JVM_WAS_SHUTDOWN = False

        logger.info("--- Début du processus de démarrage de la JVM ---")
        if not download_tweety_jars():
            logger.critical("Échec du téléchargement des JARs Tweety. Arrêt.")
            return False

        # Couche 2: Prise de contrôle explicite du cycle de vie de la JVM
        # La configuration `destroy_jvm` est obsolète dans les versions récentes de JPype.
        # Le contrôle manuel est maintenant le comportement par défaut.
        pass

        java_home = find_valid_java_home()
        if not java_home:
            logger.critical("Aucun environnement Java valide trouvé. Arrêt.")
            return False
        os.environ["JAVA_HOME"] = java_home

        tweety_libs_dir = PROJ_ROOT / settings.jvm.tweety_libs_dir
        jar_entries = _build_tweety_classpath(tweety_libs_dir)
        if not jar_entries:
            return False

        # Build classpath: native dir first for JNI SAT solver getResource(), then JARs
        classpath = []
        native_libs_dir = PROJ_ROOT / settings.jvm.native_libs_dir
        if native_libs_dir.exists():
            classpath.append(str(native_libs_dir.resolve()))
            logger.info(
                f"Native SAT dir prepended to classpath: {native_libs_dir.resolve()}"
            )
        classpath.extend(jar_entries)

        try:
            # Correction de la logique de détection du chemin de la JVM.
            # JPype a besoin du chemin vers la librairie partagée (jvm.dll/libjvm.so), pas l'exécutable.
            # On cherche dans les emplacements standards.
            java_home_path = Path(java_home)
            if platform.system() == "Windows":
                # Ordre de recherche pour Windows
                search_paths = [
                    java_home_path / "bin" / "server" / "jvm.dll",
                    java_home_path / "bin" / "client" / "jvm.dll",
                    java_home_path / "bin" / "jvm.dll",
                ]
            else:
                # Ordre de recherche pour Linux/macOS
                search_paths = [
                    java_home_path / "lib" / "server" / "libjvm.so",
                    java_home_path / "lib" / "amd64" / "server" / "libjvm.so",
                    java_home_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so",
                    java_home_path / "lib" / "libjvm.so",
                ]

            jvm_path_explicit = None
            for path in search_paths:
                if path.exists():
                    jvm_path_explicit = str(path)
                    logger.info(f"Chemin de la JVM valide trouvé : {jvm_path_explicit}")
                    break

            if not jvm_path_explicit:
                logger.critical(
                    f"Impossible de trouver le fichier jvm.dll ou libjvm.so dans les chemins de recherche standards de JAVA_HOME: {java_home_path}"
                )
                # En dernier recours, on utilise la méthode par défaut de JPype qui peut fonctionner
                # si le système est bien configuré (ex: variables d'environnement).
                jvm_path_explicit = jpype.getDefaultJVMPath()
                logger.warning(
                    f"Utilisation du chemin par défaut de JPype comme solution de repli: {jvm_path_explicit}"
                )

            jvm_options = get_jvm_options()

            logger.info("--- Paramètres de Démarrage JVM ---")
            logger.info(f"  Chemin JVM: {jvm_path_explicit}")
            logger.info(f"  Options: {jvm_options}")
            logger.info(f"  Classpath: {classpath[0] if classpath else 'Vide'}")
            logger.info("------------------------------------")

            current_thread_id = threading.get_ident()
            logger.info(
                f"Appel à jpype.startJVM sur le point d'être exécuté depuis le thread ID: {current_thread_id}"
            )

            # Get timeout from settings or use default
            startup_timeout = getattr(
                settings.jvm,
                "startup_timeout_seconds",
                DEFAULT_JVM_STARTUP_TIMEOUT_SECONDS,
            )

            def _do_start_jvm():
                """Inner function to start JVM for timeout wrapper."""
                jpype.startJVM(
                    *jvm_options,
                    classpath=classpath,
                    jvmpath=jvm_path_explicit,
                    ignoreUnrecognized=True,
                    convertStrings=False,
                )

            # Execute JVM startup with timeout to prevent silent hangs
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_do_start_jvm)
                    future.result(timeout=startup_timeout)
            except FuturesTimeoutError:
                logger.critical(
                    f"JVM startup timed out after {startup_timeout} seconds. "
                    "Possible causes: slow disk, corrupted JARs, or JVM crash."
                )
                raise JVMStartupTimeoutError(
                    f"JVM startup exceeded timeout of {startup_timeout} seconds"
                )

            logger.info(
                f"Appel à jpype.startJVM terminé (Thread ID: {current_thread_id})."
            )
            _JVM_INITIALIZED_THIS_SESSION = True
            logger.info("[SUCCESS] JVM démarrée avec succès.")

            # Auto-detect and configure external reasoning tools (issue #27)
            _configure_external_tools()

            return True
        except Exception as e:
            logger.critical(
                f"CRASH: Échec critique du démarrage de la JVM: {e}", exc_info=True
            )
            # Potentiellement marquer la JVM comme non initialisable pour éviter des boucles
            return False


def shutdown_jvm(called_by_session_fixture=False):
    global _JVM_WAS_SHUTDOWN
    with _jvm_lock:
        if not jpype.isJVMStarted():
            return
        if _SESSION_FIXTURE_OWNS_JVM and not called_by_session_fixture:
            logger.warning(
                "Arrêt de la JVM demandé, mais elle est gérée par une fixture de session."
            )
            return
        logger.info("Tentative d'arrêt de la JVM...")
        try:
            jpype.shutdownJVM()
            logger.info("[SUCCESS] JVM arrêtée.")
            _JVM_WAS_SHUTDOWN = True
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de la JVM: {e}", exc_info=True)
            _JVM_WAS_SHUTDOWN = True


def is_jvm_started() -> bool:
    try:
        return jpype.isJVMStarted()
    except Exception:
        return False


def is_jvm_owned_by_session_fixture() -> bool:
    return _SESSION_FIXTURE_OWNS_JVM


if __name__ == "__main__":
    # La configuration du logger est déjà faite en haut du fichier
    print("Ce script n'est pas conçu pour être exécuté directement.")
    print("Il sert à l'initialisation de la JVM pour le projet.")
    # Test d'initialisation pour le débogage
    logger.info("Exécution du bloc `if __name__ == '__main__':` pour le test.")
    initialize_jvm()
    if is_jvm_started():
        print("JVM semble avoir démarré correctement.")
        shutdown_jvm()
    else:
        print("Échec du démarrage de la JVM.")
