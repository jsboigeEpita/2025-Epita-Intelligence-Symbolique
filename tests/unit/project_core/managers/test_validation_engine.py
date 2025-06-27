import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Adjust the path to import the module under test
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from project_core.core_from_scripts.validation_engine import ValidationEngine

class TestValidationEngine(unittest.TestCase):
    """
    Unit tests for the ValidationEngine class.
    """

    def setUp(self):
        """Set up for each test."""
        self.engine = ValidationEngine()

    @patch('sys.platform', 'win32')
    @patch('pathlib.Path.exists')
    def test_validate_build_tools_found(self, mock_exists):
        """
        Test that build tools validation succeeds when vcvarsall.bat is found.
        """
        mock_exists.return_value = True
        result = self.engine.validate_build_tools()
        self.assertEqual(result['status'], 'success')
        self.assertIn('Outils de compilation trouvés', result['message'])

    @patch('sys.platform', 'win32')
    @patch('pathlib.Path.exists')
    def test_validate_build_tools_not_found(self, mock_exists):
        """
        Test that build tools validation fails when vcvarsall.bat is not found.
        """
        mock_exists.return_value = False
        result = self.engine.validate_build_tools()
        self.assertEqual(result['status'], 'failure')
        self.assertIn('semblent manquer', result['message'])

    @patch('sys.platform', 'linux')
    def test_validate_build_tools_skipped_on_non_windows(self):
        """
        Test that build tools validation is skipped on non-Windows platforms.
        """
        result = self.engine.validate_build_tools()
        self.assertEqual(result['status'], 'skipped')

    @patch('importlib.import_module')
    def test_validate_jvm_bridge_success(self, mock_import):
        """
        Test validation of JVM bridge when jpype is installed.
        """
        mock_import.return_value = MagicMock()
        result = self.engine.validate_jvm_bridge()
        self.assertEqual(result['status'], 'success')

    @patch('importlib.import_module', side_effect=ImportError)
    def test_validate_jvm_bridge_failure(self, mock_import):
        """
        Test validation of JVM bridge when jpype is not installed.
        """
        result = self.engine.validate_jvm_bridge()
        self.assertEqual(result['status'], 'failure')

if __name__ == '__main__':
    unittest.main()
