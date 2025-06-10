#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline d'Analyse Unifié
========================

Module réutilisable pour orchestrer les analyses rhétoriques avec :
- Support des deux modes : textes directs et textes chiffrés
- Pipeline parallélisé configurable
- Gestion des fallbacks automatiques
- Retry intelligent pour TweetyProject
- Validation d'authenticité intégrée

Utilisé par les scripts consolidés pour éviter la duplication.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class AnalysisMode(Enum):
    """Modes d'analyse disponibles."""
    FALLACIES = "fallacies"
    RHETORIC = "rhetoric" 
    LOGIC = "logic"
    COHERENCE = "coherence"
    SEMANTIC = "semantic"
    UNIFIED = "unified"
    ADVANCED = "advanced"


class SourceType(Enum):
    """Types de sources d'entrée."""
    TEXT = "text"
    FILE = "file"
    ENCRYPTED = "encrypted"
    BATCH = "batch"
    CORPUS = "corpus"


@dataclass
class AnalysisConfig:
    """Configuration pour le pipeline d'analyse."""
    # Modes d'analyse
    analysis_modes: List[AnalysisMode] = field(default_factory=lambda: [AnalysisMode.UNIFIED])
    
    # Configuration parallélisme
    enable_parallel: bool = True
    max_workers: int = 4
    batch_size: int = 10
    
    # Configuration retry
    retry_count: int = 3
    retry_delay: float = 1.0
    enable_fallback: bool = True
    
    # Configuration authenticité
    require_real_llm: bool = True
    require_real_tweety: bool = True
    mock_level: str = "none"
    
    # Configuration LLM
    llm_service: str = "openai"
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.3
    llm_timeout: int = 60
    
    # Configuration sortie
    save_intermediate: bool = False
    detailed_logging: bool = True


