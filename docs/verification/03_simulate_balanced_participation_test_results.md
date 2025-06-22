# Rapport de Test : `simulate_balanced_participation.py`

**Date de vérification :** 22/06/2025

**Objectif :** Ce document résume les résultats des tests effectués sur le script `simulate_balanced_participation.py` et la stratégie sous-jacente `BalancedParticipationStrategy`, conformément au plan de vérification.

## 1. Résumé des Résultats

| Test ID | Description                                        | Statut  | Observations                                                                                             |
| :------ | :------------------------------------------------- | :------ | :------------------------------------------------------------------------------------------------------- |
| 1.1     | Exécution Nominale                                 | ✅ Passé | Le script s'est exécuté sans erreur, a produit le graphique et les taux de participation étaient corrects. |
| 2.1     | Cibles de participation ne sommant pas à 1.0       | ✅ Passé | Le script a correctement levé une `ValueError` comme attendu.                                            |
| 2.2     | Noms d'agents inconnus dans les cibles             | ✅ Passé | Le script a correctement levé une `ValueError` comme attendu.                                            |
| 3.1     | Vérification de la création du graphique           | ✅ Passé | Le fichier `balanced_participation_simulation.png` a été trouvé après l'exécution nominale.                |

**Conclusion Générale :** La vérification a été un succès complet. Le script est fonctionnel, et la stratégie `BalancedParticipationStrategy` a démontré sa robustesse face à des configurations invalides. Aucune action corrective n'a été nécessaire.

## 2. Preuves de Test Détaillées

### Test 1.1 : Exécution Nominale

*   **Commande :** `powershell -c "& {.\activate_project_env.ps1; python .\argumentation_analysis\scripts\simulate_balanced_participation.py}"`
*   **Résultat :** Le script a affiché les logs de la simulation sur 100 tours, se terminant par les résultats finaux.
    ```
    14:29:22 [INFO] [SimulationScript] === Résultats de la simulation ===
    14:29:22 [INFO] [SimulationScript] Nombre total de tours: 100
    14:29:22 [INFO] [SimulationScript] ProjectManagerAgent: 39 tours (39.00%) - Cible: 40.00%
    14:29:22 [INFO] [SimulationScript] PropositionalLogicAgent: 31 tours (31.00%) - Cible: 30.00%
    14:29:22 [INFO] [SimulationScript] InformalAnalysisAgent: 30 tours (30.00%) - Cible: 30.00%
    14:29:24 [INFO] [SimulationScript] Graphique enregistré: C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\scripts\balanced_participation_simulation.png
    ```

### Test 2.1 : Cibles de Participation Invalides (Somme > 1.0)

*   **Modification :** `target_participation["ProjectManagerAgent"]` changé à `0.5`.
*   **Résultat :** Le script a échoué comme attendu avec le traceback suivant :
    ```
    Traceback (most recent call last):
      ...
      File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\core\strategies.py", line 205, in __init__
        raise ValueError(f"La somme des participations cibles doit être 1.0, mais est de {total_participation}.")
    ValueError: La somme des participations cibles doit être 1.0, mais est de 1.1.
    ```

### Test 2.2 : Agent Inconnu

*   **Modification :** `"PropositionalLogicAgent": 0.3` remplacé par `"AgentInconnu": 0.3`.
*   **Résultat :** Le script a échoué comme attendu avec le traceback suivant :
    ```
    Traceback (most recent call last):
      ...
      File "C:\dev\2025-Epita-Intelligence-Symbolique\argumentation_analysis\core\strategies.py", line 200, in __init__
        raise ValueError(f"L'agent '{name}' défini dans target_participation est inconnu.")
    ValueError: L'agent 'AgentInconnu' défini dans target_participation est inconnu.
    ```

### Test 3.1 : Vérification du Fichier Graphique

*   **Commande :** `powershell -c "Test-Path .\argumentation_analysis\scripts\balanced_participation_simulation.png"`
*   **Résultat :**
    ```
    True