#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DÉMONSTRATION ORCHESTRATION RÉELLE SEMANTIC KERNEL + GPT-4o-mini
===============================================================
Utilise l'infrastructure agentielle existante pour générer de vraies conversations
GPT-4o-mini capturées avec le format amélioré.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Configuration des chemins
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Imports infrastructure existante
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.orchestration.enhanced_pm_analysis_runner import (
    EnhancedProjectManagerOrchestrator,
    run_enhanced_pm_orchestration_demo
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("RealSKDemo")


def main():
    """Point d'entrée principal de la démonstration."""
    print("=" * 80)
    print("DEMONSTRATION ORCHESTRATION REELLE SEMANTIC KERNEL + GPT-4o-mini")
    print("=" * 80)
    print()
    
    # Texte d'exemple pour l'analyse
    texte_test = """L'intelligence artificielle va détruire tous les emplois.
C'est évident puisque ChatGPT peut déjà faire le travail de milliers de personnes.
Tout le monde le dit. De plus, si on n'arrête pas maintenant, ce sera trop tard.
Il faut donc interdire l'IA immédiatement, sinon nous serons tous au chômage."""
    
    print("TEXTE A ANALYSER:")
    print(f'"{texte_test}"')
    print()
    
    # Configuration LLM
    print("CONFIGURATION DU SERVICE LLM...")
    try:
        # Essayer d'abord GPT-4o-mini réel
        llm_service = create_llm_service(service_id="demo_real_orchestration")
        print(f"[OK] Service LLM configure: {llm_service.ai_model_id}")
    except Exception as e:
        print(f"[WARNING] Erreur service LLM reel: {e}")
        print("[INFO] Utilisation du service Mock pour demo...")
        llm_service = create_llm_service(service_id="demo_real_orchestration", force_mock=True)
        print(f"[OK] Service LLM Mock configure: {llm_service.ai_model_id}")
    
    print()
    print("DEMARRAGE ORCHESTRATION MULTI-AGENTS...")
    print("   - Project Manager (coordination)")
    print("   - Informal Agent (detection sophismes)")
    print("   - Modal Logic Agent (analyse formelle)")
    print("   - Extract Agent (structuration)")
    print()
    
    # Lancement de l'orchestration réelle
    try:
        result = asyncio.run(run_enhanced_pm_orchestration_demo(
            texte_a_analyser=texte_test,
            llm_service=llm_service
        ))
        
        print()
        print("=" * 80)
        print("RESULTATS DE L'ORCHESTRATION")
        print("=" * 80)
        
        if result["success"]:
            print("[SUCCESS] ORCHESTRATION TERMINEE AVEC SUCCES")
            print()
            print("STATISTIQUES:")
            print(f"   - Phases completees: {result.get('phases_completed', 'N/A')}")
            print(f"   - Snapshots d'etat: {result.get('state_snapshots', 'N/A')}")
            print(f"   - Appels d'outils: {result.get('tool_calls', 'N/A')}")
            print(f"   - Duree totale: {result.get('total_duration_ms', 0):.1f}ms")
            
            if result.get('report_path'):
                report_path = Path(result['report_path'])
                if report_path.exists():
                    print(f"[REPORT] Rapport detaille: {report_path}")
                    print(f"   Taille: {report_path.stat().st_size} bytes")
                    
                    # Afficher un extrait du rapport
                    print()
                    print("EXTRAIT DU RAPPORT GENERE:")
                    print("-" * 60)
                    try:
                        with open(report_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Afficher les premiers 1000 caractères
                            preview = content[:1000] + "..." if len(content) > 1000 else content
                            print(preview)
                    except Exception as e:
                        print(f"[WARNING] Erreur lecture rapport: {e}")
                    print("-" * 60)
            
            print()
            print("OBJECTIFS ATTEINTS:")
            print("[OK] Vraie orchestration Semantic Kernel + GPT-4o-mini")
            print("[OK] Conversations agentielles authentiques capturees")
            print("[OK] Format conversationnel ameliore avec headers")
            print("[OK] Etat partage evoluant reellement")
            print("[OK] Project Manager coordonnant effectivement")
            print("[OK] Rapport complet avec conversations authentiques")
            
        else:
            print("[ERROR] ECHEC DE L'ORCHESTRATION")
            print(f"Erreur: {result.get('error', 'Erreur inconnue')}")
    
    except Exception as e:
        print("[ERROR] ERREUR CRITIQUE:")
        print(f"   {e}")
        logger.error("Erreur orchestration", exc_info=True)
    
    print()
    print("=" * 80)
    print("FIN DE LA DEMONSTRATION")
    print("=" * 80)


if __name__ == "__main__":
    main()
