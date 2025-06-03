#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Module pour le pipeline de diagnostic de l'environnement.

Ce module fournit les fonctionnalités nécessaires pour exécuter un diagnostic complet
de l'environnement de développement. Il vérifie la configuration de Python,
l'installation du package du projet, les dépendances essentielles et optionnelles,
la configuration de Java et JPype, la présence de clés API (optionnel),
et la conformité des dépendances listées dans un fichier `requirements.txt`.

Le pipeline génère un rapport de diagnostic, des recommandations pour corriger
les problèmes détectés, un script de validation rapide de l'environnement,
et un template `.env` pour la configuration des clés API.

Ce module est conçu pour être utilisé comme un outil de diagnostic autonome ou
intégré dans des scripts de configuration ou de CI/CD.
"""

import sys
import os
import logging
import subprocess
import platform
import importlib
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional

from project_core.dev_utils.env_checks import check_java_environment, check_jpype_config, check_python_dependencies
from project_core.utils.logging_utils import setup_logging

# Configuration du logger pour ce module
logger = logging.getLogger(__name__)

class EnvironmentDiagnostic:
    """Classe principale pour effectuer le diagnostic de l'environnement.

    Cette classe encapsule toutes les logiques de vérification, de génération de rapport,
    et de création d'artefacts pour le diagnostic de l'environnement.
    Elle maintient l'état du diagnostic dans un dictionnaire `self.results`.
    """
    
    def __init__(self, requirements_file_path: Path):
        """Initialise la classe EnvironmentDiagnostic.

        :param requirements_file_path: Chemin vers le fichier `requirements.txt` à utiliser
                                       pour la vérification des dépendances Python.
        :type requirements_file_path: Path
        """
        self.project_root = Path(__file__).parent.parent.parent
        self.requirements_file_path = requirements_file_path
        self.results = {
            "python_info": {},
            "package_installation": {},
            "dependencies": {},
            "java_config": {},
            "jpype_config": {},
            "api_keys": {},
            "python_dependencies_status": {},
            "recommendations": []
        }
        
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Exécute une commande système et retourne son code de sortie, stdout et stderr.

        Cette méthode utilitaire permet d'exécuter des commandes externes de manière
        sécurisée et de capturer leur sortie.

        :param cmd: La commande à exécuter, sous forme de liste de chaînes.
        :type cmd: List[str]
        :param cwd: Le répertoire de travail courant pour l'exécution de la commande.
                    Si None, utilise la racine du projet.
        :type cwd: Optional[Path]
        :return: Un tuple contenant le code de retour (int), la sortie standard (str),
                 et la sortie d'erreur (str). En cas d'exception lors de l'exécution,
                 retourne (-1, "", message_erreur).
        :rtype: Tuple[int, str, str]
        """
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd or self.project_root
            )
            stdout, stderr = process.communicate()
            return process.returncode, stdout, stderr
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de {cmd}: {e}")
            return -1, "", str(e)
    
    def check_python_environment(self) -> Dict:
        """Vérifie et collecte des informations sur l'environnement Python courant.

        Inclut la version de Python, l'exécutable, la plateforme, l'architecture,
        la présence d'un environnement virtuel, et les premiers chemins de PYTHONPATH.
        Ajoute une recommandation si aucun environnement virtuel n'est détecté.

        :return: Un dictionnaire contenant les informations sur l'environnement Python.
        :rtype: Dict
        """
        logger.info("🐍 Vérification de l'environnement Python...")
        
        python_info = {
            "version": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "in_venv": hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
            "pythonpath": sys.path[:5]  # Premiers 5 éléments
        }
        
        logger.info(f"Version Python: {python_info['version']}")
        logger.info(f"Exécutable: {python_info['executable']}")
        logger.info(f"Environnement virtuel: {'Oui' if python_info['in_venv'] else 'Non'}")
        
        if not python_info['in_venv']:
            self.results["recommendations"].append(
                "⚠️  Recommandation: Utilisez un environnement virtuel pour éviter les conflits de dépendances"
            )
        
        self.results["python_info"] = python_info
        return python_info
    
    def check_package_installation(self) -> Dict:
        """Vérifie si le package principal du projet est installé et s'il l'est en mode éditable.

        Tente d'importer le package `argumentation_analysis` et utilise `pip show`
        pour déterminer le mode d'installation. Ajoute une recommandation si le package
        n'est pas installé.

        :return: Un dictionnaire contenant le statut d'installation du package.
        :rtype: Dict
        """
        logger.info("📦 Vérification de l'installation du package...")
        
        package_info = {
            "installed": False,
            "editable": False,
            "location": None,
            "error": None
        }
        
        try:
            # Tenter d'importer le package principal
            import argumentation_analysis # Assurez-vous que ce nom est correct et importable
            package_info["installed"] = True
            package_info["location"] = str(Path(argumentation_analysis.__file__).parent)
            
            # Vérifier si installé en mode éditable
            returncode, stdout, stderr = self.run_command([sys.executable, "-m", "pip", "show", "argumentation_analysis"])
            if returncode == 0 and "Editable project location:" in stdout:
                package_info["editable"] = True
                
        except ImportError as e:
            package_info["error"] = str(e)
            logger.warning(f"Package non installé: {e}")
            self.results["recommendations"].append(
                "🔧 Action requise: Installer le package en mode développement avec 'pip install -e .'"
            )
        
        self.results["package_installation"] = package_info
        return package_info
    
    def check_core_dependencies(self) -> Dict:
        """Vérifie la présence et la version des dépendances Python essentielles et optionnelles.

        Les listes de dépendances essentielles et optionnelles sont définies en interne.
        Tente d'importer chaque dépendance et récupère sa version si disponible.
        Ajoute une recommandation si des dépendances essentielles sont manquantes.

        :return: Un dictionnaire détaillant le statut de chaque dépendance.
        :rtype: Dict
        """
        logger.info("🔍 Vérification des dépendances essentielles...")
        
        essential_deps = [
            "numpy", "pandas", "matplotlib", "cryptography", "cffi", "psutil"
        ]
        
        optional_deps = [
            "pytest", "pytest-cov", "scikit-learn", "networkx", 
            "torch", "transformers", "notebook"
        ]
        
        deps_status = {"essential": {}, "optional": {}, "missing_essential": [], "missing_optional": []}
        
        # Vérifier dépendances essentielles
        for dep in essential_deps:
            try:
                module = importlib.import_module(dep.replace("-", "_"))
                version = getattr(module, "__version__", "unknown")
                deps_status["essential"][dep] = {"installed": True, "version": version}
                logger.info(f"✅ {dep}: {version}")
            except ImportError:
                deps_status["essential"][dep] = {"installed": False, "version": None}
                deps_status["missing_essential"].append(dep)
                logger.warning(f"❌ {dep}: Non installé")
        
        # Vérifier dépendances optionnelles
        for dep in optional_deps:
            try:
                module = importlib.import_module(dep.replace("-", "_"))
                version = getattr(module, "__version__", "unknown")
                deps_status["optional"][dep] = {"installed": True, "version": version}
                logger.info(f"✅ {dep}: {version}")
            except ImportError:
                deps_status["optional"][dep] = {"installed": False, "version": None}
                deps_status["missing_optional"].append(dep)
                logger.info(f"ℹ️  {dep}: Non installé (optionnel)")
        
        if deps_status["missing_essential"]:
            self.results["recommendations"].append(
                f"🔧 Action requise: Installer les dépendances essentielles manquantes: {', '.join(deps_status['missing_essential'])}"
            )
        
        self.results["dependencies"] = deps_status
        return deps_status

    def check_api_keys(self) -> Dict:
        """Vérifie la configuration des clés API (OpenAI, Azure) de manière optionnelle.

        Recherche la présence d'un fichier `.env` à la racine du projet et vérifie
        si les variables d'environnement `OPENAI_API_KEY` ou `AZURE_OPENAI_KEY`
        sont définies. Ne lit pas les valeurs des clés pour des raisons de sécurité.
        Ajoute une recommandation si le fichier `.env` est absent.

        :return: Un dictionnaire indiquant la présence des configurations de clés API.
        :rtype: Dict
        """
        logger.info("🔑 Vérification des clés API (optionnel)...")
        
        api_config = {
            "env_file_exists": False,
            "openai_key": False,
            "azure_key": False,
            "recommendations": []
        }
        
        # Vérifier fichier .env
        env_file = self.project_root / ".env"
        if env_file.exists():
            api_config["env_file_exists"] = True
            logger.info("✅ Fichier .env trouvé")
            
            # Lire le contenu (sans exposer les clés)
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                    api_config["openai_key"] = "OPENAI_API_KEY" in content
                    api_config["azure_key"] = "AZURE_OPENAI_KEY" in content
            except Exception as e:
                logger.warning(f"Erreur lecture .env: {e}")
        else:
            logger.info("ℹ️  Fichier .env non trouvé (optionnel)")
            api_config["recommendations"].append("Créer un fichier .env pour les clés API si nécessaire")
        
        # Vérifier variables d'environnement
        if os.environ.get("OPENAI_API_KEY"):
            api_config["openai_key"] = True
            logger.info("✅ Clé OpenAI trouvée dans l'environnement")
        
        if os.environ.get("AZURE_OPENAI_KEY"):
            api_config["azure_key"] = True
            logger.info("✅ Clé Azure trouvée dans l'environnement")
        
        if not (api_config["openai_key"] or api_config["azure_key"]):
            logger.info("ℹ️  Aucune clé API configurée (optionnel pour certains tests)")
        
        self.results["api_keys"] = api_config
        return api_config
    
    def generate_recommendations(self) -> List[str]:
        """Génère une liste de recommandations basées sur les résultats du diagnostic.

        Compile les problèmes détectés lors des différentes étapes de vérification
        (installation du package, dépendances, Java, JPype, environnement virtuel)
        et formule des actions correctives. Ces recommandations sont stockées
        dans `self.results["recommendations"]`.

        :return: Une liste de chaînes de caractères, chaque chaîne étant une recommandation.
                 Note: cette méthode modifie également `self.results["recommendations"]` directement.
        :rtype: List[str]
        """
        recommendations = []
        # Les recommandations sont ajoutées à self.results["recommendations"]
        # au fur et à mesure des vérifications et consolidées ici.
        # Cette fonction pourrait être renommée ou son rôle clarifié,
        # car elle semble à la fois générer ET récupérer/consolider.
        # Pour l'instant, on garde la logique existante où elle peuple
        # une nouvelle liste `recommendations` basée sur `self.results`.
        
        # Recommandations pour l'installation du package
        if not self.results["package_installation"].get("installed", False):
            recommendations.append("🔧 CRITIQUE: Installer le package en mode développement:")
            recommendations.append("   pip install -e .")
        
        # Recommandations pour les dépendances
        missing_essential = self.results["dependencies"].get("missing_essential", [])
        if missing_essential:
            recommendations.append("🔧 CRITIQUE: Installer les dépendances essentielles:")
            recommendations.append(f"   pip install {' '.join(missing_essential)}")
        
        # Recommandations pour Java
        java_config_results = self.results.get("java_config", {})
        if not java_config_results.get("is_ok", True): 
            recommendations.append("🔧 IMPORTANT: Problèmes détectés avec l'environnement Java.")
            recommendations.append("   Consultez les logs produits par 'project_core.dev_utils.env_checks.check_java_environment' pour plus de détails.")
            recommendations.append("   Assurez-vous que Java est installé, que 'java -version' fonctionne et que JAVA_HOME est correctement configuré.")
        
        # Recommandations pour JPype
        jpype_config_results = self.results.get("jpype_config", {})
        if not jpype_config_results.get("is_ok", True):
            recommendations.append("🔧 IMPORTANT: Problèmes détectés avec la configuration de JPype.")
            recommendations.append("   Consultez les logs produits par 'project_core.dev_utils.env_checks.check_jpype_config' pour plus de détails.")
            recommendations.append("   Assurez-vous que JPype1 est installé et que la JVM peut être démarrée.")
            recommendations.append("   Vérifiez également la configuration de JAVA_HOME si JPype ne trouve pas la JVM.")

        # Recommandations pour l'environnement virtuel
        if not self.results["python_info"].get("in_venv", False):
            recommendations.append("⚠️  RECOMMANDÉ: Utiliser un environnement virtuel:")
            recommendations.append("   python -m venv venv")
            recommendations.append("   venv\\Scripts\\activate  # Windows")
            recommendations.append("   source venv/bin/activate  # Linux/Mac")
        
        return recommendations
    
    def create_validation_script(self) -> Path:
        """Crée un script Python pour une validation rapide de l'environnement.

        Le script généré (`scripts/setup/validate_environment.py`) effectue des vérifications
        de base comme l'importation du package principal et de quelques dépendances essentielles.
        Ceci permet à l'utilisateur de rapidement tester si les corrections apportées
        ont résolu les problèmes majeurs.

        :return: Le chemin vers le script de validation créé.
        :rtype: Path
        """
        # Contenu du script de validation.
        # Ce script est destiné à être simple et autonome.
        script_content = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de validation rapide de l'environnement.
