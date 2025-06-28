# Design Doc: Réparation des Erreurs de Type par Inférence de Hiérarchie

**Statut:** Proposition  
**Auteur:** Roo, Architecte IA  
**Date:** 2025-06-27

## 1. Contexte et Objectifs

### 1.1. Problème Actuel

L'agent `FirstOrderLogicAgent` s'appuie sur un `BeliefSetBuilderPlugin` pour transformer le langage naturel en une base de connaissances en logique du premier ordre (FOL). Ce processus, bien que robuste, est très strict. Si le LLM génère une instruction qui viole les contraintes de type — par exemple, en utilisant une constante non déclarée comme `Socrate` dans un prédicat `EstMortel(Socrate)` — le `BeliefSetBuilderPlugin` lève une `ValueError`. Cette rigidité entraîne le rejet d'informations potentiellement valides mais imparfaitement formulées, ce qui est courant avec les LLMs.

### 1.2. Solution Proposée

Ce document propose d'étendre le `FirstOrderLogicAgent` avec une fonctionnalité de **réparation de types**. Plutôt que de rejeter les formules mal typées, l'agent tentera de les corriger en se basant sur une hiérarchie de sortes (types) qu'il aura préalablement inférée.

La solution se décompose en deux mécanismes principaux :
1.  **Inférence de la hiérarchie des sortes :** Analyser les axiomes existants (en particulier les implications universelles) pour construire un graphe de relations entre les sortes (ex: `homme` est une sous-sorte de `etre_vivant`).
2.  **Processus de validation et de réparation flexible :** Utiliser cette hiérarchie pour valider les faits atomiques. Si une constante est inconnue ou si son type est un sous-type du type attendu, le système corrigera ou validera la formule au lieu de la rejeter.

## 2. Algorithme d'Inférence de la Hiérarchie

### 2.1. Heuristique d'Inférence

L'heuristique principale pour construire la hiérarchie repose sur l'analyse sémantique des implications universelles.
- **Règle :** Une formule de la forme `forall X: (Antecedent(X) => Consequent(X))` est interprétée comme une relation de subsomption. La sorte associée au prédicat `Antecedent` est considérée comme une **sous-sorte** de celle associée au prédicat `Consequent`.
- **Exemple :** Si le LLM fournit "Tous les hommes sont mortels", ce qui est traduit par `forall X: (homme(X) => mortel(X))`, notre système en déduira que `sorte(homme)` est une sous-sorte de `sorte(mortel)`.

### 2.2. Processus d'Implémentation

Le processus sera contenu dans une nouvelle méthode privée du `BeliefSetBuilderPlugin`: `_infer_sort_hierarchy()`.

1.  **Déclenchement :** Cette méthode sera appelée une seule fois depuis `FirstOrderLogicAgent.text_to_belief_set()`, juste après la boucle d'appels aux outils du LLM et avant la construction finale de l'objet Java `FolBeliefSet` via `build_tweety_belief_set()`.
2.  **Logique :** La méthode itérera sur la liste `self._universal_implications` accumulée par le plugin.
3.  Pour chaque implication `(antecedent, consequent, sort)`, elle mettra à jour la structure de données de la hiérarchie (voir section 3) pour enregistrer que la sorte de l'antécédent est une sous-sorte de celle du conséquent.

La gestion des constantes (ex: `Socrate`) n'est pas effectuée à cette étape, mais lors du processus de réparation (section 4).

## 3. Représentation des Données

### 3.1. Structure de la Hiérarchie de Sortes

Pour maintenir la simplicité et l'efficacité, la hiérarchie sera représentée par un dictionnaire stocké dans l'instance du `BeliefSetBuilderPlugin`.

```python
# Ajout à __init__ et reset() dans BeliefSetBuilderPlugin
self._sort_hierarchy: Dict[str, Set[str]] = {} 
```

- **Format :** `{ sous_sorte: {super_sorte_1, super_sorte_2, ...} }`
- **Exemple :** Après avoir traité `forall X: (homme(X) => mortel(X))` et `forall X: (grec(X) => homme(X))`, la structure serait :
  ```json
  {
    "homme": {"mortel"},
    "grec": {"homme"}
  }
  ```

### 3.2. Méthode de Vérification de Compatibilité

Une méthode auxiliaire `_is_compatible(actual_sort: str, expected_sort: str) -> bool` sera créée pour exploiter cette hiérarchie.

