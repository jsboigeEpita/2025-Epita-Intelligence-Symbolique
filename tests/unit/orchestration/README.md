# Tests d'Orchestration Unifié

## Vue d'ensemble

Cette suite de tests valide le fonctionnement complet du système d'orchestration unifié qui intègre l'architecture hiérarchique et les orchestrateurs spécialisés dans le pipeline d'analyse argumentative.

## Structure des Tests

### Tests Unitaires (`tests/unit/orchestration/`)

#### 1. `test_la classe `UnifiedPipeline` du module `argumentation_analysis/pipelines/unified_pipeline.py`` (676 lignes)
**Pipeline d'orchestration principal**

- **TestExtendedOrchestrationConfig** : Configuration étendue
  - Configuration par défaut et personnalisée
  - Conversion automatique des énumérations
  - Priorités d'orchestrateurs spécialisés
  - Configuration du middleware

- **TestUnifiedOrchestrationPipeline** : Pipeline unifié complet
  - Initialisation (basic, hiérarchique, spécialisée)
  - Analyse orchestrée avec validation
  - Sélection de stratégie d'orchestration
  - Analyse des caractéristiques du texte
  - Exécution hiérarchique et spécialisée
  - Système de trace et gestion d'erreurs

- **TestOrchestrationFunctions** : Fonctions publiques
  - `run_unified_orchestration_pipeline()`
  - `run_extended_unified_analysis()` (compatibilité)
  - `create_extended_config_from_params()`
  - `compare_orchestration_approaches()`

- **TestErrorHandlingAndEdgeCases** : Gestion d'erreurs et cas limites
  - Timeout d'analyse
  - Textes volumineux
  - Analyses concurrentes
  - Configurations invalides
  - Monitoring mémoire

- **TestPerformanceAndOptimization** : Performance
  - Benchmarks de performance
  - Optimisation des traces
  - Création de configuration rapide

#### 2. `test_hierarchical_managers.py` (941 lignes)
**Gestionnaires de l'architecture hiérarchique**

- **TestStrategicManager** : Niveau stratégique
  - Initialisation et configuration
  - Analyse comprehensive du contexte stratégique
  - Génération d'objectifs hiérarchiques
  - Création de plans avec dépendances
  - Monitoring et adaptation des plans

- **TestTaskCoordinator** : Niveau tactique
  - Traitement des objectifs stratégiques
  - Décomposition en tâches opérationnelles
  - Planification avec gestion des dépendances
  - Coordination d'exécution
  - Gestion des goulots d'étranglement

- **TestOperationalManager** : Niveau opérationnel
  - Exécution de tâches tactiques
  - Extraction de prémisses par NLP
  - Détection comprehensive de sophismes
  - Exécution parallèle optimisée
  - Monitoring et optimisation des ressources

- **TestHierarchicalIntegration** : Intégration inter-niveaux
  - Flux complet hiérarchique (strategic → tactical → operational)
  - Boucles de communication et feedback
  - Escalade d'erreurs dans la hiérarchie
  - Coordination des performances

#### 3. `test_specialized_orchestrators.py` (372 lignes)
**Orchestrateurs spécialisés**

- **TestCluedoOrchestrator** : Investigations
  - Orchestration d'analyse d'investigation
  - Identification systématique des preuves
  - Analyse de crédibilité des témoins
  - Raisonnement déductif

- **TestConversationOrchestrator** : Analyses conversationnelles
  - Orchestration d'analyse de dialogue
  - Structure de dialogue et tours de parole
  - Stratégies rhétoriques et évolution argumentative

- **TestRealLLMOrchestrator** : Orchestration LLM réelle
  - Coordination multi-agents LLM
  - Optimisation des prompts
  - Validation des réponses

- **TestLogiqueComplexeOrchestrator** : Logique complexe
  - Analyse logique complexe
  - Extraction de structures formelles
  - Raisonnement formel et vérification

- **TestSpecializedOrchestratorsIntegration** : Intégration spécialisée
  - Sélection automatique par contenu
  - Collaboration entre orchestrateurs

### Tests d'Intégration (`tests/integration/`)

#### `test_orchestration_integration.py` (396 lignes)
**Tests de bout en bout et d'intégration**

- **TestEndToEndOrchestration** : Tests de bout en bout
  - Mode pipeline standard
  - Mode hiérarchique complet
  - Orchestrateurs spécialisés
  - Sélection automatique

- **TestCompatibilityWithExistingAPI** : Compatibilité API
  - Compatibilité avec `run_unified_text_analysis()`
  - Fallback vers pipeline original
  - Mapping des paramètres

