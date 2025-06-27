import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from project_core.core_from_scripts.project_setup import ProjectSetup

class TestProjectSetup(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.mock_logger = MagicMock()
        self.setup = ProjectSetup(logger=self.mock_logger)
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent

    @patch('pathlib.Path.is_dir', return_value=True)
    @patch('site.getsitepackages', return_value=['/fake/site-packages'])
    @patch('builtins.open', new_callable=mock_open)
    def test_set_project_path_file_success(self, mock_file, mock_get_site_packages, mock_is_dir):
        """Test successful creation of the .pth file."""
        # Setup
        mock_site_packages_path = Path('/fake/site-packages')
        
        # Action
        result = self.setup.set_project_path_file()

        # Assertions
        self.assertTrue(result)
        mock_get_site_packages.assert_called_once()

        expected_pth_path = mock_site_packages_path / 'argumentation_analysis_project.pth'
        mock_file.assert_called_once_with(expected_pth_path, 'w')

        # La racine du projet est calculée depuis project_setup.py, donc nous devons la recalculer de la même manière.
        code_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        
        handle = mock_file()
        handle.write.assert_called_once_with(str(code_root))
        
        self.mock_logger.info.assert_any_call(f"Création/Mise à jour du fichier .pth : {expected_pth_path}")
        self.mock_logger.info.assert_any_call(f"Le fichier '{expected_pth_path.name}' a été configuré avec succès.")

    @patch('site.getsitepackages', return_value=[])
    @patch('site.getusersitepackages', return_value=None)
    def test_set_project_path_file_failure_no_site_packages(self, mock_get_user_site_packages, mock_get_site_packages):
        """Test failure when site-packages directory cannot be determined."""
        # Action
        result = self.setup.set_project_path_file()

        # Assertions
        self.assertFalse(result)
        self.mock_logger.error.assert_called_with("Impossible de déterminer le répertoire site-packages, même avec getusersitepackages.")

if __name__ == '__main__':
    unittest.main()