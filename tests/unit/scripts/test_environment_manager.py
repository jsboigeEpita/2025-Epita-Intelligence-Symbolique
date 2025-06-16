
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

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

import logging
from unittest.mock import MagicMock, patch

# Configuration du logger
logger = logging.getLogger(__name__)
from pathlib import Path

# Configuration des chemins pour les tests
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
scripts_core = current_dir / "scripts" / "core"
if str(scripts_core) not in sys.path:
    sys.path.insert(0, str(scripts_core))

from project_core.core_from_scripts.environment_manager import (
    is_conda_env_active,
    auto_activate_env,
    EnvironmentManager
)


class TestIsCondaEnvActive(unittest.TestCase):
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

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
    """
    Classe de test pour la fonction façade `auto_activate_env`.
    La stratégie de test est de mocker la méthode centrale `EnvironmentManager.activate_project_environment`
    pour simuler ses codes de retour (0 pour succès, non-zéro pour échec) et de vérifier que
    `auto_activate_env` interprète correctement ces codes.
    """

    def setUp(self):
        """Setup minimal pour les tests de cette classe."""
        # On ne mocke plus JPype globalement ici, car non-pertinent pour ces tests logiques.
        # On garde une sauvegarde de l'environnement si nécessaire.
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Nettoyage de l'environnement après chaque test."""
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch('os.getenv')
    def test_activation_script_running_skips_execution(self, mock_getenv):
        """Vérifie que la fonction retourne True immédiatement si le script d'activation principal est déjà en cours."""
        mock_getenv.return_value = 'true'
        # On vérifie qu'EnvironmentManager n'est même pas instancié
        with patch('project_core.core_from_scripts.environment_manager.EnvironmentManager') as mock_manager:
            result = auto_activate_env()
            self.assertTrue(result)
            mock_getenv.assert_called_with('IS_ACTIVATION_SCRIPT_RUNNING')
            mock_manager.assert_not_called()

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager')
    def test_successful_activation_silent(self, mock_env_manager_class):
        """Test une activation réussie en mode silencieux."""
        # Simule un code de sortie de 0 (succès) de la méthode centrale
        mock_manager_instance = mock_env_manager_class.return_value
        mock_manager_instance.activate_project_environment.return_value = 0

        result = auto_activate_env(env_name='test-env', silent=True)

        self.assertTrue(result)
        mock_manager_instance.activate_project_environment.assert_called_once_with(env_name='test-env')

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager')
    def test_successful_activation_verbose(self, mock_env_manager_class):
        """Test une activation réussie en mode verbeux."""
        mock_manager_instance = mock_env_manager_class.return_value
        mock_manager_instance.activate_project_environment.return_value = 0
        
        # On patche le logger utilisé à l'intérieur de la fonction pour vérifier son appel
        with patch('project_core.core_from_scripts.environment_manager.Logger') as mock_logger_class:
            mock_logger_instance = mock_logger_class.return_value
            result = auto_activate_env(env_name='test-env-verbose', silent=False)

            self.assertTrue(result)
            mock_manager_instance.activate_project_environment.assert_called_once_with(env_name='test-env-verbose')
            # Vérifie que le bon message de succès est loggué
            mock_logger_instance.success.assert_called_with("Auto-activation de 'test-env-verbose' réussie via le manager central.")

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager')
    def test_failed_activation_silent(self, mock_env_manager_class):
        """Test un échec d'activation en mode silencieux."""
        # Simule un code de sortie de 1 (échec) de la méthode centrale
        mock_manager_instance = mock_env_manager_class.return_value
        mock_manager_instance.activate_project_environment.return_value = 1

        result = auto_activate_env(silent=True)

        self.assertFalse(result)
        mock_manager_instance.activate_project_environment.assert_called_once_with(env_name='projet-is')

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager')
    def test_failed_activation_verbose(self, mock_env_manager_class):
        """Test un échec d'activation en mode verbeux."""
        mock_manager_instance = mock_env_manager_class.return_value
        mock_manager_instance.activate_project_environment.return_value = 1

        with patch('project_core.core_from_scripts.environment_manager.Logger') as mock_logger_class:
            mock_logger_instance = mock_logger_class.return_value
            result = auto_activate_env(env_name='bad-env', silent=False)

            self.assertFalse(result)
            mock_manager_instance.activate_project_environment.assert_called_once_with(env_name='bad-env')
            # Vérifie que le bon message d'erreur est loggué
            mock_logger_instance.error.assert_called_with("Échec de l'auto-activation de 'bad-env' via le manager central.")

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager')
    def test_exception_handling_silent(self, mock_env_manager_class):
        """Test la gestion d'une exception inattendue en mode silencieux."""
        # Simule une exception levée par la méthode centrale
        mock_manager_instance = mock_env_manager_class.return_value
        mock_manager_instance.activate_project_environment.side_effect = RuntimeError("Critical system failure")

        result = auto_activate_env(silent=True)

        self.assertFalse(result)
        mock_manager_instance.activate_project_environment.assert_called_once()

    @patch('project_core.core_from_scripts.environment_manager.EnvironmentManager')
    def test_exception_handling_verbose(self, mock_env_manager_class):
        """Test la gestion d'une exception inattendue en mode verbeux."""
        test_exception = RuntimeError("Critical system failure")
        mock_manager_instance = mock_env_manager_class.return_value
        mock_manager_instance.activate_project_environment.side_effect = test_exception

        with patch('project_core.core_from_scripts.environment_manager.Logger') as mock_logger_class:
            mock_logger_instance = mock_logger_class.return_value
            result = auto_activate_env(silent=False)

            self.assertFalse(result)
            mock_manager_instance.activate_project_environment.assert_called_once()
            # Vérifie que l'exception est bien logguée
            mock_logger_instance.error.assert_called_with(f"❌ Erreur critique dans auto_activate_env: {test_exception}", exc_info=True)


class TestEnvironmentManagerAutoActivation(unittest.TestCase):
    """Tests d'intégration pour EnvironmentManager avec auto-activation"""
    
    def setUp(self):
        """Setup pour les tests d'intégration"""
        self.original_env = os.environ.copy()
        
    def tearDown(self):
        """Cleanup après tests"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    
    @patch('shutil.which', return_value='/path/to/conda')
    def test_environment_manager_conda_check(self, mock_which):
        """Test vérification conda dans EnvironmentManager"""
        manager = EnvironmentManager()
        result = manager.check_conda_available()
        self.assertTrue(result)
        mock_which.assert_called_once_with('conda.exe')
    
    
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
    
    
    @patch('shutil.which', return_value='/path/to/conda')
    def test_concurrent_conda_checks(self, mock_which):
        """Test vérifications conda concurrentes"""
        manager = EnvironmentManager()
        results = [manager.check_conda_available() for _ in range(5)]
        self.assertTrue(all(results))
        # shutil.which a un cache interne, donc il n'est appelé qu'une fois.
        self.assertEqual(mock_which.call_count, 1)


if __name__ == '__main__':
    # Configuration pour réduire le bruit des logs pendant les tests
    import logging
    logging.getLogger().setLevel(logging.CRITICAL)
    
    # Exécution des tests
    unittest.main(verbosity=2)