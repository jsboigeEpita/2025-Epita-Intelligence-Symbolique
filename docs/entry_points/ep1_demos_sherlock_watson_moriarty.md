# Point d'Entrée 1 : Démos Sherlock, Watson & Moriarty

Ce document décrit comment exécuter et valider les démonstrations mettant en scène les agents Sherlock, Watson et Moriarty. L'objectif est de fournir un guide de démarrage rapide et fiable pour ces scénarios.

## Statut
- **Validation** : Terminé
- **Date de validation** : 2025-07-24
- **Script principal** : `scripts/sherlock_watson/run_cluedo_oracle_enhanced.py`

## Description de la Démo
Cette démo exécute un scénario de type "Cluedo" où trois agents IA collaborent (et s'affrontent) pour résoudre un mystère :
- **Sherlock** : Mène l'enquête en posant des questions et en formulant des hypothèses.
- **Watson** : Assiste Sherlock avec une analyse logique rigoureuse des faits.
- **Moriarty** : Agit comme un "Oracle" qui possède certaines informations (les cartes du jeu) et répond aux suggestions de manière énigmatique, sans jamais mentir.

Le système est orchestré de manière cyclique (Sherlock → Watson → Moriarty) et se termine lorsqu'une solution est trouvée ou après un nombre de tours défini.

## Prérequis
Avant de lancer la démo, assurez-vous que votre environnement est correctement configuré :
1.  **Environnement Conda** : Activez l'environnement du projet (`projet-is`).
2.  **Variables d'environnement** : Assurez-vous que votre fichier `.env` est présent à la racine et contient les clés API nécessaires (notamment `OPENAI_API_KEY`).
3.  **Dépendances Java** : Le script gère automatiquement le téléchargement des dépendances Java (Tweety) et l'utilisation d'un JDK portable. Aucune configuration manuelle n'est requise.

## Comment lancer la Démo
Pour exécuter la démonstration, suivez ces étapes :

1.  **Ouvrez un terminal** à la racine du projet.

2.  **Exécutez le script d'activation et de lancement**. Ce script s'occupe d'activer l'environnement Conda et de lancer le scénario Python :

    ```powershell
    powershell -File .\\scripts\\env\\activate_project_env.ps1 -CommandToRun "python scripts/sherlock_watson/run_cluedo_oracle_enhanced.py"
    ```

3.  **Observez la sortie**. Le script affichera dans la console :
    - L'initialisation de l'environnement, y compris le démarrage de la JVM.
    - Le dialogue tour par tour entre les agents Sherlock, Watson et Moriarty.
    - Un rapport final indiquant si le mystère a été résolu, la solution correcte, et quelques métriques de performance.

## Résultat Attendu
L'exécution devrait se terminer sans erreur après un certain nombre de tours (par défaut, 15 tours ou 5 cycles complets). Le rapport final montrera le déroulement de la partie. Il est normal que les agents ne trouvent pas toujours la solution, l'objectif principal de ce point d'entrée étant de valider que l'orchestration technique entre eux est fonctionnelle.