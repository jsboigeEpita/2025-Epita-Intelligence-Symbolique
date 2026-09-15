# Outils et Utilitaires

Ce répertoire contient les outils et utilitaires utilisés par les agents du système d'analyse d'argumentation.

## Structure

- `optimization/` - Outils d'optimisation pour améliorer les performances des agents
- `analysis/` - Outils d'analyse pour évaluer les résultats et les performances

> L'outillage d'encryption historique (`encryption/`) a été retiré (#2120) : il
> était inexécutable (import absent, chaîne de clé morte) et doublait la surface
> vivante — [`core/io_manager.py`](../../core/io_manager.py) pour le chargement
> du dataset chiffré et [`scripts/security/verify_encrypted_dataset_completeness.py`](../../../../scripts/security/verify_encrypted_dataset_completeness.py)
> pour la vérification avant suppression.

## Utilisation

Ces outils sont conçus pour être utilisés en conjonction avec les agents principaux. Ils fournissent des fonctionnalités supplémentaires qui ne font pas partie du cœur des agents mais qui sont nécessaires pour leur bon fonctionnement ou pour l'analyse de leurs résultats.

### Outils d'optimisation

Les outils d'optimisation permettent d'améliorer les performances des agents en ajustant leurs paramètres ou en analysant leurs résultats pour identifier des points d'amélioration.

Exemples d'utilisation :
- Analyse de la taxonomie des sophismes
- Optimisation des prompts des agents
- Amélioration des performances des agents
- Comparaison des différentes versions des agents

### Outils d'analyse

Les outils d'analyse permettent d'évaluer les résultats produits par les agents et de générer des rapports sur leurs performances.

Exemples d'utilisation :
- Analyse des traces d'exécution
- Génération de rapports de performance
- Visualisation des résultats
- Détection d'anomalies dans les analyses

## Intégration

Ces outils peuvent être utilisés de manière indépendante ou intégrés dans des workflows plus complexes. Ils sont conçus pour être modulaires et réutilisables.