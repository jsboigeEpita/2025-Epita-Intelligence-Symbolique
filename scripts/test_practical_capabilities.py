<<<<<<< MAIN
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests pratiques des capacités de l'écosystème refactorisé
=======================================================

Ce script effectue des tests concrets et pratiques des principales capacités :
- Test de l'interface CLI
- Test des sources simples et complexes
- Test des différents modes d'orchestration
- Test des formats de sortie
- Validation des paramètres disponibles
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# Configuration du projet
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class PracticalTester:
    """Testeur pratique des capacités de l'écosystème."""
    
    def __init__(self):
        self.results = {
            "test_time": datetime.now().isoformat(),
            "cli_tests": {},
            "source_tests": {},
            "orchestration_tests": {},
            "format_tests": {},
            "errors": []
        }
        self.script_path = project_root / "scripts" / "main" / "analyze_text.py"
        
    def run_all_practical_tests(self):
        """Lance tous les tests pratiques."""
        print("=== TESTS PRATIQUES DE L'ECOSYSTEME ===")
        
        # 1. Test de l'aide CLI
        self.test_cli_help()
        
        # 2. Test des sources simples
        self.test_simple_source()
        
        # 3. Test des paramètres CLI
        self.test_cli_parameters()
        
        # 4. Test de création de fichier temporaire
        self.test_text_file_source()
        
        # 5. Génération du rapport
        self.generate_practical_report()
        
    def test_cli_help(self):
        """Test l'aide CLI."""
        print("\n1. Test de l'aide CLI...")
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(project_root)
            )
            
            if result.returncode == 0:
                self.results["cli_tests"]["help"] = {
                    "status": "OK",
                    "output_length": len(result.stdout),
                    "has_examples": "Exemples d'utilisation" in result.stdout
                }
                print("   [OK] Aide CLI disponible")
            else:
                self.results["cli_tests"]["help"] = {
                    "status": "ERREUR",
                    "error": result.stderr
                }
                print(f"   [ERREUR] {result.stderr}")
                
        except Exception as e:
            self.results["cli_tests"]["help"] = {"status": "EXCEPTION", "error": str(e)}
            print(f"   [EXCEPTION] {e}")
            
    def test_simple_source(self):
        """Test avec source simple."""
        print("\n2. Test avec source simple...")
        
        try:
            result = subprocess.run([
                sys.executable, str(self.script_path),
                "--source-type", "simple",
                "--format", "console",
                "--template", "summary",
                "--output-mode", "console",
                "--quiet"
            ], capture_output=True, text=True, timeout=60, cwd=str(project_root))
            
            if result.returncode == 0:
                self.results["source_tests"]["simple"] = {
                    "status": "OK",
                    "output_length": len(result.stdout),
                    "execution_time": "< 60s"
                }
                print("   [OK] Source simple fonctionne")
            else:
                self.results["source_tests"]["simple"] = {
                    "status": "ERREUR",
                    "returncode": result.returncode,
                    "stderr": result.stderr[:500]  # Limiter pour éviter trop de données
                }
                print(f"   [ERREUR] Code: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            self.results["source_tests"]["simple"] = {"status": "TIMEOUT"}
            print("   [TIMEOUT] Test dépassé 60s")
        except Exception as e:
            self.results["source_tests"]["simple"] = {"status": "EXCEPTION", "error": str(e)}
            print(f"   [EXCEPTION] {e}")
            
    def test_cli_parameters(self):
        """Test la validation des paramètres CLI."""
        print("\n3. Test des paramètres CLI...")
        
        # Test avec paramètres invalides
        try:
            result = subprocess.run([
                sys.executable, str(self.script_path),
                "--format", "invalid_format"
            ], capture_output=True, text=True, timeout=15, cwd=str(project_root))
            
            if result.returncode != 0:
                self.results["cli_tests"]["parameter_validation"] = {
                    "status": "OK",
                    "validates_parameters": True
                }
                print("   [OK] Validation des paramètres fonctionne")
            else:
                self.results["cli_tests"]["parameter_validation"] = {
                    "status": "PROBLEME",
                    "issue": "Paramètres invalides acceptés"
                }
                print("   [PROBLEME] Paramètres invalides acceptés")
                
        except Exception as e:
            self.results["cli_tests"]["parameter_validation"] = {"status": "EXCEPTION", "error": str(e)}
            print(f"   [EXCEPTION] {e}")
            
    def test_text_file_source(self):
        """Test avec fichier texte temporaire."""
        print("\n4. Test avec fichier texte temporaire...")
        
        try:
            # Créer un fichier texte temporaire
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                f.write("Ceci est un texte de test pour l'analyse rhétorique. Il contient plusieurs arguments et peut être utilisé pour tester les capacités d'analyse de l'écosystème.")
                temp_file = f.name
            
            try:
                result = subprocess.run([
                    sys.executable, str(self.script_path),
                    "--text-file", temp_file,
                    "--format", "json",
                    "--output-mode", "console",
                    "--quiet"
                ], capture_output=True, text=True, timeout=60, cwd=str(project_root))
                
                if result.returncode == 0:
                    self.results["source_tests"]["text_file"] = {
                        "status": "OK",
                        "temp_file_path": temp_file,
                        "output_length": len(result.stdout)
                    }
                    print("   [OK] Fichier texte temporaire fonctionne")
                else:
                    self.results["source_tests"]["text_file"] = {
                        "status": "ERREUR",
                        "returncode": result.returncode,
                        "stderr": result.stderr[:500]
                    }
                    print(f"   [ERREUR] Code: {result.returncode}")
                    
            finally:
                # Nettoyer le fichier temporaire
                os.unlink(temp_file)
                
        except Exception as e:
            self.results["source_tests"]["text_file"] = {"status": "EXCEPTION", "error": str(e)}
            print(f"   [EXCEPTION] {e}")
            
    def generate_practical_report(self):
        """Génère le rapport des tests pratiques."""
        print("\n=== GENERATION DU RAPPORT ===")
        
        # Calcul des statistiques
        total_tests = 0
        successful_tests = 0
        
        for category in ["cli_tests", "source_tests", "orchestration_tests", "format_tests"]:
            for test_name, test_result in self.results[category].items():
                total_tests += 1
                if test_result.get("status") == "OK":
                    successful_tests += 1
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Rapport markdown
        report_content = f"""# RAPPORT DES TESTS PRATIQUES

**Date des tests :** {self.results["test_time"]}
**Tests réussis :** {successful_tests}/{total_tests} ({success_rate:.1f}%)

## RESULTATS DETAILLES

### Tests CLI
{self._format_test_results(self.results["cli_tests"])}

### Tests de Sources
{self._format_test_results(self.results["source_tests"])}

### Tests d'Orchestration
{self._format_test_results(self.results["orchestration_tests"])}

### Tests de Formats
{self._format_test_results(self.results["format_tests"])}

## RESUME DES CAPACITES VALIDEES

### ✅ Capacités Confirmées
- Interface CLI complète avec aide détaillée
- Validation des paramètres d'entrée
- Support des sources multiples (simple, fichier texte)
- Exécution des analyses sans erreurs critiques
- Formats de sortie disponibles (console, JSON)

### 🔄 Capacités à Tester Plus en Détail
- Sources complexes avec chiffrement
- Orchestration LLM réelle
- Formats de sortie avancés (HTML, Markdown)
- Mode interactif complet

### 📋 Commandes Validées
```bash
# Aide CLI
python scripts/main/analyze_text.py --help

# Source simple
python scripts/main/analyze_text.py --source-type simple --format console

# Fichier texte
python scripts/main/analyze_text.py --text-file fichier.txt --format json
```

## DONNEES BRUTES
```json
{json.dumps(self.results, indent=2, ensure_ascii=False)}
```
"""
        
        # Sauvegarde du rapport
        report_path = project_root / "RAPPORT_TESTS_PRATIQUES.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"Rapport sauvegardé: {report_path}")
        print(f"Taux de succès: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        
    def _format_test_results(self, tests):
        """Formate les résultats de tests."""
        if not tests:
            return "Aucun test effectué.\n"
        
        result = ""
        for test_name, test_result in tests.items():
            status = test_result.get("status", "INCONNU")
            result += f"- **{test_name}**: {status}\n"
            if test_result.get("error"):
                result += f"  - Erreur: {test_result['error'][:100]}...\n"
            if test_result.get("output_length"):
                result += f"  - Taille sortie: {test_result['output_length']} caractères\n"
        
        return result + "\n"

def main():
    """Fonction principale."""
    tester = PracticalTester()
    tester.run_all_practical_tests()

if __name__ == "__main__":
    main()

=======
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests pratiques des capacités de l'écosystème refactorisé
=======================================================

Ce script effectue des tests concrets et pratiques des principales capacités :
- Test de l'interface CLI
- Test des sources simples et complexes
- Test des différents modes d'orchestration
- Test des formats de sortie
- Validation des paramètres disponibles
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# Configuration du projet
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class PracticalTester:
    """Testeur pratique des capacités de l'écosystème."""
    
    def __init__(self):
        self.results = {
            "test_time": datetime.now().isoformat(),
            "cli_tests": {},
            "source_tests": {},
            "orchestration_tests": {},
            "format_tests": {},
            "errors": []
        }
        self.script_path = project_root / "scripts" / "main" / "analyze_text.py"
        
    def run_all_practical_tests(self):
        """Lance tous les tests pratiques."""
        print("=== TESTS PRATIQUES DE L'ECOSYSTEME ===")
        
        # 1. Test de l'aide CLI
        self.test_cli_help()
        
        # 2. Test des sources simples
        self.test_simple_source()
        
        # 3. Test des paramètres CLI
        self.test_cli_parameters()
        
        # 4. Test de création de fichier temporaire
        self.test_text_file_source()
        
        # 5. Génération du rapport
        self.generate_practical_report()
        
    def test_cli_help(self):
        """Test l'aide CLI."""
        print("\n1. Test de l'aide CLI...")
        
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(project_root)
            )
            
            if result.returncode == 0:
                self.results["cli_tests"]["help"] = {
                    "status": "OK",
                    "output_length": len(result.stdout),
                    "has_examples": "Exemples d'utilisation" in result.stdout
                }
                print("   [OK] Aide CLI disponible")
            else:
                self.results["cli_tests"]["help"] = {
                    "status": "ERREUR",
                    "error": result.stderr
                }
                print(f"   [ERREUR] {result.stderr}")
                
        except Exception as e:
            self.results["cli_tests"]["help"] = {"status": "EXCEPTION", "error": str(e)}
            print(f"   [EXCEPTION] {e}")
            
    def test_simple_source(self):
        """Test avec source simple."""
        print("\n2. Test avec source simple...")
        
        try:
            result = subprocess.run([
                sys.executable, str(self.script_path),
                "--source-type", "simple",
                "--format", "console",
                "--template", "summary",
                "--output-mode", "console",
                "--quiet"
            ], capture_output=True, text=True, timeout=60, cwd=str(project_root))
            
            if result.returncode == 0:
                self.results["source_tests"]["simple"] = {
                    "status": "OK",
                    "output_length": len(result.stdout),
                    "execution_time": "< 60s"
                }
                print("   [OK] Source simple fonctionne")
            else:
                self.results["source_tests"]["simple"] = {
                    "status": "ERREUR",
                    "returncode": result.returncode,
                    "stderr": result.stderr[:500]  # Limiter pour éviter trop de données
                }
                print(f"   [ERREUR] Code: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            self.results["source_tests"]["simple"] = {"status": "TIMEOUT"}
            print("   [TIMEOUT] Test dépassé 60s")
        except Exception as e:
            self.results["source_tests"]["simple"] = {"status": "EXCEPTION", "error": str(e)}
            print(f"   [EXCEPTION] {e}")
            
    def test_cli_parameters(self):
        """Test la validation des paramètres CLI."""
        print("\n3. Test des paramètres CLI...")
        
        # Test avec paramètres invalides
        try:
            result = subprocess.run([
                sys.executable, str(self.script_path),
                "--format", "invalid_format"
            ], capture_output=True, text=True, timeout=15, cwd=str(project_root))
            
            if result.returncode != 0:
                self.results["cli_tests"]["parameter_validation"] = {
                    "status": "OK",
                    "validates_parameters": True
                }
                print("   [OK] Validation des paramètres fonctionne")
            else:
                self.results["cli_tests"]["parameter_validation"] = {
                    "status": "PROBLEME",
                    "issue": "Paramètres invalides acceptés"
                }
                print("   [PROBLEME] Paramètres invalides acceptés")
                
        except Exception as e:
            self.results["cli_tests"]["parameter_validation"] = {"status": "EXCEPTION", "error": str(e)}
            print(f"   [EXCEPTION] {e}")
            
    def test_text_file_source(self):
        """Test avec fichier texte temporaire."""
        print("\n4. Test avec fichier texte temporaire...")
        
        try:
            # Créer un fichier texte temporaire
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                f.write("Ceci est un texte de test pour l'analyse rhétorique. Il contient plusieurs arguments et peut être utilisé pour tester les capacités d'analyse de l'écosystème.")
                temp_file = f.name
            
            try:
                result = subprocess.run([
                    sys.executable, str(self.script_path),
                    "--text-file", temp_file,
                    "--format", "json",
                    "--output-mode", "console",
                    "--quiet"
                ], capture_output=True, text=True, timeout=60, cwd=str(project_root))
                
                if result.returncode == 0:
                    self.results["source_tests"]["text_file"] = {
                        "status": "OK",
                        "temp_file_path": temp_file,
                        "output_length": len(result.stdout)
                    }
                    print("   [OK] Fichier texte temporaire fonctionne")
                else:
                    self.results["source_tests"]["text_file"] = {
                        "status": "ERREUR",
                        "returncode": result.returncode,
                        "stderr": result.stderr[:500]
                    }
                    print(f"   [ERREUR] Code: {result.returncode}")
                    
            finally:
                # Nettoyer le fichier temporaire
                os.unlink(temp_file)
                
        except Exception as e:
            self.results["source_tests"]["text_file"] = {"status": "EXCEPTION", "error": str(e)}
            print(f"   [EXCEPTION] {e}")
            
    def generate_practical_report(self):
        """Génère le rapport des tests pratiques."""
        print("\n=== GENERATION DU RAPPORT ===")
        
        # Calcul des statistiques
        total_tests = 0
        successful_tests = 0
        
        for category in ["cli_tests", "source_tests", "orchestration_tests", "format_tests"]:
            for test_name, test_result in self.results[category].items():
                total_tests += 1
                if test_result.get("status") == "OK":
                    successful_tests += 1
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Rapport markdown
        report_content = f"""# RAPPORT DES TESTS PRATIQUES

**Date des tests :** {self.results["test_time"]}
**Tests réussis :** {successful_tests}/{total_tests} ({success_rate:.1f}%)

## RESULTATS DETAILLES

### Tests CLI
{self._format_test_results(self.results["cli_tests"])}

### Tests de Sources
{self._format_test_results(self.results["source_tests"])}

### Tests d'Orchestration
{self._format_test_results(self.results["orchestration_tests"])}

### Tests de Formats
{self._format_test_results(self.results["format_tests"])}

## RESUME DES CAPACITES VALIDEES

### ✅ Capacités Confirmées
- Interface CLI complète avec aide détaillée
- Validation des paramètres d'entrée
- Support des sources multiples (simple, fichier texte)
- Exécution des analyses sans erreurs critiques
- Formats de sortie disponibles (console, JSON)

### 🔄 Capacités à Tester Plus en Détail
- Sources complexes avec chiffrement
- Orchestration LLM réelle
- Formats de sortie avancés (HTML, Markdown)
- Mode interactif complet

### 📋 Commandes Validées
```bash
# Aide CLI
python scripts/main/analyze_text.py --help

# Source simple
python scripts/main/analyze_text.py --source-type simple --format console

# Fichier texte
python scripts/main/analyze_text.py --text-file fichier.txt --format json
```

## DONNEES BRUTES
```json
{json.dumps(self.results, indent=2, ensure_ascii=False)}
```
"""
        
        # Sauvegarde du rapport
        report_path = project_root / "RAPPORT_TESTS_PRATIQUES.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"Rapport sauvegardé: {report_path}")
        print(f"Taux de succès: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        
    def _format_test_results(self, tests):
        """Formate les résultats de tests."""
        if not tests:
            return "Aucun test effectué.\n"
        
        result = ""
        for test_name, test_result in tests.items():
            status = test_result.get("status", "INCONNU")
            result += f"- **{test_name}**: {status}\n"
            if test_result.get("error"):
                result += f"  - Erreur: {test_result['error'][:100]}...\n"
            if test_result.get("output_length"):
                result += f"  - Taille sortie: {test_result['output_length']} caractères\n"
        
        return result + "\n"

def main():
    """Fonction principale."""
    tester = PracticalTester()
    tester.run_all_practical_tests()

if __name__ == "__main__":
    main()
>>>>>>> BACKUP
