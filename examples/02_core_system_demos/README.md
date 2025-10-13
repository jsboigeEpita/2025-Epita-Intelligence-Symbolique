# ⚙️ Core System Demos

## Description

Ce répertoire contient des démonstrations exhaustives des fonctionnalités centrales du système d'argumentation. Ces démos illustrent l'utilisation des services core, l'orchestration hiérarchique, l'intégration des agents, et les cas d'usage complets.

## Contenu

### Sous-Répertoires

| Répertoire | Description | Complexité | Scripts Clés |
|------------|-------------|------------|--------------|
| **[phase2_demo/](./phase2_demo/)** | Démonstrations des fonctionnalités Phase 2 | Intermédiaire | demo_authentic_llm_validation.py |
| **[scripts_demonstration/](./scripts_demonstration/)** | Scripts de démonstration exhaustifs et modulaires | Avancé | demonstration_epita.py, modules/ |

## 📦 Phase 2 Demo

**Objectif** : Démontrer les capacités de validation et d'analyse avec LLM authentique

### Fichiers

| Fichier | Description | Lignes |
|---------|-------------|--------|
| [`demo_authentic_llm_validation.py`](./phase2_demo/demo_authentic_llm_validation.py) | Validation authentique avec LLM réel (230 lignes) | 230 |

### Fonctionnalités Démontrées

- ✅ **Intégration LLM** : Utilisation de modèles de langage réels
- ✅ **Validation authentique** : Tests avec données réelles
- ✅ **Workflows Phase 2** : Démonstration des workflows avancés
- ✅ **Gestion d'erreurs** : Robustesse et résilience

### Utilisation

```bash
# Naviguer vers le répertoire
cd examples/02_core_system_demos/phase2_demo

# Configurer les clés API (si nécessaire)
export OPENAI_API_KEY="votre-clé"

# Exécuter la démo
python demo_authentic_llm_validation.py
```

### Ce Que Vous Apprendrez

- ✅ Intégrer des LLM dans le système
- ✅ Valider les résultats d'analyse
- ✅ Gérer les appels API asynchrones
- ✅ Optimiser l'utilisation des tokens

**📖 [Code source](./phase2_demo/demo_authentic_llm_validation.py)**

## 🎯 Scripts Demonstration

**Objectif** : Collection complète de scripts modulaires démontrant toutes les fonctionnalités du système

### Architecture

```
scripts_demonstration/
├── demonstration_epita.py      # Script principal orchestrateur (843 lignes)
├── demo_tweety_interaction_simple.py  # Intégration Tweety (240 lignes)
├── generate_complex_synthetic_data.py # Génération données (379 lignes)
├── test_architecture.py        # Tests architecture (186 lignes)
├── configs/                    # Configurations YAML
│   └── demo_categories.yaml    # Catégories de démos (110 lignes)
└── modules/                    # Modules démonstration
    ├── demo_analyse_argumentation.py  # Analyse argumentative (120 lignes)
    ├── demo_cas_usage.py              # Cas d'usage (512 lignes)
    ├── demo_integrations.py           # Intégrations (393 lignes)
    ├── demo_services_core.py          # Services core (314 lignes)
    ├── demo_tests_validation.py       # Tests validation (231 lignes)
    └── demo_utils.py                  # Utilitaires (235 lignes)
```

### Scripts Principaux

#### 1. demonstration_epita.py (843 lignes)

**Script orchestrateur principal** pour démonstrations EPITA.

```bash
# Exécution complète
python scripts_demonstration/demonstration_epita.py

# Mode spécifique
python scripts_demonstration/demonstration_epita.py --mode validation
python scripts_demonstration/demonstration_epita.py --mode integration
python scripts_demonstration/demonstration_epita.py --mode cas-usage
```

**Ce qu'il démontre** :
- Orchestration de toutes les démos
- Génération de rapports exhaustifs
- Tests de validation complets
- Cas d'usage réels

#### 2. demo_tweety_interaction_simple.py (240 lignes)

**Démonstration d'intégration** avec la bibliothèque Tweety pour la logique formelle.

