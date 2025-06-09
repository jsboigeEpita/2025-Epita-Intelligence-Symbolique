"""
Test script for Web API fallacy analysis integration
This script tests the integration between speech-to-text and real web API fallacy detection
"""

import json
import time
from web_api_fallacy_detector import WebAPIFallacyDetector

def main():
    """Test the web API fallacy analysis integration"""
    print("🌐 Testing Web API Fallacy Analysis Integration...")
    
    # Initialize the web API detector
    detector = WebAPIFallacyDetector(api_base_url="http://127.0.0.1:5001")
    
    # Check API health first
    print("\n🔍 Checking API health...")
    if not detector.check_api_health():
        print("❌ API is not healthy. Please start the argumentation analysis API first.")
        print("💡 Run: cd argumentation_analysis/services/web_api && python start_api.py --port 5001")
        return False
    
    print("✅ API is healthy and ready!")
    
    # Sample text with multiple fallacies (simulating transcribed speech)
    sample_text = """
    Everyone knows that climate change is a hoax because my neighbor said so, 
    and he's a very smart person. Besides, if climate change were real, 
    then why was it cold last winter? Also, all scientists are just trying 
    to get research funding, so you can't trust anything they say. 
    We shouldn't change our lifestyle based on these false claims.
    """
    
    print("\n" + "="*60)
    print("📝 SAMPLE TEXT FOR ANALYSIS (Simulated Speech-to-Text Output)")
    print("="*60)
    print(sample_text.strip())
    
    print(f"\n📊 Text length: {len(sample_text)} characters")
    
    # Analyze for fallacies using web API
    print("\n" + "="*60)
    print("🔍 WEB API FALLACY ANALYSIS")
    print("="*60)
    print("Analyzing transcribed text using real argumentation analysis API...")
    
    try:
        start_time = time.time()
        analysis_result = detector.detect_fallacies_web_api(sample_text, {
            "severity_threshold": 0.3,  # Lower threshold to catch more fallacies
            "include_context": True,
            "max_fallacies": 15
        })
        end_time = time.time()
        
        print(f"\n⏱️ Analysis completed in {end_time - start_time:.2f} seconds")
        print("\n📋 Web API Fallacy Analysis Results:")
        print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
        
        if analysis_result['status'] == 'success':
            print(f"\n✅ Analysis completed successfully!")
            print(f"📊 Found {analysis_result['summary']['total_fallacies']} fallacies")
            print(f"📈 Overall quality: {analysis_result['summary']['overall_quality']}")
            print(f"🌐 API version: {analysis_result['summary']['api_version']}")
            
            if analysis_result['fallacies_detected']:
                print("\n🚨 Detected Fallacies:")
                for i, fallacy in enumerate(analysis_result['fallacies_detected'], 1):
                    print(f"  {i}. {fallacy['type']}: '{fallacy['text_span']}' (confidence: {fallacy['confidence']:.2f})")
                    if fallacy.get('context'):
                        print(f"     Context: {fallacy['context']}")
            
            if analysis_result['recommendations']:
                print("\n💡 Recommendations:")
                for i, rec in enumerate(analysis_result['recommendations'], 1):
                    print(f"  {i}. {rec}")
            
            print("\n" + "="*60)
            print("✅ WEB API INTEGRATION TEST SUCCESSFUL")
            print("="*60)
            print("The speech-to-text to web API fallacy analysis pipeline is working!")
            
            return True
        else:
            print(f"\n❌ Analysis failed: {analysis_result.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"\n❌ Error during web API fallacy analysis: {str(e)}")
        print("Integration test failed.")
        return False

def test_complete_analysis():
    """Test the complete analysis endpoint"""
    print("\n\n🔬 Testing Complete Analysis API...")
    
    detector = WebAPIFallacyDetector(api_base_url="http://127.0.0.1:5001")
    
    sample_text = """
    We should ban all video games because they cause violence. 
    My cousin played violent games and he got into a fight, 
    so this proves that games make people aggressive. 
    Anyone who disagrees is just a gaming addict who can't see the truth.
    """
    
    print("\n📝 Sample text for complete analysis:")
    print(sample_text.strip())
    
    try:
        start_time = time.time()
        analysis_result = detector.analyze_text_complete(sample_text, {
            "detect_fallacies": True,
            "analyze_structure": True,
            "evaluate_coherence": True,
            "include_context": True,
            "severity_threshold": 0.4
        })
        end_time = time.time()
        
        print(f"\n⏱️ Complete analysis completed in {end_time - start_time:.2f} seconds")
        
        if analysis_result['status'] == 'success':
            print(f"\n✅ Complete analysis successful!")
            print(f"📊 Fallacies: {analysis_result['summary']['total_fallacies']}")
            
            if 'structure_score' in analysis_result['summary']:
                print(f"🏗️ Structure score: {analysis_result['summary']['structure_score']}")
            if 'coherence_score' in analysis_result['summary']:
                print(f"🔗 Coherence score: {analysis_result['summary']['coherence_score']}")
            
            return True
        else:
            print(f"❌ Complete analysis failed: {analysis_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error during complete analysis: {str(e)}")
        return False

if __name__ == "__main__":
    # Test basic fallacy detection
    success1 = main()
    
    # Test complete analysis if basic test succeeds
    success2 = test_complete_analysis() if success1 else False
    
    overall_success = success1 and success2
    
    print(f"\n{'🎉' if overall_success else '❌'} Overall integration test {'PASSED' if overall_success else 'FAILED'}")
    
    exit(0 if overall_success else 1) 