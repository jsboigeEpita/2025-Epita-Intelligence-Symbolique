# CLAUDE.md - Contexte du Projet d'Intelligence Symbolique EPITA

## Vue d'ensemble du projet

Ce dépôt contient un système d'analyse argumentative sophistiqué développé pour l'EPITA, intégrant des capacités d'analyse rhétorique, de détection de sophismes et de fact-checking.

## Objectifs principaux

### 1. Intégration du module de fact-checking
- Vérification automatique de la véracité des affirmations factuelles
- Intégration avec les outils d'analyse existants
- Évaluation de la fiabilité des sources

### 2. Classification avancée des sophismes
Organisation des sophismes en 8 familles principales :
- **Sophismes d'appel à l'autorité et à la popularité**
- **Sophismes d'appel aux émotions**
- **Sophismes de généralisation et de causalité**
- **Sophismes de diversion et d'attaque**
- **Sophismes de faux dilemme et de simplification**
- **Sophismes de langage et d'ambiguïté**
- **Sophismes statistiques et probabilistes**
- **Sophismes spécifiques au contexte audio/oral**

## Architecture technique

### Structure principale
```
argumentation_analysis/
├── agents/           # Agents d'analyse (Sherlock, Watson)
├── core/            # Services centraux et logique métier
├── orchestration/   # Orchestrateurs d'analyse
├── mocks/          # Outils d'analyse simulés
├── models/         # Modèles de données
└── services/       # Services techniques (cache, crypto, etc.)
```

### Composants clés
- **FallacyTaxonomyManager** : Gestion de la taxonomie des sophismes
- **FactClaimExtractor** : Extraction d'affirmations factuelles
- **FactVerificationService** : Vérification des faits
- **FallacyFamilyAnalyzer** : Analyse par famille de sophismes

## Fonctionnalités principales

### Analyse argumentative
- Détection et classification de sophismes
- Analyse de stratégies rhétoriques
- Évaluation de la cohérence argumentative
- Analyse de sentiment et tonalité émotionnelle

### Fact-checking intégré
- Extraction automatique d'affirmations vérifiables
- Vérification multi-source (Tavily, SearXNG)
- Évaluation de la crédibilité des sources
- Génération de verdicts avec niveaux de confiance

### Interface utilisateur
- Interface web Streamlit (argumentation_analysis/ui/)
- API REST pour intégration (api/)
- Orchestration conversationnelle (agents Sherlock/Watson)

## Configuration et déploiement

### Environnement de développement
```bash
# Activation de l'environnement
source activate_project_env.sh  # Linux/Mac
# ou
./activate_project_env.ps1     # Windows

# Installation des dépendances
pip install -r requirements.txt
```

### Tests et validation
```bash
# Tests unitaires
pytest tests/

# Validation système
python demos/validation_complete_epita.py

# Tests d'intégration web
python tests_playwright/
```

## Commandes utiles

### Analyse rhétorique
```bash
# Analyse complète d'un texte
python argumentation_analysis/run_analysis.py

# Démonstration interactive
python demos/demo_epita_diagnostic.py
```

### Développement et maintenance
```bash
# Nettoyage du projet
python scripts/cleanup/cleanup_project.py

# Vérification des dépendances
python scripts/diagnostic/test_critical_dependencies.py

# Génération de rapports
python scripts/reporting/generate_comprehensive_report.py
```

## Métriques de qualité cibles

- **Précision classification sophismes** : > 85%
- **Précision fact-checking** : > 80%
- **Temps de réponse** : < 10 secondes
- **Couverture de code** : > 80%

## Cas d'usage principaux

1. **Analyse de discours politiques** - Détection d'appels aux émotions et vérification factuelle
2. **Évaluation d'articles scientifiques** - Analyse des généralisations et relations causales
3. **Analyse de débats** - Détection de diversions et attaques personnelles
4. **Évaluation publicitaire** - Analyse d'appels à l'autorité et vérification des claims

## Documentation complémentaire

- Architecture : `docs/architecture/`
- Guides utilisateur : `docs/guides/`
- Exemples : `examples/`
- Tutoriels : `tutorials/`

## Contribution

Ce projet suit les standards de développement de l'EPITA. Consulter `CONTRIBUTING.md` pour les guidelines de contribution.