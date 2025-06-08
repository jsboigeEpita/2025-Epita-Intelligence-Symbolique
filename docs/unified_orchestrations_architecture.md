# Architecture des Orchestrations Unifiées

## Vue d'ensemble

L'architecture des orchestrations unifiées constitue le cœur de coordination du système d'analyse argumentative. Elle intègre plusieurs orchestrateurs spécialisés qui travaillent ensemble pour fournir une analyse complète et robuste.

## Composants Principaux

### 1. ConversationOrchestrator

Le `ConversationOrchestrator` gère les conversations multi-agents avec traçage détaillé des interactions.

#### Caractéristiques
- **Modes d'opération** : micro, demo, trace, enhanced
- **Gestion d'état** : Synchronisation entre agents
- **Logging conversationnel** : Traces élégantes au format markdown
- **Agents simulés** : Coordination d'agents simulés pour tests rapides

#### Architecture
```
ConversationOrchestrator
├── ConversationLogger (formatage traces)
├── AnalysisState (état partagé)
├── Agents[] (agents configurés selon le mode)
└── Configuration (mode et paramètres)
```

#### Utilisation
```python
from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator

# Orchestrateur pour mode démo
orchestrator = ConversationOrchestrator(mode="demo")
result = orchestrator.run_orchestration("Texte à analyser")
```

### 2. RealLLMOrchestrator

Le `RealLLMOrchestrator` orchestre avec GPT-4o-mini authentique et feedback BNF intelligent.

#### Caractéristiques
- **LLM authentique** : Intégration avec OpenAI GPT-4o-mini
- **Feedback BNF** : Utilisation de `TweetyErrorAnalyzer` pour corrections
- **Retry intelligent** : Amélioration progressive entre tentatives
- **Semantic Kernel** : Traces détaillées SK

#### Architecture
```
RealLLMOrchestrator
├── LLM Service (OpenAI/Azure)
├── TweetyErrorAnalyzer (feedback BNF)
├── Semantic Kernel (orchestration SK)
├── RealConversationLogger (logging avancé)
└── RhetoricalAnalysisState (état rhétorique)
```

#### Utilisation
```python
from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator

# Orchestrateur LLM réel
orchestrator = RealLLMOrchestrator(mode="real")
await orchestrator.initialize()
result = await orchestrator.run_real_llm_orchestration("Texte à analyser")
```

### 3. Pipeline d'Intégration Unifié

Le pipeline unifié coordonne l'ensemble du système avec configuration dynamique.

#### Flux de traitement
1. **Configuration** → `UnifiedConfig` détermine les paramètres
2. **Sélection d'orchestrateur** → Selon le type d'orchestration
3. **Initialisation** → Setup des agents et services
4. **Exécution** → Orchestration selon le mode
5. **Feedback** → Analyse des erreurs et corrections
6. **Reporting** → Génération des rapports et traces

## Coordination Multi-Agents

### Workflow de Conversation

```
InformalAgent → FormalizeAgent → FOLLogicAgent → SynthesisAgent → ReportGenerator
     ↓              ↓               ↓              ↓              ↓
   Analyse      Formalisation   Logique FOL    Synthèse     Rapport final
  informelle    du discours     et validation  des résultats
```

### Gestion d'État Partagé

L'état partagé maintient la cohérence entre agents :

```python
class AnalysisState:
    def __init__(self):
        self.current_text = ""
        self.informal_analysis = None
        self.formal_analysis = None
        self.logic_analysis = None
        self.synthesis_result = None
        self.agents_active = 0
        self.conversation_trace = []
```

### Communication Inter-Agents

- **Messages structurés** : Format standardisé pour échanges
- **Validation des données** : Vérification cohérence des échanges
- **Timeouts et retry** : Gestion des échecs de communication
- **Logging et traçabilité** : Enregistrement de toutes les interactions

## Orchestration Authentique

### Configuration Authentique

```python
config = UnifiedConfig(
    logic_type='FOL',
    mock_level='NONE',              # Aucun mock
    orchestration_type='REAL_LLM',  # LLM authentique
    require_real_gpt=True,          # GPT-4o-mini requis
    require_real_tweety=True        # TweetyProject requis
)
```

### Feedback BNF Intelligent

Le système intègre `TweetyErrorAnalyzer` pour un feedback constructif :

```python
# Analyse d'erreur Tweety
error_text = "Predicate 'unknown_pred' has not been declared"
feedback = analyzer.analyze_error(error_text)

# Feedback structuré
{
    "error_type": "DECLARATION_ERROR",
    "corrections": ["Déclarer le prédicat", "Utiliser un prédicat existant"],
    "bnf_rules": ["predicate ::= identifier '(' args ')'"],
    "confidence": 0.95,
    "example_fix": "unknown_pred(X) :- known_pred(X)."
}
```

### Retry et Amélioration

Le système améliore progressivement ses réponses :

1. **Première tentative** → Analyse initiale
2. **Détection d'erreur** → TweetyErrorAnalyzer identifie le problème
3. **Feedback BNF** → Génération de corrections spécifiques
4. **Deuxième tentative** → Analyse améliorée avec feedback
5. **Validation** → Vérification de la correction

## Performance et Monitoring

### Métriques de Performance

- **Latence orchestration** : < 5s overhead coordination
- **Throughput agents** : > 10 analyses/minute
- **Efficacité mémoire** : Réutilisation des ressources
- **Scalabilité** : Support charge croissante

### Observabilité

```python
# Métriques collectées automatiquement
{
    "orchestration_time": 4.2,
    "agents_used": ["InformalAgent", "FOLAgent", "SynthesisAgent"],
    "llm_calls": 3,
    "tokens_used": 1250,
    "errors_handled": 1,
    "retry_count": 1,
    "success_rate": 1.0
}
```

