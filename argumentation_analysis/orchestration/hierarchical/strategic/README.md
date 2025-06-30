# Couche Stratégique

## Rôle et Responsabilités

La couche stratégique est le "cerveau" de l'orchestration hiérarchique. Elle opère au plus haut niveau d'abstraction et est responsable de la **planification à long terme** et de l'**allocation des ressources macro**.

Ses missions principales sont :

1.  **Interpréter la Requête** : Analyser la demande initiale de l'utilisateur pour en extraire les objectifs fondamentaux.
2.  **Définir la Stratégie** : Élaborer un plan d'action de haut niveau. Cela implique de choisir les grands axes d'analyse (ex: "analyse logique et informelle", "vérification des faits", "évaluation stylistique") sans entrer dans les détails de leur exécution.
3.  **Allouer les Ressources** : Déterminer les capacités générales requises (ex: "nécessite un agent logique", "nécessite un accès à la base de données X") et s'assurer qu'elles sont disponibles.
4.  **Superviser et Conclure** : Suivre la progression globale de l'analyse en se basant sur les rapports de la couche tactique et synthétiser les résultats finaux en une réponse cohérente.

En résumé, la couche stratégique définit le **"Pourquoi"** et le **"Quoi"** de l'analyse, en laissant le "Comment" aux couches inférieures.

## Composants Clés

-   **`manager.py`** : Le `StrategicManager` est le point d'entrée et de sortie de la couche. Il coordonne les autres composants et communique avec la couche tactique.
-   **`planner.py`** : Contient la logique pour décomposer la requête initiale en un plan stratégique.
-   **`allocator.py`** : Gère l'allocation des ressources de haut niveau pour le plan.
-   **`state.py`** : Modélise l'état interne de la couche stratégique tout au long de l'analyse.