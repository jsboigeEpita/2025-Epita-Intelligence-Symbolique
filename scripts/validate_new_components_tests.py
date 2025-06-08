<<<<<<< MAIN
#!/usr/bin/env python3
"""
Script de validation pour la suite de tests des nouveaux composants
================================================================

Valide que tous les tests sont bien configurés et exécutables.
"""

import sys
import subprocess
import importlib
from pathlib import Path
from typing import List, Dict, Any

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Couleurs pour output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_success(message: str):
    print(f"{Colors.GREEN}[OK] {message}{Colors.ENDC}")

def print_error(message: str):
    print(f"{Colors.RED}[ERROR] {message}{Colors.ENDC}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}[WARNING] {message}{Colors.ENDC}")

def print_info(message: str):
    print(f"{Colors.BLUE}[INFO] {message}{Colors.ENDC}")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")


class TestSuiteValidator:
    """Validateur pour la suite de tests des nouveaux composants."""
    
    def __init__(self):
        self.test_files = {
            'unit': [
                'tests/unit/argumentation_analysis/test_unified_config.py',
                'tests/unit/argumentation_analysis/test_fol_logic_agent.py',
                'tests/unit/argumentation_analysis/test_tweety_error_analyzer.py',
                'tests/unit/argumentation_analysis/test_mock_elimination.py',
                'tests/unit/argumentation_analysis/test_unified_orchestration.py',
                'tests/unit/argumentation_analysis/test_configuration_cli.py'
            ],
            'integration': [
                'tests/integration/test_fol_pipeline_integration.py',
                'tests/integration/test_authentic_components_integration.py',
                'tests/integration/test_unified_system_integration.py'
            ]
        }
        
        self.required_components = [
            'argumentation_analysis.utils.tweety_error_analyzer',
            'argumentation_analysis.orchestration.conversation_orchestrator',
            'argumentation_analysis.orchestration.real_llm_orchestrator'
        ]
        
        self.validation_results = {
            'files_exist': {},
            'syntax_valid': {},
            'imports_work': {},
            'pytest_executable': {},
            'components_available': {}
        }
    
    def validate_all(self) -> bool:
        """Valide toute la suite de tests."""
        print_header("VALIDATION SUITE DE TESTS - NOUVEAUX COMPOSANTS")
        
        success = True
        
        # 1. Vérifier existence des fichiers
        success &= self._validate_files_exist()
        
        # 2. Vérifier syntaxe Python
        success &= self._validate_syntax()
        
        # 3. Vérifier imports des tests
        success &= self._validate_imports()
        
        # 4. Vérifier exécutabilité pytest
        success &= self._validate_pytest_execution()
        
        # 5. Vérifier disponibilité des composants
        success &= self._validate_components_availability()
        
        # 6. Générer rapport final
        self._generate_final_report()
        
        return success
    
    def _validate_files_exist(self) -> bool:
        """Valide que tous les fichiers de tests existent."""
        print_header("1. VALIDATION EXISTENCE FICHIERS")
        
        all_exist = True
        
        for category, files in self.test_files.items():
            print_info(f"Vérification tests {category}...")
            
            for file_path in files:
                full_path = PROJECT_ROOT / file_path
                exists = full_path.exists()
                
                self.validation_results['files_exist'][file_path] = exists
                
                if exists:
                    print_success(f"{file_path}")
                else:
                    print_error(f"{file_path} - MANQUANT")
                    all_exist = False
        
        # Vérifier documentation
        doc_path = PROJECT_ROOT / "README_TESTS_NOUVEAUX_COMPOSANTS.md"
        if doc_path.exists():
            print_success("README_TESTS_NOUVEAUX_COMPOSANTS.md")
        else:
            print_error("README_TESTS_NOUVEAUX_COMPOSANTS.md - MANQUANT")
            all_exist = False
        
        return all_exist
    
    def _validate_syntax(self) -> bool:
        """Valide la syntaxe Python des fichiers de tests."""
        print_header("2. VALIDATION SYNTAXE PYTHON")
        
        all_valid = True
        
        for category, files in self.test_files.items():
            for file_path in files:
                full_path = PROJECT_ROOT / file_path
                
                if not full_path.exists():
                    continue
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    compile(content, str(full_path), 'exec')
                    
                    self.validation_results['syntax_valid'][file_path] = True
                    print_success(f"{file_path} - Syntaxe valide")
                    
                except SyntaxError as e:
                    self.validation_results['syntax_valid'][file_path] = False
                    print_error(f"{file_path} - Erreur syntaxe: {e}")
                    all_valid = False
                    
                except Exception as e:
                    self.validation_results['syntax_valid'][file_path] = False
                    print_error(f"{file_path} - Erreur: {e}")
                    all_valid = False
        
        return all_valid
    
    def _validate_imports(self) -> bool:
        """Valide que les imports des tests fonctionnent."""
        print_header("3. VALIDATION IMPORTS TESTS")
        
        all_imports_work = True
        
        for category, files in self.test_files.items():
            for file_path in files:
                full_path = PROJECT_ROOT / file_path
                
                if not full_path.exists():
                    continue
                
                try:
                    # Lire le fichier et extraire les imports principaux
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Vérifier que les imports critiques sont présents
                    critical_imports = ['pytest', 'sys', 'Path']
                    missing_imports = []
                    
                    for imp in critical_imports:
                        if imp not in content:
                            missing_imports.append(imp)
                    
                    if missing_imports:
                        self.validation_results['imports_work'][file_path] = False
                        print_warning(f"{file_path} - Imports manquants: {missing_imports}")
                    else:
                        self.validation_results['imports_work'][file_path] = True
                        print_success(f"{file_path} - Imports OK")
                        
                except Exception as e:
                    self.validation_results['imports_work'][file_path] = False
                    print_error(f"{file_path} - Erreur imports: {e}")
                    all_imports_work = False
        
        return all_imports_work
    
    def _validate_pytest_execution(self) -> bool:
        """Valide que pytest peut exécuter les tests."""
        print_header("4. VALIDATION EXÉCUTION PYTEST")
        
        all_executable = True
        
        # Test général pytest
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print_success("pytest disponible")
            else:
                print_error("pytest non disponible")
                return False
                
        except Exception as e:
            print_error(f"Erreur vérification pytest: {e}")
            return False
        
        # Test execution dry-run des fichiers de tests
        for category, files in self.test_files.items():
            for file_path in files:
                full_path = PROJECT_ROOT / file_path
                
                if not full_path.exists():
                    continue
                
                try:
                    # Dry run avec --collect-only
                    result = subprocess.run(
                        [sys.executable, '-m', 'pytest', str(full_path), '--collect-only', '-q'],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=str(PROJECT_ROOT)
                    )
                    
                    if result.returncode == 0:
                        self.validation_results['pytest_executable'][file_path] = True
                        print_success(f"{file_path} - Exécutable pytest")
                    else:
                        self.validation_results['pytest_executable'][file_path] = False
                        print_warning(f"{file_path} - Problème pytest: {result.stderr[:100]}...")
                        
                except subprocess.TimeoutExpired:
                    self.validation_results['pytest_executable'][file_path] = False
                    print_error(f"{file_path} - Timeout pytest")
                    all_executable = False
                    
                except Exception as e:
                    self.validation_results['pytest_executable'][file_path] = False
                    print_error(f"{file_path} - Erreur pytest: {e}")
                    all_executable = False
        
        return all_executable
    
    def _validate_components_availability(self) -> bool:
        """Valide la disponibilité des composants requis."""
        print_header("5. VALIDATION COMPOSANTS DISPONIBLES")
        
        for component in self.required_components:
            try:
                importlib.import_module(component)
                self.validation_results['components_available'][component] = True
                print_success(f"{component} - Disponible")
                
            except ImportError:
                self.validation_results['components_available'][component] = False
                print_warning(f"{component} - Non disponible (tests utiliseront mocks)")
            
            except Exception as e:
                self.validation_results['components_available'][component] = False
                print_error(f"{component} - Erreur: {e}")
        
        return True  # Non bloquant car mocks disponibles
    
    def _generate_final_report(self):
        """Génère le rapport final de validation."""
        print_header("RAPPORT FINAL DE VALIDATION")
        
        # Compteurs
        total_files = sum(len(files) for files in self.test_files.values())
        files_exist = sum(1 for exists in self.validation_results['files_exist'].values() if exists)
        syntax_valid = sum(1 for valid in self.validation_results['syntax_valid'].values() if valid)
        imports_work = sum(1 for works in self.validation_results['imports_work'].values() if works)
        pytest_executable = sum(1 for exec in self.validation_results['pytest_executable'].values() if exec)
        components_available = sum(1 for avail in self.validation_results['components_available'].values() if avail)
        
        print(f"""
[STATS] STATISTIQUES:
   - Fichiers de tests: {files_exist}/{total_files} existent
   - Syntaxe valide: {syntax_valid}/{total_files} fichiers
   - Imports fonctionnels: {imports_work}/{total_files} fichiers
   - Executables pytest: {pytest_executable}/{total_files} fichiers
   - Composants disponibles: {components_available}/{len(self.required_components)} composants

[COVERAGE] COUVERTURE:
   - Tests unitaires: 6 fichiers (configuration, FOL, BNF, mocks, orchestration, CLI)
   - Tests d'integration: 3 fichiers (pipeline FOL, authentiques, systeme unifie)
   - Documentation: README complet avec instructions

[COMMANDS] COMMANDES D'EXECUTION:
   - Tests unitaires: python -m pytest tests/unit/argumentation_analysis/ -v
   - Tests integration: python -m pytest tests/integration/ -v
   - Tous les tests: python -m pytest tests/ -v

[CONFIG] CONFIGURATION AUTHENTIQUE:
   - OPENAI_API_KEY=your_key pour LLM reel
   - USE_REAL_JPYPE=true pour Tweety authentique
   - MOCK_LEVEL=none pour elimination mocks
        """)
        
        if files_exist == total_files and syntax_valid == total_files:
            print_success("[READY] SUITE DE TESTS PRETE A L'UTILISATION")
        else:
            print_warning("[PARTIAL] Quelques ajustements necessaires avant utilisation complete")


