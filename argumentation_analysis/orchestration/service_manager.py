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

# ===== AUTO-ACTIVATION ENVIRONNEMENT =====
try:
    import argumentation_analysis.core.environment  # Auto-activation environnement intelligent
except ImportError:
    # Fallback si l'import direct ne fonctionne pas
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    try:
        import argumentation_analysis.core.environment
    except ImportError:
        # Si ça ne marche toujours pas, ignorer l'auto-env pour les tests
        pass
# =========================================
import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Union, Callable, Type
from datetime import datetime
from pathlib import Path
import json
import os
import inspect
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.config.settings import settings
from argumentation_analysis.core.llm_service import create_llm_service
# Imports du système de base
from argumentation_analysis.core.bootstrap import initialize_project_environment, ProjectContext

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
    # CORRECTIF: Importe CluedoExtendedOrchestrator et l'aliase en CluedoOrchestrator
    from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator as CluedoOrchestrator
    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
except ImportError as e:
    logging.warning(f"Certains orchestrateurs spécialisés ne sont pas disponibles: {e}")
    CluedoOrchestrator = None
    ConversationOrchestrator = None
    RealLLMOrchestrator = None

# Imports des systèmes de communication
try:
    # Utiliser les exports directs du package communication grâce à son __init__.py
    from argumentation_analysis.core.communication import (
        MessageMiddleware, Message, ChannelType,
        MessagePriority, MessageType, AgentLevel,
        HierarchicalChannel  # Importer la classe concrète du canal
    )
