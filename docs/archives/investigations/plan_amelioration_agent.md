# Plan de Refactoring et d'Amélioration pour `FOLLogicAgent`

## 1. Introduction

Ce document présente un plan d'action détaillé pour le refactoring de l'agent `FOLLogicAgent`. Il se base sur les conclusions du `rapport_technique_fol_agent.md` et vise à intégrer les stratégies les plus efficaces qui ont été identifiées pour améliorer la robustesse, la fiabilité et la maintenabilité de l'agent.

Le principe directeur de ce refactoring est de consolider et de généraliser les approches qui ont prouvé leur efficacité : la sérialisation des objets Java, une gestion des erreurs rigoureuse, et une confiance accrue dans le LLM pour la génération de la Logique du Premier Ordre (FOL) via une ingénierie de prompt avancée.

## 2. Feuille de Route du Refactoring

Le refactoring sera mené en quatre étapes séquentielles et interdépendantes.

---

### Étape 1 : Généralisation de la Sérialisation des Objets Java

**Objectif :** Standardiser l'utilisation de la sérialisation/désérialisation JSON pour tous les objets `FolBeliefSet`. Cette approche supprime la nécessité de maintenir des références directes à des objets Java en mémoire Python, ce qui a été identifié comme une source majeure d'instabilité et de fuites de mémoire.

**Fichiers à modifier :**

*   [`argumentation_analysis/agents/core/logic/first_order_logic_agent.py`](argumentation_analysis/agents/core/logic/first_order_logic_agent.py)
*   [`argumentation_analysis/agents/core/logic/fol_handler.py`](argumentation_analysis/agents/core/logic/fol_handler.py)
*   [`argumentation_analysis/agents/core/logic/belief_set.py`](argumentation_analysis/agents/core/logic/belief_set.py)

**Description des changements :**

1.  **`first_order_logic_agent.py`**:
    *   Rendre le paramètre `use_serialization` non optionnel et le fixer à `True` par défaut dans le `__init__`. L'ancienne approche sans sérialisation sera considérée comme obsolète.
    *   Auditer toutes les méthodes manipulant un `FirstOrderBeliefSet` pour garantir qu'elles utilisent systématiquement la méthode `_recreate_java_belief_set` avant toute interaction avec la couche Java.
    *   Aucun attribut d'instance ne doit conserver un objet `jpype` vivant après une opération.

2.  **`fol_handler.py`**:
    *   La méthode `create_and_serialize_belief_set` devient la méthode standard pour la création.
    *   Toute autre méthode retournant un `FolBeliefSet` doit s'assurer qu'il est correctement sérialisé et que l'objet Java sous-jacent est libéré.

**Validation de l'étape :**

*   Les tests d'intégration existants dans [`tests/integration/workers/test_worker_fol_tweety.py`](tests/integration/workers/test_worker_fol_tweety.py) seront adaptés.
*   La fixture `use_serialization` sera modifiée pour forcer la valeur à `True`, ou les tests ne passant pas avec la sérialisation seront corrigés ou supprimés.
*   Des tests de charge (si possible) pourraient être envisagés pour confirmer la stabilité de la mémoire sur un grand nombre d'opérations.

---

### Étape 2 : Blindage des Interactions avec TweetyProject

**Objectif :** Rendre l'agent résilient aux erreurs potentielles levées par la bibliothèque Java sous-jacente. Une défaillance dans la création d'une signature ou l'ajout d'une formule ne doit pas faire planter l'agent mais être capturée, loguée et gérée proprement.

**Fichiers à modifier :**

*   [`argumentation_analysis/agents/core/logic/fol_handler.py`](argumentation_analysis/agents/core/logic/fol_handler.py)

**Description des changements :**

1.  **`fol_handler.py`**:
    *   Effectuer un audit complet de toutes les méthodes interagissant avec `jpype`.
    *   Envelopper chaque appel potentiellement risqué (ex: `signature.add()`, `beliefSet.add()`, les appels de parsing) dans un bloc `try...except jpype.JException as e`.
    *   En cas d'exception, la méthode doit :
        *   Logger l'erreur de manière détaillée (la formule ou l'élément qui a causé le problème et l'exception Java).
        *   Retourner une valeur indiquant l'échec (par exemple, `None` ou un objet `Result` dédié) au lieu de laisser l'exception se propager.

