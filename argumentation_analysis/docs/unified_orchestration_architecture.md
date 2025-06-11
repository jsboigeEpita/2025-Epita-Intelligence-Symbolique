# Architecture d'Orchestration Unifiée - Documentation Complète

## Vue d'ensemble

Le pipeline d'orchestration unifié (`unified_orchestration_pipeline.py`) étend les capacités du `unified_text_analysis.py` original en intégrant l'architecture hiérarchique complète à 3 niveaux et les orchestrateurs spécialisés disponibles dans le projet.

## Architecture Hiérarchique

### Niveau Stratégique
- **Gestionnaire Stratégique** (`StrategicManager`)
- Définition des objectifs globaux d'analyse
- Planification stratégique et allocation de ressources
- Interface avec l'utilisateur et supervision générale

### Niveau Tactique  
- **Coordinateur de Tâches** (`TaskCoordinator`)
- Décomposition des objectifs stratégiques en tâches concrètes
- Coordination entre les niveaux stratégique et opérationnel
- Établissement des dépendances entre tâches

### Niveau Opérationnel
- **Gestionnaire Opérationnel** (`OperationalManager`)
- Exécution concrète des tâches d'analyse
- Interface avec les agents d'analyse spécialisés
- Collecte et rapport des résultats

## Orchestrateurs Spécialisés

### CluedoOrchestrator
- **Type d'analyse** : Investigative, Debate Analysis
- **Fonctionnalité** : Analyse de type enquête avec hypothèses et déductions
- **Usage** : Textes complexes nécessitant une approche investigative

### ConversationOrchestrator
- **Type d'analyse** : Rhetorical, Comprehensive
- **Fonctionnalité** : Orchestration conversationnelle entre agents
- **Usage** : Analyses collaboratives et discussions argumentatives

### RealLLMOrchestrator
- **Type d'analyse** : Fallacy Focused, Argument Structure
- **Fonctionnalité** : Orchestration avec LLM réels pour analyses sophistiquées
- **Usage** : Détection fine de sophismes et analyse structurelle

### LogiqueComplexeOrchestrator
- **Type d'analyse** : Logical, Comprehensive
- **Fonctionnalité** : Analyse logique formelle avancée
- **Usage** : Vérification de cohérence et raisonnement logique

## Modes d'Orchestration

### Modes de Base (Compatibilité)
- `PIPELINE` : Mode pipeline classique
- `REAL` : Orchestration LLM réelle
- `CONVERSATION` : Mode conversationnel

### Modes Hiérarchiques
- `HIERARCHICAL_FULL` : Architecture hiérarchique complète
- `STRATEGIC_ONLY` : Niveau stratégique uniquement
- `TACTICAL_COORDINATION` : Coordination tactique
- `OPERATIONAL_DIRECT` : Exécution directe opérationnelle

### Modes Spécialisés
- `CLUEDO_INVESTIGATION` : Investigation de type Cluedo
- `LOGIC_COMPLEX` : Logique complexe
- `ADAPTIVE_HYBRID` : Mode hybride adaptatif

### Mode Automatique
- `AUTO_SELECT` : Sélection automatique selon le contexte

## Types d'Analyse Supportés

| Type | Description | Orchestrateurs Recommandés |
|------|-------------|---------------------------|
| `COMPREHENSIVE` | Analyse complète multi-facettes | Hierarchical, Hybrid |
| `RHETORICAL` | Analyse rhétorique et stylistique | Conversation, Real LLM |
| `LOGICAL` | Analyse logique formelle | Logic Complex, Hierarchical |
| `INVESTIGATIVE` | Analyse investigative type enquête | Cluedo, Hierarchical |
| `FALLACY_FOCUSED` | Détection ciblée de sophismes | Real LLM, Conversation |
| `ARGUMENT_STRUCTURE` | Structure des arguments | Real LLM, Logic Complex |
| `DEBATE_ANALYSIS` | Analyse de débat | Cluedo, Conversation |
| `CUSTOM` | Analyse personnalisée | Auto Select |