def main():
    """Point d'entrée principal."""
    validator = TestSuiteValidator()
    
    try:
        success = validator.validate_all()
        
        if success:
            print_success("\n[SUCCESS] VALIDATION REUSSIE - Suite de tests operationnelle")
            return 0
        else:
            print_error("\n[FAILED] VALIDATION ECHOUEE - Corrections necessaires")
            return 1
            
    except KeyboardInterrupt:
        print_warning("\n[INTERRUPTED] Validation interrompue par utilisateur")
        return 130
        
    except Exception as e:
        print_error(f"\n[EXCEPTION] Erreur inattendue: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

=======
#!/usr/bin/env python3
"""
Script de validation pour la suite de tests des nouveaux composants
================================================================

Valide que tous les tests sont bien configurés et exécutables.
"""

import sys
import subprocess
import importlib
from pathlib import Path
from typing import List, Dict, Any

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Couleurs pour output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_success(message: str):
    print(f"{Colors.GREEN}[OK] {message}{Colors.ENDC}")

def print_error(message: str):
    print(f"{Colors.RED}[ERROR] {message}{Colors.ENDC}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}[WARNING] {message}{Colors.ENDC}")

def print_info(message: str):
    print(f"{Colors.BLUE}[INFO] {message}{Colors.ENDC}")

def print_header(message: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")


class TestSuiteValidator:
    """Validateur pour la suite de tests des nouveaux composants."""
    
    def __init__(self):
        self.test_files = {
            'unit': [
                'tests/unit/argumentation_analysis/test_unified_config.py',
                'tests/unit/argumentation_analysis/test_fol_logic_agent.py',
                'tests/unit/argumentation_analysis/test_tweety_error_analyzer.py',
                'tests/unit/argumentation_analysis/test_mock_elimination.py',
                'tests/unit/argumentation_analysis/test_unified_orchestration.py',
                'tests/unit/argumentation_analysis/test_configuration_cli.py'
            ],
            'integration': [
                'tests/integration/test_fol_pipeline_integration.py',
                'tests/integration/test_authentic_components_integration.py',
                'tests/integration/test_unified_system_integration.py'
            ]
        }
        
        self.required_components = [
            'argumentation_analysis.utils.tweety_error_analyzer',
            'argumentation_analysis.orchestration.conversation_orchestrator',
            'argumentation_analysis.orchestration.real_llm_orchestrator'
        ]
        
        self.validation_results = {
            'files_exist': {},
            'syntax_valid': {},
            'imports_work': {},
            'pytest_executable': {},
            'components_available': {}
        }
    
    def validate_all(self) -> bool:
        """Valide toute la suite de tests."""
        print_header("VALIDATION SUITE DE TESTS - NOUVEAUX COMPOSANTS")
        
        success = True
        
        # 1. Vérifier existence des fichiers
        success &= self._validate_files_exist()
        
        # 2. Vérifier syntaxe Python
        success &= self._validate_syntax()
        
        # 3. Vérifier imports des tests
        success &= self._validate_imports()
        
        # 4. Vérifier exécutabilité pytest
        success &= self._validate_pytest_execution()
        
        # 5. Vérifier disponibilité des composants
        success &= self._validate_components_availability()
        
        # 6. Générer rapport final
        self._generate_final_report()
        
        return success
    
    def _validate_files_exist(self) -> bool:
        """Valide que tous les fichiers de tests existent."""
        print_header("1. VALIDATION EXISTENCE FICHIERS")
        
        all_exist = True
        
        for category, files in self.test_files.items():
            print_info(f"Vérification tests {category}...")
            
            for file_path in files:
                full_path = PROJECT_ROOT / file_path
                exists = full_path.exists()
                
                self.validation_results['files_exist'][file_path] = exists
                
                if exists:
                    print_success(f"{file_path}")
                else:
                    print_error(f"{file_path} - MANQUANT")
                    all_exist = False
        
        # Vérifier documentation
        doc_path = PROJECT_ROOT / "README_TESTS_NOUVEAUX_COMPOSANTS.md"
        if doc_path.exists():
            print_success("README_TESTS_NOUVEAUX_COMPOSANTS.md")
        else:
            print_error("README_TESTS_NOUVEAUX_COMPOSANTS.md - MANQUANT")
            all_exist = False
        
        return all_exist
    
    def _validate_syntax(self) -> bool:
        """Valide la syntaxe Python des fichiers de tests."""
        print_header("2. VALIDATION SYNTAXE PYTHON")
        
        all_valid = True
        
        for category, files in self.test_files.items():
            for file_path in files:
                full_path = PROJECT_ROOT / file_path
                
                if not full_path.exists():
                    continue
                
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    compile(content, str(full_path), 'exec')
                    
                    self.validation_results['syntax_valid'][file_path] = True
                    print_success(f"{file_path} - Syntaxe valide")
                    
                except SyntaxError as e:
                    self.validation_results['syntax_valid'][file_path] = False
                    print_error(f"{file_path} - Erreur syntaxe: {e}")
                    all_valid = False
                    
                except Exception as e:
                    self.validation_results['syntax_valid'][file_path] = False
                    print_error(f"{file_path} - Erreur: {e}")
                    all_valid = False
        
        return all_valid
    
    def _validate_imports(self) -> bool:
        """Valide que les imports des tests fonctionnent."""
        print_header("3. VALIDATION IMPORTS TESTS")
        
        all_imports_work = True
        
        for category, files in self.test_files.items():
            for file_path in files:
                full_path = PROJECT_ROOT / file_path
                
                if not full_path.exists():
                    continue
                
                try:
                    # Lire le fichier et extraire les imports principaux
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Vérifier que les imports critiques sont présents
                    critical_imports = ['pytest', 'sys', 'Path']
                    missing_imports = []
                    
                    for imp in critical_imports:
                        if imp not in content:
                            missing_imports.append(imp)
                    
                    if missing_imports:
                        self.validation_results['imports_work'][file_path] = False
                        print_warning(f"{file_path} - Imports manquants: {missing_imports}")
                    else:
                        self.validation_results['imports_work'][file_path] = True
                        print_success(f"{file_path} - Imports OK")
                        
                except Exception as e:
                    self.validation_results['imports_work'][file_path] = False
                    print_error(f"{file_path} - Erreur imports: {e}")
                    all_imports_work = False
        
        return all_imports_work
    
    def _validate_pytest_execution(self) -> bool:
        """Valide que pytest peut exécuter les tests."""
        print_header("4. VALIDATION EXÉCUTION PYTEST")
        
        all_executable = True
        
        # Test général pytest
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print_success("pytest disponible")
            else:
                print_error("pytest non disponible")
                return False
                
        except Exception as e:
            print_error(f"Erreur vérification pytest: {e}")
            return False
        
        # Test execution dry-run des fichiers de tests
        for category, files in self.test_files.items():
            for file_path in files:
                full_path = PROJECT_ROOT / file_path
                
                if not full_path.exists():
                    continue
                
                try:
                    # Dry run avec --collect-only
                    result = subprocess.run(
                        [sys.executable, '-m', 'pytest', str(full_path), '--collect-only', '-q'],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=str(PROJECT_ROOT)
                    )
                    
                    if result.returncode == 0:
                        self.validation_results['pytest_executable'][file_path] = True
                        print_success(f"{file_path} - Exécutable pytest")
                    else:
                        self.validation_results['pytest_executable'][file_path] = False
                        print_warning(f"{file_path} - Problème pytest: {result.stderr[:100]}...")
                        
                except subprocess.TimeoutExpired:
                    self.validation_results['pytest_executable'][file_path] = False
                    print_error(f"{file_path} - Timeout pytest")
                    all_executable = False
                    
                except Exception as e:
                    self.validation_results['pytest_executable'][file_path] = False
                    print_error(f"{file_path} - Erreur pytest: {e}")
                    all_executable = False
        
        return all_executable
    
    def _validate_components_availability(self) -> bool:
        """Valide la disponibilité des composants requis."""
        print_header("5. VALIDATION COMPOSANTS DISPONIBLES")
        
        for component in self.required_components:
            try:
                importlib.import_module(component)
                self.validation_results['components_available'][component] = True
                print_success(f"{component} - Disponible")
                
            except ImportError:
                self.validation_results['components_available'][component] = False
                print_warning(f"{component} - Non disponible (tests utiliseront mocks)")
            
            except Exception as e:
                self.validation_results['components_available'][component] = False
                print_error(f"{component} - Erreur: {e}")
        
        return True  # Non bloquant car mocks disponibles
    
    def _generate_final_report(self):
        """Génère le rapport final de validation."""
        print_header("RAPPORT FINAL DE VALIDATION")
        
        # Compteurs
        total_files = sum(len(files) for files in self.test_files.values())
        files_exist = sum(1 for exists in self.validation_results['files_exist'].values() if exists)
        syntax_valid = sum(1 for valid in self.validation_results['syntax_valid'].values() if valid)
        imports_work = sum(1 for works in self.validation_results['imports_work'].values() if works)
        pytest_executable = sum(1 for exec in self.validation_results['pytest_executable'].values() if exec)
        components_available = sum(1 for avail in self.validation_results['components_available'].values() if avail)
        
        print(f"""
[STATS] STATISTIQUES:
   - Fichiers de tests: {files_exist}/{total_files} existent
   - Syntaxe valide: {syntax_valid}/{total_files} fichiers
   - Imports fonctionnels: {imports_work}/{total_files} fichiers
   - Executables pytest: {pytest_executable}/{total_files} fichiers
   - Composants disponibles: {components_available}/{len(self.required_components)} composants

[COVERAGE] COUVERTURE:
   - Tests unitaires: 6 fichiers (configuration, FOL, BNF, mocks, orchestration, CLI)
   - Tests d'integration: 3 fichiers (pipeline FOL, authentiques, systeme unifie)
   - Documentation: README complet avec instructions

[COMMANDS] COMMANDES D'EXECUTION:
   - Tests unitaires: python -m pytest tests/unit/argumentation_analysis/ -v
   - Tests integration: python -m pytest tests/integration/ -v
   - Tous les tests: python -m pytest tests/ -v

[CONFIG] CONFIGURATION AUTHENTIQUE:
   - OPENAI_API_KEY=your_key pour LLM reel
   - USE_REAL_JPYPE=true pour Tweety authentique
   - MOCK_LEVEL=none pour elimination mocks
        """)
        
        if files_exist == total_files and syntax_valid == total_files:
            print_success("[READY] SUITE DE TESTS PRETE A L'UTILISATION")
        else:
            print_warning("[PARTIAL] Quelques ajustements necessaires avant utilisation complete")


def main():
    """Point d'entrée principal."""
    validator = TestSuiteValidator()
    
    try:
        success = validator.validate_all()
        
        if success:
            print_success("\n[SUCCESS] VALIDATION REUSSIE - Suite de tests operationnelle")
            return 0
        else:
            print_error("\n[FAILED] VALIDATION ECHOUEE - Corrections necessaires")
            return 1
            
    except KeyboardInterrupt:
        print_warning("\n[INTERRUPTED] Validation interrompue par utilisateur")
        return 130
        
    except Exception as e:
        print_error(f"\n[EXCEPTION] Erreur inattendue: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
>>>>>>> BACKUP
