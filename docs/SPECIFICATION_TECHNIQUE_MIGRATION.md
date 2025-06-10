# 📋 Spécification Technique - Migration vers Pipeline Unifié Central

## 🎯 **Objectif**
Transformer les 3 scripts consolidés pour utiliser `unified_orchestration_pipeline.py` comme moteur central, en préservant leurs interfaces et fonctionnalités.

## 🔌 **API Pipeline Unifié - Points d'Entrée**

### **Fonction Principale**
```python
# Point d'entrée principal
async def run_unified_orchestration_pipeline(
    text: str, 
    config: ExtendedOrchestrationConfig
) -> Dict[str, Any]

# Alternative avec classe
pipeline = UnifiedOrchestrationPipeline(config)
result = await pipeline.analyze_text_extended(text)
```

### **Configuration Unifiée**
```python
class ExtendedOrchestrationConfig(UnifiedAnalysisConfig):
    def __init__(self,
        # === Configuration de base ===
        analysis_modes: List[str] = None,
        orchestration_mode: OrchestrationMode = OrchestrationMode.PIPELINE,
        logic_type: str = "fol",
        use_mocks: bool = False,
        use_advanced_tools: bool = True,
        output_format: str = "detailed",
        enable_conversation_logging: bool = True,
        
        # === Configuration orchestration étendue ===
        analysis_type: AnalysisType = AnalysisType.COMPREHENSIVE,
        enable_hierarchical: bool = True,
        enable_specialized_orchestrators: bool = True,
        enable_communication_middleware: bool = True,
        max_concurrent_analyses: int = 10,
        analysis_timeout: int = 300,
        auto_select_orchestrator: bool = True,
        hierarchical_coordination_level: str = "full",
        specialized_orchestrator_priority: List[str] = None,
        save_orchestration_trace: bool = True,
        middleware_config: Dict[str, Any] = None
    )
```

### **Enums Disponibles**
```python
class OrchestrationMode(Enum):
    # Modes de base
    PIPELINE = "pipeline"
    REAL = "real"
    CONVERSATION = "conversation"
    
    # Modes hiérarchiques
    HIERARCHICAL_FULL = "hierarchical_full"
    STRATEGIC_ONLY = "strategic_only"
    TACTICAL_COORDINATION = "tactical_coordination"
    OPERATIONAL_DIRECT = "operational_direct"
    
    # Modes spécialisés
    CLUEDO_INVESTIGATION = "cluedo_investigation"
    LOGIC_COMPLEX = "logic_complex"
    ADAPTIVE_HYBRID = "adaptive_hybrid"
    AUTO_SELECT = "auto_select"

class AnalysisType(Enum):
    COMPREHENSIVE = "comprehensive"
    RHETORICAL = "rhetorical"
    LOGICAL = "logical"
    INVESTIGATIVE = "investigative"
    FALLACY_FOCUSED = "fallacy_focused"
    ARGUMENT_STRUCTURE = "argument_structure"
    DEBATE_ANALYSIS = "debate_analysis"
    CUSTOM = "custom"
```

---

## 🔄 **Transformations Détaillées par Script**

### **1. unified_production_analyzer.py**

#### **AVANT - Méthodes actuelles**
```python
async def analyze_text(self, text: str, analysis_type: str = "rhetorical") -> Dict[str, Any]:
    # 50+ lignes de logique interne avec retry, fallback, etc.

async def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
    # Logique parallélisation manuelle avec semaphore
```

