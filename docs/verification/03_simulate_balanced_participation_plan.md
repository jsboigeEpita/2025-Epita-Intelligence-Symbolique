# Plan de Vérification : `simulate_balanced_participation.py`

**Date :** 21/06/2025
**Auteur :** Roo
**Statut :** En cours

## Contexte

Ce document détaille le plan de vérification pour le script `argumentation_analysis/scripts/simulate_balanced_participation.py`. L'objectif de ce script est de simuler et visualiser le comportement de la `BalancedParticipationStrategy` pour assurer une répartition équitable ou ciblée du temps de parole entre les agents conversationnels.

Ce plan est structuré en quatre phases :
1.  **Analyse (Mapping) :** Comprendre le fonctionnement interne et externe du script.
2.  **Test (Plan de Test) :** Définir des cas de tests pour valider sa fonctionnalité, sa robustesse et ses limites.
3.  **Nettoyage (Cleaning) :** Identifier les axes d'amélioration du code.
4.  **Documentation :** Lister les actions pour garantir que le code est bien documenté.

---

## Phase 1 : Analyse (Mapping)

### 1.1. Rôle et Objectifs du Script

Le script `simulate_balanced_participation.py` est un outil de simulation et non un composant de production. Ses principaux objectifs sont :
*   **Démontrer** le fonctionnement de la `BalancedParticipationStrategy`.
*   **Visualiser** la convergence des taux de participation des agents vers des cibles prédéfinies au fil du temps.
*   **Valider** que la stratégie est capable de corriger des déséquilibres, notamment ceux introduits par une désignation explicite et biaisée d'agents.

### 1.2. Logique Principale

Le script s'articule autour de la classe `ConversationSimulator` :
1.  **Initialisation :** Une instance de `ConversationSimulator` est créée avec une liste de noms d'agents. De vraies instances d'agents (`InformalAnalysisAgent`, `ExtractAgent`) sont créées, ainsi qu'un état partagé (`RhetoricalAnalysisState`).
2.  **Exécution de la simulation (`run_simulation`) :**
    *   La méthode exécute une boucle sur un nombre de tours (`num_turns`).
    *   À chaque tour, il y a une probabilité (`designation_probability`) qu'un agent soit "explicitement désigné" pour parler, suivant un biais (`designation_bias`).
    *   Indépendamment de la désignation, la `BalancedParticipationStrategy` est invoquée via `strategy.next()` pour sélectionner l'agent suivant, en tenant compte de l'historique de participation pour atteindre les cibles.
    *   Les compteurs de participation sont mis à jour.
3.  **Génération des résultats :**
    *   À la fin de la simulation, les taux de participation finaux sont affichés dans la console.
    *   Une visualisation graphique de l'évolution des taux de participation est générée avec `matplotlib`. Le graphique est sauvegardé sous `balanced_participation_simulation.png` et affiché à l'écran.

### 1.3. Interactions et Dépendances

