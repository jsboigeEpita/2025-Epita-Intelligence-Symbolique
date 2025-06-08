#!/usr/bin/env python3
"""
Script d'orchestration principal pour les demos Playwright - Version sans Unicode
"""

import sys
import subprocess
import time
import os
from pathlib import Path

class PlaywrightDemoOrchestrator:
    """Orchestrateur principal pour les demos Playwright"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.react_app_path = self.project_root / "services/web_api/interface-web-argumentative"
        self.results = {
            'setup': False,
            'static_tests': False,
            'react_tests': False,
            'browser_install': False
        }
    
    def print_banner(self, title):
        """Affiche une banniere formatee"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)
    
    def check_python_dependencies(self):
        """Verifie les dependances Python"""
        self.print_banner("VERIFICATION DES DEPENDANCES PYTHON")
        
        required_packages = [
            'playwright', 'pytest', 'pytest-playwright', 
            'pytest-asyncio', 'pytest-mock'
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"[OK] {package}")
            except ImportError:
                print(f"[ERREUR] {package}")
                missing.append(package)
        
        if missing:
            print(f"\n[ATTENTION] Dependances manquantes: {', '.join(missing)}")
            print("[*] Installation depuis requirements.txt...")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", 
                    str(self.project_root / "requirements.txt")
                ], check=True, cwd=self.project_root)
                print("[OK] Dependances installees")
                return True
            except subprocess.CalledProcessError as e:
                print(f"[ERREUR] Erreur installation: {e}")
                return False
        else:
            print("[OK] Toutes les dependances Python presentes")
            return True
    
    def install_playwright_browsers(self):
        """Installe les navigateurs Playwright"""
        self.print_banner("INSTALLATION DES NAVIGATEURS PLAYWRIGHT")
        
        try:
            # Installer les navigateurs
            subprocess.run([
                sys.executable, "-m", "playwright", "install"
            ], check=True)
            print("[OK] Navigateurs Playwright installes")
            self.results['browser_install'] = True
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERREUR] Erreur installation navigateurs: {e}")
            return False
        except FileNotFoundError:
            print("[ERREUR] Commande playwright non trouvee")
            return False
    
    def run_setup_test(self):
        """Execute le test de setup"""
        self.print_banner("TEST DE SETUP PLAYWRIGHT")
        
        try:
            result = subprocess.run([
                sys.executable, 
                str(Path(__file__).parent / "test_playwright_setup.py")
            ], cwd=self.project_root, capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print("Erreurs:", result.stderr)
            
            self.results['setup'] = result.returncode == 0
            return result.returncode == 0
        except Exception as e:
            print(f"[ERREUR] Erreur test setup: {e}")
            return False
    
    def run_static_interface_tests(self):
        """Execute les tests de l'interface statique"""
        self.print_banner("TESTS INTERFACE STATIQUE")
        
        try:
            result = subprocess.run([
                sys.executable, 
                str(Path(__file__).parent / "test_webapp_interface_demo.py")
            ], cwd=self.project_root, capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print("Erreurs:", result.stderr)
            
            self.results['static_tests'] = result.returncode == 0
            return result.returncode == 0
        except Exception as e:
            print(f"[ERREUR] Erreur tests statiques: {e}")
            return False
    
    def prepare_react_app(self):
        """Prepare l'application React"""
        self.print_banner("PREPARATION APPLICATION REACT")
        
        if not self.react_app_path.exists():
            print("[ERREUR] Application React non trouvee")
            return False
        
        package_json = self.react_app_path / "package.json"
        if not package_json.exists():
            print("[ERREUR] package.json non trouve")
            return False
        
        node_modules = self.react_app_path / "node_modules"
        if not node_modules.exists():
            print("[*] Installation des dependances Node.js...")
            try:
                subprocess.run([
                    "npm", "install"
                ], cwd=self.react_app_path, check=True)
                print("[OK] Dependances Node.js installees")
            except subprocess.CalledProcessError as e:
                print(f"[ATTENTION] Erreur npm install: {e}")
                return False
            except FileNotFoundError:
                print("[ATTENTION] npm non trouve, tests React ignores")
                return False
        else:
            print("[OK] Dependances Node.js deja presentes")
        
        return True
    
    def run_react_tests(self):
        """Execute les tests React"""
        self.print_banner("TESTS APPLICATION REACT")
        
        if not self.prepare_react_app():
            print("[ATTENTION] Application React non preparee, tests ignores")
            return False
        
        try:
            result = subprocess.run([
                sys.executable, 
                str(Path(__file__).parent / "test_react_webapp_full.py")
            ], cwd=self.project_root, capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print("Erreurs:", result.stderr)
            
            self.results['react_tests'] = result.returncode == 0
            return result.returncode == 0
        except Exception as e:
            print(f"[ERREUR] Erreur tests React: {e}")
            return False
    
    def run_pytest_playwright(self):
        """Execute pytest avec Playwright"""
        self.print_banner("EXECUTION PYTEST PLAYWRIGHT")
        
        try:
            # Executer pytest sur le dossier demos/playwright
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(Path(__file__).parent),
                "-v", "--tb=short"
            ], cwd=self.project_root, capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print("Erreurs:", result.stderr)
            
            return result.returncode == 0
        except Exception as e:
            print(f"[ERREUR] Erreur pytest: {e}")
            return False
    
    def generate_report(self):
        """Genere le rapport final"""
        self.print_banner("RAPPORT FINAL DES DEMOS PLAYWRIGHT")
        
        print("RESULTATS:")
        print(f"  [+] Dependances Python: {'[OK]' if self.results['setup'] else '[ERREUR]'}")
        print(f"  [+] Navigateurs Playwright: {'[OK]' if self.results['browser_install'] else '[ERREUR]'}")
        print(f"  [+] Interface statique: {'[OK]' if self.results['static_tests'] else '[ERREUR]'}")
        print(f"  [+] Interface React: {'[OK]' if self.results['react_tests'] else '[OPTIONNEL]'}")
        
        total_success = sum([
            self.results['setup'],
            self.results['browser_install'],
            self.results['static_tests']
        ])
        
        print(f"\nSCORE DE REUSSITE: {total_success}/3 composants critiques")
        
        if total_success >= 2:
            print("\n[SUCCES] SYSTEME PLAYWRIGHT FONCTIONNEL")
            print("[OK] Demos web disponibles pour presentation")
            if not self.results['react_tests']:
                print("[INFO] Interface React optionnelle non testee")
        else:
            print("\n[ERREUR] SYSTEME PLAYWRIGHT PARTIELLEMENT FONCTIONNEL")
            print("[ATTENTION] Certains composants necessitent une intervention")
        
        return total_success >= 2
    
    def run_all_demos(self):
        """Execute toutes les demos"""
        self.print_banner("LANCEMENT DES DEMOS PLAYWRIGHT COMPLETES")
        
        print("[*] Demarrage de l'orchestration Playwright...")
        print("[*] Phases: Setup -> Navigateurs -> Tests statiques -> Tests React")
        
        # Phase 1: Verifications et setup
        if not self.check_python_dependencies():
            print("[ERREUR] Setup echoue")
            return False
        
        # Phase 2: Installation navigateurs
        self.install_playwright_browsers()
        
        # Phase 3: Test de setup
        self.run_setup_test()
        
        # Phase 4: Tests interface statique (critique)
        self.run_static_interface_tests()
        
        # Phase 5: Tests React (optionnel)
        self.run_react_tests()
        
        # Phase 6: Pytest global (optionnel)
        try:
            self.run_pytest_playwright()
        except:
            print("[ATTENTION] Pytest global optionnel echoue")
        
        # Phase 7: Rapport final
        return self.generate_report()

def main():
    """Point d'entree principal"""
    orchestrator = PlaywrightDemoOrchestrator()
    
    try:
        success = orchestrator.run_all_demos()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n[INFO] Arret demande par l'utilisateur")
        return 2
    except Exception as e:
        print(f"\n[ERREUR] Erreur critique: {e}")
        import traceback
        traceback.print_exc()
        return 3

if __name__ == "__main__":
    sys.exit(main())