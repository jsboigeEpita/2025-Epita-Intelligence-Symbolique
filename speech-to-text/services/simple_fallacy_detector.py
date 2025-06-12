"""
Simple Fallacy Detector for Testing Integration
This script provides a mock fallacy detection service for testing purposes
"""

import json
import re
from typing import List, Dict, Any

def detect_fallacies_simple(text: str) -> Dict[str, Any]:
    """
    Simple fallacy detection using pattern matching.
    This is a mock implementation for testing purposes.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        dict: Analysis results with detected fallacies
    """
    
    fallacies_detected = []
    
    # Define simple patterns for common fallacies
    fallacy_patterns = {
        "Ad Hominem": [
            r"you can't trust.*because.*person",
            r"he's.*so.*can't.*trust",
            r"scientists.*just.*trying.*get.*funding"
        ],
        "Appeal to Authority": [
            r"everyone knows",
            r"my.*said so.*smart person",
            r"neighbor said.*very smart"
        ],
        "False Cause": [
            r"if.*were.*then why",
            r"because.*was.*last.*winter"
        ],
        "Hasty Generalization": [
            r"all.*are.*just",
            r"everyone.*is"
        ],
        "Straw Man": [
            r"based on.*false claims",
            r"these.*claims"
        ]
    }
    
    # Check for each fallacy pattern
    for fallacy_type, patterns in fallacy_patterns.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                fallacies_detected.append({
                    "type": fallacy_type,
                    "confidence": 0.8,
                    "text_span": match.group(),
                    "start_position": match.start(),
                    "end_position": match.end(),
                    "description": f"Detected {fallacy_type} pattern",
                    "severity": "medium"
                })
    
    # Calculate overall analysis
    total_fallacies = len(fallacies_detected)
    fallacy_types = list(set([f["type"] for f in fallacies_detected]))
    
    analysis_result = {
        "status": "success",
        "text_length": len(text),
        "fallacies_detected": fallacies_detected,
        "summary": {
            "total_fallacies": total_fallacies,
            "unique_fallacy_types": len(fallacy_types),
            "fallacy_types_found": fallacy_types,
            "overall_quality": "poor" if total_fallacies > 3 else "moderate" if total_fallacies > 1 else "good"
        },
        "recommendations": [
            "Consider providing evidence for claims" if total_fallacies > 0 else "Good logical structure",
            "Avoid personal attacks" if "Ad Hominem" in fallacy_types else None,
            "Question authority claims" if "Appeal to Authority" in fallacy_types else None,
            "Check causal relationships" if "False Cause" in fallacy_types else None
        ]
    }
    
    # Remove None recommendations
    analysis_result["recommendations"] = [r for r in analysis_result["recommendations"] if r is not None]
    
    return analysis_result

def main():
    """Test the simple fallacy detector"""
    print("🧠 Testing Simple Fallacy Detector...")
    
    # Sample text with multiple fallacies
    sample_text = """
    Everyone knows that climate change is a hoax because my neighbor said so, 
    and he's a very smart person. Besides, if climate change were real, 
    then why was it cold last winter? Also, all scientists are just trying 
    to get research funding, so you can't trust anything they say. 
    We shouldn't change our lifestyle based on these false claims.
    """
    
    print("\n" + "="*60)
    print("📝 SAMPLE TEXT FOR ANALYSIS")
    print("="*60)
    print(sample_text.strip())
    
    print(f"\n📊 Text length: {len(sample_text)} characters")
    
    # Analyze for fallacies
    print("\n" + "="*60)
    print("🔍 FALLACY ANALYSIS (Simple Detector)")
    print("="*60)
    print("Analyzing sample text for logical fallacies...")
    
    analysis_result = detect_fallacies_simple(sample_text)
    
    print("\n📋 Fallacy Analysis Results:")
    print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
    
    print(f"\n✅ Analysis completed! Found {analysis_result['summary']['total_fallacies']} fallacies")
    print(f"📈 Overall quality: {analysis_result['summary']['overall_quality']}")

if __name__ == "__main__":
    main() 