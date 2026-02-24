# Cartographie de la Structure des Tests Unitaires

Ce document décrit l'organisation du répertoire `tests/unit/` et la manière dont les tests unitaires sont structurés par rapport au code de production.

## Organisation Générale

La suite de tests unitaires, située dans `tests/unit/`, est conçue pour refléter la structure modulaire du code source de l'application. Chaque sous-répertoire dans `tests/unit/` correspond à un module ou un composant majeur du projet.

Cette approche permet de :
-   **Localiser facilement les tests** pour un module spécifique.
-   **Comprendre la couverture de test** pour chaque partie de l'application.
-   **Maintenir une organisation claire** à mesure que le projet évolue.

## Structure par Composant

Voici une description des principaux répertoires de tests et de leur correspondance avec le code de production :

-   `tests/unit/argumentation_analysis/` : Contient les tests pour le cœur de l'analyse argumentative. Il est subdivisé en tests pour :
    -   `agents/` : Tests des différents types d'agents (logiques, d'extraction, etc.).
    -   `core/` : Tests des mécanismes centraux et des modèles de données.
    -   `orchestration/` : Tests des orchestrateurs qui gèrent les flux d'analyse.
    -   `nlp/` : Tests pour les utilitaires de traitement du langage naturel.
    -   `utils/` : Tests pour les fonctions utilitaires générales.

-   `tests/unit/api/` : Teste les points d'exposition de l'API (`endpoints`), la logique des services et les schémas de données.

-   `tests/unit/agents/` : Teste les agents logiques de manière plus ciblée, notamment les agents `Sherlock` et `Watson` basés sur JTMS.

-   `tests/unit/orchestration/` : Se concentre sur les tests du moteur d'orchestration, y compris les gestionnaires hiérarchiques et les orchestrateurs spécialisés.

-   `tests/unit/services/` : Valide les services indépendants, comme le serveur MCP.

-   `tests/unit/webapp/` : Contient les tests pour les composants liés à l'application web, tels que les gestionnaires backend/frontend et les configurations.

-   `tests/unit/config/` : Teste la logique de configuration unifiée pour s'assurer que tous les paramètres sont correctement chargés et validés.

-   `tests/unit/utils/` : Contient les tests pour les utilitaires transversaux (cryptographie, gestion de fichiers, etc.).

## Comment Lancer les Tests

Pour exécuter l'intégralité de la suite de tests unitaires, utilisez la commande suivante à la racine du projet :

```bash
pytest tests/unit/
```

Cette commande découvrira et exécutera automatiquement tous les tests situés dans ce répertoire.