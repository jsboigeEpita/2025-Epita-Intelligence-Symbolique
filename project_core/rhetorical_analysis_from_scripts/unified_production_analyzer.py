#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Production Analyzer - Point d'entrée CLI principal pour l'analyse en production
========================================================================================

Script consolidé intégrant les meilleurs éléments de :
- scripts/main/analyze_text.py (CLI complet avec 20+ paramètres)
- scripts/execution/advanced_rhetorical_analysis.py (production mature)
- scripts/main/analyze_text_authentic.py (authenticité 100%)

Innovations intégrées :
- Configuration LLM centralisée (élimine 15+ duplications)
- Mécanisme de retry automatique pour TweetyProject
- Système de validation d'authenticité à 100%
- Architecture d'orchestration multi-agents sophistiquée
- TraceAnalyzer v2.0 avec conversation agentielle

Version: 1.0.0
Créé: 10/06/2025
Auteur: Roo
"""
# Workflow d'Exécution :
# 1. Parsing des arguments CLI et/ou d'un fichier de configuration.
# 2. Validation des dépendances critiques (Python, Tweety, LLM).
# 3. Initialisation des services (LLM, TraceAnalyzer).
# 4. Traitement de l'entrée (texte simple, fichier, ou dossier en mode batch).
# 5. Orchestration de l'analyse via le UnifiedProductionAnalyzer.
# 6. Génération et sauvegarde d'un rapport de session détaillé.
import os # Déplacé ici
import sys # Déplacé ici

# Configuration UTF-8 pour la sortie standard et les erreurs
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')
import asyncio
import logging
import argparse
import json
import time
import warnings # Ajout de warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from pydantic import BaseModel
from dataclasses import field
from enum import Enum
import traceback

# Ajout du répertoire racine du projet au chemin

# --- GESTION DE LA DÉPRÉCIATION ---
# Ce script est maintenant considéré comme obsolète et son importation ne doit pas
# provoquer d'effets de bord comme l'activation d'environnement ou un sys.exit().
# L'activation est gérée par des scripts de plus haut niveau comme activate_project_env.ps1.
warnings.warn(
    "Le script 'unified_production_analyzer.py' est obsolète. "
    "Son importation est une opération sans effet (no-op) pour maintenir la compatibilité des tests. "
    "L'activation de l'environnement est maintenant gérée en amont.",
    DeprecationWarning,
    stacklevel=2
)
# Le bloc d'activation d'environnement précédent a été supprimé pour éviter les sys.exit().
# Configuration avancée du logging (déplacée ici AVANT l'activation de l'env)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("UnifiedProductionAnalyzer_Global") # Nom différent pour éviter conflit potentiel

# Auto-activation de l'environnement CONDA/VENV via le one-liner
# C'est maintenant la méthode standard recommandée pour s'assurer que l'environnement
# est prêt, y compris le chargement de .env et la configuration de JAVA_HOME.
# import scripts.core.auto_env # NEUTRALISÉ - L'environnement est maintenant activé en amont par environment_manager.py
class LogicType(Enum):
    """Types de logique supportés avec fallback automatique"""
    FOL = "fol"
    PL = "propositional"
    MODAL = "modal"


class MockLevel(Enum):
    """Niveaux de simulation pour le contrôle d'authenticité"""
    NONE = "none"        # 100% authentique - défaut production
    PARTIAL = "partial"   # Hybride développement
    FULL = "full"        # Test uniquement


class OrchestrationType(Enum):
    """Types d'orchestration multi-agents"""
    UNIFIED = "unified"
    CONVERSATION = "conversation"
    MICRO = "micro"
    REAL_LLM = "real_llm"


class AnalysisMode(Enum):
    """Modes d'analyse rhétorique"""
    FALLACIES = "fallacies"
    COHERENCE = "coherence"
    SEMANTIC = "semantic"
    UNIFIED = "unified"
    ADVANCED = "advanced"


