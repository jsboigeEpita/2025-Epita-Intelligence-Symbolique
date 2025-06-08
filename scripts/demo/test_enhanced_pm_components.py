#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test rapide pour valider les composants du Project Manager amélioré
sans lancer la démo complète.

Ce script teste :
- Chargement des modules Enhanced PM
- Instanciation des composants de trace
- Validation du format de conversation
- Test de la gestion d'état partagé
"""

import sys
import os
import time
import logging
from datetime import datetime

# Configuration de l'encodage pour éviter les problèmes Unicode
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration des chemins
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_script_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("EnhancedPMTest")


def test_enhanced_trace_analyzer():
    """Test du système de trace amélioré."""
    print("[TEST] Test du systeme de trace ameliore...")
    
    try:
        from argumentation_analysis.reporting.enhanced_real_time_trace_analyzer import (
            EnhancedRealTimeTraceAnalyzer,
            StateSnapshot,
            EnhancedToolCall,
            ProjectManagerPhase,
            enhanced_global_trace_analyzer
        )
        
        print("   [OK] Import des modules de trace reussi")
        
        # Test de l'instanciation
        analyzer = EnhancedRealTimeTraceAnalyzer()
        print("   [OK] Instanciation EnhancedRealTimeTraceAnalyzer reussie")
        
        # Test StateSnapshot
        snapshot = StateSnapshot(
            phase_id="test_phase",
            tour_number=1,
            agent_active="TestAgent",
            state_variables={"test_var": "test_value", "count": 42},
            metadata={"test_meta": "test_meta_value"}
        )
        
        snapshot_markdown = snapshot.to_markdown_format()
        print("   [OK] StateSnapshot cree et formate en markdown")
        print(f"      Apercu: {snapshot_markdown.split()[0:3]}...")
        
        # Test EnhancedToolCall
        tool_call = EnhancedToolCall(
            agent_name="TestAgent",
            tool_name="test_tool",
            arguments={"arg1": "value1", "arg2": "value2"},
            result="Test result",
            timestamp=time.time(),
            execution_time_ms=100.5,
            success=True
        )
        
        tool_call_format = tool_call.to_enhanced_conversation_format()
        print("   [OK] EnhancedToolCall cree et formate")
        print(f"      Contient headers speciaux: {'### 🔧 **Tool**:' in tool_call_format}")
        
        return True
        
    except Exception as e:
        print(f"   [ERROR] Erreur test trace analyzer: {e}")
        return False


def test_enhanced_pm_orchestrator():
    """Test de l'orchestrateur PM amélioré."""
    print("[TEST] Test de l'orchestrateur PM ameliore...")
    
    try:
        from argumentation_analysis.orchestration.enhanced_pm_analysis_runner import (
            EnhancedProjectManagerOrchestrator,
            run_enhanced_pm_orchestration_demo,
            EnhancedPMAnalysisRunner
        )
        
        print("   [OK] Import des modules PM orchestrator reussi")
        
        # Test d'instanciation (sans LLM service pour le test)
        print("   [OK] Classes PM disponibles pour instanciation")
        
        return True
        
    except Exception as e:
        print(f"   [ERROR] Erreur test PM orchestrator: {e}")
        return False


