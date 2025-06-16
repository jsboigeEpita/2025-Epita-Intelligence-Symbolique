## Plan de Refactoring Détaillé pour `jpype_mock.py`

### 1. Nouvelle Structure de Fichiers Proposée

Un nouveau répertoire `tests/mocks/jpype_components/` sera créé pour organiser les différents modules du mock. Le fichier `tests/mocks/jpype_mock.py` actuel servira de point d'entrée principal, important les composants nécessaires.

```
tests/
└── mocks/
    ├── jpype_mock.py  (Fichier principal allégé)
    ├── jpype_components/
    │   ├── __init__.py
    │   ├── jvm.py             (Gestion de la JVM)
    │   ├── config.py          (Mock de jpype.config)
    │   ├── imports.py         (Mock de jpype.imports)
    │   ├── types.py           (Mocks des types JPype de base: JString, JArray, JObject, etc.)
    │   ├── exceptions.py      (Mocks des exceptions JPype)
    │   ├── collections.py     (MockJavaCollection, _ModuleLevelMockJavaIterator)
    │   ├── jclass_core.py     (MockJClass de base)
    │   ├── tweety_enums.py    (Mocks pour les Enums Tweety)
    │   ├── tweety_syntax.py   (Mocks pour syntaxe Tweety: Argument, Attack, Formules, Parsers)
    │   ├── tweety_theories.py (Mocks pour DungTheory, etc.)
    │   ├── tweety_reasoners.py(Mocks pour Reasoners Tweety)
    │   └── tweety_agents.py   (Mocks pour agents et protocoles Tweety)
    └── ... (autres mocks)
```

### 2. Stratégie de Découpage et Contenu des Nouveaux Fichiers

*   **`tests/mocks/jpype_mock.py` (Allégé) :**
    *   Initialisation du mock, variables globales (`_jvm_started`, `_jvm_path`), exposition des fonctions et classes principales par imports depuis `jpype_components`. `MockJavaNamespace` et `_MockInternalJpypeModule` y restent.

*   **`tests/mocks/jpype_components/jvm.py` :**
    *   Logique de simulation de la JVM : `isJVMStarted()`, `startJVM()`, `shutdownJVM()`, `getDefaultJVMPath()`, `getJVMPath()`, `getJVMVersion()`, `getClassPath()`.

*   **`tests/mocks/jpype_components/config.py` :**
    *   `MockConfig` et instance `config`.

*   **`tests/mocks/jpype_components/imports.py` :**
    *   `MockJpypeImports`, instance `imports`, et patch `sys.modules['jpype.imports']`.

*   **`tests/mocks/jpype_components/types.py` :**
    *   `JString()`, `JArray()`, `JObject`, `JBoolean()`, `JInt()`, `JDouble()`, etc.

*   **`tests/mocks/jpype_components/exceptions.py` :**
    *   `JException`, `JVMNotFoundException`.

*   **`tests/mocks/jpype_components/collections.py` :**
    *   `MockJavaCollection`, `_ModuleLevelMockJavaIterator`.

*   **`tests/mocks/jpype_components/jclass_core.py` :**
    *   `MockJClassCore` (anciennement `MockJClass`) : initialisation de base, `__getattr__` générique, `__call__` générique (retournant `MagicMock` ou `MockJavaCollection`), `equals()`/`hashCode()` par défaut, logique `java.lang.ClassLoader.getSystemClassLoader()`.

*   **`tests/mocks/jpype_components/tweety_enums.py` :**
    *   Configuration des attributs statiques pour les enums Tweety (ex: `OpponentModel.SIMPLE`, `Quantifier.EXISTS`) sur les instances `MockJClassCore`.

*   **`tests/mocks/jpype_components/tweety_syntax.py` :**
    *   Configuration de `MockJClassCore` pour `Argument`, `Attack` (logique `equals()`, `hashCode()`, `getName()`, etc.).
    *   Logique pour parsers de formules (`PlParser`, `FolParser`, `QbfParser`) et `parseFormula()`.
    *   Logique pour `QuantifiedBooleanFormula` (`getQuantifier`, `getVariables`).

*   **`tests/mocks/jpype_components/tweety_theories.py` :**
    *   Configuration de `MockJClassCore` pour `DungTheory`.
    *   Logique d'initialisation, `add()`, `contains()`, `isAttackedBy()`, `getNodes()`, `getAttacks()` pour `DungTheory`.

*   **`tests/mocks/jpype_components/tweety_reasoners.py` :**
    *   Configuration de `MockJClassCore` pour les `Reasoner`.
    *   Logique spécifique (calcul d'extensions) pour `CompleteReasoner`, `StableReasoner`, `PreferredReasoner`, `GroundedReasoner`.
    *   Helpers d'argumentation (ex: `is_admissible_set_helper`).

*   **`tests/mocks/jpype_components/tweety_agents.py` :**
    *   Logique pour `InconsistencyMeasure`, `PersuasionProtocol`, `ArgumentationAgent`.

### 3. Mocks à Simplifier ou Supprimer

Avec un JPype fonctionnel, l'objectif est d'utiliser les vraies classes Java.

*   **À Supprimer/Simplifier Drastiquement :**
    1.  **Logique de sémantique d'argumentation dans `tweety_reasoners.py`** (calculs d'extensions, helpers `is_admissible_set_helper`, etc.) : Les tests utiliseront les vrais reasoners Java. Les mocks de reasoners, s'ils sont conservés pour des tests unitaires très spécifiques, ne simuleront plus ces calculs.
    2.  **Logique détaillée de `DungTheory` (`add`, `contains`, `isAttackedBy`) dans `tweety_theories.py`** : Les tests utiliseront la vraie `DungTheory` Java.
    3.  **Logique `equals()`/`hashCode()` détaillée pour `Argument`, `Attack` dans `tweety_syntax.py`** : Les objets Java auront leurs propres méthodes.
    4.  **Logique de `parseFormula()` retournant des mocks de formules complexes dans `tweety_syntax.py`** : Les vrais parsers Java seront utilisés.
    5.  **`MockJavaCollection` et `_ModuleLevelMockJavaIterator` (en grande partie)** : JPype gère bien les collections Java. Pourrait être simplifié si un mock de collection est encore nécessaire.
    6.  **Mocks d'enums dans `tweety_enums.py`** : Accès direct aux vrais enums Java.

*   **À Conserver (potentiellement simplifié) :**
    *   Le framework de base du mock JPype (`jvm.py`, `config.py`, `imports.py`, `types.py`, `exceptions.py`, `jclass_core.py`).
    *   `MockJavaNamespace` pour simuler `jpype.java.package.Class`.

### 4. Gestion des Interdépendances

*   Utilisation d'imports Python standards entre les modules de `jpype_components/`.
*   Le `JClass()` principal (dans `jpype_mock.py`) instanciera `MockJClassCore` et appliquera dynamiquement des configurations spécifiques à Tweety importées des modules `tweety_*.py` en fonction du nom de la classe demandée.

### 5. Objectifs du Plan

*   **Maintenabilité et Lisibilité Accrues :** Code mieux organisé et plus facile à comprendre.
*   **Réduction de la Duplication :** Moins de logique Java réimplémentée en Python.
*   **Facilitation de la Transition :** Permet de désactiver progressivement les mocks Tweety au profit des classes Java réelles.

Ce plan vise à rendre les mocks plus ciblés sur la simulation de l'interface JPype elle-même, plutôt que de réimplémenter des pans entiers de la logique de Tweety, ce qui deviendra inutile avec un environnement JPype fonctionnel.