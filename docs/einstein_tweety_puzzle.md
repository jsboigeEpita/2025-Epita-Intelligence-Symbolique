# Documentation : Résolution de l'Énigme d'Einstein avec Tweety

Ce document décrit comment utiliser le système pour résoudre l'énigme de logique connue sous le nom d'énigme d'Einstein. Cette tâche met en évidence l'intégration avec le solveur de logique formelle **TweetyProject** pour déduire la solution à partir d'un ensemble de contraintes.

## 1. Contexte

Contrairement à l'enquête Cluedo qui repose sur un raisonnement en langage naturel et une analyse de corpus, l'énigme d'Einstein est un pur problème de logique. Le système utilise des agents spécialisés qui traduisent les règles de l'énigme en expressions logiques formelles, puis exploitent la puissance de TweetyProject pour explorer l'espace des solutions et trouver la réponse.

L'objectif de cette démonstration est de valider la capacité du système à :
-   Comprendre et formaliser des contraintes logiques complexes.
-   Interagir correctement avec une bibliothèque Java externe (Tweety) via le pont JPype.
-   Utiliser un raisonneur logique pour résoudre une énigme non triviale.

## 2. Script Principal

Le script principal pour cette tâche est `scripts/sherlock_watson/run_unified_investigation.py`. C'est le même script que pour l'enquête Cluedo, mais configuré pour exécuter un workflow différent.

## 3. Comment Lancer la Résolution

Pour lancer la résolution de l'énigme d'Einstein, exécutez la commande suivante depuis la racine du projet :

```bash
python scripts/sherlock_watson/run_unified_investigation.py --workflow einstein
```

### Arguments Clés :

-   `--workflow einstein` : (Obligatoire) Spécifie que nous voulons exécuter le scénario de l'énigme d'Einstein.

Le script ne prend pas d'arguments pour le nom ou l'emplacement du fichier de sortie. Les résultats sont sauvegardés automatiquement.

### Sauvegarde des Résultats

Les traces et les résultats de l'exécution sont automatiquement sauvegardés dans un sous-répertoire unique au sein de `results/unified_investigation/`. Le nom du fichier de résultat sera formaté comme suit : `result_einstein_[session_id].json`.

### Fonctionnement Interne :

1.  **Initialisation** : Le script initialise un environnement avec des agents spécialisés dans la logique.
2.  **Formalisation** : Les agents lisent les règles de l'énigme et les convertissent en une base de connaissance formelle.
3.  **Invocation de Tweety** : Le `WatsonLogicAssistant` (configuré pour utiliser Tweety) envoie des requêtes au solveur pour tester des hypothèses et déduire de nouvelles informations.
4.  **Génération de la Trace** : Chaque étape du raisonnement, y compris les appels à Tweety et les déductions logiques, est enregistrée dans le fichier de trace de sortie.

## 4. Génération de la Trace de Démonstration

Pour générer une trace de démonstration, nous allons exécuter la commande simple mentionnée ci-dessus. Cette trace, enregistrée dans un fichier JSON, montrera le processus de pensée des agents et leur utilisation de la logique formelle.