### Logging Structuré

- **Logs hiérarchiques** : Orchestrateur → Agents → Services
- **Traces conversationnelles** : Format markdown élégant
- **Métriques temps réel** : Monitoring continu
- **Alerting proactif** : Détection anomalies

## Gestion d'Erreurs Orchestrées

### Propagation d'Erreurs

```
Agent Error → Agent Handler → Orchestrator Handler → Global Handler
     ↓              ↓               ↓                     ↓
  Local retry  → Agent restart  → Orchestrator      → System
               recovery        fallback           recovery
```

### Recovery Coordonnée

1. **Détection** → Erreur identifiée à n'importe quel niveau
2. **Classification** → Type d'erreur et gravité
3. **Strategy** → Sélection de la stratégie de récupération
4. **Recovery** → Exécution de la récupération
5. **Validation** → Vérification du succès
6. **Learning** → Mise à jour des patterns d'erreur

### Modes de Fonctionnement Dégradé

- **Mode minimal** → Agents essentiels uniquement
- **Mode fallback** → Utilisation de mocks temporaires
- **Mode diagnostic** → Logging détaillé pour débogage
- **Mode healing** → Auto-réparation progressive

## Intégration avec Composants Validés

### TweetyErrorAnalyzer

```python
# Intégration dans l'orchestrateur
orchestrator = RealLLMOrchestrator(config)
result = orchestrator.run_with_bnf_feedback(text)
assert "BNF feedback" in result.metadata
```

### UnifiedConfig

```python
# Configuration respectée par orchestrateur
config = UnifiedConfig(logic_type='FOL', mock_level='NONE')
orchestrator = OrchestrationFactory.create(config)
assert orchestrator.is_authentic_mode()
```

### FirstOrderLogicAgent

```python
# Agent FOL coordonné par orchestrateur
orchestrator = ConversationOrchestrator(config)
agents = orchestrator.get_available_agents()
assert any(isinstance(a, FirstOrderLogicAgent) for a in agents)
```

## Patterns d'Architecture

### Factory Pattern

```python
class OrchestrationFactory:
    @staticmethod
    def create(config: UnifiedConfig):
        if config.orchestration_type == 'CONVERSATION':
            return ConversationOrchestrator(config=config)
        elif config.orchestration_type == 'REAL_LLM':
            return RealLLMOrchestrator(config=config)
        elif config.orchestration_type == 'UNIFIED':
            return UnifiedOrchestrator(config=config)
```

### Observer Pattern

```python
class OrchestrationObserver:
    def on_agent_start(self, agent_name: str): pass
    def on_agent_complete(self, agent_name: str, result: Any): pass
    def on_error(self, error: Exception): pass
    def on_orchestration_complete(self, final_result: Any): pass
```

### State Pattern

```python
class OrchestrationState:
    def handle_request(self, context: OrchestrationContext): pass

class InitializingState(OrchestrationState): pass
class RunningState(OrchestrationState): pass
class ErrorState(OrchestrationState): pass
class CompletedState(OrchestrationState): pass
```

## Sécurité et Authenticity

### Validation d'Authenticité

- **Vérification composants** → Tous les services réels disponibles
- **Validation configuration** → Cohérence des paramètres
- **Contrôle d'accès** → Permissions appropriées
- **Audit trail** → Traçabilité complète des opérations

### Gestion des Secrets

```python
# Configuration sécurisée
config = UnifiedConfig(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    azure_endpoint=os.getenv('AZURE_ENDPOINT'),
    auth_mode='secure'
)
```

## Tests et Validation

### Stratégie de Tests

1. **Tests unitaires** → Chaque orchestrateur individuellement
2. **Tests d'intégration** → Coordination entre orchestrateurs
3. **Tests de performance** → Validation des métriques
4. **Tests de robustesse** → Gestion d'erreurs
5. **Tests bout-en-bout** → Pipeline complet

### Validation Continue

```bash
# Script de validation
python scripts/validate_unified_orchestrations.py

# Tests automatisés
pytest tests/unit/orchestration/test_unified_orchestrations.py
pytest tests/integration/test_unified_system_integration.py
```

## Déploiement et Monitoring

### Configuration de Production

```python
production_config = UnifiedConfig(
    logic_type='FOL',
    mock_level='NONE',
    orchestration_type='UNIFIED',
    require_real_gpt=True,
    require_real_tweety=True,
    performance_mode='optimized',
    monitoring_enabled=True,
    retry_attempts=3,
    timeout_seconds=30
)
```

### Monitoring en Production

- **Dashboards** → Grafana/Prometheus pour métriques
- **Logs centralisés** → ELK stack pour logs
- **Alerting** → PagerDuty/Slack pour incidents
- **Health checks** → Vérifications périodiques automatiques

## Roadmap et Évolutions

### Améliorations Prévues

1. **Orchestration parallèle** → Agents en parallèle pour performance
2. **Auto-scaling** → Adaptation dynamique à la charge
3. **ML-driven optimization** → Optimisation par apprentissage
4. **Caching intelligent** → Cache des résultats fréquents
5. **API REST** → Exposition via API pour intégrations

### Extensibilité

Le système est conçu pour être facilement extensible :

- **Nouveaux orchestrateurs** → Interface standardisée
- **Nouveaux agents** → Plugin architecture
- **Nouveaux services LLM** → Abstraction service layer
- **Nouvelles métriques** → Observer pattern extensible

---

## Conclusion

L'architecture des orchestrations unifiées fournit une base solide pour l'analyse argumentative avancée. Elle combine flexibilité, performance et robustesse tout en maintenant une séparation claire des responsabilités et une observabilité complète.

Le système est production-ready avec une couverture de tests complète, une gestion d'erreurs robuste, et des mécanismes de monitoring intégrés.