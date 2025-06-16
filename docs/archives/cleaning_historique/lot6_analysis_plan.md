# Lot 6 - Plan d'Analyse et de Nettoyage des Tests

## Contexte
Ce document détaille le plan d'analyse et de nettoyage pour le lot 6 des tests du projet, conformément aux instructions fournies. L'objectif est de finaliser la réorganisation des tests d'intégration (hors JPype), d'explorer les tests d'orchestration restants, et d'aborder les tests de scripts et d'interface utilisateur.

## Phase 1: Préparation de l'environnement et synchronisation
1.  Vérification de la présence du script `activate_project_env.ps1`. (Confirmé)
2.  **Modification de `activate_project_env.ps1` :** Le script a été modifié pour gérer correctement les arguments multiples lors du "sourcing", permettant son utilisation directe pour les commandes Git complexes.
3.  Exécution de `powershell -Command ". .\activate_project_env.ps1 'git' 'checkout' 'main'"` pour s'assurer d'être sur la branche `main`. (Confirmé et réussi après modification du script)
4.  Exécution de `powershell -Command ". .\activate_project_env.ps1 'git' 'pull' 'origin' 'main' '--rebase'"` pour synchroniser la branche. (Confirmé et réussi)

## Phase 2: Traitement itératif des fichiers de test
Pour chacun des 10 fichiers listés :
    a.  **Analyse du fichier :**
        *   Lecture de son contenu.
        *   Vérification de son emplacement, de son nom et de sa pertinence.
        *   Examen du `README.md` du répertoire parent (création/mise à jour si besoin).
        *   Identification des fixtures et fonctions d'aide potentiellement extractibles.
        *   Identification des sections de la documentation projet qui pourraient référencer ces tests.
    b.  **Élaboration d'un plan d'action pour le fichier.**
    c.  **Validation du plan par l'utilisateur.**
    d.  **Exécution des actions validées** (par l'utilisateur ou un mode approprié après confirmation du plan).
    e.  **Consignation des informations** pour le rapport final.

### Fichiers à traiter :
1.  `tests/integration/test_informal_analysis_integration.py`
2.  `tests/integration/test_logic_agents_integration.py`
3.  `tests/integration/test_logic_api_integration.py`
4.  `tests/integration/test_notebooks_execution.py`
5.  `tests/integration/test_tactical_operational_integration.py`
6.  `tests/orchestration/hierarchical/operational/test_manager.py`
7.  `tests/orchestration/hierarchical/tactical/test_coordinator.py`
8.  `tests/scripts/test_embed_all_sources.py`
9.  `tests/ui/test_extract_definition_persistence.py`
10. `tests/ui/test_utils.py`

## Phase 3: Création des rapports et finalisation
1.  Mise à jour de ce fichier (`lot6_analysis_plan.md`) avec les analyses détaillées.
2.  Création et remplissage de `docs/cleaning_reports/lot6_completion_report.md`.
3.  Utilisation de l'outil `attempt_completion` pour présenter le résultat final.