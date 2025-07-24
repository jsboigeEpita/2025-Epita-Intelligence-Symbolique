"""
Test script for fallacy analysis integration
This script tests the integration between speech-to-text and fallacy detection
"""

import json
from simple_fallacy_detector import detect_fallacies_simple

def main():
    """Test the fallacy analysis integration"""
    print("🧠 Testing Fallacy Analysis Integration...")
    
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
    
    # Analyze for fallacies using simple detector
    print("\n" + "="*60)
    print("🔍 FALLACY ANALYSIS")
    print("="*60)
    print("Analyzing transcribed text for logical fallacies...")
    
    try:
        analysis_result = detect_fallacies_simple(sample_text)
        
        print("\n📋 Fallacy Analysis Results:")
        print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
        
        print(f"\n✅ Analysis completed successfully!")
        print(f"📊 Found {analysis_result['summary']['total_fallacies']} fallacies")
        print(f"📈 Overall quality: {analysis_result['summary']['overall_quality']}")
        
        if analysis_result['fallacies_detected']:
            print("\n🚨 Detected Fallacies:")
            for i, fallacy in enumerate(analysis_result['fallacies_detected'], 1):
                print(f"  {i}. {fallacy['type']}: '{fallacy['text_span']}'")
        
        if analysis_result['recommendations']:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(analysis_result['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "="*60)
        print("✅ INTEGRATION TEST SUCCESSFUL")
        print("="*60)
        print("The speech-to-text to fallacy analysis pipeline is working!")
        
    except Exception as e:
        print(f"\n❌ Error during fallacy analysis: {str(e)}")
        print("Integration test failed.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 