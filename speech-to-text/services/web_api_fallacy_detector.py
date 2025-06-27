"""
Web API Fallacy Detector for Speech-to-Text Integration
This script uses the real argumentation analysis web API services
"""

import json
import requests
import time
from typing import Dict, Any, Optional
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebAPIFallacyDetector:
    """
    Fallacy detector that uses the argumentation analysis web API
    """
    
    def __init__(self, api_base_url: str = "http://127.0.0.1:5000"):
        """
        Initialize the web API fallacy detector
        
        Args:
            api_base_url (str): Base URL of the argumentation analysis API
        """
        self.api_base_url = api_base_url
        self.fallacies_endpoint = f"{api_base_url}/api/fallacies"
        self.health_endpoint = f"{api_base_url}/api/health"
        self.analyze_endpoint = f"{api_base_url}/api/analyze"
        
    def check_api_health(self) -> bool:
        """
        Check if the API is healthy and running
        
        Returns:
            bool: True if API is healthy, False otherwise
        """
        try:
            response = requests.get(self.health_endpoint, timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"API Health Status: {health_data.get('status', 'unknown')}")
                return health_data.get('status') == 'healthy'
            return False
        except Exception as e:
            logger.error(f"Failed to check API health: {e}")
            return False
    
    def detect_fallacies_web_api(self, text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Detect fallacies using the web API
        
        Args:
            text (str): Text to analyze for fallacies
            options (dict, optional): Options for fallacy detection
            
        Returns:
            dict: Analysis results from the web API
        """
        if options is None:
            options = {
                "severity_threshold": 0.5,
                "include_context": True,
                "max_fallacies": 10
            }
        
        payload = {
            "text": text,
            "options": options
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            logger.info("Sending request to fallacy detection API...")
            response = requests.post(
                self.fallacies_endpoint, 
                headers=headers, 
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully detected {len(result.get('fallacies', []))} fallacies")
                return self._standardize_response(result)
            else:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                return self._create_error_response(f"API error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return self._create_error_response(f"Request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return self._create_error_response(f"Unexpected error: {e}")
    
    def analyze_text_complete(self, text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform complete text analysis including fallacy detection
        
        Args:
            text (str): Text to analyze
            options (dict, optional): Analysis options
            
        Returns:
            dict: Complete analysis results
        """
        if options is None:
            options = {
                "detect_fallacies": True,
                "analyze_structure": True,
                "evaluate_coherence": True,
                "include_context": True,
                "severity_threshold": 0.5
            }
        
        payload = {
            "text": text,
            "options": options
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            logger.info("Sending request to complete analysis API...")
            response = requests.post(
                self.analyze_endpoint, 
                headers=headers, 
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Complete analysis completed successfully")
                return self._standardize_analysis_response(result)
            else:
                logger.error(f"API returned status {response.status_code}: {response.text}")
                return self._create_error_response(f"Analysis API error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Analysis request failed: {e}")
            return self._create_error_response(f"Analysis request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected analysis error: {e}")
            return self._create_error_response(f"Unexpected analysis error: {e}")
    
    def _standardize_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize the API response to match our expected format
        
        Args:
            api_response (dict): Raw API response
            
        Returns:
            dict: Standardized response
        """
        fallacies = api_response.get('fallacies', [])
        
        # Convert API fallacies to our standard format
        standardized_fallacies = []
        for fallacy in fallacies:
            standardized_fallacy = {
                "type": fallacy.get('type', 'Unknown'),
                "confidence": fallacy.get('confidence', 0.5),
                "text_span": fallacy.get('text_span', ''),
                "start_position": fallacy.get('position', {}).get('start', 0),
                "end_position": fallacy.get('position', {}).get('end', 0),
                "description": fallacy.get('description', ''),
                "severity": fallacy.get('severity', 'medium'),
                "context": fallacy.get('context', '')
            }
            standardized_fallacies.append(standardized_fallacy)
        
        # Calculate summary statistics
        total_fallacies = len(standardized_fallacies)
        fallacy_types = list(set([f["type"] for f in standardized_fallacies]))
        
        # Generate recommendations based on detected fallacies
        recommendations = self._generate_recommendations(fallacy_types, total_fallacies)
        
        return {
            "status": "success",
            "text_length": len(api_response.get('text', '')),
            "fallacies_detected": standardized_fallacies,
            "summary": {
                "total_fallacies": total_fallacies,
                "unique_fallacy_types": len(fallacy_types),
                "fallacy_types_found": fallacy_types,
                "overall_quality": self._assess_quality(total_fallacies),
                "processing_time": api_response.get('processing_time', 0),
                "api_version": "web_api"
            },
            "recommendations": recommendations,
            "raw_api_response": api_response  # Keep original for debugging
        }
    
    def _standardize_analysis_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize complete analysis response
        
        Args:
            api_response (dict): Raw analysis API response
            
        Returns:
            dict: Standardized analysis response
        """
        fallacies = api_response.get('fallacies', {}).get('detected', [])
        structure = api_response.get('structure', {})
        coherence = api_response.get('coherence', {})
        
        # Process fallacies using the same logic
        fallacy_response = self._standardize_response({'fallacies': fallacies, 'text': api_response.get('text', '')})
        
        # Add structure and coherence information
        fallacy_response['structure_analysis'] = structure
        fallacy_response['coherence_analysis'] = coherence
        fallacy_response['summary']['structure_score'] = structure.get('score', 0)
        fallacy_response['summary']['coherence_score'] = coherence.get('score', 0)
        
        return fallacy_response
    
    def _generate_recommendations(self, fallacy_types: list, total_fallacies: int) -> list:
        """
        Generate recommendations based on detected fallacies
        
        Args:
            fallacy_types (list): List of detected fallacy types
            total_fallacies (int): Total number of fallacies
            
        Returns:
            list: List of recommendations
        """
        recommendations = []
        
        if total_fallacies == 0:
            recommendations.append("Excellent logical structure with no fallacies detected")
            return recommendations
        
        # General recommendation
        recommendations.append("Consider reviewing the logical structure of your arguments")
        
        # Specific recommendations based on fallacy types
        fallacy_recommendations = {
            "Ad Hominem": "Focus on addressing arguments rather than attacking the person",
            "Straw Man": "Ensure you're addressing the actual argument, not a distorted version",
            "False Dilemma": "Consider whether there are more than two options available",
            "Slippery Slope": "Evaluate whether the consequences you describe are truly inevitable",
            "Appeal to Authority": "Verify that cited authorities are relevant and credible",
            "Appeal to Emotion": "Support emotional appeals with logical reasoning",
            "Bandwagon": "Consider whether popularity makes something true or correct",
            "Circular Reasoning": "Ensure your premises don't simply restate your conclusion",
            "Hasty Generalization": "Consider whether your sample size supports your general conclusion"
        }
        
        for fallacy_type in fallacy_types:
            if fallacy_type in fallacy_recommendations:
                recommendations.append(fallacy_recommendations[fallacy_type])
        
        return recommendations
    
    def _assess_quality(self, total_fallacies: int) -> str:
        """
        Assess overall argument quality based on fallacy count
        
        Args:
            total_fallacies (int): Number of detected fallacies
            
        Returns:
            str: Quality assessment
        """
        if total_fallacies == 0:
            return "excellent"
        elif total_fallacies <= 2:
            return "good"
        elif total_fallacies <= 5:
            return "moderate"
        else:
            return "poor"
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Create a standardized error response
        
        Args:
            error_message (str): Error message
            
        Returns:
            dict: Error response
        """
        return {
            "status": "error",
            "error": error_message,
            "fallacies_detected": [],
            "summary": {
                "total_fallacies": 0,
                "unique_fallacy_types": 0,
                "fallacy_types_found": [],
                "overall_quality": "unknown"
            },
            "recommendations": ["Unable to analyze due to API error"]
        }

def main():
    """Test the web API fallacy detector"""
    print("🌐 Testing Web API Fallacy Detector...")
    
    detector = WebAPIFallacyDetector()
    
    # Check API health first
    print("\n🔍 Checking API health...")
    if not detector.check_api_health():
        print("❌ API is not healthy. Please start the argumentation analysis API first.")
        print("💡 Run: cd argumentation_analysis/services/web_api && python start_api.py")
        return False
    
    print("✅ API is healthy and ready!")
    
    # Sample text with multiple fallacies
    sample_text = """
    Everyone knows that climate change is a hoax because my neighbor said so, 
    and he's a very smart person. Besides, if climate change were real, 
    then why was it cold last winter? Also, all scientists are just trying 
    to get research funding, so you can't trust anything they say. 
    We shouldn't change our lifestyle based on these false claims.
    """
    
    print("\n" + "="*60)
    print("📝 SAMPLE TEXT FOR WEB API ANALYSIS")
    print("="*60)
    print(sample_text.strip())
    
    print(f"\n📊 Text length: {len(sample_text)} characters")
    
    # Analyze for fallacies using web API
    print("\n" + "="*60)
    print("🔍 WEB API FALLACY ANALYSIS")
    print("="*60)
    print("Analyzing text using real argumentation analysis API...")
    
    start_time = time.time()
    analysis_result = detector.detect_fallacies_web_api(sample_text)
    end_time = time.time()
    
    print(f"\n⏱️ Analysis completed in {end_time - start_time:.2f} seconds")
    print("\n📋 Web API Fallacy Analysis Results:")
    print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
    
    if analysis_result['status'] == 'success':
        print(f"\n✅ Analysis completed successfully!")
        print(f"📊 Found {analysis_result['summary']['total_fallacies']} fallacies")
        print(f"📈 Overall quality: {analysis_result['summary']['overall_quality']}")
        
        if analysis_result['fallacies_detected']:
            print("\n🚨 Detected Fallacies:")
            for i, fallacy in enumerate(analysis_result['fallacies_detected'], 1):
                print(f"  {i}. {fallacy['type']}: '{fallacy['text_span']}' (confidence: {fallacy['confidence']:.2f})")
        
        if analysis_result['recommendations']:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(analysis_result['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "="*60)
        print("✅ WEB API INTEGRATION TEST SUCCESSFUL")
        print("="*60)
        print("The speech-to-text to web API fallacy analysis pipeline is working!")
    else:
        print("❌ Analysis failed:", analysis_result.get('error', 'Unknown error'))
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 