#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test rapide de l'installation Semantic-Kernel."""

import sys
import os

def test_imports():
    """Test les imports nécessaires."""
    print("Testing imports...")
    
    try:
        import semantic_kernel as sk
        print(f"[OK] semantic_kernel version: {getattr(sk, '__version__', 'unknown')}")
        sk_available = True
    except ImportError as e:
        print(f"[ERROR] semantic_kernel: {e}")
        sk_available = False
    
    try:
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        print("[OK] OpenAIChatCompletion import success")
    except ImportError as e:
        print(f"[ERROR] OpenAIChatCompletion: {e}")
    
    try:
        from config.unified_config import UnifiedConfig, PresetConfigs
        print("[OK] unified_config import success")
    except ImportError as e:
        print(f"[ERROR] unified_config: {e}")
    
    # Test configuration
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"[KEY] OPENAI_API_KEY: {'Present' if api_key else 'Missing'}")
    
    return sk_available

if __name__ == "__main__":
    sk_available = test_imports()
    print(f"\nSemantic-Kernel ready: {sk_available}")
    print(f"Can run authentic script: {sk_available and os.getenv('OPENAI_API_KEY')}")