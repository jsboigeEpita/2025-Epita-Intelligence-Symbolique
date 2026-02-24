# Pont Tweety (Tweety Bridge)

## 1. Introduction

Ce document décrit le composant `TweetyBridge`, situé dans [`argumentation_analysis/agents/core/logic/tweety_bridge.py`](../../argumentation_analysis/agents/core/logic/tweety_bridge.py:1). Ce pont sert d'interface principale entre l'environnement Python du projet et les bibliothèques Java de TweetyProject, permettant d'exploiter les capacités de raisonnement formel de Tweety.

## 2. Rôle et Objectifs

Le `TweetyBridge` a pour objectifs principaux de :
*   Encapsuler la complexité de l'interaction avec la JVM et les bibliothèques Java via `jpype`.
*   Fournir une API Python claire pour accéder aux fonctionnalités de Tweety.
*   Gérer l'initialisation de la JVM et le chargement des classes Tweety nécessaires (en s'appuyant sur [`argumentation_analysis/core/jvm_setup.py`](../../argumentation_analysis/core/jvm_setup.py:1)).
*   Permettre le parsing de formules et de bases de croyances pour différentes logiques.
*   Exécuter des requêtes logiques (inférence, validation) en utilisant les raisonneurs de Tweety.
*   Convertir les types de données entre Python et Java.

## 3. Architecture et Composants Clés

### 3.1. Initialisation de la JVM
Le `TweetyBridge` s'assure que la JVM est démarrée et correctement configurée avec les JARs de Tweety. Il utilise les fonctions de [`argumentation_analysis/core/jvm_setup.py`](../../argumentation_analysis/core/jvm_setup.py:1) pour cela.

### 3.2. Chargement des Classes Tweety
Lors de son initialisation, le pont charge dynamiquement les classes Java requises de TweetyProject pour :
*   **Logique Propositionnelle (PL) :**
    *   `org.tweetyproject.logics.pl.parser.PlParser`
    *   `org.tweetyproject.logics.pl.reasoner.SatReasoner`
    *   `org.tweetyproject.logics.pl.syntax.PlFormula`
*   **Logique du Premier Ordre (FOL) :**
    *   `org.tweetyproject.logics.fol.parser.FolParser`
    *   `org.tweetyproject.logics.fol.reasoner.SimpleFolReasoner`
    *   `org.tweetyproject.logics.fol.syntax.FolFormula`
*   **Logique Modale (ML) :**
    *   `org.tweetyproject.logics.ml.parser.MlParser`
    *   `org.tweetyproject.logics.ml.reasoner.SimpleMlReasoner`
    *   `org.tweetyproject.logics.ml.syntax.MlFormula`

### 3.3. Instances des Parsers et Raisonneurs
Des instances de ces classes Java sont maintenues par le `TweetyBridge` pour être réutilisées.

## 4. Fonctionnalités Principales

Le `TweetyBridge` expose des méthodes pour :

### 4.1. Validation Syntaxique
*   `validate_formula(formula_string: str) -> Tuple[bool, str]`: Valide une formule de logique propositionnelle.
*   `validate_belief_set(belief_set_string: str) -> Tuple[bool, str]`: Valide un ensemble de croyances en logique propositionnelle.
*   `validate_fol_formula(formula_string: str) -> Tuple[bool, str]`: Valide une formule FOL.
*   `validate_fol_belief_set(belief_set_string: str) -> Tuple[bool, str]`: Valide un ensemble de croyances FOL.
*   `validate_modal_formula(formula_string: str) -> Tuple[bool, str]`: Valide une formule modale.
*   `validate_modal_belief_set(belief_set_string: str) -> Tuple[bool, str]`: Valide un ensemble de croyances modales.

### 4.2. Exécution de Requêtes Logiques
Ces méthodes sont également exposées comme `kernel_function` pour une intégration facilitée avec Semantic Kernel.
*   `execute_pl_query(belief_set_content: str, query_string: str) -> str`: Exécute une requête en logique propositionnelle.
*   `execute_fol_query(belief_set_content: str, query_string: str) -> str`: Exécute une requête en logique du premier ordre.
*   `execute_modal_query(belief_set_content: str, query_string: str) -> str`: Exécute une requête en logique modale.

### 4.3. Méthodes Internes de Parsing et d'Exécution
Le pont utilise des méthodes internes (préfixées par `_parse_...` et `_execute_..._internal`) pour gérer la conversion des chaînes de caractères en objets Java Tweety et pour interagir avec les raisonneurs.

## 5. Interaction avec d'Autres Composants

*   **Agent de Logique / `PropositionalLogicAgent` :** Ces agents utilisent le `TweetyBridge` pour effectuer des analyses logiques formelles. (Voir [`docs/composants/reasoning_engine.md`](./reasoning_engine.md)).
*   **`jvm_setup.py` :** Le `TweetyBridge` s'appuie sur [`argumentation_analysis/core/jvm_setup.py`](../../argumentation_analysis/core/jvm_setup.py:1) pour la gestion de bas niveau de la JVM.

## 6. Syntaxe des Formules et Ensembles de Croyances

Il est crucial de respecter la syntaxe attendue par TweetyProject pour les formules et les ensembles de croyances.
*   **Logique Propositionnelle :**
    *   Négation : `!`
    *   Conjonction : `&&` (ou `&`)
    *   Disjonction : `||` (ou `|`)
    *   Implication : `=>`
    *   Équivalence : `<=>`
    *   XOR : `^^`
    *   Constantes : `true`, `false`
    *   Variables propositionnelles : `a, b, prop1, ...`
*   **Logique du Premier Ordre :**
    *   Quantificateurs : `forall X: (formula)`, `exists X: (formula)`
    *   Prédicats : `P(X,y)`
    *   Connecteurs : similaires à PL.
*   **Logique Modale :**
    *   Opérateur de nécessité (Box) : `[]` ou `Box`
    *   Opérateur de possibilité (Diamond) : `<>` ou `Diamond`
    *   Connecteurs : similaires à PL.

Les ensembles de croyances sont typiquement une liste de formules, chacune sur une nouvelle ligne. Les commentaires peuvent être introduits par `#`.

## 7. Limitations et Développements Futurs

*   Actuellement, le `TweetyBridge` se concentre sur PL, FOL et ML. D'autres logiques ou fonctionnalités de Tweety (ex: argumentation abstraite, révision de croyances) pourraient être intégrées.
*   La gestion des erreurs pourrait être affinée pour fournir des diagnostics plus précis.
*   Des optimisations de performance pour des requêtes complexes ou de grandes bases de croyances pourraient être explorées.