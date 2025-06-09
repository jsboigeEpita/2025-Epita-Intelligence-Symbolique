#!/usr/bin/env python3
"""
Tests unitaires pour le module environment_manager
================================================

Tests des nouvelles fonctionnalités d'auto-activation d'environnement.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock, call
from pathlib import Path

# Configuration des chemins pour les tests
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
scripts_core = current_dir / "scripts" / "core"
if str(scripts_core) not in sys.path:
    sys.path.insert(0, str(scripts_core))

from scripts.core.environment_manager import (
    is_conda_env_active, 
    auto_activate_env,
    EnvironmentManager
)


class TestIsCondaEnvActive(unittest.TestCase):
    """Tests pour la fonction is_conda_env_active"""
    
    def setUp(self):
        """Setup pour chaque test"""
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Cleanup après chaque test"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_env_active_default(self):
        """Test environnement actif avec nom par défaut"""
        os.environ['CONDA_DEFAULT_ENV'] = 'projet-is'
        
        result = is_conda_env_active()
        
        self.assertTrue(result)
    
    def test_env_active_custom(self):
        """Test environnement actif avec nom personnalisé"""
        os.environ['CONDA_DEFAULT_ENV'] = 'custom-env'
        
        result = is_conda_env_active('custom-env')
        
        self.assertTrue(result)
    
    def test_env_not_active(self):
        """Test environnement non actif"""
        os.environ['CONDA_DEFAULT_ENV'] = 'other-env'
        
        result = is_conda_env_active('projet-is')
        
        self.assertFalse(result)
    
    def test_env_var_missing(self):
        """Test variable d'environnement absente"""
        os.environ.pop('CONDA_DEFAULT_ENV', None)
        
        result = is_conda_env_active()
        
        self.assertFalse(result)
    
    def test_env_var_empty(self):
        """Test variable d'environnement vide"""
        os.environ['CONDA_DEFAULT_ENV'] = ''
        
        result = is_conda_env_active()
        
        self.assertFalse(result)


class TestAutoActivateEnv(unittest.TestCase):
    """Tests pour la fonction auto_activate_env"""
    
    def setUp(self):
        """Setup pour chaque test"""
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Cleanup après chaque test"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @patch('scripts.core.environment_manager.is_conda_env_active')
    def test_env_already_active_silent(self, mock_is_active):
        """Test environnement déjà actif en mode silencieux"""
        mock_is_active.return_value = True
        
        result = auto_activate_env(silent=True)
        
        self.assertTrue(result)
        mock_is_active.assert_called_once_with('projet-is')
    
    @patch('scripts.core.environment_manager.is_conda_env_active')
    @patch('builtins.print')
    def test_env_already_active_verbose(self, mock_print, mock_is_active):
        """Test environnement déjà actif en mode verbeux"""
        mock_is_active.return_value = True
        
        result = auto_activate_env(silent=False)
        
        self.assertTrue(result)
        mock_print.assert_called_with("[OK] Environnement 'projet-is' deja actif")
    
    @patch('scripts.core.environment_manager.is_conda_env_active')
    @patch('scripts.core.environment_manager.EnvironmentManager')
    def test_conda_not_available(self, mock_env_manager_class, mock_is_active):
        """Test conda non disponible"""
        mock_is_active.return_value = False
        mock_env_manager = MagicMock()
        mock_env_manager.check_conda_available.return_value = False
        mock_env_manager_class.return_value = mock_env_manager
        
        result = auto_activate_env(silent=True)
        
        self.assertFalse(result)
        mock_env_manager.check_conda_available.assert_called_once()
    
    @patch('scripts.core.environment_manager.is_conda_env_active')
    @patch('scripts.core.environment_manager.EnvironmentManager')
    @patch('builtins.print')
    def test_conda_not_available_verbose(self, mock_print, mock_env_manager_class, mock_is_active):
        """Test conda non disponible en mode verbeux"""
        mock_is_active.return_value = False
        mock_env_manager = MagicMock()
        mock_env_manager.check_conda_available.return_value = False
        mock_env_manager_class.return_value = mock_env_manager
        
        result = auto_activate_env(env_name='test-env', silent=False)
        
        self.assertFalse(result)
        mock_print.assert_called_with("[ERROR] Conda non disponible - impossible d'activer 'test-env'")
    
    @patch('scripts.core.environment_manager.is_conda_env_active')
    @patch('scripts.core.environment_manager.EnvironmentManager')
    def test_env_not_exists(self, mock_env_manager_class, mock_is_active):
        """Test environnement n'existe pas"""
        mock_is_active.return_value = False
        mock_env_manager = MagicMock()
        mock_env_manager.check_conda_available.return_value = True
        mock_env_manager.check_conda_env_exists.return_value = False
        mock_env_manager_class.return_value = mock_env_manager
        
        result = auto_activate_env(silent=True)
        
        self.assertFalse(result)
        mock_env_manager.check_conda_env_exists.assert_called_once()
    
    @patch('scripts.core.environment_manager.is_conda_env_active')
    @patch('scripts.core.environment_manager.EnvironmentManager')
    @patch('builtins.print')
    def test_successful_activation(self, mock_print, mock_env_manager_class, mock_is_active):
        """Test activation réussie"""
        mock_is_active.return_value = False
        mock_env_manager = MagicMock()
        mock_env_manager.check_conda_available.return_value = True
        mock_env_manager.check_conda_env_exists.return_value = True
        mock_env_manager_class.return_value = mock_env_manager
        
        result = auto_activate_env(env_name='projet-is', silent=False)
        
        self.assertTrue(result)
        
        # Vérifier les appels
        mock_env_manager.check_conda_available.assert_called_once()
        mock_env_manager.check_conda_env_exists.assert_called_once_with('projet-is')
        mock_env_manager.setup_environment_variables.assert_called_once()
        
        # Vérifier les prints
        mock_print.assert_any_call("[INFO] Auto-activation de l'environnement 'projet-is'...")
        mock_print.assert_any_call("[OK] Environnement 'projet-is' auto-active")
        
        # Vérifier que la variable d'environnement est définie
        self.assertEqual(os.environ.get('CONDA_DEFAULT_ENV'), 'projet-is')
    
    @patch('scripts.core.environment_manager.is_conda_env_active')
    def test_exception_handling(self, mock_is_active):
        """Test gestion d'exception"""
        mock_is_active.side_effect = Exception("Test error")
        
        result = auto_activate_env(silent=True)
        
        self.assertFalse(result)
    
    @patch('scripts.core.environment_manager.is_conda_env_active')
    @patch('builtins.print')
    def test_exception_handling_verbose(self, mock_print, mock_is_active):
        """Test gestion d'exception en mode verbeux"""
        mock_is_active.side_effect = Exception("Test error")
        
        result = auto_activate_env(silent=False)
        
        self.assertFalse(result)
        mock_print.assert_called_with("❌ Erreur auto-activation: Test error")


