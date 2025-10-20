import os

modules = [
    "argumentation_analysis/agents/core/logic/fol_logic_agent.py",
    "argumentation_analysis/utils/report_generator.py",
    "argumentation_analysis/orchestration/real_llm_orchestrator.py",
    "config/unified_config.py",
]

alternative_modules = [
    "argumentation_analysis/config/config_utils.py",
    "argumentation_analysis/utils/config_utils.py",
    "argumentation_analysis/utils/reporting_utils.py",
]

print("=== VÉRIFICATION INTÉGRITÉ MODULES CRITIQUES ===")
for module in modules:
    if os.path.exists(module):
        size = os.path.getsize(module)
        print(f"✅ {module}: {size} bytes")
    else:
        print(f"❌ MANQUANT: {module}")

print("\n=== VÉRIFICATION MODULES ALTERNATIFS ===")
for module in alternative_modules:
    if os.path.exists(module):
        size = os.path.getsize(module)
        print(f"🔍 TROUVÉ: {module}: {size} bytes")

print("Vérification terminée")
