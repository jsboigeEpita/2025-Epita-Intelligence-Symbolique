# Tests Fonctionnels

Ce répertoire contient les tests fonctionnels du projet. Ces tests sont conçus pour vérifier que des fonctionnalités complètes ou des workflows spécifiques du système fonctionnent comme attendu, en intégrant plusieurs composants.

## Objectifs des Tests Fonctionnels

*   Valider des scénarios d'utilisation de bout en bout.
*   S'assurer que les interactions entre différents modules et services produisent les résultats escomptés.
*   Vérifier la robustesse du système face à des données d'entrée et des conditions variées.

## Fichiers de Test Notables

*   [`test_agent_collaboration_workflow.py`](test_agent_collaboration_workflow.py:1): Teste le workflow complet de collaboration entre les agents (PM, PL, Informal, Extract) orchestrés par une architecture hiérarchique (Strategic, Tactical, Operational Managers).
*   [`test_fallacy_detection_workflow.py`](test_fallacy_detection_workflow.py:1): Teste l'enchaînement des analyseurs de sophismes (contextuel, complexe, évaluateur de sévérité) pour un workflow de détection complet.
*   [`test_python_analysis_workflow_components.py`](test_python_analysis_workflow_components.py:1): Teste les composants individuels du workflow d'analyse Python, y compris les fonctions de chiffrement/déchiffrement, le chargement de corpus, des aspects de `InformalAgent`, et l'exécution du script complet `run_full_python_analysis_workflow.py`.
*   [`test_rhetorical_analysis_workflow.py`](test_rhetorical_analysis_workflow.py:1): (À compléter en fonction du contenu de ce fichier)

## Exécution des Tests

Ces tests sont généralement exécutés avec les autres tests du projet via la commande pytest standard. Consulter le `README.md` principal du répertoire `tests/` pour plus de détails sur l'exécution des tests.
Certains tests fonctionnels peuvent nécessiter des configurations spécifiques ou des services externes (mockés ou réels selon l'environnement de test).