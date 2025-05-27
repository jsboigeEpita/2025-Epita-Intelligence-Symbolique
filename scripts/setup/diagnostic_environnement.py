#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de diagnostic complet de l'environnement pour le projet d'Intelligence Symbolique.

Ce script diagnostique et résout automatiquement les problèmes de dépendances complexes :
1. Configuration Java/JPype
2. Gestion des clés API LLM (optionnel)
3. Tests de validation de l'environnement
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

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("diagnostic_environnement")

class EnvironmentDiagnostic:
    """Classe principale pour le diagnostic de l'environnement."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.results = {
            "python_info": {},
            "package_installation": {},
            "dependencies": {},
            "java_config": {},
            "api_keys": {},
            "recommendations": []
        }
        
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Exécute une commande et retourne le résultat."""
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
        """Vérifie l'environnement Python."""
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
        """Vérifie si le package du projet est installé."""
        logger.info("📦 Vérification de l'installation du package...")
        
        package_info = {
            "installed": False,
            "editable": False,
            "location": None,
            "error": None
        }
        
        try:
            # Tenter d'importer le package principal
            import argumentation_analysis
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
        """Vérifie les dépendances essentielles."""
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
    
    def check_java_configuration(self) -> Dict:
        """Vérifie la configuration Java et JPype."""
        logger.info("☕ Vérification de la configuration Java...")
        
        java_config = {
            "java_home": os.environ.get("JAVA_HOME"),
            "java_executable": None,
            "java_version": None,
            "jpype_available": False,
            "jpype_version": None,
            "jpype_mock_available": False,
            "recommendations": []
        }
        
        # Vérifier JAVA_HOME
        if java_config["java_home"]:
            logger.info(f"JAVA_HOME: {java_config['java_home']}")
            java_exe = Path(java_config["java_home"]) / "bin" / "java.exe"
            if java_exe.exists():
                java_config["java_executable"] = str(java_exe)
        else:
            logger.warning("JAVA_HOME non défini")
            java_config["recommendations"].append("Définir la variable d'environnement JAVA_HOME")
        
        # Vérifier Java dans PATH
        returncode, stdout, stderr = self.run_command(["java", "-version"])
        if returncode == 0:
            java_config["java_version"] = stderr.split('\n')[0] if stderr else stdout.split('\n')[0]
            logger.info(f"Java trouvé: {java_config['java_version']}")
        else:
            logger.warning("Java non trouvé dans PATH")
            java_config["recommendations"].append("Ajouter Java au PATH")
        
        # Vérifier JPype
        try:
            import jpype1 as jpype
            java_config["jpype_available"] = True
            java_config["jpype_version"] = jpype.__version__
            logger.info(f"✅ JPype1 installé: {java_config['jpype_version']}")
            
            # Tester JPype
            try:
                default_jvm = jpype.getDefaultJVMPath()
                logger.info(f"JVM par défaut: {default_jvm}")
            except Exception as e:
                logger.warning(f"Problème avec JPype: {e}")
                java_config["recommendations"].append("Vérifier la configuration JPype")
                
        except ImportError:
            logger.warning("JPype1 non installé")
            
            # Vérifier si le mock JPype est disponible
            try:
                mock_path = self.project_root / "tests" / "mocks" / "jpype_mock.py"
                if mock_path.exists():
                    java_config["jpype_mock_available"] = True
                    logger.info("✅ Mock JPype disponible")
                    java_config["recommendations"].append("Utiliser le mock JPype pour les tests")
                else:
                    java_config["recommendations"].append("Installer JPype1 ou configurer le mock JPype")
            except Exception:
                java_config["recommendations"].append("Installer JPype1 ou configurer le mock JPype")
        
        self.results["java_config"] = java_config
        return java_config
    
    def check_api_keys(self) -> Dict:
        """Vérifie la configuration des clés API (optionnel)."""
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
        """Génère des recommandations basées sur le diagnostic."""
        recommendations = []
        
        # Recommandations pour l'installation du package
        if not self.results["package_installation"].get("installed", False):
            recommendations.append("🔧 CRITIQUE: Installer le package en mode développement:")
            recommendations.append("   pip install -e .")
        
        # Recommandations pour les dépendances
        missing_essential = self.results["dependencies"].get("missing_essential", [])
        if missing_essential:
            recommendations.append("🔧 CRITIQUE: Installer les dépendances essentielles:")
            recommendations.append(f"   pip install {' '.join(missing_essential)}")
        
        # Recommandations pour Java/JPype
        java_config = self.results["java_config"]
        if not java_config.get("jpype_available", False) and not java_config.get("jpype_mock_available", False):
            recommendations.append("🔧 IMPORTANT: Configurer JPype ou utiliser le mock:")
            recommendations.append("   Option 1: pip install jpype1")
            recommendations.append("   Option 2: Utiliser le mock JPype (recommandé pour Python 3.12+)")
        
        # Recommandations pour l'environnement virtuel
        if not self.results["python_info"].get("in_venv", False):
            recommendations.append("⚠️  RECOMMANDÉ: Utiliser un environnement virtuel:")
            recommendations.append("   python -m venv venv")
            recommendations.append("   venv\\Scripts\\activate  # Windows")
            recommendations.append("   source venv/bin/activate  # Linux/Mac")
        
        return recommendations
    
    def create_validation_script(self) -> Path:
        """Crée un script de validation de l'environnement."""
        script_content = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de validation rapide de l'environnement.
