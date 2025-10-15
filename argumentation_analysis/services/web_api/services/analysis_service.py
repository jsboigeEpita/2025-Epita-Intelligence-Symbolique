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
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.exceptions.service_exceptions import ServiceResponseException
import json

# Imports du moteur d'analyse (style b282af4 avec gestion d'erreur)
try:
    from argumentation_analysis.config.settings import AppSettings
    from argumentation_analysis.agents.factory import AgentFactory, AgentType
    from argumentation_analysis.agents.core.informal.informal_agent import (
        InformalAnalysisAgent,
    )
    from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import (
        ComplexFallacyAnalyzer,
    )
    from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import (
        ContextualFallacyAnalyzer,
    )
    from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import (
        FallacySeverityEvaluator,
    )
    from argumentation_analysis.orchestration.hierarchical.operational.manager import (
        OperationalManager,
    )

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
    # AgentFactory = None # This is now handled by the late import
    ComplexFallacyAnalyzer = None
    ContextualFallacyAnalyzer = None
    FallacySeverityEvaluator = None
    OperationalManager = None
    create_llm_service = None
    get_taxonomy_path = None

# Imports des modèles (style HEAD)
from argumentation_analysis.services.web_api.models.request_models import (
    AnalysisRequest,
)
from argumentation_analysis.services.web_api.models.response_models import (
    AnalysisResponse,
    FallacyDetection,
    ArgumentStructure,
)

logger = logging.getLogger("AnalysisService")


