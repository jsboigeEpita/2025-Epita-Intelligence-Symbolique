#!/usr/bin/env python3
"""
Script de Migration d'Usage - Consolidation 42→3 Scripts
Date: 10/06/2025
Objectif: Aider les utilisateurs à migrer des anciens scripts vers les nouveaux scripts consolidés
"""

import os
import sys
from pathlib import Path

# Mapping des anciens scripts vers les nouveaux scripts consolidés
MIGRATION_MAPPING = {
    # Anciens scripts → Nouveau script unifié
    "demos/demo_rhetorique_complete.py": "scripts/consolidated/educational_showcase_system.py",
    "demos/demo_rhetorique_corrige.py": "scripts/consolidated/educational_showcase_system.py",
    "demos/demo_unified_system.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    
    # Examples Logic Agents → Production Analyzer
    "examples/logic_agents/api_integration_example.py": "scripts/consolidated/unified_production_analyzer.py",
    "examples/logic_agents/combined_logic_example.py": "scripts/consolidated/unified_production_analyzer.py",
    "examples/temp_demos/temp_fol_logic_agent.py": "scripts/consolidated/educational_showcase_system.py",
    "examples/demo_orphelins/demo_real_sk_orchestration.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "examples/demo_orphelins/demo_real_sk_orchestration_fixed.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    
    # Scripts Execution → Production Analyzer
    "scripts/execution/advanced_rhetorical_analysis.py": "scripts/consolidated/unified_production_analyzer.py",
    "scripts/execution/run_full_python_analysis_workflow.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/execution/run_performance_tests.py": "scripts/consolidated/unified_production_analyzer.py",
    "scripts/execution/run_test.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    
    # Scripts Diagnostic → Educational Showcase
    "scripts/diagnostic/test_fol_demo_simple.py": "scripts/consolidated/educational_showcase_system.py",
    "scripts/diagnostic/test_pipeline_bout_en_bout.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/diagnostic/test_micro_orchestration.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/diagnostic/test_advanced_rhetorical_enhanced.py": "scripts/consolidated/unified_production_analyzer.py",
    "scripts/diagnostic/test_simple_unified_pipeline.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/diagnostic/test_sophismes_detection.py": "scripts/consolidated/unified_production_analyzer.py",
    "scripts/diagnostic/test_trace_analyzer_conversation_format.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/diagnostic/test_report_generation.py": "scripts/consolidated/unified_production_analyzer.py",
    "scripts/diagnostic/test_modal_retry_mechanism.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    
    # Scripts Demo → Educational Showcase
    "scripts/demo/run_rhetorical_analysis_demo.py": "scripts/consolidated/educational_showcase_system.py",
    "scripts/demo/run_rhetorical_analysis_phase2_authentic.py": "scripts/consolidated/educational_showcase_system.py",
    "scripts/demo/test_enhanced_pm_components.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/demo/test_modal_logic_agent.py": "scripts/consolidated/educational_showcase_system.py",
    "scripts/demo/test_synthesis_agent_simple.py": "scripts/consolidated/educational_showcase_system.py",
    "scripts/demo/test_synthesis_agent.py": "scripts/consolidated/educational_showcase_system.py",
    
    # Scripts Main/Test/Testing
    "scripts/main/analyze_text_authentic.py": "scripts/consolidated/unified_production_analyzer.py",
    "scripts/main/analyze_text.py": "scripts/consolidated/unified_production_analyzer.py",
    "scripts/test/test_unified_authentic_system.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/testing/run_all_new_component_tests.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/testing/test_pl_agent_functionality.py": "scripts/consolidated/educational_showcase_system.py",
    
    # Scripts Supplémentaires
    "scripts/testing/test_informal_agent_taxonomy_exploration.py": "scripts/consolidated/educational_showcase_system.py",
    "scripts/testing/test_fallacy_adapter.py": "scripts/consolidated/unified_production_analyzer.py",
    "scripts/testing/test_agent_informel.py": "scripts/consolidated/educational_showcase_system.py",
    "scripts/testing/test_rhetorical_analysis.py": "scripts/consolidated/unified_production_analyzer.py",
    "scripts/testing/simulation_agent_informel.py": "scripts/consolidated/educational_showcase_system.py",
    "scripts/orchestration_llm_real.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/orchestration_conversation_unified.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "scripts/run_fol_tests.py": "scripts/consolidated/educational_showcase_system.py",
    "scripts/run_phase2_tests.py": "scripts/consolidated/comprehensive_workflow_processor.py",
    "run_all_new_component_tests.ps1": "scripts/consolidated/comprehensive_workflow_processor.py"
}

# Description des nouveaux scripts consolidés
CONSOLIDATED_SCRIPTS_INFO = {
    "scripts/consolidated/unified_production_analyzer.py": {
        "description": "Analyseur de production unifié pour l'analyse rhétorique avancée",
        "usage": "python scripts/consolidated/unified_production_analyzer.py --config scripts/consolidated/config_example.json",
        "config": "scripts/consolidated/config_example.json",
        "test": "scripts/consolidated/test_unified_analyzer.py",
        "readme": "scripts/consolidated/README.md",
        "capabilities": [
            "Analyse rhétorique complète",
            "Détection de sophismes",
            "Génération de rapports",
            "Tests de performance",
            "API d'intégration"
        ]
    },
    "scripts/consolidated/educational_showcase_system.py": {
        "description": "Système de démonstration éducatif pour l'apprentissage",
        "usage": "python scripts/consolidated/educational_showcase_system.py --config scripts/consolidated/educational_config_example.json",
        "config": "scripts/consolidated/educational_config_example.json",
        "test": "scripts/consolidated/test_educational_showcase_system.py",
        "readme": "scripts/consolidated/README_educational_showcase_system.md",
        "capabilities": [
            "Démonstrations interactives",
            "Logique du premier ordre simplifiée",
            "Agents pédagogiques",
            "Tests de base",
            "Exemples d'usage"
        ]
    },
    "scripts/consolidated/comprehensive_workflow_processor.py": {
        "description": "Processeur de workflow compréhensif pour l'orchestration complexe",
        "usage": "python scripts/consolidated/comprehensive_workflow_processor.py --config scripts/consolidated/comprehensive_config_example.json",
        "config": "scripts/consolidated/comprehensive_config_example.json",
        "test": "scripts/consolidated/test_comprehensive_workflow.py",
        "readme": "scripts/consolidated/README_comprehensive_workflow.md",
        "capabilities": [
            "Orchestration de workflows",
            "Pipeline bout en bout",
            "Micro-orchestration",
            "Gestion conversationnelle",
            "Tests d'intégration"
        ]
    }
}

