# Tests Unitaires pour l'Analyse d'Argumentation

## Objectif

Ce répertoire est le point d'entrée pour tous les tests unitaires liés au cœur du projet d'analyse d'argumentation. Il couvre l'ensemble des composants, des agents spécialisés aux pipelines d'orchestration, en passant par les services de bas niveau et les utilitaires transverses.

L'objectif global de ces tests est de garantir que chaque composant individuel du système fonctionne de manière isolée, fiable et prévisible. Cela permet de s'assurer que les briques fondamentales de l'application sont solides avant de les intégrer dans des tests de plus haut niveau.

## Sous-répertoires

-   **[agents](./agents/README.md)** : Contient les tests pour les agents d'analyse et leurs outils. Valide la logique des agents de base (`core`) et des outils d'analyse spécialisés (`tools`).

-   **[analytics](./analytics/README.md)** : Contient les tests pour les modules d'analyse statistique et textuelle, garantissant la fiabilité des calculs de métriques et de l'orchestration des analyses.

-   **[core](./core/README.md)** : Contient les tests pour les composants et pipelines fondamentaux du système, comme les processus de configuration et de maintenance de l'environnement.

-   **[mocks](./mocks/README.md)** : Contient les tests pour les classes qui simulent des outils d'analyse complexes. Ces tests garantissent que les mocks sont fiables pour les tests des composants de plus haut niveau.

-   **[nlp](./nlp/README.md)** : Contient les tests pour les utilitaires de traitement du langage naturel, notamment la génération et la sauvegarde des "embeddings".

-   **[orchestration](./orchestration/README.md)** : Contient les tests pour les modules qui orchestrent des séquences d'analyse complexes, en s'assurant que le flux de données et la gestion des erreurs sont corrects.

-   **[pipelines](./pipelines/README.md)** : Contient les tests pour les pipelines de haut niveau qui exécutent des séquences complètes d'analyse, de la lecture des données à la génération des résultats.

-   **[reporting](./reporting/README.md)** : Contient les tests pour les modules de génération de rapports, validant la création de synthèses et de documents à partir des résultats d'analyse.

-   **[service_setup](./service_setup/README.md)** : Contient les tests pour la configuration et l'initialisation des services de base (JVM, LLM, etc.).

-   **[utils](./utils/README.md)** : Contient les tests pour tous les modules utilitaires, qu'ils soient fondamentaux (`core_utils`) ou destinés au développement (`dev_tools`).
