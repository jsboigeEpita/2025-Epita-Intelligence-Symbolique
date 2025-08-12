# ADR 0001 : Mise à niveau de Semantic-Kernel et refonte du prompt de l'agent d'analyse de sophismes

**Date** : 2025-08-12

**Statut** : Accepté

## Contexte

Le projet dépend de la bibliothèque `semantic-kernel` pour orchestrer les agents basés sur des LLMs. Une mise à jour majeure de la bibliothèque (v1.5.0) a introduit des changements cassants (`breaking changes`) dans son API, rendant notre implémentation existante de `InformalFallacyAgent` obsolète.

L'objectif initial était de mettre à jour le code pour qu'il soit compatible avec la nouvelle API, tout en s'assurant qu'il n'y ait pas de régression fonctionnelle via un script de validation (`demos/validation_complete_epita.py`).

## Décision

Après plusieurs itérations de débogage et de tests, deux changements majeurs ont été implémentés :

1.  **Mise à jour du code de l'agent** : Le code dans `argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py` a été modifié pour utiliser les nouveaux patrons de conception de `semantic-kernel` v1.5.0. La création et l'invocation de fonctions à partir de prompts se font désormais en instanciant `KernelFunctionFromPrompt` et en l'invoquant via `kernel.invoke()`.

2.  **Simplification radicale du prompt** : Les tentatives initiales pour faire fonctionner l'agent avec des prompts complexes simulant une chaîne de pensée ("Chain of Thought") ont échoué. Le modèle ne parvenait pas à respecter le format de sortie attendu. La solution a été de simplifier radicalement le prompt dans `argumentation_analysis/agents/prompts/InformalFallacyAgent/skprompt.txt`. Le nouveau prompt est plus direct, se concentre sur la tâche et le format de sortie, et s'appuie sur des exemples "input/output" clairs plutôt que sur une simulation du raisonnement.

## Conséquences

**Positives** :
- Le code est maintenant compatible avec la dernière version stable de `semantic-kernel`.
- La régression fonctionnelle a été corrigée, et les tests de validation passent avec succès pour la majorité des cas.
- Le prompt final est plus simple, plus maintenable et plus aligné avec les bonnes pratiques d'utilisation de `semantic-kernel`.

**Négatives** :
- Un test (`Argument par le Scénario`) échoue encore sur le plan sémantique (mauvaise classification), mais cela est considéré comme un problème de performance du modèle et non un bug technique bloquant.
- Le processus de débogage a été itératif et a nécessité de multiples ajustements du prompt.