def print_migration_guide():
    """Affiche le guide de migration complet"""
    print("=" * 80)
    print("GUIDE DE MIGRATION - Consolidation 42->3 Scripts")
    print("=" * 80)
    print()
    
    print("NOUVEAUX SCRIPTS CONSOLIDES:")
    print("-" * 40)
    for script_path, info in CONSOLIDATED_SCRIPTS_INFO.items():
        print(f"\n[SCRIPT] {script_path}")
        print(f"   Description: {info['description']}")
        print(f"   Usage: {info['usage']}")
        print(f"   Config: {info['config']}")
        print(f"   Test: {info['test']}")
        print(f"   README: {info['readme']}")
        print(f"   Capacités:")
        for cap in info['capabilities']:
            print(f"     - {cap}")
    
    print("\n" + "=" * 80)
    print("MAPPING DE MIGRATION:")
    print("=" * 80)
    
    # Grouper par nouveau script
    by_new_script = {}
    for old, new in MIGRATION_MAPPING.items():
        if new not in by_new_script:
            by_new_script[new] = []
        by_new_script[new].append(old)
    
    for new_script, old_scripts in by_new_script.items():
        print(f"\n[NOUVEAU] {new_script}")
        print("   Remplace:")
        for old_script in old_scripts:
            print(f"     [ANCIEN] {old_script}")

def find_replacement(old_script_path):
    """Trouve le script de remplacement pour un ancien script"""
    if old_script_path in MIGRATION_MAPPING:
        return MIGRATION_MAPPING[old_script_path]
    
    # Recherche approximative
    for old_pattern, new_script in MIGRATION_MAPPING.items():
        if old_script_path in old_pattern or old_pattern in old_script_path:
            return new_script
    
    return None

def interactive_migration():
    """Mode interactif pour aider à la migration"""
    print("\nMODE INTERACTIF DE MIGRATION")
    print("-" * 40)
    
    while True:
        old_script = input("\nEntrez le nom de l'ancien script (ou 'quit' pour quitter): ").strip()
        
        if old_script.lower() in ['quit', 'exit', 'q']:
            break
        
        replacement = find_replacement(old_script)
        
        if replacement:
            print(f"[OK] Remplacement trouvé:")
            print(f"   Ancien: {old_script}")
            print(f"   Nouveau: {replacement}")
            
            if replacement in CONSOLIDATED_SCRIPTS_INFO:
                info = CONSOLIDATED_SCRIPTS_INFO[replacement]
                print(f"   Usage: {info['usage']}")
                print(f"   Config: {info['config']}")
        else:
            print(f"[ERREUR] Aucun remplacement direct trouvé pour: {old_script}")
            print("   Consultez le mapping complet ci-dessus")

def validate_consolidated_scripts():
    """Valide que les scripts consolidés existent et sont fonctionnels"""
    print("\nVALIDATION DES SCRIPTS CONSOLIDES:")
    print("-" * 40)
    
    all_valid = True
    
    for script_path, info in CONSOLIDATED_SCRIPTS_INFO.items():
        print(f"\n[SCRIPT] {script_path}")
        
        # Vérifier l'existence du script principal
        if os.path.exists(script_path):
            print("   [OK] Script principal: EXISTE")
        else:
            print("   [ERREUR] Script principal: MANQUANT")
            all_valid = False
        
        # Vérifier les fichiers associés
        for file_type, file_path in [("Config", info['config']), ("Test", info['test']), ("README", info['readme'])]:
            if os.path.exists(file_path):
                print(f"   [OK] {file_type}: EXISTE")
            else:
                print(f"   [ERREUR] {file_type}: MANQUANT")
                all_valid = False
    
    print(f"\n[RESULTAT] RÉSULTAT GLOBAL: {'[OK] TOUS VALIDES' if all_valid else '[ERREUR] FICHIERS MANQUANTS'}")
    return all_valid

def main():
    """Fonction principale"""
    print("Script de Migration - Consolidation des Scripts")
    print(f"Répertoire actuel: {os.getcwd()}")
    print()
    
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == "guide":
            print_migration_guide()
        elif action == "interactive":
            print_migration_guide()
            interactive_migration()
        elif action == "validate":
            validate_consolidated_scripts()
        elif action == "help":
            print("AIDE:")
            print("  python migration_guide.py guide      - Affiche le guide complet")
            print("  python migration_guide.py interactive - Mode interactif")
            print("  python migration_guide.py validate   - Valide les scripts consolidés")
            print("  python migration_guide.py help       - Affiche cette aide")
        else:
            print(f"Action inconnue: {action}")
            print("Utilisez 'help' pour voir les options disponibles")
    else:
        # Mode par défaut : guide complet + validation
        print_migration_guide()
        validate_consolidated_scripts()
        print("\nTIP: Utilisez 'python migration_guide.py interactive' pour l'aide à la migration")

if __name__ == "__main__":
    main()