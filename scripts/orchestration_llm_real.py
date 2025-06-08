#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestration conversationnelle avec VRAIS agents LLM
====================================================

Script d'orchestration utilisant le RealLLMOrchestrator pour des analyses
authentiques avec de vrais agents LLM.
"""

import asyncio
import sys
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ajout du répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator, LLMAnalysisRequest


class RealLLMConversationOrchestration:
    """
    Orchestration conversationnelle avec de vrais agents LLM.
    
    Utilise le RealLLMOrchestrator pour effectuer des analyses
    authentiques d'argumentation avec de vrais modèles LLM.
    """
    
    def __init__(self):
        """Initialise l'orchestration LLM réelle."""
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        self.llm_orchestrator = None
        self.conversation_history = []
        
        self.logger.info("Orchestration LLM réelle initialisée")
    
    def setup_logging(self):
        """Configure le logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def initialize(self) -> bool:
        """
        Initialise l'orchestrateur LLM réel.
        
        Returns:
            bool: True si l'initialisation réussit
        """
        try:
            print("🚀 Initialisation de l'orchestration LLM réelle...")
            
            self.llm_orchestrator = RealLLMOrchestrator()
            success = await self.llm_orchestrator.initialize()
            
            if success:
                print("✅ Orchestration LLM réelle initialisée")
            else:
                print("❌ Échec de l'initialisation LLM")
                
            return success
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation: {e}")
            self.logger.error(f"Erreur d'initialisation: {e}")
            return False
    
    async def analyze_with_real_llm(
        self,
        text: str,
        analysis_type: str = "unified_analysis",
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyse un texte avec de vrais agents LLM.
        
        Args:
            text: Texte à analyser
            analysis_type: Type d'analyse à effectuer
            context: Contexte optionnel
            
        Returns:
            Résultats de l'analyse LLM
        """
        try:
            request = LLMAnalysisRequest(
                text=text,
                analysis_type=analysis_type,
                context=context or {},
                parameters={'use_real_llm': True}
            )
            
            print(f"🤖 Analyse LLM réelle: {analysis_type}")
            print(f"📝 Texte: {text[:60]}...")
            
            result = await self.llm_orchestrator.analyze_text(request)
            
            # Ajouter à l'historique
            self.conversation_history.append({
                'timestamp': datetime.now(),
                'text': text,
                'analysis_type': analysis_type,
                'result': result,
                'context': context
            })
            
            print(f"✅ Analyse terminée (confiance: {result.confidence:.1%})")
            return result
            
        except Exception as e:
            print(f"❌ Erreur lors de l'analyse LLM: {e}")
            self.logger.error(f"Erreur d'analyse LLM: {e}")
            raise
    
    async def conversation_with_llm_agents(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Conduit une conversation avec plusieurs agents LLM.
        
        Args:
            texts: Liste de textes à analyser
            
        Returns:
            Liste des résultats d'analyse
        """
        print(f"🗣️  Démarrage conversation avec {len(texts)} textes")
        
        results = []
        analysis_types = ['syntactic', 'semantic', 'logical', 'unified_analysis']
        
        for i, text in enumerate(texts, 1):
            print(f"\n💬 Message {i}/{len(texts)}")
            
            # Analyser avec différents types d'agents LLM
            text_results = {}
            
            for analysis_type in analysis_types:
                try:
                    result = await self.analyze_with_real_llm(
                        text=text,
                        analysis_type=analysis_type,
                        context={
                            'conversation_turn': i,
                            'total_turns': len(texts),
                            'agent_type': analysis_type
                        }
                    )
                    
                    text_results[analysis_type] = result
                    
                except Exception as e:
                    print(f"  ❌ Erreur {analysis_type}: {e}")
                    text_results[analysis_type] = {'error': str(e)}
            
            results.append({
                'text': text,
                'turn': i,
                'analyses': text_results
            })
        
        return results
    
    async def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé de la conversation.
        
        Returns:
            Résumé avec statistiques et métriques
        """
        if not self.conversation_history:
            return {'message': 'Aucune conversation en cours'}
        
        # Calculer les statistiques
        total_analyses = len(self.conversation_history)
        analysis_types = {}
        total_confidence = 0
        
        for entry in self.conversation_history:
            analysis_type = entry['analysis_type']
            analysis_types[analysis_type] = analysis_types.get(analysis_type, 0) + 1
            total_confidence += entry['result'].confidence
        
        avg_confidence = total_confidence / total_analyses if total_analyses > 0 else 0
        
        # Métriques LLM
        llm_metrics = self.llm_orchestrator.get_metrics()
        
        return {
            'conversation_stats': {
                'total_analyses': total_analyses,
                'analysis_types': analysis_types,
                'average_confidence': avg_confidence,
                'duration': (
                    self.conversation_history[-1]['timestamp'] - 
                    self.conversation_history[0]['timestamp']
                ).total_seconds() if len(self.conversation_history) > 1 else 0
            },
            'llm_metrics': llm_metrics,
            'last_analysis': self.conversation_history[-1]['timestamp'].isoformat()
        }


async def demo_real_llm_orchestration():
    """Démonstration de l'orchestration LLM réelle."""
    print("🌟 DÉMONSTRATION - ORCHESTRATION LLM RÉELLE")
    print("=" * 60)
    
    # Initialiser l'orchestration
    orchestration = RealLLMConversationOrchestration()
    if not await orchestration.initialize():
        print("❌ Échec de l'initialisation")
        return False
    
    try:
        # Textes de démonstration pour conversation
        demo_texts = [
            "L'argumentation déductive part de prémisses générales pour aboutir à des conclusions spécifiques.",
            "La rhétorique aristotélicienne distingue trois modes de persuasion : ethos, pathos, et logos.",
            "L'analyse critique d'arguments nécessite l'évaluation de la validité logique et de la vérité des prémisses."
        ]
        
        # Conduire la conversation avec les agents LLM
        results = await orchestration.conversation_with_llm_agents(demo_texts)
        
        # Afficher les résultats
        print(f"\n📊 RÉSULTATS DE LA CONVERSATION")
        print("=" * 60)
        
        for result in results:
            print(f"\n💬 Tour {result['turn']}: {result['text'][:50]}...")
            analyses = result['analyses']
            
            for analysis_type, analysis_result in analyses.items():
                if 'error' in analysis_result:
                    print(f"  ❌ {analysis_type}: {analysis_result['error']}")
                else:
                    confidence = analysis_result.confidence
                    print(f"  ✅ {analysis_type}: {confidence:.1%} confiance")
        
        # Afficher le résumé
        summary = await orchestration.get_conversation_summary()
        print(f"\n📈 RÉSUMÉ DE LA CONVERSATION")
        print("=" * 60)
        
        stats = summary['conversation_stats']
        print(f"Total analyses: {stats['total_analyses']}")
        print(f"Confiance moyenne: {stats['average_confidence']:.1%}")
        print(f"Durée: {stats['duration']:.2f}s")
        print(f"Types d'analyse: {list(stats['analysis_types'].keys())}")
        
        print("\n🎉 Démonstration terminée avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la démonstration: {e}")
        return False


async def main():
    """Fonction principale."""
    print("🤖 ORCHESTRATION CONVERSATIONNELLE - VRAIS AGENTS LLM")
    print("=" * 55)
    
    success = await demo_real_llm_orchestration()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