**Validation de l'étape :**

*   Créer de nouveaux tests unitaires/d'intégration dans [`tests/agents/core/logic/test_fol_handler_fix.py`](tests/agents/core/logic/test_fol_handler_fix.py) qui injectent délibérément des données invalides (e.g., un prédicat mal formé, une constante déjà définie) et vérifient que :
    *   Le `fol_handler` ne lève pas d'exception.
    *   Une erreur est correctement loguée.
    *   La valeur de retour signale bien l'échec.

---

### Étape 3 : Consolidation de l'Approche "LLM-Centrique"

**Objectif :** Acter définitivement que la qualité de la FOL est sous la responsabilité du LLM. Ceci implique d'affiner le prompt pour qu'il soit le plus directif possible et de supprimer toute logique de correction palliative en code Python.

**Fichiers à modifier :**

*   [`argumentation_analysis/agents/core/logic/first_order_logic_agent.py`](argumentation_analysis/agents/core/logic/first_order_logic_agent.py)

**Description des changements :**

1.  **Prompt Engineering**:
    *   Isoler le `PROMPT_TEXT_TO_UNIFIED_FOL` dans un fichier de template dédié (par exemple, `prompts/fol_generation.txt`) pour une meilleure lisibilité et maintenance.
    *   Réviser le prompt pour le rendre encore plus strict, en insistant sur la **Règle d'or de la cohérence des types** et en ajoutant potentiellement des exemples "one-shot" ou "few-shot" directement dans le prompt.

2.  **Simplification du code**:
    *   Supprimer définitivement la méthode `_normalize_logical_structure` ou la réduire à une simple validation de la présence des clés attendues dans le JSON (`sorts`, `predicates`, etc.). Toute logique de "réparation" des types ou des noms doit être retirée.
    *   Améliorer la robustesse de `_extract_json_block` pour gérer les cas où le JSON est précédé ou suivi de texte explicatif généré par le LLM.

**Validation de l'étape :**

*   Les tests existants doivent continuer de passer, prouvant que le LLM, avec le prompt amélioré, est capable de générer une sortie correcte sans aide du code Python.
*   Créer de nouveaux tests avec des textes d'entrée ambigus ou complexes pour vérifier que le prompt est suffisamment robuste pour guider le LLM vers la bonne structure FOL.
*   Tester spécifiquement la fonction `_extract_json_block` avec des chaînes de caractères simulant des réponses LLM imparfaites.

---

### Étape 4 : Adaptation et Renforcement de la Suite de Tests

**Objectif :** Mettre à jour l'ensemble des tests pour qu'ils reflètent l'architecture cible et valident toutes les améliorations de robustesse apportées.

**Fichiers à modifier :**

*   [`tests/integration/workers/test_worker_fol_tweety.py`](tests/integration/workers/test_worker_fol_tweety.py)
*   [`tests/agents/core/logic/test_fol_handler_fix.py`](tests/agents/core/logic/test_fol_handler_fix.py)

**Description des changements :**

1.  **Correction Asynchrone**:
    *   Faire un audit final pour s'assurer qu'absolument tous les appels de méthodes `async` sont correctement précédés du mot-clé `await`.

2.  **Alignement avec le Refactoring**:
    *   Mettre à jour les mocks (`AsyncMock`) pour correspondre aux nouvelles signatures de méthodes et aux comportements attendus (par exemple, retourner `None` en cas d'erreur de `fol_handler`).
    *   Les tests doivent se concentrer sur la validation du comportement de l'agent avec la sérialisation activée.

**Validation de l'étape :**

*   L'intégralité de la suite de tests doit passer avec succès.
*   Le "coverage" des tests doit être maintenu ou amélioré, en particulier sur les nouvelles logiques de gestion d'erreur.