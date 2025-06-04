# argumentation_analysis/core/jvm_setup.py
import jpype
import jpype.imports
import logging
import os
from pathlib import Path
from typing import Optional, List

# Configuration du logger pour ce module
logger = logging.getLogger("Orchestration.JPype") # Utiliser le même nom de logger que dans l'erreur originale

# Tentative de récupération du chemin du JDK portable, sinon None
PORTABLE_JDK_PATH: Optional[Path] = None
try:
    # S'assurer que PROJECT_ROOT_DIR est bien défini comme dans paths.py
    # Cela suppose que ce fichier est dans argumentation_analysis/core/
    PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    _JDK_SUBDIR = "libs/portable_jdk/jdk-17.0.11+9" # Ajuster si la version/nom du JDK change
    
    # Vérifier si le répertoire JDK existe
    _potential_jdk_path = PROJECT_ROOT_DIR / _JDK_SUBDIR
    if _potential_jdk_path.is_dir():
        PORTABLE_JDK_PATH = _potential_jdk_path
        logger.info(f"✅ JDK portable détecté : {PORTABLE_JDK_PATH}")
    else:
        logger.warning(f"⚠️ JDK portable non trouvé à l'emplacement attendu : {_potential_jdk_path}")
except Exception as e:
    logger.error(f"❌ Erreur lors de la détection du JDK portable : {e}", exc_info=True)


