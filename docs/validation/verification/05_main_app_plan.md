# Plan de Vérification pour `argumentation_analysis/main_orchestrator.py`

Ce document décrit le plan de test pour le script principal `main_orchestrator.py`, qui sert de point d'entrée à l'application d'analyse rhétorique.

## 1. Test de Démarrage et d'Aide

- **Objectif :** Vérifier que le script peut être lancé sans erreur et qu'il répond correctement aux arguments de base.
- **Commande :** `python argumentation_analysis/main_orchestrator.py --help`
- **Résultat Attendu :** Le script affiche un message d'aide listant les arguments disponibles (`--skip-ui`, `--text-file`) et se termine sans erreur.

## 2. Tests Fonctionnels

### 2.1 Test d'Intégration de Bout en Bout (Mode `skip-ui` avec fichier)

- **Objectif :** Valider le chemin d'exécution principal non interactif, de la lecture d'un fichier à la fin de l'analyse.
- **Prérequis :** Créer un fichier `docs/verification/test_input.txt` avec un texte simple.
- **Commande :** `python argumentation_analysis/main_orchestrator.py --skip-ui --text-file docs/verification/test_input.txt`
- **Résultat Attendu :**
    - Le script démarre, initialise la JVM et le service LLM.
    - Il lit le contenu de `test_input.txt`.
    - Il exécute `run_analysis_conversation` sans erreur.
    - Le script se termine avec un message de succès.
    - Les logs produits indiquent le déroulement normal de l'analyse.

### 2.2 Test du Mode `skip-ui` sans Fichier

- **Objectif :** Vérifier que le script utilise correctement le texte d'exemple interne.
- **Commande :** `python argumentation_analysis/main_orchestrator.py --skip-ui`
- **Résultat Attendu :**
    - Similaire au test 2.1, mais le script doit loguer qu'il utilise le "texte d'exemple prédéfini".
    - L'analyse doit se dérouler et se terminer correctement.

*Note : Le mode UI interactif ne sera pas testé de manière automatisée ici, car il nécessite une interaction manuelle. La robustesse des modes non interactifs est prioritaire pour la CI/CD.*

## 3. Tests de la Gestion d'Erreur

### 3.1 Test avec un Fichier Inexistant

- **Objectif :** S'assurer que le script gère gracieusement l'échec de lecture d'un fichier.
- **Commande :** `python argumentation_analysis/main_orchestrator.py --skip-ui --text-file docs/verification/fichier_qui_n_existe_pas.txt`
- **Résultat Attendu :**
    - Le script démarre.
    - Il logue une erreur claire indiquant que le fichier n'a pas pu être lu.
    - Le script se termine proprement sans eception non gérée et sans tenter de lancer l'analyse.

### 3.2 Test de Démarrage sans Fichier `.env` (Simulation)

- **Objectif :** Vérifier que le script détecte l'absence de configuration essentielle et se termine avec un message d'erreur approprié.
- **Méthode :** Ce test sera conceptuel ou nécessitera de renommer temporairement le `.env`. Le script `ensure_env` devrait lever une exception ou quitter proprement. Le plus simple est de vérifier le code pour s'assurer que des messages clairs sont affichés. Les premières lignes de `main()` vérifient déjà si les variables d'environnement sont présentes et affichent leur statut.
- **Résultat Attendu dans les logs :** Des messages comme `LLM Model ID présent: False` devraient apparaître, et si l'initialisation du LLM échoue, le script devrait loguer un message critique et ne pas lancer l'analyse.

## 4. Test d'Intégration des Sorties

- **Objectif :** Valider que les artefacts (fichiers de résultats, logs) sont générés comme prévu.
- **Méthode :** Après l'exécution réussie du test 2.1, inspecter le répertoire de travail pour les sorties attendues. La fonction `run_analysis_conversation` est supposée générer des rapports ou des logs.
- **Résultat Attendu :**
    - Des fichiers de logs contenant les traces de l'exécution sont présents.
    - Si des fichiers de résultats sont prévus (ex: `results/*.json`), vérifier leur présence et leur format de base.