```bash
python scripts_demonstration/demo_tweety_interaction_simple.py
```

**Ce qu'il démontre** :
- Intégration Tweety (Java bridge)
- Logique argumentative formelle
- Calcul d'extensions
- Sémantiques de Dung

#### 3. generate_complex_synthetic_data.py (379 lignes)

**Générateur de données synthétiques** complexes pour tests.

```bash
# Générer 100 exemples
python scripts_demonstration/generate_complex_synthetic_data.py --count 100

# Avec sophismes spécifiques
python scripts_demonstration/generate_complex_synthetic_data.py --fallacies "ad_hominem,straw_man"

# Export JSON
python scripts_demonstration/generate_complex_synthetic_data.py --output synthetic_data.json
```

**Ce qu'il génère** :
- Textes argumentatifs variés
- Sophismes de tous types
- Structures rhétoriques complexes
- Données annotées pour ML

### Modules de Démonstration

#### Analyse Argumentation

**Fichier** : `modules/demo_analyse_argumentation.py` (120 lignes)

**Démontre** :
- Extraction d'arguments
- Détection de sophismes
- Analyse de cohérence
- Évaluation de qualité

```python
from modules.demo_analyse_argumentation import demo_analyse_complete

# Analyser un texte
resultat = demo_analyse_complete("Texte argumentatif...")
print(resultat.sophismes)
print(resultat.structure)
```

#### Cas d'Usage

**Fichier** : `modules/demo_cas_usage.py` (512 lignes)

**Démontre** :
- Analyse de discours politique
- Évaluation d'article scientifique
- Débat contradictoire
- Argumentation juridique

```python
from modules.demo_cas_usage import demo_discours_politique

# Cas d'usage: discours politique
demo_discours_politique("discours.txt")
```

#### Intégrations

**Fichier** : `modules/demo_integrations.py` (393 lignes)

**Démontre** :
- Intégration API externe
- Workflows distribués
- Microservices
- Event-driven architecture

#### Services Core

**Fichier** : `modules/demo_services_core.py` (314 lignes)

**Démontre** :
- ExtractService
- AnalysisService
- ValidationService
- ReportingService

#### Tests & Validation

**Fichier** : `modules/demo_tests_validation.py` (231 lignes)

**Démontre** :
- Tests unitaires
- Tests d'intégration
- Tests de performance
- Validation end-to-end

### Configuration

#### demo_categories.yaml (110 lignes)

Définit les catégories de démonstrations :

```yaml
categories:
  - name: "Analyse Argumentative"
    demos:
      - id: "analyse_simple"
        description: "Analyse de base"
      - id: "analyse_avancee"
        description: "Analyse approfondie"
  
  - name: "Intégrations"
    demos:
      - id: "tweety"
        description: "Intégration Tweety"
```

### Documentation Complémentaire

| Document | Description | Lignes |
|----------|-------------|--------|
| [ARCHITECTURE_SUMMARY.md](./scripts_demonstration/ARCHITECTURE_SUMMARY.md) | Résumé de l'architecture (160 lignes) | 160 |
| [README_DEMONSTRATION.md](./scripts_demonstration/README_DEMONSTRATION.md) | Guide détaillé (200 lignes) | 200 |
| [GUIDE_VISUEL.md](./scripts_demonstration/GUIDE_VISUEL.md) | Guide visuel avec diagrammes (198 lignes) | 198 |

## Cas d'Usage Complets

### 1. Validation de Pipeline Complet

```bash
# Validation end-to-end
cd scripts_demonstration
python demonstration_epita.py --full-validation

# Génère un rapport complet
# - Résultats par module
# - Métriques de performance
# - Logs détaillés
```

### 2. Génération de Données de Test

```bash
# Générer dataset pour ML
python generate_complex_synthetic_data.py \
  --count 1000 \
  --output ml_dataset.json \
  --balanced \
  --annotated
```

### 3. Démo Interactive

