import project_core.core_from_scripts.auto_env
#!/usr/bin/env python3
"""
Runner de test alternatif à pytest
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock

# Configuration des mocks globaux
sys.modules['pytest'] = Mock()
sys.modules['jpype'] = Mock()

def run_all_tests():
    """Exécute tous les tests disponibles"""
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\nRésultats: {result.testsRun} tests, {len(result.failures)} échecs, {len(result.errors)} erreurs")
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
