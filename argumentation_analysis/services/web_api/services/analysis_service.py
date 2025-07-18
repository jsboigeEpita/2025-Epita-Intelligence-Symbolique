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
from argumentation_analysis.config.settings import AppSettings
import semantic_kernel as sk
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.exceptions.service_exceptions import ServiceResponseException
import json

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

# Imports des modèles (style HEAD)
from argumentation_analysis.services.web_api.models.request_models import AnalysisRequest
from argumentation_analysis.services.web_api.models.response_models import (
    AnalysisResponse, FallacyDetection, ArgumentStructure
)

logger = logging.getLogger("AnalysisService")

class AnalysisService:
    """
    Service pour l'analyse complète de textes argumentatifs.
    """
    
    def __init__(self, settings: AppSettings):
        """Initialise le service d'analyse."""
        self.logger = logger
        self.settings = settings
        self.is_initialized = False
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialise les composants d'analyse internes du service."""
        try:
            self.logger.info("=== Initializing Analysis Service Components ===")
            if ComplexFallacyAnalyzer:
                self.complex_analyzer = ComplexFallacyAnalyzer()
                self.logger.info("[OK] ComplexFallacyAnalyzer initialized")
            else:
                self.complex_analyzer = None
            
            if ContextualFallacyAnalyzer:
                self.contextual_analyzer = ContextualFallacyAnalyzer()
                self.logger.info("[OK] ContextualFallacyAnalyzer initialized")
            else:
                self.contextual_analyzer = None
            
            if FallacySeverityEvaluator:
                self.severity_evaluator = FallacySeverityEvaluator()
                self.logger.info("[OK] FallacySeverityEvaluator initialized")
            else:
                self.severity_evaluator = None

            self.fallacy_service = None
            
            self.tools = {}
            if self.complex_analyzer: self.tools['complex_fallacy_analyzer'] = self.complex_analyzer
            if self.contextual_analyzer: self.tools['contextual_fallacy_analyzer'] = self.contextual_analyzer
            if self.severity_evaluator: self.tools['fallacy_severity_evaluator'] = self.severity_evaluator
            
            if AgentFactory and create_llm_service and get_taxonomy_path:
                self.logger.info("[INIT] Attempting to initialize informal agent via AgentFactory...")
                kernel = sk.Kernel()
                llm_service_instance = None
                try:
                    llm_service_instance = create_llm_service(service_id="default_analysis_llm")
                    kernel.add_service(llm_service_instance)
                except Exception as llm_e:
                    self.logger.error(f"[ERROR] Failed to create LLM service for AgentFactory: {llm_e}")
                
                if kernel and llm_service_instance:
                    try:
                        factory = AgentFactory(kernel=kernel, settings=self.settings)
                        from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
                        self.informal_agent = factory.create_agent(
                            agent_class=InformalAnalysisAgent,
                            agent_name="InformalFallacyAgent_from_service"
                       )
                        self.logger.info("[OK] InformalAgent created and configured successfully via AgentFactory.")
                    except Exception as factory_e:
                        self.logger.error(f"[ERROR] Failed to create InformalAgent from factory: {factory_e}", exc_info=True)
                        self.informal_agent = None
                else:
                    self.informal_agent = None
            else:
                self.informal_agent = None

            self.is_initialized = True
            if self.informal_agent:
                self.logger.info("AnalysisService initialized successfully (with InformalAgent).")
            else:
                self.logger.warning("AnalysisService initialized, but InformalAgent could not be created/configured.")
        except Exception as e:
            self.logger.error(f"Critical error during AnalysisService initialization: {e}")
            self.is_initialized = False
    
    def is_healthy(self) -> bool:
        has_informal = self.informal_agent is not None
        has_analyzers = any([self.complex_analyzer, self.contextual_analyzer, self.severity_evaluator])
        is_healthy = self.is_initialized and (has_informal or has_analyzers)
        return is_healthy
    
    async def analyze_text(self, request: AnalysisRequest) -> AnalysisResponse:
        start_time = time.time()
        self.logger.info(f"ENTERING AnalysisService.analyze_text with text: '{request.text[:50]}...'")
        
        try:
            if not self.is_healthy():
                self.logger.warning("AnalysisService is not healthy - creating fallback response.")
                return self._create_fallback_response(request, start_time)
            
            fallacies = await self._detect_fallacies(request.text, request.options)
            structure = await asyncio.to_thread(self._analyze_structure, request.text, request.options)
            
            overall_quality = self._calculate_overall_quality(fallacies, structure)
            coherence_score = self._calculate_coherence_score(structure)

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
        fallacies = []
        self.logger.info(f"ENTERING _detect_fallacies with text: '{text[:50]}...'")
        
        if self.informal_agent:
            self.logger.info("Using InformalAgent for fallacy detection.")
            try:
                agent_response = self.informal_agent.invoke(input=text)
                full_response_str = ""
                result_data = None
                
                if inspect.isasyncgen(agent_response):
                    self.logger.info("Consuming agent response as an async generator (streaming).")
                    full_response_str = "".join([str(chunk.content) async for chunk in agent_response if chunk.content])
                    
                    if full_response_str.strip().startswith("```") and full_response_str.strip().endswith("```"):
                        json_str = full_response_str.strip()
                        json_str = json_str.removeprefix("```json").removesuffix("```").strip()
                        full_response_str = json_str
                    
                    tool_calls_data = json.loads(full_response_str)
                    if isinstance(tool_calls_data, list) and tool_calls_data:
                        first_tool_call = tool_calls_data[0]
                        if 'function' in first_tool_call and 'arguments' in first_tool_call['function']:
                            result_data = json.loads(first_tool_call['function']['arguments'])
                else:
                    self.logger.info("Consuming agent response as a direct awaitable (non-streaming).")
                    response_content = await agent_response
                    final_message = response_content[0] if isinstance(response_content, list) else response_content
                    if isinstance(final_message, ChatMessageContent) and final_message.tool_calls:
                        tool_call = final_message.tool_calls[0]
                        result_data = tool_call.function.arguments if hasattr(tool_call.function, 'arguments') else None

                if result_data and 'fallacies' in result_data and isinstance(result_data['fallacies'], list):
                    for fallacy_data in result_data['fallacies']:
                        fallacies.append(FallacyDetection(**fallacy_data))
            
            except ServiceResponseException as e:
                self.logger.error(f"A critical API error occurred during fallacy detection: {e}", exc_info=True)
                raise # Re-raise the exception to be caught by analyze_text
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode JSON from agent. Raw response: '''{full_response_str}'''. Error: {e}")
                # Do not raise, consider it a parsing failure, not a critical error
            except Exception as e:
                self.logger.error(f"An unexpected error occurred during agent response processing: {e}", exc_info=True)
                raise # Re-raise for other unexpected errors

        elif self.contextual_analyzer:
            self.logger.info("Using ContextualAnalyzer for fallacy detection.")
            result = await asyncio.to_thread(self.contextual_analyzer.identify_contextual_fallacies, argument=text, context="")
            if result:
                for fallacy_data in result:
                    fallacies.append(FallacyDetection(**fallacy_data))
            
        if options and hasattr(options, 'severity_threshold') and options.severity_threshold is not None:
             fallacies = [f for f in fallacies if f.severity >= options.severity_threshold]

        self.logger.info(f"EXITING _detect_fallacies, found {len(fallacies)} fallacies.")
        return fallacies

    def _analyze_structure(self, text: str, options: Optional[Any]) -> Optional[ArgumentStructure]:
        try:
            import re
            clean_text = text.strip()
            conclusion_indicators = [r'\bdonc\b', r'\bpar conséquent\b', r'\bainsi\b']
            premise_indicators = [r'\bparce que\b', r'\bcar\b', r'\bpuisque\b']
            premises = []
            conclusion = ""
            argument_type = "simple"
            
            conclusion_found = False
            for indicator in conclusion_indicators:
                if matches := list(re.finditer(indicator, clean_text, re.IGNORECASE)):
                    conclusion_found = True
                    conclusion = clean_text[matches[-1].end():].strip()
                    premises = [clean_text[:matches[-1].start()].strip()]
                    break
            
            if not conclusion_found:
                for indicator in premise_indicators:
                    if matches := list(re.finditer(indicator, clean_text, re.IGNORECASE)):
                        premises = [clean_text[matches[0].end():].strip()]
                        conclusion = clean_text[:matches[0].start()].strip()
                        conclusion_found = True
                        break

            if not conclusion_found:
                sentences = re.split(r'[.!?]+', clean_text)
                sentences = [s.strip() for s in sentences if s.strip()]
                if len(sentences) >= 2:
                    conclusion = sentences[-1]
                    premises = sentences[:-1]
                elif sentences:
                    conclusion = sentences[0]

            return ArgumentStructure(
                premises=premises,
                conclusion=conclusion,
                argument_type=argument_type,
                strength=0.5,
                coherence=0.5
            )
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de structure: {e}")
            return None
    
    def _calculate_overall_quality(self, fallacies: List[FallacyDetection], structure: Optional[ArgumentStructure]) -> float:
        fallacy_score = 1.0
        if fallacies:
            fallacy_penalty = sum(f.severity for f in fallacies) / len(fallacies)
            fallacy_score = 1.0 - fallacy_penalty
        structure_score = structure.strength if structure else 0.1
        return (fallacy_score * 0.7 + structure_score * 0.3)
    
    def _calculate_coherence_score(self, structure: Optional[ArgumentStructure]) -> float:
        return structure.coherence if structure else 0.3
    
    def _create_fallback_response(self, request: AnalysisRequest, start_time: float) -> AnalysisResponse:
        processing_time = time.time() - start_time
        return AnalysisResponse(
            success=False,
            text_analyzed=request.text,
            fallacies=[],
            argument_structure=ArgumentStructure(premises=[], conclusion=request.text, argument_type="unknown"),
            overall_quality=0.0,
            coherence_score=0.0,
            fallacy_count=0,
            processing_time=processing_time,
            analysis_options=request.options.dict() if request.options else {}
        )