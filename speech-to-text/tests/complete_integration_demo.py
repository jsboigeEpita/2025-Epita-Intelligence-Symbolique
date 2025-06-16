"""
Complete Integration Demo: Speech-to-Text + Fallacy Analysis
This script demonstrates the complete pipeline from audio transcription to fallacy detection
"""

import json
import time
from simple_fallacy_detector import detect_fallacies_simple

def simulate_speech_to_text(audio_description: str) -> str:
    """
    Simulates speech-to-text transcription.
    In a real implementation, this would use Whisper or another STT service.
    
    Args:
        audio_description (str): Description of the audio content
        
    Returns:
        str: Simulated transcribed text
    """
    
    # Simulate different types of speeches with fallacies
    sample_speeches = {
        "climate_debate": """
        Everyone knows that climate change is a hoax because my neighbor said so, 
        and he's a very smart person. Besides, if climate change were real, 
        then why was it cold last winter? Also, all scientists are just trying 
        to get research funding, so you can't trust anything they say. 
        We shouldn't change our lifestyle based on these false claims.
        """,
        
        "political_speech": """
        My opponent is clearly unfit for office because he went to a fancy school, 
        so he can't understand regular people like us. Everyone in my neighborhood 
        agrees that we need change. If his policies were any good, then why 
        is there still unemployment? All politicians are corrupt anyway, 
        so we might as well vote for someone new.
        """,
        
        "product_review": """
        This product is terrible because the company's CEO is young and inexperienced. 
        Everyone knows that young people don't understand business. My friend tried 
        a similar product once and it broke, so all products from this category 
        are unreliable. If this product was good, then why do they need to advertise it?
        """,
        
        "health_discussion": """
        You shouldn't trust doctors because they just want to make money from you. 
        My grandmother lived to 95 without ever going to a doctor, so medical care 
        is unnecessary. Everyone in my family has good genes, so we don't need 
        to worry about health issues. These medical studies are all funded by 
        pharmaceutical companies anyway.
        """
    }
    
    # Return the appropriate sample or a default
    return sample_speeches.get(audio_description, sample_speeches["climate_debate"]).strip()

def process_audio_pipeline(audio_description: str, show_steps: bool = True):
    """
    Complete pipeline: Audio → Speech-to-Text → Fallacy Analysis
    
    Args:
        audio_description (str): Description of the audio to process
        show_steps (bool): Whether to show intermediate steps
    """
    
    if show_steps:
        print("🎤 COMPLETE AUDIO ANALYSIS PIPELINE")
        print("="*60)
        print(f"📁 Processing audio: {audio_description}")
    
    # Step 1: Speech-to-Text (simulated)
    if show_steps:
        print("\n🔄 Step 1: Speech-to-Text Transcription")
        print("Transcribing audio to text...")
        time.sleep(1)  # Simulate processing time
    
    transcribed_text = simulate_speech_to_text(audio_description)
    
    if show_steps:
        print("✅ Transcription completed!")
        print(f"📝 Transcribed text ({len(transcribed_text)} characters):")
        print("-" * 40)
        print(transcribed_text)
    
    # Step 2: Fallacy Analysis
    if show_steps:
        print(f"\n🔄 Step 2: Fallacy Analysis")
        print("Analyzing transcribed text for logical fallacies...")
        time.sleep(1)  # Simulate processing time
    
    analysis_result = detect_fallacies_simple(transcribed_text)
    
    if show_steps:
        print("✅ Fallacy analysis completed!")
        
        # Summary
        print(f"\n📊 ANALYSIS SUMMARY")
        print("-" * 40)
        print(f"Total fallacies detected: {analysis_result['summary']['total_fallacies']}")
        print(f"Unique fallacy types: {analysis_result['summary']['unique_fallacy_types']}")
        print(f"Overall quality: {analysis_result['summary']['overall_quality']}")
        
        # Detected fallacies
        if analysis_result['fallacies_detected']:
            print(f"\n🚨 DETECTED FALLACIES:")
            for i, fallacy in enumerate(analysis_result['fallacies_detected'], 1):
                print(f"  {i}. {fallacy['type']}: '{fallacy['text_span']}'")
        
        # Recommendations
        if analysis_result['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(analysis_result['recommendations'], 1):
                print(f"  {i}. {rec}")
    
    return {
        "transcribed_text": transcribed_text,
        "fallacy_analysis": analysis_result,
        "pipeline_success": True
    }

def main():
    """Main demonstration function"""
    print("🎯 COMPLETE INTEGRATION DEMONSTRATION")
    print("="*60)
    print("This demo shows the complete pipeline:")
    print("Audio Input → Speech-to-Text → Fallacy Analysis → Results")
    
    # Test different types of audio content
    test_cases = [
        ("climate_debate", "Climate Change Debate Audio"),
        ("political_speech", "Political Campaign Speech"),
        ("product_review", "Product Review Video"),
        ("health_discussion", "Health Discussion Podcast")
    ]
    
    results = []
    
    for audio_type, description in test_cases:
        print(f"\n" + "="*80)
        print(f"🎵 PROCESSING: {description}")
        print("="*80)
        
        result = process_audio_pipeline(audio_type, show_steps=True)
        results.append({
            "audio_type": audio_type,
            "description": description,
            "result": result
        })
        
        print(f"\n✅ Pipeline completed for: {description}")
        time.sleep(0.5)  # Brief pause between tests
    
    # Overall summary
    print(f"\n" + "="*80)
    print("📈 OVERALL PIPELINE SUMMARY")
    print("="*80)
    
    total_fallacies = sum(r["result"]["fallacy_analysis"]["summary"]["total_fallacies"] for r in results)
    successful_runs = sum(1 for r in results if r["result"]["pipeline_success"])
    
    print(f"✅ Successful pipeline runs: {successful_runs}/{len(results)}")
    print(f"🚨 Total fallacies detected across all tests: {total_fallacies}")
    
    print(f"\n📋 DETAILED RESULTS:")
    for result in results:
        analysis = result["result"]["fallacy_analysis"]
        print(f"  • {result['description']}: {analysis['summary']['total_fallacies']} fallacies ({analysis['summary']['overall_quality']} quality)")
    
    print(f"\n🎉 INTEGRATION DEMONSTRATION COMPLETE!")
    print("The speech-to-text + fallacy analysis pipeline is working successfully!")

if __name__ == "__main__":
    main() 