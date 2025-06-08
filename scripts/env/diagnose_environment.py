#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de diagnostic complet de l'environnement - Oracle Enhanced v2.1.0

Vérifie l'état de l'environnement dédié et propose des solutions automatiques.
"""

import sys
import os
import subprocess
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXPECTED_ENV_NAME = "projet-is"
CRITICAL_PACKAGES = [
    "numpy", "pandas", "scipy", "scikit-learn", "nltk", "spacy",
    "flask", "requests", "pydantic", "cryptography", "tqdm",
    "matplotlib", "seaborn", "networkx", "clingo", "jpype1",
    "torch", "transformers", "semantic-kernel", "pytest"
]

class EnvironmentDiagnostic:
    """Diagnostic complet de l'environnement."""
    
    def __init__(self):
        self.results = {}
        self.warnings = []
        self.errors = []
        self.solutions = []
        
    def run_full_diagnostic(self, verbose: bool = False) -> Dict:
        """Exécute le diagnostic complet."""
        print("[LOUPE] DIAGNOSTIC ENVIRONNEMENT - Oracle Enhanced v2.1.0")
        print("=" * 60)
        
        # 1. Détection environnement actuel
        self._detect_current_environment()
        
        # 2. Vérification Python
        self._check_python_version()
        
        # 3. Vérification PYTHONPATH
        self._check_pythonpath()
        
        # 4. Vérification dépendances critiques
        self._check_critical_dependencies(verbose)
        
        # 5. Vérification environnements disponibles
        self._check_available_environments()
        
        # 6. Vérification fallbacks
        self._check_fallbacks()
        
        # 7. Génération du rapport
        self._generate_report()
        
        return self.results
    
    def _detect_current_environment(self):
        """Détecte l'environnement Python actuel."""
        print("\n📍 DÉTECTION ENVIRONNEMENT ACTUEL")
        
        # Vérifier CONDA_DEFAULT_ENV
        conda_env = os.environ.get('CONDA_DEFAULT_ENV', 'N/A')
        virtual_env = os.environ.get('VIRTUAL_ENV', None)
        
        env_type = "système"
        env_name = "python-système"
        
        if conda_env and conda_env != "N/A":
            env_type = "conda"
            env_name = conda_env
            if conda_env == EXPECTED_ENV_NAME:
                print(f"[OK] Environnement conda correct: {conda_env}")
            else:
                print(f"[ATTENTION]  Environnement conda: {conda_env} (attendu: {EXPECTED_ENV_NAME})")
                self.warnings.append(f"Environnement conda incorrect: {conda_env}")
        elif virtual_env:
            env_type = "venv"
            env_name = Path(virtual_env).name
            print(f"ℹ️  Environnement venv: {env_name}")
        else:
            print(f"[ATTENTION]  Python système utilisé (non recommandé)")
            self.warnings.append("Python système utilisé au lieu de l'environnement dédié")
        
        self.results['environment'] = {
            'type': env_type,
            'name': env_name,
            'is_dedicated': env_type in ['conda', 'venv'],
            'is_correct': env_name == EXPECTED_ENV_NAME
        }
    
    def _check_python_version(self):
        """Vérifie la version Python."""
        print("\n🐍 VERSION PYTHON")
        
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        expected_version = "3.10"
        
        print(f"Version actuelle: Python {version_str}")
        print(f"Exécutable: {sys.executable}")
        
        if f"{version.major}.{version.minor}" == expected_version:
            print(f"[OK] Version Python correcte: {expected_version}")
        else:
            print(f"[ATTENTION]  Version Python: {version.major}.{version.minor} (recommandé: {expected_version})")
            self.warnings.append(f"Version Python {version.major}.{version.minor} (recommandé: {expected_version})")
        
        self.results['python'] = {
            'version': version_str,
            'executable': sys.executable,
            'is_correct_version': f"{version.major}.{version.minor}" == expected_version
        }
    
    def _check_pythonpath(self):
        """Vérifie la configuration PYTHONPATH."""
        print("\n📂 PYTHONPATH")
        
        pythonpath = os.environ.get('PYTHONPATH', '')
        required_paths = [
            str(PROJECT_ROOT),
            str(PROJECT_ROOT / "project_core"),
            str(PROJECT_ROOT / "libs"),
            str(PROJECT_ROOT / "argumentation_analysis")
        ]
        
        missing_paths = []
        for path in required_paths:
            if path in sys.path:
                print(f"[OK] {path}")
            else:
                print(f"[X] {path} (manquant dans sys.path)")
                missing_paths.append(path)
        
        if missing_paths:
            self.warnings.append(f"Chemins manquants dans PYTHONPATH: {len(missing_paths)}")
            self.solutions.append("Utiliser setup_project_env.ps1 pour configurer PYTHONPATH")
        
        self.results['pythonpath'] = {
            'configured': bool(pythonpath),
            'missing_paths': missing_paths,
            'sys_path_count': len(sys.path)
        }
    
    def _check_critical_dependencies(self, verbose: bool):
        """Vérifie les dépendances critiques."""
        print("\n📦 DÉPENDANCES CRITIQUES")
        
        installed = {}
        missing = []
        
        for package in CRITICAL_PACKAGES:
            try:
                module = importlib.import_module(package)
                version = getattr(module, '__version__', 'unknown')
                installed[package] = version
                if verbose:
                    print(f"[OK] {package}: {version}")
                else:
                    print(f"[OK] {package}")
            except ImportError:
                missing.append(package)
                print(f"[X] {package}: MANQUANT")
        
        if missing:
            self.errors.append(f"Dépendances manquantes: {', '.join(missing)}")
            self.solutions.append("Installer avec: conda env create -f environment.yml")
        
        # Vérifications spéciales
        self._check_semantic_kernel()
        self._check_jpype()
        
        self.results['dependencies'] = {
            'installed': installed,
            'missing': missing,
            'total_required': len(CRITICAL_PACKAGES),
            'success_rate': len(installed) / len(CRITICAL_PACKAGES) * 100
        }
    
    def _check_semantic_kernel(self):
        """Vérification spéciale semantic-kernel."""
        try:
            import semantic_kernel
            sk_version = semantic_kernel.__version__
            print(f"ℹ️  semantic-kernel: {sk_version}")
            
            # Vérifier fallback agents
            try:
                from project_core.semantic_kernel_agents_fallback import AuthorRole
                print("[OK] Fallback agents: OK")
            except ImportError:
                print("[ATTENTION]  Fallback agents: Non disponible")
                self.warnings.append("Fallback semantic-kernel agents non disponible")
                
        except ImportError:
            self.errors.append("semantic-kernel non installé")
    
    def _check_jpype(self):
        """Vérification spéciale JPype."""
        jpype_ok = False
        try:
            import jpype1
            print(f"[OK] JPype1: {jpype1.__version__}")
            jpype_ok = True
        except ImportError:
            try:
                from tests.mocks import jpype_mock
                print("[OK] JPype Mock: OK")
                jpype_ok = True
            except ImportError:
                print("[ATTENTION]  JPype/Mock: Non disponible")
                self.warnings.append("JPype non disponible (tests Java limités)")
        
        self.results['jpype'] = jpype_ok
    
    def _check_available_environments(self):
        """Vérifie les environnements disponibles."""
        print("\n[MONDE] ENVIRONNEMENTS DISPONIBLES")
        
        # Conda
        conda_envs = []
        try:
            result = subprocess.run(['conda', 'env', 'list'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip() and not line.startswith('#'):
                        env_name = line.split()[0]
                        conda_envs.append(env_name)
                        if env_name == EXPECTED_ENV_NAME:
                            print(f"[OK] Conda: {env_name} (TARGET)")
                        else:
                            print(f"ℹ️  Conda: {env_name}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("[ATTENTION]  Conda: Non disponible")
        
        # Venv locaux
        venv_dirs = []
        for venv_name in ['venv', 'env', '.venv']:
            venv_path = PROJECT_ROOT / venv_name
            if venv_path.exists():
                venv_dirs.append(venv_name)
                print(f"ℹ️  Venv local: {venv_name}")
        
        if not conda_envs and not venv_dirs:
            self.errors.append("Aucun environnement virtuel détecté")
            self.solutions.append("Créer l'environnement: conda env create -f environment.yml")
        
        self.results['available_environments'] = {
            'conda': conda_envs,
            'venv': venv_dirs,
            'has_target': EXPECTED_ENV_NAME in conda_envs
        }
    
    def _check_fallbacks(self):
        """Vérifie les fallbacks implémentés."""
        print("\n🛡️  FALLBACKS")
        
        fallback_files = [
            "project_core/semantic_kernel_agents_fallback.py",
            "project_core/semantic_kernel_agents_import.py",
            "tests/mocks/jpype_mock.py"
        ]
        
        available_fallbacks = []
        for fallback in fallback_files:
            path = PROJECT_ROOT / fallback
            if path.exists():
                available_fallbacks.append(fallback)
                print(f"[OK] {fallback}")
            else:
                print(f"[X] {fallback}")
        
        self.results['fallbacks'] = available_fallbacks
    
    def _generate_report(self):
        """Génère le rapport final."""
        print("\n" + "=" * 60)
        print("[GRAPHIQUE] RÉSUMÉ DIAGNOSTIC")
        print("=" * 60)
        
        # Score global
        total_checks = 5
        passed_checks = 0
        
        if self.results['environment']['is_dedicated']:
            passed_checks += 1
        if self.results['python']['is_correct_version']:
            passed_checks += 1
        if not self.results['pythonpath']['missing_paths']:
            passed_checks += 1
        if self.results['dependencies']['success_rate'] > 90:
            passed_checks += 1
        if self.results['available_environments']['has_target']:
            passed_checks += 1
        
        score = (passed_checks / total_checks) * 100
        
        print(f"Score environnement: {score:.0f}% ({passed_checks}/{total_checks})")
        
        # Statut
        if score >= 90:
            print("[OK] ENVIRONNEMENT OPTIMAL")
        elif score >= 70:
            print("[ATTENTION]  ENVIRONNEMENT ACCEPTABLE (améliorations recommandées)")
        else:
            print("[X] ENVIRONNEMENT PROBLÉMATIQUE (action requise)")
        
        # Warnings
        if self.warnings:
            print(f"\n[ATTENTION]  Avertissements ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        # Erreurs
        if self.errors:
            print(f"\n[X] Erreurs ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        # Solutions
        if self.solutions:
            print(f"\n[CLE] Solutions recommandées:")
            for solution in self.solutions:
                print(f"   • {solution}")
        
        self.results['summary'] = {
            'score': score,
            'status': 'optimal' if score >= 90 else 'acceptable' if score >= 70 else 'problematic',
            'warnings_count': len(self.warnings),
            'errors_count': len(self.errors)
        }

def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnostic environnement Oracle Enhanced")
    parser.add_argument('--full', action='store_true', 
                       help='Diagnostic complet avec détails')
    parser.add_argument('--json', action='store_true', 
                       help='Sortie en format JSON')
    
    args = parser.parse_args()
    
    diagnostic = EnvironmentDiagnostic()
    results = diagnostic.run_full_diagnostic(verbose=args.full)
    
    if args.json:
        import json
        print("\n" + "=" * 60)
        print("JSON EXPORT")
        print("=" * 60)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # Code de sortie basé sur le score
    score = results.get('summary', {}).get('score', 0)
    sys.exit(0 if score >= 70 else 1)

if __name__ == "__main__":
    main()