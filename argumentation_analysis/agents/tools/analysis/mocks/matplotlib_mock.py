"""
Mock pour matplotlib - Sprint 3
Évite les imports circulaires critiques
"""

import sys
from unittest.mock import MagicMock

class MockPyplot:
    """Mock simple pour pyplot"""
    
    def __init__(self):
        self.figure = MagicMock()
        self.subplot = MagicMock()
        self.plot = MagicMock()
        self.scatter = MagicMock()
        self.title = MagicMock()
        self.xlabel = MagicMock()
        self.ylabel = MagicMock()
        self.legend = MagicMock()
        self.show = MagicMock()
        self.savefig = MagicMock()
        self.close = MagicMock()
        self.subplots = MagicMock(return_value=(MagicMock(), MagicMock()))

# Remplacer matplotlib temporairement
if 'matplotlib.pyplot' not in sys.modules:
    sys.modules['matplotlib.pyplot'] = type(sys)('matplotlib.pyplot')
    sys.modules['matplotlib.pyplot'].plt = MockPyplot()

plt = MockPyplot()

print("[OK] Mock matplotlib appliqué pour éviter l'import circulaire")
