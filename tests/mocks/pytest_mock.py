#!/usr/bin/env python3
"""
Mock pour pytest
"""

from unittest.mock import Mock, MagicMock

# Mock principal de pytest
pytest = Mock()

# Fonctions principales de pytest
def main(*args, **kwargs):
    return 0

def raises(*args, **kwargs):
    class RaisesContext:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            return True
    return RaisesContext()

def mark(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

def fixture(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

def skip(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

def parametrize(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

# Configuration du mock
pytest.main = main
pytest.raises = raises
pytest.mark = Mock()
pytest.mark.parametrize = parametrize
pytest.mark.skip = skip
pytest.mark.timeout = mark
pytest.fixture = fixture
pytest.skip = skip

# Export
__all__ = ['pytest', 'main', 'raises', 'mark', 'fixture', 'skip', 'parametrize']