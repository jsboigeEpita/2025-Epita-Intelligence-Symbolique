# Plan de Vérification : `unified_production_analyzer.py`

**Objectif :** Valider le workflow complet du script `project_core/rhetorical_analysis_from_scripts/unified_production_analyzer.py`.

## 1. Test de Base

*   **Description :** Exécuter le script avec un texte simple et les paramètres par défaut pour valider qu'il se termine sans erreur et génère un rapport.
*   **Commande :**
    ```powershell
    ./activate_project_env.ps1; python project_core/rhetorical_analysis_from_scripts/unified_production_analyzer.py "Ceci est un test."
    ```
*   **Validation :**
    *   Le script se termine avec un code de sortie 0.
    *   Un fichier de rapport JSON est créé dans le répertoire `reports/`.
    *   Le rapport contient une analyse réussie.

## 2. Test de la Génération (Analyse)

*   **Description :** Vérifier que la phase d'analyse produit des données non vides et correctement formatées.
*   **Commande :**
    ```powershell
    ./activate_project_env.ps1; python project_core/rhetorical_analysis_from_scripts/unified_production_analyzer.py "Les LLMs sont des outils puissants, mais ils peuvent parfois halluciner." --analysis-modes fallacies coherence
    ```
*   **Validation :**
    *   Le rapport de sortie contient des sections pour `fallacies` et `coherence`.
    *   Les résultats de l'analyse ne sont pas vides.
    *   La structure des résultats est conforme à ce qui est attendu.

## 3. Test de la Gestion d'Erreur (Entrée Manquante)

*   **Description :** Valider que le script gère correctement l'absence de fichier d'entrée.
*   **Commande :**
    ```powershell
    ./activate_project_env.ps1; python project_core/rhetorical_analysis_from_scripts/unified_production_analyzer.py "un_fichier_qui_n_existe_pas.txt"
    ```
*   **Validation :**
    *   Le script se termine avec un code de sortie non nul.
    *   Un message d'erreur clair est affiché, indiquant que l'entrée est invalide.

## 4. Test d'Analyse en Mode Batch

*   **Description :** Vérifier le fonctionnement du mode batch sur un répertoire de fichiers texte.
*   **Prérequis :** Créer un répertoire `temp_test_batch` contenant deux fichiers `.txt`.
*   **Commandes :**
    ```powershell
    New-Item -ItemType Directory -Path temp_test_batch
    Set-Content -Path temp_test_batch/test1.txt -Value "Premier argument pour le test batch."
    Set-Content -Path temp_test_batch/test2.txt -Value "Deuxième argument pour le test batch."
    ./activate_project_env.ps1; python project_core/rhetorical_analysis_from_scripts/unified_production_analyzer.py temp_test_batch --batch
    ```
*   **Validation :**
    *   Le script traite les deux fichiers.
    *   Le rapport final contient les résultats des deux analyses.
    *   Le répertoire `temp_test_batch` est supprimé après le test.