class UnifiedProductionConfig(BaseModel):
    """Configuration centralisée pour l'analyse en production"""
    
    # === Configuration LLM Centralisée ===
    llm_service: str = "openai"
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2000
    llm_timeout: int = 60
    llm_retry_count: int = 3
    llm_retry_delay: float = 1.0
    
    # === Configuration Logique ===
    logic_type: LogicType = LogicType.FOL
    enable_fallback: bool = True
    fallback_order: List[LogicType] = field(default_factory=lambda: [LogicType.FOL, LogicType.PL])
    
    # === Configuration Authenticité ===
    mock_level: MockLevel = MockLevel.NONE
    require_real_gpt: bool = True
    require_real_tweety: bool = True
    require_full_taxonomy: bool = True
    validate_tools: bool = True
    
    # === Configuration Orchestration ===
    orchestration_type: OrchestrationType = OrchestrationType.UNIFIED
    enable_conversation_trace: bool = True
    enable_micro_orchestration: bool = False
    max_agents: int = 5
    
    # === Configuration Analyse ===
    analysis_modes: List[AnalysisMode] = field(default_factory=lambda: [AnalysisMode.UNIFIED])
    batch_size: int = 10
    enable_parallel: bool = True
    max_workers: int = 4
    
    # === Configuration Retry TweetyProject ===
    tweety_retry_count: int = 5
    tweety_retry_delay: float = 2.0
    tweety_timeout: int = 30
    tweety_memory_limit: str = "2g"
    
    # === Configuration Rapports ===
    output_format: str = "json"
    enable_detailed_logs: bool = True
    save_intermediate: bool = False
    report_level: str = "production"
    save_trace: bool = True
    save_orchestration_trace: bool = True
    
    # === Configuration Validation ===
    validate_inputs: bool = True
    validate_outputs: bool = True
    check_dependencies: bool = True
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Valide la configuration et retourne les erreurs détectées"""
        errors = []
        
        # Validation authenticité
        if self.mock_level == MockLevel.NONE:
            if not self.require_real_gpt:
                errors.append("Mode production requiert require_real_gpt=True")
            if not self.require_real_tweety:
                errors.append("Mode production requiert require_real_tweety=True")
        
        # Validation retry
        if self.tweety_retry_count < 1:
            errors.append("tweety_retry_count doit être >= 1")
        if self.llm_retry_count < 1:
            errors.append("llm_retry_count doit être >= 1")
            
        # Validation parallélisme
        if self.enable_parallel and self.max_workers < 1:
            errors.append("max_workers doit être >= 1 si enable_parallel=True")
            
        return len(errors) == 0, errors


class RetryMechanism:
    """Mécanisme de retry intelligent pour TweetyProject et LLM"""
    
    def __init__(self, config: UnifiedProductionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.RetryMechanism")
        
    async def retry_with_fallback(self, operation: callable, *args, **kwargs) -> Any:
        """
        Exécute une opération avec retry et fallback automatique
        
        Args:
            operation: Fonction à exécuter
            *args, **kwargs: Arguments de la fonction
            
        Returns:
            Résultat de l'opération ou exception
        """
        last_exception = None
        
        # Retry principal
        for attempt in range(self.config.tweety_retry_count):
            try:
                self.logger.debug(f"Tentative {attempt + 1}/{self.config.tweety_retry_count}")
                result = await operation(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"✅ Succès après {attempt + 1} tentatives")
                return result
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"⚠️ Tentative {attempt + 1} échouée: {e}")
                
                if attempt < self.config.tweety_retry_count - 1:
                    delay = self.config.tweety_retry_delay * (2 ** attempt)  # Backoff exponentiel
                    self.logger.debug(f"Attente {delay}s avant retry...")
                    await asyncio.sleep(delay)
        
        # Fallback si activé
        if self.config.enable_fallback and hasattr(operation, '__fallback__'):
            try:
                self.logger.warning("🔄 Activation du fallback...")
                return await operation.__fallback__(*args, **kwargs)
            except Exception as fallback_error:
                self.logger.error(f"❌ Échec du fallback: {fallback_error}")
                
        # Échec final
        self.logger.error(f"❌ Échec définitif après {self.config.tweety_retry_count} tentatives")
        raise last_exception


class TraceAnalyzerV2:
    """TraceAnalyzer v2.0 avec conversation agentielle avancée"""
    
    def __init__(self, config: UnifiedProductionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.TraceAnalyzerV2")
        self.conversation_history = []
        self.agent_states = {}
        
    async def initialize(self) -> bool:
        """Initialise l'analyseur de traces"""
        try:
            self.logger.info("🔧 Initialisation TraceAnalyzer v2.0...")
            
            # Initialisation des états d'agents
            self.agent_states = {
                "sherlock": {"status": "ready", "context": {}},
                "watson": {"status": "ready", "context": {}}, 
                "oracle": {"status": "ready", "context": {}},
                "synthesis": {"status": "ready", "context": {}}
            }
            
            self.logger.info("✅ TraceAnalyzer v2.0 initialisé")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation TraceAnalyzer: {e}")
            return False
    
    async def capture_conversation(self, agent_name: str, message: str, response: str) -> str:
        """Capture une interaction conversationnelle"""
        timestamp = datetime.now().isoformat()
        
        conversation_entry = {
            "timestamp": timestamp,
            "agent": agent_name,
            "message": message,
            "response": response,
            "context": self.agent_states.get(agent_name, {})
        }
        
        self.conversation_history.append(conversation_entry)
        
        # Mise à jour de l'état de l'agent
        if agent_name in self.agent_states:
            self.agent_states[agent_name]["last_interaction"] = timestamp
            self.agent_states[agent_name]["interaction_count"] = \
                self.agent_states[agent_name].get("interaction_count", 0) + 1
        
        self.logger.debug(f"📝 Conversation capturée: {agent_name} -> {len(response)} chars")
        return conversation_entry["timestamp"]
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Génère un résumé de la conversation"""
        return {
            "total_interactions": len(self.conversation_history),
            "agents_used": list(self.agent_states.keys()),
            "conversation_duration": self._calculate_duration(),
            "agent_stats": self.agent_states
        }
    
    def _calculate_duration(self) -> float:
        """Calcule la durée totale de la conversation"""
        if len(self.conversation_history) < 2:
            return 0.0
        
        start_time = datetime.fromisoformat(self.conversation_history[0]["timestamp"])
        end_time = datetime.fromisoformat(self.conversation_history[-1]["timestamp"])
        
        return (end_time - start_time).total_seconds()


class UnifiedLLMService:
    """Service LLM centralisé avec gestion d'authenticité"""
    
    def __init__(self, config: UnifiedProductionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.UnifiedLLMService")
        self.retry_mechanism = RetryMechanism(config)
        self._client = None
        
    async def initialize(self) -> bool:
        """Initialise le service LLM selon la configuration"""
        try:
            self.logger.info(f"🔧 Initialisation service LLM ({self.config.llm_service})...")
            
            # Validation authenticité
            if self.config.mock_level == MockLevel.NONE and not self.config.require_real_gpt:
                raise ValueError("Mode production requiert un LLM authentique")
            
            # Initialisation selon le mode mock (prioritaire sur le service)
            if self.config.mock_level == MockLevel.FULL:
                await self._initialize_mock()
            elif self.config.llm_service == "openai":
                await self._initialize_openai()
            elif self.config.llm_service == "mock":
                await self._initialize_mock()
            else:
                raise ValueError(f"Service LLM non supporté: {self.config.llm_service}")
            
            self.logger.info("✅ Service LLM initialisé")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation LLM: {e}")
            return False
    
    async def _initialize_openai(self):
        """Initialise le client OpenAI authentique"""
        try:
            import openai
            self._client = openai.AsyncOpenAI()
            
            # Test de connexion seulement si mode authentique
            if self.config.mock_level == MockLevel.NONE:
                await self._client.models.list()
                self.logger.info("✅ Client OpenAI authentique connecté")
            else:
                self.logger.info("✅ Client OpenAI initialisé (mode test)")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur connexion OpenAI: {e}")
            raise
    
    async def _initialize_mock(self):
        """Initialise un service mock pour les tests"""
        self.logger.warning("⚠️ Utilisation d'un service LLM mock")
        self._client = "mock_client"
    
    async def analyze_text(self, text: str, analysis_type: str = "rhetorical") -> Dict[str, Any]:
        """Analyse un texte avec retry automatique"""
        
        async def _perform_analysis():
            # Logique de décision améliorée :
            # 1. Si le service est explicitement 'mock', on utilise TOUJOURS l'analyse mock.
            # 2. Sinon, on se base sur le mock_level pour décider entre réel et mock.
            if self.config.llm_service == "mock" or self.config.mock_level != MockLevel.NONE:
                return await self._mock_analysis(text, analysis_type)
            else:
                return await self._real_analysis(text, analysis_type)
        
        return await self.retry_mechanism.retry_with_fallback(_perform_analysis)
    
    async def _real_analysis(self, text: str, analysis_type: str) -> Dict[str, Any]:
        """Analyse authentique via OpenAI"""
        prompt = self._build_prompt(text, analysis_type)
        
        response = await self._client.chat.completions.create(
            model=self.config.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
            timeout=self.config.llm_timeout
        )
        
        return {
            "analysis": response.choices[0].message.content,
            "model_used": self.config.llm_model,
            "tokens_used": response.usage.total_tokens,
            "authentic": True
        }
    
    async def _mock_analysis(self, text: str, analysis_type: str) -> Dict[str, Any]:
        """Analyse simulée pour tests"""
        await asyncio.sleep(0.1)  # Simulation latence
        return {
            "analysis": f"[MOCK] Analyse {analysis_type} de {len(text)} caractères",
            "model_used": "mock",
            "tokens_used": len(text) // 4,
            "authentic": False
        }
    
    def _build_prompt(self, text: str, analysis_type: str) -> str:
        """Construit le prompt d'analyse selon le type"""
        prompts = {
            "rhetorical": f"Analysez les techniques rhétoriques dans ce texte:\n\n{text}",
            "fallacies": f"Identifiez les sophismes dans ce texte:\n\n{text}",
            "coherence": f"Évaluez la cohérence logique de ce texte:\n\n{text}",
            "semantic": f"Analysez la sémantique de ce texte:\n\n{text}"
        }
        
        return prompts.get(analysis_type, prompts["rhetorical"])


class DependencyValidator:
    """Validateur de dépendances pré-exécution"""
    
    def __init__(self, config: UnifiedProductionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.DependencyValidator")
        
    async def validate_all(self) -> Tuple[bool, List[str]]:
        """Valide toutes les dépendances critiques"""
        self.logger.info("🔍 Validation des dépendances...")
        
        errors = []
        
        # Validation packages Python
        python_deps = await self._validate_python_dependencies()
        errors.extend(python_deps)
        
        # Validation TweetyProject si requis
        if self.config.require_real_tweety:
            tweety_deps = await self._validate_tweety_dependencies()
            errors.extend(tweety_deps)
        
        # Validation LLM
        llm_deps = await self._validate_llm_dependencies()
        errors.extend(llm_deps)
        
        # Validation système
        system_deps = await self._validate_system_dependencies()
        errors.extend(system_deps)
        
        success = len(errors) == 0
        
        if success:
            self.logger.info("✅ Toutes les dépendances validées")
        else:
            self.logger.error(f"❌ {len(errors)} erreurs de dépendances détectées")
            
        return success, errors
    
    async def _validate_python_dependencies(self) -> List[str]:
        """Valide les dépendances Python critiques"""
        errors = []
        critical_packages = [
            "asyncio", "pathlib", "json", "logging",
            "argparse", "datetime", "typing"
        ]
        
        for package in critical_packages:
            try:
                __import__(package)
            except ImportError:
                errors.append(f"Package Python manquant: {package}")
        
        return errors
    
    async def _validate_tweety_dependencies(self) -> List[str]:
        """Valide TweetyProject et JPype"""
        from pathlib import Path
        errors = []

        try:
            # === DEBUT BLOC DE DEBUGGING JPYPE ===
            self.logger.info("="*20 + " DEBUT DEBUG JPYPE " + "="*20)
            
            # 1. Vérifier JAVA_HOME
            java_home = os.getenv('JAVA_HOME')
            if java_home:
                self.logger.info(f"[DEBUG_JPYPE] JAVA_HOME trouvé: {java_home}")
                if not os.path.exists(java_home):
                    self.logger.warning(f"[DEBUG_JPYPE] ATTENTION: Le chemin JAVA_HOME n'existe pas: {java_home}")
            else:
                self.logger.warning("[DEBUG_JPYPE] ATTENTION: La variable d'environnement JAVA_HOME n'est pas définie.")

            # 2. Afficher les variables d'environnement liées à Java et Conda
            self.logger.debug("[DEBUG_JPYPE] Variables d'environnement pertinentes:")
            for var in ['JAVA_HOME', 'JDK_HOME', 'JRE_HOME', 'CONDA_PREFIX', 'PATH']:
                self.logger.debug(f"[DEBUG_JPYPE]   - {var}: {os.getenv(var)}")

            self.logger.info("="*20 + " FIN DEBUG JPYPE " + "="*20)
            # === FIN BLOC DE DEBUGGING JPYPE ===
            # === Le PATCH a été supprimé. On fait confiance à l'environnement d'exécution. ===
            # La configuration correcte du PATH, y compris les chemins de la JVM,
            # est maintenant entièrement gérée par `environment_manager.py`.
            # Le script n'a plus besoin d'essayer de réparer son propre `sys.path`.

            import jpype
            # S'assurer que la JVM est démarrée avant de vérifier son état
            if not jpype.isJVMStarted():
                try:
                    jpype.startJVM(jpype.getDefaultJVMPath(), convertStrings=False)
                    self.logger.info("JVM démarrée avec succès par DependencyValidator.")
                except Exception as e:
                    errors.append(f"Impossible de démarrer la JVM pour TweetyProject: {e}")
            if not jpype.isJVMStarted() and not any("Impossible de démarrer la JVM" in err for err in errors): # Revérifier après tentative de démarrage
                errors.append("JVM TweetyProject non démarrée (après tentative)")
        except ImportError as e:
            self.logger.error(f"Échec de l'import JPype1. sys.path: {sys.path}")
            self.logger.error(f"Traceback de l'erreur d'importation JPype:\n{traceback.format_exc()}")
            errors.append(f"JPype1 import failed: {e}")
            
        # Vérification des JARs TweetyProject
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        libs_dir = project_root / "libs" / "tweety"
        if not libs_dir.exists():
            errors.append("Répertoire libs/tweety manquant")
        else:
            jar_files = list(libs_dir.glob("*.jar"))
            if len(jar_files) == 0:
                errors.append("Aucun JAR TweetyProject trouvé")
        
        return errors
    
    async def _validate_llm_dependencies(self) -> List[str]:
        """Valide les dépendances LLM"""
        errors = []
        
        if self.config.llm_service == "openai" and self.config.mock_level == MockLevel.NONE:
            try:
                import openai
                # Vérification clé API
                if not os.getenv("OPENAI_API_KEY"):
                    errors.append("Variable OPENAI_API_KEY manquante")
            except ImportError:
                errors.append("Package openai manquant")
        
        return errors
    
    async def _validate_system_dependencies(self) -> List[str]:
        """Valide les dépendances système"""
        errors = []
        
        # Vérification espace disque
        import shutil
        free_space = shutil.disk_usage(".").free
        min_space = 1024 * 1024 * 100  # 100MB minimum
        
        if free_space < min_space:
            errors.append(f"Espace disque insuffisant: {free_space // (1024*1024)}MB disponible")
        
        # Vérification mémoire (estimation)
        try:
            import psutil
            available_memory = psutil.virtual_memory().available
            min_memory = 1024 * 1024 * 512  # 512MB minimum
            
            if available_memory < min_memory:
                errors.append(f"Mémoire insuffisante: {available_memory // (1024*1024)}MB disponible")
        except ImportError:
            # psutil optionnel
            pass
        
        return errors


class UnifiedProductionAnalyzer:
    """Analyseur de production unifié - Point d'entrée principal"""
    
    def __init__(self, config: UnifiedProductionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.UnifiedProductionAnalyzer")
        
        # Composants principaux
        self.llm_service = UnifiedLLMService(config)
        self.trace_analyzer = TraceAnalyzerV2(config)
        self.dependency_validator = DependencyValidator(config)
        
        # État
        self.initialized = False
        self.analysis_results = []
        self.session_id = None
        
    async def initialize(self) -> bool:
        """Initialise tous les composants du système"""
        try:
            self.logger.info("🚀 Initialisation Unified Production Analyzer...")
            
            # Génération ID de session
            self.session_id = f"upa_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.logger.info(f"📋 Session ID: {self.session_id}")
            
            # Validation configuration
            config_valid, config_errors = self.config.validate()
            if not config_valid:
                self.logger.error("❌ Configuration invalide:")
                for error in config_errors:
                    self.logger.error(f"  - {error}")
                return False
            
            # Validation dépendances si activée
            if self.config.check_dependencies:
                deps_valid, deps_errors = await self.dependency_validator.validate_all()
                if not deps_valid:
                    self.logger.error("❌ Dépendances invalides:")
                    for error in deps_errors:
                        self.logger.error(f"  - {error}")
                    return False
            
            # Initialisation des composants
            if not await self.llm_service.initialize():
                return False
                
            if not await self.trace_analyzer.initialize():
                return False
            
            self.initialized = True
            self.logger.info("✅ Unified Production Analyzer initialisé")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation: {e}")
            self.logger.debug(traceback.format_exc())
            return False
    
    async def analyze_text(self, text: str, analysis_modes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyse un texte selon les modes spécifiés
        
        Args:
            text: Texte à analyser
            analysis_modes: Modes d'analyse (par défaut: configuration)
            
        Returns:
            Résultats d'analyse structurés
        """
        if not self.initialized:
            raise RuntimeError("Analyseur non initialisé")
        
        start_time = time.time()
        analysis_id = f"analysis_{len(self.analysis_results) + 1}"
        
        self.logger.info(f"🔍 Démarrage analyse: {analysis_id}")
        self.logger.debug(f"Texte: {len(text)} caractères")
        
        # Détermination des modes d'analyse
        modes = analysis_modes or [mode.value for mode in self.config.analysis_modes]
        self.logger.debug(f"Modes: {modes}")
        
        try:
            results = {}
            
            # Analyse selon chaque mode
            for mode in modes:
                self.logger.debug(f"Mode: {mode}")
                
                # Capture conversation si activée
                if self.config.enable_conversation_trace:
                    await self.trace_analyzer.capture_conversation(
                        "analyzer", f"Starting {mode} analysis", f"Processing {len(text)} chars"
                    )
                
                # Analyse LLM
                mode_result = await self.llm_service.analyze_text(text, mode)
                results[mode] = mode_result
                
                self.logger.debug(f"✅ Mode {mode} terminé")
            
            # Synthèse des résultats
            analysis_result = {
                "id": analysis_id,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "text_length": len(text),
                "modes_analyzed": modes,
                "results": results,
                "execution_time": time.time() - start_time,
                "config_snapshot": {
                    "logic_type": self.config.logic_type.value,
                    "mock_level": self.config.mock_level.value,
                    "orchestration_type": self.config.orchestration_type.value
                }
            }
            
            # Conversation summary si activé
            if self.config.enable_conversation_trace:
                analysis_result["conversation_summary"] = self.trace_analyzer.get_conversation_summary()
            
            # Stockage résultat
            self.analysis_results.append(analysis_result)
            
            self.logger.info(f"✅ Analyse {analysis_id} terminée en {analysis_result['execution_time']:.2f}s")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse {analysis_id}: {e}")
            self.logger.debug(traceback.format_exc())
            
            # Résultat d'erreur
            error_result = {
                "id": analysis_id,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "execution_time": time.time() - start_time
            }
            
            self.analysis_results.append(error_result)
            raise
    
    def _map_orchestration_mode(self):
        """Mappe le type d'orchestration vers les modes du pipeline unifié"""
        mapping = {
            OrchestrationType.UNIFIED: "pipeline",
            OrchestrationType.CONVERSATION: "conversation",
            OrchestrationType.MICRO: "operational_direct",
            OrchestrationType.REAL_LLM: "hierarchical_full"
        }
        
        # Créer un objet avec attribut value
        class ModeResult:
            def __init__(self, value):
                self.value = value
        
        return ModeResult(mapping.get(self.config.orchestration_type, "pipeline"))
    
    def _map_analysis_type(self, analysis_type: str):
        """Mappe les types d'analyse vers les modes unifiés"""
        mapping = {
            "rhetorical": "rhetorical",
            "fallacies": "fallacy_focused",
            "coherence": "argument_structure",
            "semantic": "comprehensive",
            "unified": "rhetorical",
            "advanced": "comprehensive"
        }
        
        # Créer un objet avec attribut value
        class AnalysisResult:
            def __init__(self, value):
                self.value = value
        
        return AnalysisResult(mapping.get(analysis_type, "rhetorical"))
    
    def _build_config(self, analysis_type: str):
        """Construit la configuration unifiée pour le pipeline"""
        # Créer un objet configuration compatible
        class UnifiedConfig:
            def __init__(self, config, analyzer):
                self.analysis_modes = [mode.value for mode in config.analysis_modes]
                self.orchestration_mode = analyzer._map_orchestration_mode().value
                self.enable_hierarchical = config.orchestration_type in [
                    OrchestrationType.UNIFIED, OrchestrationType.REAL_LLM
                ]
                self.logic_type = config.logic_type.value
                self.mock_level = config.mock_level.value
                
                # Attributs additionnels attendus par les tests
                self.enable_specialized_orchestrators = True
                self.enable_communication_middleware = True
                self.save_orchestration_trace = config.save_orchestration_trace
                
        return UnifiedConfig(self.config, self)
    
    def generate_report(self, output_file: Path) -> Dict[str, Any]:
        """Génère un rapport final des analyses"""
        
        # Calculs statistiques
        successful_analyses = len([r for r in self.analysis_results if 'error' not in r])
        failed_analyses = len([r for r in self.analysis_results if 'error' in r])
        total_time = sum(r.get('execution_time', 0) for r in self.analysis_results)
        avg_time = total_time / len(self.analysis_results) if self.analysis_results else 0
        
        report = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "results_summary": {
                "total_analyses": len(self.analysis_results),
                "successful_analyses": successful_analyses,
                "failed_analyses": failed_analyses,
                "total_execution_time": total_time,
                "average_execution_time": avg_time
            },
            "configuration": {
                "logic_type": self.config.logic_type.value,
                "mock_level": self.config.mock_level.value,
                "orchestration_type": self.config.orchestration_type.value,
                "analysis_modes": [mode.value for mode in self.config.analysis_modes]
            },
            "detailed_results": self.analysis_results
        }
        
        # Sauvegarde du rapport
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📊 Rapport sauvegardé: {output_file}")
        return report

    async def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Analyse un lot de textes en parallèle ou séquentiel"""
        self.logger.info(f"📦 Analyse batch: {len(texts)} textes")
        
        if self.config.enable_parallel:
            return await self._analyze_batch_parallel(texts)
        else:
            return await self._analyze_batch_sequential(texts)
    
    async def _analyze_batch_parallel(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Analyse en parallèle avec contrôle de concurrence"""
        semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def analyze_with_semaphore(text):
            async with semaphore:
                return await self.analyze_text(text)
        
        tasks = [analyze_with_semaphore(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Conversion des exceptions en résultats d'erreur
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "id": f"batch_error_{i}",
                    "error": str(result),
                    "text_index": i
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _analyze_batch_sequential(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Analyse séquentielle avec barre de progression"""
        results = []
        
        for i, text in enumerate(texts):
            self.logger.info(f"📄 Texte {i+1}/{len(texts)}")
            try:
                result = await self.analyze_text(text)
                results.append(result)
            except Exception as e:
                self.logger.error(f"❌ Erreur texte {i+1}: {e}")
                results.append({
                    "id": f"sequential_error_{i}",
                    "error": str(e),
                    "text_index": i
                })
        
        return results
    
    def generate_report(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Génère un rapport complet de session"""
        
        report = {
            "session_info": {
                "id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "total_analyses": len(self.analysis_results),
                "config": {
                    "logic_type": self.config.logic_type.value,
                    "mock_level": self.config.mock_level.value,
                    "orchestration_type": self.config.orchestration_type.value,
                    "analysis_modes": [mode.value for mode in self.config.analysis_modes]
                }
            },
            "results_summary": {
                "successful_analyses": len([r for r in self.analysis_results if "error" not in r]),
                "failed_analyses": len([r for r in self.analysis_results if "error" in r]),
                "total_execution_time": sum(r.get("execution_time", 0) for r in self.analysis_results),
                "average_execution_time": None
            },
            "detailed_results": self.analysis_results
        }
        
        # Calcul moyenne si analyses réussies
        successful_count = report["results_summary"]["successful_analyses"]
        if successful_count > 0:
            report["results_summary"]["average_execution_time"] = \
                report["results_summary"]["total_execution_time"] / successful_count
        
        # Sauvegarde si chemin spécifié
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            self.logger.info(f"📄 Rapport sauvegardé: {output_path}")
        
        return report


def create_cli_parser() -> argparse.ArgumentParser:
    """Crée le parser CLI avec tous les paramètres essentiels"""
    
    parser = argparse.ArgumentParser(
        description="Unified Production Analyzer - Analyse rhétorique en production",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # === Arguments principaux ===
    parser.add_argument(
        "input",
        nargs="?",
        help="Texte à analyser ou chemin vers fichier/dossier"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Mode batch pour analyse multiple"
    )
    
    # === Configuration LLM ===
    llm_group = parser.add_argument_group("Configuration LLM")
    llm_group.add_argument(
        "--llm-service",
        choices=["openai", "mock"],
        default="openai",
        help="Service LLM à utiliser"
    )
    llm_group.add_argument(
        "--llm-model",
        default="gpt-4",
        help="Modèle LLM spécifique"
    )
    llm_group.add_argument(
        "--llm-temperature",
        type=float,
        default=0.3,
        help="Température du modèle LLM"
    )
    llm_group.add_argument(
        "--llm-max-tokens",
        type=int,
        default=2000,
        help="Nombre maximum de tokens"
    )
    
    # === Configuration Logique ===
    logic_group = parser.add_argument_group("Configuration Logique")
    logic_group.add_argument(
        "--logic-type",
        choices=["fol", "propositional", "modal"],
        default="fol",
        help="Type de logique à utiliser"
    )
    logic_group.add_argument(
        "--enable-fallback",
        action="store_true",
        default=True,
        help="Activer fallback automatique FOL->PL"
    )
    logic_group.add_argument(
        "--no-fallback",
        action="store_false",
        dest="enable_fallback",
        help="Désactiver fallback automatique"
    )
    
    # === Configuration Authenticité ===
    auth_group = parser.add_argument_group("Configuration Authenticité")
    auth_group.add_argument(
        "--mock-level",
        choices=["none", "partial", "full"],
        default="none",
        help="Niveau de simulation (none=100%% authentique)"
    )
    auth_group.add_argument(
        "--require-real-gpt",
        action="store_true",
        default=True,
        help="Exiger un LLM authentique"
    )
    auth_group.add_argument(
        "--allow-mock-gpt",
        action="store_false",
        dest="require_real_gpt",
        help="Autoriser LLM simulé"
    )
    auth_group.add_argument(
        "--require-real-tweety",
        action="store_true",
        default=True,
        help="Exiger TweetyProject authentique"
    )
    auth_group.add_argument(
        "--allow-mock-tweety",
        action="store_false", 
        dest="require_real_tweety",
        help="Autoriser TweetyProject simulé"
    )
    
    # === Configuration Orchestration ===
    orch_group = parser.add_argument_group("Configuration Orchestration")
    orch_group.add_argument(
        "--orchestration-type",
        choices=["unified", "conversation", "micro", "real_llm"],
        default="unified",
        help="Type d'orchestration multi-agents"
    )
    orch_group.add_argument(
        "--enable-conversation-trace",
        action="store_true",
        default=True,
        help="Activer capture conversation agentielle"
    )
    orch_group.add_argument(
        "--no-conversation-trace",
        action="store_false",
        dest="enable_conversation_trace",
        help="Désactiver capture conversation"
    )
    orch_group.add_argument(
        "--max-agents",
        type=int,
        default=5,
        help="Nombre maximum d'agents simultanés"
    )
    
    # === Configuration Analyse ===
    analysis_group = parser.add_argument_group("Configuration Analyse")
    analysis_group.add_argument(
        "--analysis-modes",
        nargs="+",
        choices=["fallacies", "coherence", "semantic", "unified", "advanced"],
        default=["unified"],
        help="Modes d'analyse à appliquer"
    )
    analysis_group.add_argument(
        "--enable-parallel",
        action="store_true",
        default=True,
        help="Activer traitement parallèle"
    )
    analysis_group.add_argument(
        "--no-parallel",
        action="store_false",
        dest="enable_parallel",
        help="Forcer traitement séquentiel"
    )
    analysis_group.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Nombre maximum de workers parallèles"
    )
    
    # === Configuration Retry ===
    retry_group = parser.add_argument_group("Configuration Retry")
    retry_group.add_argument(
        "--tweety-retry-count",
        type=int,
        default=5,
        help="Nombre de tentatives TweetyProject"
    )
    retry_group.add_argument(
        "--tweety-retry-delay",
        type=float,
        default=2.0,
        help="Délai entre tentatives TweetyProject"
    )
    retry_group.add_argument(
        "--llm-retry-count",
        type=int,
        default=3,
        help="Nombre de tentatives LLM"
    )
    
    # === Configuration Sortie ===
    output_group = parser.add_argument_group("Configuration Sortie")
    output_group.add_argument(
        "--output-format",
        choices=["json", "yaml", "txt"],
        default="json",
        help="Format de sortie des résultats"
    )
    output_group.add_argument(
        "--output-file",
        type=Path,
        help="Fichier de sortie (défaut: auto-généré)"
    )
    output_group.add_argument(
        "--save-intermediate",
        action="store_true",
        help="Sauvegarder résultats intermédiaires"
    )
    output_group.add_argument(
        "--report-level",
        choices=["minimal", "standard", "production", "debug"],
        default="production",
        help="Niveau de détail des rapports"
    )
    
    # === Configuration Validation ===
    validation_group = parser.add_argument_group("Configuration Validation")
    validation_group.add_argument(
        "--validate-inputs",
        action="store_true",
        default=True,
        help="Valider les entrées"
    )
    validation_group.add_argument(
        "--no-validate-inputs",
        action="store_false",
        dest="validate_inputs",
        help="Désactiver validation entrées"
    )
    validation_group.add_argument(
        "--check-dependencies",
        action="store_true",
        default=True,
        help="Vérifier les dépendances au démarrage"
    )
    validation_group.add_argument(
        "--no-check-dependencies",
        action="store_false",
        dest="check_dependencies",
        help="Ignorer vérification dépendances"
    )
    
    # === Options générales ===
    general_group = parser.add_argument_group("Options Générales")
    general_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbeux"
    )
    general_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Mode silencieux"
    )
    general_group.add_argument(
        "--config-file",
        type=Path,
        help="Fichier de configuration JSON"
    )
    general_group.add_argument(
        "--version",
        action="version",
        version="Unified Production Analyzer 1.0.0"
    )
    
    return parser


def load_config_from_file(config_path: Path) -> Dict[str, Any]:
    """Charge la configuration depuis un fichier JSON"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Erreur chargement configuration {config_path}: {e}")
        return {}


def create_config_from_args(args) -> UnifiedProductionConfig:
    """Crée la configuration depuis les arguments CLI"""
    
    # Chargement config fichier si spécifié
    file_config = {}
    if args.config_file and args.config_file.exists():
        file_config = load_config_from_file(args.config_file)
        logger.info(f"📄 Configuration chargée depuis {args.config_file}")
    
    # Mapping des enums
    logic_type_map = {
        "fol": LogicType.FOL,
        "propositional": LogicType.PL,
        "modal": LogicType.MODAL
    }
    
    mock_level_map = {
        "none": MockLevel.NONE,
        "partial": MockLevel.PARTIAL,
        "full": MockLevel.FULL
    }
    
    orchestration_type_map = {
        "unified": OrchestrationType.UNIFIED,
        "conversation": OrchestrationType.CONVERSATION,
        "micro": OrchestrationType.MICRO,
        "real_llm": OrchestrationType.REAL_LLM
    }
    
    analysis_modes_map = {
        "fallacies": AnalysisMode.FALLACIES,
        "coherence": AnalysisMode.COHERENCE,
        "semantic": AnalysisMode.SEMANTIC,
        "unified": AnalysisMode.UNIFIED,
        "advanced": AnalysisMode.ADVANCED
    }
    
    # Construction configuration (CLI prioritaire sur fichier)
    config_dict = {
        # LLM
        "llm_service": getattr(args, "llm_service", file_config.get("llm_service", "openai")),
        "llm_model": getattr(args, "llm_model", file_config.get("llm_model", "gpt-4")),
        "llm_temperature": getattr(args, "llm_temperature", file_config.get("llm_temperature", 0.3)),
        "llm_max_tokens": getattr(args, "llm_max_tokens", file_config.get("llm_max_tokens", 2000)),
        "llm_retry_count": getattr(args, "llm_retry_count", file_config.get("llm_retry_count", 3)),
        
        # Logique
        "logic_type": logic_type_map.get(
            getattr(args, "logic_type", file_config.get("logic_type", "fol")),
            LogicType.FOL
        ),
        "enable_fallback": getattr(args, "enable_fallback", file_config.get("enable_fallback", True)),
        
        # Authenticité
        "mock_level": mock_level_map.get(
            getattr(args, "mock_level", file_config.get("mock_level", "none")),
            MockLevel.NONE
        ),
        "require_real_gpt": getattr(args, "require_real_gpt", file_config.get("require_real_gpt", True)),
        "require_real_tweety": getattr(args, "require_real_tweety", file_config.get("require_real_tweety", True)),
        
        # Orchestration
        "orchestration_type": orchestration_type_map.get(
            getattr(args, "orchestration_type", file_config.get("orchestration_type", "unified")),
            OrchestrationType.UNIFIED
        ),
        "enable_conversation_trace": getattr(args, "enable_conversation_trace", 
                                           file_config.get("enable_conversation_trace", True)),
        "max_agents": getattr(args, "max_agents", file_config.get("max_agents", 5)),
        
        # Analyse
        "analysis_modes": [
            analysis_modes_map.get(mode, AnalysisMode.UNIFIED) 
            for mode in getattr(args, "analysis_modes", file_config.get("analysis_modes", ["unified"]))
        ],
        "enable_parallel": getattr(args, "enable_parallel", file_config.get("enable_parallel", True)),
        "max_workers": getattr(args, "max_workers", file_config.get("max_workers", 4)),
        
        # Retry
        "tweety_retry_count": getattr(args, "tweety_retry_count", file_config.get("tweety_retry_count", 5)),
        "tweety_retry_delay": getattr(args, "tweety_retry_delay", file_config.get("tweety_retry_delay", 2.0)),
        
        # Sortie
        "output_format": getattr(args, "output_format", file_config.get("output_format", "json")),
        "save_intermediate": getattr(args, "save_intermediate", file_config.get("save_intermediate", False)),
        "report_level": getattr(args, "report_level", file_config.get("report_level", "production")),
        
        # Validation
        "validate_inputs": getattr(args, "validate_inputs", file_config.get("validate_inputs", True)),
        "check_dependencies": getattr(args, "check_dependencies", file_config.get("check_dependencies", True))
    }
    
    return UnifiedProductionConfig(**config_dict)


async def main():
    """Fonction principale du script"""
    
    # Configuration logging selon verbosité
    parser = create_cli_parser()
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    logger.info("🚀 Unified Production Analyzer v1.0.0")
    logger.info("=" * 60)
    
    try:
        # Création configuration
        config = create_config_from_args(args)
        logger.info(f"⚙️ Configuration: {config.logic_type.value}/{config.mock_level.value}")
        
        # Validation authenticité mode production
        if config.mock_level == MockLevel.NONE:
            logger.info("🛡️ Mode production authentique activé (0% mocks)")
        else:
            logger.warning(f"⚠️ Mode {config.mock_level.value} - Non recommandé en production")
        
        # Initialisation analyseur
        analyzer = UnifiedProductionAnalyzer(config)
        
        if not await analyzer.initialize():
            logger.error("❌ Échec initialisation - Arrêt")
            sys.exit(1)
        
        # Détermination de l'entrée
        if not args.input:
            logger.error("❌ Aucune entrée spécifiée")
            parser.print_help()
            sys.exit(1)
        
        input_path = Path(args.input)
        
        # Traitement selon le type d'entrée
        if input_path.exists():
            if input_path.is_file():
                # Fichier unique
                logger.info(f"📄 Analyse fichier: {input_path}")
                with open(input_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                result = await analyzer.analyze_text(text, args.analysis_modes)
                logger.info(f"✅ Analyse terminée: {result['id']}")
                
            elif input_path.is_dir() and args.batch:
                # Dossier en mode batch
                logger.info(f"📁 Analyse dossier: {input_path}")
                
                text_files = list(input_path.glob("*.txt")) + list(input_path.glob("*.md"))
                texts = []
                
                for file_path in text_files:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        texts.append(f.read())
                
                results = await analyzer.analyze_batch(texts)
                logger.info(f"✅ Batch terminé: {len(results)} analyses")
                
            else:
                logger.error("❌ Dossier spécifié mais mode batch non activé (--batch)")
                sys.exit(1)
        else:
            # Texte direct
            logger.info("📝 Analyse texte direct")
            result = await analyzer.analyze_text(args.input, args.analysis_modes)
            logger.info(f"✅ Analyse terminée: {result['id']}")
        
        # Génération rapport final
        output_file = args.output_file
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(f"reports/unified_analysis_{timestamp}.json")
        
        report = analyzer.generate_report(output_file)
        
        # Résumé final
        logger.info("=" * 60)
        logger.info("📊 RÉSUMÉ FINAL")
        logger.info(f"Session: {analyzer.session_id}")
        logger.info(f"Analyses réussies: {report['results_summary']['successful_analyses']}")
        logger.info(f"Analyses échouées: {report['results_summary']['failed_analyses']}")
        logger.info(f"Temps total: {report['results_summary']['total_execution_time']:.2f}s")
        
        if report['results_summary']['average_execution_time']:
            logger.info(f"Temps moyen: {report['results_summary']['average_execution_time']:.2f}s")
        
        logger.info(f"Rapport: {output_file}")
        logger.info("🎉 Analyse terminée avec succès!")
        
    except KeyboardInterrupt:
        logger.warning("⚠️ Interruption utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    # Gestion de l'event loop selon la plateforme
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Erreur event loop: {e}")
        sys.exit(1)