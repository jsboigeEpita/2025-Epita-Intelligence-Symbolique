#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test du TraceAnalyzer v2.0 avec format de conversation agentielle optimisé.
Démonstration sur extrait 2_1 (Argument Historique Ukraine - Poutine).
"""

import time
import json
from datetime import datetime
from argumentation_analysis.reporting.trace_analyzer import TraceAnalyzer, ToolCall, AgentStep

def simulate_analysis_with_conversation_format():
    """Simule une analyse avec le nouveau format de conversation agentielle."""
    
    print("=== DEMONSTRATION TRACEANALYZER v2.0 - FORMAT CONVERSATION AGENTIELLE ===")
    print(f"Démarrage à: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Initialisation du TraceAnalyzer
    analyzer = TraceAnalyzer()
    analyzer.start_conversation_capture()
    
    # === ÉTAPE 1: AGENT INFORMEL ===
    print("Simulation Agent Informel...")
    step1 = analyzer.start_agent_step("InformalAnalysisAgent")
    
    # Simulation d'un appel d'outil de détection de sophismes
    tool_call_1 = ToolCall(
        tool_name="detect_sophisms_from_taxonomy",
        arguments={
            "text": "So, I will start with the fact that modern Ukraine was entirely created by Russia or, to be more precise, by Bolshevik, Communist Russia. This process started practically right after the 1917 revolution, and Lenin and his associates did it in a way that was extremely harsh on Russia – by separating, severing what is historically Russian land. Nobody asked the millions of people living there what they thought. Then, both under Stalin and Khrushchev, Ukraine received considerable territorial additions, including Crimea.",
            "branches": ["logical", "emotional", "rhetorical"],
            "severity_threshold": 0.3
        },
        result=[
            {"type": "Historical Rewriting", "confidence": 0.85, "location": "paragraph 1"},
            {"type": "False Cause", "confidence": 0.78, "location": "Lenin attribution"},
            {"type": "Cherry Picking", "confidence": 0.72, "location": "territorial claims"}
        ],
        timestamp=time.time(),
        execution_time_ms=15.2,
        success=True
    )
    step1.add_tool_call(tool_call_1)
    
    # Deuxième outil
    tool_call_2 = ToolCall(
        tool_name="analyze_rhetorical_patterns",
        arguments={
            "text_segments": ["modern Ukraine was entirely created by Russia", "extremely harsh on Russia", "Nobody asked the millions"],
            "pattern_types": ["nationalism", "victimization", "authority"],
            "context": "political_speech"
        },
        result={
            "patterns_found": 5,
            "nationalist_appeals": 3,
            "victimization_narrative": 2,
            "authority_claims": 1
        },
        timestamp=time.time(),
        execution_time_ms=8.7,
        success=True
    )
    step1.add_tool_call(tool_call_2)
    step1.complete()
    
    # === ÉTAPE 2: AGENT LOGIQUE MODAL ===
    print("Simulation Agent Logique Modal...")
    step2 = analyzer.start_agent_step("ModalLogicAgent")
    
    tool_call_3 = ToolCall(
        tool_name="text_to_belief_set",
        arguments={
            "text": "Ukraine was entirely created by Russia... Lenin and his associates did it in a way that was extremely harsh on Russia",
            "logic_type": "modal",
            "extract_propositions": True
        },
        result={
            "propositions": ["BOX(Created(Ukraine, Russia))", "DIAMOND(Harsh(Lenin_actions, Russia))", "NOT(Asked(millions_people))"],
            "modal_operators": ["necessity", "possibility", "negation"],
            "consistency_status": "potentially_inconsistent"
        },
        timestamp=time.time(),
        execution_time_ms=23.4,
        success=True
    )
    step2.add_tool_call(tool_call_3)
    
    tool_call_4 = ToolCall(
        tool_name="generate_inference_queries",
        arguments={
            "belief_set": ["BOX(Created(Ukraine, Russia))", "DIAMOND(Harsh(Lenin_actions, Russia))"],
            "query_types": ["consistency", "entailment", "contradiction"]
        },
        result=["Query: BOX(Created(Ukraine, Russia)) IMPLIES NOT_DIAMOND(Independent(Ukraine))", "Query: DIAMOND(Harsh(Lenin_actions, Russia)) AND BOX(Beneficial(Soviet_policy))"],
        timestamp=time.time(),
        execution_time_ms=12.1,
        success=True
    )
    step2.add_tool_call(tool_call_4)
    step2.complete()
    
    # === ÉTAPE 3: AGENT DE SYNTHÈSE ===
    print("Simulation Agent de Synthèse...")
    step3 = analyzer.start_agent_step("SynthesisAgent")
    
    tool_call_5 = ToolCall(
        tool_name="unify_analysis_results",
        arguments={
            "informal_results": {"fallacies_detected": 3, "confidence_avg": 0.78},
            "formal_results": {"propositions": 3, "consistency": "inconsistent"},
            "synthesis_strategy": "comprehensive",
            "weight_distribution": {"informal": 0.6, "formal": 0.4}
        },
        result={
            "unified_score": 0.73,
            "contradiction_count": 2,
            "overall_validity": "questionable",
            "main_issues": ["historical_distortion", "logical_inconsistency"]
        },
        timestamp=time.time(),
        execution_time_ms=18.9,
        success=True
    )
    step3.add_tool_call(tool_call_5)
    step3.complete()
    
    # Finalisation
    analyzer.finalize_conversation_capture()
    
    # === GÉNÉRATION DU RAPPORT ===
    print("\n" + "="*70)
    print("RAPPORT DE CONVERSATION AGENTIELLE GÉNÉRÉ:")
    print("="*70)
    
    conversation_report = analyzer.generate_conversation_format_report()
    print(conversation_report)
    
    # === SAUVEGARDE ===
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"logs/conversation_agentielle_report_{timestamp}.md"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(conversation_report)
        print(f"\n[OK] Rapport sauvegarde: {report_file}")
    except Exception as e:
        print(f"\n[ERREUR] Erreur de sauvegarde: {e}")
    
    return conversation_report

def generate_comparison_report():
    """Génère un rapport de comparaison entre ancien et nouveau format."""
    
    print("\n" + "="*70)
    print("COMPARAISON ANCIEN vs NOUVEAU FORMAT")
    print("="*70)
    
    print("""
    ANCIEN FORMAT (Rapport traditionnel):
    ═══════════════════════════════════
    - Rapport structuré en sections markdown
    - Données regroupées par type d'analyse
    - Format textuel descriptif
    - Pas de visibilité sur les outils utilisés
    - Timing global seulement
    
    NOUVEAU FORMAT (Conversation agentielle):
    ════════════════════════════════════════
    ✅ [AGENT] Nom de l'agent clairement visible
    ✅ │ [TOOL] Outil utilisé identifiable en un coup d'œil
    ✅ │ [ARGS] Arguments tronqués intelligemment (~100-150 chars)
    ✅ │ [TIME] Timing précis pour chaque opération
    ✅ │ [RESULT] Résultat concis et informatif
    ✅ │ (Indentation claire pour hiérarchie)
    
    AVANTAGES DU NOUVEAU FORMAT:
    ═══════════════════════════════
    • Conversation agentielle lisible et compacte
    • Outils repérés instantanément
    • Arguments intelligemment tronqués pour lisibilité
    • Timing visible pour analyse de performance
    • Structure hiérarchique claire
    • Facilite debugging et optimisation
    """)

if __name__ == "__main__":
    print("Lancement du test TraceAnalyzer v2.0...")
    report = simulate_analysis_with_conversation_format()
    generate_comparison_report()
    print("\n[SUCCESS] Test termine avec succes!")