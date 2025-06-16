# core/jvm_setup.py
import os
import sys
import jpype
import logging
import platform
import shutil
import subprocess
import zipfile
import requests
from pathlib import Path
from typing import Optional, List, Dict
from tqdm import tqdm


# --- Configuration et Constantes ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constantes de Configuration ---
# Répertoires (utilisant pathlib pour la robustesse multi-plateforme)
PROJ_ROOT = Path(__file__).resolve().parents[3]
LIBS_DIR = PROJ_ROOT / "libs"
TWEETY_VERSION = "1.24" # Mettre à jour au besoin
# TODO: Lire depuis un fichier de config centralisé (par ex. pyproject.toml ou un .conf)
# Au lieu de TWEETY_VERSION = "1.24", on pourrait avoir get_config("tweety.version")

# Configuration des URLs des dépendances
TWEETY_BASE_URL = "https://repo.maven.apache.org/maven2"
TWEETY_ARTIFACTS: Dict[str, Dict[str, str]] = {
    # Core
    "tweety-arg": {"group": "net.sf.tweety", "version": TWEETY_VERSION},
    # Modules principaux (à adapter selon les besoins du projet)
    "tweety-lp": {"group": "net.sf.tweety.lp", "version": TWEETY_VERSION},
    "tweety-log": {"group": "net.sf.tweety.log", "version": TWEETY_VERSION},
    "tweety-math": {"group": "net.sf.tweety.math", "version": TWEETY_VERSION},
    # Natives (exemple ; peuvent ne pas exister pour toutes les versions)
    "tweety-native-maxsat": {"group": "net.sf.tweety.native", "version": TWEETY_VERSION, "classifier": f"maxsat-{platform.system().lower()}"}
}

# Configuration JDK portable
MIN_JAVA_VERSION = 11
JDK_VERSION = "17.0.2" # Exemple, choisir une version LTS stable
JDK_BUILD = "8"
JDK_URL_TEMPLATE = "https://github.com/adoptium/temurin{maj_v}-binaries/releases/download/jdk-{v}%2B{b}/OpenJDK{maj_v}U-jdk_{arch}_{os}_hotspot_{v}_{b_flat}.zip"
# Windows: x64_windows, aarch64_windows | Linux: x64_linux, aarch64_linux | macOS: x64_mac, aarch64_mac

# --- Fonctions Utilitaires ---
def get_os_arch_for_jdk() -> Dict[str, str]:
    """Détermine l'OS et l'architecture pour l'URL de téléchargement du JDK."""
    system = platform.system().lower()
    arch = platform.machine().lower()

    os_map = {"windows": "windows", "linux": "linux", "darwin": "mac"}
    arch_map = {"amd64": "x64", "x86_64": "x64", "aarch64": "aarch64", "arm64": "aarch64"}

    if system not in os_map:
        raise OSError(f"Système d'exploitation non supporté pour le JDK portable : {platform.system()}")
    if arch not in arch_map:
        raise OSError(f"Architecture non supportée pour le JDK portable : {arch}")

    return {"os": os_map[system], "arch": arch_map[arch]}


