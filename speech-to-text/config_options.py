#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Options for Fallacy Detection System
Choose your preferred operation mode
"""

# OPTION 1: Pattern Matching Only (Fastest, No External Dependencies)
PATTERN_MATCHING_ONLY = {
    "use_advanced_services": False,
    "use_web_api": False,
    "description": "Pure pattern matching - fast and reliable"
}

# OPTION 2: With Real OpenAI API Key (Most Advanced)
WITH_OPENAI_API = {
    "use_advanced_services": True,
    "openai_api_key": "your-real-openai-key-here",  # Replace with real key
    "description": "Full AI-powered analysis with semantic understanding"
}

# OPTION 3: Current Setup (Mock + Fallback)
CURRENT_SETUP = {
    "use_advanced_services": True,
    "openai_api_key": "mock_key",  # Will fail and fallback
    "description": "Try advanced, fallback to pattern matching (current behavior)"
}

def get_recommended_config():
    """Get recommended configuration for most users"""
    return {
        "mode": "pattern_matching_only",
        "config": PATTERN_MATCHING_ONLY,
        "reason": "Reliable, fast, no external dependencies or costs"
    }

def configure_service_for_pattern_matching_only():
    """Configure the service to skip OpenAI calls entirely"""
    import os
    os.environ["SKIP_ADVANCED_SERVICES"] = "true"
    print("✅ Configured for pattern matching only - no more OpenAI errors!")

if __name__ == "__main__":
    print("🔧 Fallacy Detection Configuration Options")
    print("=" * 50)
    
    print("\n1. 🚀 Pattern Matching Only (Recommended)")
    print("   • Fast and reliable")
    print("   • No external API calls")
    print("   • No costs or API keys needed")
    
    print("\n2. 🤖 With Real OpenAI API")
    print("   • Most advanced analysis")
    print("   • Requires valid OpenAI API key")
    print("   • Costs money per request")
    
    print("\n3. 🔄 Current Setup (Mock + Fallback)")
    print("   • Shows errors but works")
    print("   • Falls back to pattern matching")
    print("   • Good for testing architecture")
    
    print(f"\n💡 Recommendation: Use Option 1 for production")
    print(f"   Call: configure_service_for_pattern_matching_only()") 