Généré automatiquement par le pipeline de diagnostic.
"""

import sys
import importlib

def validate_environment():
    """Valide rapidement l'environnement."""
    print("🔍 Validation rapide de l'environnement...")
    
    # Vérifier le package principal
    try:
        import argumentation_analysis # Assurez-vous que ce nom est correct
        print("✅ Package argumentation_analysis: OK")
    except ImportError as e:
        print(f"❌ Package argumentation_analysis: {e}")
        return False
    
    # Vérifier dépendances essentielles
    essential_deps = ["numpy", "pandas", "matplotlib", "cryptography"]
    for dep in essential_deps:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep}: OK")
        except ImportError:
            print(f"❌ {dep}: Manquant")
            return False
    
    # Vérifier JPype ou mock
    jpype_ok = False
    try:
        import jpype1
        print("✅ JPype1: OK")
        jpype_ok = True
    except ImportError:
        try:
            # Tenter d'importer un mock si JPype n'est pas là.
            # Adapter le chemin si nécessaire, ex: from project_core.mocks import jpype_mock
            # Pour l'instant, on suppose un mock local au script de test ou un mock global.
            # Si le mock est dans tests/mocks/jpype_mock.py, il faut que tests soit dans PYTHONPATH
            # ou que le script soit lancé depuis la racine du projet.
            # Pour un module de pipeline, il est préférable de ne pas dépendre de tests/.
            # On pourrait passer un flag pour utiliser un mock ou le rendre configurable.
            # Pour l'instant, on laisse le try-except simple.
            # import jpype_mock # Ceci ne fonctionnera probablement pas directement.
            print("ℹ️  JPype1 non trouvé, tentative d'utilisation d'un mock non implémentée ici.")
        except ImportError:
            print("⚠️  JPype/Mock: Non disponible")
            # jpype_ok = False # Déjà False
    
    print("\\n🎉 Validation terminée!")
    return True

