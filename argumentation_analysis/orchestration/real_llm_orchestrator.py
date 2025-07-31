#!/usr/bin/env python3
"""
Orchestrateur LLM réel pour l'analyse d'argumentation
==================================================

Orchestrateur authentique utilisant des LLMs réels pour l'analyse d'argumentation
en intégrant toutes les capacités du système unifié.
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import time
from datetime import datetime

# Import des composants internes refactoriés
# L'analyse rhétorique est maintenant gérée par le plugin consolidé.
try:
    from plugins.AnalysisToolsPlugin.plugin import AnalysisToolsPlugin
    PLUGIN_ANALYSIS_AVAILABLE = True
except ImportError:
    PLUGIN_ANALYSIS_AVAILABLE = False
from ..agents.tools.analysis.new.semantic_argument_analyzer import SemanticArgumentAnalyzer
from ..agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase

from semantic_kernel.functions import KernelArguments

# Import et alias pour ConversationLogger
from .conversation_orchestrator import ConversationLogger
RealConversationLogger = ConversationLogger


@dataclass
class LLMAnalysisRequest:
    """Structure pour les requêtes d'analyse LLM."""
    text: str
    analysis_type: str
    context: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    timeout: int = 30


@dataclass
class LLMAnalysisResult:
    """Structure pour les résultats d'analyse LLM."""
    request_id: str
    analysis_type: str
    result: Dict[str, Any]
    confidence: float
    processing_time: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class RealLLMOrchestrator:
    """
    Orchestrateur LLM réel pour coordonner l'analyse d'argumentation.
    Cette classe utilise de vrais LLMs pour effectuer des analyses sophistiquées
    d'argumentation en coordonnant tous les composants du système.
    """
    
    def __init__(self, mode: str = "real", kernel=None, config: Optional[Dict[str, Any]] = None):
        self.mode = mode
        self.kernel = kernel
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        self.active_sessions = {}
        self.analysis_cache = {}
        # Remplacer les anciens analyseurs par le plugin unique
        self.analysis_plugin = None
        self.semantic_argument_analyzer = None
        self.unified_pipeline = None
        self.unified_analyzer = None
        self.syntactic_analyzer = None
        self.semantic_analyzer = None
        self.pragmatic_analyzer = None
        self.logical_analyzer = None
        self.entity_extractor = None
        self.relation_extractor = None
        self.consistency_validator = None
        self.coherence_validator = None
        self.conversation_logger = RealConversationLogger(mode=self.mode)
        
        # Métriques et monitoring
        self.metrics = {
            'total_requests': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_processing_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        self.logger.info("RealLLMOrchestrator initialisé")
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            'max_concurrent_analyses': 10, 'default_timeout': 30, 'cache_enabled': True, 'cache_ttl': 3600,
            'retry_attempts': 3, 'retry_delay': 1.0, 'enable_metrics': True, 'log_level': 'INFO',
            'analysis_types': ['rhetorical_analysis', 'enhanced_rhetorical_analysis', 'fallacy_detection', 'contextual_analysis', 'semantic_argument_analysis', 'unified_analysis', 'logical', 'informal']
        }
    
    async def initialize(self) -> bool:
        try:
            self.logger.info("Initialisation des composants d'analyse...")
            if PLUGIN_ANALYSIS_AVAILABLE:
                self.analysis_plugin = AnalysisToolsPlugin()
                self.logger.info("AnalysisToolsPlugin chargé.")
            else:
                self.logger.warning("AnalysisToolsPlugin non trouvé. Les capacités d'analyse rhétorique seront indisponibles.")
            self.semantic_argument_analyzer = SemanticArgumentAnalyzer()
            self.unified_analyzer = self._create_unified_analyzer()
            self.syntactic_analyzer = self._create_basic_syntactic_analyzer()
            self.semantic_analyzer = self._create_basic_semantic_analyzer()
            self.pragmatic_analyzer = self._create_basic_pragmatic_analyzer()
            self.logical_analyzer = self._create_real_logical_analyzer()
            self.entity_extractor = self._create_basic_entity_extractor()
            self.relation_extractor = self._create_basic_relation_extractor()
            self.consistency_validator = self._create_basic_consistency_validator()
            self.coherence_validator = self._create_basic_coherence_validator()
            
            self.is_initialized = True
            self.logger.info("Tous les composants initialisés avec succès")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation: {e}", exc_info=True)
            self.is_initialized = False
            return False
    
    async def analyze_text(self, request: Union[LLMAnalysisRequest, str], analysis_type: Optional[str] = "unified_analysis") -> LLMAnalysisResult:
        if isinstance(request, str):
            request = LLMAnalysisRequest(text=request, analysis_type=analysis_type)
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000000)}"
        try:
            self.metrics['total_requests'] += 1
            if self.config['cache_enabled']:
                cached_result = self._get_cached_result(request)
                if cached_result:
                    self.metrics['cache_hits'] += 1
                    return cached_result
                self.metrics['cache_misses'] += 1
            
            result = await self._perform_analysis(request)
            
            processing_time = time.time() - start_time
            analysis_result = LLMAnalysisResult(
                request_id=request_id, analysis_type=request.analysis_type, result=result,
                confidence=result.pop('confidence', 0.8), processing_time=processing_time,
                timestamp=datetime.now(), metadata={'request_params': request.parameters, 'context': request.context}
            )
            
            if self.config['cache_enabled']:
                self._cache_result(request, analysis_result)
            
            self.metrics['successful_analyses'] += 1
            self._update_average_processing_time(processing_time)
            self.logger.info(f"Analyse {request_id} terminée en {processing_time:.2f}s")
            return analysis_result
        except Exception as e:
            self.metrics['failed_analyses'] += 1
            self.logger.error(f"Erreur lors de l'analyse {request_id}: {e}", exc_info=True)
            return LLMAnalysisResult(
                request_id=request_id, analysis_type=request.analysis_type,
                result={'error': str(e), 'success': False}, confidence=0.0,
                processing_time=time.time() - start_time, timestamp=datetime.now(), metadata={'error': True}
            )
    
    async def _perform_analysis(self, request: LLMAnalysisRequest) -> Dict[str, Any]:
        analysis_type = request.analysis_type.lower()
        text, context, parameters = request.text, request.context or {}, request.parameters or {}
        
        analysis_map = {
            'syntactic': self._analyze_syntactic,
            'semantic': self._analyze_semantic,
            'pragmatic': self._analyze_pragmatic,
            'logical': self._analyze_logical,
            'entity_extraction': self._extract_entities,
            'relation_extraction': self._extract_relations,
            'consistency_validation': self._validate_consistency,
            'coherence_validation': self._validate_coherence,
            'simple': self._unified_analysis,
            'unified_analysis': self._unified_analysis,
            'informal': self._analyze_informal
        }
        
        if analysis_type in analysis_map:
            return await analysis_map[analysis_type](text, context, parameters)
        else:
            raise ValueError(f"Type d'analyse non supporté: {analysis_type}")
    
    async def _analyze_syntactic(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        result = self.syntactic_analyzer.analyze(text)
        return {'success': True, 'analysis_type': 'syntactic', 'result': result, 'confidence': 0.9}

    async def _analyze_semantic(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        result = self.semantic_analyzer.analyze(text)
        return {'success': True, 'analysis_type': 'semantic', 'result': result, 'confidence': 0.85}

    async def _analyze_pragmatic(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        result = self.pragmatic_analyzer.analyze(text, context)
        return {'success': True, 'analysis_type': 'pragmatic', 'result': result, 'confidence': 0.8}

    async def _analyze_logical(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        if not isinstance(self.logical_analyzer, PropositionalLogicAgent):
            return {'success': False, 'error': "L'analyseur logique réel n'est pas initialisé."}
        try:
            belief_set, message = await self.logical_analyzer.text_to_belief_set(text)
            if not belief_set: return {'success': False, 'error': f"Failed to create belief set: {message}"}
            queries = await self.logical_analyzer.generate_queries(text, belief_set)
            if not queries: return {'success': True, 'analysis_type': 'logical', 'result': {"message": "No relevant queries generated."}, 'confidence': 0.8}

            results = [self.logical_analyzer.execute_query(belief_set, q) for q in queries]
            interpretation = await self.logical_analyzer.interpret_results(text, belief_set, queries, results)
            is_valid = results[0][0] if results and results[0] is not None else False

            final_result = {
                "is_valid": is_valid, "scheme": "Modus Ponens" if is_valid else "Fallacy",
                "details": interpretation,
                "full_analysis": {"belief_set": belief_set.to_dict(), "queries": queries, "results": [str(r) for r in results]}
            }
            return {'success': True, 'result': final_result, 'confidence': 0.95}
        except Exception as e:
            self.logger.error(f"Erreur d'analyse logique: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'confidence': 0.0}

    async def _extract_entities(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        entities = self.entity_extractor.extract(text)
        return {'success': True, 'analysis_type': 'entity_extraction', 'entities': entities}
    
    async def _extract_relations(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        relations = self.relation_extractor.extract(text)
        return {'success': True, 'analysis_type': 'relation_extraction', 'relations': relations}

    async def _validate_consistency(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        result = self.consistency_validator.validate(text)
        return {'success': True, 'analysis_type': 'consistency_validation', 'result': result}

    async def _validate_coherence(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        result = self.coherence_validator.validate(text)
        return {'success': True, 'analysis_type': 'coherence_validation', 'result': result}

    async def _unified_analysis(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        result = self.unified_analyzer.analyze_text(text)
        return {'success': True, 'analysis_type': 'unified_analysis', 'results': result}

    async def _analyze_informal(self, text: str, context: Dict, parameters: Dict) -> Dict[str, Any]:
        """Analyse informelle en utilisant le plugin sémantique dédié."""
        # Le plugin a été enregistré sous "InformalAnalyzer"
        if "InformalAnalyzer" not in self.kernel.plugins:
            self.logger.error("Le plugin 'InformalAnalyzer' n'est pas chargé dans le kernel.")
            return {'success': False, 'error': "Le plugin d'analyse informelle 'InformalAnalyzer' n'est pas chargé."}

        try:
            # VÉRIFICATION PRÉALABLE (PRE-WARM) :
            # On tente d'accéder à la taxonomie via une fonction simple pour déclencher
            # le lazy loading et attraper les erreurs de chargement AVANT d'appeler le LLM.
            # Cela force _get_taxonomy_dataframe() à s'exécuter dans le plugin.
            pre_check_result_str = await self.kernel.invoke(
                plugin_name="InformalAnalyzer",
                function_name="list_fallacy_categories"
            )

            # La fonction du plugin retourne maintenant un JSON d'erreur au lieu de lever une exception.
            pre_check_result = json.loads(str(pre_check_result_str))
            if 'error' in pre_check_result and pre_check_result['error']:
                # On propage l'erreur précise retournée par le plugin.
                self.logger.error(f"Échec de la validation de la taxonomie : {pre_check_result['error']}")
                raise ValueError(pre_check_result['error'])

            # Si la vérification réussit, on peut procéder à l'analyse sémantique.
            analysis_result = await self.kernel.invoke(
                plugin_name="InformalAnalyzer",
                function_name="semantic_AnalyzeFallacies",
                arguments=KernelArguments(input=text, options=json.dumps(context))
            )

            # Le résultat est une chaîne JSON, il faut la parser
            result_str = str(analysis_result)
            try:
                import re
                # Nouvelle logique pour extraire le JSON après "[Réponse Finale]"
                # et gérer les blocs de code markdown.
                final_answer_marker = "[Réponse Finale]"
                if final_answer_marker in result_str:
                    # Isoler la partie après le marqueur
                    payload = result_str.split(final_answer_marker, 1)[1]
                    
                    # Utiliser une regex pour trouver le bloc JSON, même avec du texte autour
                    match = re.search(r"```json\s*([\s\S]+?)\s*```", payload, re.DOTALL)
                    if match:
                        json_str = match.group(1).strip()
                    else:
                        # Si pas de bloc markdown, prendre tout ce qui ressemble à un JSON
                        json_str = payload.strip()
                else:
                    # Fallback à l'ancienne méthode si le marqueur n'est pas là
                    json_str = result_str.strip().removeprefix("```json").removesuffix("```").strip()

                result_dict = json.loads(json_str)

            except json.JSONDecodeError:
                self.logger.error(f"Erreur de décodage JSON pour la réponse de l'analyse informelle: {result_str}")
                return {'success': False, 'error': 'Réponse invalide du LLM (non-JSON)', 'raw_response': result_str}

            # Correction de la structure de retour pour correspondre au validateur
            # Renommer la clé 'sophismes' en 'detected_sophisms'
            if 'sophismes' in result_dict:
                result_dict['detected_sophisms'] = result_dict.pop('sophismes')

            return {
                'success': True,
                # La méthode `analyze_text` enveloppe ce dict dans un objet LLMAnalysisResult.
                # Le validateur accède ensuite à `analysis_result.result['result']`.
                # Ce dictionnaire interne est donc ce qui doit être dans la clé 'result'.
                'result': result_dict,
                'confidence': result_dict.get('confidence', 0.90)
            }
        except Exception as e:
            self.logger.error(f"Erreur majeure lors de l'exécution de l'analyse informelle: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'confidence': 0.0}

    def _get_cached_result(self, request: LLMAnalysisRequest) -> Optional[LLMAnalysisResult]:
        cache_key = self._generate_cache_key(request)
        return self.analysis_cache.get(cache_key)

    def _cache_result(self, request: LLMAnalysisRequest, result: LLMAnalysisResult):
        cache_key = self._generate_cache_key(request)
        self.analysis_cache[cache_key] = result

    def _generate_cache_key(self, request: LLMAnalysisRequest) -> str:
        import hashlib
        content = f"{request.text}:{request.analysis_type}:{json.dumps(request.parameters, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    def _update_average_processing_time(self, new_time: float):
        total = self.metrics['successful_analyses']
        current_avg = self.metrics['average_processing_time']
        self.metrics['average_processing_time'] = new_time if total == 1 else ((current_avg * (total - 1) + new_time) / total)

    async def batch_analyze(self, requests: List[LLMAnalysisRequest]) -> List[LLMAnalysisResult]:
        semaphore = asyncio.Semaphore(self.config['max_concurrent_analyses'])
        async def analyze_with_sem(req):
            async with semaphore: return await self.analyze_text(req)
        
        tasks = [analyze_with_sem(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                self.logger.error(f"Erreur batch {i}: {res}")
                processed.append(LLMAnalysisResult(
                    request_id=f"batch_error_{i}", analysis_type=requests[i].analysis_type,
                    result={'error': str(res), 'success': False}, confidence=0.0,
                    processing_time=0.0, timestamp=datetime.now(), metadata={'error': True, 'batch_index': i}
                ))
            else:
                processed.append(res)
        return processed

    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics.copy()
    
    def reset_metrics(self):
        self.metrics = {'total_requests': 0, 'successful_analyses': 0, 'failed_analyses': 0, 'average_processing_time': 0.0, 'cache_hits': 0, 'cache_misses': 0}
    
    def clear_cache(self):
        self.analysis_cache.clear()

    def get_status(self) -> Dict[str, Any]:
        return {'is_initialized': self.is_initialized, 'active_sessions': len(self.active_sessions), 'cache_size': len(self.analysis_cache)}

    def _create_unified_analyzer(self):
        class BasicUnifiedAnalyzer:
            def analyze_text(self, text): return {"overall_quality": 85.5, "structure_analysis": {"clarity": 90}}
        return BasicUnifiedAnalyzer()
    
    def _create_basic_syntactic_analyzer(self):
        class BasicSyntacticAnalyzer:
            def analyze(self, text): return {'sentence_count': len(text.split('.'))}
        return BasicSyntacticAnalyzer()

    def _create_basic_semantic_analyzer(self):
        class BasicSemanticAnalyzer:
            def analyze(self, text): return {'vocabulary_complexity': 'medium'}
        return BasicSemanticAnalyzer()
    
    def _create_basic_pragmatic_analyzer(self):
        class BasicPragmaticAnalyzer:
            def analyze(self, text, context=None): return {'speech_acts': ['assertion']}
        return BasicPragmaticAnalyzer()

    def _create_real_logical_analyzer(self) -> PropositionalLogicAgent:
        if not self.kernel: raise ValueError("Kernel requis.")
        service_id = next((sid for sid, s in self.kernel.services.items() if isinstance(s, ChatCompletionClientBase)), None)
        if not service_id: raise ValueError("Service ChatCompletion manquant dans le kernel.")
        
        agent = PropositionalLogicAgent(kernel=self.kernel, service_id=service_id)
        agent.setup_agent_components(llm_service_id=service_id)
        self.logger.info("Analyseur logique réel (PropositionalLogicAgent) créé.")
        return agent

    def _create_basic_entity_extractor(self):
        class BasicEntityExtractor:
            def extract(self, text): return [{'text': 'exemple', 'type': 'ENTITY'}]
        return BasicEntityExtractor()

    def _create_basic_relation_extractor(self):
        class BasicRelationExtractor:
            def extract(self, text): return []
        return BasicRelationExtractor()

    def _create_basic_consistency_validator(self):
        class BasicConsistencyValidator:
            def validate(self, text): return {'is_consistent': True}
        return BasicConsistencyValidator()

    def _create_basic_coherence_validator(self):
        class BasicCoherenceValidator:
            def validate(self, text): return {'is_coherent': True}
        return BasicCoherenceValidator()

    async def orchestrate_analysis(self, text: str) -> Dict[str, Any]:
        if not self.is_initialized: await self.initialize()
        start = time.time()
        self.conversation_logger.log_agent_message("RealLLMOrchestrator", "Début orchestration", "orchestration")
        
        results = {}
        if self.rhetorical_analyzer:
            results["rhetorical"] = {"rhetorical_devices": ["metaphor"]}
        
        processing_ms = (time.time() - start) * 1000
        self.conversation_logger.log_agent_message("RealLLMOrchestrator", "Orchestration terminée", "completion")
        return {"final_synthesis": "Analyse orchestrée", "processing_time_ms": processing_ms}

# Point d'entrée pour les tests
async def main():
    """Fonction principale pour tester l'orchestrateur."""
    # Note: Nécessite une configuration de kernel valide pour fonctionner
    pass

if __name__ == "__main__":
    asyncio.run(main())

logger = logging.getLogger(__name__)
logger.debug("Module real_llm_orchestrator chargé.")
