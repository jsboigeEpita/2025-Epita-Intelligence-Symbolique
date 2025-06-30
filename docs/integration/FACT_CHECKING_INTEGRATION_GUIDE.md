# Guide d'Intégration du Système de Fact-Checking et Taxonomie des Sophismes

## Vue d'ensemble

Ce guide documente l'intégration réussie du module de fact-checking et de la taxonomie des sophismes en 8 familles dans le système d'analyse argumentative de l'EPITA.

## Architecture Intégrée

### Nouveaux Composants

#### 1. FallacyTaxonomyManager
**Localisation** : `argumentation_analysis/services/fallacy_taxonomy_service.py`

**Responsabilités** :
- Gestion de la taxonomie des 8 familles de sophismes
- Classification automatique des sophismes détectés
- Intégration avec la taxonomie existante (400+ sophismes)

**8 Familles de Sophismes** :
1. **Authority & Popularity** : Appels à l'autorité et à la popularité
2. **Emotional Appeals** : Manipulation émotionnelle
3. **Generalization & Causality** : Erreurs de généralisation et causalité
4. **Diversion & Attack** : Diversions et attaques personnelles
5. **False Dilemma & Simplification** : Faux dilemmes et simplifications
6. **Language & Ambiguity** : Ambiguïtés linguistiques
7. **Statistical & Probabilistic** : Erreurs statistiques
8. **Audio/Oral Context** : Sophismes du contexte oral

#### 2. FactClaimExtractor
**Localisation** : `argumentation_analysis/agents/tools/analysis/fact_claim_extractor.py`

**Fonctionnalités** :
- Extraction automatique d'affirmations vérifiables
- 10 types d'affirmations (statistique, historique, scientifique, etc.)
- Évaluation de la vérifiabilité
- Support NLP avec spaCy (optionnel)

#### 3. FactVerificationService
**Localisation** : `argumentation_analysis/services/fact_verification_service.py`

**Capacités** :
- Vérification multi-source (Tavily, SearXNG, simulation)
- Évaluation de la fiabilité des sources
- 7 statuts de vérification
- Cache intelligent avec expiration

#### 4. FallacyFamilyAnalyzer
**Localisation** : `argumentation_analysis/agents/tools/analysis/fallacy_family_analyzer.py`

**Fonctionnalités** :
- Analyse complète intégrant fact-checking + sophismes
- 4 niveaux de profondeur (basic, standard, comprehensive, expert)
- Analyse stratégique et insights
- Recommandations contextuelles

#### 5. FactCheckingOrchestrator
**Localisation** : `argumentation_analysis/orchestration/fact_checking_orchestrator.py`

**Coordination** :
- Orchestration complète du processus d'analyse
- Analyse en lot et traitement parallèle
- Métriques de performance
- Health checks intégrés

## Intégration avec l'Architecture Existante

### ServiceManager
Le `OrchestrationServiceManager` a été étendu pour inclure le `FactCheckingOrchestrator` :

```python
# Nouveaux types d'analyse supportés
'fact_checking': self.fact_checking_orchestrator,
'comprehensive': self.fact_checking_orchestrator,
'fallacy_analysis': self.fact_checking_orchestrator,
'rhetorical': self.fact_checking_orchestrator,
```

### Configuration
```python
config = {
    'enable_specialized_orchestrators': True,
    'fact_checking_api_config': {
        'tavily_api_key': 'your_api_key',
        'searxng_url': 'http://your.searxng.url'
    }
}
```

## Utilisation

### 1. Analyse Complète avec Fact-Checking