#### **APRÈS - Délégation au pipeline unifié**
```python
# Import unique
from argumentation_analysis.pipelines.unified_orchestration_pipeline import (
    run_unified_orchestration_pipeline,
    ExtendedOrchestrationConfig,
    OrchestrationMode,
    AnalysisType
)

class UnifiedProductionAnalyzer:
    def _map_orchestration_mode(self) -> OrchestrationMode:
        """Mappe orchestration_type CLI vers OrchestrationMode"""
        mapping = {
            "unified": OrchestrationMode.HIERARCHICAL_FULL,
            "conversation": OrchestrationMode.CONVERSATION,
            "micro": OrchestrationMode.OPERATIONAL_DIRECT,
            "real_llm": OrchestrationMode.REAL
        }
        return mapping.get(self.orchestration_type, OrchestrationMode.PIPELINE)
    
    def _map_analysis_type(self, analysis_type: str) -> AnalysisType:
        """Mappe analysis_mode CLI vers AnalysisType"""
        mapping = {
            "rhetorical": AnalysisType.RHETORICAL,
            "fallacies": AnalysisType.FALLACY_FOCUSED,
            "coherence": AnalysisType.ARGUMENT_STRUCTURE,
            "semantic": AnalysisType.COMPREHENSIVE,
            "unified": AnalysisType.COMPREHENSIVE,
            "advanced": AnalysisType.COMPREHENSIVE
        }
        return mapping.get(analysis_type, AnalysisType.COMPREHENSIVE)
    
    def _build_config(self, analysis_type: str = "rhetorical") -> ExtendedOrchestrationConfig:
        """Construit la configuration pour le pipeline unifié"""
        return ExtendedOrchestrationConfig(
            # Mapping des paramètres CLI
            orchestration_mode=self._map_orchestration_mode(),
            analysis_type=self._map_analysis_type(analysis_type),
            logic_type=self.logic_type.value if hasattr(self.logic_type, 'value') else self.logic_type,
            use_mocks=(self.mock_level != MockLevel.NONE),
            use_advanced_tools=self.enable_advanced_tools,
            output_format=self.output_format,
            enable_conversation_logging=self.enable_conversation_logging,
            
            # Configuration orchestration
            enable_hierarchical=True,
            enable_specialized_orchestrators=True,
            max_concurrent_analyses=self.max_workers,
            analysis_timeout=self.timeout_seconds,
            auto_select_orchestrator=True,
            save_orchestration_trace=self.save_trace
        )
    
    async def analyze_text(self, text: str, analysis_type: str = "rhetorical") -> Dict[str, Any]:
        """Version simplifiée utilisant le pipeline unifié"""
        config = self._build_config(analysis_type)
        return await run_unified_orchestration_pipeline(text, config)
    
    async def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Version batch utilisant le pipeline unifié"""
        config = self._build_config()
        config.max_concurrent_analyses = min(self.max_workers, len(texts))
        
        # Le pipeline unifié gère le parallélisme
        results = []
        for text in texts:
            try:
                result = await run_unified_orchestration_pipeline(text, config)
                results.append(result)
            except Exception as e:
                results.append({
                    "status": "error",
                    "error": str(e),
                    "text_preview": text[:100] + "..." if len(text) > 100 else text
                })
        
        return results
```

### **2. educational_showcase_system.py**

#### **AVANT - Multiple imports et orchestrateurs**
```python
from argumentation_analysis.pipelines.unified_text_analysis import UnifiedTextAnalysisPipeline
from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
# ... 12+ autres imports
```