```bash
# Mode interactif pour présentation
python demonstration_epita.py --interactive

# Permet de:
# - Sélectionner les démos à exécuter
# - Voir les résultats en temps réel
# - Exporter les rapports
```

## Performance

### Métriques Typiques

| Script | Temps d'exécution | Mémoire | Complexité |
|--------|-------------------|---------|------------|
| demo_authentic_llm_validation | 10-30 secondes | ~100 MB | Moyenne |
| demonstration_epita (complet) | 2-5 minutes | ~200 MB | Élevée |
| generate_complex_synthetic_data | 5-10 secondes/100 exemples | ~50 MB | Variable |
| demo_tweety_interaction_simple | 5-15 secondes | ~150 MB | Moyenne |

### Optimisations

- **Caching** : Les résultats LLM sont mis en cache
- **Parallel processing** : Certaines démos s'exécutent en parallèle
- **Lazy loading** : Modules chargés à la demande
- **Resource pooling** : Connexions réutilisées

## Développement

### Ajouter une Nouvelle Démo

1. **Créer le module** dans `modules/`
   ```python
   # modules/demo_ma_feature.py
   def demo_ma_feature():
       """Démontre ma nouvelle fonctionnalité"""
       # Implémentation
       pass
   ```

2. **Enregistrer dans la config**
   ```yaml
   # configs/demo_categories.yaml
   - id: "ma_feature"
     description: "Ma nouvelle fonctionnalité"
     module: "demo_ma_feature"
   ```

3. **Intégrer dans l'orchestrateur**
   ```python
   # demonstration_epita.py
   from modules.demo_ma_feature import demo_ma_feature
   
   def run_all_demos():
       # ...
       demo_ma_feature()
   ```

### Structure Recommandée

```python
#!/usr/bin/env python3
"""
Module: demo_ma_feature
Description: Démontre ma fonctionnalité
"""

def demo_ma_feature(config=None):
    """
    Point d'entrée principal de la démo
    
    Args:
        config: Configuration optionnelle
        
    Returns:
        Résultats de la démo
    """
    print("=== Ma Feature Demo ===\n")
    
    # 1. Setup
    setup()
    
    # 2. Exécution
    results = execute()
    
    # 3. Validation
    validate(results)
    
    # 4. Rapport
    return generate_report(results)

if __name__ == "__main__":
    demo_ma_feature()
```

## Bonnes Pratiques

### Pour les Démos

1. **Auto-contenu** : Chaque démo doit fonctionner indépendamment
2. **Documentation** : Docstrings claires et complètes
3. **Logging** : Utiliser le logging pour traçabilité
4. **Validation** : Valider les résultats systématiquement
5. **Rapport** : Générer un résumé des résultats

### Pour le Code

1. **Modulaire** : Un fichier = une responsabilité
2. **Réutilisable** : Extraire les fonctions communes
3. **Testable** : Écrire des tests pour chaque module
4. **Documenté** : README + docstrings + commentaires
5. **Type hints** : Annotations de types

## Ressources Connexes

- **[Logic & Riddles](../01_logic_and_riddles/)** : Exemples de logique
- **[Integrations](../03_integrations/)** : Intégrations système
- **[Plugins](../04_plugins/)** : Architecture extensible
- **[Tutorials](../../tutorials/)** : Guides d'apprentissage
- **[Demos](../../demos/)** : Autres démonstrations

## Contribution

### Workflow

1. **Identifier le besoin** : Quelle démo manque ?
2. **Créer le module** : Suivre la structure recommandée
3. **Tester** : Valider le fonctionnement
4. **Documenter** : README + docstrings
5. **Intégrer** : Ajouter à l'orchestrateur
6. **PR** : Soumettre pour review

### Checklist

- [ ] Module créé dans `modules/`
- [ ] Tests écrits et passants
- [ ] Documentation complète
- [ ] Intégré dans `demonstration_epita.py`
- [ ] Ajouté dans `demo_categories.yaml`
- [ ] README mis à jour

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA  
**Niveau** : Intermédiaire à Avancé  
**Technologies** : Python, Semantic Kernel, LLM, Tweety