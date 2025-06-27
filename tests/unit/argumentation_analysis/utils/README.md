# Tests Unitaires pour les Utilitaires

## Objectif

Ce répertoire regroupe tous les tests unitaires pour les modules utilitaires du projet. Ces modules fournissent des fonctionnalités transverses qui sont utilisées par de nombreux autres composants du système, allant des opérations de bas niveau (fichiers, réseau) aux outils de plus haut niveau pour le développement et la maintenance.

L'objectif est de garantir la fiabilité et la robustesse de ces fondations essentielles.

## Sous-répertoires

-   **[core_utils](./core_utils/README.md)** : Contient les tests pour les utilitaires fondamentaux. Ces tests valident les fonctions de manipulation de fichiers, de cryptographie, d'exécution de commandes, de traitement de texte et de reporting.

-   **[dev_tools](./dev_tools/README.md)** : Contient les tests pour les outils destinés à aider au développement. Ces tests valident les fonctions de formatage de code, de validation de syntaxe, de correction d'encodage et les utilitaires de mocking (comme le simulateur JPype).
