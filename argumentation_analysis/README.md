# Module d'Analyse d'Argumentation

Ce document fournit une vue d'ensemble du module `argumentation_analysis`, de son architecture et de la manière de l'utiliser.

## Architecture

L'architecture du module est conçue pour être flexible et modulaire, s'appuyant sur deux modèles d'orchestration principaux pour traiter les demandes d'analyse.

### Modèles Architecturaux

1.  **Le Modèle d'Orchestration Hiérarchique** :
    *   **Description** : Une architecture classique à trois niveaux (Stratégique, Tactique, Opérationnel) où une demande est progressivement décomposée en objectifs, puis en tâches exécutables.
    *   **Flux** : `Demande -> Analyse Stratégique -> Plan Tactique -> Exécution Opérationnelle -> Synthèse`.
    *   **Idéal pour** : Des analyses complexes et profondes nécessitant une planification détaillée.

2.  **Le Modèle d'Orchestration Spécialisée (Plugin)** :
    *   **Description** : Un modèle qui court-circuite la hiérarchie pour exécuter directement un "orchestrateur spécialisé" conçu pour une tâche très spécifique (ex: analyse de conversation, analyse logique).
    *   **Flux** : `Demande -> Sélection du Plugin -> Exécution par l'Orchestrateur Spécialisé -> Résultat`.
    *   **Idéal pour** : Des tâches bien définies et spécifiques où une approche directe est plus efficace.

La sélection entre ces modèles est dynamique, permettant au système de choisir la meilleure approche en fonction du contexte de la demande.

## Utilisation

Le point d'entrée principal pour lancer une analyse via la ligne de commande est le module `argumentation_analysis.orchestration.engine.main_orchestrator`.

### Commande d'Exécution

Pour exécuter une analyse, utilisez la commande suivante à la racine du projet. Assurez-vous que votre environnement Python est correctement configuré et que les dépendances sont installées.

```bash
python -m argumentation_analysis.orchestration.engine.main_orchestrator --text "L'intelligence artificielle représente une avancée majeure pour l'humanité, mais elle soulève également des questions éthiques importantes concernant l'autonomie et la surveillance."
```

### Arguments

*   `--text` : (Requis) La chaîne de caractères contenant le texte que vous souhaitez analyser.

## Configuration

La configuration du module est gérée de manière centralisée et se trouve principalement dans le répertoire `argumentation_analysis/config/`.

*   **`settings.py`**: Ce fichier contient les paramètres de configuration principaux de l'application. Vous pouvez y ajuster les chemins, les clés d'API et d'autres paramètres de comportement du système.
*   **`.env` / `.env.template`**: Le module utilise des variables d'environnement (via `python-dotenv`) pour gérer les secrets comme les clés d'API. Copiez `.env.template` en `.env` et remplissez les valeurs requises pour votre environnement local.


### Configuration du Solveur Logique (First-Order Logic)

Le moteur d'analyse s'appuie sur un système de logique formelle configurable. Vous pouvez sélectionner le solveur à utiliser via la variable d'environnement `ARG_ANALYSIS_SOLVER`.

**Options :**
*   `tweety` (Défaut) : Solution intégrée basée sur [TweetyProject](https://tweetyproject.org/).
*   `prover9` : Fait appel au solveur externe [Prover9](https://www.cs.unm.edu/~mccune/prover9/). Assurez-vous qu'il est installé et disponible dans le `PATH` de votre système.

**Exemple d'utilisation (PowerShell) :**
```powershell
$env:ARG_ANALYSIS_SOLVER="prover9"
python -m argumentation_analysis.orchestration.engine.main_orchestrator --text "..."
```

**Exemple d'utilisation (Bash) :**
```bash
ARG_ANALYSIS_SOLVER=prover9 python -m argumentation_analysis.orchestration.engine.main_orchestrator --text "..."
```
