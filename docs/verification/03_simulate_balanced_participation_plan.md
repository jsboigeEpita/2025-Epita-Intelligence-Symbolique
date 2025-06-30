# Plan de Vérification : `simulate_balanced_participation.py`

**Objectif :** Valider le comportement du script de simulation et de la stratégie `BalancedParticipationStrategy`, en particulier la robustesse de ses entrées et la génération correcte des sorties.

## 1. Tests Fonctionnels

### Test 1.1 : Exécution Nominale

*   **Description :** Exécuter le script sans modification pour s'assurer qu'il fonctionne dans sa configuration par défaut.
*   **Commande :**
    ```powershell
    .\activate_project_env.ps1; python ./argumentation_analysis/scripts/simulate_balanced_participation.py
    ```
*   **Résultat Attendu :**
    *   Le script s'exécute jusqu'au bout sans erreur.
    *   Un graphique nommé `balanced_participation_simulation.png` est généré dans le répertoire `argumentation_analysis/scripts/`.
    *   La sortie console affiche les taux de participation finaux qui convergent vers les cibles définies (0.4, 0.3, 0.3).

## 2. Tests de Robustesse (Validation des Entrées)

Ces tests seront menés en modifiant temporairement le script `simulate_balanced_participation.py` pour initialiser la stratégie avec des données invalides.

### Test 2.1 : Cibles de Participation ne sommant pas à 1.0

*   **Description :** Vérifier que la stratégie lève une `ValueError` si les cibles de participation ne totalisent pas 1.0.
*   **Modification du script (`run_standard_simulation`) :**
    ```python
    target_participation = {
        "ProjectManagerAgent": 0.5, # 0.5 + 0.3 + 0.3 = 1.1
        "PropositionalLogicAgent": 0.3,
        "InformalAnalysisAgent": 0.3
    }
    ```
*   **Commande :**
    ```powershell
    .\activate_project_env.ps1; python ./argumentation_analysis/scripts/simulate_balanced_participation.py
    ```
*   **Résultat Attendu :** Le script doit s'arrêter et lever une `ValueError` avec un message indiquant que la somme des participations n'est pas 1.0.

### Test 2.2 : Noms d'Agents Inconnus dans les Cibles

*   **Description :** S'assurer qu'une `ValueError` est levée si un nom d'agent dans `target_participation` n'existe pas dans la liste des agents.
*   **Modification du script (`run_standard_simulation`) :**
    ```python
    target_participation = {
        "ProjectManagerAgent": 0.4,
        "AgentInconnu": 0.3, # Ce nom n'existe pas
        "InformalAnalysisAgent": 0.3
    }
    ```
*   **Commande :**
    ```powershell
    .\activate_project_env.ps1; python ./argumentation_analysis/scripts/simulate_balanced_participation.py
    ```
*   **Résultat Attendu :** Le script doit s'arrêter et lever une `ValueError` avec un message indiquant que "AgentInconnu" est un agent inconnu.

## 3. Validation des Sorties

### Test 3.1 : Vérification de la Création du Graphique

*   **Description :** Confirmer que l'artefact visuel (le graphique) est bien créé.
*   **Action :** Après l'exécution réussie du Test 1.1, vérifier la présence du fichier `argumentation_analysis/scripts/balanced_participation_simulation.png`.
*   **Commande (pour vérification) :**
    ```powershell
    Test-Path ./argumentation_analysis/scripts/balanced_participation_simulation.png
    ```
*   **Résultat Attendu :** La commande retourne `True`.