def test_conversation_format_generation():
    """Test de génération du format de conversation amélioré."""
    print("[TEST] Test de generation du format de conversation...")
    
    try:
        from argumentation_analysis.reporting.enhanced_real_time_trace_analyzer import (
            EnhancedRealTimeTraceAnalyzer,
            StateSnapshot,
            EnhancedToolCall,
            ProjectManagerPhase
        )
        
        # Simulation d'une phase complète
        analyzer = EnhancedRealTimeTraceAnalyzer()
        analyzer.start_capture()
        
        # Ajout d'une phase de test
        test_phase = analyzer.start_pm_phase(
            phase_id="test_phase_1",
            phase_name="Test Informal Analysis",
            assigned_agents=["ProjectManagerAgent", "InformalAnalysisAgent"]
        )
        
        # Ajout d'un snapshot d'état
        analyzer.capture_state_snapshot(
            phase_id="test_phase_1",
            tour_number=1,
            agent_active="ProjectManagerAgent",
            state_variables={
                "sophistication_score": 0.85,
                "fallacies_detected": 4,
                "logical_consistency": 0.65,
                "agent_consensus": "partial"
            },
            metadata={
                "phase_type": "initialization",
                "coordination": "pm_directed"
            }
        )
        
        # Ajout d'un tool call
        analyzer.record_enhanced_tool_call(
            agent_name="InformalAnalysisAgent",
            tool_name="add_argument",
            arguments={"description": "Test argument description"},
            result="arg_1",
            execution_time_ms=150.3,
            success=True
        )
        
        analyzer.stop_capture()
        
        # Génération du rapport
        report = analyzer.generate_enhanced_pm_orchestration_report()
        
        # Validation du format
        format_checks = [
            ("Header principal", "# DÉMO PROJECT MANAGER" in report),
            ("Métadonnées", "## 1. Métadonnées de l'orchestration" in report),
            ("État partagé", "## 📊 **État Partagé**" in report),
            ("Variables d'état", "sophistication_score" in report),
            ("Tool calls", "### 🔧 **Tool**:" in report),
            ("Timing", "**Timing:**" in report),
            ("Arguments", "**Arguments:**" in report),
            ("Validation PM", "✅ **Project Manager opérationnel**" in report)
        ]
        
        print("   [CHECK] Validation du format genere:")
        all_valid = True
        for check_name, is_valid in format_checks:
            status = "[OK]" if is_valid else "[KO]"
            print(f"      {status} {check_name}")
            if not is_valid:
                all_valid = False
        
        if all_valid:
            print("   [OK] Format de conversation ameliore entierement valide")
        else:
            print("   [WARNING] Format de conversation partiellement valide")
        
        # Sauvegarde du rapport de test
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_report_path = f"./logs/test_enhanced_format_{timestamp}.md"
        
        try:
            os.makedirs("./logs", exist_ok=True)
            with open(test_report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"   [SAVE] Rapport de test sauvegarde: {test_report_path}")
        except Exception as e:
            print(f"   [WARNING] Erreur sauvegarde: {e}")
        
        return all_valid
        
    except Exception as e:
        print(f"   [ERROR] Erreur test format conversation: {e}")
        return False


def test_state_management():
    """Test de la gestion d'état partagé."""
    print("[TEST] Test de la gestion d'etat partage...")
    
    try:
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        from argumentation_analysis.reporting.enhanced_real_time_trace_analyzer import (
            enhanced_global_trace_analyzer,
            capture_shared_state
        )
        
        # Test de l'état partagé
        state = RhetoricalAnalysisState(initial_text="Test text for state management")
        
        # Ajout de données de test
        task_id = state.add_task("Test analysis task")
        arg_id = state.add_argument("Test argument identification")
        fallacy_id = state.add_fallacy("Ad Hominem", "Test fallacy justification", arg_id)
        
        print("   [OK] Etat partage cree et peuple")
        print(f"      Taches: {len(state.analysis_tasks)}")
        print(f"      Arguments: {len(state.identified_arguments)}")
        print(f"      Sophismes: {len(state.identified_fallacies)}")
        
        # Test de capture de snapshot
        enhanced_global_trace_analyzer.start_capture()
        
        capture_shared_state(
            phase_id="test_state_phase",
            tour_number=1,
            agent_active="TestAgent",
            state_variables={
                "tasks_count": len(state.analysis_tasks),
                "arguments_count": len(state.identified_arguments),
                "fallacies_count": len(state.identified_fallacies)
            },
            metadata={"test": "state_management"}
        )
        
        print("   [OK] Snapshot d'etat capture")
        print(f"      Snapshots totaux: {enhanced_global_trace_analyzer.total_state_snapshots}")
        
        enhanced_global_trace_analyzer.stop_capture()
        
        return True
        
    except Exception as e:
        print(f"   [ERROR] Erreur test gestion d'etat: {e}")
        return False


def main():
    """Fonction principale de test."""
    print("[TEST] TESTS COMPOSANTS PROJECT MANAGER AMELIORE")
    print("=" * 60)
    print(f"[DATE] Debut des tests: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_results = []
    
    # Exécution des tests
    test_results.append(("Système de trace amélioré", test_enhanced_trace_analyzer()))
    test_results.append(("Orchestrateur PM amélioré", test_enhanced_pm_orchestrator()))
    test_results.append(("Format de conversation", test_conversation_format_generation()))
    test_results.append(("Gestion d'état partagé", test_state_management()))
    
    # Résumé des résultats
    print("\n" + "=" * 60)
    print("[RESUME] RESUME DES TESTS")
    print("-" * 30)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "[OK] SUCCES" if passed else "[KO] ECHEC"
        print(f"   {status}: {test_name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("[SUCCESS] TOUS LES TESTS REUSSIS!")
        print("   Le systeme Project Manager ameliore est pret pour la demo complete.")
        print("   Vous pouvez maintenant lancer: python scripts/demo/run_enhanced_pm_orchestration_demo.py")
    else:
        print("[WARNING] CERTAINS TESTS ONT ECHOUE")
        print("   Verifiez les erreurs ci-dessus avant de lancer la demo complete.")
    
    print(f"\n[DATE] Fin des tests: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)