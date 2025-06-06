# Documentation du Script de Démonstration

Ce document décrit le fonctionnement de la suite de démonstration du projet d'Intelligence Symbolique EPITA, qui est orchestrée par le script principal `demonstration_epita.py`.

## Objectif et Structure

La suite de démonstration est conçue pour être modulaire et claire. Elle est divisée en plusieurs scripts pour séparer les préoccupations :

1.  **`demonstration_epita.py` (Orchestrateur)** : Le point d'entrée principal. Son rôle est d'exécuter les différentes parties de la démonstration dans un ordre logique :
    - Vérification des dépendances.
    - Exécution du script des fonctionnalités notables.
    - Exécution du script des fonctionnalités avancées.
    - Lancement de la suite de tests complète du projet.

2.  **`demo_notable_features.py` (Sous-script)** : Ce script présente les fonctionnalités clés et les plus simples à comprendre du projet, en se basant sur des **mocks**. Cela permet une exécution rapide et sans dépendances externes lourdes. Il couvre :
    - L'analyse de cohérence.
    - Le score de clarté.
    - L'extraction d'arguments.
    - La génération (simulée) de visualisations.

3.  **`demo_advanced_features.py` (Sous-script)** : Ce script illustre des cas d'usage plus complexes qui peuvent interagir avec des services réels (si configurés). Il couvre :
    - L'analyse de texte clair avec un agent.
    - Le pipeline complet d'analyse de données chiffrées.
    - La génération de rapports.
    - L'interaction avec la bibliothèque Java Tweety via JPype.
    - La simulation de l'**orchestration tactique** pour décomposer des objectifs complexes.
    - La simulation de l'**analyse de sophismes composés** pour une détection plus fine.

## Comment Exécuter la Suite de Démonstration

Pour lancer l'ensemble de la suite, exécutez la commande suivante depuis la **racine du projet** :

```bash
python examples/scripts_demonstration/demonstration_epita.py
```

Le script orchestrateur se chargera d'appeler les sous-scripts et d'exécuter les tests dans le bon ordre, en affichant la progression dans la console.