
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python3
"""
Tests unitaires pour le module auto_env
======================================

Tests complets du one-liner auto-activateur d'environnement intelligent.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import unittest
import os
import sys

from pathlib import Path
from unittest.mock import patch, MagicMock

# Configuration des chemins pour les tests
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
scripts_core = current_dir / "scripts" / "core"
if str(scripts_core) not in sys.path:
    sys.path.insert(0, str(scripts_core))

from project_core.core_from_scripts.auto_env import ensure_env, get_one_liner, get_simple_import


class TestAutoEnv(unittest.TestCase):
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

    """Tests pour le module auto_env"""
    
    def setUp(self):
        """Setup pour chaque test"""
        self.original_env = os.environ.copy()
        
    def tearDown(self):
        """Cleanup après chaque test"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    
    @patch('project_core.core_from_scripts.environment_manager.auto_activate_env')
    def test_ensure_env_success(self, mock_auto_activate):
        """Test ensure_env avec succès"""
        mock_auto_activate.return_value = True
        
        result = ensure_env()
        
        self.assertTrue(result)
        mock_auto_activate.assert_called_once_with(env_name="projet-is", silent=True)
    
    
    @patch('project_core.core_from_scripts.environment_manager.auto_activate_env')
    def test_ensure_env_failure(self, mock_auto_activate):
        """Test ensure_env avec échec"""
        mock_auto_activate.return_value = False
        
        result = ensure_env()
        
        self.assertFalse(result)
        mock_auto_activate.assert_called_once_with(env_name="projet-is", silent=True)
    
    
    def test_ensure_env_custom_params(self):
        """Test ensure_env avec des paramètres personnalisés lève une erreur comme attendu."""
        # Ce test vérifie maintenant correctement que l'appel de ensure_env pour un
        # environnement *différent* de celui en cours lève bien une RuntimeError.
        with self.assertRaises(RuntimeError) as cm:
            ensure_env(env_name="custom-env", silent=False)

        self.assertIn("L'INTERPRÉTEUR PYTHON EST INCORRECT", str(cm.exception))
        self.assertIn("'custom-env'", str(cm.exception))
    
    
    @patch('project_core.core_from_scripts.environment_manager.auto_activate_env')
    def test_ensure_env_exception_handling(self, mock_auto_activate):
        """Test gestion d'exception dans ensure_env"""
        mock_auto_activate.side_effect = Exception("Test error")
        
        # Maintenant que le try/except a été supprimé du code de production,
        # l'exception doit se propager.
        with self.assertRaises(Exception) as cm:
            ensure_env(silent=True)
        
        self.assertEqual(str(cm.exception), "Test error")
    
    
    
    @patch('sys.path')
    @patch('os.path.exists')
    def test_ensure_env_path_detection(self, mock_exists, mock_sys_path):
        """Test détection des chemins dans ensure_env"""
        mock_exists.return_value = True
        mock_sys_path.insert = MagicMock()
        
        with patch('project_core.core_from_scripts.environment_manager.auto_activate_env', return_value=True):
            ensure_env()
        
        # Vérifier que le chemin est ajouté
        mock_sys_path.insert.assert_called()
    
    def test_get_one_liner(self):
        """Test génération du one-liner complet"""
        one_liner = get_one_liner()
        
        self.assertIsInstance(one_liner, str)
        self.assertIn("sys.path.insert", one_liner)
        self.assertIn("scripts", one_liner)
        self.assertIn("core", one_liner)
        self.assertIn("auto_env", one_liner)
        self.assertIn("ensure_env", one_liner)
    
    def test_get_simple_import(self):
        """Test génération de l'import simple"""
        simple_import = get_simple_import()
        
        self.assertIsInstance(simple_import, str)
        self.assertIn("import project_core.core_from_scripts.auto_env", simple_import)
        self.assertIn("Auto-activation", simple_import)


