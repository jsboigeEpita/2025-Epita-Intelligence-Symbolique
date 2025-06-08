#!/usr/bin/env python3
"""Test des imports Semantic Kernel pour diagnostiquer les erreurs de collecte pytest."""

print("Test des imports Semantic Kernel...")

# Test 1: AuthorRole
try:
    from semantic_kernel.contents import AuthorRole
    print("OK: AuthorRole import")
except ImportError as e:
    print(f"FAILED: AuthorRole import - {e}")

# Test 2: ChatMessageContent
try:
    from semantic_kernel.contents import ChatMessageContent
    print("OK: ChatMessageContent import")
except ImportError as e:
    print(f"FAILED: ChatMessageContent import - {e}")

# Test 3: semantic_kernel.agents
try:
    import semantic_kernel.agents
    print("OK: semantic_kernel.agents module")
    print(f"    Available: {[attr for attr in dir(semantic_kernel.agents) if not attr.startswith('_')]}")
except ImportError as e:
    print(f"FAILED: semantic_kernel.agents module - {e}")

# Test 4: semantic_kernel.agents.Agent
try:
    from semantic_kernel.agents import Agent
    print("OK: Agent class import")
except ImportError as e:
    print(f"FAILED: Agent class import - {e}")

print("Tests terminés.")