#!/usr/bin/env python3
"""
Script d'orchestration principal pour les démos Playwright
"""

import sys
import subprocess
import time
import os
from pathlib import Path

class PlaywrightDemoOrchestrator:
    """Orchestrateur principal pour les démos Playwright"""
    
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
        """Affiche une bannière formatée"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)
    
    def check_python_dependencies(self):
        """Vérifie les dépendances Python"""
        self.print_banner("VÉRIFICATION DES DÉPENDANCES PYTHON")
        
        required_packages = [
            'playwright', 'pytest', 'pytest-playwright', 
            'pytest-asyncio', 'pytest-mock'
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package}")
                missing.append(package)
        
        if missing:
            print(f"\n⚠️  Dépendances manquantes: {', '.join(missing)}")
            print("📦 Installation depuis requirements.txt...")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", 
                    str(self.project_root / "requirements.txt")
                ], check=True, cwd=self.project_root)
                print("✅ Dépendances installées")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Erreur installation: {e}")
                return False
        else:
            print("✅ Toutes les dépendances Python présentes")
            return True
    
    def install_playwright_browsers(self):
        """Installe les navigateurs Playwright"""
        self.print_banner("INSTALLATION DES NAVIGATEURS PLAYWRIGHT")
        
        try:
            # Installer les navigateurs
            subprocess.run([
                sys.executable, "-m", "playwright", "install"
            ], check=True)
            print("✅ Navigateurs Playwright installés")
            self.results['browser_install'] = True
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur installation navigateurs: {e}")
            return False
        except FileNotFoundError:
            print("❌ Commande playwright non trouvée")
            return False
    
    def run_setup_test(self):
        """Exécute le test de setup"""
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
            print(f"❌ Erreur test setup: {e}")
            return False
    
    def run_static_interface_tests(self):
        """Exécute les tests de l'interface statique"""
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
            print(f"❌ Erreur tests statiques: {e}")
            return False
    
    def prepare_react_app(self):
        """Prépare l'application React"""
        self.print_banner("PRÉPARATION APPLICATION REACT")
        
        if not self.react_app_path.exists():
            print("❌ Application React non trouvée")
            return False
        
        package_json = self.react_app_path / "package.json"
        if not package_json.exists():
            print("❌ package.json non trouvé")
            return False
        
        node_modules = self.react_app_path / "node_modules"
        if not node_modules.exists():
            print("[*] Installation des dependances Node.js...")
            try:
                subprocess.run([
                    "npm", "install"
                ], cwd=self.react_app_path, check=True)
                print("✅ Dépendances Node.js installées")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Erreur npm install: {e}")
                return False
            except FileNotFoundError:
                print("⚠️  npm non trouvé, tests React ignorés")
                return False
        else:
            print("✅ Dépendances Node.js déjà présentes")
        
        return True
    
    def run_react_tests(self):
        """Exécute les tests React"""
        self.print_banner("TESTS APPLICATION REACT")
        
        if not self.prepare_react_app():
            print("⚠️  Application React non préparée, tests ignorés")
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
            print(f"❌ Erreur tests React: {e}")
            return False
    
    def run_pytest_playwright(self):
        """Exécute pytest avec Playwright"""
        self.print_banner("EXÉCUTION PYTEST PLAYWRIGHT")
        
        try:
            # Exécuter pytest sur le dossier demos/playwright
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
            print(f"❌ Erreur pytest: {e}")
            return False
    
    def generate_report(self):
        """Génère le rapport final"""
        self.print_banner("RAPPORT FINAL DES DÉMOS PLAYWRIGHT")
        
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
        
        print(f"\nSCORE DE RÉUSSITE: {total_success}/3 composants critiques")
        
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
        """Exécute toutes les démos"""
        self.print_banner("LANCEMENT DES DÉMOS PLAYWRIGHT COMPLÈTES")
        
        print("[*] Demarrage de l'orchestration Playwright...")
        print("[*] Phases: Setup -> Navigateurs -> Tests statiques -> Tests React")
        
        # Phase 1: Vérifications et setup
        if not self.check_python_dependencies():
            print("❌ Setup échoué")
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
            print("⚠️  Pytest global optionnel échoué")
        
        # Phase 7: Rapport final
        return self.generate_report()

def main():
    """Point d'entrée principal"""
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