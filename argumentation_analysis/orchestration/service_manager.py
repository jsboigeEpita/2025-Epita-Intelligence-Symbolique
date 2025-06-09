#!/usr/bin/env python3
"""
ServiceManager - Gestionnaire Unifié des Services d'Orchestration
================================================================

Module principal qui fournit une interface unifiée pour tous les services
d'orchestration du système d'analyse argumentative.

Ce ServiceManager coordonne :
- Les gestionnaires hiérarchiques (Stratégique, Tactique, Opérationnel)
- Les orchestrateurs spécialisés (Cluedo, Logique, Conversation)
- Les services de communication et de middleware
- L'interface avec les agents d'analyse

Version: 1.0.0
Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Union, Callable, Type
from datetime import datetime
from pathlib import Path
import json

# Imports du système de base
from argumentation_analysis.paths import DATA_DIR, RESULTS_DIR

# Imports des gestionnaires hiérarchiques
try:
    from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
    from argumentation_analysis.orchestration.hierarchical.tactical.manager import TacticalManager  
    from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
except ImportError as e:
    logging.warning(f"Certains gestionnaires hiérarchiques ne sont pas disponibles: {e}")
    StrategicManager = None
    TacticalManager = None
    OperationalManager = None

# Imports des orchestrateurs spécialisés
try:
    from argumentation_analysis.orchestration.cluedo_orchestrator import CluedoOrchestrator
    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
except ImportError as e:
    logging.warning(f"Certains orchestrateurs spécialisés ne sont pas disponibles: {e}")
    CluedoOrchestrator = None
    ConversationOrchestrator = None
    RealLLMOrchestrator = None

# Imports des systèmes de communication
try:
    from argumentation_analysis.core.communication import (
        MessageMiddleware, Message, ChannelType, 
        MessagePriority, MessageType, AgentLevel
    )
except ImportError as e:
    logging.warning(f"Système de communication non disponible: {e}")
    MessageMiddleware = None


class ServiceManagerError(Exception):
    """Exception spécifique au ServiceManager."""
    pass


class ServiceManagerState:
    """Classe pour gérer l'état du ServiceManager."""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.active_services = {}
        self.service_states = {}
        self.last_activity = datetime.now()
        
    def update_activity(self):
        """Met à jour le timestamp de dernière activité."""
        self.last_activity = datetime.now()
        
    def get_uptime(self) -> float:
        """Retourne le temps de fonctionnement en secondes."""
        return (datetime.now() - self.start_time).total_seconds()


