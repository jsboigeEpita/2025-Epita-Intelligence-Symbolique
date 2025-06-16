import project_core.core_from_scripts.auto_env
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestration complexe multi-agents utilisant les outils de reporting existants.
SANS emojis Unicode pour éviter les problèmes d'encodage.
"""

import asyncio
import os
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Import des systèmes de reporting existants
from argumentation_analysis.reporting.real_time_trace_analyzer import RealToolCall
from argumentation_analysis.utils.unified_pipeline import UnifiedAnalysisPipeline
from argumentation_analysis.utils.unified_pipeline import AnalysisConfig, AnalysisMode, SourceType

# Configuration du logging SANS emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

def safe_print(text: str):
    """Print sécurisé qui évite les erreurs d'encodage Unicode."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Remplacer les caractères problématiques
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)

class SimpleTracker:
    """Tracker simple pour capturer les interactions sans emojis."""
    
    def __init__(self):
        self.session_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.traces = []
        self.start_time = datetime.now()
        
    def log_interaction(self, agent: str, action: str, input_text: str, output: Any, duration: float = 0):
        """Enregistre une interaction agent/outil."""
        trace = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "action": action,
            "input_length": len(input_text),
            "output_length": len(str(output)),
            "duration_seconds": duration,
            "success": True
        }
        self.traces.append(trace)
    
    def generate_simple_report(self, source_info: Dict, final_results: Dict) -> str:
        """Génère un rapport simple en texte."""
        
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        report = f"""
RAPPORT D'ANALYSE COMPLEXE MULTI-AGENTS
======================================

Session: {self.session_id}
Date: {self.start_time.strftime('%d/%m/%Y à %H:%M:%S')}
Durée: {total_duration:.2f} secondes

SOURCE ANALYSÉE
--------------
Titre: {source_info.get('title', 'N/A')}
Longueur: {source_info.get('length', 0):,} caractères
Type: {source_info.get('type', 'N/A')}

AGENTS UTILISÉS
--------------
"""
        
        agents = list(set(t['agent'] for t in self.traces))
        for agent in agents:
            agent_traces = [t for t in self.traces if t['agent'] == agent]
            total_time = sum(t['duration_seconds'] for t in agent_traces)
            report += f"- {agent}: {len(agent_traces)} interactions, {total_time:.2f}s\n"
        
        report += f"""
RESULTATS
---------
"""
        
        fallacies_result = final_results.get('fallacies', {})
        if isinstance(fallacies_result, dict) and 'fallacies' in fallacies_result:
            fallacies_list = fallacies_result['fallacies']
            if fallacies_list:
                report += f"Sophismes détectés: {len(fallacies_list)}\n"
                for i, fallacy in enumerate(fallacies_list[:5], 1):  # Max 5
                    if isinstance(fallacy, dict):
                        name = fallacy.get('nom', fallacy.get('name', 'inconnu'))
                        report += f"  {i}. {name}\n"
            else:
                report += "Aucun sophisme détecté\n"
        
        report += f"""
Authenticité: {'OUI' if fallacies_result.get('authentic') else 'NON'}
Modèle: {fallacies_result.get('model_used', 'N/A')}
Confiance: {fallacies_result.get('confidence', 0):.2f}

PERFORMANCE
----------
Interactions totales: {len(self.traces)}
Agents différents: {len(agents)}
Durée moyenne/interaction: {total_duration / len(self.traces) if self.traces else 0:.2f}s
Taux de succès: {sum(1 for t in self.traces if t['success']) / len(self.traces) * 100 if self.traces else 0:.1f}%

"""
        
        return report

async def load_test_text():
    """Charge un texte de test avec quelques sophismes évidents."""
    return {
        'text': """
        Le gouvernement français doit absolument réformer le système éducatif immédiatement.
        Tous les experts pédagogiques reconnus s'accordent unanimement à dire que notre méthode révolutionnaire est la seule solution viable.
        Si nous n'agissons pas maintenant, c'est l'échec scolaire catastrophique garanti pour toute une génération d'enfants.
        Les partis d'opposition ne proposent que des mesures complètement dépassées qui ont déjà lamentablement échoué en Finlande et en Suède.
        Cette réforme éducative permettra miraculeusement de créer des millions d'emplois et de sauver définitivement notre économie.
        Seuls les parents vraiment responsables et qui aiment leurs enfants soutiendront cette initiative cruciale pour l'avenir.
        """,
        'title': 'Discours Politique - Réforme Éducative',
        'source': 'Test politique',
        'length': 0,  # Sera calculé
        'type': 'Texte politique de test',
        'preview': ''  # Sera rempli
    }