- **TestPerformanceAndRobustness** : Performance et robustesse
  - Requêtes concurrentes
  - Gestion d'erreurs robuste
  - Optimisation mémoire
  - Fonctionnalité des traces

- **TestSpecializedIntegrationScenarios** : Scénarios spécialisés
  - Coordination multi-orchestrateurs
  - Chaînes d'escalade et fallback

## Lancement des Tests

### Script automatisé
```bash
# Tous les tests avec rapport HTML
python tests/run_orchestration_tests.py --html-report --coverage

# Tests unitaires seulement
python tests/run_orchestration_tests.py --unit --verbose

# Tests d'intégration seulement  
python tests/run_orchestration_tests.py --integration

# Tests rapides en parallèle
python tests/run_orchestration_tests.py --fast --parallel 4
```

### Commandes pytest directes
```bash
# Tests unitaires d'orchestration
pytest tests/unit/orchestration/ -v

# Tests d'intégration
pytest tests/integration/test_orchestration_integration.py -v

# Avec couverture de code
pytest tests/unit/orchestration/ --cov=argumentation_analysis.pipelines.unified_orchestration_pipeline --cov-report=html

# Tests spécifiques
pytest tests/unit/orchestration/test_la classe `UnifiedPipeline` du module `argumentation_analysis/pipelines/unified_pipeline.py`::TestUnifiedOrchestrationPipeline::test_analyze_text_orchestrated_basic -v
```

## Couverture de Code

### Composants testés
- ✅ `UnifiedOrchestrationPipeline` (pipeline principal)
- ✅ `ExtendedOrchestrationConfig` (configuration étendue)
- ✅ `StrategicManager` (gestionnaire stratégique)
- ✅ `TaskCoordinator` (coordinateur tactique)
- ✅ `OperationalManager` (gestionnaire opérationnel)
- ✅ `CluedoOrchestrator` (orchestrateur d'investigation)
- ✅ `ConversationOrchestrator` (orchestrateur conversationnel)
- ✅ `RealLLMOrchestrator` (orchestrateur LLM réel)
- ✅ `LogiqueComplexeOrchestrator` (orchestrateur logique complexe)
- ✅ Fonctions publiques d'orchestration
- ✅ Intégration avec l'API existante
- ✅ Gestion d'erreurs et fallbacks

### Objectifs de couverture
- **Tests unitaires** : >90% de couverture de code
- **Tests d'intégration** : 100% des flux principaux
- **Gestion d'erreurs** : Tous les cas d'échec critiques
- **Performance** : Tests de charge et optimisation

## Stratégies de Test

### 1. **Mocking et Isolation**
- Services LLM mockés pour performance
- Composants isolés pour tests unitaires
- Fallbacks testés séparément

### 2. **Tests de Performance**
- Benchmarks de temps d'exécution
- Tests de charge concurrente
- Monitoring d'usage mémoire
- Optimisation des traces

### 3. **Tests de Robustesse**
- Gestion d'erreurs multiples niveaux
- Fallbacks et récupération gracieuse
- Validation des configurations
- Tests de cas limites

### 4. **Tests d'Intégration**
- Flux complets de bout en bout
- Compatibilité API existante
- Coordination inter-composants
- Scénarios réels d'usage

## Métriques de Qualité

### Couverture attendue
```
Component                           Lignes    Couvert    %
===========================================================
unified_orchestration_pipeline     1142      >1027     >90%
hierarchical_managers              ~800      >720      >90%
specialized_orchestrators          ~600      >540      >90%
integration_scenarios              ~400      >360      >90%
===========================================================
TOTAL                              ~2942     >2647     >90%
```

### Tests par catégorie
- **Tests unitaires** : ~140 tests
- **Tests d'intégration** : ~25 tests
- **Tests de performance** : ~15 tests
- **Tests de robustesse** : ~20 tests
- **Total estimé** : ~200 tests

## Maintenance et Évolution

### Ajout de nouveaux tests
1. **Tests unitaires** : Ajouter dans le fichier correspondant au composant
2. **Tests d'intégration** : Étendre `test_orchestration_integration.py`
3. **Nouveaux orchestrateurs** : Créer section dans `test_specialized_orchestrators.py`

### Debugging et Diagnostics
- Utiliser `--verbose` pour détails d'exécution
- Activer les traces d'orchestration avec `save_orchestration_trace=True`
- Analyser les rapports de couverture HTML
- Vérifier les logs de performance pour optimisations

### CI/CD Integration
Les tests sont conçus pour s'intégrer facilement dans les pipelines CI/CD :
- Support des markers pytest (`@pytest.mark.slow`, etc.)
- Rapports XML/HTML pour intégration
- Tests parallèles pour performance
- Mocks pour isolation des dépendances externes