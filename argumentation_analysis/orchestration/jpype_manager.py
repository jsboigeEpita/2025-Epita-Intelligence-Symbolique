import jpype
import jpype.imports
import os
import sys
import glob
from pathlib import Path
import logging

class JPypeManager:
    """
    Gestionnaire pour la configuration et le cycle de vie de la JVM via JPype.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.jars_path = None
        self.jvm_options = [
            '-Xms64m',
            '-Xmx512m',
            '-Dfile.encoding=UTF-8',
            '-Djava.awt.headless=true'
        ]

    def set_jars_path(self, path: str):
        """Définit le chemin vers le répertoire contenant les fichiers JAR."""
        self.jars_path = path

    def start_jvm(self):
        """
        Démarre la JVM avec le classpath et les options configurés.
        """
        if jpype.isJVMStarted():
            self.logger.info("La JVM est déjà démarrée.")
            return

        if not self.jars_path:
            raise ValueError("Le chemin vers les fichiers JAR n'a pas été défini. Appelez set_jars_path() d'abord.")

        project_root = Path(__file__).parent.parent.parent
        full_jars_path = project_root / self.jars_path
        
        if not full_jars_path.exists():
            raise FileNotFoundError(f"Le répertoire des JARs est introuvable: {full_jars_path}")

        jar_files = glob.glob(str(full_jars_path / '*.jar'))
        if not jar_files:
            raise FileNotFoundError(f"Aucun fichier JAR trouvé dans {full_jars_path}")

        classpath = os.pathsep.join(jar_files)
        self.logger.info(f"Classpath configuré : {classpath}")

        try:
            jvm_path = self._find_portable_jvm()
            if not jvm_path:
                self.logger.warning("Aucun JDK portable trouvé, utilisation de jpype.getDefaultJVMPath().")
                jvm_path = jpype.getDefaultJVMPath()

            self.logger.info(f"Utilisation de la JVM: {jvm_path}")
            self.logger.info("Démarrage de la JVM...")
            jpype.startJVM(jvm_path, "-ea", f"-Djava.class.path={classpath}", *self.jvm_options)
            self.logger.info("JVM démarrée avec succès.")
        except Exception as e:
            self.logger.error(f"Échec du démarrage de la JVM: {e}")
            raise

    def _find_portable_jvm(self) -> str:
        """
        Cherche un JDK portable dans le répertoire du projet.
        Retourne le chemin vers la librairie jvm (dll ou so) si trouvé.
        """
        project_root = Path(__file__).parent.parent.parent
        portable_jdk_dir = project_root / 'portable_jdk'
        
        if not portable_jdk_dir.is_dir():
            self.logger.info("Le répertoire JDK portable n'existe pas.")
            return None

        # Chercher la librairie jvm de manière récursive
        if sys.platform == "win32":
            jvm_libs = list(portable_jdk_dir.glob("**/bin/server/jvm.dll"))
        else:
            jvm_libs = list(portable_jdk_dir.glob("**/lib/server/libjvm.so"))
        
        if jvm_libs:
            self.logger.info(f"JDK portable trouvé : {jvm_libs[0]}")
            return str(jvm_libs[0])
            
        self.logger.warning("Aucune librairie JVM trouvée dans le répertoire JDK portable.")
        return None