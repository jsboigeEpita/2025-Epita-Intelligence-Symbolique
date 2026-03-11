# Guide de Démarrage - Point d'Entrée 3 : Démonstration EPITA

## 1. Objectif

Ce document décrit le fonctionnement et l'utilisation du script `demonstration_epita.py`, le point d'entrée principal pour les démonstrations techniques du projet.

Ce script agit comme un orchestrateur qui charge et exécute dynamiquement des modules de démonstration indépendants. Chaque module présente une fonctionnalité spécifique du système, comme l'analyse d'argumentation, la validation de tests ou l'interaction avec des services d'IA.

L'objectif est de fournir un cadre stable et standardisé pour lancer des démonstrations techniques de manière isolée ou séquentielle.

## 2. Fonctionnalités

Le script `demonstration_epita.py` supporte plusieurs modes de fonctionnement via des arguments en ligne de commande :

*   **Démonstration individuelle** : Lance un module de démonstration spécifique.
    *   Exemple : `--demo-analyse-argumentation`
*   **Tests de validation** : Exécute une série de tests pour valider l'intégrité du système.
    *   Exemple : `--demo-tests-validation`
*   **Exécution complète** : Lance l'ensemble des tests et démonstrations disponibles en une seule commande.
    *   Exemple : `--all-tests`

## 3. Prérequis

Avant de lancer le script, assurez-vous que toutes les dépendances du projet sont installées. Si vous avez suivi le guide d'installation principal, vous devriez déjà avoir un environnement configuré.

Si ce n'est pas le cas, exécutez la commande suivante à la racine du projet pour installer les dépendances nécessaires :

```bash
pip install -r requirements.txt
```

Assurez-vous également que votre fichier `.env` est correctement configuré avec les clés d'API nécessaires pour les services externes (ex: OpenAI).

## 4. Utilisation

Pour exécuter les démonstrations, utilisez la syntaxe `python [chemin_vers_le_script] [options]`.

### Commande de base

La commande la plus simple pour vérifier que tout fonctionne est de lancer tous les tests :

```bash
python examples/scripts_demonstration/demonstration_epita.py --all-tests
```

Cette commande exécute séquentiellement tous les modules de test et de démonstration et affiche les résultats dans la console. Un code de sortie `0` indique que toutes les opérations se sont déroulées avec succès.

### Lancer une démonstration spécifique

Pour lancer un module particulier, utilisez l'argument correspondant. Par exemple, pour lancer la démonstration d'analyse d'argumentation :

```bash
python examples/scripts_demonstration/demonstration_epita.py --demo-analyse-argumentation --text "Le soleil est une étoile car il brille de sa propre lumière." --agent-type "FALLACY_DETECTION"
```

Cet exemple illustre également comment passer des arguments spécifiques (`--text`, `--agent-type`) qui ne seront transmis qu'au module concerné.