except ImportError as e:
    logging.error(f"Échec critique de l'importation des modules de communication: {e}", exc_info=True)
    # Si ces imports échouent, le ServiceManager ne peut pas fonctionner.
    # Il est préférable de laisser l'application échouer tôt ou de gérer cela plus radicalement.
    MessageMiddleware = None # Pour éviter des NameError plus loin si on continue malgré tout
    HierarchicalChannel = None # Idem
    # Les autres (Message, ChannelType, etc.) causeront des NameError s'ils sont utilisés.


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
    
    def __init__(self, enable_logging: bool = True, log_level: int = logging.INFO):
        """
        Initialise le ServiceManager.
        
        La configuration est maintenant lue depuis `argumentation_analysis.config.settings`.

        Args:
            enable_logging: Active/désactive le logging
            log_level: Niveau de logging
        """
        # La configuration est maintenant gérée par l'objet `settings` global.
        self.config = None # Cet attribut est obsolète mais conservé pour éviter de casser des `hasattr` potentiels.
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

        # Kernel Semantic Kernel et service LLM principal
        self.kernel: Optional[sk.Kernel] = None
        self.llm_service_id: Optional[str] = "gpt-4o-mini" # Default, sera confirmé lors de l'ajout au kernel
        self.project_context: Optional[ProjectContext] = None # Contexte du projet
        
        # État d'initialisation
        self._initialized = False
        self._shutdown = False
        
        self.logger.info(f"ServiceManager créé avec session_id: {self.state.session_id}")
        
    # La méthode _get_default_config est supprimée car la configuration est gérée par `settings`.
        
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

            # 1. Initialisation du contexte du projet (bootstrap)
            self.project_context = initialize_project_environment()
            if not self.project_context:
                raise ServiceManagerError("Échec de l'initialisation du contexte du projet (bootstrap).")
            self.logger.info("Contexte du projet initialisé.")

            # 2. Initialisation du Kernel Semantic Kernel et du service LLM
            self.kernel = sk.Kernel()
            api_key = settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
            self.llm_service_id = settings.service_manager.default_llm_service_id

            if api_key:
                try:
                    llm_service = create_llm_service(service_id=self.llm_service_id)
                    self.kernel.add_service(llm_service)
                    self.logger.info(f"Service LLM résilient '{self.llm_service_id}' ajouté au kernel.")
                except Exception as e_kernel_service:
                    self.logger.error(f"Échec de l'ajout du service LLM résilient au kernel: {e_kernel_service}", exc_info=True)
            else:
                self.logger.warning("API Key OpenAI non trouvée dans la configuration. Le service LLM ne sera pas configuré.")

            # 3. Initialisation du middleware de communication
            if settings.service_manager.enable_communication_middleware:
                await self.initialize_middleware()

            # 4. Initialisation des gestionnaires hiérarchiques (après le middleware)
            if settings.service_manager.enable_hierarchical:
                await self._initialize_hierarchical_managers()

            # 5. Initialisation des orchestrateurs spécialisés
            if settings.service_manager.enable_specialized_orchestrators:
                await self._initialize_specialized_orchestrators()
                
            self._initialized = True
            self.state.update_activity()
            
            self.logger.info("ServiceManager initialisé avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}")
            return False
            
    async def initialize_middleware(self):
        """Initialise le middleware de communication et ses canaux."""
        if self.middleware:
            self.logger.info("Middleware déjà initialisé.")
            return

        if settings.service_manager.enable_communication_middleware and MessageMiddleware:
            self.middleware = MessageMiddleware()
            self.logger.info("Middleware de communication instancié.")

            # Enregistrer les canaux nécessaires
            if HierarchicalChannel:
                try:
                    hierarchical_channel_id = settings.service_manager.hierarchical_channel_id
                    hc = HierarchicalChannel(channel_id=hierarchical_channel_id)
                    self.middleware.register_channel(hc)
                    self.logger.info(f"Canal HIERARCHICAL '{hierarchical_channel_id}' enregistré dans le middleware.")
                except Exception as e_chan:
                    self.logger.error(f"Échec de l'enregistrement du HierarchicalChannel: {e_chan}", exc_info=True)
            else:
                self.logger.error("Classe HierarchicalChannel non disponible pour enregistrement.")
        else:
            self.logger.warning("Middleware de communication désactivé ou non disponible.")

    async def _initialize_hierarchical_managers(self):
        """Initialise les gestionnaires hiérarchiques, s'assurant que le middleware est prêt."""
        if not self.middleware:
            self.logger.warning("Middleware non initialisé. Impossible d'initialiser les gestionnaires hiérarchiques.")
            return

        try:
            if StrategicManager:
                self.strategic_manager = StrategicManager(middleware=self.middleware)
                self.logger.info("StrategicManager initialisé et abonné au middleware.")
                
            if TacticalManager:
                self.tactical_manager = TacticalManager(middleware=self.middleware)
                self.logger.info("TacticalManager initialisé et abonné au middleware.")
                
            if OperationalManager:
                self.operational_manager = OperationalManager(
                    middleware=self.middleware,
                    kernel=self.kernel,
                    llm_service_id=self.llm_service_id,
                    project_context=self.project_context
                )
                self.logger.info("OperationalManager initialisé et abonné au middleware.")
                    
        except Exception as e:
            self.logger.error(f"Erreur critique lors de l'initialisation des gestionnaires hiérarchiques: {e}", exc_info=True)
            # Optionnellement, remettre les managers à None pour indiquer un état d'échec partiel
            self.strategic_manager = self.tactical_manager = self.operational_manager = None

    async def _initialize_specialized_orchestrators(self):
        """Initialise les orchestrateurs spécialisés."""
        try:
            if CluedoOrchestrator:
                self.cluedo_orchestrator = CluedoOrchestrator(kernel=self.kernel) # Passer le kernel
                self.logger.info("CluedoOrchestrator initialisé")
                
            if ConversationOrchestrator:
                # Supposons qu'il puisse aussi bénéficier du kernel ou d'un llm_service
                # Pour l'instant, on garde son initialisation simple.
                self.conversation_orchestrator = ConversationOrchestrator()
                self.logger.info("ConversationOrchestrator initialisé")
                
            if RealLLMOrchestrator:
                # CORRECTION: On passe le kernel complet au RealLLMOrchestrator, pas seulement un service.
                # L'orchestrateur a besoin du kernel pour instancier ses propres agents.
                self.llm_orchestrator = RealLLMOrchestrator(kernel=self.kernel)
                self.logger.info(f"RealLLMOrchestrator initialisé avec le kernel principal.")
                
        except Exception as e:
            self.logger.error(f"Erreur critique lors de l'initialisation des orchestrateurs spécialisés: {e}")
            self.llm_orchestrator = None
            raise Exception(f"Impossible d'initialiser les orchestrateurs: {e}")
            
    async def analyze_text(self, 
                          text: str,
                          analysis_type: str = "unified_analysis",
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
                    orchestrator, text, analysis_type, options
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
            if settings.service_manager.save_results:
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
            'language_model': self.llm_orchestrator,
            # Force tous les types d'analyse vers RealLLMOrchestrator
            'comprehensive': self.llm_orchestrator, # Gardé pour rétrocompatibilité potentielle
            'unified_analysis': self.llm_orchestrator,
            'modal': self.llm_orchestrator,
            'propositional': self.llm_orchestrator,
            'logical': self.llm_orchestrator,
            'rhetorical': self.llm_orchestrator
        }
        
        # Si aucun mapping spécifique, utilise RealLLMOrchestrator par défaut
        result = orchestrator_map.get(analysis_type.lower())
        return result if result is not None else self.llm_orchestrator
        
    async def _run_specialized_analysis(self,
                                      orchestrator: Any,
                                      text: str,
                                      analysis_type: str,  # Ajout du paramètre
                                      options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Lance une analyse avec un orchestrateur spécialisé."""
        try:
            # Interface spécialisée pour RealLLMOrchestrator
            if hasattr(orchestrator, 'analyze_text'):
                from .real_llm_orchestrator import LLMAnalysisRequest
                request = LLMAnalysisRequest(
                    text=text,
                    # Correction: Utilise le analysis_type propagé
                    analysis_type=analysis_type,
                    context=options.get('context') if options else None,
                    parameters=options or {}
                )
                result = await orchestrator.analyze_text(request)
                return {
                    'method': 'real_llm',
                    'request_id': result.request_id,
                    'analysis_type': result.analysis_type,
                    'result': result.result,
                    'confidence': result.confidence,
                    'processing_time': result.processing_time,
                    'timestamp': result.timestamp.isoformat(),
                    'orchestrator': orchestrator.__class__.__name__
                }
            # Interface générique pour autres orchestrateurs
            elif hasattr(orchestrator, 'analyze'):
                return await orchestrator.analyze(text, options)
            elif hasattr(orchestrator, 'process'):
                return await orchestrator.process(text, options)
            else:
                # Plus de fallback autorisé
                raise Exception(f"Orchestrateur {orchestrator.__class__.__name__} sans méthode d'analyse supportée")
        except Exception as e:
            self.logger.error(f"Erreur critique dans l'orchestrateur spécialisé: {e}")
            raise Exception(f"Échec analyse orchestrateur: {e}")
            
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
        self.logger.info(f"ServiceManager._run_strategic_analysis appelée pour le texte : '{text[:50]}...'")
        if not self.strategic_manager:
            self.logger.warning("StrategicManager non disponible pour _run_strategic_analysis.")
            return {'error': 'StrategicManager not available', 'status': 'skipped'}

        try:
            # Note: Les méthodes du StrategicManager sont synchrones.
            # Si elles devenaient asynchrones, il faudrait utiliser await.
            # Pour l'instant, on les appelle directement. Si elles bloquent trop,
            # envisager asyncio.to_thread pour les exécuter dans un thread séparé.
            
            self.logger.info("Appel de strategic_manager.initialize_analysis...")
            initial_strategic_data = self.strategic_manager.initialize_analysis(text)
            self.logger.info(f"strategic_manager.initialize_analysis retourné : {initial_strategic_data}")
            
            objectives = initial_strategic_data.get('objectives', [])
            if not objectives:
                self.logger.warning("Aucun objectif stratégique retourné par initialize_analysis.")
                return {
                    'level': 'strategic',
                    'status': 'completed_no_objectives',
                    'initial_data': initial_strategic_data,
                    'manager': 'StrategicManager'
                }

            self.logger.info(f"Définition de {len(objectives)} objectifs stratégiques...")
            # Itérer sur une copie de la liste pour éviter les problèmes de modification pendant l'itération
            for objective in list(objectives):
                self.logger.info(f"Appel de strategic_manager.define_strategic_goal pour l'objectif : {objective.get('id')}")
                self.strategic_manager.define_strategic_goal(objective) # Synchrone
                self.logger.info(f"Objectif {objective.get('id')} transmis au niveau tactique (via define_strategic_goal).")
            
            return {
                'level': 'strategic',
                'status': 'objectives_defined',
                'objectives_count': len(objectives),
                'initial_plan': initial_strategic_data.get('strategic_plan'),
                'manager': 'StrategicManager'
            }
        except Exception as e:
            self.logger.error(f"Erreur dans _run_strategic_analysis: {e}", exc_info=True)
            return {'error': str(e), 'status': 'failed_in_strategic_manager'}
        
    async def _run_tactical_analysis(self, text: str, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Lance l'analyse tactique avec de vrais appels LLM."""
        self.logger.info(f"ServiceManager._run_tactical_analysis appelée pour le texte : '{text[:50]}...'. Options: {options}")
        
        if not self.tactical_manager:
            self.logger.error("TacticalManager non initialisé")
            return {
                'level': 'tactical',
                'status': 'error',
                'message': 'TacticalManager non disponible',
                'manager': 'TacticalManager'
            }
        
        try:
            # Utiliser l'API OpenAI async pour les vrais appels LLM non-bloquants
            import openai
            import time
            
            api_key = settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
            if not api_key:
                self.logger.error("OPENAI_API_KEY non configuré dans les settings")
                return {
                    'level': 'tactical',
                    'status': 'error',
                    'message': 'API key non configuré',
                    'manager': 'TacticalManager'
                }
            
            # Prompt pour l'analyse tactique
            tactical_prompt = f"""Effectue une analyse tactique du texte suivant en identifiant les arguments, les sophismes potentiels, et la structure rhétorique:

TEXTE À ANALYSER:
{text}

INSTRUCTIONS:
1. Identifie les arguments principaux et secondaires
2. Détecte les sophismes logiques éventuels
3. Analyse la structure rhétorique
4. Évalue la cohérence argumentative
5. Fournis des recommandations tactiques

Réponds au format JSON avec les clés: arguments, sophismes, structure_rhetorique, coherence, recommandations."""

            # Configuration OpenAI standard avec AsyncOpenAI
            client = openai.AsyncOpenAI(api_key=api_key)
            model = "gpt-4o-mini"
            
            # Mesurer le temps de début
            start_time = time.time()
            
            # Faire l'appel LLM authentique async
            # Utiliser le kernel pour l'invocation, ce qui bénéficie de la résilience
            chat_function = self.kernel.create_function_from_prompt(prompt=tactical_prompt, function_name="tactical_analysis")
            response = await self.kernel.invoke(chat_function)
            
            # Mesurer le temps de fin
            end_time = time.time()
            response_time = end_time - start_time
            
            llm_result = str(response)
            
            return {
                'level': 'tactical',
                'status': 'completed',
                'llm_response': llm_result,
                'prompt_used': tactical_prompt,
                'model': model,
                'response_time': response_time,
                'manager': 'TacticalManager',
                'options': options
            }
            
        except Exception as e:
            self.logger.error(f"Erreur dans l'analyse tactique: {e}", exc_info=True)
            return {
                'level': 'tactical',
                'status': 'error',
                'error': str(e),
                'manager': 'TacticalManager'
            }
        
    async def _run_operational_analysis(self, text: str, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Lance l'analyse opérationnelle avec de vrais appels LLM."""
        self.logger.info(f"ServiceManager._run_operational_analysis appelée pour le texte : '{text[:50]}...'. Options: {options}")
        
        if not self.operational_manager:
            self.logger.error("OperationalManager non initialisé")
            return {
                'level': 'operational',
                'status': 'error',
                'message': 'OperationalManager non disponible',
                'manager': 'OperationalManager'
            }
        
        try:
            # Utiliser l'API OpenAI async pour les vrais appels LLM non-bloquants
            import openai
            import time
            
            api_key = settings.openai.api_key.get_secret_value() if settings.openai.api_key else None
            if not api_key:
                self.logger.error("OPENAI_API_KEY non configuré dans les settings")
                return {
                    'level': 'operational',
                    'status': 'error',
                    'message': 'API key non configuré',
                    'manager': 'OperationalManager'
                }
            
            # Prompt pour l'analyse opérationnelle détaillée
            operational_prompt = f"""Effectue une analyse opérationnelle approfondie du texte suivant en te concentrant sur l'extraction d'éléments concrets et l'identification de patterns:

TEXTE À ANALYSER:
{text}

INSTRUCTIONS OPÉRATIONNELLES:
1. Extrais toutes les entités nommées (personnes, lieux, dates, concepts)
2. Identifie les relations logiques explicites et implicites
3. Détecte les patterns linguistiques et rhétoriques
4. Analyse les mécanismes de persuasion utilisés
5. Extrait les prémisses et conclusions principales
6. Identifie les biais cognitifs potentiels
7. Fournis une évaluation de la validité logique

Réponds au format JSON avec les clés: entites, relations, patterns, persuasion, premisses, conclusions, biais, validite_logique."""

            # Configuration OpenAI standard avec AsyncOpenAI
            client = openai.AsyncOpenAI(api_key=api_key)
            model = "gpt-4o-mini"
            
            # Mesurer le temps de début
            start_time = time.time()
            
            # Faire l'appel LLM authentique async
            chat_function = self.kernel.create_function_from_prompt(prompt=operational_prompt, function_name="operational_analysis")
            response = await self.kernel.invoke(chat_function)
            
            # Mesurer le temps de fin
            end_time = time.time()
            response_time = end_time - start_time
            
            llm_result = str(response)
            
            return {
                'level': 'operational',
                'status': 'completed',
                'llm_response': llm_result,
                'prompt_used': operational_prompt,
                'model': model,
                'response_time': response_time,
                'manager': 'OperationalManager',
                'options': options
            }
            
        except Exception as e:
            self.logger.error(f"Erreur dans l'analyse opérationnelle: {e}", exc_info=True)
            return {
                'level': 'operational',
                'status': 'error',
                'error': str(e),
                'manager': 'OperationalManager'
            }
        
    async def _save_results(self, results: Dict[str, Any]):
        """Sauvegarde les résultats d'analyse."""
        try:
            results_dir = settings.service_manager.results_dir
            results_dir.mkdir(parents=True, exist_ok=True)
            
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
            }
            # 'config' est obsolète, les paramètres sont dans `settings`
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

    def is_available(self) -> bool:
        """
        Vérifie si le service est opérationnel.

        Returns:
            True si le service est initialisé et non arrêté, False sinon.
        """
        return self._initialized and not self._shutdown

    def get_status_details(self) -> Dict[str, Any]:
        """
        Retourne des détails sur l'état des services internes.
        S'inspire de ce qu'une API Flask pourrait retourner pour le statut.
        """
        service_details = {
            'overall_status': 'available' if self.is_available() else 'unavailable',
            'session_id': self.state.session_id,
            'start_time': self.state.start_time.isoformat(),
            'uptime_seconds': self.state.get_uptime(),
            'last_activity': self.state.last_activity.isoformat(),
            'initialized': self._initialized,
            'shutdown_initiated': self._shutdown,
            'configuration': "obsolete (see settings module)",
            'active_components': {},
            'component_specific_status': {}
        }

        # Statut des gestionnaires hiérarchiques
        if settings.service_manager.enable_hierarchical:
            service_details['active_components']['strategic_manager'] = self.strategic_manager is not None
            service_details['active_components']['tactical_manager'] = self.tactical_manager is not None
            service_details['active_components']['operational_manager'] = self.operational_manager is not None
            
            if self.strategic_manager and hasattr(self.strategic_manager, 'get_status'):
                try:
                    service_details['component_specific_status']['strategic_manager'] = self.strategic_manager.get_status()
                except Exception as e:
                    service_details['component_specific_status']['strategic_manager'] = {'error': str(e)}
            
            if self.tactical_manager and hasattr(self.tactical_manager, 'get_status'):
                try:
                    service_details['component_specific_status']['tactical_manager'] = self.tactical_manager.get_status()
                except Exception as e:
                    service_details['component_specific_status']['tactical_manager'] = {'error': str(e)}

            if self.operational_manager and hasattr(self.operational_manager, 'get_status'):
                try:
                    service_details['component_specific_status']['operational_manager'] = self.operational_manager.get_status()
                except Exception as e:
                    service_details['component_specific_status']['operational_manager'] = {'error': str(e)}

        # Statut des orchestrateurs spécialisés
        if settings.service_manager.enable_specialized_orchestrators:
            service_details['active_components']['cluedo_orchestrator'] = self.cluedo_orchestrator is not None
            service_details['active_components']['conversation_orchestrator'] = self.conversation_orchestrator is not None
            service_details['active_components']['llm_orchestrator'] = self.llm_orchestrator is not None

            if self.cluedo_orchestrator and hasattr(self.cluedo_orchestrator, 'get_status'):
                try:
                    service_details['component_specific_status']['cluedo_orchestrator'] = self.cluedo_orchestrator.get_status()
                except Exception as e:
                    service_details['component_specific_status']['cluedo_orchestrator'] = {'error': str(e)}
            
            if self.conversation_orchestrator and hasattr(self.conversation_orchestrator, 'get_status'):
                try:
                    service_details['component_specific_status']['conversation_orchestrator'] = self.conversation_orchestrator.get_status()
                except Exception as e:
                    service_details['component_specific_status']['conversation_orchestrator'] = {'error': str(e)}

            if self.llm_orchestrator and hasattr(self.llm_orchestrator, 'get_status'):
                try:
                    service_details['component_specific_status']['llm_orchestrator'] = self.llm_orchestrator.get_status()
                except Exception as e:
                    service_details['component_specific_status']['llm_orchestrator'] = {'error': str(e)}
        
        # Statut du middleware de communication
        if settings.service_manager.enable_communication_middleware:
            service_details['active_components']['middleware'] = self.middleware is not None
            if self.middleware and hasattr(self.middleware, 'get_status'):
                try:
                    service_details['component_specific_status']['middleware'] = self.middleware.get_status()
                except Exception as e:
                    service_details['component_specific_status']['middleware'] = {'error': str(e)}
        
        return service_details
        
    async def shutdown(self):
        """Arrête proprement le ServiceManager."""
        if self._shutdown:
            return
            
        self.logger.info("Arrêt du ServiceManager...")
        
        try:
            # Fonction d'aide pour un arrêt sécurisé des composants
            async def safe_shutdown(component, name):
                """Appelle shutdown() de manière sécurisée, qu'il soir sync ou async."""
                if component and hasattr(component, 'shutdown'):
                    self.logger.debug(f"Tentative d'arrêt de {name}...")
                    shutdown_call = component.shutdown()
                    if inspect.isawaitable(shutdown_call):
                        await shutdown_call
                        self.logger.debug(f"{name} arrêté (async).")
                    else:
                        # La méthode était synchrone, l'appel a déjà eu lieu
                        self.logger.debug(f"{name} arrêté (sync).")

            # Arrêt des composants en utilisant la fonction sécurisée
            await safe_shutdown(self.cluedo_orchestrator, "CluedoOrchestrator")
            await safe_shutdown(self.conversation_orchestrator, "ConversationOrchestrator")
            await safe_shutdown(self.llm_orchestrator, "RealLLMOrchestrator")
            await safe_shutdown(self.strategic_manager, "StrategicManager")
            await safe_shutdown(self.tactical_manager, "TacticalManager")
            await safe_shutdown(self.operational_manager, "OperationalManager")
            await safe_shutdown(self.middleware, "MessageMiddleware")

            self._shutdown = True
            self.logger.info("ServiceManager arrêté proprement")

        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt: {e}", exc_info=True)
            
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