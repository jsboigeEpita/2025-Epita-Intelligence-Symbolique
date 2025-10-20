#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de résolution automatique des problèmes d'environnement.

Ce script résout automatiquement les problèmes identifiés par diagnostic_environnement.py :
1. Installation du package en mode développement
2. Installation des dépendances manquantes
3. Configuration du mock JPype si nécessaire
import argumentation_analysis.core.environment
4. Validation finale
"""

import sys
import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fix_environment")


class EnvironmentFixer:
    """Classe pour résoudre automatiquement les problèmes d'environnement."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.diagnostic_report = None

    def load_diagnostic_report(self) -> Optional[Dict]:
        """Charge le rapport de diagnostic s'il existe."""
        report_path = self.project_root / "diagnostic_report.json"

        if report_path.exists():
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    self.diagnostic_report = json.load(f)
                logger.info("✅ Rapport de diagnostic chargé")
                return self.diagnostic_report
            except Exception as e:
                logger.warning(f"Erreur lors du chargement du rapport: {e}")
        else:
            logger.info(
                "ℹ️  Aucun rapport de diagnostic trouvé, exécution du diagnostic..."
            )

        return None

    def run_command(
        self, cmd: List[str], cwd: Optional[Path] = None
    ) -> Tuple[int, str, str]:
        """Exécute une commande et retourne le résultat."""
        try:
            logger.info(f"Exécution: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd or self.project_root,
            )
            stdout, stderr = process.communicate()
            return process.returncode, stdout, stderr
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de {cmd}: {e}")
            return -1, "", str(e)

    def fix_package_installation(self) -> bool:
        """Installe le package en mode développement."""
        logger.info("🔧 Installation du package en mode développement...")

        # Vérifier si setup.py existe
        setup_py = self.project_root / "setup.py"
        if not setup_py.exists():
            logger.error("❌ Fichier setup.py non trouvé")
            return False

        # Installer en mode développement
        returncode, stdout, stderr = self.run_command(
            [sys.executable, "-m", "pip", "install", "-e", "."]
        )

        if returncode == 0:
            logger.info("✅ Package installé en mode développement")
            return True
        else:
            logger.error(f"❌ Erreur lors de l'installation: {stderr}")
            return False

    def fix_essential_dependencies(self) -> bool:
        """Installe les dépendances essentielles manquantes."""
        logger.info("🔧 Installation des dépendances essentielles...")

        # Dépendances essentielles de base
        essential_deps = [
            "numpy>=1.24.0",
            "pandas>=2.0.0",
            "matplotlib>=3.5.0",
            "cryptography>=37.0.0",
            "cffi>=1.15.0",
            "psutil>=5.9.0",
        ]

        # Installer les dépendances essentielles
        returncode, stdout, stderr = self.run_command(
            [sys.executable, "-m", "pip", "install"] + essential_deps
        )

        if returncode == 0:
            logger.info("✅ Dépendances essentielles installées")
        else:
            logger.warning(
                f"⚠️  Problème lors de l'installation des dépendances: {stderr}"
            )

        return returncode == 0

    def fix_test_dependencies(self) -> bool:
        """Installe les dépendances de test."""
        logger.info("🔧 Installation des dépendances de test...")

        test_deps = ["pytest>=7.0.0", "pytest-cov>=3.0.0", "pytest-asyncio>=0.18.0"]

        returncode, stdout, stderr = self.run_command(
            [sys.executable, "-m", "pip", "install"] + test_deps
        )

        if returncode == 0:
            logger.info("✅ Dépendances de test installées")
            return True
        else:
            logger.warning(
                f"⚠️  Problème lors de l'installation des dépendances de test: {stderr}"
            )
            return False

    def fix_jpype_configuration(self) -> bool:
        """Configure JPype ou le mock JPype."""
        logger.info("🔧 Configuration de JPype...")

        # Vérifier la version de Python
        python_version = sys.version_info

        if python_version >= (3, 12):
            logger.info("Python 3.12+ détecté, configuration du mock JPype...")
            return self.setup_jpype_mock()
        else:
            logger.info("Python < 3.12 détecté, tentative d'installation de JPype1...")
            return self.install_jpype1()

    def install_jpype1(self) -> bool:
        """Tente d'installer JPype1."""
        try:
            returncode, stdout, stderr = self.run_command(
                [sys.executable, "-m", "pip", "install", "jpype1>=1.4.0"]
            )

            if returncode == 0:
                logger.info("✅ JPype1 installé avec succès")
                return True
            else:
                logger.warning(f"⚠️  Échec de l'installation de JPype1: {stderr}")
                logger.info("Basculement vers le mock JPype...")
                return self.setup_jpype_mock()

        except Exception as e:
            logger.warning(f"⚠️  Erreur lors de l'installation de JPype1: {e}")
            logger.info("Basculement vers le mock JPype...")
            return self.setup_jpype_mock()

    def setup_jpype_mock(self) -> bool:
        """Configure le mock JPype."""
        logger.info("🔧 Configuration du mock JPype...")

        # Créer le répertoire des mocks s'il n'existe pas
        mock_dir = self.project_root / "tests" / "mocks"
        mock_dir.mkdir(parents=True, exist_ok=True)

        # Créer le fichier __init__.py
        init_file = mock_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Mock modules\n")

        # Créer le mock JPype
        mock_content = '''"""
Mock de JPype1 pour la compatibilité avec Python 3.12+.

Ce mock simule les fonctionnalités essentielles de JPype1 utilisées par le projet.
"""

import sys
import os
from unittest.mock import MagicMock

# Version du mock
__version__ = "1.4.0-mock"

# Variables globales pour simuler l'état de la JVM
_jvm_started = False
_jvm_path = None

def isJVMStarted():
    """Simule jpype.isJVMStarted()."""
    return _jvm_started

def startJVM(jvmpath=None, *args, **kwargs):
    """Simule jpype.startJVM()."""
    global _jvm_started, _jvm_path
    _jvm_started = True
    _jvm_path = jvmpath or getDefaultJVMPath()
    print(f"[MOCK] JVM démarrée avec le chemin: {_jvm_path}")

def shutdownJVM():
    """Simule jpype.shutdownJVM()."""
    global _jvm_started
    _jvm_started = False
    print("[MOCK] JVM arrêtée")

def getDefaultJVMPath():
    """Simule jpype.getDefaultJVMPath()."""
    # Retourner un chemin par défaut basé sur l'OS
    if sys.platform == "win32":
        return "C:\\\\Program Files\\\\Java\\\\jdk-11\\\\bin\\\\server\\\\jvm.dll"
    elif sys.platform == "darwin":
        return "/Library/Java/JavaVirtualMachines/jdk-11.jdk/Contents/Home/lib/server/libjvm.dylib"
    else:
        return "/usr/lib/jvm/java-11-openjdk/lib/server/libjvm.so"

def JClass(name):
    """Simule jpype.JClass()."""
    mock_class = MagicMock()
    mock_class.__name__ = name
    return mock_class

def JArray(type_):
    """Simule jpype.JArray()."""
    return MagicMock()

def JString(value):
    """Simule jpype.JString()."""
    return str(value)

# Classes Java simulées
class JObject:
    """Simule jpype.JObject."""
    pass

class JException(Exception):
    """Simule jpype.JException."""
    pass

# Installer le mock dans sys.modules
sys.modules['jpype1'] = sys.modules[__name__]
sys.modules['jpype'] = sys.modules[__name__]

print("[MOCK] Mock JPype1 activé pour la compatibilité Python 3.12+")
'''

        mock_file = mock_dir / "jpype_mock.py"
        with open(mock_file, "w", encoding="utf-8") as f:
            f.write(mock_content)

        logger.info("✅ Mock JPype configuré")

        # Créer un script d'activation du mock
        activation_script = '''"""
Script d'activation du mock JPype.
À importer avant toute utilisation de JPype dans les tests.
"""

# Importer le mock pour l'activer
from tests.mocks import jpype_mock

print("Mock JPype activé")
'''

        activation_file = mock_dir / "activate_jpype_mock.py"
        with open(activation_file, "w", encoding="utf-8") as f:
            f.write(activation_script)

        return True

    def create_installation_script(self) -> Path:
        """Crée un script d'installation complet pour les étudiants."""
        script_content = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'installation automatique pour les étudiants.