if __name__ == "__main__":
    success = validate_environment()
    sys.exit(0 if success else 1)
'''
        
        script_path = self.project_root / "scripts" / "setup" / "validate_environment.py"
        # S'assurer que le répertoire existe
        script_path.parent.mkdir(parents=True, exist_ok=True)
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        logger.info(f"✅ Script de validation créé: {script_path}")
        return script_path
    
    def create_env_template(self) -> Path:
        """Crée un fichier template `.env.template` à la racine du projet.

        Ce template fournit un modèle que les utilisateurs peuvent copier vers `.env`
        pour configurer leurs clés API et d'autres variables d'environnement
        pertinentes pour le projet (Java, JPype, logging).

        :return: Le chemin vers le fichier template `.env.template` créé.
        :rtype: Path
        """
        # Contenu du template .env.
        # Il est important de ne pas inclure de vraies clés ici.
        env_template = '''# Template de configuration des clés API
# Copiez ce fichier vers .env et remplissez vos clés

# Clés OpenAI (optionnel)
# OPENAI_API_KEY=your_openai_api_key_here
# OPENAI_ORG_ID=your_openai_org_id_here

# Clés Azure OpenAI (optionnel)
# AZURE_OPENAI_KEY=your_azure_openai_key_here
# AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint_here
# AZURE_OPENAI_VERSION=2023-12-01-preview