#### **APRÈS - Configuration éducative unifiée**
```python
# Import simplifié
from argumentation_analysis.pipelines.unified_orchestration_pipeline import (
    run_unified_orchestration_pipeline,
    ExtendedOrchestrationConfig,
    OrchestrationMode,
    AnalysisType
)

class EducationalShowcaseSystem:
    def _build_educational_config(self, mode: str = "interactive") -> ExtendedOrchestrationConfig:
        """Configuration spécialisée pour l'éducation"""
        return ExtendedOrchestrationConfig(
            # Mode conversationnel pour l'éducation
            orchestration_mode=OrchestrationMode.CONVERSATION,
            analysis_type=AnalysisType.COMPREHENSIVE,
            
            # Fonctionnalités éducatives
            use_mocks=False,  # Toujours authentique en mode éducatif
            enable_conversation_logging=True,
            save_orchestration_trace=True,
            
            # Configuration orchestration éducative
            enable_hierarchical=True,
            enable_specialized_orchestrators=True,
            enable_communication_middleware=True,
            auto_select_orchestrator=True,
            hierarchical_coordination_level="full",
            specialized_orchestrator_priority=["conversation", "real_llm"],
            
            # Configuration middleware pour capture conversations
            middleware_config={
                "capture_agent_conversations": True,
                "detailed_logging": True,
                "educational_mode": True,
                "conversation_export_format": "markdown"
            }
        )
    
    async def run_educational_analysis(self, text: str, mode: str = "interactive") -> Dict[str, Any]:
        """Analyse éducative utilisant le pipeline unifié"""
        config = self._build_educational_config(mode)
        result = await run_unified_orchestration_pipeline(text, config)
        
        # Post-traitement éducatif
        if "orchestration_trace" in result:
            result["educational_insights"] = self._extract_educational_insights(result["orchestration_trace"])
        
        return result
    
    def _extract_educational_insights(self, trace: List[Dict]) -> Dict[str, Any]:
        """Extrait les insights pédagogiques de la trace d'orchestration"""
        return {
            "agents_involved": [step.get("agent", "unknown") for step in trace],
            "conversation_flow": self._build_conversation_flow(trace),
            "learning_points": self._identify_learning_points(trace),
            "complexity_metrics": self._calculate_complexity_metrics(trace)
        }
```

### **3. comprehensive_workflow_processor.py**

#### **AVANT - Workflow manuel complexe**
```python
# Imports multiples et workflow manuel
from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
# Configuration manuelle des étapes...
```

#### **APRÈS - Mode workflow unifié**
```python
# Import simplifié
from argumentation_analysis.pipelines.unified_orchestration_pipeline import (
    run_unified_orchestration_pipeline,
    ExtendedOrchestrationConfig,
    OrchestrationMode,
    AnalysisType
)

class ComprehensiveWorkflowProcessor:
    def _build_workflow_config(self, mode: WorkflowMode) -> ExtendedOrchestrationConfig:
        """Configuration pour workflow complet"""
        mode_mapping = {
            WorkflowMode.FULL: OrchestrationMode.HIERARCHICAL_FULL,
            WorkflowMode.ANALYSIS_ONLY: OrchestrationMode.OPERATIONAL_DIRECT,
            WorkflowMode.TESTING_ONLY: OrchestrationMode.TACTICAL_COORDINATION,
            WorkflowMode.VALIDATION_ONLY: OrchestrationMode.STRATEGIC_ONLY,
            WorkflowMode.PERFORMANCE: OrchestrationMode.ADAPTIVE_HYBRID,
            WorkflowMode.BATCH: OrchestrationMode.HIERARCHICAL_FULL
        }
        
        return ExtendedOrchestrationConfig(
            orchestration_mode=mode_mapping.get(mode, OrchestrationMode.HIERARCHICAL_FULL),
            analysis_type=AnalysisType.COMPREHENSIVE,
            
            # Configuration workflow
            use_mocks=False,
            use_advanced_tools=True,
            enable_conversation_logging=True,
            save_orchestration_trace=True,
            
            # Configuration orchestration pour workflow
            enable_hierarchical=True,
            enable_specialized_orchestrators=True,
            enable_communication_middleware=True,
            max_concurrent_analyses=self.max_workers,
            analysis_timeout=self.timeout_seconds,
            auto_select_orchestrator=True,
            hierarchical_coordination_level="full",
            
            # Configuration workflow spécialisée
            middleware_config={
                "workflow_mode": True,
                "batch_processing": (mode == WorkflowMode.BATCH),
                "performance_monitoring": True,
                "comprehensive_validation": True
            }
        )
    
    async def run_comprehensive_workflow(self, data: Dict[str, Any], mode: WorkflowMode) -> Dict[str, Any]:
        """Workflow complet utilisant le pipeline unifié"""
        config = self._build_workflow_config(mode)
        
        # Le pipeline unifié gère l'orchestration complète
        if isinstance(data, dict) and "corpus_data" in data:
            # Mode corpus
            results = []
            for item in data["corpus_data"]:
                text = item.get("content", str(item))
                result = await run_unified_orchestration_pipeline(text, config)
                result["source_info"] = item.get("source_info", "unknown")
                results.append(result)
            
            return {
                "workflow_mode": mode.value,
                "results": results,
                "summary": self._build_workflow_summary(results)
            }
        else:
            # Mode texte simple
            text = str(data)
            return await run_unified_orchestration_pipeline(text, config)
```

