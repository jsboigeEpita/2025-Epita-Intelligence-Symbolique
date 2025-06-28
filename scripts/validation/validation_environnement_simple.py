#!/usr/bin/env python3
"""
Script de validation d'environnement simplifie
==============================================

Validation rapide de l'environnement Intelligence Symbolique :
- Environnement conda 'projet-is' 
- Variables .env (OPENAI_API_KEY, etc.)
- Configuration Java JDK17
- Test gpt-4o-mini
import argumentation_analysis.core.environment

Usage: python scripts/validation_environnement_simple.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Ajouter le répertoire racine au path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

def log_status(message, status="INFO"):
    """Log simple avec statut"""
    prefixes = {
        "INFO": "[INFO]",
        "OK": "[OK]  ",
        "WARN": "[WARN]",
        "ERROR": "[ERROR]"
    }
    prefix = prefixes.get(status, "[INFO]")
    print(f"{prefix} {message}")

def test_auto_env():
    """Test import auto_env"""
    log_status("Test 1: Import scripts.core.auto_env")
    try:
        import scripts.core.auto_env
        log_status("Import scripts.core.auto_env reussi", "OK")
        
        from scripts.core.auto_env import ensure_env
        result = ensure_env(silent=True)
        
        if result:
            log_status("Auto-activation environnement reussie", "OK")
        else:
            log_status("Auto-activation en mode degrade", "WARN")
        return True
    except Exception as e:
        log_status(f"Echec import auto_env: {e}", "ERROR")
        return False

def test_conda():
    """Test environnement conda"""
    log_status("Test 2: Environnement conda 'projet-is'")
    try:
        # Tester conda
        result = subprocess.run(['conda', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            log_status("Conda non disponible", "ERROR")
            return False
        
        log_status(f"Conda disponible: {result.stdout.strip()}", "OK")
        
        # Lister environnements
        result = subprocess.run(['conda', 'env', 'list', '--json'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            envs_data = json.loads(result.stdout)
            env_names = [Path(env_path).name for env_path in envs_data.get('envs', [])]
            
            if 'projet-is' in env_names:
                log_status("Environnement 'projet-is' trouve", "OK")
                
                current_env = os.environ.get('CONDA_DEFAULT_ENV', '')
                if current_env == 'projet-is':
                    log_status("Environnement 'projet-is' actif", "OK")
                else:
                    log_status(f"Environnement actuel: {current_env or 'base'}", "INFO")
                return True
            else:
                log_status("Environnement 'projet-is' non trouve", "ERROR")
                log_status(f"Disponibles: {env_names}", "INFO")
                return False
        else:
            log_status("Impossible de lister les environnements", "ERROR")
            return False
    except Exception as e:
        log_status(f"Erreur test conda: {e}", "ERROR")
        return False

def test_dotenv():
    """Test variables .env"""
    log_status("Test 3: Variables .env")
    
    # Variables critiques
    required_vars = ['OPENAI_API_KEY', 'OPENAI_CHAT_MODEL_ID', 'GLOBAL_LLM_SERVICE']
    optional_vars = ['OPENAI_BASE_URL', 'JAVA_HOME', 'TEXT_CONFIG_PASSPHRASE']
    
    env_file = project_root / '.env'
    if not env_file.exists():
        log_status("Fichier .env non trouve", "ERROR")
        return False
    
    log_status(f"Fichier .env trouve: {env_file}", "OK")
    
    missing_required = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_required.append(var)
            log_status(f"Variable requise manquante: {var}", "ERROR")
        else:
            if 'KEY' in var:
                display = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display = value
            log_status(f"{var}={display}", "OK")
    
    for var in optional_vars:
        value = os.environ.get(var)
        if not value:
            log_status(f"Variable optionnelle manquante: {var}", "WARN")
        else:
            if 'KEY' in var:
                display = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display = value
            log_status(f"{var}={display}", "OK")
    
    return len(missing_required) == 0

def test_gpt4o():
    """Test configuration gpt-4o-mini"""
    log_status("Test 4: Configuration gpt-4o-mini")
    
    api_key = os.environ.get('OPENAI_API_KEY')
    model_id = os.environ.get('OPENAI_CHAT_MODEL_ID')
    base_url = os.environ.get('OPENAI_BASE_URL')
    
    if not api_key:
        log_status("OPENAI_API_KEY manquante", "ERROR")
        return False
    
    if model_id != 'gpt-4o-mini':
        log_status(f"Modele configure: {model_id} (attendu: gpt-4o-mini)", "WARN")
    else:
        log_status("Modele gpt-4o-mini configure", "OK")
    
    if base_url:
        log_status(f"Base URL: {base_url}", "OK")
    else:
        log_status("API OpenAI standard", "INFO")
    
    return True

def test_java():
    """Test Java JDK17"""
    log_status("Test 5: Java JDK17")
    
    java_home = os.environ.get('JAVA_HOME')
    if not java_home:
        log_status("JAVA_HOME non defini", "WARN")
        return True  # Non critique
    
    java_home_path = Path(java_home)
    if not java_home_path.is_absolute():
        java_home_path = (project_root / java_home_path).resolve()
    
    if not java_home_path.exists():
        log_status(f"JAVA_HOME inexistant: {java_home_path}", "ERROR")
        return False
    
    log_status(f"JAVA_HOME: {java_home_path}", "OK")
    
    # Tester java executable
    java_exe = java_home_path / "bin" / "java.exe"
    java_bin = java_home_path / "bin" / "java"
    
    java_cmd = None
    if java_exe.exists():
        java_cmd = str(java_exe)
    elif java_bin.exists():
        java_cmd = str(java_bin)
    
    if java_cmd:
        try:
            result = subprocess.run([java_cmd, '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                log_status("Java executable trouve", "OK")
                version_output = result.stderr
                if "17." in version_output:
                    log_status("Java JDK17 confirme", "OK")
                else:
                    log_status("Version Java differente de JDK17", "WARN")
            else:
                log_status("Java non executable", "WARN")
        except Exception as e:
            log_status(f"Erreur test Java: {e}", "WARN")
    else:
        log_status("Executable Java non trouve", "WARN")
    
    return True

def test_directories():
    """Test répertoires de travail"""
    log_status("Test 6: Repertoires de travail")
    
    required_dirs = ['.temp', 'logs', 'output']
    
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            log_status(f"Repertoire cree: {dir_name}", "OK")
        else:
            log_status(f"Repertoire existant: {dir_name}", "OK")
    
    return True

def main():
    """Point d'entrée principal"""
    log_status("DEBUT VALIDATION ENVIRONNEMENT")
    log_status("=" * 50)
    
    tests = [
        ("Import auto_env", test_auto_env),
        ("Conda environment", test_conda),
        ("Variables .env", test_dotenv),
        ("Configuration gpt-4o-mini", test_gpt4o),
        ("Java JDK17", test_java),
        ("Repertoires", test_directories)
    ]
    
    passed = 0
    total = len(tests)
    errors = []
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                errors.append(test_name)
        except Exception as e:
            log_status(f"Erreur dans {test_name}: {e}", "ERROR")
            errors.append(test_name)
        log_status("-" * 40)
    
    # Résumé
    log_status("RESUME VALIDATION")
    log_status("=" * 50)
    log_status(f"Tests reussis: {passed}/{total}")
    
    if errors:
        log_status(f"Tests echoues: {errors}", "ERROR")
    
    # One-liner
    log_status("ONE-LINER D'ACTIVATION:")
    log_status("import scripts.core.auto_env", "OK")
    
    success = len(errors) == 0
    log_status(f"VALIDATION {'REUSSIE' if success else 'ECHOUEE'}")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)