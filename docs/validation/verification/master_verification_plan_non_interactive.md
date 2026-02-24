# Plan Directeur de Vérification Non-Interactive

## 1. Introduction

L'objectif de ce plan est de définir une stratégie de vérification complète et non-interactive pour les cinq points d'entrée critiques du projet. Pour chaque point d'entrée, nous appliquerons un cycle "Map, Test, Clean, Document" de manière autonome, orchestré via une unique sous-tâche déléguée.

## 2. Points d'Entrée Cibles

La vérification portera sur les cinq scripts suivants :

1.  `scripts/launch_webapp_background.py`
2.  `scripts/orchestrate_complex_analysis.py`
3.  `argumentation_analysis/scripts/simulate_balanced_participation.py`
4.  `argumentation_analysis/scripts/generate_and_analyze_arguments.py`
5.  `argumentation_analysis/main_app.py`

## 3. Stratégie d'Orchestration

Pour chaque point d'entrée listé ci-dessus, une seule sous-tâche sera créée et assignée à un agent `code`. Cette sous-tâche englobera l'intégralité du cycle de vérification :

*   **Map :** L'agent créera un plan de test détaillé dans un fichier `_plan.md`. Ce plan décrira les scénarios de test, les données d'entrée et les résultats attendus.
*   **Test :** L'agent exécutera le plan de test de manière autonome, en lançant les scripts et en capturant les sorties et les erreurs.
*   **Clean :** En cas d'échec des tests, l'agent analysera les logs d'erreurs et tentera d'appliquer des corrections de manière autonome.
*   **Document :** L'agent produira un rapport de résultats complet dans un fichier `_test_results.md`, incluant les résultats des tests, les erreurs rencontrées et les corrections appliquées. Il améliorera également la documentation existante du code (docstrings, commentaires) en fonction des découvertes.
*   **Commit :** Une fois le cycle terminé pour un point d'entrée, l'agent sauvegardera tous les nouveaux artefacts (plan, résultats) et les modifications de code dans Git via un commit unique et atomique, puis poussera les changements.

## 4. Structure des Artefacts

Pour chaque point d'entrée `N` (par exemple, `01_launch_webapp_background`), les artefacts suivants seront créés dans le répertoire `docs/verification/` :

*   `NN_..._plan.md` : Le plan de test détaillé.
*   `NN_..._test_results.md` : Le rapport de résultats de test.

Cette approche garantit une traçabilité complète et une exécution cohérente du processus de vérification pour chaque composant clé.