---

## 🧪 **Plan de Tests**

### **Tests de Non-Régression**
```python
# Test pour chaque script transformé
async def test_production_analyzer_migration():
    """Vérifie que l'interface CLI fonctionne toujours"""
    analyzer = UnifiedProductionAnalyzer()
    # Tester tous les paramètres CLI existants
    
async def test_educational_system_migration():
    """Vérifie que les fonctionnalités pédagogiques sont préservées"""
    system = EducationalShowcaseSystem()
    # Tester capture conversations, rapports markdown, etc.
    
async def test_workflow_processor_migration():
    """Vérifie que les workflows batch fonctionnent"""
    processor = ComprehensiveWorkflowProcessor()
    # Tester tous les modes de workflow
```

### **Tests de Performance**
```python
async def test_performance_comparison():
    """Compare performance avant/après migration"""
    # Mesurer temps d'exécution
    # Vérifier utilisation mémoire
    # Valider parallélisme
```

---

## 📅 **Plan d'Implémentation Détaillé**

### **Jour 1 : unified_production_analyzer.py**
**Matin (2-3h)** :
1. ✅ Ajouter import du pipeline unifié
2. ✅ Créer méthodes de mapping `_map_orchestration_mode()` et `_map_analysis_type()`
3. ✅ Créer `_build_config()` 
4. ✅ Remplacer `analyze_text()` par appel pipeline unifié

**Après-midi (2-3h)** :
5. ✅ Remplacer `analyze_batch()` par version pipeline unifié
6. ✅ Tests de non-régression CLI
7. ✅ Validation avec tous les paramètres existants

### **Jour 2 : educational_showcase_system.py**
**Matin (2-3h)** :
1. ✅ Simplifier les imports multiples
2. ✅ Créer `_build_educational_config()`
3. ✅ Transformer `run_educational_analysis()`

**Après-midi (2-3h)** :
4. ✅ Adapter extraction des insights pédagogiques
5. ✅ Tests des fonctionnalités conversationnelles
6. ✅ Validation génération rapports markdown

### **Jour 3 : comprehensive_workflow_processor.py**
**Matin (2-3h)** :
1. ✅ Créer `_build_workflow_config()` avec mapping modes
2. ✅ Transformer `run_comprehensive_workflow()`
3. ✅ Adapter gestion corpus et batch

**Après-midi (2-3h)** :
4. ✅ Tests workflow complets
5. ✅ Tests performance et parallélisme
6. ✅ Validation intégration complète

---

## ✅ **Critères de Réussite**

### **Fonctionnel**
- ✅ Interface utilisateur inchangée (CLI, arguments, outputs)
- ✅ Toutes les fonctionnalités existantes préservées
- ✅ Performance égale ou améliorée
- ✅ Tests de non-régression passent à 100%

### **Technique**
- ✅ Code simplifié et plus maintenable
- ✅ Réduction significative des imports
- ✅ Logique centralisée dans le pipeline unifié
- ✅ Traçabilité et logging améliorés

### **Architecture**
- ✅ Pipeline unifié devient le point central
- ✅ Scripts transformés en façades légères
- ✅ Réutilisation maximale des capacités d'orchestration
- ✅ Évolutivité pour futures fonctionnalités