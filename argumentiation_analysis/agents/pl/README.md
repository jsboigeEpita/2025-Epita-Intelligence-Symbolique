# 📐 Propositional Logic Agent (`agents/pl/`)

Agent spécialisé dans l'analyse logique formelle (Logique Propositionnelle - PL) utilisant la bibliothèque Java [TweetyProject](https://tweetyproject.org/) via [JPype](https://jpype.readthedocs.io/).

[Retour au README Agents](../README.md)

**Prérequis Spécifique :** 🔥☕ Le bon fonctionnement de cet agent dépend crucialement d'une **JVM initialisée correctement** via `core.jvm_setup.initialize_jvm()` (qui nécessite un JDK >= 11 et `JAVA_HOME` configuré).

## Rôle ⚙️

* **Formaliser :** Traduire des extraits de texte ou des arguments (fournis par le PM) en un "Belief Set" PL (ensemble de formules logiques) en utilisant `PLAnalyzer.semantic_TextToPLBeliefSet`. Le résultat doit respecter la **syntaxe stricte** de Tweety et est enregistré via `StateManager.add_belief_set`.
* **Interroger :**
    * Générer des requêtes logiques PL pertinentes (syntaxe Tweety) pour un belief set donné via `PLAnalyzer.semantic_GeneratePLQueries`.
    * Exécuter ces requêtes sur le belief set via la fonction native `PLAnalyzer.execute_pl_query`. Cette fonction interagit avec le `SatReasoner` de Tweety (via JPype) pour déterminer si la requête est une conséquence logique du belief set.
    * Enregistrer chaque requête et son résultat brut (ACCEPTED/REJECTED/Unknown) via `StateManager.log_query_result`.
* **Interpréter :** Traduire les résultats bruts des requêtes Tweety en langage naturel compréhensible via `PLAnalyzer.semantic_InterpretPLResult`, en expliquant le raisonnement basé sur le belief set.
* **Répondre** aux tâches assignées par le PM via `StateManager.add_answer`.

**Syntaxe Cruciale (BNF Tweety) :** ✍️
L'agent LLM doit générer des Belief Sets et des Requêtes conformes à la BNF suivante. Il est **impératif d'utiliser les opérateurs `!`, `||`, `=>`, `<=>`, `^^`** et d'éviter `>>` et `&&`. Les formules dans un Belief Set sont séparées par `\n`.

```bnf
FORMULASET ::== FORMULA ( "\\n" FORMULA )*
FORMULA ::== PROPOSITION | "(" FORMULA ")" | FORMULA ">>" FORMULA |
             FORMULA "||" FORMULA | FORMULA "=>" FORMULA | FORMULA "<=>" FORMULA |
             FORMULA "^^" FORMULA | "!" FORMULA | "+" | "-"
PROPOSITION is a sequence of characters excluding |,&,!,(),=,<,> and whitespace.

## Composants 🛠️

  * **[`pl_definitions.py`](https://www.google.com/search?q=./pl_definitions.py)** :
      * `PropositionalLogicPlugin`: Classe gérant l'interface JPype \<-\> Tweety. Elle charge les classes Java (`PlParser`, `SatReasoner`, `PlFormula`), contient la logique de parsing et d'exécution des requêtes, et expose la fonction native `execute_pl_query`. Gère l'état d'initialisation de ses composants Java.
      * `setup_pl_kernel`: Configure le kernel SK. Vérifie si la JVM est prête avant d'ajouter le plugin.
      * `PL_AGENT_INSTRUCTIONS`: Instructions système très détaillées, incluant le rappel de la syntaxe et les workflows pour chaque tâche.
  * **[`prompts.py`](https://www.google.com/search?q=./prompts.py)** :
      * `prompt_text_to_pl_v*`: Traduction Texte -\> Belief Set PL.
      * `prompt_gen_pl_queries_v*`: Génération de requêtes PL.
      * `prompt_interpret_pl_v*`: Interprétation des résultats Tweety.