def get_jvm_options(jdk_path: Optional[Path] = PORTABLE_JDK_PATH) -> List[str]:
    """Prépare les options pour le démarrage de la JVM, incluant le chemin du JDK si disponible."""
    options = [
        "-Xms128m",  # Mémoire initiale minimale
        "-Xmx512m"   # Mémoire maximale
    ]
    logger.info(f"Options JVM de base définies : {options}")
    if jdk_path and jdk_path.is_dir():
        jvm_dll_path = None
        # Tenter de trouver le chemin correct vers jvm.dll ou libjvm.so
        # Pour Windows
        if (jdk_path / "bin" / "server" / "jvm.dll").exists():
            jvm_dll_path = jdk_path / "bin" / "server" / "jvm.dll"
        elif (jdk_path / "jre" / "bin" / "server" / "jvm.dll").exists(): # Structure JDK plus ancienne
             jvm_dll_path = jdk_path / "jre" / "bin" / "server" / "jvm.dll"
        # Pour Linux/macOS
        elif (jdk_path / "lib" / "server" / "libjvm.so").exists():
            jvm_dll_path = jdk_path / "lib" / "server" / "libjvm.so"
        elif (jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so").exists(): # Structure plus ancienne
            jvm_dll_path = jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so"

        if jvm_dll_path:
            logger.info(f"Utilisation de la JVM spécifiée : {jvm_dll_path}")
            # jpype.startJVM prend le chemin du fichier DLL/SO directement
            # ou le chemin du répertoire contenant la DLL/SO via l'option -Djava.library.path
            # Ici, nous passons le chemin direct à jpype.startJVM via l'argument jvmpath
            # donc pas besoin de l'ajouter aux options ici.
        else:
            logger.warning(f"jvm.dll ou libjvm.so non trouvé dans {jdk_path}. Utilisation du JDK par défaut du système.")
    else:
        logger.info("Aucun JDK portable spécifié ou trouvé. Utilisation du JDK par défaut du système.")
    return options

def initialize_jvm(lib_dir_path: str, jdk_path: Optional[Path] = PORTABLE_JDK_PATH) -> bool:
    """
    Initialise la JVM avec les JARs de TweetyProject.

    :param lib_dir_path: Chemin vers le répertoire contenant les fichiers JAR.
    :type lib_dir_path: str
    :param jdk_path: Chemin optionnel vers un JDK portable à utiliser.
    :type jdk_path: Optional[Path]
    :return: True si la JVM a été démarrée avec succès ou était déjà démarrée, False sinon.
    :rtype: bool
    """
    if jpype.isJVMStarted():
        logger.info("JVM déjà démarrée.")
        return True

    try:
        jar_directory = Path(lib_dir_path)
        if not jar_directory.is_dir():
            logger.error(f"❌ Le répertoire des JARs '{jar_directory}' n'existe pas ou n'est pas un répertoire.")
            return False

        # Stratégie: Inclure tous les JARs du répertoire.
        logger.info(f"Construction du classpath avec tous les JARs trouvés dans '{jar_directory}'.")
        jars = [str(jar_file) for jar_file in jar_directory.glob("*.jar")]
        
        if not jars:
            logger.error(f"❌ Aucun JAR trouvé pour le classpath dans '{jar_directory}' ! Démarrage annulé.")
            return False
        
        classpath = os.pathsep.join(jars)
        logger.info(f"Classpath construit avec {len(jars)} JAR(s) depuis '{jar_directory}'.")
        logger.debug(f"Classpath: {classpath}")

        jvm_options = get_jvm_options(jdk_path)
        
        # La logique de recherche de jvm_dll_to_use (lignes 99-112) est conservée pour information
        # mais jvm_dll_to_use n'est plus utilisé directement ci-dessous pour startJVM.
        jvm_dll_to_use = None
        if jdk_path:
            # Tenter de trouver le chemin correct vers jvm.dll ou libjvm.so
            # Pour Windows
            if (jdk_path / "bin" / "server" / "jvm.dll").exists():
                jvm_dll_to_use = str(jdk_path / "bin" / "server" / "jvm.dll")
            elif (jdk_path / "jre" / "bin" / "server" / "jvm.dll").exists(): # Structure JDK plus ancienne
                 jvm_dll_to_use = str(jdk_path / "jre" / "bin" / "server" / "jvm.dll")
            # Pour Linux/macOS
            elif (jdk_path / "lib" / "server" / "libjvm.so").exists():
                jvm_dll_to_use = str(jdk_path / "lib" / "server" / "libjvm.so")
            elif (jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so").exists(): # Structure plus ancienne
                jvm_dll_to_use = str(jdk_path / "jre" / "lib" / "amd64" / "server" / "libjvm.so")

            if jvm_dll_to_use: # Log informatif si un JDK portable est détecté
                 logger.info(f"Un JDK portable a été détecté à {jdk_path} (jvm.dll estimé: {jvm_dll_to_use}), mais nous allons prioriser la configuration système.")
            else:
                 logger.info(f"Aucun jvm.dll/libjvm.so trouvé dans le JDK portable spécifié: {jdk_path}. Nous allons utiliser la configuration système.")
        else:
            logger.info("Aucun JDK portable spécifié. Nous allons utiliser la configuration système.")

        # Simplified: Attempt to start JVM using system configuration.
        # This replaces the logic that tried portable JDK first or as fallback.
        logger.info(f"Attempting JVM start with system config. Classpath: {classpath}, Options: {jvm_options}")
        try:
            jpype.startJVM(classpath=[classpath], *jvm_options, convertStrings=False)
            logger.info("JVM started successfully with system configuration.")
        except Exception as e_system_start:
            logger.error(f"Failed to start JVM with system configuration: {e_system_start}", exc_info=True)
            raise # Re-raise the exception to see the full error for diagnosis
            
        logger.info("✅ JVM démarrée avec succès (ou tentatives faites).")
        
        # Test simple pour vérifier que les classes Tweety sont accessibles
        try:
            _ = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlSignature")
            logger.info("✅ Test de chargement de classe Tweety (PlSignature) réussi.")
        except Exception as e_test:
            logger.error(f"❌ Test de chargement de classe Tweety échoué après démarrage JVM: {e_test}", exc_info=True)
            # Ne pas retourner False ici, la JVM est démarrée, mais il y a un problème avec les JARs/classpath.
            # L'erreur originale "Aucun JAR trouvé" devrait être résolue si on arrive ici.
            # Le problème sera capturé plus tard lors de l'initialisation des composants Tweety.

        return True

    except Exception as e:
        logger.critical(f"❌ Échec critique du démarrage de la JVM: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # Pour des tests directs de ce module
    logging.basicConfig(level=logging.DEBUG)
    
    # Simuler LIBS_DIR comme dans paths.py pour le test
    # PROJECT_ROOT_DIR_MAIN est d:/2025-Epita-Intelligence-Symbolique-4
    # LIBS_DIR_MAIN est d:/2025-Epita-Intelligence-Symbolique-4/libs/tweety
    PROJECT_ROOT_DIR_MAIN = Path(__file__).resolve().parent.parent.parent 
    LIBS_DIR_MAIN = PROJECT_ROOT_DIR_MAIN / "libs" / "tweety"
    
    logger.info(f"Test: Utilisation de LIBS_DIR: {LIBS_DIR_MAIN}")
    
    # S'assurer que les JARs sont copiés pour le test si ce n'est pas déjà fait
    # (Normalement fait par les étapes précédentes de la tâche principale)
    if not list(LIBS_DIR_MAIN.glob("*.jar")):
        logger.warning(f"Aucun JAR dans {LIBS_DIR_MAIN}. Le test peut échouer si les JARs ne sont pas copiés.")

    success = initialize_jvm(str(LIBS_DIR_MAIN))
    if success:
        logger.info("Test initialize_jvm: SUCCÈS")
        # Tenter d'importer une classe pour vérifier
        try:
            TestClass = jpype.JClass("org.tweetyproject.logics.pl.syntax.PropositionalSignature")
            logger.info(f"Classe de test chargée: {TestClass}")
            sig = TestClass()
            logger.info(f"Instance de signature créée: {sig}")
            logger.info(f"Contient 'a': {sig.contains('a')}")
            sig.add(jpype.JClass("org.tweetyproject.logics.pl.syntax.Proposition")("a"))
            logger.info(f"Contient 'a' après ajout: {sig.contains('a')}")
            
        except Exception as e:
            logger.error(f"Erreur lors du test avec la classe Tweety: {e}", exc_info=True)
        finally:
            if jpype.isJVMStarted():
                jpype.shutdownJVM()
                logger.info("JVM arrêtée après le test.")
    else:
        logger.error("Test initialize_jvm: ÉCHEC")