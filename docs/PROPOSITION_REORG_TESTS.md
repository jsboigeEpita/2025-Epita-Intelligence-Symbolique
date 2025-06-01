# Proposition de Réorganisation des Répertoires de Tests

Ce document propose une nouvelle structure pour le répertoire `tests/` afin d'améliorer la clarté, la maintenabilité et la distinction entre les différents types de tests (unitaires, intégration avec mocks, intégration réelle JVM).

## Structure Actuelle (Observée)

Le répertoire `tests/` contient actuellement une structure assez plate avec des sous-répertoires thématiques (`agents/`, `functional/`, `integration/`, `mocks/`, etc.), mais la distinction entre les tests unitaires et les tests d'intégration, en particulier ceux qui dépendent de la JVM réelle, n'est pas toujours explicite au premier coup d'œil.

Exemples de répertoires actuels :
*   `tests/` (racine, contient de nombreux `test_*.py` directs)
*   `tests/agents/`
*   `tests/functional/`
*   `tests/integration/`
*   `tests/integration/jpype_tweety/` (tests JVM réels)
*   `tests/legacy_root_tests/`
*   `tests/minimal_jpype_tweety_tests/`
*   `tests/mocks/`
*   `tests/orchestration/`
*   `tests/scripts/`
*   `tests/ui/`
*   `tests/utils/`

## Proposition de Nouvelle Organisation

Je propose la structure suivante pour mieux catégoriser les tests :

```
tests/
├── unit/
│   ├── <module_name>/
│   │   └── test_*.py (tests purement unitaires, mocks intensifs, pas de JVM)
│   ├── agents/
│   ├── functional/
│   ├── mocks/ (peut rester ici ou être déplacé à la racine des tests si considéré comme une ressource globale)
│   └── ... (autres tests unitaires existants)
├── integration/
│   ├── mocked_jpype/
│   │   └── test_*.py (tests d'intégration simulant JPype/Tweety avec mocks)
│   ├── real_jvm/
│   │   └── jpype_tweety/
│   │       └── test_*.py (tests d'intégration nécessitant une JVM réelle)
│   └── ... (autres tests d'intégration sans JVM spécifique)
├── functional_workflows/ (si les tests fonctionnels sont des workflows de haut niveau)
│   └── test_*.py
├── fixtures/ (pour les données de test, les configurations partagées)
│   └── *.py
└── README.md (expliquant la nouvelle structure)
```

### Justification des Catégories Proposées :

1.  **`tests/unit/`**
    *   **Objectif :** Contenir tous les tests purement unitaires. Ces tests doivent être rapides, isolés et ne jamais démarrer une JVM. Ils devraient utiliser des mocks pour toutes les dépendances externes (y compris JPype).
    *   **Avantages :** Facilite l'exécution rapide des tests de régression pour les développeurs, assure l'isolation des composants, et permet de valider la logique métier sans les complexités de l'environnement d'intégration.
    *   **Migration :** La plupart des fichiers `test_*.py` actuellement à la racine de `tests/` ou dans des sous-répertoires comme `tests/agents/`, `tests/functional/`, `tests/orchestration/`, `tests/scripts/`, `tests/ui/`, `tests/utils/` qui n'appellent pas directement la JVM réelle devraient être déplacés ici.

2.  **`tests/integration/`**
    *   **Objectif :** Contenir les tests qui vérifient l'interaction entre plusieurs composants ou avec des systèmes externes.
    *   **Sous-catégories :**
        *   **`tests/integration/mocked_jpype/` :** Pour les tests qui simulent des scénarios d'intégration complexes avec JPype/Tweety, mais en utilisant les mocks JPype. Cela permet de tester les couches d'intégration sans la surcharge d'une JVM réelle.
        *   **`tests/integration/real_jvm/` :** **Crucial pour la clarté.** Ce répertoire contiendrait spécifiquement les tests qui *nécessitent* le démarrage d'une JVM réelle et l'interaction avec les JARs de Tweety. Actuellement, `tests/integration/jpype_tweety/` et `tests/minimal_jpype_tweety_tests/` seraient déplacés ici.
    *   **Avantages :** Sépare clairement les tests coûteux en ressources et dépendants de l'environnement, permettant de les exécuter séparément ou moins fréquemment. Facilite le diagnostic des problèmes liés à l'intégration réelle.

3.  **`tests/functional_workflows/` (Optionnel)**
    *   **Objectif :** Si des tests fonctionnels couvrent des parcours utilisateur ou des workflows de bout en bout (même avec des mocks pour les services externes), ils pourraient être regroupés ici pour une meilleure visibilité.

4.  **`tests/fixtures/`**
    *   **Objectif :** Centraliser les fixtures Pytest et les données de test partagées.

5.  **`tests/legacy_root_tests/` et `tests/corrections_appliquees/`**
    *   Ces répertoires pourraient être renommés ou leur contenu migré vers `unit/` ou `integration/` selon leur nature, puis les répertoires vides supprimés. L'objectif est de ne pas avoir de tests à la racine de `tests/` à terme.

## Avantages de cette Réorganisation :

*   **Clarté Accrue :** Les développeurs peuvent rapidement identifier le type de test et ses dépendances.
*   **Exécution Ciblée :** Permet d'exécuter des sous-ensembles de tests (ex: `pytest tests/unit/` pour un feedback rapide, `pytest tests/integration/real_jvm/` pour valider l'environnement complet).
*   **Gestion des Dépendances :** Renforce la discipline sur l'utilisation des mocks et la gestion des environnements.
*   **Documentation Implicite :** La structure elle-même documente les intentions des tests.
*   **Évolutivité :** Facilite l'ajout de nouveaux tests et de nouvelles catégories à mesure que le projet grandit.

Cette proposition vise à rendre la suite de tests plus robuste, plus facile à naviguer et à maintenir pour tous les contributeurs, en particulier les étudiants.