@dataclass
class AnalysisResult:
    """Résultat d'une analyse."""
    id: str
    timestamp: datetime
    source_type: SourceType
    content_preview: str
    analysis_modes: List[str]
    results: Dict[str, Any]
    execution_time: float
    status: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class UnifiedAnalysisPipeline:
    """Pipeline d'analyse unifié réutilisable."""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.UnifiedAnalysisPipeline")
        self.session_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results_cache = []
        
    async def analyze_text(self, text: str, source_type: SourceType = SourceType.TEXT) -> AnalysisResult:
        """
        Analyse un texte unique.
        
        Args:
            text: Texte à analyser
            source_type: Type de source
            
        Returns:
            Résultat de l'analyse
        """
        start_time = time.time()
        analysis_id = f"analysis_{len(self.results_cache) + 1}"
        
        self.logger.info(f"[ANALYSE] Analyse {analysis_id}: {len(text)} caractères")
        
        result = AnalysisResult(
            id=analysis_id,
            timestamp=datetime.now(),
            source_type=source_type,
            content_preview=text[:200] + "..." if len(text) > 200 else text,
            analysis_modes=[mode.value for mode in self.config.analysis_modes],
            results={},
            execution_time=0.0,
            status="processing"
        )
        
        try:
            # Exécution des analyses selon les modes configurés
            for mode in self.config.analysis_modes:
                mode_result = await self._execute_analysis_mode(text, mode)
                result.results[mode.value] = mode_result
            
            result.status = "completed"
            result.execution_time = time.time() - start_time
            
            self.logger.info(f"[OK] Analyse {analysis_id} terminée en {result.execution_time:.2f}s")
            
        except Exception as e:
            result.status = "error"
            result.errors.append(str(e))
            result.execution_time = time.time() - start_time
            
            self.logger.error(f"[ERREUR] Erreur analyse {analysis_id}: {e}")
        
        self.results_cache.append(result)
        return result
    
    async def analyze_batch(self, texts: List[str], source_type: SourceType = SourceType.BATCH) -> List[AnalysisResult]:
        """
        Analyse un lot de textes.
        
        Args:
            texts: Liste des textes à analyser
            source_type: Type de source
            
        Returns:
            Liste des résultats d'analyse
        """
        self.logger.info(f"[BATCH] Analyse batch: {len(texts)} textes")
        
        if self.config.enable_parallel:
            return await self._analyze_batch_parallel(texts, source_type)
        else:
            return await self._analyze_batch_sequential(texts, source_type)
    
    async def analyze_corpus_data(self, corpus_data: Dict[str, Any]) -> List[AnalysisResult]:
        """
        Analyse des données de corpus déchiffrées.
        
        Args:
            corpus_data: Données de corpus (résultat du déchiffrement)
            
        Returns:
            Liste des résultats d'analyse
        """
        self.logger.info("[CORPUS] Analyse de données de corpus")
        
        texts_to_analyze = []
        
        # Extraction des textes depuis les données de corpus
        for file_data in corpus_data.get("loaded_files", []):
            for definition in file_data.get("definitions", []):
                if "content" in definition and definition["content"]:
                    texts_to_analyze.append(definition["content"])
        
        if not texts_to_analyze:
            self.logger.warning("Aucun texte trouvé dans le corpus")
            return []
        
        return await self.analyze_batch(texts_to_analyze, SourceType.CORPUS)
    
    async def _execute_analysis_mode(self, text: str, mode: AnalysisMode) -> Dict[str, Any]:
        """Exécute un mode d'analyse spécifique avec retry."""
        
        for attempt in range(self.config.retry_count):
            try:
                if self.config.require_real_llm:
                    return await self._real_llm_analysis(text, mode)
                else:
                    return await self._mock_analysis(text, mode)
                    
            except Exception as e:
                if attempt < self.config.retry_count - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    self.logger.warning(f"[WARNING] Tentative {attempt + 1} échouée: {e}, retry dans {delay}s")
                    await asyncio.sleep(delay)
                else:
                    # Fallback si activé
                    if self.config.enable_fallback:
                        self.logger.warning(f"[FALLBACK] Activation du fallback pour {mode.value}")
                        return await self._fallback_analysis(text, mode)
                    raise
    
    async def _real_llm_analysis(self, text: str, mode: AnalysisMode) -> Dict[str, Any]:
        """Analyse authentique via LLM."""
        try:
            # Import dynamique pour éviter les erreurs
            from config.unified_config import UnifiedConfig, LogicType, MockLevel, AgentType
            from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
            import semantic_kernel as sk
            import os
            
            # Configuration selon le mode d'authenticité
            mock_level = MockLevel.NONE if self.config.mock_level == "none" else MockLevel.MINIMAL
            
            analysis_config = UnifiedConfig(
                logic_type=LogicType.PL,  # ← CHANGÉ: Propositional Logic sans Java
                agents=[AgentType.INFORMAL, AgentType.SYNTHESIS],  # ← CHANGÉ: Exclure FOL_LOGIC
                mock_level=mock_level,
                enable_jvm=False,  # ← CHANGÉ: Désactiver Java pour éviter les complications
                orchestration_type="unified"
            )
            
            # Création du kernel avec service OpenAI configuré
            kernel = sk.Kernel()
            
            # Configuration du service OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.logger.warning("[API-KEY] OPENAI_API_KEY non trouvée, utilisation fallback")
                return await self._fallback_analysis(text, mode)
            
            # Ajout du service OpenAI au kernel
            from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
            
            kernel.add_service(
                OpenAIChatCompletion(
                    service_id="openai",
                    ai_model_id=self.config.llm_model,
                    api_key=api_key
                )
            )
            
            self.logger.info(f"[OPENAI] Service OpenAI configuré avec modèle: {self.config.llm_model}")
            
            # Création et exécution de l'agent avec les bons paramètres
            agent = InformalAnalysisAgent(
                kernel=kernel,
                agent_name="PipelineInformalAgent"
            )
            
            # Setup avec un service LLM par défaut (méthode synchrone)
            agent.setup_agent_components(llm_service_id="openai")
            
            # Analyse selon le mode - utiliser la méthode appropriée
            analysis_result = await agent.analyze_text(text[:1000])  # Limite pour performance
            
            return {
                "mode": mode.value,
                "result": analysis_result,
                "authentic": True,
                "model_used": self.config.llm_model,
                "timestamp": datetime.now().isoformat()
            }
            
        except ImportError:
            # Fallback si les modules ne sont pas disponibles
            return await self._fallback_analysis(text, mode)
    
    async def _mock_analysis(self, text: str, mode: AnalysisMode) -> Dict[str, Any]:
        """Analyse simulée pour tests."""
        await asyncio.sleep(0.1)  # Simulation latence
        
        return {
            "mode": mode.value,
            "result": f"[MOCK] Analyse {mode.value} de {len(text)} caractères",
            "authentic": False,
            "model_used": "mock",
            "timestamp": datetime.now().isoformat(),
            "fallacies_detected": ["mock_fallacy"] if mode == AnalysisMode.FALLACIES else [],
            "confidence": 0.85
        }
    
    async def _fallback_analysis(self, text: str, mode: AnalysisMode) -> Dict[str, Any]:
        """Analyse de fallback simplifiée."""
        await asyncio.sleep(0.05)
        
        # Analyse basique basée sur des mots-clés
        fallback_result = {
            "mode": mode.value,
            "result": f"Analyse fallback {mode.value}",
            "authentic": False,
            "fallback": True,
            "timestamp": datetime.now().isoformat()
        }
        
        if mode == AnalysisMode.FALLACIES:
            # Détection simple de sophismes par mots-clés
            fallacy_keywords = {
                "ad_hominem": ["attaque", "personne", "individu"],
                "strawman": ["extrême", "caricature", "déformer"],
                "slippery_slope": ["conséquence", "mènera", "finira"]
            }
            
            detected_fallacies = []
            for fallacy, keywords in fallacy_keywords.items():
                if any(keyword in text.lower() for keyword in keywords):
                    detected_fallacies.append(fallacy)
            
            fallback_result["fallacies_detected"] = detected_fallacies
            fallback_result["confidence"] = 0.6
        
        return fallback_result
    
    async def _analyze_batch_parallel(self, texts: List[str], source_type: SourceType) -> List[AnalysisResult]:
        """Analyse en parallèle avec contrôle de concurrence."""
        semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def analyze_with_semaphore(text):
            async with semaphore:
                return await self.analyze_text(text, source_type)
        
        tasks = [analyze_with_semaphore(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Traitement des exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = AnalysisResult(
                    id=f"batch_error_{i}",
                    timestamp=datetime.now(),
                    source_type=source_type,
                    content_preview=texts[i][:200] if i < len(texts) else "unknown",
                    analysis_modes=[],
                    results={},
                    execution_time=0.0,
                    status="error",
                    errors=[str(result)]
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _analyze_batch_sequential(self, texts: List[str], source_type: SourceType) -> List[AnalysisResult]:
        """Analyse séquentielle avec progression."""
        results = []
        
        for i, text in enumerate(texts):
            self.logger.info(f"[DOC] Analyse {i+1}/{len(texts)}")
            try:
                result = await self.analyze_text(text, source_type)
                results.append(result)
            except Exception as e:
                error_result = AnalysisResult(
                    id=f"sequential_error_{i}",
                    timestamp=datetime.now(),
                    source_type=source_type,
                    content_preview=text[:200],
                    analysis_modes=[],
                    results={},
                    execution_time=0.0,
                    status="error",
                    errors=[str(e)]
                )
                results.append(error_result)
        
        return results
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de la session d'analyse."""
        total_analyses = len(self.results_cache)
        successful_analyses = len([r for r in self.results_cache if r.status == "completed"])
        failed_analyses = len([r for r in self.results_cache if r.status == "error"])
        
        total_time = sum(r.execution_time for r in self.results_cache)
        avg_time = total_time / total_analyses if total_analyses > 0 else 0
        
        return {
            "session_id": self.session_id,
            "total_analyses": total_analyses,
            "successful_analyses": successful_analyses,
            "failed_analyses": failed_analyses,
            "success_rate": successful_analyses / total_analyses if total_analyses > 0 else 0,
            "total_execution_time": total_time,
            "average_execution_time": avg_time,
            "analysis_modes": [mode.value for mode in self.config.analysis_modes]
        }


# Factory function pour faciliter l'utilisation
def create_analysis_pipeline(
    analysis_modes: Optional[List[str]] = None,
    parallel_workers: int = 4,
    require_authentic: bool = True
) -> UnifiedAnalysisPipeline:
    """Crée un pipeline d'analyse avec configuration simplifiée."""
    
    modes = []
    if analysis_modes:
        for mode_str in analysis_modes:
            try:
                modes.append(AnalysisMode(mode_str))
            except ValueError:
                logging.warning(f"Mode d'analyse invalide: {mode_str}")
    
    if not modes:
        modes = [AnalysisMode.UNIFIED]
    
    config = AnalysisConfig(
        analysis_modes=modes,
        max_workers=parallel_workers,
        require_real_llm=require_authentic,
        require_real_tweety=require_authentic,
        mock_level="none" if require_authentic else "minimal"
    )
    
    return UnifiedAnalysisPipeline(config)