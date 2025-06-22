# Plan de Vérification : `orchestrate_complex_analysis.py`

**Objectif :** Valider le fonctionnement autonome, la robustesse et la génération de rapports du script `scripts/orchestration/orchestrate_complex_analysis.py`.

## 1. Test de base (Happy Path)

*   **Description :** Exécuter le script sans aucun argument pour s'assurer qu'il se termine sans erreur, en utilisant le flux par défaut (chargement d'extrait aléatoire, analyse et génération de rapport).
*   **Commande :**
    ```powershell
    ./scripts/system/activate_project_env.ps1 -ScriptPath "python" -ScriptArgs "scripts/orchestration/orchestrate_complex_analysis.py"
    ```
*   **Critères de succès :**
    *   Le script se termine avec un code de sortie 0.
    *   Un message "ORCHESTRATION COMPLEXE TERMINEE" est affiché.
    *   Un fichier de rapport Markdown (ex: `rapport_analyse_complexe_YYYYMMDD_HHMMSS.md`) est créé dans le répertoire racine.
    *   Le rapport contient une section "Résultats Finaux" avec des données.

## 2. Validation des Entrées (Gestion d'Erreurs)

*   **Description :** Simuler un échec de chargement du corpus pour vérifier que le mécanisme de fallback du script est correctement activé. Cela se fait en modifiant temporairement le chemin du fichier corpus dans le script ou en s'assurant que le fichier est inaccessible.
*   **Hypothèse :** Le test de base couvre déjà implicitement le cas d'echec si le fichier `tests/extract_sources_backup.enc` n'est pas ou ne peut pas être lu. Le script devrait utiliser le texte de fallback.
*   **Critères de succès :**
    *   Le script se termine avec succès (code 0).
    *   Le rapport généré indique "Texte statique de secours" comme type de source.
    *   Un log de niveau `ERROR` ou `WARNING` est généré, indiquant l'échec du chargement du corpus.

## 3. Validation des Sorties

*   **Description :** Analyser le contenu du rapport Markdown généré pour s'assurer de sa complétude et de sa structure.
*   **Actions :**
    1.  Ouvrir le rapport généré lors du test de base.
    2.  Vérifier la présence des sections suivantes :
        *   `Source Analysée`
        *   `Agents Orchestrés`
        *   `Outils Utilisés`
        *   `Trace Conversationnelle Détaillée`
        *   `Résultats Finaux` (avec une section `Mode Fallacies`)
        *   `Métriques de Performance`
    3.  Vérifier que le nombre d'interactions, d'agents et d'outils n'est pas nul.
    4.  Valider que la section des sophismes (`Mode Fallacies`) contient soit des sophismes détectés, soit le message "Aucun sophisme valide détecté...".

## 4. Test d'Intégration des Agents

*   **Description :** Confirmer que les agents (réels ou simulés) sont correctement invoqués et que leurs interactions sont tracées.
*   **Hypothèse :** Le test de base couvre ce point, car le script orchestre `InformalAnalysisAgent` (réel) et simule `RhetoricalAnalysisAgent` et `SynthesisAgent`.
*   **Critères de succès :**
    *   Le rapport de test mentionne les agents suivants dans la section `Agents Orchestrés` : `CorpusManager`, `InformalAnalysisAgent`, `RhetoricalAnalysisAgent`, `SynthesisAgent`.
    *   La trace conversationnelle détaillée montre des interactions pour chaque agent listé.