# Configuration Java (optionnel)
# JAVA_HOME=C:\\Program Files\\Java\\jdk-11.0.x
# JPYPE_JVM_PATH=C:\\Program Files\\Java\\jdk-11.0.x\\bin\\server\\jvm.dll

# Configuration de développement
# DEBUG=true
# LOG_LEVEL=INFO
'''
        
        template_path = self.project_root / ".env.template"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(env_template)
        
        logger.info(f"✅ Template .env créé: {template_path}")
        return template_path
    
    def save_diagnostic_report(self) -> Path:
        """Sauvegarde le rapport de diagnostic complet au format JSON.

        Le rapport (`diagnostic_report.json`) contient tous les résultats collectés
        par les différentes méthodes de vérification. Il est sauvegardé à la racine du projet.

        :return: Le chemin vers le fichier de rapport JSON sauvegardé.
        :rtype: Path
        """
        report_path = self.project_root / "diagnostic_report.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Rapport de diagnostic sauvegardé: {report_path}")
        return report_path
    
    def run_full_diagnostic(self) -> Dict:
        """Exécute l'ensemble du pipeline de diagnostic.

        Cette méthode orchestre l'appel séquentiel de toutes les étapes de vérification :
        - Environnement Python
        - Installation du package
        - Dépendances principales
        - Environnement Java (via `check_java_environment`)
        - Configuration JPype (via `check_jpype_config`)
        - Clés API (optionnel)
        - Dépendances Python listées dans `requirements.txt` (via `check_python_dependencies`)

        Elle génère ensuite les recommandations, crée le script de validation et le template .env,
        sauvegarde le rapport de diagnostic et affiche un résumé.

        :return: Un dictionnaire contenant tous les résultats du diagnostic.
        :rtype: Dict
        """
        logger.info("🚀 Démarrage du diagnostic complet de l'environnement...")
        logger.info("=" * 60)
        
        # Exécuter tous les checks
        self.check_python_environment()
        self.check_package_installation()
        self.check_core_dependencies()
        
        java_env_is_ok = check_java_environment()
        self.results["java_config"] = {
            "is_ok": java_env_is_ok,
            "message": "La vérification de l'environnement Java est effectuée par project_core.dev_utils.env_checks. Consulter les logs pour les détails."
        }
        jpype_env_is_ok = check_jpype_config()
        self.results["jpype_config"] = {
            "is_ok": jpype_env_is_ok,
            "message": "La vérification de la configuration JPype est effectuée par project_core.dev_utils.env_checks. Consulter les logs pour les détails."
        }
        self.check_api_keys()

        # Vérifier les dépendances Python à partir de requirements.txt
        # self.requirements_file_path est maintenant passé au constructeur
        python_deps_ok = check_python_dependencies(self.requirements_file_path)
        self.results["python_dependencies_status"] = {
            "file_checked": str(self.requirements_file_path),
            "all_ok": python_deps_ok,
            "message": f"Vérification des dépendances de {self.requirements_file_path} {'réussie' if python_deps_ok else 'échouée'}."
        }
        if not python_deps_ok:
            self.results["recommendations"].append(
                f"⚠️  Avertissement: Certaines dépendances dans {self.requirements_file_path} ne sont pas satisfaites. Consultez les logs de 'check_python_dependencies'."
            )
        
        # Générer recommandations
        recommendations = self.generate_recommendations() # self.results["recommendations"] est étendu à l'intérieur
        # self.results["recommendations"].extend(recommendations) # Déjà fait dans generate_recommendations si on modifie la liste directement
        
        # Créer fichiers utiles
        self.create_validation_script()
        self.create_env_template()
        
        # Sauvegarder rapport
        self.save_diagnostic_report()
        
        # Afficher résumé
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Affiche un résumé formaté du diagnostic dans les logs.

        Le résumé inclut un statut global (succès ou échec basé sur les vérifications critiques),
        le statut de chaque vérification majeure, les recommandations, et la liste des
        fichiers créés ou mis à jour par le pipeline.
        """
        logger.info("=" * 60)
        logger.info("📋 RÉSUMÉ DU DIAGNOSTIC")
        logger.info("=" * 60)
        
        # Statut général
        package_ok = self.results["package_installation"].get("installed", False)
        essential_deps_ok = len(self.results["dependencies"].get("missing_essential", [])) == 0
        java_ok = self.results["java_config"].get("is_ok", False)
        jpype_ok = self.results["jpype_config"].get("is_ok", False)
        python_deps_file_ok = self.results["python_dependencies_status"].get("all_ok", False)

        overall_status = package_ok and essential_deps_ok and java_ok and jpype_ok and python_deps_file_ok
        
        if overall_status:
            logger.info("🎉 STATUT GLOBAL: Environnement semble correctement configuré.")
        else:
            logger.warning("❌ STATUT GLOBAL: Des problèmes ont été détectés. Veuillez consulter les recommandations.")

        logger.info(f"  - Installation du package: {'✅ OK' if package_ok else '❌ Problème'}")
        logger.info(f"  - Dépendances essentielles: {'✅ OK' if essential_deps_ok else '❌ Problèmes'}")
        logger.info(f"  - Environnement Java: {'✅ OK' if java_ok else '❌ Problème'}")
        logger.info(f"  - Configuration JPype: {'✅ OK' if jpype_ok else '❌ Problème'}")
        logger.info(f"  - Dépendances ({self.requirements_file_path.name}): {'✅ OK' if python_deps_file_ok else '❌ Problèmes'}")

        # Afficher recommandations
        if self.results["recommendations"]:
            logger.info("\n🔧 ACTIONS RECOMMANDÉES:")
            unique_recommendations = sorted(list(set(self.results["recommendations"]))) # Éviter les doublons
            for rec in unique_recommendations:
                logger.info(f"   {rec}")
        
        logger.info("\n📁 FICHIERS CRÉÉS/MIS À JOUR:")
        logger.info(f"   - {self.project_root / 'scripts' / 'setup' / 'validate_environment.py'} (validation rapide)")
        logger.info(f"   - {self.project_root / '.env.template'} (template de configuration)")
        logger.info(f"   - {self.project_root / 'diagnostic_report.json'} (rapport détaillé)")
        
        logger.info("=" * 60)

def run_environment_diagnostic_pipeline(requirements_path: str, log_level: str = "INFO") -> int:
    """Exécute le pipeline de diagnostic complet de l'environnement.

    Cette fonction principale orchestre le diagnostic de l'environnement.
    Elle configure le logging, initialise la classe `EnvironmentDiagnostic`,
    et lance une série de vérifications. Ces vérifications incluent:
    - L'environnement Python (version, exécutable, environnement virtuel).
    - L'installation du package principal du projet.
    - Les dépendances Python essentielles et optionnelles.
    - La configuration de l'environnement Java (JDK, JAVA_HOME).
    - La configuration de JPype pour l'intégration Java-Python.
    - La présence (optionnelle) de clés API via un fichier `.env` ou variables d'environnement.
    - La conformité des dépendances listées dans le fichier `requirements.txt` spécifié.

    Sur la base des résultats, le pipeline génère des recommandations pour résoudre
    les problèmes identifiés. Il crée également des artefacts utiles :
    - Un script Python de validation rapide de l'environnement.
    - Un fichier template `.env.template` pour la gestion des clés API.
    - Un rapport de diagnostic détaillé au format JSON.

    La fonction se termine en affichant un résumé du diagnostic et retourne un code de sortie
    indiquant le succès global des vérifications critiques.

    :param requirements_path: Chemin vers le fichier `requirements.txt` à vérifier.
    :type requirements_path: str
    :param log_level: Niveau de logging à utiliser pour le pipeline (par exemple, "INFO", "DEBUG").
                      La valeur par défaut est "INFO".
    :type log_level: str
    :return: Code de sortie indiquant le résultat du diagnostic.
             0 si les vérifications critiques (installation du package, dépendances essentielles,
             Java, JPype, et le fichier requirements) sont toutes OK.
             1 si un ou plusieurs problèmes critiques sont détectés.
    :rtype: int
    :raises FileNotFoundError: Si le fichier `requirements.txt` spécifié n'est pas trouvé
                               lorsque le pipeline est exécuté directement via `if __name__ == '__main__':`.
                               (Note: cette exception est gérée dans le bloc `if __name__ == '__main__':`
                               et n'est pas directement levée par cette fonction elle-même dans son usage normal).
    """
    # Configuration du logging pour le pipeline
    # Le logger global du module est déjà défini, setup_logging configure le root logger
    # et potentiellement d'autres handlers.
    # Si setup_logging est bien idempotent ou configure le root, c'est OK.
    # Sinon, il faudrait peut-être passer le logger spécifique.
    # Pour l'instant, on suppose que setup_logging gère bien la configuration globale.
    numeric_log_level = getattr(logging, log_level.upper(), logging.INFO)
    setup_logging(level=numeric_log_level) # Utilise la fonction importée

    logger.info(f"Démarrage du pipeline de diagnostic de l'environnement avec log_level={log_level}.")
    logger.info(f"Fichier requirements utilisé : {requirements_path}")

    req_file_path = Path(requirements_path)
    if not req_file_path.is_absolute():
        # Si le chemin n'est pas absolu, on le considère relatif à la racine du projet
        # La classe EnvironmentDiagnostic calcule project_root, utilisons-le.
        # Pour l'instant, on le passe tel quel, EnvironmentDiagnostic le résoudra si besoin
        # ou on s'assure que le script appelant passe un chemin absolu ou bien résolu.
        # Pour l'instant, on suppose que le chemin est correct.
        pass

    diagnostic = EnvironmentDiagnostic(requirements_file_path=req_file_path)
    results = diagnostic.run_full_diagnostic()
    
    # Code de sortie basé sur le statut (peut être affiné)
    package_ok = results["package_installation"].get("installed", False)
    essential_deps_ok = len(results["dependencies"].get("missing_essential", [])) == 0
    java_ok = results["java_config"].get("is_ok", False)
    jpype_ok = results["jpype_config"].get("is_ok", False)
    python_deps_file_ok = results["python_dependencies_status"].get("all_ok", False)

    # Un diagnostic est considéré comme "réussi" si tous les éléments critiques sont OK.
    if package_ok and essential_deps_ok and java_ok and jpype_ok and python_deps_file_ok:
        logger.info("Pipeline de diagnostic terminé avec succès.")
        return 0  # Succès
    else:
        logger.warning("Pipeline de diagnostic terminé avec des problèmes détectés.")
        return 1  # Problèmes détectés

if __name__ == '__main__':
    # Exemple d'utilisation directe du pipeline (pour test)
    # Dans un scénario réel, ce pipeline serait appelé par un script lanceur
    # qui gère argparse.
    
    # Déterminer le chemin racine du projet pour trouver requirements.txt par défaut
    current_script_path = Path(__file__).resolve()
    project_root_dir = current_script_path.parent.parent.parent 
    default_req_path = project_root_dir / "requirements.txt"

    if not default_req_path.exists():
        print(f"ERREUR: Le fichier requirements.txt par défaut est introuvable à {default_req_path}", file=sys.stderr)
        print("Veuillez spécifier un chemin valide via les arguments du script lanceur.", file=sys.stderr)
        sys.exit(2)

    print(f"Lancement du pipeline de diagnostic en mode test depuis {__file__}...")
    exit_code = run_environment_diagnostic_pipeline(
        requirements_path=str(default_req_path),
        log_level="INFO"
    )
    print(f"Pipeline de diagnostic (test) terminé avec le code de sortie: {exit_code}")
    sys.exit(exit_code)