def download_file(url: str, dest_path: Path):
    """Télécharge un fichier avec une barre de progression."""
    logging.info(f"Téléchargement de {url} vers {dest_path}...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        with open(dest_path, "wb") as f, tqdm(
            desc=dest_path.name,
            total=total_size,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                bar.update(size)
    except requests.RequestException as e:
        logging.error(f"Erreur de téléchargement pour {url}: {e}")
        if dest_path.exists():
            dest_path.unlink() # Nettoyer le fichier partiel
        raise
    except IOError as e:
        logging.error(f"Erreur d'écriture du fichier {dest_path}: {e}")
        if dest_path.exists():
            dest_path.unlink()
        raise


def unzip_file(zip_path: Path, dest_dir: Path):
    """Décompresse un fichier ZIP."""
    logging.info(f"Décompression de {zip_path} vers {dest_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Pour éviter les problèmes de "répertoire dans un répertoire"
            # On vérifie si tout le contenu est dans un seul dossier
            file_list = zip_ref.namelist()
            top_level_dirs = {Path(f).parts[0] for f in file_list}
            
            if len(top_level_dirs) == 1:
                 # Cas où le contenu est dans un sous-répertoire (ex: jdk-17.0.2+8/...)
                 # On extrait directement le contenu de ce sous-répertoire
                temp_extract_dir = dest_dir / "temp_extract"
                zip_ref.extractall(temp_extract_dir)
                
                source_dir = temp_extract_dir / top_level_dirs.pop()
                for item in source_dir.iterdir():
                    shutil.move(str(item), str(dest_dir / item.name))
                temp_extract_dir.rmdir() # rm -r
            else:
                 # Le contenu est déjà à la racine du zip
                 zip_ref.extractall(dest_dir)

        zip_path.unlink() # Nettoyer l'archive
        logging.info("Décompression terminée.")
    except (zipfile.BadZipFile, IOError) as e:
        logging.error(f"Erreur lors de la décompression de {zip_path}: {e}")
        raise

# --- Fonctions de Gestion des Dépendances ---

# --- Fonction Principale de Téléchargement Tweety ---
def download_tweety_jars(
    version: str = TWEETY_VERSION,
    target_dir: str = LIBS_DIR,
    native_subdir: str = "native"
    ) -> bool:
    """
    Vérifie et télécharge les JARs Tweety (Core + Modules) et les binaires natifs nécessaires.

    Returns:
        bool: True si des téléchargements ont eu lieu, False sinon.
    """
    LIBS_DIR.mkdir(exist_ok=True)
    (LIBS_DIR / native_subdir).mkdir(exist_ok=True)
    
    downloaded = False
    for name, a_info in TWEETY_ARTIFACTS.items():
        group_path = a_info["group"].replace('.', '/')
        a_version = a_info["version"]
        
        jar_name_parts = [name, a_version]
        if "classifier" in a_info:
            jar_name_parts.append(a_info['classifier'])

        jar_filename = f"{'-'.join(jar_name_parts)}.jar"
        jar_path = LIBS_DIR / jar_filename

        if not jar_path.exists():
            downloaded = True
            url = f"{TWEETY_BASE_URL}/{group_path}/{name}/{a_version}/{jar_filename}"
            try:
                download_file(url, jar_path)
            except Exception:
                logging.error(f"Échec du téléchargement pour {name}. Le projet pourrait ne pas fonctionner.")
                return False # On arrête si un JAR critique manque

    if downloaded:
        logging.info("Téléchargement des bibliothèques Tweety terminé.")
    else:
        logging.info("Toutes les bibliothèques Tweety sont déjà à jour.")
        
    return downloaded


# --- Fonction de détection JAVA_HOME (modifiée pour prioriser Java >= MIN_JAVA_VERSION) ---
def find_valid_java_home() -> Optional[str]:
    """
    Cherche un JAVA_HOME valide ou un JDK portable.
    1. Vérifie la variable d'environnement JAVA_HOME.
    2. Si invalide, cherche un JDK portable local.
    3. Si non trouvé, télécharge et installe un JDK portable.
    """
    # 1. Vérifier JAVA_HOME
    java_home_env = os.environ.get("JAVA_HOME")
    if java_home_env:
        logging.info(f"Variable JAVA_HOME trouvée : {java_home_env}")
        if is_valid_jdk(Path(java_home_env)):
            return java_home_env

    # 2. Chercher un JDK portable
    portable_jdk_dir = PROJ_ROOT / "jdk"
    if portable_jdk_dir.exists() and is_valid_jdk(portable_jdk_dir):
        logging.info(f"JDK portable valide trouvé : {portable_jdk_dir}")
        return str(portable_jdk_dir)

    # 3. Télécharger un nouveau JDK portable
    logging.warning("Aucun JDK valide trouvé. Tentative de téléchargement d'un JDK portable.")
    return download_portable_jdk(portable_jdk_dir)


def download_portable_jdk(target_dir: Path) -> Optional[str]:
    """Télécharge et extrait un JDK portable."""
    try:
        os_arch = get_os_arch_for_jdk()
    except OSError as e:
        logging.error(e)
        return None

    jdk_url = JDK_URL_TEMPLATE.format(
        maj_v=JDK_VERSION.split('.')[0],
        v=JDK_VERSION,
        b=JDK_BUILD,
        b_flat=JDK_BUILD, # Le format de l'URL est parfois incohérent
        arch=os_arch['arch'],
        os=os_arch['os']
    )
    
    target_dir.mkdir(exist_ok=True)
    zip_path = target_dir / "jdk.zip"

    try:
        download_file(jdk_url, zip_path)
        # Supprimer le contenu précédent avant de décompresser
        for item in target_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            elif item.is_file() and item.suffix != '.zip':
                item.unlink()

        unzip_file(zip_path, target_dir)
        
        # Vérifier que le JDK est maintenant valide
        if is_valid_jdk(target_dir):
            logging.info(f"JDK portable installé avec succès dans {target_dir}")
            return str(target_dir)
        else:
            logging.error("L'extraction du JDK n'a pas produit une installation valide.")
            return None

    except (requests.RequestException, IOError, zipfile.BadZipFile, shutil.Error) as e:
        logging.error(f"Échec de l'installation du JDK portable : {e}")
        shutil.rmtree(target_dir, ignore_errors=True) # Nettoyage complet
        return None


def is_valid_jdk(path: Path) -> bool:
    """Vérifie si un répertoire est un JDK valide et respecte la version minimale."""
    if not path.is_dir():
        return False
        
    java_exe = path / "bin" / ("java.exe" if platform.system() == "Windows" else "java")
    if not java_exe.exists():
        logging.warning(f"Validation JDK échouée: 'java' non trouvé dans {path / 'bin'}")
        return False

    try:
        # Exécuter `java -version` et capturer la sortie
        # stderr est utilisé par Java pour afficher la version
        result = subprocess.run(
            [str(java_exe), "-version"],
            capture_output=True,
            text=True,
            check=True,
            stderr=subprocess.PIPE
        )
        version_output = result.stderr
        
        # Parser la version (ex: "openjdk version "11.0.12" 2021-07-20")
        first_line = version_output.splitlines()[0]
        version_str = first_line.split('"')[1] # "11.0.12"
        major_version = int(version_str.split('.')[0])

        if major_version >= MIN_JAVA_VERSION:
            logging.info(f"Version Java détectée: {version_str} (Majeure: {major_version}) -> Valide.")
            return True
        else:
            logging.warning(f"Version Java {major_version} est inférieure au minimum requis ({MIN_JAVA_VERSION}).")
            return False

    except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError) as e:
        logging.error(f"Erreur lors de la validation de la version de Java à {path}: {e}")
        return False
        
# --- Gestion du cycle de vie de la JVM ---

_jvm_started = False

def start_jvm_if_needed(force_restart: bool = False):
    """
    Démarre la JVM avec le classpath configuré, si elle n'est pas déjà démarrée.
    Cette fonction est idempotente par défaut.
    """
    global _jvm_started
    if _jvm_started and not force_restart:
        logging.debug("La JVM est déjà démarrée. Aucune action requise.")
        return

    if force_restart and jpype.isJVMStarted():
        logging.info("Forçage du redémarrage de la JVM...")
        shutdown_jvm()

    # 1. S'assurer que les dépendances sont présentes
    download_tweety_jars()
    
    # 2. Trouver un JAVA_HOME valide (ou installer un JDK)
    java_home = find_valid_java_home()
    if not java_home:
        raise RuntimeError(
            "Impossible de trouver ou d'installer un JDK valide. "
            "Veuillez définir JAVA_HOME sur un JDK version 11+ ou assurer une connexion internet."
        )

    # 3. Construire le Classpath
    jar_paths = [str(p) for p in LIBS_DIR.glob("*.jar")]
    classpath = os.pathsep.join(jar_paths)

    if not jar_paths:
        raise RuntimeError(f"Aucune bibliothèque (.jar) trouvée dans {LIBS_DIR}. Le classpath est vide.")
        
    logging.info(f"Classpath configuré : {classpath}")
    
    # 4. Démarrer la JVM
    try:
        logging.info("Démarrage de la JVM...")
        jpype.startJVM(
            #jpype.getDefaultJVMPath(), # Laisser JPype trouver la libjvm
            jvmpath=jpype.getDefaultJVMPath(),
            classpath=classpath,
            ignoreUnrecognized=True,
            convertStrings=False,
            # Passer le JAVA_HOME trouvé permet de s'assurer que JPype utilise le bon JDK
            # C'est implicite si la libjvm est trouvée via le path, mais c'est plus sûr
        )
        _jvm_started = True
        logging.info("JVM démarrée avec succès.")

    except Exception as e:
        logging.error(f"Erreur fatale lors du démarrage de la JVM : {e}")
        logging.error(f"JAVA_HOME utilisé (si trouvé) : {java_home}")
        logging.error(f"Chemin JVM par défaut de JPype : {jpype.getDefaultJVMPath()}")
        # Tenter d'offrir plus de diagnostics
        if sys.platform == "win32" and "Error: Could not find " in str(e):
             logging.error("Astuce Windows: Assurez-vous que Microsoft Visual C++ Redistributable est installé.")
        elif "No matching overloads found" in str(e):
             logging.error("Astuce: Cette erreur peut survenir si le classpath est incorrect ou si une dépendance manque.")
        raise


def shutdown_jvm():
    """Arrête la JVM si elle est en cours d'exécution."""
    global _jvm_started
    if jpype.isJVMStarted():
        logging.info("Arrêt de la JVM...")
        jpype.shutdownJVM()
        _jvm_started = False
        logging.info("JVM arrêtée.")
    else:
        logging.debug("La JVM n'est pas en cours d'exécution.")

# --- Point d'entrée pour exemple ou test ---
if __name__ == "__main__":
    logging.info("--- Démonstration du module jvm_setup ---")
    try:
        logging.info("\n1. Première tentative de démarrage de la JVM...")
        start_jvm_if_needed()

        logging.info("\n2. Tentative de démarrage redondante (devrait être ignorée)...")
        start_jvm_if_needed()

        # Test simple d'importation Java
        try:
            JString = jpype.JClass("java.lang.String")
            my_string = JString("Ceci est un test depuis Python!")
            logging.info(f"Test Java réussi: {my_string}")
        except Exception as e:
            logging.error(f"Le test d'importation Java a échoué: {e}")

    except Exception as e:
        logging.error(f"Une erreur est survenue durant la démonstration : {e}")

    finally:
        logging.info("\n3. Arrêt de la JVM...")
        shutdown_jvm()
        logging.info("\n--- Fin de la démonstration ---")