*   **Arguments d'entrée :** Le script ne prend pas d'arguments via la ligne de commande. Toutes les configurations (nombre d'agents, cibles de participation, nombre de tours) sont codées en dur dans les fonctions `run_standard_simulation` et `run_comparison_simulation`.
*   **Sorties :**
    *   **Console :** Logs d'information sur la progression de la simulation et résultats finaux.
    *   **Fichier :** Création d'une image `argumentation_analysis/scripts/balanced_participation_simulation.png`.
    *   **GUI :** Affichage d'une fenêtre `matplotlib` avec le graphique.
*   **Dépendances critiques :**
    *   `argumentation_analysis.core.strategies.BalancedParticipationStrategy` (l'objet sous test).
    *   `argumentation_analysis.core.shared_state.RhetoricalAnalysisState`.
    *   Implémentations d'agents réels comme `InformalAnalysisAgent`.
    *   Librairies externes : `matplotlib`, `numpy`.

---

## Phase 2 : Plan de Test

Les tests seront effectués en modifiant directement le script et en l'exécutant via `powershell`.

### 2.1. Test Nominal 1 : Simulation Standard

*   **Objectif :** Valider l'exécution du script dans sa configuration par défaut.
*   **Configuration :** Aucune modification requise. Le `if __name__ == "__main__":` exécute `run_standard_simulation()`.
*   **Commande :**
    ```powershell
    python argumentation_analysis/scripts/simulate_balanced_participation.py
    ```
*   **Résultats Attendus :**
    1.  Le script se termine avec un code de sortie 0, sans aucune exception.
    2.  Les logs affichent 100 tours de simulation.
    3.  Le fichier `argumentation_analysis/scripts/balanced_participation_simulation.png` est créé.
    4.  Le graphique affiché montre les taux de participation des 3 agents qui convergent visiblement vers leurs cibles respectives (PM: 40%, PL: 30%, IA: 30%).

### 2.2. Test Nominal 2 : Simulation Comparative

*   **Objectif :** Valider le second mode de simulation du script.
*   **Configuration :** Modifier le bloc `if __name__ == "__main__":` :
    ```python
    # asyncio.run(run_standard_simulation())
    asyncio.run(run_comparison_simulation())
    ```
*   **Commande :**
    ```powershell
    python argumentation_analysis/scripts/simulate_balanced_participation.py
    ```
*   **Résultats Attendus :**
    1.  Le script se termine sans erreur.
    2.  Deux simulations sont exécutées successivement, avec des logs clairs pour chacune.
    3.  Deux graphiques sont générés et affichés, l'un après l'autre.
    4.  Le premier graphique montre une convergence vers des cibles équitables (~33% chacun).
    5.  Le second graphique montre une convergence vers des cibles où le PM est dominant (60%).

### 2.3. Test des Limites : Grand Nombre de Tours

*   **Objectif :** Évaluer la stabilité et la précision de la convergence sur une longue durée.
*   **Configuration :** Dans `run_standard_simulation`, changer `num_turns` de 100 à 1000.
    ```python
    history = await simulator.run_simulation(
        strategy,
        num_turns=1000, # Changé de 100 à 1000
        designation_probability=0.3,
        designation_bias=designation_bias
    )
    ```
*   **Commande :**
    ```powershell
    python argumentation_analysis/scripts/simulate_balanced_participation.py
    ```
*   **Résultats Attendus :**
    1.  Le script s'exécute avec succès, bien que plus lentement.
    2.  Le graphique généré montre une convergence plus lisse et des taux de participation finaux encore plus proches des cibles.

### 2.4. Test d'Erreurs 1 : Cibles de Participation Incohérentes

*   **Objectif :** Vérifier que la `BalancedParticipationStrategy` normalise correctement des cibles dont la somme n'est pas 1.0.
*   **Configuration :** Dans `run_standard_simulation`, modifier `target_participation` :
    ```python
    target_participation = {
        "ProjectManagerAgent": 0.8,     # Somme = 1.6
        "PropositionalLogicAgent": 0.4,
        "InformalAnalysisAgent": 0.4
    }
    ```
*   **Commande :**
    ```powershell
    python argumentation_analysis/scripts/simulate_balanced_participation.py
    ```
*   **Résultats Attendus :**
    1.  Le script s'exécute sans erreur.
    2.  Les cibles effectives utilisées par la stratégie devraient être normalisées (0.5, 0.25, 0.25).
    3.  Les taux de participation sur le graphique convergent vers ces valeurs normalisées.

### 2.5. Test d'Erreurs 2 : Nom d'Agent Incorrect

*   **Objectif :** Tester la robustesse face à une mauvaise configuration des cibles.
*   **Configuration :** Dans `run_standard_simulation`, introduire une faute de frappe dans le nom d'un agent :
    ```python
    target_participation = {
        "ProjectManagerAgent": 0.4,
        "PropositionalLogic_AGENT": 0.3, # Faute de frappe
        "InformalAnalysisAgent": 0.3
    }
    ```
*   **Commande :**
    ```powershell
    python argumentation_analysis/scripts/simulate_balanced_participation.py
    ```
*   **Résultats Attendus :**
    1.  Le script devrait échouer et lever une exception, idéalement une `KeyError` ou une `ValueError` au moment de l'initialisation de `BalancedParticipationStrategy`, avec un message d'erreur explicite indiquant que le nom de l'agent n'a pas été trouvé.

---

## Phase 3 : Nettoyage (Cleaning)

*   **R1 : Améliorer les imports :** Le `sys.path.append` est une solution de contournement. Le projet devrait être installable (ex: `pip install -e .`) pour permettre des imports absolus propres sans manipulation de `sys.path`.
*   **R2 : Rendre le script configurable :** Remplacer les valeurs codées en dur par des arguments en ligne de commande en utilisant le module `argparse`. Cela permettrait de changer `num_turns`, `designation_probability`, les cibles, etc., sans modifier le code, rendant le script plus flexible et réutilisable.
*   **R3 : Cohérence des objets :** Remplacer le `MagicMock` pour `ChatMessageContent` par une véritable instance de la classe. Même si son contenu est trivial, cela renforce la cohérence de la simulation et l'affirmation "PLUS AUCUN MOCK".
*   **R4 : Élégance de la réinitialisation :** Dans `run_comparison_simulation`, une nouvelle instance de `ConversationSimulator` est créée. Une méthode `simulator.reset()` qui réinitialise l'historique et l'état interne serait une alternative plus propre.

---

## Phase 4 : Documentation

*   **D1 : Compléter les Docstrings :** Bien que les docstrings soient de bonne qualité, s'assurer que tous les paramètres, en particulier `designation_bias` dans `run_simulation`, sont expliqués avec précision (ex: "Les valeurs sont des probabilités relatives qui seront normalisées").
*   **D2 : Ajouter un README pour les scripts :** Créer un fichier `docs/scripts_usage.md` qui documente les scripts utilitaires comme celui-ci. Pour ce script, il faudrait expliquer son but, comment l'exécuter, et comment interpréter le graphique de sortie.
*   **D3 : Valider le typage statique :** Lancer `mypy` sur le script pour s'assurer que toutes les annotations de type sont correctes et cohérentes, ce qui constitue une forme de documentation de code.