```python
from argumentation_analysis.orchestration.fact_checking_orchestrator import (
    get_fact_checking_orchestrator, FactCheckingRequest, AnalysisDepth
)

# Configuration API (optionnelle)
api_config = {
    'tavily_api_key': 'your_tavily_api_key'
}

# Créer une requête
request = FactCheckingRequest(
    text="En 2024, 85% des entreprises utilisent l'IA selon une étude récente.",
    analysis_depth=AnalysisDepth.COMPREHENSIVE,
    enable_fact_checking=True,
    api_config=api_config
)

# Analyser
orchestrator = get_fact_checking_orchestrator(api_config)
response = await orchestrator.analyze_with_fact_checking(request)

# Résultats
print(f"Statut: {response.status}")
print(f"Familles détectées: {len(response.comprehensive_result.family_results)}")
print(f"Affirmations vérifiées: {len(response.comprehensive_result.fact_check_results)}")
```

### 2. Fact-Checking Rapide

```python
# Fact-checking uniquement (sans analyse complète des sophismes)
result = await orchestrator.quick_fact_check(
    "90% des français utilisent internet quotidiennement.",
    max_claims=5
)

print(f"Claims trouvées: {result['claims_count']}")
print(f"Score de crédibilité: {result['summary']['credibility_score']}")
```

### 3. Analyse des Familles de Sophismes

```python
# Analyse des sophismes uniquement (sans fact-checking)
result = await orchestrator.analyze_fallacy_families_only(
    "Tous les experts s'accordent à dire que cette solution est la meilleure.",
    depth=AnalysisDepth.STANDARD
)

print(f"Sophismes détectés: {len(result['fallacies_detected'])}")
for family, stats in result['family_statistics'].items():
    if stats['present']:
        print(f"Famille {family}: {stats['count']} sophismes")
```

### 4. Via ServiceManager

```python
from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager

# Créer et initialiser
manager = OrchestrationServiceManager(config={
    'enable_specialized_orchestrators': True,
    'fact_checking_api_config': api_config
})
await manager.initialize()

# Analyser
result = await manager.analyze_text(
    "Texte à analyser avec fact-checking intégré",
    analysis_type="comprehensive",
    options={'enable_fact_checking': True}
)

print(f"Méthode: {result['results']['specialized']['method']}")
print(f"Temps de traitement: {result['duration']}s")
```

## Fonctions de Commodité

### Analyse Rapide
```python
from argumentation_analysis.orchestration.fact_checking_orchestrator import (
    quick_analyze_text, quick_fact_check_only, quick_fallacy_analysis_only
)

# Analyse complète en une ligne
result = await quick_analyze_text("Votre texte ici", api_config)

# Fact-checking uniquement
fact_result = await quick_fact_check_only("Affirmation à vérifier", api_config)

# Sophismes uniquement
fallacy_result = await quick_fallacy_analysis_only("Texte avec sophismes")
```

## Patterns Singleton

Tous les composants principaux utilisent le pattern singleton pour optimiser les performances :

```python
# Instances globales réutilisables
taxonomy_manager = get_taxonomy_manager()
family_analyzer = get_family_analyzer(api_config)
verification_service = get_verification_service(api_config)
fact_checking_orchestrator = get_fact_checking_orchestrator(api_config)
```

## Métriques et Monitoring

### Performance de l'Orchestrateur
```python
metrics = orchestrator.get_performance_metrics()
print(f"Analyses totales: {metrics['total_analyses']}")
print(f"Temps moyen: {metrics['average_processing_time']:.2f}s")
print(f"Taux d'erreur: {metrics['error_rate']:.2%}")
```

### Health Check
```python
health = await orchestrator.health_check()
print(f"Statut global: {health['status']}")
for component, status in health['components'].items():
    print(f"{component}: {status['status']}")
```

## Structures de Données

### Résultat d'Analyse Complète
```python
{
    "analysis_timestamp": "2024-12-06T...",
    "analysis_depth": "comprehensive",
    "family_results": {
        "emotional_appeals": {
            "fallacies_detected": [...],
            "family_score": 0.75,
            "severity_assessment": "Haute",
            "recommendations": [...]
        }
    },
    "factual_claims": [...],
    "fact_check_results": [...],
    "overall_assessment": {
        "total_families_detected": 3,
        "overall_severity": "Moyenne",
        "credibility_score": 0.65
    },
    "strategic_insights": {
        "argumentation_strategy": "Persuasion émotionnelle",
        "sophistication_level": "Avancé"
    },
    "recommendations": [...]
}
```

