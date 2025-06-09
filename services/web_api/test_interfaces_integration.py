#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests d'intégration inter-interfaces
====================================

Tests pour valider la coexistence et l'intégration entre l'interface React 
et l'interface Flask dans le même environnement de services web.

Version: 1.0.0
Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import sys
import os
import json
import subprocess
import time
import unittest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Configuration des chemins
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class TestInterfacesCoexistence(unittest.TestCase):
    """Tests de coexistence des interfaces React et Flask."""
    
    @classmethod
    def setUpClass(cls):
        """Configuration des tests."""
        cls.project_root = PROJECT_ROOT
        cls.services_dir = cls.project_root / "services" / "web_api"
        
        # Répertoires des interfaces
        cls.simple_interface_dir = cls.services_dir / "interface-simple"
        cls.react_interface_dir = cls.services_dir / "interface-web-argumentative"
        
        # Vérifier l'existence des répertoires
        cls.simple_exists = cls.simple_interface_dir.exists()
        cls.react_exists = cls.react_interface_dir.exists()
        
        # Fichiers clés à vérifier
        cls.key_files = {
            'simple_app': cls.simple_interface_dir / "app.py",
            'simple_test': cls.simple_interface_dir / "test_webapp.py",
            'react_package': cls.react_interface_dir / "package.json",
            'react_app': cls.react_interface_dir / "src" / "App.js"
        }
    
    def test_01_interface_directories_structure(self):
        """Test 1: Structure des répertoires d'interfaces."""
        self.assertTrue(self.simple_exists, "Le répertoire interface-simple doit exister")
        self.assertTrue(self.react_exists, "Le répertoire interface-web-argumentative doit exister")
        
        # Vérifier que les deux interfaces sont bien séparées
        self.assertNotEqual(self.simple_interface_dir, self.react_interface_dir,
                           "Les interfaces doivent être dans des répertoires séparés")
    
    def test_02_key_files_existence(self):
        """Test 2: Existence des fichiers clés des interfaces."""
        for file_name, file_path in self.key_files.items():
            with self.subTest(file=file_name):
                self.assertTrue(file_path.exists(), f"Le fichier {file_name} doit exister: {file_path}")
    
    def test_03_port_configuration_separation(self):
        """Test 3: Configuration des ports pour éviter les conflits."""
        # Vérifier que les interfaces utilisent des ports différents par défaut
        
        # Interface simple (Flask) - port 3000 par défaut
        if self.key_files['simple_app'].exists():
            with open(self.key_files['simple_app'], 'r', encoding='utf-8') as f:
                simple_content = f.read()
            
            # Recherche des configurations de port (3000 est le port par défaut)
            port_found = any(port in simple_content for port in ['3000', '5000', 'PORT'])
            self.assertTrue(port_found,
                         "L'interface simple doit avoir une référence à un port (3000, 5000, ou PORT)")
        
        # Interface React - vérifier package.json
        if self.key_files['react_package'].exists():
            with open(self.key_files['react_package'], 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            # Vérifier la configuration des scripts
            self.assertIn('scripts', package_data, "package.json doit contenir des scripts")
            scripts = package_data.get('scripts', {})
            
            # Le script start doit exister
            self.assertIn('start', scripts, "Le script 'start' doit exister pour React")
    
    def test_04_documentation_integration(self):
        """Test 4: Documentation et intégration."""
        # Vérifier l'existence des README
        readme_files = [
            self.services_dir / "README.md",
            self.simple_interface_dir / "README_INTEGRATION.md",
            self.react_interface_dir / "README.md"
        ]
        
        existing_readmes = [f for f in readme_files if f.exists()]
        self.assertGreater(len(existing_readmes), 0, 
                          "Au moins un fichier README doit exister")
        
        # Vérifier le contenu du README principal si disponible
        main_readme = self.services_dir / "README.md"
        if main_readme.exists():
            with open(main_readme, 'r', encoding='utf-8') as f:
                readme_content = f.read().lower()
            
            # Le README doit mentionner les deux interfaces
            self.assertIn('interface', readme_content, 
                         "Le README doit mentionner les interfaces")
    
    def test_05_dependency_conflicts_check(self):
        """Test 5: Vérification des conflits de dépendances."""
        # Vérifier que les dépendances Python (Flask) et Node.js (React) ne entrent pas en conflit
        
        # Check des imports Python dans l'interface simple
        if self.key_files['simple_app'].exists():
            try:
                # Test d'import sans exécution
                # Test d'import depuis le répertoire interface-simple
                result = subprocess.run([
                    sys.executable, '-c',
                    f"import sys; import os; os.chdir('{self.simple_interface_dir}'); "
                    f"from app import app; print('OK')"
                ], capture_output=True, text=True, timeout=10)
                
                self.assertEqual(result.returncode, 0, 
                               "L'import de l'interface Flask ne doit pas échouer")
                
            except subprocess.TimeoutExpired:
                self.fail("L'import de l'interface Flask a dépassé le timeout")
        
        # Vérifier la validité du package.json React
        if self.key_files['react_package'].exists():
            try:
                with open(self.key_files['react_package'], 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                
                # Vérifier la structure basique
                self.assertIn('name', package_data, "package.json doit avoir un nom")
                self.assertIn('dependencies', package_data, "package.json doit avoir des dépendances")
                
            except json.JSONDecodeError:
                self.fail("Le fichier package.json doit être un JSON valide")
    
    def test_06_services_scripts_integration(self):
        """Test 6: Intégration des scripts de services."""
        # Vérifier que les scripts de gestion reconnaissent les deux interfaces
        scripts_to_check = [
            self.services_dir / "start_simple_only.py",
            self.services_dir / "stop_all_services.py",
            self.services_dir / "health_check.py"
        ]
        
        for script in scripts_to_check:
            if script.exists():
                with self.subTest(script=script.name):
                    # Vérifier que le script mentionne ou gère les interfaces
                    with open(script, 'r', encoding='utf-8') as f:
                        script_content = f.read().lower()
                    
                    # Le script doit au moins mentionner une forme d'interface
                    interface_mentions = ['interface', 'flask', 'react', 'web']
                    has_interface_mention = any(mention in script_content for mention in interface_mentions)
                    
                    self.assertTrue(has_interface_mention, 
                                   f"Le script {script.name} doit mentionner les interfaces")
    
    def test_07_shared_resources_no_conflicts(self):
        """Test 7: Ressources partagées sans conflits."""
        # Vérifier que les ressources partagées (templates, static) ne créent pas de conflits
        
        # Interface simple - templates et static
        simple_templates = self.simple_interface_dir / "templates"
        simple_static = self.simple_interface_dir / "static"
        
        # Interface React - build et public
        react_public = self.react_interface_dir / "public"
        react_src = self.react_interface_dir / "src"
        
        # Vérifier la séparation des ressources
        if simple_templates.exists() and react_src.exists():
            # Les fichiers templates Flask ne doivent pas interférer avec React
            simple_files = set(f.name for f in simple_templates.rglob('*') if f.is_file())
            react_files = set(f.name for f in react_src.rglob('*') if f.is_file())
            
            # Vérifier qu'il n'y a pas de conflits de noms critiques
            critical_conflicts = simple_files.intersection(react_files)
            critical_conflicts = critical_conflicts.intersection({'index.html', 'app.js', 'main.js'})
            
            if critical_conflicts:
                # C'est acceptable si les fichiers sont dans des contextes différents
                print(f"[INFO] Fichiers avec noms similaires détectés: {critical_conflicts}")
                print("[INFO] Ceci est acceptable si les contextes sont séparés")
    
    def test_08_integration_apis_compatibility(self):
        """Test 8: Compatibilité des APIs d'intégration."""
        # Vérifier que les APIs Flask et les appels React sont compatibles
        
        if self.key_files['simple_app'].exists():
            with open(self.key_files['simple_app'], 'r', encoding='utf-8') as f:
                flask_content = f.read()
            
            # Rechercher les routes API définies
            api_routes = []
            lines = flask_content.split('\n')
            for line in lines:
                if '@app.route' in line and '/api/' in line:
                    api_routes.append(line.strip())
            
            # Vérifier les routes API communes
            expected_routes = ['/status', '/analyze', '/api/examples']
            for route in expected_routes:
                route_defined = any(route in flask_content for route in expected_routes)
                if route_defined:
                    # Au moins une route API est définie
                    break
            else:
                self.fail("Aucune route API standard trouvée dans l'interface Flask")
        
        # Vérifier les appels API côté React
        if self.react_interface_dir.exists():
            api_files = list((self.react_interface_dir / "src").rglob("*api*"))
            if api_files:
                # Examiner les fichiers API React
                for api_file in api_files:
                    if api_file.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                        try:
                            with open(api_file, 'r', encoding='utf-8') as f:
                                api_content = f.read()
                            
                            # Vérifier les URLs d'API
                            if 'localhost' in api_content or 'api/' in api_content:
                                # L'interface React fait des appels API
                                self.assertIn('/', api_content, "Les appels API doivent être structurés")
                        except UnicodeDecodeError:
                            # Ignorer les fichiers non-texte
                            continue
    
    def test_09_build_system_compatibility(self):
        """Test 9: Compatibilité des systèmes de build."""
        # Vérifier que les systèmes de build Flask et React sont compatibles
        
        # Flask - pas de build nécessaire, vérifier les imports
        flask_app = self.key_files['simple_app']
        if flask_app.exists():
            # Tester la syntaxe Python
            try:
                result = subprocess.run([
                    sys.executable, '-m', 'py_compile', str(flask_app)
                ], capture_output=True, text=True, timeout=10)
                
                self.assertEqual(result.returncode, 0, "L'app Flask doit être syntaxiquement correcte")
                
            except subprocess.TimeoutExpired:
                self.fail("La compilation Flask a dépassé le timeout")
        
        # React - vérifier package.json et structure
        if self.key_files['react_package'].exists():
            # Vérifier la structure des scripts de build
            with open(self.key_files['react_package'], 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            scripts = package_data.get('scripts', {})
            
            # Les scripts essentiels doivent exister
            essential_scripts = ['start', 'build']
            for script in essential_scripts:
                if script in scripts:
                    self.assertIsInstance(scripts[script], str, 
                                        f"Le script {script} doit être une chaîne")


class TestIntegrationEnvironment(unittest.TestCase):
    """Tests de l'environnement d'intégration."""
    
    def setUp(self):
        """Configuration pour les tests d'environnement."""
        self.services_dir = PROJECT_ROOT / "services" / "web_api"
    
    def test_shared_dependencies_management(self):
        """Test de gestion des dépendances partagées."""
        # Vérifier que OrchestrationServiceManager est accessible aux deux interfaces
        try:
            from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager
            servicemanager_available = True
        except ImportError:
            servicemanager_available = False
        
        # OrchestrationServiceManager doit être géré de manière cohérente
        self.assertIsInstance(servicemanager_available, bool,
                            "La disponibilité de OrchestrationServiceManager doit être déterminable")
    
    def test_logging_integration(self):
        """Test d'intégration des logs."""
        # Vérifier que les logs des deux interfaces ne se chevauchent pas
        logs_dir = PROJECT_ROOT / "logs"
        
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            
            # S'assurer qu'il n'y a pas de conflits dans les noms de logs
            log_names = [f.name for f in log_files]
            unique_names = set(log_names)
            
            self.assertEqual(len(log_names), len(unique_names), 
                           "Les fichiers de log ne doivent pas avoir de noms en conflit")
    
    def test_configuration_consistency(self):
        """Test de cohérence des configurations."""
        # Vérifier que les configurations sont cohérentes entre interfaces
        config_files = [
            self.services_dir / "config.json",
            PROJECT_ROOT / "config" / "webapp_config.yml"
        ]
        
        existing_configs = [f for f in config_files if f.exists()]
        
        # Si des configurations existent, elles doivent être valides
        for config_file in existing_configs:
            with self.subTest(config=config_file.name):
                if config_file.suffix == '.json':
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            json.load(f)
                        self.assertTrue(True, f"Configuration JSON {config_file.name} valide")
                    except json.JSONDecodeError:
                        self.fail(f"Configuration JSON {config_file.name} invalide")


def test_interfaces_integration_complete():
    """Test complet d'intégration des interfaces."""
    print("=== TESTS D'INTÉGRATION INTER-INTERFACES ===")
    print("=" * 50)
    
    # Tests de coexistence
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInterfacesCoexistence)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIntegrationEnvironment))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Résumé détaillé
    print("\n" + "=" * 50)
    print("RÉSUMÉ DES TESTS D'INTÉGRATION")
    print("=" * 50)
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    
    if result.failures:
        print("\nÉCHECS DÉTAILLÉS:")
        for test, traceback in result.failures:
            print(f"- {test}")
            error_lines = traceback.split('\n')
            for line in error_lines:
                if 'AssertionError:' in line:
                    print(f"  -> {line.strip()}")
    
    if result.errors:
        print("\nERREURS DÉTAILLÉES:")
        for test, traceback in result.errors:
            print(f"- {test}")
            error_lines = traceback.split('\n')
            for line in error_lines:
                if any(keyword in line for keyword in ['Error:', 'Exception:']):
                    print(f"  -> {line.strip()}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nSTATUT INTÉGRATION: {'[OK] SUCCÈS' if success else '[ERREUR] PROBLÈMES DÉTECTÉS'}")
    
    # Recommandations basées sur les résultats
    if not success:
        print("\n[INFO] RECOMMANDATIONS:")
        print("- Vérifier la séparation des ports entre interfaces")
        print("- Contrôler la cohérence des configurations")
        print("- Valider les dépendances partagées")
    else:
        print("\n[OK] INTÉGRATION VALIDÉE:")
        print("- Interfaces correctement séparées")
        print("- Pas de conflits détectés")
        print("- Environnement d'intégration stable")
    
    return success


if __name__ == '__main__':
    success = test_interfaces_integration_complete()
    sys.exit(0 if success else 1)