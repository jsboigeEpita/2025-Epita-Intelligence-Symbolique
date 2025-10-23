#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple integration test for the cleaned up fallacy detection system
"""

import sys
import time
import pytest
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from services.fallacy_detector import get_fallacy_detection_service


@pytest.mark.skip(
    reason="Test étudiant. De plus, problème de PYTHONPATH ou __init__.py manquant, à corriger."
)
def test_fallacy_detection_service():
    """Test the core fallacy detection service"""
    print("🧪 Testing Fallacy Detection Service...")

    # Get the service
    service = get_fallacy_detection_service()

    # Check health
    health = service.check_health()
    print(f"Service health: {health}")
    assert health["status"] == "ok"

    # Test sample text
    sample_text = """
    Le réchauffement climatique est un mensonge parce que les scientifiques sont tous des idiots.
    Soit on arrête toute l'industrie, soit la planète va mourir.
    """

    print("\n📝 Testing with sample text:")
    print(sample_text.strip())

    # Detect fallacies
    start_time = time.time()
    result = service.detect_fallacies(sample_text)
    end_time = time.time()

    print("\n📊 Results:")
    print(f"Status: {result['status']}")
    print(f"Total fallacies: {result['summary']['total_fallacies']}")
    print(f"Processing time: {end_time - start_time:.2f}s")
    print(f"Analysis method: {result['summary']['analysis_method']}")
    print(f"Overall quality: {result['summary']['overall_quality']}")

    if result["fallacies_detected"]:
        print("\n🚨 Detected Fallacies:")
        for i, fallacy in enumerate(result["fallacies_detected"], 1):
            print(f"  {i}. {fallacy['name']} (confidence: {fallacy['confidence']:.2f})")
            print(f"     {fallacy['description']}")

    if result["recommendations"]:
        print("\n💡 Recommendations:")
        for i, rec in enumerate(result["recommendations"], 1):
            print(f"  {i}. {rec}")

    print("\n✅ Service test completed!")
    assert result["status"] == "success"