Généré automatiquement par diagnostic_environnement.py
"""

import sys
import importlib

def validate_environment():
    """Valide rapidement l'environnement."""
    print("🔍 Validation rapide de l'environnement...")
    
    # Vérifier le package principal
    try:
        import argumentation_analysis
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
            from tests.mocks import jpype_mock
            print("✅ Mock JPype: OK")
            jpype_ok = True
        except ImportError:
            print("⚠️  JPype/Mock: Non disponible")
    
    print("\\n🎉 Validation terminée!")
    return True

if __name__ == "__main__":
    success = validate_environment()
    sys.exit(0 if success else 1)
'''
        
        script_path = self.project_root / "scripts" / "setup" / "validate_environment.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        logger.info(f"✅ Script de validation créé: {script_path}")
        return script_path
    
    def create_env_template(self) -> Path:
        """Crée un template .env sécurisé."""
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
        """Sauvegarde le rapport de diagnostic."""
        report_path = self.project_root / "diagnostic_report.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Rapport de diagnostic sauvegardé: {report_path}")
        return report_path
    
    def run_full_diagnostic(self) -> Dict:
        """Exécute le diagnostic complet."""
        logger.info("🚀 Démarrage du diagnostic complet de l'environnement...")
        logger.info("=" * 60)
        
        # Exécuter tous les checks
        self.check_python_environment()
        self.check_package_installation()
        self.check_core_dependencies()
        self.check_java_configuration()
        self.check_api_keys()
        
        # Générer recommandations
        recommendations = self.generate_recommendations()
        self.results["recommendations"].extend(recommendations)
        
        # Créer fichiers utiles
        self.create_validation_script()
        self.create_env_template()
        
        # Sauvegarder rapport
        self.save_diagnostic_report()
        
        # Afficher résumé
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Affiche un résumé du diagnostic."""
        logger.info("=" * 60)
        logger.info("📋 RÉSUMÉ DU DIAGNOSTIC")
        logger.info("=" * 60)
        
        # Statut général
        package_ok = self.results["package_installation"].get("installed", False)
        essential_deps_ok = len(self.results["dependencies"].get("missing_essential", [])) == 0
        
        if package_ok and essential_deps_ok:
            logger.info("🎉 STATUT: Environnement fonctionnel")
        elif package_ok:
            logger.info("⚠️  STATUT: Package installé, dépendances manquantes")
        else:
            logger.info("❌ STATUT: Configuration requise")
        
        # Afficher recommandations
        if self.results["recommendations"]:
            logger.info("\n🔧 ACTIONS RECOMMANDÉES:")
            for rec in self.results["recommendations"]:
                logger.info(f"   {rec}")
        
        logger.info("\n📁 FICHIERS CRÉÉS:")
        logger.info("   - scripts/setup/validate_environment.py (validation rapide)")
        logger.info("   - .env.template (template de configuration)")
        logger.info("   - diagnostic_report.json (rapport détaillé)")
        
        logger.info("=" * 60)

def main():
    """Fonction principale."""
    diagnostic = EnvironmentDiagnostic()
    results = diagnostic.run_full_diagnostic()
    
    # Code de sortie basé sur le statut
    package_ok = results["package_installation"].get("installed", False)
    essential_deps_ok = len(results["dependencies"].get("missing_essential", [])) == 0
    
    if package_ok and essential_deps_ok:
        sys.exit(0)  # Succès
    else:
        sys.exit(1)  # Problèmes détectés

if __name__ == "__main__":
    main()