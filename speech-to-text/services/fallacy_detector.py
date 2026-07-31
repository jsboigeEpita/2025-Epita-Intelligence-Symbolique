#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core Fallacy Detection Service
Provides comprehensive fallacy detection with multiple detection methods
"""

import sys
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to path
current_dir = Path(__file__).parent.parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class FallacyDetectionService:
    """
    Main fallacy detection service with two-tier fallback architecture:
    1. Web API (when available and healthy)
    2. Simple Pattern Matching (always available)

    #1567 — the former tier 1 ("Advanced Services", an InformalAnalysisAgent
    bootstrapped via an ``AnalysisRunner`` import) was DEAD: the module
    ``argumentation_analysis.orchestration.analysis_runner`` was removed in
    ``d2fef7b4`` (obsolete analysis runners) and never replaced, the
    ``AnalysisRunner`` class exists in NO module, and the assigned instance
    was never read. Worse, the kernel was built with a FAKE key
    (``api_key="mock_key"``), so repairing the import alone would have
    flipped an honestly-OFF tier into a tier that LIES about being available
    then fails on the first real call (motif #1019). The branch could not be
    wired honestly without inventing a class for an unconsumed instance + a
    real key + a reachability healthcheck — a feature, not a fix, never
    requested (``SKIP_ADVANCED_SERVICES=true`` was already the config default).
    Decision: REMOVE the tier (argumented); the rejected branch (wire it) is
    documented above. Tiers web-API and pattern-matching are untouched.
    """

    def __init__(self):
        """Initialize the fallacy detection service"""
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        self.use_web_api = False
        self.web_api_detector = None
        self.api_base_url = "http://localhost:5000"

        self._initialize_services()

    def _initialize_services(self):
        """Initialize services with fallback hierarchy (web API -> pattern)."""
        # #1567: the dead "advanced services" tier (import to a removed module
        # + fake key) is gone — no try/except ImportError can mask an
        # unavailable tier here, because there is no such tier to mask. The
        # web-API tier below reports its availability honestly via its own
        # ``check_health`` (it only claims readiness when the endpoint answers).
        try:
            # Import web API detector if available
            from .web_api_client import WebAPIClient

            self.web_api_detector = WebAPIClient(self.api_base_url)

            if self.web_api_detector.check_health():
                self.use_web_api = True
                self.logger.info("Web API fallback initialized")
        except ImportError:
            self.logger.info("Web API client not available")
        except Exception as e:
            self.logger.warning(f"Web API initialization failed: {e}")

        self.is_initialized = True
        self.logger.info("Fallacy detection service initialized")

    def check_health(self) -> Dict[str, Any]:
        """Check service health and return status.

        #1567: ``advanced_services`` is no longer reported — the dead tier was
        removed, so check_health can no longer advertise a tier that would
        fail on the first real call (DoD). ``web_api`` is reported honestly
        (only True when the endpoint answered ``check_health`` at init).
        """
        return {
            "service": "fallacy_detection",
            "status": "healthy" if self.is_initialized else "unhealthy",
            "web_api": self.use_web_api,
            "pattern_matching": True,  # Always available
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def detect_fallacies(
        self, text: str, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main fallacy detection method with automatic fallback

        Args:
            text: Text to analyze
            options: Detection options (severity_threshold, include_context, etc.)

        Returns:
            Standardized analysis result
        """
        if not self.is_initialized:
            return self._create_error_response("Service not initialized")

        if options is None:
            options = {
                "severity_threshold": 0.5,
                "include_context": True,
                "max_fallacies": 10,
            }

        start_time = time.time()

        try:
            # Method 1: Web API (the advanced-services tier was removed in
            # #1567 — it was dead since d2fef7b4 and could only have lied).
            if self.use_web_api and self.web_api_detector:
                try:
                    result = self.web_api_detector.detect_fallacies(text, options)
                    processing_time = time.time() - start_time
                    result["summary"]["processing_time"] = processing_time
                    result["summary"]["analysis_method"] = "web_api"
                    return result
                except Exception as e:
                    self.logger.error(f"Web API analysis failed: {e}")

            # Method 3: Pattern Matching (always available)
            result = self._pattern_matching_analysis(text)
            processing_time = time.time() - start_time
            return self._format_result(
                result, text, processing_time, "pattern_matching", options
            )

        except Exception as e:
            self.logger.error(f"All analysis methods failed: {e}")
            processing_time = time.time() - start_time
            return self._create_error_response(f"Analysis failed: {e}", processing_time)

    def _pattern_matching_analysis(self, text: str) -> Dict[str, Any]:
        """Pattern-based fallacy detection (always available)"""
        fallacies = []
        text_lower = text.lower()

        patterns = {
            "Ad Hominem": {
                "keywords": ["idiot", "stupide", "imbécile", "crétin", "nul"],
                "confidence": 0.70,
            },
            "False Dilemma": {
                "keywords": ["soit", "ou bien", "seulement deux", "pas d'autre choix"],
                "confidence": 0.65,
            },
            "Hasty Generalization": {
                "keywords": ["tous", "toutes", "toujours", "jamais", "aucun"],
                "confidence": 0.60,
            },
            "Appeal to Authority": {
                "keywords": [
                    "expert dit",
                    "scientifique affirme",
                    "selon les spécialistes",
                ],
                "confidence": 0.65,
            },
        }

        for fallacy_type, pattern_info in patterns.items():
            for keyword in pattern_info["keywords"]:
                if keyword in text_lower:
                    position = text_lower.find(keyword)
                    fallacies.append(
                        {
                            "type": fallacy_type,
                            "name": fallacy_type,
                            "confidence": pattern_info["confidence"],
                            "description": f"Pattern detection: {keyword}",
                            "start_position": position,
                            "end_position": position + len(keyword),
                            "context": text[max(0, position - 30) : position + 50],
                            "severity": "medium",
                        }
                    )
                    break

        return {"fallacies": fallacies, "analysis_method": "pattern_matching"}

    def _format_result(
        self,
        result: Dict[str, Any],
        text: str,
        processing_time: float,
        method: str,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Format analysis result to standard format"""
        fallacies = result.get("fallacies", [])
        total_fallacies = len(fallacies)

        # Generate recommendations
        recommendations = self._generate_recommendations(fallacies, total_fallacies)

        return {
            "status": "success",
            "text_length": len(text),
            "fallacies_detected": fallacies,
            "summary": {
                "total_fallacies": total_fallacies,
                "unique_fallacy_types": len(set([f["type"] for f in fallacies])),
                "fallacy_types_found": list(set([f["type"] for f in fallacies])),
                "overall_quality": self._assess_quality(total_fallacies),
                "processing_time": processing_time,
                "analysis_method": method,
            },
            "recommendations": recommendations,
            "metadata": {
                "service": "fallacy_detection",
                "options_used": options,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

    def _generate_recommendations(
        self, fallacies: List[Dict[str, Any]], total_fallacies: int
    ) -> List[str]:
        """Generate recommendations based on detected fallacies"""
        recommendations = []

        if total_fallacies == 0:
            recommendations.append("✅ Excellent! No major fallacies detected.")
            return recommendations

        fallacy_types = [f["type"] for f in fallacies]

        if "Ad Hominem" in fallacy_types:
            recommendations.append("🎯 Avoid personal attacks - focus on the argument.")

        if "False Dilemma" in fallacy_types:
            recommendations.append(
                "🔍 Look for alternative options beyond binary choices."
            )

        if "Hasty Generalization" in fallacy_types:
            recommendations.append(
                "📊 Be careful with generalizations - seek more evidence."
            )

        if "Appeal to Authority" in fallacy_types:
            recommendations.append(
                "🧐 Question authority claims - ask for concrete evidence."
            )

        if total_fallacies > 3:
            recommendations.append("💡 Consider restructuring the entire argument.")
        elif total_fallacies > 1:
            recommendations.append("🔄 Strengthen the logical flow of your argument.")

        return recommendations

    def _assess_quality(self, total_fallacies: int) -> str:
        """Assess argument quality based on fallacy count"""
        if total_fallacies == 0:
            return "excellent"
        elif total_fallacies <= 1:
            return "good"
        elif total_fallacies <= 3:
            return "moderate"
        else:
            return "poor"

    def _create_error_response(
        self, error_message: str, processing_time: float = 0.0
    ) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "status": "error",
            "error_message": error_message,
            "text_length": 0,
            "fallacies_detected": [],
            "summary": {
                "total_fallacies": 0,
                "unique_fallacy_types": 0,
                "fallacy_types_found": [],
                "overall_quality": "unknown",
                "processing_time": processing_time,
                "analysis_method": "error",
            },
            "recommendations": ["Please resolve technical issues before proceeding."],
            "metadata": {
                "service": "fallacy_detection",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": error_message,
            },
        }


# Singleton instance for the service
_service_instance = None


def get_fallacy_detection_service() -> FallacyDetectionService:
    """Get or create the fallacy detection service singleton"""
    global _service_instance
    if _service_instance is None:
        _service_instance = FallacyDetectionService()
    return _service_instance
