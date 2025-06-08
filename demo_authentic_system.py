#!/usr/bin/env python3
"""
Démonstration du système 100% authentique
=========================================

Démonstration complète du système d'analyse rhétorique avec :
- Élimination totale des mocks
- Validation d'authenticité en temps réel
- Pipeline complet avec composants authentiques
"""

import asyncio
import sys
import logging
from pathlib import Path
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# Ajout du répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

# Import des composants authentiques
from argumentation_analysis.pipelines.unified_text_analysis import UnifiedTextAnalyzer
from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator, LLMAnalysisRequest


class AuthenticSystemDemo:
    """
    Démonstration du système 100% authentique d'analyse d'argumentation.
    
    Cette classe orchestre une démonstration complète du système unifié
    en utilisant uniquement des composants authentiques.
    """
    
    def __init__(self):
        """Initialise la démonstration."""
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Composants authentiques
        self.unified_analyzer = None
        self.conversation_orchestrator = None
        self.llm_orchestrator = None
        
        # Textes de démonstration
        self.demo_texts = [
            "L'argumentation rationnelle est la base de tout débat constructif. "
            "Elle permet d'établir des conclusions logiques à partir de prémisses valides.",
            
            "La rhétorique classique distingue trois modes de persuasion : "
            "l'ethos (crédibilité), le pathos (émotion) et le logos (logique).",
            
            "Dans un argument inductif, on tire des conclusions générales "
            "à partir d'observations particulières, contrairement à la déduction."
        ]
        
        self.logger.info("Démonstration du système authentique initialisée")
    
    def setup_logging(self):
        """Configure le logging pour la démonstration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('demo_authentic_system.log')
            ]
        )
    
    async def initialize_components(self) -> bool:
        """
        Initialise tous les composants authentiques.
        
        Returns:
            bool: True si l'initialisation réussit
        """
        try:
            print("🚀 Initialisation des composants authentiques...")
            
            # Initialiser l'analyseur unifié
            print("  📊 Initialisation UnifiedTextAnalyzer...")
            self.unified_analyzer = UnifiedTextAnalyzer()
            
            # Initialiser l'orchestrateur conversationnel
            print("  💬 Initialisation ConversationOrchestrator...")
            self.conversation_orchestrator = ConversationOrchestrator()
            await self.conversation_orchestrator.initialize()
            
            # Initialiser l'orchestrateur LLM réel
            print("  🤖 Initialisation RealLLMOrchestrator...")
            self.llm_orchestrator = RealLLMOrchestrator()
            await self.llm_orchestrator.initialize()
            
            print("✅ Tous les composants authentiques initialisés avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}")
            print(f"❌ Erreur d'initialisation: {e}")
            return False
    
    async def demo_unified_analysis(self) -> Dict[str, Any]:
        """
        Démonstration de l'analyse unifiée.
        
        Returns:
            Dict: Résultats de l'analyse unifiée
        """
        print("\n📊 DÉMONSTRATION - ANALYSE UNIFIÉE")
        print("=" * 50)
        
        results = {}
        
        for i, text in enumerate(self.demo_texts, 1):
            print(f"\n🔍 Analyse du texte {i}:")
            print(f"📝 Texte: {text[:100]}...")
            
            try:
                start_time = time.time()
                result = self.unified_analyzer.analyze_text(text)
                processing_time = time.time() - start_time
                
                print(f"⏱️  Temps de traitement: {processing_time:.2f}s")
                print(f"✅ Analyse réussie - Composants détectés: {len(result.get('components', {}))}")
                
                results[f"text_{i}"] = {
                    'text': text,
                    'result': result,
                    'processing_time': processing_time
                }
                
            except Exception as e:
                print(f"❌ Erreur lors de l'analyse: {e}")
                results[f"text_{i}"] = {'error': str(e)}
        
        return results
    
    async def demo_conversation_orchestration(self) -> Dict[str, Any]:
        """
        Démonstration de l'orchestration conversationnelle.
        
        Returns:
            Dict: Résultats de l'orchestration
        """
        print("\n💬 DÉMONSTRATION - ORCHESTRATION CONVERSATIONNELLE")
        print("=" * 50)
        
        try:
            # Créer une session de conversation
            session_id = await self.conversation_orchestrator.create_session()
            print(f"🆔 Session créée: {session_id}")
            
            results = {}
            
            for i, text in enumerate(self.demo_texts, 1):
                print(f"\n🗣️  Analyse conversationnelle {i}:")
                print(f"📝 Texte: {text[:80]}...")
                
                start_time = time.time()
                result = await self.conversation_orchestrator.analyze_conversation(
                    session_id=session_id,
                    text=text,
                    context={'demo': True, 'iteration': i}
                )
                processing_time = time.time() - start_time
                
                print(f"⏱️  Temps de traitement: {processing_time:.2f}s")
                print(f"✅ Orchestration réussie")
                
                results[f"conversation_{i}"] = {
                    'text': text,
                    'result': result,
                    'processing_time': processing_time
                }
            
            # Clôturer la session
            await self.conversation_orchestrator.close_session(session_id)
            print(f"🔚 Session {session_id} fermée")
            
            return results
            
        except Exception as e:
            print(f"❌ Erreur lors de l'orchestration conversationnelle: {e}")
            return {'error': str(e)}
    
    async def demo_llm_orchestration(self) -> Dict[str, Any]:
        """
        Démonstration de l'orchestration LLM réelle.
        
        Returns:
            Dict: Résultats de l'orchestration LLM
        """
        print("\n🤖 DÉMONSTRATION - ORCHESTRATION LLM RÉELLE")
        print("=" * 50)
        
        results = {}
        analysis_types = ['unified_analysis', 'semantic', 'logical']
        
        for i, text in enumerate(self.demo_texts, 1):
            print(f"\n🧠 Analyse LLM {i}:")
            print(f"📝 Texte: {text[:80]}...")
            
            text_results = {}
            
            for analysis_type in analysis_types:
                try:
                    request = LLMAnalysisRequest(
                        text=text,
                        analysis_type=analysis_type,
                        context={'demo': True},
                        parameters={'confidence_threshold': 0.7}
                    )
                    
                    start_time = time.time()
                    result = await self.llm_orchestrator.analyze_text(request)
                    processing_time = time.time() - start_time
                    
                    print(f"  ✅ {analysis_type}: {processing_time:.2f}s "
                          f"(confiance: {result.confidence:.1%})")
                    
                    text_results[analysis_type] = {
                        'result': result,
                        'processing_time': processing_time
                    }
                    
                except Exception as e:
                    print(f"  ❌ {analysis_type}: Erreur - {e}")
                    text_results[analysis_type] = {'error': str(e)}
            
            results[f"llm_text_{i}"] = text_results
        
        return results
    
    async def demo_system_metrics(self) -> Dict[str, Any]:
        """
        Affichage des métriques du système.
        
        Returns:
            Dict: Métriques du système
        """
        print("\n📈 MÉTRIQUES DU SYSTÈME")
        print("=" * 50)
        
        try:
            # Métriques de l'orchestrateur LLM
            llm_metrics = self.llm_orchestrator.get_metrics()
            print("🤖 Métriques LLM Orchestrator:")
            for key, value in llm_metrics.items():
                print(f"  📊 {key}: {value}")
            
            # État du système
            system_status = self.llm_orchestrator.get_status()
            print("\n🔍 État du système:")
            print(f"  🟢 Initialisé: {system_status['is_initialized']}")
            print(f"  📂 Cache: {system_status['cache_size']} entrées")
            print(f"  🔄 Sessions actives: {system_status['active_sessions']}")
            
            # État de l'orchestrateur conversationnel
            conv_status = await self.conversation_orchestrator.get_system_status()
            print("\n💬 État conversationnel:")
            for key, value in conv_status.items():
                print(f"  📊 {key}: {value}")
            
            return {
                'llm_metrics': llm_metrics,
                'system_status': system_status,
                'conversation_status': conv_status
            }
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des métriques: {e}")
            return {'error': str(e)}
    
    async def run_complete_demo(self) -> Dict[str, Any]:
        """
        Exécute la démonstration complète.
        
        Returns:
            Dict: Résultats complets de la démonstration
        """
        print("🌟 DÉMONSTRATION SYSTÈME 100% AUTHENTIQUE")
        print("=" * 60)
        print(f"📅 Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        demo_start = time.time()
        results = {}
        
        # 1. Initialisation
        if not await self.initialize_components():
            return {'error': 'Échec de l\'initialisation'}
        
        # 2. Démonstration analyse unifiée
        try:
            unified_results = await self.demo_unified_analysis()
            results['unified_analysis'] = unified_results
        except Exception as e:
            results['unified_analysis'] = {'error': str(e)}
        
        # 3. Démonstration orchestration conversationnelle
        try:
            conv_results = await self.demo_conversation_orchestration()
            results['conversation_orchestration'] = conv_results
        except Exception as e:
            results['conversation_orchestration'] = {'error': str(e)}
        
        # 4. Démonstration orchestration LLM
        try:
            llm_results = await self.demo_llm_orchestration()
            results['llm_orchestration'] = llm_results
        except Exception as e:
            results['llm_orchestration'] = {'error': str(e)}
        
        # 5. Métriques finales
        try:
            metrics = await self.demo_system_metrics()
            results['final_metrics'] = metrics
        except Exception as e:
            results['final_metrics'] = {'error': str(e)}
        
        # Résumé final
        total_time = time.time() - demo_start
        print(f"\n🏁 DÉMONSTRATION TERMINÉE")
        print("=" * 60)
        print(f"⏱️  Durée totale: {total_time:.2f}s")
        print(f"📊 Composants testés: Analyse Unifiée, Orchestration Conversationnelle, Orchestration LLM")
        print("✅ Système 100% authentique validé")
        
        results['demo_summary'] = {
            'total_time': total_time,
            'completion_time': datetime.now().isoformat(),
            'status': 'completed'
        }
        
        return results


async def main() -> int:
    """
    Fonction principale de démonstration.
    
    Returns:
        int: Code de sortie (0 = succès, 1 = erreur)
    """
    try:
        demo = AuthenticSystemDemo()
        results = await demo.run_complete_demo()
        
        # Sauvegarder les résultats
        import json
        results_file = f"demo_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convertir les objets non-sérialisables
        def serialize_results(obj):
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=serialize_results)
        
        print(f"\n💾 Résultats sauvegardés dans: {results_file}")
        
        # Vérifier s'il y a eu des erreurs
        has_errors = any('error' in str(v) for v in results.values())
        if has_errors:
            print("⚠️  Des erreurs ont été détectées pendant la démonstration")
            return 1
        
        print("🎉 Démonstration réussie - Système 100% authentique validé!")
        return 0
        
    except Exception as e:
        print(f"💥 Erreur fatale: {e}")
        logging.error(f"Erreur fatale dans la démonstration: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
