"""
Services package for fallacy detection system.

This package contains all the core business logic and services:
- FallacyDetectionService: Main service for detecting fallacies
- WebAPIClient: Client for external API integration  
- SimpleFallacyDetector: Simple pattern-based detector
- WebAPIFallacyDetector: Advanced web API detector
"""

from .fallacy_detector import FallacyDetectionService, get_fallacy_detection_service
from .web_api_client import WebAPIClient

try:
    from .simple_fallacy_detector import SimpleFallacyDetector
except ImportError:
    SimpleFallacyDetector = None

try:
    from .web_api_fallacy_detector import WebAPIFallacyDetector
except ImportError:
    WebAPIFallacyDetector = None

__all__ = [
    "FallacyDetectionService",
    "get_fallacy_detection_service",
    "WebAPIClient",
    "SimpleFallacyDetector",
    "WebAPIFallacyDetector",
]
