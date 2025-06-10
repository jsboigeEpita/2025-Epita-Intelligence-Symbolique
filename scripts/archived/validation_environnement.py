#!/usr/bin/env python3
"""
Script de validation d'environnement pour le projet Intelligence Symbolique
========================================================================

Ce script valide que tous les composants nécessaires sont correctement configurés :
- Environnement conda 'projet-is' avec JDK17
- Chargement des variables .env (OPENAI_API_KEY, etc.)
- Accès à gpt-4o-mini via OpenRouter
- Configuration JVM pour TweetyProject
- Répertoires de travail (.temp, etc.)

Utilisation:
    python scripts/validation_environnement.py
    python scripts/validation_environnement.py --verbose
    python scripts/validation_environnement.py --test-api

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

# Ajouter le répertoire racine au path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

class EnvironmentValidator:
    """Validateur complet de l'environnement de développement"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = project_root
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_tests = 0
        
    def log(self, message: str, level: str = "INFO"):
        """Log avec niveau"""
        if self.verbose or level in ["ERROR", "SUCCESS"]:
            prefix = {
                "INFO": "[INFO] ",
                "SUCCESS": "[OK] ",
                "WARNING": "[WARN] ",
                "ERROR": "[ERROR] "
            }.get(level, "")
            print(f"{prefix} {message}")
    
    def test_auto_env_import(self) -> bool:
        """Test 1: Import de scripts.core.auto_env"""
        self.total_tests += 1
        self.log("Test 1: Import scripts.core.auto_env", "INFO")
        
        try:
            # Test import simple
            import scripts.core.auto_env
            self.log("Import scripts.core.auto_env reussi", "SUCCESS")
            
            # Test fonction ensure_env
            from scripts.core.auto_env import ensure_env
            result = ensure_env(silent=not self.verbose)
            
            if result:
                self.log("Auto-activation environnement reussie", "SUCCESS")
                self.success_count += 1
                return True
            else:
                self.log("Auto-activation environnement en mode degrade", "WARNING")
                self.warnings.append("Auto-activation environnement limitée")
                self.success_count += 1
                return True
                
        except Exception as e:
            self.log(f"Echec import auto_env: {e}", "ERROR")
            self.errors.append(f"Import auto_env: {e}")
            return False
    
    def test_conda_environment(self) -> bool:
        """Test 2: Environnement conda 'projet-is'"""
        self.total_tests += 1
        self.log("Test 2: Environnement conda 'projet-is'", "INFO")
        
        try:
            # Vérifier conda disponible
            result = subprocess.run(['conda', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
            self.log("Conda non disponible", "ERROR")
                self.errors.append("Conda non installé ou non accessible")
                return False
            
            self.log(f"Conda disponible: {result.stdout.strip()}", "SUCCESS")
            
            # Lister les environnements
            result = subprocess.run(['conda', 'env', 'list', '--json'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                envs_data = json.loads(result.stdout)
                env_names = [Path(env_path).name for env_path in envs_data.get('envs', [])]
                
                if 'projet-is' in env_names:
                self.log("Environnement 'projet-is' trouve", "SUCCESS")
                    
                    # Vérifier si actif
                    current_env = os.environ.get('CONDA_DEFAULT_ENV', '')
                    if current_env == 'projet-is':
                    self.log("Environnement 'projet-is' actuellement actif", "SUCCESS")
                    else:
                    self.log(f"Environnement actuel: {current_env or 'base'}", "INFO")
                    
                    self.success_count += 1
                    return True
                else:
                self.log("Environnement 'projet-is' non trouve", "ERROR")
                    self.log(f"Environnements disponibles: {env_names}", "INFO")
                    self.errors.append("Environnement conda 'projet-is' manquant")
                    return False
            else:
            self.log("Impossible de lister les environnements conda", "ERROR")
                self.errors.append("Erreur listing environnements conda")
                return False
                
        except Exception as e:
            self.log(f"Erreur test conda: {e}", "ERROR")
            self.errors.append(f"Test conda: {e}")
            return False
    
    def test_dotenv_loading(self) -> bool:
        """Test 3: Chargement des variables .env"""
        self.total_tests += 1
        self.log("Test 3: Chargement variables .env", "INFO")
        
        # Variables critiques à vérifier
        required_vars = [
            'OPENAI_API_KEY',
            'OPENAI_CHAT_MODEL_ID', 
            'GLOBAL_LLM_SERVICE'
        ]
        
        optional_vars = [
            'OPENAI_BASE_URL',
            'OPENROUTER_API_KEY',
            'TEXT_CONFIG_PASSPHRASE',
            'JAVA_HOME'
        ]
        
        missing_required = []
        missing_optional = []
        
        # Vérifier .env existe
        env_file = self.project_root / '.env'
        if not env_file.exists():
            self.log("Fichier .env non trouve", "ERROR")
            self.errors.append("Fichier .env manquant")
            return False
        
        self.log(f"Fichier .env trouve: {env_file}", "SUCCESS")
        
        # Vérifier variables requises
        for var in required_vars:
            value = os.environ.get(var)
            if not value:
                missing_required.append(var)
            self.log(f"Variable requise manquante: {var}", "ERROR")
            else:
                # Masquer les clés API pour la sécurité
                if 'KEY' in var:
                    display_value = value[:10] + "..." if len(value) > 10 else "***"
                else:
                    display_value = value
            self.log(f"{var}={display_value}", "SUCCESS")
        
        # Vérifier variables optionnelles
        for var in optional_vars:
            value = os.environ.get(var)
            if not value:
                missing_optional.append(var)
            self.log(f"Variable optionnelle manquante: {var}", "WARNING")
            else:
                if 'KEY' in var:
                    display_value = value[:10] + "..." if len(value) > 10 else "***"
                else:
                    display_value = value
            self.log(f"{var}={display_value}", "SUCCESS")
        
        if missing_required:
            self.errors.append(f"Variables requises manquantes: {missing_required}")
            return False
        
        if missing_optional:
            self.warnings.append(f"Variables optionnelles manquantes: {missing_optional}")
        
        self.success_count += 1
        return True
    
    def test_gpt4o_mini_access(self, test_api: bool = False) -> bool:
        """Test 4: Accès à gpt-4o-mini"""
        self.total_tests += 1
        self.log("Test 4: Configuration gpt-4o-mini", "INFO")
        
        try:
            # Vérifier configuration de base
            api_key = os.environ.get('OPENAI_API_KEY')
            base_url = os.environ.get('OPENAI_BASE_URL')
            model_id = os.environ.get('OPENAI_CHAT_MODEL_ID')
            
            if not api_key:
                self.log("OPENAI_API_KEY manquante", "ERROR")
                self.errors.append("API Key OpenAI manquante")
                return False
            
            if model_id != 'gpt-4o-mini':
                self.log(f"Modele configure: {model_id} (attendu: gpt-4o-mini)", "WARNING")
                self.warnings.append(f"Modèle différent de gpt-4o-mini: {model_id}")
            else:
                self.log("Modele gpt-4o-mini configure", "SUCCESS")
            
            if base_url:
                self.log(f"Base URL configuree: {base_url}", "SUCCESS")
            else:
                self.log("Utilisation API OpenAI standard", "INFO")
            
            # Test API optionnel
            if test_api:
                self.log("Test connexion API...", "INFO")
                try:
                    import openai
                    
                    client = openai.OpenAI(
                        api_key=api_key,
                        base_url=base_url if base_url else None
                    )
                    
                    # Test simple avec prompt minimal
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": "Test connexion: répondez 'OK'"}],
                        max_tokens=5,
                        temperature=0
                    )
                    
                    content = response.choices[0].message.content
                    self.log(f"Test API reussi. Reponse: {content}", "SUCCESS")
                    
                except Exception as e:
                    self.log(f"Test API echoue: {e}", "WARNING")
                    self.warnings.append(f"Test API: {e}")
            
            self.success_count += 1
            return True
            
        except Exception as e:
            self.log(f"Erreur test gpt-4o-mini: {e}", "ERROR")
            self.errors.append(f"Test gpt-4o-mini: {e}")
            return False
    
    def test_java_jdk17(self) -> bool:
        """Test 5: Configuration Java JDK17"""
        self.total_tests += 1
        self.log("Test 5: Configuration Java JDK17", "INFO")
        
        try:
            java_home = os.environ.get('JAVA_HOME')
            
            if not java_home:
                self.log("JAVA_HOME non defini", "WARNING")
                self.warnings.append("JAVA_HOME non configuré")
            else:
                java_home_path = Path(java_home)
                
                # Convertir en chemin absolu si relatif
                if not java_home_path.is_absolute():
                    java_home_path = (self.project_root / java_home_path).resolve()
                    self.log(f"JAVA_HOME relatif resolu: {java_home_path}", "INFO")
                
                if java_home_path.exists():
                    self.log(f"JAVA_HOME trouve: {java_home_path}", "SUCCESS")
                    
                    # Vérifier java.exe ou java
                    java_exe = java_home_path / "bin" / "java.exe"
                    java_bin = java_home_path / "bin" / "java"
                    
                    java_cmd = None
                    if java_exe.exists():
                        java_cmd = str(java_exe)
                    elif java_bin.exists():
                        java_cmd = str(java_bin)
                    
                    if java_cmd:
                        # Tester version Java
                        result = subprocess.run([java_cmd, '-version'], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            version_output = result.stderr  # Java affiche version sur stderr
                            self.log(f"✓ Java disponible", "SUCCESS")
                            
                            # Chercher version 17
                            if "17." in version_output or "version 17" in version_output:
                                self.log("✓ Java JDK17 confirmé", "SUCCESS")
                            else:
                                self.log(f"⚠️  Version Java: {version_output.split()[2] if len(version_output.split()) > 2 else 'inconnue'}", "WARNING")
                                self.warnings.append("Version Java différente de JDK17")
                        else:
                            self.log("⚠️  Impossible d'exécuter Java", "WARNING")
                            self.warnings.append("Java non exécutable")
                    else:
                        self.log("⚠️  Exécutable Java non trouvé dans JAVA_HOME/bin", "WARNING")
                        self.warnings.append("Exécutable Java manquant")
                else:
                    self.log(f"✗ JAVA_HOME inexistant: {java_home_path}", "ERROR")
                    self.errors.append(f"JAVA_HOME inexistant: {java_home_path}")
                    return False
            
            self.success_count += 1
            return True
            
        except Exception as e:
            self.log(f"✗ Erreur test Java: {e}", "ERROR")
            self.errors.append(f"Test Java: {e}")
            return False
    
    def test_work_directories(self) -> bool:
        """Test 6: Répertoires de travail"""
        self.total_tests += 1
        self.log("Test 6: Répertoires de travail", "INFO")
        
        required_dirs = ['.temp', 'logs', 'output']
        optional_dirs = ['data', 'cache', 'backup']
        
        try:
            for dir_name in required_dirs:
                dir_path = self.project_root / dir_name
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.log(f"✓ Répertoire créé: {dir_name}", "SUCCESS")
                else:
                    self.log(f"✓ Répertoire existant: {dir_name}", "SUCCESS")
            
            for dir_name in optional_dirs:
                dir_path = self.project_root / dir_name
                if dir_path.exists():
                    self.log(f"✓ Répertoire optionnel trouvé: {dir_name}", "SUCCESS")
                else:
                    self.log(f"ℹ️  Répertoire optionnel absent: {dir_name}", "INFO")
            
            self.success_count += 1
            return True
            
        except Exception as e:
            self.log(f"✗ Erreur création répertoires: {e}", "ERROR")
            self.errors.append(f"Répertoires de travail: {e}")
            return False
    
    def get_one_liner_activation(self) -> str:
        """Génère le one-liner d'activation optimal"""
        return "import scripts.core.auto_env  # Auto-activation environnement intelligent"
    
    def run_validation(self, test_api: bool = False) -> Dict:
        """Exécute tous les tests de validation"""
        self.log("DEBUT VALIDATION ENVIRONNEMENT", "INFO")
        self.log("=" * 60, "INFO")
        
        # Exécuter tous les tests
        tests = [
            self.test_auto_env_import,
            self.test_conda_environment, 
            self.test_dotenv_loading,
            lambda: self.test_gpt4o_mini_access(test_api),
            self.test_java_jdk17,
            self.test_work_directories
        ]
        
        passed_tests = 0
        for test in tests:
            try:
                if test():
                    passed_tests += 1
                self.log("-" * 40, "INFO")
            except Exception as e:
                self.log(f"✗ Erreur inattendue dans test: {e}", "ERROR")
                self.errors.append(f"Erreur test: {e}")
        
        # Résumé
        self.log("RESUME VALIDATION", "INFO")
        self.log("=" * 60, "INFO")
        self.log(f"Tests réussis: {passed_tests}/{self.total_tests}", "SUCCESS" if passed_tests == self.total_tests else "WARNING")
        
        if self.errors:
        if self.errors:
            self.log(f"Erreurs ({len(self.errors)}):", "ERROR")
            for error in self.errors:
                self.log(f"  - {error}", "ERROR")
        
        if self.warnings:
        if self.warnings:
            self.log(f"Avertissements ({len(self.warnings)}):", "WARNING")
            for warning in self.warnings:
                self.log(f"  - {warning}", "WARNING")
        
        # One-liner
        self.log("ONE-LINER D'ACTIVATION:", "INFO")
        self.log(self.get_one_liner_activation(), "SUCCESS")
        
        return {
            'success': len(self.errors) == 0,
            'passed_tests': passed_tests,
            'total_tests': self.total_tests,
            'errors': self.errors,
            'warnings': self.warnings,
            'one_liner': self.get_one_liner_activation()
        }


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Validation complète de l'environnement Intelligence Symbolique"
    )
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mode verbeux avec détails complets')
    parser.add_argument('--test-api', action='store_true',
                       help='Tester la connexion API réelle (optionnel)')
    
    args = parser.parse_args()
    
    validator = EnvironmentValidator(verbose=args.verbose)
    result = validator.run_validation(test_api=args.test_api)
    
    # Code de sortie
    exit_code = 0 if result['success'] else 1
    
    print(f"\nVALIDATION {'REUSSIE' if result['success'] else 'ECHOUEE'}")
    print(f"Exit code: {exit_code}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()