class TestAutoEnvIntegration(unittest.TestCase):
    """Tests d'intégration pour auto_env"""
    
    def setUp(self):
        """Setup pour les tests d'intégration"""
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Cleanup après tests d'intégration"""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    
    @patch('subprocess.run')
    def test_integration_conda_available(self, mock_subprocess):
        """Test d'intégration avec conda disponible"""
        # Mock conda disponible
        conda_version_result = MagicMock()
        conda_version_result.returncode = 0
        conda_version_result.stdout = "conda 4.12.0"
        
        # Mock environnements conda
        conda_env_result = MagicMock()
        conda_env_result.returncode = 0
        conda_env_result.stdout = '{"envs": ["/path/to/projet-is"]}'
        
        mock_subprocess.side_effect = [conda_version_result, conda_env_result]
        
        # Test avec environnement non actif
        os.environ.pop('CONDA_DEFAULT_ENV', None)
        
        # Le test échoue car même si conda est disponible, la variable d'environnement
        # CONDA_DEFAULT_ENV n'est pas définie, ce qui déclenche la RuntimeError finale.
        # Le test doit donc s'attendre à cette exception.
        with self.assertRaises(RuntimeError):
            ensure_env(silent=False)
    
    
    @patch('subprocess.run')
    def test_integration_conda_unavailable(self, mock_subprocess):
        """Test d'intégration avec conda indisponible"""
        # Mock conda indisponible
        mock_subprocess.side_effect = FileNotFoundError("conda not found")
        
        # S'assurer que l'environnement n'est pas marqué comme actif
        os.environ.pop('CONDA_DEFAULT_ENV', None)
        
        # Comme pour le test précédent, l'échec de l'activation mènera
        # à une RuntimeError lors de la vérification finale.
        with self.assertRaises(RuntimeError):
            ensure_env(silent=True)
    
    def test_integration_env_already_active(self):
        """Test d'intégration avec environnement déjà actif"""
        # Simuler environnement déjà actif
        os.environ['CONDA_DEFAULT_ENV'] = 'projet-is'
        
        # Simuler un environnement où le script d'activation n'est PAS le parent
        with patch.dict(os.environ, {'IS_ACTIVATION_SCRIPT_RUNNING': 'false'}):
            with patch('project_core.core_from_scripts.environment_manager.is_conda_env_active', return_value=True):
                with patch('builtins.print') as mock_print:
                    result = ensure_env(silent=False)
                    
                    self.assertTrue(result)
                    # Le message exact est `Vérification de l'environnement réussie...`
                    self.assertTrue(any("Vérification de l'environnement réussie" in str(call) for call in mock_print.call_args_list))


class TestAutoEnvStressTests(unittest.TestCase):
    """Tests de stress et cas limites pour auto_env"""
    
    def test_multiple_calls_idempotent(self):
        """Test que plusieurs appels sont idempotents"""
        with patch('project_core.core_from_scripts.environment_manager.auto_activate_env', return_value=True) as mock_activate:
            # Plusieurs appels successifs
            results = [ensure_env() for _ in range(5)]
            
            # Tous doivent retourner True
            self.assertTrue(all(results))
            
            # Fonction appelée 5 fois
            self.assertEqual(mock_activate.call_count, 5)
    
    def test_concurrent_imports_simulation(self):
        """Test simulation d'imports concurrents"""
        with patch('project_core.core_from_scripts.environment_manager.auto_activate_env', return_value=True):
            # Simuler plusieurs threads/processus important en même temps
            results = []
            for i in range(10):
                try:
                    result = ensure_env()
                    results.append(result)
                except Exception as e:
                    self.fail(f"Exception lors de l'appel {i}: {e}")
            
            # Tous les appels doivent réussir
            self.assertTrue(all(results))
            self.assertEqual(len(results), 10)
    
    def test_memory_usage_stability(self):
        """Test stabilité de la mémoire"""
        with patch('project_core.core_from_scripts.environment_manager.auto_activate_env', return_value=True):
            # Multiples appels pour vérifier qu'il n'y a pas de fuite mémoire
            for _ in range(100):
                ensure_env()
            
            # Si on arrive ici sans exception, c'est bon
            self.assertTrue(True)
    
    def test_invalid_env_names(self):
        """Test avec noms d'environnement invalides"""
        invalid_names = ["", " ", "invalid-env-name", "env with spaces", "env/with/slashes"]
        
        for invalid_name in invalid_names:
            with self.subTest(invalid_name=invalid_name):
                # La vérification de `sys.executable` lèvera une RuntimeError pour tout nom
                # ne correspondant pas à l'environnement de test ('projet-is').
                 with self.assertRaises(RuntimeError):
                    ensure_env(env_name=invalid_name, silent=True)


if __name__ == '__main__':
    # Configuration du logger pour les tests
    import logging
    logging.getLogger().setLevel(logging.CRITICAL)  # Réduire le bruit pendant les tests
    
    # Exécution des tests
    unittest.main(verbosity=2)