"""
Mock pour PyTorch dans les tests d'intégration
Évite les erreurs de chargement de torch_python.dll
"""

import sys
from unittest.mock import MagicMock

def mock_torch():
    """Configure un mock pour torch si le module n'est pas disponible"""
    if 'torch' not in sys.modules:
        # Créer un mock pour torch
        torch_mock = MagicMock()
        torch_mock.__version__ = "2.0.0"
        
        # Mock des classes essentielles
        torch_mock.nn = MagicMock()
        torch_mock.nn.Module = MagicMock
        torch_mock.optim = MagicMock()
        torch_mock.cuda = MagicMock()
        torch_mock.cuda.is_available = MagicMock(return_value=False)
        
        # Mock des fonctions de base
        torch_mock.tensor = MagicMock()
        torch_mock.zeros = MagicMock()
        torch_mock.ones = MagicMock()
        torch_mock.randn = MagicMock()
        
        # Mock de transformers si nécessaire
        transformers_mock = MagicMock()
        transformers_mock.AutoTokenizer = MagicMock()
        transformers_mock.AutoModel = MagicMock()
        
        # Injecter les mocks dans sys.modules
        sys.modules['torch'] = torch_mock
        sys.modules['transformers'] = transformers_mock
        
        return True
    return False

# Auto-configuration au moment de l'import
mock_torch()