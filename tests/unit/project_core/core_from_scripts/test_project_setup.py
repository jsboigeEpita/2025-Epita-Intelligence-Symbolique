"""
Tests unitaires pour le ProjectSetup.
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import logging

from project_core.core_from_scripts.project_setup import ProjectSetup

# Désactiver le logging pour les tests
logging.disable(logging.CRITICAL)

class TestProjectSetup(unittest.TestCase):
    """Suite de tests pour le ProjectSetup."""

    def setUp(self):
        """Configuration initiale pour chaque test."""
        self.logger = logging.getLogger(__name__)
        self.setup = ProjectSetup(logger=self.logger)

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.is_dir', return_value=True)
    @patch('site.getsitepackages', return_value=['/fake/site-packages'])
    def test_set_project_path_file_with_getsitepackages(self, mock_getsitepackages, mock_is_dir, mock_file):
        """Teste la création réussie du .pth via site.getsitepackages."""
        result = self.setup.set_project_path_file()

        self.assertTrue(result)
        mock_file.assert_called_once_with(Path('/fake/site-packages/argumentation_analysis_project.pth'), 'w')

    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.is_dir', return_value=True)
    @patch('site.getusersitepackages', return_value='/fake/user-site-packages')
    @patch('site.getsitepackages', return_value=[])
    def test_set_project_path_file_fallback_to_getusersitepackages(self, mock_getsitepackages, mock_getusersitepackages, mock_is_dir, mock_file):
        """Teste la création réussie du .pth via le fallback sur site.getusersitepackages."""
        result = self.setup.set_project_path_file()

        self.assertTrue(result)
        mock_file.assert_called_once_with(Path('/fake/user-site-packages/argumentation_analysis_project.pth'), 'w')

    @patch('site.getsitepackages', return_value=[])
    @patch('site.getusersitepackages', return_value=None)
    def test_set_project_path_file_no_site_packages_found(self, mock_getusersitepackages, mock_getsitepackages):
        """Teste l'échec lorsque aucun répertoire site-packages n'est trouvé."""
        result = self.setup.set_project_path_file()
        self.assertFalse(result)
        mock_getsitepackages.assert_called_once()
        mock_getusersitepackages.assert_called_once()

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)