## Utilisation

### Configuration Simple

```python
from argumentation_analysis.pipelines.unified_orchestration_pipeline import (
    run_unified_orchestration_pipeline,
    ExtendedOrchestrationConfig,
    OrchestrationMode,
    AnalysisType
)

# Configuration automatique (recommandée)
results = await run_unified_orchestration_pipeline(
    text="Votre texte à analyser",
    config=None  # Configuration par défaut avec sélection automatique
)
```

### Configuration Avancée

```python
# Configuration personnalisée
config = ExtendedOrchestrationConfig(
    analysis_modes=["informal", "formal", "unified"],
    orchestration_mode=OrchestrationMode.HIERARCHICAL_FULL,
    analysis_type=AnalysisType.COMPREHENSIVE,
    enable_hierarchical=True,
    enable_specialized_orchestrators=True,
    auto_select_orchestrator=True,
    save_orchestration_trace=True
)

results = await run_unified_orchestration_pipeline(text, config)
```

### API de Compatibilité

```python
from argumentation_analysis.pipelines.unified_orchestration_pipeline import run_extended_unified_analysis

# Interface compatible avec l'API existante
results = await run_extended_unified_analysis(
    text="Votre texte",
    mode="comprehensive",  # ou "rhetorical", "logical", etc.
    orchestration_mode="auto_select"  # ou "hierarchical", "specialized", etc.
)
```

## Structure des Résultats

```python
{
    "metadata": {
        "analysis_id": "analysis_1234567890",
        "analysis_timestamp": "2025-06-10T03:40:00Z",
        "pipeline_version": "unified_orchestration_2.0",
        "orchestration_mode": "hierarchical_full",
        "analysis_type": "comprehensive",
        "text_length": 1500,
        "source_info": "Document analysé"
    },
    
    # Résultats de l'orchestration hiérarchique
    "strategic_analysis": {
        "objectives": [...],
        "strategic_plan": {...}
    },
    "tactical_coordination": {
        "tasks_created": 8,
        "tasks_by_objective": {...}
    },
    "operational_results": {
        "tasks_executed": 8,
        "task_results": [...],
        "summary": {...}
    },
    
    # Résultats de l'orchestration spécialisée
    "specialized_orchestration": {
        "orchestrator_used": "conversation",
        "orchestrator_priority": 2,
        "results": {...}
    },
    
    # Résultats du service manager
    "service_manager_results": {...},
    
    # Résultats de base (compatibilité)
    "informal_analysis": {...},
    "formal_analysis": {...},
    "unified_analysis": {...},
    "orchestration_analysis": {...},
    
    # Métadonnées d'orchestration
    "orchestration_trace": [...],
    "communication_log": [...],
    "hierarchical_coordination": {
        "coordination_effectiveness": 0.85,
        "strategic_alignment": 0.90,
        "tactical_efficiency": 0.80,
        "operational_success": 0.85,
        "overall_score": 0.85
    },
    
    "recommendations": [...],
    "execution_time": 5.2,
    "status": "success"
}
```

## Fonctionnalités Avancées

### Trace d'Orchestration

Le système enregistre automatiquement une trace détaillée de toutes les opérations d'orchestration :

```python
# Activer la trace (activée par défaut)
config = ExtendedOrchestrationConfig(save_orchestration_trace=True)

# La trace est sauvegardée dans RESULTS_DIR/orchestration_trace_{analysis_id}.json
```

### Middleware de Communication

Le système utilise un middleware de communication pour coordonner les échanges entre niveaux :

```python
# Configuration du middleware
config = ExtendedOrchestrationConfig(
    enable_communication_middleware=True,
    middleware_config={
        "max_message_history": 1000,
        "enable_logging": True
    }
)
```

### Comparaison d'Approches

