# Plan d'Analyse et de Nettoyage - Lot 2

**Objectif Général :** Améliorer l'organisation, la documentation et la réutilisabilité des fichiers de test du Lot 2.

**Prérequis (à exécuter une seule fois au début) :**

1.  **Activation de l'Environnement et Synchronisation Git :**
    *   Ouvrir un nouveau terminal PowerShell.
    *   Activer l'environnement Conda `projet-is` : `conda activate projet-is`
    *   Se positionner sur la branche `main` : `git checkout main`
    *   Synchroniser avec `origin/main` : `git pull origin main --rebase`

**Traitement Fichier par Fichier (pour chaque fichier du lot) :**

**Fichiers `test_informal_*.py` (Groupe 1)**
(Concerne : `test_informal_agent_creation.py`, `test_informal_agent.py`, `test_informal_analysis_methods.py`, `test_informal_definitions.py`, `test_informal_error_handling.py`)

*   **a. Organisation des Tests :**
    *   **Analyse :** Ces fichiers testent des composants liés aux agents informels situés dans `argumentation_analysis.agents.core.informal`. Leur emplacement actuel à la racine de `tests/` n'est pas optimal.
    *   **Action proposée :**
        1.  Créer le répertoire `tests/agents/core/informal/` s'il n'existe pas.
        2.  Déplacer les fichiers `test_informal_*.py` listés ci-dessus vers `tests/agents/core/informal/`.
        3.  **Vérification des imports :** Examiner chaque fichier déplacé. Supprimer les manipulations de `sys.path` (comme `sys.path.append(os.path.abspath('..'))`) et s'assurer que les imports fonctionnent (en privilégiant les imports absolus depuis la racine du projet ou les imports relatifs corrects).
    *   **Nom des fichiers :** Les noms actuels sont clairs et suivent les conventions. Aucun renommage nécessaire.

*   **b. Documentation du Répertoire de Test :**
    *   **Analyse :** Les répertoires `tests/`, `tests/agents/`, `tests/agents/core/` et le nouveau `tests/agents/core/informal/` sont concernés.
    *   **Action proposée :**
        1.  Créer/Mettre à jour `tests/agents/core/informal/README.md` pour décrire l'objectif des tests qu'il contient (tests des agents et fonctionnalités informelles).
        2.  Créer/Mettre à jour `tests/agents/core/README.md` pour mentionner le sous-répertoire `informal` et son rôle.
        3.  Mettre à jour `tests/agents/README.md` pour refléter la nouvelle structure sous `core/`.
        4.  Mettre à jour `tests/README.md` pour indiquer que les tests d'agents informels sont maintenant dans `tests/agents/core/informal/`.

*   **c. Extraction de Composants Réutilisables :**
    *   **Analyse :** Parcourir l'ensemble des fichiers `test_informal_*.py` déplacés.
    *   **Action proposée :**
        *   Identifier les mocks communs (ex: `MockSemanticKernel`, mocks d'outils comme `fallacy_detector`), les instanciations d'agents répétitives, ou les fonctions d'aide (helper functions) utilisées dans plusieurs de ces fichiers de test.
        *   Centraliser ces composants réutilisables dans un nouveau fichier de fixtures dédié : `tests/agents/core/informal/fixtures.py`, ou les ajouter aux fixtures existantes plus générales comme `tests/fixtures/agent_fixtures.py` si leur portée dépasse les tests informels.
        *   Si des logiques de test particulièrement complexes et génériques (non spécifiques aux mocks mais à la *manière* de tester certaines fonctionnalités) sont identifiées, évaluer si elles pourraient être transformées en fonctions ou classes utilitaires dans le code source principal (`argumentation_analysis/`).

*   **d. Documentation des Composants Source (si créés) :**
    *   Si des composants sont extraits vers `argumentation_analysis/`, s'assurer qu'ils sont correctement documentés (docstrings, commentaires).

*   **e. Enrichissement de la Documentation Croisée :**
    *   **Analyse :** Les tests des agents informels valident leur création, leur comportement, leurs méthodes d'analyse, leurs définitions et la gestion des erreurs.
    *   **Suggestions d'enrichissement :**
        *   Dans la documentation des modules correspondants sous `argumentation_analysis/agents/core/informal/`, ajouter des références aux fichiers de test spécifiques dans `tests/agents/core/informal/`.
        *   Dans la documentation générale sur l'architecture des agents (si elle existe, ex: `docs/projets/architecture_agents.md`), mettre à jour les références vers les emplacements des tests unitaires.

**Autres Fichiers du Lot (Traitement Individuel) :**

Pour chaque fichier suivant, une analyse spécifique sera menée pour déterminer les actions appropriées concernant l'organisation, la documentation, l'extraction et l'enrichissement de la documentation croisée.

6.  **`tests/test_installation.py`**
    *   **Plan d'analyse :** Lire le contenu pour comprendre ce qui est testé (dépendances, environnement, etc.). Évaluer si sa place à la racine de `tests/` est la plus pertinente ou si un sous-répertoire (ex: `tests/setup/`, `tests/environment/`) serait mieux.

7.  **`tests/test_load_extract_definitions.py`**
    *   **Plan d'analyse :** Lire le contenu. Concerne probablement `argumentation_analysis/utils/` ou une fonctionnalité liée aux "extracts". Déterminer le meilleur emplacement (ex: `tests/utils/`, `tests/extraction/`).

8.  **`tests/test_minimal.py`**
    *   **Plan d'analyse :** Lire le contenu. Si c'est un test de fumée basique, la racine de `tests/` ou `tests/smoke/` pourrait convenir.

9.  **`tests/test_network_errors.py`**
    *   **Plan d'analyse :** Lire le contenu. Identifier les composants du code source qui gèrent les aspects réseau. Le test pourrait être placé près des tests de ces composants ou dans un répertoire `tests/common/` ou `tests/utils/` si la gestion d'erreur est générique.

10. **`tests/test_project_imports.py`**
    *   **Plan d'analyse :** Lire le contenu. Teste probablement la cohérence des imports à travers le projet. La racine de `tests/` ou un `tests/project_health/` ou `tests/structure/` pourrait être approprié.

**Commits et Push (Rappel) :**

*   Effectuer des commits atomiques après avoir traité des groupes logiques de fichiers (ex: tous les `test_informal_*` ensemble, puis les autres individuellement ou par petits groupes).
*   Pousser régulièrement sur `origin/main` après `git pull origin main --rebase`.

**Rapport Final (Rappel) :**

*   Ce fichier (`docs/cleaning_reports/lot2_analysis_plan.md`) constitue le plan initial.
*   Un fichier `docs/cleaning_reports/lot2_completion_report.md` sera créé à la fin, détaillant :
    *   Pour chaque fichier de test du lot : résumé des analyses, actions entreprises, propositions d'extraction complexes (si applicable), suggestions spécifiques d'enrichissement de la documentation croisée.
    *   Confirmation que tous les changements ont été poussés sur `origin/main` et indication du hash du dernier commit pertinent pour ce lot.