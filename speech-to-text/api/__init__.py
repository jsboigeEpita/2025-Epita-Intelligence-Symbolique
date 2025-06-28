"""
API package for fallacy detection system.

This package contains the REST API endpoints and related functionality:
- fallacy_api: Main Flask API application
- rest_endpoints: Additional REST endpoints
- mock_api_server: Mock server for testing
"""

from .fallacy_api import app

try:
    from .mock_api_server import MockAPIServer
except ImportError:
    MockAPIServer = None

__all__ = [
    'app',
    'MockAPIServer'
] 