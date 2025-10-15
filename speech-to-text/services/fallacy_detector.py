#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Core Fallacy Detection Service
Provides comprehensive fallacy detection with multiple detection methods
"""

import sys
import os
import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
current_dir = Path(__file__).parent.parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class FallacyDetectionService:
    """
    Main fallacy detection service with three-tier fallback architecture:
    1. Advanced Services (InformalAnalysisAgent)
    2. Web API (when available)
    3. Simple Pattern Matching (always available)
    """

    def __init__(self):
        """Initialize the fallacy detection service"""
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        self.use_advanced_services = False
        self.use_web_api = False
        self.informal_agent = None
        self.analysis_runner = None
        self.web_api_detector = None
        self.api_base_url = "http://localhost:5000"

        self._initialize_services()

    def _initialize_services(self):
        """Initialize services with fallback hierarchy"""
        # Check if advanced services should be skipped
        skip_advanced = os.environ.get("SKIP_ADVANCED_SERVICES", "").lower() == "true"

        if skip_advanced:
            self.logger.info("Skipping advanced services (SKIP_ADVANCED_SERVICES=true)")
        else:
            # Try advanced services first
            try:
                from argumentation_analysis.agents.core.informal.informal_agent import (
                    InformalAnalysisAgent,
                )
                from argumentation_analysis.orchestration.analysis_runner import (
                    AnalysisRunner,
                )
                import semantic_kernel as sk
                from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

                kernel = sk.Kernel()
                mock_llm_service = OpenAIChatCompletion(
                    service_id="mock_openai",
                    ai_model_id="gpt-3.5-turbo",
                    api_key="mock_key",
                )
                kernel.add_service(mock_llm_service)

                self.informal_agent = InformalAnalysisAgent(
                    kernel=kernel, agent_name="fallacy_detection_service"
                )
                self.informal_agent.setup_agent_components(mock_llm_service.service_id)
                self.analysis_runner = AnalysisRunner()

                self.use_advanced_services = True
                self.logger.info("Advanced services initialized successfully")

            except ImportError as e:
                self.logger.warning(f"Advanced services not available: {e}")

            except Exception as e:
                self.logger.warning(f"Error initializing advanced services: {e}")

        # Try web API fallback
        if not self.use_advanced_services:
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
        """Check service health and return status"""
        return {
            "service": "fallacy_detection",
            "status": "healthy" if self.is_initialized else "unhealthy",
            "advanced_services": self.use_advanced_services,
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
            # Method 1: Advanced Services
            if self.use_advanced_services and self.informal_agent:
                try:
                    result = self._run_advanced_analysis(text)
                    processing_time = time.time() - start_time
                    return self._format_result(
                        result, text, processing_time, "advanced_services", options
                    )
                except Exception as e:
                    self.logger.error(f"Advanced analysis failed: {e}")

            # Method 2: Web API
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

    def _run_advanced_analysis(self, text: str) -> Dict[str, Any]:
        """Run analysis using advanced services with async handling"""
        try:
            # Handle async/await properly
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, self._async_advanced_analysis(text)
                        )
                        return future.result(timeout=30)
                else:
                    return loop.run_until_complete(self._async_advanced_analysis(text))
            except RuntimeError:
                return asyncio.run(self._async_advanced_analysis(text))

        except Exception as e:
            self.logger.error(f"Advanced analysis error: {e}")
            # Fallback to pattern matching
            return self._pattern_matching_analysis(text)

    async def _async_advanced_analysis(self, text: str) -> Dict[str, Any]:
        """Async advanced analysis using InformalAnalysisAgent"""
        try:
            plugin = self.informal_agent.sk_kernel.plugins.get("InformalAnalyzer")
            if not plugin:
                return {"error": "InformalAnalyzer plugin not found"}

            available_functions = list(plugin.functions.keys())
            self.logger.info(f"Available functions: {available_functions}")

            # Try semantic analysis first
            if "semantic_AnalyzeFallacies" in available_functions:
                try:
                    from semantic_kernel.functions import KernelArguments

                    arguments = KernelArguments(input=text)

                    result = await self.informal_agent.sk_kernel.invoke(
                        plugin_name="InformalAnalyzer",
                        function_name="semantic_AnalyzeFallacies",
                        arguments=arguments,
                    )

                    analysis_text = str(result.value) if result and result.value else ""
                    fallacies = self._parse_semantic_analysis(analysis_text)

                    return {
                        "fallacies": fallacies,
                        "analysis_method": "semantic_analysis",
                        "raw_analysis": analysis_text,
                    }

                except Exception as e:
                    self.logger.error(f"Semantic analysis failed: {e}")

            # Fallback to pattern matching with advanced service context
            fallacies = self._pattern_matching_analysis(text)["fallacies"]
            return {
                "fallacies": fallacies,
                "analysis_method": "advanced_services_with_pattern_matching",
                "taxonomy_available": True,
            }

        except Exception as e:
            self.logger.error(f"Async analysis error: {e}")
            return {"error": f"Analysis failed: {str(e)}"}

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

    def _parse_semantic_analysis(self, analysis_text: str) -> List[Dict[str, Any]]:
        """Parse semantic analysis results"""
        fallacies = []

        if not analysis_text.strip():
            return fallacies

        lines = analysis_text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if any(
                keyword in line.lower()
                for keyword in ["fallacy", "sophisme", "erreur logique"]
            ):
                fallacies.append(
                    {
                        "type": "Semantic Detection",
                        "name": "Detected Fallacy",
                        "confidence": 0.75,
                        "description": line,
                        "start_position": 0,
                        "end_position": 0,
                        "context": "semantic analysis",
                        "severity": "medium",
                    }
                )

        return fallacies

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