async def orchestrate_with_existing_tools():
    """Orchestre une analyse complexe en utilisant les outils existants."""
    
    load_dotenv()
    tracker = SimpleTracker()
    
    logger.info(f"DEBUT orchestration - Session {tracker.session_id}")
    
    try:
        # 1. Charger un texte de test
        logger.info("Chargement texte de test...")
        extract_info = await load_test_text()
        extract_info['length'] = len(extract_info['text'])
        extract_info['preview'] = extract_info['text'][:200]
        
        tracker.log_interaction(
            agent="TextLoader",
            action="load_test_text", 
            input_text="Chargement texte test",
            output=f"Texte chargé: {extract_info['length']} chars"
        )
        
        logger.info(f"Texte chargé: {extract_info['title']} ({extract_info['length']} caractères)")
        
        # 2. Configuration du pipeline pour analyse authentique
        analysis_config = AnalysisConfig(
            analysis_modes=[AnalysisMode.FALLACIES],
            enable_parallel=False,
            require_real_llm=True,
            enable_fallback=True,
            retry_count=1,
            mock_level="none",
            llm_model="gpt-4o-mini"
        )
        
        pipeline = UnifiedAnalysisPipeline(analysis_config)
        
        # 3. Analyse avec GPT-4o-mini
        logger.info("DEBUT analyse sophismes avec GPT-4o-mini...")
        start_time = datetime.now()
        
        fallacies_result = await pipeline.analyze_text(extract_info['text'], SourceType.TEXT)
        
        duration = (datetime.now() - start_time).total_seconds()
        tracker.log_interaction(
            agent="InformalAnalysisAgent",
            action="analyze_fallacies_gpt4o",
            input_text=extract_info['text'],
            output=fallacies_result.results,
            duration=duration
        )
        
        logger.info(f"Analyse terminée en {duration:.2f}s")
        
        # 4. Compilation des résultats
        final_results = {
            "fallacies": fallacies_result.results.get('fallacies', {}),
            "total_agents": len(set(t['agent'] for t in tracker.traces)),
            "total_interactions": len(tracker.traces)
        }
        
        # 5. Génération du rapport simple
        logger.info("Génération rapport...")
        report = tracker.generate_simple_report(extract_info, final_results)
        
        # 6. Sauvegarde
        report_filename = f"rapport_simple_{tracker.session_id}.txt"
        report_path = Path(report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Rapport sauvegardé: {report_path.absolute()}")
        
        # 7. Affichage sécurisé des résultats
        safe_print("\n" + "="*60)
        safe_print("ORCHESTRATION TERMINEE AVEC SUCCES")
        safe_print("="*60)
        safe_print(f"Rapport généré: {report_filename}")
        safe_print(f"Agents utilisés: {final_results['total_agents']}")
        safe_print(f"Interactions: {final_results['total_interactions']}")
        safe_print(f"Durée: {(datetime.now() - tracker.start_time).total_seconds():.2f}s")
        
        # Affichage des résultats clés
        fallacies_data = final_results['fallacies']
        if isinstance(fallacies_data, dict):
            authentic = fallacies_data.get('authentic', False)
            model = fallacies_data.get('model_used', 'N/A')
            safe_print(f"Authentique: {'OUI' if authentic else 'NON'}")
            safe_print(f"Modèle: {model}")
            
            if 'fallacies' in fallacies_data:
                fallacy_list = fallacies_data['fallacies']
                safe_print(f"Sophismes trouvés: {len(fallacy_list) if fallacy_list else 0}")
        
        safe_print("="*60)
        
        return True, report_path
        
    except Exception as e:
        logger.error(f"Erreur orchestration: {e}", exc_info=True)
        return False, None

if __name__ == "__main__":
    success, report_path = asyncio.run(orchestrate_with_existing_tools())
    if success:
        safe_print(f"\nSUCCES! Rapport: {report_path}")
    else:
        safe_print("\nECHEC de l'orchestration")