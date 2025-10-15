#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Investigation Semantic Kernel - Version et modules disponibles"""

import argumentation_analysis.core.environment
import sys
import os

print("=== SEMANTIC KERNEL INVESTIGATION ===")

try:
    import semantic_kernel

    print("✅ semantic_kernel importé avec succès")

    # Version
    try:
        print(f"Version: {semantic_kernel.__version__}")
    except AttributeError:
        print("__version__ non disponible")

    # Modules disponibles
    print("\nModules disponibles:")
    modules = [m for m in dir(semantic_kernel) if not m.startswith("_")]
    for mod in modules:
        print(f"  - {mod}")

    # Test du module agents
    print("\n=== TEST AGENTS MODULE ===")
    try:
        import semantic_kernel.agents

        print("✅ SUCCESS: semantic_kernel.agents disponible!")

        print("\nComposants agents:")
        agents_components = dir(semantic_kernel.agents)
        for comp in agents_components:
            if not comp.startswith("_"):
                print(f"  - {comp}")

    except ImportError as e:
        print(f"❌ ABSENT: semantic_kernel.agents non disponible - {e}")

    # Test des alternatives
    print("\n=== TEST ALTERNATIVES ===")
    try:
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

        print("✅ OpenAIChatCompletion disponible")
    except ImportError as e:
        print(f"❌ OpenAIChatCompletion non disponible - {e}")

    try:
        from semantic_kernel.kernel import Kernel

        print("✅ Kernel disponible")
    except ImportError as e:
        print(f"❌ Kernel non disponible - {e}")

except ImportError as e:
    print(f"❌ ERREUR: Impossible d'importer semantic_kernel - {e}")

print("\n=== INVESTIGATION COMPLETE ===")
