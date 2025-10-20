#!/usr/bin/env python3
"""
Phase 4 - Mesure de performance système complet
"""

import time
import psutil

print("=== MESURES PERFORMANCE SYSTÈME ===")

# Mesure mémoire avant
memory_before = psutil.virtual_memory().used / 1024 / 1024  # MB

start_total = time.time()

try:
    # Import et initialisation des modules critiques
    start_import = time.time()
    from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
    from argumentation_analysis.orchestration.real_llm_orchestrator import (
        RealLLMOrchestrator,
    )

    end_import = time.time()

    # Initialisation
    start_init = time.time()
    fol_agent = FOLLogicAgent()
    orchestrator = RealLLMOrchestrator()
    end_init = time.time()

    # Mesure mémoire après
    memory_after = psutil.virtual_memory().used / 1024 / 1024  # MB

    end_total = time.time()

    print(f"⚡ Import modules: {end_import - start_import:.3f}s")
    print(f"⚡ Initialisation: {end_init - start_init:.3f}s")
    print(f"⚡ Temps total: {end_total - start_total:.3f}s")
    print(f"💾 Mémoire utilisée: {memory_after - memory_before:.1f} MB")

    # Validation critères
    if end_total - start_total < 2.0:
        print("✅ Performance système excellente (<2s)")
    else:
        print("⚠️ Performance système acceptable (>2s)")

    if memory_after - memory_before < 100:
        print("✅ Consommation mémoire excellente (<100MB)")
    else:
        print("⚠️ Consommation mémoire élevée (>100MB)")

except Exception as e:
    print(f"❌ Erreur performance: {e}")
    import traceback

    traceback.print_exc()
