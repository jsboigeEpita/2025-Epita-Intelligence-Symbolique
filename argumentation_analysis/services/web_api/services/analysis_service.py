#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Service d'analyse complète utilisant le moteur d'analyse argumentative.
"""
import time
import logging
import asyncio
import inspect
from typing import Dict, List, Any, Optional
import semantic_kernel as sk
from semantic_kernel.contents.chat_message_content import ChatMessageContent

# Imports du moteur d'analyse (style b282af4 avec gestion d'erreur)
try:
    from argumentation_analysis.agents.agent_factory import AgentFactory
    from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator
    from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
    
    # Imports optionnels qui peuvent échouer
    try:
        from argumentation_analysis.core.llm_service import create_llm_service
    except ImportError as llm_e:
        logging.warning(f"Failed to import create_llm_service: {llm_e}")
        create_llm_service = None
        
    try:
        from argumentation_analysis.utils.taxonomy_loader import get_taxonomy_path
    except ImportError as tax_e:
        logging.warning(f"Failed to import get_taxonomy_path: {tax_e}")
        get_taxonomy_path = None
        
except ImportError as e:
    logging.warning(f"[ERROR] CRITICAL: Core analysis modules import failed: {e}")
    # Mode dégradé pour les tests
    AgentFactory = None
    ComplexFallacyAnalyzer = None
    ContextualFallacyAnalyzer = None
    FallacySeverityEvaluator = None
    OperationalManager = None
    create_llm_service = None
    get_taxonomy_path = None

# # Fallback pour les variables qui seraient normalement importées
# InformalAgent = None
# ComplexFallacyAnalyzer = None
# ContextualFallacyAnalyzer = None
# FallacySeverityEvaluator = None
# OperationalManager = None
# create_llm_service = None
# get_taxonomy_path = None

# Imports des modèles (style HEAD)
from argumentation_analysis.services.web_api.models.request_models import AnalysisRequest
from argumentation_analysis.services.web_api.models.response_models import (
    AnalysisResponse, FallacyDetection, ArgumentStructure
)

# L'import de FallacyService est supprimé pour éviter l'appel circulaire.
# from argumentation_analysis.services.web_api.services.fallacy_service import FallacyService

logger = logging.getLogger("AnalysisService")

class AnalysisService:
    """
    Service pour l'analyse complète de textes argumentatifs.
    
    Ce service utilise le moteur d'analyse existant pour fournir
    une analyse complète incluant la détection de sophismes,
    l'analyse de structure et l'évaluation de cohérence.
    """
    
    def __init__(self):
        """Initialise le service d'analyse."""
        self.logger = logger
        self.is_initialized = False
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialise les composants d'analyse internes du service.

        Tente d'instancier `ComplexFallacyAnalyzer`, `ContextualFallacyAnalyzer`,
        `FallacySeverityEvaluator`, et `InformalAgent`.
        Met à jour `self.is_initialized` en fonction du succès.

        :return: None
        :rtype: None
        """
        try:
            self.logger.info("=== Initializing Analysis Service Components ===")
            # Initialisation des analyseurs
            if ComplexFallacyAnalyzer:
                self.complex_analyzer = ComplexFallacyAnalyzer()
                self.logger.info("[OK] ComplexFallacyAnalyzer initialized")
            else:
                self.complex_analyzer = None
                self.logger.warning("[WARN] ComplexFallacyAnalyzer not available (import failed or class not found)")
            
            if ContextualFallacyAnalyzer:
                self.contextual_analyzer = ContextualFallacyAnalyzer()
                # self.contextual_analyzer = None # Désactivé pour les tests
                self.logger.info("[OK] ContextualFallacyAnalyzer initialized")
            else:
                self.contextual_analyzer = None
                self.logger.warning("[WARN] ContextualFallacyAnalyzer not available (import failed or class not found)")
            
            if FallacySeverityEvaluator:
                self.severity_evaluator = FallacySeverityEvaluator()
                self.logger.info("[OK] FallacySeverityEvaluator initialized")
            else:
                self.severity_evaluator = None
                self.logger.warning("[WARN] FallacySeverityEvaluator not available (import failed or class not found)")
            
            # La section responsable de l'appel circulaire est supprimée.
            # self.fallacy_service = FallacyService()
            self.fallacy_service = None
            
            # Configuration des outils pour l'agent informel
            self.tools = {}
            if self.complex_analyzer:
                self.tools['complex_fallacy_analyzer'] = self.complex_analyzer
            if self.contextual_analyzer:
                self.tools['contextual_fallacy_analyzer'] = self.contextual_analyzer
            if self.severity_evaluator:
                self.tools['fallacy_severity_evaluator'] = self.severity_evaluator
            
            # Initialisation de l'agent informel via AgentFactory
            if AgentFactory:
                self.logger.info("[INIT] Attempting to initialize informal agent via AgentFactory...")
                
                # Vérification des dépendances disponibles
                self.logger.info(f"create_llm_service available: {create_llm_service is not None}")
                self.logger.info(f"get_taxonomy_path available: {get_taxonomy_path is not None}")

                # Mode compatible sans dépendances manquantes
                if not create_llm_service or not get_taxonomy_path:
                    self.logger.warning("[WARN] Missing dependencies for AgentFactory - using fallback mode")
                    self.informal_agent = None
                else:
                    # Création du kernel et ajout du service LLM
                    kernel = sk.Kernel()
                    llm_service_instance = None # Renommé pour éviter conflit avec variable globale potentielle
                    try:
                        llm_service_instance = create_llm_service(service_id="default_analysis_llm", model_id="gpt-4o-mini")
                        kernel.add_service(llm_service_instance)
                        self.logger.info("[OK] LLM service created and added to kernel for AgentFactory")
                    except Exception as llm_e:
                        self.logger.error(f"[ERROR] Failed to create LLM service for AgentFactory: {llm_e}")

                    taxonomy_path_instance = None # Renommé
                    try:
                        taxonomy_path_instance = get_taxonomy_path()
                        self.logger.info(f"[OK] Taxonomy path obtained for AgentFactory: {taxonomy_path_instance}")
                    except Exception as tax_e:
                        self.logger.error(f"[ERROR] Failed to get taxonomy path for AgentFactory: {tax_e}")
                    
                    if kernel and llm_service_instance:
                        try:
                            from argumentation_analysis.config.settings import AppSettings
                            settings = AppSettings()
                            settings.service_manager.default_llm_service_id = "default_analysis_llm"
                            factory = AgentFactory(kernel=kernel, settings=settings)
                            self.informal_agent = factory.create_informal_fallacy_agent(
                                config_name="full"
                            )
                            self.logger.info("[OK] InformalAgent created and configured successfully via AgentFactory.")
                        except Exception as factory_e:
                            self.logger.error(f"[ERROR] Failed to create InformalAgent from factory: {factory_e}", exc_info=True)
                            self.informal_agent = None
                    else:
                        self.logger.error("[ERROR] Cannot initialize InformalAgent - missing kernel or LLM service instance")
                        self.informal_agent = None
            else:
                self.informal_agent = None
                self.logger.warning("[WARN] AgentFactory not available (import failed or class not found)")
            
            self.is_initialized = True
            if self.informal_agent:
                self.logger.info("AnalysisService initialized successfully (with InformalAgent).")
            else:
                self.logger.warning("AnalysisService initialized, but InformalAgent could not be created/configured.")
            
        except Exception as e:
            self.logger.error(f"Critical error during AnalysisService initialization: {e}")
            self.is_initialized = False
    
    def is_healthy(self) -> bool:
        """Vérifie l'état de santé du service d'analyse.

        :return: True si le service est initialisé et qu'au moins un composant
                 d'analyse (agent informel ou analyseur spécifique) est disponible,
                 False sinon.
        :rtype: bool
        """
        has_informal = self.informal_agent is not None
        has_analyzers = any([self.complex_analyzer, self.contextual_analyzer, self.severity_evaluator])
        # Le health check est simplifié pour ne plus dépendre de FallacyService.
        is_healthy = self.is_initialized and (has_informal or has_analyzers)
        
        self.logger.info(f"=== Health Check: Analysis Service ===")
        self.logger.info(f"is_initialized: {self.is_initialized}")
        self.logger.info(f"has_informal_agent: {has_informal}")
        self.logger.info(f"has_analyzers: {has_analyzers}")
        self.logger.info(f"complex_analyzer: {self.complex_analyzer is not None}")
        self.logger.info(f"contextual_analyzer: {self.contextual_analyzer is not None}")
        self.logger.info(f"severity_evaluator: {self.severity_evaluator is not None}")
        self.logger.info(f"overall_health: {is_healthy}")
        
        return is_healthy
    
    async def analyze_text(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Effectue une analyse complète d'un texte argumentatif.

        Orchestre la détection de sophismes, l'analyse de la structure argumentative,
        et le calcul de métriques globales comme la qualité et la cohérence.

        :param request: L'objet `AnalysisRequest` contenant le texte à analyser
                        et les options d'analyse.
        :type request: AnalysisRequest
        :return: Un objet `AnalysisResponse` contenant les résultats de l'analyse.
                 En cas d'échec d'initialisation du service, une réponse de fallback
                 est retournée.
        :rtype: AnalysisResponse
        """
        start_time = time.time()
        
        self.logger.info(f"ENTERING AnalysisService.analyze_text with text: '{request.text[:50]}...'")
        self.logger.debug(f"Analysis options: {request.options}")
        
        try:
            # Vérification de l'état du service
            if not self.is_healthy():
                self.logger.warning("AnalysisService is not healthy - creating fallback response.")
                return self._create_fallback_response(request, start_time)
            
            # --- START DEBUG BLOCK ---
            self.logger.debug("AnalysisService is healthy - proceeding with analysis.")
            try:
                # Analyse des sophismes
                fallacies = await self._detect_fallacies(request.text, request.options)
                
                # Analyse de la structure argumentative
                # Run the synchronous _analyze_structure in a separate thread to avoid blocking the event loop
                structure = await asyncio.to_thread(self._analyze_structure, request.text, request.options)
                
                # Calcul des métriques globales
                overall_quality = self._calculate_overall_quality(fallacies, structure)
                coherence_score = self._calculate_coherence_score(structure)
            except Exception as analysis_exception:
                self.logger.critical("--- CATCHING THE BUG! ---")
                self.logger.critical(f"An unexpected error occurred during the core analysis logic: {analysis_exception}", exc_info=True)
                # On relève l'exception pour que le gestionnaire global la transforme en 500,
                # mais nous aurons maintenant la trace précise.
                raise
            # --- END DEBUG BLOCK ---

            processing_time = time.time() - start_time
            self.logger.info(f"EXITING AnalysisService.analyze_text successfully in {processing_time:.2f}s")
            
            return AnalysisResponse(
                success=True,
                text_analyzed=request.text,
                fallacies=fallacies,
                argument_structure=structure,
                overall_quality=overall_quality,
                coherence_score=coherence_score,
                fallacy_count=len(fallacies),
                processing_time=processing_time,
                analysis_options=request.options.dict() if request.options else {}
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse: {e}", exc_info=True)
            processing_time = time.time() - start_time
            self.logger.info(f"EXITING AnalysisService.analyze_text with ERROR in {processing_time:.2f}s")
            return AnalysisResponse(
                success=False,
                text_analyzed=request.text,
                fallacies=[],
                argument_structure=None,
                overall_quality=0.0,
                coherence_score=0.0,
                fallacy_count=0,
                processing_time=processing_time,
                analysis_options=request.options.dict() if request.options else {}
            )
    
    async def _detect_fallacies(self, text: str, options: Optional[Any]) -> List[FallacyDetection]:
        """Détecte les sophismes dans le texte en utilisant les analyseurs disponibles.

        Utilise `self.informal_agent` si disponible, sinon `self.contextual_analyzer`.
        Filtre les résultats en fonction du `severity_threshold` des options.

        :param text: Le texte à analyser.
        :type text: str
        :param options: Les options d'analyse (par exemple, `AnalysisOptions` ou `FallacyOptions`)
                        pouvant contenir `severity_threshold`.
        :type options: Optional[Any]
        :return: Une liste d'objets `FallacyDetection`.
        :rtype: List[FallacyDetection]
        """
        fallacies = []
        
        self.logger.info(f"ENTERING _detect_fallacies with text: '{text[:50]}...'")
        
        try:
            import json
            # La logique d'appel circulaire via FallacyService a été supprimée.
            # L'analyse se base maintenant sur les composants internes comme prévu.

            # PRIORITÉ 1: Utilisation de l'agent informel
            if self.informal_agent:
                self.logger.info("Using InformalAgent for fallacy detection.")
                
                # --- NOUVELLE LOGIQUE DE CONSOMMATION DE L'AGENT ---
                # Approche simplifiée pour gérer les deux types de retours de `invoke`.

                agent_response = self.informal_agent.invoke(input=text)
                full_response_str = ""
                result = None

                self.logger.info(f"Agent response type: {type(agent_response)}")

                try:
                    if inspect.isasyncgen(agent_response):
                        self.logger.info("Consuming agent response as an async generator (streaming).")
                        
                        # Agréger le contenu de tous les chunks streamés
                        full_response_str = "".join([chunk.content async for chunk in agent_response if chunk.content])
                        self.logger.debug(f"Aggregated stream content: '''{full_response_str}'''")

                        # Les LLMs enveloppent souvent le JSON dans des blocs de code.
                        if full_response_str.strip().startswith("```") and full_response_str.strip().endswith("```"):
                             # Extraire le JSON du bloc de code (ex: ```json ... ```)
                            json_str = full_response_str.strip()
                            if json_str.startswith("```json"):
                                json_str = json_str[7:]
                            elif json_str.startswith("```"):
                                json_str = json_str[3:]
                            
                            if json_str.endswith("```"):
                                 json_str = json_str[:-3]
                            
                            full_response_str = json_str.strip()
                            self.logger.debug(f"Extracted JSON from markdown block: '''{full_response_str}'''")

                        # Parser le contenu agrégé qui devrait être la représentation JSON d'un tool_call
                        tool_calls_data = json.loads(full_response_str)
                        
                        # Extraire les arguments du premier appel d'outil
                        if isinstance(tool_calls_data, list) and tool_calls_data:
                            first_tool_call = tool_calls_data[0]
                            if 'function' in first_tool_call and 'arguments' in first_tool_call['function']:
                                # Les arguments sont eux-mêmes une chaîne JSON à parser
                                result = json.loads(first_tool_call['function']['arguments'])
                            else:
                                self.logger.warning(f"Unexpected tool_call format in stream: {first_tool_call}")
                        else:
                            self.logger.warning(f"Unexpected data format in stream: {tool_calls_data}")
                            
                    else:  # Cas du mock qui retourne directement un awaitable
                        self.logger.info("Consuming agent response as a direct awaitable (non-streaming).")
                        response_content = await agent_response
                        self.logger.debug(f"Direct awaitable response from agent: {response_content}")

                        # Le mock retourne une liste, on prend le premier élément
                        final_message = response_content[0] if isinstance(response_content, list) and response_content else response_content
                        
                        if isinstance(final_message, ChatMessageContent) and final_message.tool_calls:
                            tool_call = final_message.tool_calls[0]
                            # Dans le mock, 'arguments' est déjà un dictionnaire, pas une chaîne JSON.
                            result = tool_call.function.arguments if hasattr(tool_call.function, 'arguments') else None
                        else:
                            self.logger.warning(f"Unexpected non-streamed response format: {final_message}")

                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to decode JSON from agent. Raw response: '''{full_response_str}'''. Error: {e}")
                    result = None
                except Exception as e:
                    self.logger.error(f"An unexpected error occurred during agent response processing: {e}", exc_info=True)
                    result = None
                
                # --- FIN DE LA NOUVELLE LOGIQUE ---
                
                if result and 'fallacies' in result and isinstance(result['fallacies'], list):
                    for fallacy_data in result['fallacies']:
                        fallacy = FallacyDetection(
                            type=fallacy_data.get('type', 'semantic'),
                            name=fallacy_data.get('fallacy_type', fallacy_data.get('nom', fallacy_data.get('name', 'Sophisme non identifié'))),
                            description=fallacy_data.get('explication', fallacy_data.get('description', fallacy_data.get('explanation', ''))),
                            severity=fallacy_data.get('severity', 0.7),
                            confidence=fallacy_data.get('confidence', 0.8),
                            location=fallacy_data.get('location'),
                            context=fallacy_data.get('context', fallacy_data.get('reformulation')),
                            explanation=fallacy_data.get('explication', fallacy_data.get('explanation', ''))
                        )
                        fallacies.append(fallacy)
            
            # PRIORITÉ 3: Analyse contextuelle si les autres méthodes n'ont rien donné
            elif not fallacies and self.contextual_analyzer:
                self.logger.info("Using ContextualAnalyzer for fallacy detection (wrapped in asyncio.to_thread).")
                # Wrap the synchronous, potentially blocking call in a separate thread.
                result = await asyncio.to_thread(self.contextual_analyzer.analyze_fallacies, text)
                if result:
                    for fallacy_data in result:
                        fallacy = FallacyDetection(
                            type=fallacy_data.get('type', 'contextual'),
                            name=fallacy_data.get('name', 'Sophisme contextuel'),
                            description=fallacy_data.get('description', ''),
                            severity=fallacy_data.get('severity', 0.5),
                            confidence=fallacy_data.get('confidence', 0.5),
                            context=fallacy_data.get('context')
                        )
                        fallacies.append(fallacy)
            
            # Filtrage par seuil de sévérité
            if options and hasattr(options, 'severity_threshold') and options.severity_threshold is not None:
                self.logger.info(f"Filtering fallacies with severity >= {options.severity_threshold}")
                initial_count = len(fallacies)
                fallacies = [f for f in fallacies if f.severity >= options.severity_threshold]
                self.logger.info(f"Filtered {initial_count - len(fallacies)} fallacies.")

        except Exception as e:
            self.logger.error(f"Erreur lors de la détection de sophismes: {e}", exc_info=True)
        
        self.logger.info(f"EXITING _detect_fallacies, found {len(fallacies)} fallacies.")
        return fallacies
    
    def _analyze_structure(self, text: str, options: Optional[Any]) -> Optional[ArgumentStructure]:
        """Analyse la structure argumentative du texte avec détection améliorée des connecteurs logiques.

        Cette méthode utilise la détection de connecteurs logiques pour identifier
        les prémisses et conclusions plus précisément que la simple division par phrases.
        
        :param text: Le texte à analyser.
        :type text: str
        :param options: Options d'analyse (non utilisées actuellement dans cette méthode).
        :type options: Optional[Any]
        :return: Un objet `ArgumentStructure` ou None si une erreur survient.
        :rtype: Optional[ArgumentStructure]
        """
        try:
            import re
            
            # Nettoyage et normalisation du texte
            clean_text = text.strip()
            
            # Connecteurs logiques pour identifier les structures argumentatives
            conclusion_indicators = [
                r'\bdonc\b', r'\bpar conséquent\b', r'\bainsi\b', r'\bde ce fait\b',
                r'\bc\'est pourquoi\b', r'\bpar suite\b', r'\bde là\b', r'\ben conclusion\b'
            ]
            
            premise_indicators = [
                r'\bparce que\b', r'\bcar\b', r'\bpuisque\b', r'\bétant donné que\b',
                r'\bcomme\b', r'\ben effet\b', r'\bdu fait que\b', r'\bvu que\b'
            ]
            
            causal_patterns = [
                r'\bsi\b.*\balors\b', r'\bquand\b.*\balors\b'
            ]
            
            # Détection de structures argumentatives
            premises = []
            conclusion = ""
            argument_type = "simple"
            
            # 1. Recherche de connecteurs de conclusion
            conclusion_found = False
            for indicator in conclusion_indicators:
                matches = list(re.finditer(indicator, clean_text, re.IGNORECASE))
                if matches:
                    conclusion_found = True
                    # La conclusion est généralement après le connecteur
                    conclusion_start = matches[-1].end()
                    conclusion = clean_text[conclusion_start:].strip()
                    premises_text = clean_text[:matches[-1].start()].strip()
                    if premises_text:
                        premises = [premises_text]
                    argument_type = "deductive"
                    break
            
            # 2. Si pas de connecteur de conclusion, recherche de connecteurs de prémisse
            if not conclusion_found:
                for indicator in premise_indicators:
                    matches = list(re.finditer(indicator, clean_text, re.IGNORECASE))
                    if matches:
                        # Structure: [Conclusion] parce que [Prémisse]
                        premise_start = matches[0].end()
                        premise_text = clean_text[premise_start:].strip()
                        conclusion_text = clean_text[:matches[0].start()].strip()
                        
                        if premise_text and conclusion_text:
                            premises = [premise_text]
                            conclusion = conclusion_text
                            argument_type = "causal"
                            conclusion_found = True
                            break
            
            # 3. Détection de patterns causaux (si...alors)
            if not conclusion_found:
                for pattern in causal_patterns:
                    matches = list(re.finditer(pattern, clean_text, re.IGNORECASE))
                    if matches:
                        # Structure conditionnelle détectée
                        match = matches[0]
                        si_match = re.search(r'\bsi\b(.*?)\balors\b', clean_text, re.IGNORECASE)
                        if si_match:
                            condition = si_match.group(1).strip()
                            conclusion_start = si_match.end()
                            conclusion_text = clean_text[conclusion_start:].strip()
                            
                            premises = [f"Si {condition}"]
                            conclusion = conclusion_text
                            argument_type = "conditional"
                            conclusion_found = True
                            break
            
            # 4. Fallback : division par phrases avec amélioration
            if not conclusion_found:
                # Division par points, points d'exclamation, points d'interrogation
                sentences = re.split(r'[.!?]+', clean_text)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                if len(sentences) >= 2:
                    conclusion = sentences[-1]
                    premises = sentences[:-1]
                    argument_type = "simple"
                elif len(sentences) == 1:
                    conclusion = sentences[0]
                    premises = []
                    argument_type = "assertion"
                else:
                    conclusion = clean_text
                    premises = []
                    argument_type = "fragment"
            
            # Calcul de la force et cohérence améliorés
            strength = self._calculate_argument_strength(premises, conclusion, argument_type)
            coherence = self._calculate_structural_coherence(premises, conclusion, argument_type, clean_text)
            
            self.logger.debug(f"Structure analysée: type={argument_type}, premises={len(premises)}, strength={strength:.2f}, coherence={coherence:.2f}")
            
            return ArgumentStructure(
                premises=premises,
                conclusion=conclusion,
                argument_type=argument_type,
                strength=strength,
                coherence=coherence
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de structure: {e}")
            return None
    
    def _calculate_argument_strength(self, premises: List[str], conclusion: str, argument_type: str) -> float:
        """Calcule la force de l'argument basée sur la structure détectée."""
        try:
            base_strength = 0.3
            
            # Bonus selon le type d'argument
            type_bonus = {
                "deductive": 0.4,
                "causal": 0.3,
                "conditional": 0.35,
                "simple": 0.2,
                "assertion": 0.1,
                "fragment": 0.05
            }
            base_strength += type_bonus.get(argument_type, 0.1)
            
            # Bonus selon le nombre de prémisses
            if premises:
                premise_bonus = min(0.3, len(premises) * 0.1)
                base_strength += premise_bonus
            
            # Pénalité pour arguments trop courts ou incomplets
            if not conclusion or len(conclusion.strip()) < 10:
                base_strength *= 0.7
            if not premises or all(len(p.strip()) < 5 for p in premises):
                base_strength *= 0.6
            
            return min(1.0, max(0.0, base_strength))
            
        except Exception as e:
            self.logger.error(f"Erreur calcul force argument: {e}")
            return 0.3
    
    def _calculate_structural_coherence(self, premises: List[str], conclusion: str, argument_type: str, original_text: str) -> float:
        """Calcule la cohérence structurelle basée sur la qualité des connecteurs et la logique."""
        try:
            import re
            
            base_coherence = 0.3
            
            # Bonus pour présence de connecteurs logiques
            logical_connectors = [
                r'\bdonc\b', r'\bparce que\b', r'\bcar\b', r'\bpuisque\b',
                r'\bpar conséquent\b', r'\bainsi\b', r'\bde ce fait\b'
            ]
            
            connector_count = 0
            for connector in logical_connectors:
                if re.search(connector, original_text, re.IGNORECASE):
                    connector_count += 1
            
            if connector_count > 0:
                base_coherence += min(0.4, connector_count * 0.15)
            
            # Bonus selon le type d'argument
            type_coherence = {
                "deductive": 0.3,
                "causal": 0.25,
                "conditional": 0.2,
                "simple": 0.1,
                "assertion": 0.05,
                "fragment": 0.0
            }
            base_coherence += type_coherence.get(argument_type, 0.05)
            
            # Pénalité pour incohérences structurelles
            if argument_type in ["assertion", "fragment"]:
                base_coherence *= 0.5
            
            # Pénalité pour raisonnement circulaire détecté
            if self._detect_circular_reasoning_patterns(original_text):
                base_coherence *= 0.2  # Forte pénalité
            
            return min(1.0, max(0.0, base_coherence))
            
        except Exception as e:
            self.logger.error(f"Erreur calcul cohérence: {e}")
            return 0.3
    
    def _detect_circular_reasoning_patterns(self, text: str) -> bool:
        """Détecte des patterns de raisonnement circulaire dans le texte."""
        try:
            import re
            
            circular_patterns = [
                r'(.+)\s+parce que\s+(.+)\s+dit.+et\s+(.+)\s+est\s+(vraie?|correct)\s+parce que',
                r'(.+)\s+existe\s+parce que\s+(.+)\s+le dit.+et\s+(.+)\s+est\s+(vraie?|véridique)\s+parce que',
                r'A\s+parce que\s+B.+et\s+B\s+parce que\s+A',
                r'est vrai parce que.+est vrai',
                r'existe parce que.+dit.+est vraie? parce que'
            ]
            
            for pattern in circular_patterns:
                if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erreur détection circularité: {e}")
            return False
    
    def _calculate_overall_quality(self, fallacies: List[FallacyDetection], structure: Optional[ArgumentStructure]) -> float:
        """Calcule un score de qualité globale basé sur les sophismes et la structure.

        Combine un score basé sur la pénalité des sophismes et un score basé sur
        la force de la structure argumentative. Amélioration : pénalise davantage
        les sophismes et les arguments mal structurés.

        :param fallacies: Liste des sophismes détectés.
        :type fallacies: List[FallacyDetection]
        :param structure: La structure argumentative analysée.
        :type structure: Optional[ArgumentStructure]
        :return: Un score de qualité globale entre 0.0 et 1.0.
        :rtype: float
        """
        try:
            # Calcul du score basé sur les sophismes (pénalité plus forte)
            if fallacies:
                # Pénalité progressive : chaque sophisme réduit significativement le score
                fallacy_penalty = 0.0
                for fallacy in fallacies:
                    # Pénalité basée sur la sévérité et le type de sophisme
                    severity_penalty = fallacy.severity * 0.4  # Augmentation de 0.1 à 0.4
                    fallacy_penalty += severity_penalty
                
                # Pénalité supplémentaire pour les sophismes multiples
                if len(fallacies) > 1:
                    fallacy_penalty += len(fallacies) * 0.1
                
                fallacy_score = max(0.0, 1.0 - fallacy_penalty)
            else:
                fallacy_score = 1.0
            
            # Calcul du score de structure (plus strict)
            if structure:
                structure_score = structure.strength
                
                # Pénalité pour arguments mal structurés
                if structure.argument_type == "simple" and len(structure.premises) == 0:
                    # Argument sans prémisses claires = qualité très faible
                    structure_score = max(0.1, structure_score * 0.3)
                elif structure.argument_type == "unknown":
                    structure_score = max(0.1, structure_score * 0.5)
                
                # Bonus pour arguments bien structurés
                if len(structure.premises) >= 2 and structure.argument_type == "deductive":
                    structure_score = min(1.0, structure_score * 1.2)
            else:
                structure_score = 0.1  # Très faible si pas de structure
            
            # Pondération ajustée : plus d'importance aux sophismes
            overall = (fallacy_score * 0.7 + structure_score * 0.3)
            result = min(1.0, max(0.0, overall))
            
            self.logger.debug(f"Qualité calculée: fallacy_score={fallacy_score:.2f}, structure_score={structure_score:.2f}, overall={result:.2f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de qualité: {e}")
            return 0.2  # Valeur plus faible en cas d'erreur
    
    def _calculate_coherence_score(self, structure: Optional[ArgumentStructure]) -> float:
        """Calcule le score de cohérence basé sur la structure argumentative.

        :param structure: La structure argumentative analysée.
        :type structure: Optional[ArgumentStructure]
        :return: Le score de cohérence de la structure, ou 0.3 par défaut si
                 la structure est None ou si une erreur survient.
        :rtype: float
        """
        try:
            if structure:
                return structure.coherence
            return 0.3 # Cohérence faible par défaut
        except Exception as e:
            self.logger.error(f"Erreur lors du calcul de cohérence: {e}")
            return 0.3
    
    def _create_fallback_response(self, request: AnalysisRequest, start_time: float) -> AnalysisResponse:
        """Crée une réponse `AnalysisResponse` de fallback en cas d'échec d'initialisation du service.

        :param request: La requête d'analyse originale.
        :type request: AnalysisRequest
        :param start_time: Le timestamp du début du traitement de la requête.
        :type start_time: float
        :return: Un objet `AnalysisResponse` indiquant un échec avec des valeurs par défaut.
        :rtype: AnalysisResponse
        """
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            success=False,
            text_analyzed=request.text,
            fallacies=[],
            argument_structure=ArgumentStructure( # Fournir une structure par défaut
                premises=[],
                conclusion=request.text, # Au moins retourner le texte comme conclusion
                argument_type="unknown",
                strength=0.0,
                coherence=0.0
            ),
            overall_quality=0.0,
            coherence_score=0.0,
            fallacy_count=0,
            processing_time=processing_time,
            analysis_options=request.options.dict() if request.options else {}
        )