class AnalysisService:
    """
    Service pour l'analyse complète de textes argumentatifs.
    """

    def __init__(self, llm_service: ChatCompletionClientBase):
        """Initialise le service d'analyse."""
        self.logger = logger
        # self.settings is not set here in HEAD version
        self.is_initialized = False
        self._initialize_components(llm_service)

    def _initialize_components(self, llm_service: ChatCompletionClientBase) -> None:
        """Initialise les composants d'analyse internes du service.

        Tente d'instancier `ComplexFallacyAnalyzer`, `ContextualFallacyAnalyzer`,
        `FallacySeverityEvaluator`, et `InformalAgent`.
        Met à jour `self.is_initialized` en fonction du succès.

        :return: None
        :rtype: None
        """
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
            if self.complex_analyzer:
                self.tools["complex_fallacy_analyzer"] = self.complex_analyzer
            if self.contextual_analyzer:
                self.tools["contextual_fallacy_analyzer"] = self.contextual_analyzer
            if self.severity_evaluator:
                self.tools["fallacy_severity_evaluator"] = self.severity_evaluator

            try:
                from argumentation_analysis.agents.factory import AgentFactory
            except ImportError as e:
                self.logger.warning(f"Could not import AgentFactory: {e}")
                AgentFactory = None

            if AgentFactory and create_llm_service and get_taxonomy_path:
                self.logger.info(
                    "[INIT] Attempting to initialize informal agent via AgentFactory..."
                )
                kernel = sk.Kernel()
                llm_service_instance = None
                try:
                    llm_service_instance = create_llm_service(
                        service_id="default_analysis_llm"
                    )
                    kernel.add_service(llm_service_instance)
                except Exception as llm_e:
                    self.logger.error(
                        f"[ERROR] Failed to create LLM service for AgentFactory: {llm_e}"
                    )

                # Vérification des dépendances disponibles
                self.logger.info(
                    f"create_llm_service available: {create_llm_service is not None}"
                )
                self.logger.info(
                    f"get_taxonomy_path available: {get_taxonomy_path is not None}"
                )

                # Mode compatible sans dépendances manquantes
                if not create_llm_service or not get_taxonomy_path:
                    self.logger.warning(
                        "[WARN] Missing dependencies for AgentFactory - using fallback mode"
                    )
                    self.informal_agent = None
                else:
                    # Création du kernel et ajout du service LLM
                    kernel = sk.Kernel()
                    llm_service_instance = llm_service  # Utiliser le service injecté
                    if llm_service_instance:
                        kernel.add_service(llm_service_instance)
                        self.logger.info(
                            f"[OK] LLM service '{llm_service_instance.service_id}' injecté dans le kernel pour AgentFactory"
                        )
                    else:
                        self.logger.error(
                            "[ERROR] Aucun service LLM n'a été fourni à AnalysisService."
                        )

                    taxonomy_path_instance = None  # Renommé
                    try:
                        taxonomy_path_instance = get_taxonomy_path()
                        self.logger.info(
                            f"[OK] Taxonomy path obtained for AgentFactory: {taxonomy_path_instance}"
                        )
                    except Exception as tax_e:
                        self.logger.error(
                            f"[ERROR] Failed to get taxonomy path for AgentFactory: {tax_e}"
                        )

                    if kernel and llm_service_instance:
                        try:
                            # Créer une instance de settings par défaut pour la factory
                            app_settings = AppSettings()
                            factory = AgentFactory(
                                kernel=kernel,
                                llm_service_id=llm_service_instance.service_id,
                            )

                            # Utiliser la méthode générique pour créer l'agent
                            # L'argument 'agent_name' n'est pas attendu par la factory pour ce type d'agent.
                            # Il est géré en interne par la classe de l'agent.
                            self.informal_agent = factory.create_agent(
                                agent_type=AgentType.INFORMAL_FALLACY,
                                config_name="default_with_plugins",
                            )
                            self.logger.info(
                                "[OK] InformalAgent created and configured successfully via AgentFactory."
                            )
                        except Exception as factory_e:
                            self.logger.error(
                                f"[ERROR] Failed to create InformalAgent from factory: {factory_e}",
                                exc_info=True,
                            )
                            self.informal_agent = None
                    else:
                        self.logger.error(
                            "[ERROR] Cannot initialize InformalAgent - missing kernel or LLM service instance"
                        )
                        self.informal_agent = None
            else:
                self.logger.warning(
                    "[WARN] AgentFactory or its dependencies are not available."
                )
                self.informal_agent = None

            self.is_initialized = True
            if self.informal_agent:
                self.logger.info(
                    "AnalysisService initialized successfully (with InformalAgent)."
                )
            else:
                self.logger.warning(
                    "AnalysisService initialized, but InformalAgent could not be created/configured."
                )
        except Exception as e:
            self.logger.error(
                f"Critical error during AnalysisService initialization: {e}"
            )
            self.is_initialized = False

    def is_healthy(self) -> bool:
        has_informal = self.informal_agent is not None
        has_analyzers = any(
            [self.complex_analyzer, self.contextual_analyzer, self.severity_evaluator]
        )
        is_healthy = self.is_initialized and (has_informal or has_analyzers)
        return is_healthy

    async def analyze_text(self, request: AnalysisRequest) -> AnalysisResponse:
        start_time = time.time()
        self.logger.info(
            f"ENTERING AnalysisService.analyze_text with text: '{request.text[:50]}...'"
        )

        try:
            if not self.is_healthy():
                self.logger.warning(
                    "AnalysisService is not healthy - creating fallback response."
                )
                return self._create_fallback_response(request, start_time)

            fallacies = await self._detect_fallacies(request.text, request.options)
            structure = await asyncio.to_thread(
                self._analyze_structure, request.text, request.options
            )

            overall_quality = self._calculate_overall_quality(fallacies, structure)
            coherence_score = self._calculate_coherence_score(structure)

            processing_time = time.time() - start_time
            self.logger.info(
                f"EXITING AnalysisService.analyze_text successfully in {processing_time:.2f}s"
            )

            return AnalysisResponse(
                success=True,
                text_analyzed=request.text,
                fallacies=fallacies,
                argument_structure=structure,
                overall_quality=overall_quality,
                coherence_score=coherence_score,
                fallacy_count=len(fallacies),
                processing_time=processing_time,
                analysis_options=request.options.dict() if request.options else {},
            )
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse: {e}", exc_info=True)
            processing_time = time.time() - start_time
            self.logger.info(
                f"EXITING AnalysisService.analyze_text with ERROR in {processing_time:.2f}s"
            )
            return AnalysisResponse(
                success=False,
                text_analyzed=request.text,
                fallacies=[],
                argument_structure=None,
                overall_quality=0.0,
                coherence_score=0.0,
                fallacy_count=0,
                processing_time=processing_time,
                analysis_options=request.options.dict() if request.options else {},
            )

    async def _detect_fallacies(
        self, text: str, options: Optional[Any]
    ) -> List[FallacyDetection]:
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

                messages = [ChatMessageContent(role="user", content=text)]
                agent_response = self.informal_agent.invoke(messages)
                full_response_str = ""
                result = None

                self.logger.info(f"Agent response type: {type(agent_response)}")

                if inspect.isasyncgen(agent_response):
                    self.logger.info(
                        "Consuming agent response as an async generator (streaming)."
                    )

                    content_parts = []
                    async for message_content_list in agent_response:
                        for chunk in message_content_list:
                            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                                self.logger.info("Tool call detected in stream chunk.")
                                tool_call = chunk.tool_calls[0]

                                if hasattr(tool_call, "function") and hasattr(
                                    tool_call.function, "arguments"
                                ):
                                    arguments_str = tool_call.function.arguments
                                elif (
                                    isinstance(tool_call, dict)
                                    and "function" in tool_call
                                    and "arguments" in tool_call["function"]
                                ):
                                    arguments_str = tool_call["function"]["arguments"]
                                else:
                                    self.logger.warning(
                                        f"Could not extract arguments from tool_call: {tool_call}"
                                    )
                                    continue

                                if isinstance(arguments_str, str):
                                    try:
                                        result = json.loads(arguments_str)
                                        break
                                    except json.JSONDecodeError:
                                        self.logger.warning(
                                            f"Tool call argument is not valid JSON: {arguments_str}"
                                        )

                            if hasattr(chunk, "content") and chunk.content:
                                content_parts.append(str(chunk.content))

                        if result:
                            break

                    if not result and content_parts:
                        full_response_str = "".join(content_parts)
                        self.logger.debug(
                            f"Aggregated stream content: '''{full_response_str}'''"
                        )
                        try:
                            result = json.loads(full_response_str)
                        except json.JSONDecodeError:
                            self.logger.warning(
                                "Aggregated stream content is not valid JSON."
                            )
                else:
                    self.logger.warning(
                        "Consuming agent response as a direct awaitable (non-streaming fallback)."
                    )
                    response_content = await agent_response
                    final_message = (
                        response_content[0]
                        if isinstance(response_content, list) and response_content
                        else response_content
                    )
                    if (
                        isinstance(final_message, ChatMessageContent)
                        and final_message.tool_calls
                    ):
                        tool_call = final_message.tool_calls[0]
                        if hasattr(tool_call, "function"):
                            result = tool_call.function.arguments
                        elif isinstance(tool_call, dict) and "function" in tool_call:
                            result = json.loads(tool_call["function"]["arguments"])
                        else:
                            result = None

                if (
                    result
                    and "fallacies" in result
                    and isinstance(result["fallacies"], list)
                ):
                    for fallacy_data in result["fallacies"]:
                        fallacy = FallacyDetection(
                            type=fallacy_data.get("type", "semantic"),
                            name=fallacy_data.get(
                                "fallacy_type",
                                fallacy_data.get(
                                    "nom",
                                    fallacy_data.get("name", "Sophisme non identifié"),
                                ),
                            ),
                            description=fallacy_data.get(
                                "explication",
                                fallacy_data.get(
                                    "description", fallacy_data.get("explanation", "")
                                ),
                            ),
                            severity=fallacy_data.get("severity", 0.7),
                            confidence=fallacy_data.get("confidence", 0.8),
                            location=fallacy_data.get("location"),
                            context=fallacy_data.get(
                                "context", fallacy_data.get("reformulation")
                            ),
                            explanation=fallacy_data.get(
                                "explication", fallacy_data.get("explanation", "")
                            ),
                        )
                        fallacies.append(fallacy)

            # PRIORITÉ 3: Analyse contextuelle si les autres méthodes n'ont rien donné
            elif not fallacies and self.contextual_analyzer:
                self.logger.info(
                    "Using ContextualAnalyzer for fallacy detection (wrapped in asyncio.to_thread)."
                )
                # Wrap the synchronous, potentially blocking call in a separate thread.
                result = await asyncio.to_thread(
                    self.contextual_analyzer.identify_contextual_fallacies,
                    text,
                    "général",
                )
                if result:
                    for fallacy_data in result:
                        fallacy = FallacyDetection(
                            type=fallacy_data.get("type", "contextual"),
                            name=fallacy_data.get(
                                "fallacy_type", "Sophisme contextuel non identifié"
                            ),
                            description=fallacy_data.get("description", ""),
                            severity=fallacy_data.get("severity", 0.5),
                            confidence=fallacy_data.get("confidence", 0.5),
                            context=fallacy_data.get("context"),
                        )
                        fallacies.append(fallacy)

        except json.JSONDecodeError as e:
            self.logger.error(
                f"Failed to decode JSON from agent. Raw response: '''{full_response_str}'''. Error: {e}"
            )
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred during agent response processing: {e}",
                exc_info=True,
            )

        # Filtrage par seuil de sévérité
        if (
            options
            and hasattr(options, "severity_threshold")
            and options.severity_threshold is not None
        ):
            self.logger.info(
                f"Filtering fallacies with severity >= {options.severity_threshold}"
            )
            initial_count = len(fallacies)
            fallacies = [
                f for f in fallacies if f.severity >= options.severity_threshold
            ]
            self.logger.info(f"Filtered {initial_count - len(fallacies)} fallacies.")

        self.logger.info(
            f"EXITING _detect_fallacies, found {len(fallacies)} fallacies."
        )
        return fallacies

    def _analyze_structure(
        self, text: str, options: Optional[Any]
    ) -> Optional[ArgumentStructure]:
        try:
            import re

            clean_text = text.strip()
            conclusion_indicators = [r"\bdonc\b", r"\bpar conséquent\b", r"\bainsi\b"]
            premise_indicators = [r"\bparce que\b", r"\bcar\b", r"\bpuisque\b"]
            premises = []
            conclusion = ""
            argument_type = "simple"

            conclusion_found = False
            for indicator in conclusion_indicators:
                if matches := list(re.finditer(indicator, clean_text, re.IGNORECASE)):
                    conclusion_found = True
                    conclusion = clean_text[matches[-1].end() :].strip()
                    premises = [clean_text[: matches[-1].start()].strip()]
                    break

            if not conclusion_found:
                for indicator in premise_indicators:
                    if matches := list(
                        re.finditer(indicator, clean_text, re.IGNORECASE)
                    ):
                        premises = [clean_text[matches[0].end() :].strip()]
                        conclusion = clean_text[: matches[0].start()].strip()
                        conclusion_found = True
                        break

            if not conclusion_found:
                sentences = re.split(r"[.!?]+", clean_text)
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
                coherence=0.5,
            )
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de structure: {e}")
            return None

    def _calculate_overall_quality(
        self, fallacies: List[FallacyDetection], structure: Optional[ArgumentStructure]
    ) -> float:
        fallacy_score = 1.0
        if fallacies:
            fallacy_penalty = sum(f.severity for f in fallacies) / len(fallacies)
            fallacy_score = 1.0 - fallacy_penalty
        structure_score = structure.strength if structure else 0.1
        return fallacy_score * 0.7 + structure_score * 0.3

    def _calculate_coherence_score(
        self, structure: Optional[ArgumentStructure]
    ) -> float:
        return structure.coherence if structure else 0.3

    def _create_fallback_response(
        self, request: AnalysisRequest, start_time: float
    ) -> AnalysisResponse:
        processing_time = time.time() - start_time
        return AnalysisResponse(
            success=False,
            text_analyzed=request.text,
            fallacies=[],
            argument_structure=ArgumentStructure(
                premises=[], conclusion=request.text, argument_type="unknown"
            ),
            overall_quality=0.0,
            coherence_score=0.0,
            fallacy_count=0,
            processing_time=processing_time,
            analysis_options=request.options.dict() if request.options else {},
        )
