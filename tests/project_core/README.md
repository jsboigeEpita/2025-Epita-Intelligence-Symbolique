# Tests du Cœur du Projet

## Objectif

Ce répertoire regroupe les tests qui valident les briques fondamentales et les services essentiels du projet. Ces tests ne sont pas liés à une fonctionnalité métier spécifique, mais garantissent plutôt que les composants de base sur lesquels repose l'ensemble de l'application sont stables, fiables et correctement configurés.

L'objectif est de s'assurer que l'infrastructure logicielle de base est saine, ce qui est une condition préalable à la fois pour le développement de nouvelles fonctionnalités et pour la stabilité globale du système.

## Structure des Tests

Les tests du cœur du projet sont organisés dans les sous-répertoires suivants :

-   **`dev_utils/`**: Contient les tests pour les outils et utilitaires de développement. Ces tests valident les scripts utilisés pour la préparation des données, la validation de la configuration et la maintenance du projet. Ils garantissent notamment l'intégrité des extraits de données, qui sont essentiels pour l'entraînement et l'évaluation des modèles.

-   **`service_setup/`**: Contient les tests pour l'initialisation et la configuration des services centraux de l'application. Ces tests s'assurent que des services critiques comme la JVM, le service de grand modèle de langage (LLM) et les services de gestion de la configuration sont correctement démarrés et orchestrés.

-   **`utils/`**: Ce répertoire est destiné à contenir les tests pour les utilitaires génériques du projet qui pourraient être ajoutés à l'avenir.

## Importance pour l'Application

Les tests dans ce module sont d'une importance capitale car ils valident les fondations de l'application. Une défaillance dans l'un de ces composants de base pourrait avoir des répercussions importantes sur l'ensemble du système. En garantissant la fiabilité de ces briques fondamentales, nous nous assurons que les couches supérieures de l'application peuvent s'appuyer sur une base solide et prévisible.
