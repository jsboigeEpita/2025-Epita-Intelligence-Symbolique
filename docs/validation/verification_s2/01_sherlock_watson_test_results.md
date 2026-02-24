# Rapport de Test - Sherlock/Watson/Moriarty

Ce document consigne les résultats des tests effectués sur les démos Sherlock/Watson/Moriarty.
---

**Nom du script :** `argumentation_analysis/demos/jtms/run_demo.py`
**Commande exécutée :** `powershell -c "conda run --no-capture-output -n projet-is python argumentation_analysis/demos/jtms/run_demo.py"`
**Résultat :** `SUCCÈS`
**Corrections apportées :** Aucune.
---
### Test de `argumentation_analysis/orchestration/cluedo_orchestrator.py`

**Date :** 24/06/2025
**Résultat :** SUCCÈS

**Actions correctives :**
1.  **Refactoring majeur :** Remplacement de `autogen.GroupChat` par une boucle d'orchestration manuelle pour contourner les incompatibilités de version d'`autogen`.
2.  **Correction de l'enregistrement du service Kernel :** Modification de la méthode d'ajout du service `OpenAIChatCompletion` au `Kernel` pour résoudre une `KernelServiceNotFoundError` persistante due à des changements d'API dans `semantic-kernel`. Le `service_id` a été aligné entre la déclaration du service et son utilisation par les agents.
3.  **Corrections d'attributs (AttributeError) :**
    - Corrigé l'appel `final_state.nom_enquete` en `final_state.nom_enquete_cluedo`.
    - Corrigé l'appel `final_state.solution_correcte` en `final_state.solution_secrete_cluedo`.
    - Corrigé l'itération sur `final_state.hypotheses.values()` en `final_state.get_hypotheses()`.
    - Corrigé l'itération sur `final_state.tasks.values()` en `final_state.tasks`.

**Observations :**
Le script exécute maintenant une conversation de 10 tours entre les agents Sherlock et Watson. La cause initiale des échecs était une cascade d'erreurs dues à des versions de bibliothèques incompatibles (`semantic-kernel`, `autogen`). Les corrections ont permis de stabiliser le script qui est maintenant fonctionnel.
---
### Test de `argumentation_analysis/orchestration/cluedo_extended_orchestrator.py`

**Date :** 24/06/2025
**Résultat :** SUCCÈS

**Actions correctives :**
1.  **Correction de l'enregistrement du service Kernel :** Ajout de l'initialisation du service `OpenAIChatCompletion` dans la fonction `main`, en répliquant le correctif appliqué à `cluedo_orchestrator.py`. Cela a résolu la `KernelServiceNotFoundError` qui empêchait les agents Sherlock et Watson de fonctionner.
2.  **Correction de la clé de dictionnaire (`KeyError`) :** Remplacé `result['final_state']['correct_solution']` par `result['final_state']['secret_solution']` pour afficher correctement la solution à la fin du script.

**Observations :**
Le script s'exécute maintenant sans erreur et termine la boucle d'orchestration. Bien que les agents n'aient pas trouvé la solution correcte dans cette exécution, le workflow lui-même est fonctionnel. Les erreurs d'infrastructure ont été résolues.