```python
from argumentation_analysis.pipelines.unified_orchestration_pipeline import compare_orchestration_approaches

# Comparer différentes approches d'orchestration
comparison = await compare_orchestration_approaches(
    text="Votre texte",
    approaches=["pipeline", "hierarchical", "specialized", "hybrid"]
)

print(f"Approche la plus rapide: {comparison['comparison']['fastest']}")
print(f"Approche la plus complète: {comparison['comparison']['most_comprehensive']}")
```

## Service Manager Centralisé

Le `OrchestrationServiceManager` coordonne tous les services d'orchestration :

- Gestion unifiée des gestionnaires hiérarchiques
- Coordination des orchestrateurs spécialisés
- Interface avec les agents d'analyse
- Monitoring et logging centralisé

```python
# Utilisation directe du service manager
from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager

service_manager = OrchestrationServiceManager()
await service_manager.initialize()

results = await service_manager.analyze_text(
    text="Votre texte",
    analysis_type="comprehensive"
)
```

## Migration depuis l'API Existante

### Remplacement Direct

```python
# Ancien code
from argumentation_analysis.pipelines.unified_text_analysis import run_unified_text_analysis_pipeline
results = await run_unified_text_analysis_pipeline(text)

# Nouveau code (compatible)
from argumentation_analysis.pipelines.unified_orchestration_pipeline import run_extended_unified_analysis
results = await run_extended_unified_analysis(text)
```

### Utilisation des Nouvelles Fonctionnalités

```python
# Ancien code avec configuration manuelle
config = UnifiedAnalysisConfig(analysis_modes=["informal", "formal"])
results = await run_unified_text_analysis_pipeline(text, config)

# Nouveau code avec orchestration hiérarchique
config = ExtendedOrchestrationConfig(
    analysis_modes=["informal", "formal", "unified"],
    orchestration_mode=OrchestrationMode.HIERARCHICAL_FULL,
    enable_hierarchical=True
)
results = await run_unified_orchestration_pipeline(text, config)
```

## Performance et Optimisation

### Sélection Automatique d'Orchestrateur

Le système analyse automatiquement les caractéristiques du texte pour sélectionner l'orchestrateur optimal :

- Longueur du texte
- Complexité argumentative
- Présence de marqueurs logiques
- Type d'analyse demandé

### Gestion des Ressources

```python
config = ExtendedOrchestrationConfig(
    max_concurrent_analyses=5,  # Limite les analyses simultanées
    analysis_timeout=300,       # Timeout en secondes
    auto_cleanup=True          # Nettoyage automatique
)
```

### Mode Mock pour les Tests

```python
config = ExtendedOrchestrationConfig(
    use_mocks=True,  # Utilise des mocks pour les tests
    enable_hierarchical=True,
    enable_specialized_orchestrators=False  # Désactive pour simplifier les tests
)
```

## Débogage et Monitoring

### Logs Détaillés

Le système fournit des logs détaillés à chaque niveau :

```python
import logging
logging.basicConfig(level=logging.INFO)

# Les logs incluent :
# [INIT] Initialisation des composants
# [HIERARCHICAL] Opérations hiérarchiques  
# [SPECIALIZED] Orchestration spécialisée
# [SERVICE_MANAGER] Service manager
# [TRACE] Trace d'orchestration
```

### Analyse des Traces

```python
# Charger et analyser une trace sauvegardée
import json
with open("results/orchestration_trace_analysis_123.json") as f:
    trace = json.load(f)

for event in trace["trace"]:
    print(f"{event['timestamp']}: {event['event_type']}")
```

## Exemples d'Usage

Voir le fichier `examples/run_orchestration_pipeline_demo.py` pour des exemples complets d'utilisation des différents modes d'orchestration.

## Dépendances

Le pipeline d'orchestration unifié nécessite :

- Tous les composants du `unified_text_analysis.py` original
- Architecture hiérarchique (`orchestration/hierarchical/`)
- Orchestrateurs spécialisés (`orchestration/`)
- Service manager (`orchestration/service_manager.py`)
- Système de communication (`core/communication.py`)

Les dépendances manquantes sont gérées gracieusement avec des fallbacks appropriés.