Ce script configure automatiquement l'environnement de développement.
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd):
    """Exécute une commande et affiche le résultat."""
    print(f"Exécution: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Erreur: {result.stderr}")
        return False
    return True

def main():
    """Installation automatique."""
    print("🚀 Installation automatique de l'environnement...")
    print("=" * 50)
    
    # Vérifier Python
    print(f"Python version: {sys.version}")
    
    # Mettre à jour pip
    print("\\n📦 Mise à jour de pip...")
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Installer le package en mode développement
    print("\\n🔧 Installation du package en mode développement...")
    if not run_command([sys.executable, "-m", "pip", "install", "-e", "."]):
        print("❌ Échec de l'installation du package")
        return False
    
    # Installer les dépendances essentielles
    print("\\n📚 Installation des dépendances essentielles...")
    essential_deps = [
        "numpy>=1.24.0", "pandas>=2.0.0", "matplotlib>=3.5.0",
        "cryptography>=37.0.0", "cffi>=1.15.0", "psutil>=5.9.0",
        "pytest>=7.0.0", "pytest-cov>=3.0.0"
    ]
    
    if not run_command([sys.executable, "-m", "pip", "install"] + essential_deps):
        print("⚠️  Problème lors de l'installation des dépendances")
    
    # Configurer JPype
    print("\\n☕ Configuration de JPype...")
    python_version = sys.version_info
    if python_version >= (3, 12):
        print("Python 3.12+ détecté, utilisation du mock JPype")
        # Le mock sera configuré automatiquement
    else:
        print("Tentative d'installation de JPype1...")
        run_command([sys.executable, "-m", "pip", "install", "jpype1>=1.4.0"])
    
    # Validation finale
    print("\\n✅ Validation de l'installation...")
    validation_result = subprocess.run([
        sys.executable, "scripts/setup/validate_environment.py"
    ], capture_output=True, text=True)
    
    if validation_result.returncode == 0:
        print("🎉 Installation réussie!")
        print("\\nVous pouvez maintenant:")
        print("  - Exécuter les tests: pytest")
        print("  - Utiliser les notebooks: jupyter notebook")
        print("  - Consulter la documentation: docs/")
    else:
        print("⚠️  Installation partiellement réussie")
        print("Consultez le rapport de diagnostic pour plus de détails")
    
    return validation_result.returncode == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''

        script_path = self.project_root / "install_environment.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        logger.info(f"✅ Script d'installation créé: {script_path}")
        return script_path

    def run_validation(self) -> bool:
        """Exécute la validation finale."""
        logger.info("🔍 Validation finale de l'environnement...")

        validation_script = (
            self.project_root / "scripts" / "setup" / "validate_environment.py"
        )

        if validation_script.exists():
            returncode, stdout, stderr = self.run_command(
                [sys.executable, str(validation_script)]
            )

            if returncode == 0:
                logger.info("✅ Validation réussie!")
                return True
            else:
                logger.warning("⚠️  Validation partiellement réussie")
                logger.info(stdout)
                return False
        else:
            logger.warning("Script de validation non trouvé")
            return False

    def fix_all_issues(self) -> bool:
        """Résout tous les problèmes détectés."""
        logger.info("🚀 Résolution automatique des problèmes...")
        logger.info("=" * 60)

        success = True

        # 1. Installer le package en mode développement
        if not self.fix_package_installation():
            success = False

        # 2. Installer les dépendances essentielles
        if not self.fix_essential_dependencies():
            success = False

        # 3. Installer les dépendances de test
        if not self.fix_test_dependencies():
            success = False

        # 4. Configurer JPype
        if not self.fix_jpype_configuration():
            success = False

        # 5. Créer le script d'installation pour les étudiants
        self.create_installation_script()

        # 6. Validation finale
        validation_success = self.run_validation()

        # Résumé
        logger.info("=" * 60)
        if success and validation_success:
            logger.info("🎉 SUCCÈS: Tous les problèmes ont été résolus!")
            logger.info("L'environnement est maintenant prêt à l'utilisation.")
        elif success:
            logger.info("⚠️  PARTIEL: La plupart des problèmes ont été résolus.")
            logger.info("Quelques problèmes mineurs peuvent subsister.")
        else:
            logger.info(
                "❌ ÉCHEC: Certains problèmes n'ont pas pu être résolus automatiquement."
            )
            logger.info("Consultez les logs ci-dessus pour plus de détails.")

        logger.info("\\n📁 FICHIERS CRÉÉS:")
        logger.info("   - install_environment.py (installation automatique)")
        logger.info("   - tests/mocks/jpype_mock.py (mock JPype)")
        logger.info("   - scripts/setup/validate_environment.py (validation)")

        return success and validation_success


def main():
    """Fonction principale."""
    fixer = EnvironmentFixer()

    # Charger le rapport de diagnostic si disponible
    fixer.load_diagnostic_report()

    # Résoudre tous les problèmes
    success = fixer.fix_all_issues()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
