# Documentation des Workflows d'Enquête

Ce document décrit comment utiliser le script unifié `run_unified_investigation.py` pour lancer différents workflows d'enquête.

## Script Principal

Le script à exécuter est : `run_unified_investigation.py`.

## Commande d'Exécution

Pour garantir que les modules Python sont correctement résolus, il est impératif d'utiliser le flag `-m` lors de l'exécution du script depuis la racine du projet.

```bash
python -m scripts.sherlock_watson.run_unified_investigation --workflow <nom_du_workflow>
```

## Workflows Disponibles

L'argument `--workflow` accepte les valeurs suivantes :

*   `cluedo`
*   `einstein`
*   `jtms`

### Descriptions des Workflows

-   **cluedo**: Lance une enquête collaborative pour résoudre un mystère inspiré du jeu Cluedo. Les agents collaborent pour identifier le coupable, l'arme et le lieu du crime.
-   **einstein**: Démarre une résolution (simulée) de la célèbre énigme d'Einstein. Ce workflow démontre les capacités de raisonnement logique des agents face à un problème complexe.
-   **jtms**: Initie une enquête collaborative où le raisonnement de chaque agent est validé en temps réel par un Justification-Truth Maintenance System (JTMS). Cette validation est effectuée via une intégration avec la bibliothèque Tweety, assurant la cohérence des arguments avancés.