- **Logique :**
    1.  Retourne `True` si `actual_sort == expected_sort`.
    2.  Sinon, elle effectue une recherche en profondeur (ou en largeur) dans le graphe `_sort_hierarchy` en partant de `actual_sort` pour déterminer si `expected_sort` est l'un de ses ancêtres (super-sortes).
    3.  La recherche inclura une détection de cycle pour prévenir les boucles infinies.

## 4. Processus de Réparation des Formules

Le point d'entrée de la réparation est la méthode `add_atomic_fact()`. Sa logique de validation sera assouplie.

### 4.1. Diagramme du Flux de Réparation

```mermaid
graph TD
    A[Appel de add_atomic_fact(pred, args)] --> B{Pour chaque constante 'c' dans les args...};
    B --> C{Constante 'c' déclarée ?};
    C -- Non --> E[Réparation: Déclarer 'c' dans la sorte attendue par le prédicat];
    C -- Oui --> D{Sorte actuelle de 'c' compatible avec sorte attendue ?};
    D -- Appel --> F[_is_compatible(sorte_actuelle, sorte_attendue)];
    F -- Oui --> G[Validation de l'argument OK];
    G --> H{Tous les arguments validés?};
    H -- Oui --> I[Ajouter le fait atomique];
    F -- Non --> J[Échec: Lever ValueError];
    E --> G;
    H -- Non --> J;
```

### 4.2. Scénarios de Réparation

La logique de validation dans `add_atomic_fact` est modifiée pour gérer les cas suivants :

1.  **Scénario 1: Constante Inconnue**
    - **Situation :** `add_atomic_fact("EstMortel", ["Socrate"])` est appelé, mais la constante `socrate` n'existe dans aucune sorte.
    - **Action :** Au lieu de lever une erreur, le système identifie la sorte attendue par `EstMortel` (ex: `etre_vivant`). Il exécute alors `self.add_constant_to_sort("socrate", "etre_vivant")` en interne, ajoutant la déclaration manquante.

2.  **Scénario 2: Sorte Incompatible mais Réparable par Hiérarchie**
    - **Situation :** `Socrate` est déjà déclaré comme `homme`, et le prédicat `EstMortel` attend une sorte `etre_vivant`.
    - **Action :** La validation appelle `_is_compatible("homme", "etre_vivant")`. Grâce à la hiérarchie inférée, cette fonction retourne `True`. La validation de l'argument réussit.

3.  **Scénario 3: Incompatibilité Irréparable**
    - **Situation :** `Socrate` est de sorte `philosophe`, et `EstUnePlanete` attend `corps_celeste`. Il n'existe aucune relation hiérarchique entre `philosophe` et `corps_celeste`.
    - **Action :** `_is_compatible` retourne `False`. Le comportement actuel est conservé : une `ValueError` est levée pour signaler une incohérence logique que l'agent ne doit pas tenter de résoudre.

## 5. Intégration dans le Code Existant

### 5.1. Modifications dans `BeliefSetBuilderPlugin`

La majorité des changements sont circonscrits à cette classe :

- **`__init__()` / `reset()` :**
  - Initialiser `self._sort_hierarchy = {}`.
- **`add_atomic_fact()` :**
  - Remplacer la logique de validation stricte par le nouveau flux de réparation décrit dans la section 4.
- **`_unify_sorts()`**: 
  - Pourrait être utilisé ou étendu pour aider à construire la hiérarchie, en plus de l'analyse des implications.
- **Nouvelle méthode `_infer_sort_hierarchy()` :**
  - Contient la logique d'itération sur `self._universal_implications` pour peupler `_sort_hierarchy`.
- **Nouvelle méthode `_is_compatible()` :**
  - Implémente la traversée du graphe de hiérarchie pour la validation de type.

### 5.2. Modifications dans `FirstOrderLogicAgent`

L'impact sur la classe de l'agent est minime, ce qui préserve la séparation des préoccupations.

- **`text_to_belief_set()` :**
  - Ajouter un appel à `self._builder_plugin._infer_sort_hierarchy()` après la boucle principale d'invocation des outils et avant l'appel à `self._builder_plugin.build_tweety_belief_set()`.

```python
# Dans FirstOrderLogicAgent.text_to_belief_set()

# ... après la boucle for sur max_loops ...

self.logger.info("Le LLM a terminé d'appeler les outils. Inférence de la hiérarchie des sortes...")
# NOUVELLE LIGNE
self._builder_plugin._infer_sort_hierarchy() 

self.logger.info("Construction de l'ensemble de croyances Tweety...")
java_belief_set = self._builder_plugin.build_tweety_belief_set(self._tweety_bridge)
# ... reste de la méthode ...