class OrchestrationServiceManager:
    """
    Gestionnaire Unifié des Services d'Orchestration.
    
    Cette classe principale coordonne tous les services d'orchestration
    et fournit une interface unifiée pour :
    
    - Gestion des gestionnaires hiérarchiques
    - Coordination des orchestrateurs spécialisés
    - Interface avec les agents d'analyse
    - Gestion des communications inter-services
    - Monitoring et logging centralisé
    
    Exemple d'utilisation:
    
    ```python
    # Création du service manager
    service_manager = OrchestrationServiceManager()
    
    # Initialisation des services
    await service_manager.initialize()
    
    # Analyse d'un texte
    result = await service_manager.analyze_text("Votre texte ici")
    
    # Nettoyage
    await service_manager.shutdown()
    ```
    """
    
    def __init__(self, 
                 config: Optional[Dict[str, Any]] = None,
                 enable_logging: bool = True,
                 log_level: int = logging.INFO):
        """
        Initialise le ServiceManager.
        
        Args:
            config: Configuration optionnelle du service manager
            enable_logging: Active/désactive le logging
            log_level: Niveau de logging
        """
        # Configuration de base
        self.config = config or self._get_default_config()
        self.state = ServiceManagerState()
        
        # Configuration du logging
        if enable_logging:
            self._setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        
        # Gestionnaires et orchestrateurs
        self.strategic_manager: Optional[StrategicManager] = None
        self.tactical_manager: Optional[TacticalManager] = None
        self.operational_manager: Optional[OperationalManager] = None
        
        # Orchestrateurs spécialisés
        self.cluedo_orchestrator: Optional[CluedoOrchestrator] = None
        self.conversation_orchestrator: Optional[ConversationOrchestrator] = None
        self.llm_orchestrator: Optional[RealLLMOrchestrator] = None
        
        # Middleware de communication
        self.middleware: Optional[MessageMiddleware] = None
        
        # État d'initialisation
        self._initialized = False
        self._shutdown = False
        
        self.logger.info(f"ServiceManager créé avec session_id: {self.state.session_id}")
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut."""
        return {
            'enable_hierarchical': True,
            'enable_specialized_orchestrators': True,
            'enable_communication_middleware': True,
            'max_concurrent_analyses': 10,
            'analysis_timeout': 300,  # 5 minutes
            'auto_cleanup': True,
            'save_results': True,
            'results_dir': str(RESULTS_DIR),
            'data_dir': str(DATA_DIR)
        }
        
    def _setup_logging(self, log_level: int):
        """Configure le système de logging."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)s] [ServiceManager] %(message)s',
            datefmt='%H:%M:%S'
        )
        
    async def initialize(self) -> bool:
        """
        Initialise tous les services.
        
        Returns:
            True si l'initialisation réussit, False sinon
        """
        if self._initialized:
            self.logger.warning("ServiceManager déjà initialisé")
            return True
            
        try:
            self.logger.info("Initialisation du ServiceManager...")
            
            # Initialisation du middleware de communication
            if self.config.get('enable_communication_middleware', True) and MessageMiddleware:
                self.middleware = MessageMiddleware()
                self.logger.info("Middleware de communication initialisé")
                
            # Initialisation des gestionnaires hiérarchiques
            if self.config.get('enable_hierarchical', True):
                await self._initialize_hierarchical_managers()
                
            # Initialisation des orchestrateurs spécialisés
            if self.config.get('enable_specialized_orchestrators', True):
                await self._initialize_specialized_orchestrators()
                
            self._initialized = True
            self.state.update_activity()
            
            self.logger.info("ServiceManager initialisé avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}")
            return False
            
    async def _initialize_hierarchical_managers(self):
        """Initialise les gestionnaires hiérarchiques."""
        try:
            if StrategicManager:
                self.strategic_manager = StrategicManager(middleware=self.middleware)
                self.logger.info("StrategicManager initialisé")
                
            if TacticalManager:
                self.tactical_manager = TacticalManager(middleware=self.middleware)
                self.logger.info("TacticalManager initialisé")
                
            if OperationalManager:
                self.operational_manager = OperationalManager(middleware=self.middleware)
                self.logger.info("OperationalManager initialisé")
                
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'initialisation des gestionnaires hiérarchiques: {e}")
            
    async def _initialize_specialized_orchestrators(self):
        """Initialise les orchestrateurs spécialisés."""
        try:
            if CluedoOrchestrator:
                self.cluedo_orchestrator = CluedoOrchestrator()
                self.logger.info("CluedoOrchestrator initialisé")
                
            if ConversationOrchestrator:
                self.conversation_orchestrator = ConversationOrchestrator()
                self.logger.info("ConversationOrchestrator initialisé")
                
            if RealLLMOrchestrator:
                self.llm_orchestrator = RealLLMOrchestrator()
                self.logger.info("RealLLMOrchestrator initialisé")
                
        except Exception as e:
            self.logger.warning(f"Erreur lors de l'initialisation des orchestrateurs spécialisés: {e}")
            
    async def analyze_text(self, 
                          text: str, 
                          analysis_type: str = "comprehensive",
                          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Lance une analyse de texte en utilisant les services appropriés.
        
        Args:
            text: Le texte à analyser
            analysis_type: Type d'analyse ('comprehensive', 'logical', 'rhetorical', etc.)
            options: Options supplémentaires pour l'analyse
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse
        """
        if not self._initialized:
            raise ServiceManagerError("ServiceManager non initialisé. Appelez initialize() d'abord.")
            
        if not text or not text.strip():
            raise ServiceManagerError("Texte vide ou invalide fourni pour l'analyse.")
            
        analysis_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        self.logger.info(f"Début d'analyse {analysis_id} - Type: {analysis_type}")
        
        try:
            # Préparation des résultats
            results = {
                'analysis_id': analysis_id,
                'text': text,
                'analysis_type': analysis_type,
                'start_time': start_time.isoformat(),
                'options': options or {},
                'results': {},
                'status': 'in_progress'
            }
            
            # Sélection de l'orchestrateur approprié
            orchestrator = self._select_orchestrator(analysis_type)
            
            if orchestrator:
                # Analyse avec orchestrateur spécialisé
                orchestrator_results = await self._run_specialized_analysis(
                    orchestrator, text, options
                )
                results['results']['specialized'] = orchestrator_results
            else:
                # Analyse générique avec gestionnaires hiérarchiques
                hierarchical_results = await self._run_hierarchical_analysis(
                    text, analysis_type, options
                )
                results['results']['hierarchical'] = hierarchical_results
                
            # Métadonnées finales
            end_time = datetime.now()
            results.update({
                'end_time': end_time.isoformat(),
                'duration': (end_time - start_time).total_seconds(),
                'status': 'completed'
            })
            
            # Sauvegarde si configurée
            if self.config.get('save_results', True):
                await self._save_results(results)
                
            self.state.update_activity()
            self.logger.info(f"Analyse {analysis_id} terminée avec succès")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse {analysis_id}: {e}")
            return {
                'analysis_id': analysis_id,
                'text': text,
                'analysis_type': analysis_type,
                'status': 'failed',
                'error': str(e),
                'end_time': datetime.now().isoformat()
            }
            
    def _select_orchestrator(self, analysis_type: str) -> Optional[Any]:
        """Sélectionne l'orchestrateur approprié selon le type d'analyse."""
        orchestrator_map = {
            'cluedo': self.cluedo_orchestrator,
            'detective': self.cluedo_orchestrator,
            'conversation': self.conversation_orchestrator,
            'dialogue': self.conversation_orchestrator,
            'llm': self.llm_orchestrator,
            'language_model': self.llm_orchestrator
        }
        
        return orchestrator_map.get(analysis_type.lower())
        
    async def _run_specialized_analysis(self, 
                                      orchestrator: Any, 
                                      text: str, 
                                      options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Lance une analyse avec un orchestrateur spécialisé."""
        try:
            # Interface générique pour les orchestrateurs
            if hasattr(orchestrator, 'analyze'):
                return await orchestrator.analyze(text, options)
            elif hasattr(orchestrator, 'process'):
                return await orchestrator.process(text, options)
            else:
                # Fallback : analyse basique
                return {
                    'method': 'fallback',
                    'text_length': len(text),
                    'word_count': len(text.split()),
                    'orchestrator': orchestrator.__class__.__name__
                }
        except Exception as e:
            self.logger.warning(f"Erreur dans l'orchestrateur spécialisé: {e}")
            return {'error': str(e), 'method': 'specialized_failed'}
            
    async def _run_hierarchical_analysis(self, 
                                       text: str, 
                                       analysis_type: str, 
                                       options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Lance une analyse avec les gestionnaires hiérarchiques."""
        results = {}
        
        try:
            # Analyse stratégique
            if self.strategic_manager:
                try:
                    strategic_result = await self._run_strategic_analysis(text, options)
                    results['strategic'] = strategic_result
                except Exception as e:
                    results['strategic'] = {'error': str(e)}
                    
            # Analyse tactique  
            if self.tactical_manager:
                try:
                    tactical_result = await self._run_tactical_analysis(text, options)
                    results['tactical'] = tactical_result
                except Exception as e:
                    results['tactical'] = {'error': str(e)}
                    
            # Analyse opérationnelle
            if self.operational_manager:
                try:
                    operational_result = await self._run_operational_analysis(text, options)
                    results['operational'] = operational_result
                except Exception as e:
                    results['operational'] = {'error': str(e)}
                    
            return results
            
        except Exception as e:
            self.logger.error(f"Erreur dans l'analyse hiérarchique: {e}")
            return {'error': str(e), 'method': 'hierarchical_failed'}
            
    async def _run_strategic_analysis(self, text: str, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Lance l'analyse stratégique."""
        return {
            'level': 'strategic',
            'text_analysis': {
                'length': len(text),
                'complexity': 'medium' if len(text) > 100 else 'simple'
            },
            'manager': 'StrategicManager'
        }
        
    async def _run_tactical_analysis(self, text: str, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Lance l'analyse tactique."""
        return {
            'level': 'tactical', 
            'processing': {
                'word_count': len(text.split()),
                'sentence_estimation': text.count('.') + text.count('!') + text.count('?')
            },
            'manager': 'TacticalManager'
        }
        
    async def _run_operational_analysis(self, text: str, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Lance l'analyse opérationnelle."""
        return {
            'level': 'operational',
            'execution': {
                'characters': len(text),
                'words': len(text.split()),
                'timestamp': datetime.now().isoformat()
            },
            'manager': 'OperationalManager'
        }
        
    async def _save_results(self, results: Dict[str, Any]):
        """Sauvegarde les résultats d'analyse."""
        try:
            results_dir = Path(self.config['results_dir'])
            results_dir.mkdir(exist_ok=True)
            
            filename = f"analysis_{results['analysis_id']}.json"
            filepath = results_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
                
            self.logger.debug(f"Résultats sauvegardés: {filepath}")
            
        except Exception as e:
            self.logger.warning(f"Erreur lors de la sauvegarde: {e}")
            
    async def get_status(self) -> Dict[str, Any]:
        """Retourne le statut actuel du ServiceManager."""
        return {
            'session_id': self.state.session_id,
            'initialized': self._initialized,
            'uptime_seconds': self.state.get_uptime(),
            'last_activity': self.state.last_activity.isoformat(),
            'active_services': {
                'strategic_manager': self.strategic_manager is not None,
                'tactical_manager': self.tactical_manager is not None,
                'operational_manager': self.operational_manager is not None,
                'cluedo_orchestrator': self.cluedo_orchestrator is not None,
                'conversation_orchestrator': self.conversation_orchestrator is not None,
                'llm_orchestrator': self.llm_orchestrator is not None,
                'middleware': self.middleware is not None
            },
            'config': self.config
        }
        
    async def health_check(self) -> Dict[str, Any]:
        """Effectue un contrôle de santé des services."""
        health_status = {
            'overall': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Test basique de fonctionnement
        try:
            test_text = "Test de santé du ServiceManager."
            start_time = datetime.now()
            
            # Test d'analyse simple
            result = await self.analyze_text(test_text, "health_check")
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            health_status['checks']['analysis'] = {
                'status': 'ok' if result.get('status') == 'completed' else 'warning',
                'response_time_seconds': response_time
            }
            
        except Exception as e:
            health_status['overall'] = 'unhealthy'
            health_status['checks']['analysis'] = {
                'status': 'error',
                'error': str(e)
            }
            
        return health_status
        
    async def shutdown(self):
        """Arrête proprement le ServiceManager."""
        if self._shutdown:
            return
            
        self.logger.info("Arrêt du ServiceManager...")
        
        try:
            # Nettoyage des orchestrateurs
            if self.cluedo_orchestrator and hasattr(self.cluedo_orchestrator, 'shutdown'):
                await self.cluedo_orchestrator.shutdown()
                
            if self.conversation_orchestrator and hasattr(self.conversation_orchestrator, 'shutdown'):
                await self.conversation_orchestrator.shutdown()
                
            if self.llm_orchestrator and hasattr(self.llm_orchestrator, 'shutdown'):
                await self.llm_orchestrator.shutdown()
                
            # Nettoyage des gestionnaires
            if self.strategic_manager and hasattr(self.strategic_manager, 'shutdown'):
                await self.strategic_manager.shutdown()
                
            if self.tactical_manager and hasattr(self.tactical_manager, 'shutdown'):
                await self.tactical_manager.shutdown()
                
            if self.operational_manager and hasattr(self.operational_manager, 'shutdown'):
                await self.operational_manager.shutdown()
                
            # Nettoyage du middleware
            if self.middleware and hasattr(self.middleware, 'shutdown'):
                await self.middleware.shutdown()
                
            self._shutdown = True
            self.logger.info("ServiceManager arrêté proprement")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt: {e}")
            
    def __str__(self) -> str:
        return f"ServiceManager(session_id={self.state.session_id}, initialized={self._initialized})"
        
    def __repr__(self) -> str:
        return (f"ServiceManager(session_id='{self.state.session_id}', "
                f"initialized={self._initialized}, uptime={self.state.get_uptime():.1f}s)")


# Fonctions utilitaires pour faciliter l'utilisation

async def create_service_manager(config: Optional[Dict[str, Any]] = None) -> OrchestrationServiceManager:
    """
    Crée et initialise un OrchestrationServiceManager.
    
    Args:
        config: Configuration optionnelle
        
    Returns:
        OrchestrationServiceManager initialisé
    """
    manager = OrchestrationServiceManager(config)
    await manager.initialize()
    return manager


def get_default_service_manager() -> OrchestrationServiceManager:
    """
    Retourne une instance par défaut du OrchestrationServiceManager (non initialisée).
    
    Returns:
        OrchestrationServiceManager avec configuration par défaut
    """
    return OrchestrationServiceManager()


# Alias temporaire pour compatibilité - DEPRECATED
import warnings

def ServiceManager(*args, **kwargs):
    """
    DEPRECATED: Utilisez OrchestrationServiceManager à la place.
    
    Cette fonction sera supprimée dans une version future.
    Migrez votre code vers OrchestrationServiceManager.
    """
    warnings.warn(
        "ServiceManager est déprécié dans argumentation_analysis.orchestration.service_manager. "
        "Utilisez OrchestrationServiceManager à la place. "
        "Cette compatibilité sera supprimée dans une version future.",
        DeprecationWarning,
        stacklevel=2
    )
    return OrchestrationServiceManager(*args, **kwargs)


# Point d'entrée pour les tests rapides
if __name__ == "__main__":
    async def main():
        print("=== Test du ServiceManager ===")
        
        # Création et initialisation
        manager = OrchestrationServiceManager()
        success = await manager.initialize()
        
        if success:
            print("✓ ServiceManager initialisé avec succès")
            
            # Test de statut
            status = await manager.get_status()
            print(f"✓ Statut: {status['session_id']}")
            
            # Test de santé
            health = await manager.health_check()
            print(f"✓ Santé: {health['overall']}")
            
            # Test d'analyse
            result = await manager.analyze_text("Ceci est un test du ServiceManager.")
            print(f"✓ Analyse: {result['status']}")
            
            # Arrêt propre
            await manager.shutdown()
            print("✓ ServiceManager arrêté proprement")
            
        else:
            print("✗ Échec de l'initialisation du ServiceManager")
    
    # Exécution du test
    asyncio.run(main())