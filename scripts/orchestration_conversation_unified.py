#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ORCHESTRATION CONVERSATIONNELLE UNIFIÉE
=======================================

Script unifié pour l'orchestration conversationnelle avec intégration
de tous les composants d'analyse d'argumentation.
"""

import asyncio
import sys
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ajout du répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
from argumentation_analysis.pipelines.unified_text_analysis import UnifiedTextAnalyzer


class UnifiedConversationOrchestration:
    """
    Orchestration conversationnelle unifiée.
    
    Combine l'orchestrateur conversationnel avec l'analyse unifiée
    pour une expérience complète d'analyse d'argumentation.
    """
    
    def __init__(self):
        """Initialise l'orchestration."""
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        self.conversation_orchestrator = None
        self.unified_analyzer = None
        self.active_sessions = {}
        
        self.logger.info("Orchestration conversationnelle unifiée initialisée")
    
    def setup_logging(self):
        """Configure le logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def initialize(self) -> bool:
        """
        Initialise tous les composants.
        
        Returns:
            bool: True si l'initialisation réussit
        """
        try:
            print("🚀 Initialisation de l'orchestration conversationnelle unifiée...")
            
            # Initialiser l'orchestrateur conversationnel
            self.conversation_orchestrator = ConversationOrchestrator()
            await self.conversation_orchestrator.initialize()
            
            # Initialiser l'analyseur unifié
            self.unified_analyzer = UnifiedTextAnalyzer()
            
            print("✅ Orchestration conversationnelle unifiée initialisée")
            return True
            
        except Exception as e:
            print(f"❌ Erreur d'initialisation: {e}")
            self.logger.error(f"Erreur d'initialisation: {e}")
            return False
    
    async def create_unified_session(self, context: Optional[Dict] = None) -> str:
        """
        Crée une session conversationnelle unifiée.
        
        Args:
            context: Contexte optionnel pour la session
            
        Returns:
            ID de la session créée
        """
        session_id = await self.conversation_orchestrator.create_session()
        
        self.active_sessions[session_id] = {
            'created_at': datetime.now(),
            'context': context or {},
            'analysis_count': 0
        }
        
        print(f"🆔 Session unifiée créée: {session_id}")
        return session_id
    
    async def analyze_conversation_unified(
        self, 
        session_id: str, 
        text: str, 
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyse conversationnelle avec analyse unifiée.
        
        Args:
            session_id: ID de la session
            text: Texte à analyser
            context: Contexte additionnel
            
        Returns:
            Résultats combinés des analyses
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} non trouvée")
        
        try:
            # Analyse conversationnelle
            conv_result = await self.conversation_orchestrator.analyze_conversation(
                session_id=session_id,
                text=text,
                context=context
            )
            
            # Analyse unifiée
            unified_result = self.unified_analyzer.analyze_text(text)
            
            # Combiner les résultats
            combined_result = {
                'session_id': session_id,
                'text': text,
                'conversation_analysis': conv_result,
                'unified_analysis': unified_result,
                'timestamp': datetime.now().isoformat(),
                'context': context
            }
            
            # Mettre à jour les statistiques de session
            self.active_sessions[session_id]['analysis_count'] += 1
            
            print(f"✅ Analyse conversationnelle unifiée terminée pour session {session_id}")
            return combined_result
            
        except Exception as e:
            print(f"❌ Erreur lors de l'analyse: {e}")
            self.logger.error(f"Erreur d'analyse pour session {session_id}: {e}")
            raise
    
    async def close_unified_session(self, session_id: str) -> Dict[str, Any]:
        """
        Ferme une session unifiée.
        
        Args:
            session_id: ID de la session à fermer
            
        Returns:
            Statistiques de la session fermée
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} non trouvée")
        
        try:
            # Fermer la session conversationnelle
            await self.conversation_orchestrator.close_session(session_id)
            
            # Récupérer les statistiques
            session_stats = self.active_sessions[session_id].copy()
            session_stats['closed_at'] = datetime.now()
            session_stats['duration'] = (
                session_stats['closed_at'] - session_stats['created_at']
            ).total_seconds()
            
            # Supprimer de la liste active
            del self.active_sessions[session_id]
            
            print(f"🔚 Session unifiée {session_id} fermée")
            return session_stats
            
        except Exception as e:
            print(f"❌ Erreur lors de la fermeture: {e}")
            self.logger.error(f"Erreur de fermeture pour session {session_id}: {e}")
            raise
    
    async def get_unified_status(self) -> Dict[str, Any]:
        """
        Retourne l'état de l'orchestration unifiée.
        
        Returns:
            État complet du système
        """
        try:
            conv_status = await self.conversation_orchestrator.get_system_status()
            
            return {
                'active_sessions': len(self.active_sessions),
                'session_details': {
                    sid: {
                        'created_at': session['created_at'].isoformat(),
                        'analysis_count': session['analysis_count'],
                        'context': session['context']
                    }
                    for sid, session in self.active_sessions.items()
                },
                'conversation_orchestrator_status': conv_status,
                'unified_analyzer_available': self.unified_analyzer is not None
            }
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération du statut: {e}")
            return {'error': str(e)}


async def demo_unified_orchestration():
    """Démonstration de l'orchestration unifiée."""
    print("🌟 DÉMONSTRATION - ORCHESTRATION CONVERSATIONNELLE UNIFIÉE")
    print("=" * 70)
    
    # Initialiser l'orchestration
    orchestration = UnifiedConversationOrchestration()
    if not await orchestration.initialize():
        print("❌ Échec de l'initialisation")
        return False
    
    try:
        # Créer une session
        session_id = await orchestration.create_unified_session({
            'demo': True,
            'type': 'unified_demonstration'
        })
        
        # Textes de démonstration
        demo_texts = [
            "L'argumentation rationnelle est fondamentale pour un débat constructif.",
            "La logique déductive part de prémisses générales vers des conclusions spécifiques.",
            "L'analyse rhétorique examine les moyens de persuasion utilisés dans un discours."
        ]
        
        # Analyser chaque texte
        results = []
        for i, text in enumerate(demo_texts, 1):
            print(f"\n🔍 Analyse {i}: {text[:50]}...")
            
            result = await orchestration.analyze_conversation_unified(
                session_id=session_id,
                text=text,
                context={'demo_iteration': i}
            )
            
            results.append(result)
            print(f"✅ Analyse {i} terminée")
        
        # Afficher le statut
        print("\n📊 Statut de l'orchestration:")
        status = await orchestration.get_unified_status()
        for key, value in status.items():
            if key != 'session_details':
                print(f"  {key}: {value}")
        
        # Fermer la session
        session_stats = await orchestration.close_unified_session(session_id)
        print(f"\n📈 Statistiques de session:")
        print(f"  Durée: {session_stats['duration']:.2f}s")
        print(f"  Analyses: {session_stats['analysis_count']}")
        
        print("\n🎉 Démonstration terminée avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la démonstration: {e}")
        return False


async def main():
    """Fonction principale."""
    print("🚀 ORCHESTRATION CONVERSATIONNELLE UNIFIÉE")
    print("=" * 50)
    
    success = await demo_unified_orchestration()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
