# Cartographie de la Démonstration EPITA

## 1. Objectif

Ce document cartographie l'architecture et les composants de la démonstration EPITA, validée par le script `demos/validation_complete_epita.py`. L'objectif de cette démo est de présenter les capacités d'analyse de l'argumentation du projet, en combinant des agents logiques et des outils d'analyse de la rhétorique.

## 2. Composants Principaux

### 2.1. Orchestrateur de Validation

- **Script**: [`demos/validation_complete_epita.py`](demos/validation_complete_epita.py:0)
- **Rôle**: Ce script est le point d'entrée pour lancer une validation complète et rigoureuse de la démonstration. Il exécute une série de tests, collecte des métriques et génère des rapports de certification.

### 2.2. Script de Démonstration

- **Script**: [`examples/scripts_demonstration/demonstration_epita.py`](examples/scripts_demonstration/demonstration_epita.py:0)
- **Rôle**: C'est le cœur de la démo. Il met en scène des scénarios d'analyse, invoque les agents d'argumentation et affiche les résultats.

## 3. Modules et Dépendances

### 3.1. Analyse de l'Argumentation

- **Répertoire**: [`argumentation_analysis/`](argumentation_analysis/)
- **Description**: Ce module central fournit toutes les capacités d'analyse. Il est structuré en plusieurs sous-modules clés :
    - `agents/core/logic/`: Contient les agents responsables de l'analyse logique formelle (logique propositionnelle, premier ordre, modale).
    - `agents/core/informal/`: Contient les agents pour la détection de sophismes et l'analyse de la rhétorique.
    - `orchestration/`: Gère la coordination entre les différents agents pour des analyses complexes.
    - `utils/`: Fournit des fonctions utilitaires pour la journalisation, le traitement de texte et la génération de rapports.

### 3.2. Modules de la Démonstration

- **Répertoire**: [`examples/scripts_demonstration/modules/`](examples/scripts_demonstration/modules/)
- **Description**: Ces modules sont spécifiques à la démonstration EPITA et contiennent des scénarios de test, des configurations et des données d'exemple.

## 4. Flux d'Exécution

1.  L'utilisateur lance [`demos/validation_complete_epita.py`](demos/validation_complete_epita.py:0) avec des paramètres optionnels (mode, complexité).
2.  Le script configure l'environnement et les chemins nécessaires.
3.  Il exécute le script [`examples/scripts_demonstration/demonstration_epita.py`](examples/scripts_demonstration/demonstration_epita.py:0) avec différents arguments pour tester sa robustesse.
4.  Il valide l'importation et la syntaxe des modules dans [`examples/scripts_demonstration/modules/`](examples/scripts_demonstration/modules/).
5.  Des tests synthétiques peuvent être générés et soumis aux agents d'analyse pour évaluer leur précision.
6.  Les résultats, les temps d'exécution et les scores d'authenticité sont collectés.
7.  Un rapport de validation final est généré, certifiant le niveau de fiabilité de la démonstration.