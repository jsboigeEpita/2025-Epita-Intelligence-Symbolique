#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Web API Client for Fallacy Detection
Handles communication with external fallacy detection APIs
"""

import requests
import time
import logging
from typing import Dict, Any, Optional

class WebAPIClient:
    """
    Client for communicating with web-based fallacy detection APIs
    """
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        Initialize the web API client
        
        Args:
            base_url: Base URL for the API server
        """
        self.base_url = base_url.rstrip('/')
        self.logger = logging.getLogger(__name__)
        self.timeout = 30
        
    def check_health(self) -> bool:
        """
        Check if the API server is healthy
        
        Returns:
            bool: True if server is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/health",
                timeout=self.timeout
            )
            return response.status_code == 200
            
        except requests.RequestException as e:
            self.logger.warning(f"Health check failed: {e}")
            return False
    
    def detect_fallacies(self, text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Detect fallacies using the web API
        
        Args:
            text: Text to analyze
            options: Detection options
            
        Returns:
            Analysis result from the API
        """
        if options is None:
            options = {
                "severity_threshold": 0.5,
                "include_context": True,
                "max_fallacies": 10
            }
        
        try:
            payload = {
                "text": text,
                "options": options
            }
            
            response = requests.post(
                f"{self.base_url}/api/fallacies",
                json=payload,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"API returned status {response.status_code}"
                try:
                    error_detail = response.json().get("error", error_msg)
                except:
                    error_detail = error_msg
                    
                return self._create_error_response(error_detail)
                
        except requests.RequestException as e:
            self.logger.error(f"Web API request failed: {e}")
            return self._create_error_response(f"API request failed: {str(e)}")
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
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
                "processing_time": 0.0,
                "analysis_method": "web_api_error"
            },
            "recommendations": ["Please check API server status."],
            "metadata": {
                "service": "web_api",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": error_message
            }
        } 