### Affirmation Factuelle
```python
{
    "claim_text": "85% des entreprises utilisent l'IA",
    "claim_type": "statistical",
    "verifiability": "highly_verifiable",
    "confidence": 0.9,
    "entities": [...],
    "numerical_values": [{"value": 85.0, "unit": "%"}],
    "sources_mentioned": [...]
}
```

### Résultat de Vérification
```python
{
    "status": "verified_true",
    "confidence": 0.85,
    "verdict": "Affirmation vérifiée comme vraie",
    "sources": [...],
    "supporting_sources": 3,
    "contradicting_sources": 0,
    "fallacy_implications": [...]
}
```

## Tests et Validation

### Tests Unitaires
```bash
# Tests des nouveaux composants
pytest tests/test_fact_checking_integration.py -v

# Tests d'intégration avec l'orchestration
pytest tests/test_orchestration_integration.py -v
```

### Tests de Performance
Les tests incluent des validations de performance :
- Extraction d'affirmations : < 10 secondes
- Classification taxonomique : < 5 secondes
- Analyse complète : temps raisonnable selon la complexité

## Configuration Avancée

### API de Fact-Checking
```python
api_config = {
    # Tavily (recommandé)
    'tavily_api_key': 'your_tavily_key',
    
    # SearXNG (auto-hébergé)
    'searxng_url': 'http://your.searxng.instance',
    
    # Sources personnalisées
    'custom_reliable_sources': [
        'your-trusted-domain.com'
    ],
    
    # Configuration de cache
    'cache_duration_hours': 24,
    'max_concurrent_verifications': 3
}
```

### Niveaux d'Analyse
- **BASIC** : Détection rapide, analyse limitée
- **STANDARD** : Analyse équilibrée (recommandé)
- **COMPREHENSIVE** : Analyse approfondie avec insights
- **EXPERT** : Analyse maximale avec patterns complexes

## Dépannage

### Problèmes Courants

1. **Import Errors** : Vérifier que tous les nouveaux modules sont dans le PYTHONPATH
2. **API Keys** : Configurer les clés API pour le fact-checking externe
3. **Performance** : Ajuster les niveaux d'analyse selon les besoins
4. **spaCy** : Installation optionnelle pour améliorer l'extraction NLP

### Logs et Debug
```python
import logging
logging.getLogger("FallacyTaxonomyManager").setLevel(logging.DEBUG)
logging.getLogger("FactVerificationService").setLevel(logging.DEBUG)
logging.getLogger("FactCheckingOrchestrator").setLevel(logging.DEBUG)
```

## Évolutions Futures

### Roadmap
1. **Intégration LLM** : Utilisation d'OpenAI/Claude pour l'analyse
2. **Sources étendues** : Intégration avec d'autres APIs de fact-checking
3. **ML Classification** : Amélioration de la classification des sophismes
4. **Interface Web** : Dashboard pour l'analyse interactive
5. **API REST** : Exposition des fonctionnalités via API

### Extensibilité
Le système est conçu pour être facilement extensible :
- Nouvelles familles de sophismes
- Nouveaux types d'affirmations factuelles
- Sources de vérification additionnelles
- Métriques personnalisées

## Support et Contribution

Pour toute question ou contribution :
1. Consulter la documentation existante
2. Vérifier les tests unitaires
3. Suivre les patterns établis
4. Ajouter des tests pour les nouvelles fonctionnalités

## Conclusion

L'intégration du système de fact-checking et de taxonomie des sophismes enrichit considérablement les capacités d'analyse argumentative du système EPITA. La combinaison de la détection de sophismes par famille et de la vérification factuelle offre une analyse complète et contextuelle des arguments.

Les performances, la modularité et l'extensibilité du système permettent une adoption progressive et une adaptation aux besoins spécifiques de chaque utilisateur.