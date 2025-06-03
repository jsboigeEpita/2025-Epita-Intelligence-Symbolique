# Données de Test pour les Outils d'Analyse Rhétorique

Ce répertoire contient les jeux de données de test utilisés pour valider le fonctionnement des outils d'analyse rhétorique améliorés.

## Vue d'ensemble

Les données de test jouent un rôle crucial dans la validation et l'évaluation des performances des outils d'analyse rhétorique. Ce répertoire fournit :

- Des textes argumentatifs de différentes natures et complexités
- Des exemples annotés de sophismes dans divers contextes
- Des jeux de données spécifiques pour les tests de performance
- Des mappings de référence pour les sophismes et les contextes

Ces données sont structurées pour permettre des tests systématiques et reproductibles des capacités d'analyse rhétorique du système.

## Contenu principal

### rhetorical_test_dataset.py

Ce module contient les jeux de données principaux et les fonctions utilitaires pour y accéder :

#### Jeux de données

- `RHETORICAL_TEST_DATASET` : Collection de textes argumentatifs organisés par :
  - Domaine (politique, science, économie, etc.)
  - Complexité (simple, sophismes_simples, sophismes_complexes, etc.)
  - Avec des annotations sur les sophismes présents

- `PERFORMANCE_TEST_DATASET` : Jeu de données spécifiquement conçu pour les tests de performance, avec :
  - Des textes de différentes longueurs
  - Des complexités variables
  - Des métriques de référence pour l'évaluation

#### Mappings de référence

- `FALLACY_MAPPING` : Dictionnaire associant les types de sophismes à leurs descriptions et caractéristiques
- `CONTEXT_MAPPING` : Dictionnaire définissant les différents contextes d'analyse et leurs particularités

#### Fonctions utilitaires

- `get_test_text(domain, complexity, index)` : Récupère un texte de test spécifique
- `get_performance_test_data(size)` : Récupère un ensemble de données pour les tests de performance
- `get_fallacy_info(fallacy_type)` : Obtient les informations sur un type de sophisme
- `get_context_info(context)` : Obtient les informations sur un contexte d'analyse

## Organisation des données

Les données de test sont organisées selon plusieurs dimensions :

### Par domaine

- **Politique** : Discours politiques, débats électoraux, etc.
- **Science** : Articles scientifiques, controverses scientifiques, etc.
- **Économie** : Analyses économiques, prévisions, etc.
- **Philosophie** : Arguments philosophiques, débats éthiques, etc.
- **Médias** : Articles de presse, éditoriaux, etc.

### Par complexité

- **Simple** : Textes argumentatifs sans sophismes
- **Sophismes simples** : Textes contenant des sophismes facilement identifiables
- **Sophismes complexes** : Textes contenant des sophismes subtils ou multiples
- **Contextuels** : Textes dont l'analyse dépend fortement du contexte

### Par type de sophisme

Les données incluent des exemples de nombreux types de sophismes, notamment :
- Ad hominem
- Pente glissante
- Faux dilemme
- Appel à l'autorité
- Homme de paille
- Et bien d'autres...

## Utilisation

Pour utiliser ces données de test dans vos tests d'outils rhétoriques :

```python
from argumentation_analysis.tests.tools.test_data import (
    get_test_text, get_fallacy_info, RHETORICAL_TEST_DATASET
)

# Récupérer un texte politique simple
texte = get_test_text("politique", "simple", 0)

# Obtenir des informations sur un type de sophisme
info_sophisme = get_fallacy_info("ad_hominem")

# Parcourir tous les textes contenant des sophismes complexes
for domaine, complexites in RHETORICAL_TEST_DATASET.items():
    if "sophismes_complexes" in complexites:
        for texte in complexites["sophismes_complexes"]:
            # Analyser le texte avec votre outil
            resultats = mon_outil_analyse.analyser(texte)
            # ...
```

## Extension des données de test

Pour ajouter de nouveaux exemples ou catégories aux données de test :

1. Modifiez le fichier `rhetorical_test_dataset.py`
2. Ajoutez vos nouveaux textes dans la structure appropriée
3. Si nécessaire, étendez les mappings avec de nouvelles catégories
4. Mettez à jour les tests pour couvrir les nouveaux cas

## Validation et maintenance

Les données de test sont régulièrement validées pour s'assurer qu'elles :
- Couvrent un éventail représentatif de cas d'utilisation
- Contiennent des exemples correctement annotés
- Permettent de tester efficacement toutes les fonctionnalités des outils
- Restent à jour avec les évolutions des outils d'analyse

## Voir aussi

- [Documentation des tests des outils rhétoriques](../README.md)
- [Tests des outils d'analyse rhétorique](../test_rhetorical_tools_integration.py)
- [Tests de performance des outils rhétoriques](../test_rhetorical_tools_performance.py)
- [Documentation des outils d'analyse rhétorique](../../../../docs/outils/README.md)