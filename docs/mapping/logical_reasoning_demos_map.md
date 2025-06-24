# Cartographie des Démonstrations de Raisonnement Logique

Ce document détaille l'architecture et les interactions des composants impliqués dans les démonstrations de raisonnement logique (Cluedo & Einstein), principalement orchestrées par le script [`agents_logiques_production.py`](../../examples/Sherlock_Watson/agents_logiques_production.py).

## 1. Vue d'ensemble de l'Architecture

Le système est conçu autour d'un modèle d'orchestration d'agents, où un script principal configure et dirige des agents spécialisés pour analyser et débattre de scénarios logiques.

- **Orchestrateur** : `examples/Sherlock_Watson/agents_logiques_production.py`
- **Agents** : Définis dans `argumentation_analysis/agents/`
- **Scénarios** : Fichiers JSON (`cluedo_scenario.json`, `einstein_scenario.json`)

## 2. Composants Clés

### 2.1. Le Script Orchestrateur (`agents_logiques_production.py`)

C'est le point d'entrée et le chef d'orchestre. Ses responsabilités incluent :

- **Parsing des arguments** : La fonction [`main()`](../../examples/Sherlock_Watson/agents_logiques_production.py:670) utilise `argparse` pour accepter un fichier de scénario via l'argument `--scenario`.
- **Chargement des scénarios** : La fonction [`load_scenarios()`](../../examples/Sherlock_Watson/agents_logiques_production.py:535) lit les fichiers JSON qui décrivent les tâches à exécuter.
- **Initialisation** : La classe [`ProductionAgentOrchestrator`](../../examples/Sherlock_Watson/agents_logiques_production.py:408) est instanciée pour gérer le cycle de vie des agents.
- **Création des Agents** : Le script crée des instances de [`ProductionLogicalAgent`](../../examples/Sherlock_Watson/agents_logiques_production.py:301), notamment :
    - `sherlock` (Raisonnement déductif)
    - `watson` (Raisonnement inductif)
    - `moriarty` (Raisonnement contradictoire / adversaire)
- **Exécution du Scénario** : La fonction [`run_production_agents_demo()`](../../examples/Sherlock_Watson/agents_logiques_production.py:549) exécute les différentes étapes définies dans le fichier de scénario (tests de données, dialogues, débats).

### 2.2. Les Agents Logiques (`ProductionLogicalAgent`)

Chaque agent est une entité autonome capable d'analyse.

- **Traitement interne** : Chaque agent utilise une instance de [`ProductionCustomDataProcessor`](../../examples/Sherlock_Watson/agents_logiques_production.py:94) pour l'analyse du langage naturel. Ce processeur identifie les propositions, détecte les sophismes et analyse la logique modale à l'aide d'expressions régulières.
- **Base de connaissances** : Les agents maintiennent une base de connaissances et une mémoire de leurs conversations pour conserver le contexte.
- **Communication** : La méthode [`communicate_with_agent()`](../../examples/Sherlock_Watson/agents_logiques_production.py:366) permet aux agents d'échanger des messages, qui sont à leur tour analysés.

### 2.3. Les Fichiers de Scénario (JSON)

Ces fichiers sont le moteur des démonstrations. Ils décrivent une séquence d'actions à réaliser par l'orchestrateur. Un scénario typique contient des clés comme :

- `name` : Le nom du scénario.
- `custom_data_test` : Une tâche de traitement de texte pour un agent spécifique.
- `dialogue_test` : Un échange de messages entre deux agents.
- `debate_test` : Un débat structuré sur un sujet, orchestré par [`orchestrate_logical_debate()`](../../examples/Sherlock_Watson/agents_logiques_production.py:434).

## 3. Flux d'Interaction

1.  Un utilisateur lance [`agents_logiques_production.py`](../../examples/Sherlock_Watson/agents_logiques_production.py) en spécifiant un fichier de scénario (`--scenario cluedo_scenario.json`).
2.  L'**Orchestrateur** charge le JSON, initialise et crée les agents `sherlock`, `watson`, et `moriarty`.
3.  L'Orchestrateur lit les tâches dans le scénario (ex: un débat sur le coupable dans le Cluedo).
4.  Il appelle les méthodes appropriées sur les agents (ex: `process_argument` ou `communicate_with_agent`).
5.  Chaque **Agent** utilise son `ProductionCustomDataProcessor` pour analyser le texte.
6.  Les agents retournent des résultats d'analyse structurés.
7.  L'Orchestrateur collecte les résultats, les affiche dans la console et génère des statistiques.
8.  Le script se termine en indiquant un succès ou un échec.

Ce flux garantit que le raisonnement est effectué de manière transparente et sans mocks, en s'appuyant sur les capacités d'analyse définies dans le code.