class TestEnvironmentManagerAutoActivation(unittest.TestCase):
    """Tests d'intégration pour EnvironmentManager avec auto-activation"""
    
    def setUp(self):
        """Setup pour les tests d'intégration"""
        self.original_env = os.environ.copy()
        
    def tearDown(self):
        """Cleanup après tests"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @patch('subprocess.run')
    def test_environment_manager_conda_check(self, mock_subprocess):
        """Test vérification conda dans EnvironmentManager"""
        # Mock conda disponible
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "conda 4.12.0"
        mock_subprocess.return_value = mock_result
        
        manager = EnvironmentManager()
        result = manager.check_conda_available()
        
        self.assertTrue(result)
        mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_environment_manager_env_exists(self, mock_subprocess):
        """Test vérification existence environnement"""
        # Mock liste environnements
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"envs": ["/path/to/projet-is", "/path/to/other-env"]}'
        mock_subprocess.return_value = mock_result
        
        manager = EnvironmentManager()
        result = manager.check_conda_env_exists('projet-is')
        
        self.assertTrue(result)
        
        # Test environnement inexistant
        result = manager.check_conda_env_exists('nonexistent-env')
        self.assertFalse(result)
    
    def test_environment_manager_setup_variables(self):
        """Test configuration des variables d'environnement"""
        manager = EnvironmentManager()
        
        # Variables avant setup
        original_vars = {k: v for k, v in os.environ.items() 
                        if k in ['PYTHONIOENCODING', 'PYTHONPATH', 'PROJECT_ROOT']}
        
        manager.setup_environment_variables()
        
        # Vérifier que les variables sont définies
        self.assertEqual(os.environ.get('PYTHONIOENCODING'), 'utf-8')
        self.assertIsNotNone(os.environ.get('PYTHONPATH'))
        self.assertIsNotNone(os.environ.get('PROJECT_ROOT'))
    
    def test_environment_manager_setup_additional_vars(self):
        """Test configuration avec variables additionnelles"""
        manager = EnvironmentManager()
        additional_vars = {'TEST_VAR': 'test_value', 'CUSTOM_PATH': '/custom/path'}
        
        manager.setup_environment_variables(additional_vars)
        
        # Vérifier variables standard
        self.assertEqual(os.environ.get('PYTHONIOENCODING'), 'utf-8')
        
        # Vérifier variables additionnelles
        self.assertEqual(os.environ.get('TEST_VAR'), 'test_value')
        self.assertEqual(os.environ.get('CUSTOM_PATH'), '/custom/path')


class TestEnvironmentManagerStressTests(unittest.TestCase):
    """Tests de stress pour EnvironmentManager"""
    
    def test_multiple_manager_instances(self):
        """Test création multiple d'instances EnvironmentManager"""
        managers = [EnvironmentManager() for _ in range(10)]
        
        # Tous les managers doivent avoir les mêmes configurations de base
        for manager in managers:
            self.assertEqual(manager.default_conda_env, "projet-is")
            self.assertEqual(manager.required_python_version, (3, 8))
    
    @patch('subprocess.run')
    def test_concurrent_conda_checks(self, mock_subprocess):
        """Test vérifications conda concurrentes"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "conda 4.12.0"
        mock_subprocess.return_value = mock_result
        
        manager = EnvironmentManager()
        
        # Multiples vérifications
        results = [manager.check_conda_available() for _ in range(5)]
        
        # Toutes doivent réussir
        self.assertTrue(all(results))
        
        # Subprocess appelé 5 fois
        self.assertEqual(mock_subprocess.call_count, 5)


if __name__ == '__main__':
    # Configuration pour réduire le bruit des logs pendant les tests
    import logging
    logging.getLogger().setLevel(logging.CRITICAL)
    
    # Exécution des tests
    unittest.main(verbosity=2)