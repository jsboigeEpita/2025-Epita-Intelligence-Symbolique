# Projet Intelligence Symbolique

## Table des Matières
- [Introduction](#introduction)
- [Modalités du projet](#modalités-du-projet)
  - [Composition des équipes](#composition-des-équipes)
  - [Livrables](#livrables)
  - [Présentation](#présentation)
  - [Évaluation](#évaluation)
- [Utilisation des LLMs et IA Symbolique](#utilisation-des-llms-et-ia-symbolique)
  - [Outils à disposition](#outils-à-disposition)
  - [Combinaison IA Générative et IA Symbolique](#combinaison-ia-générative-et-ia-symbolique)
- [Sujets de Projets](#sujets-de-projets)
  - [Domaines Fondamentaux](#domaines-fondamentaux)
  - [Frameworks d'Argumentation Avancés](#frameworks-dargumentation-avancés)
  - [Planification et Raisonnement](#planification-et-raisonnement)
  - [Ingénierie des Connaissances](#ingénierie-des-connaissances)
  - [Maintenance de la Vérité](#maintenance-de-la-vérité)
  - [Smart Contracts](#smart-contracts)
  - [Développements Transversaux](#développements-transversaux)
  - [Conduite de Projet et Orchestration](#conduite-de-projet-et-orchestration)
  - [Gestion des Sources](#gestion-des-sources)
  - [Moteur Agentique](#moteur-agentique)
  - [Intégration MCP (Model Context Protocol)](#intégration-mcp-model-context-protocol)
  - [Agents Spécialistes](#agents-spécialistes)
  - [Indexation Sémantique](#indexation-sémantique)
  - [Automatisation](#automatisation)
  - [Développement d'Interfaces Utilisateurs](#développement-dinterfaces-utilisateurs)
  - [Projets Intégrateurs](#projets-intégrateurs)
- [Directives de Contribution](#directives-de-contribution)
  - [Workflow de développement](#workflow-de-développement)
  - [Standards de codage](#standards-de-codage)
  - [Documentation](#documentation)
  - [Processus de revue](#processus-de-revue)
- [Ressources et Documentation](#ressources-et-documentation)

## Introduction

Ce projet a pour but de vous permettre d'appliquer concrètement les méthodes et outils vus en cours sur l'intelligence symbolique. Vous serez amenés à résoudre des problèmes réels ou réalistes à l'aide de ces techniques en développant un projet complet, depuis la modélisation jusqu'à la solution opérationnelle.

Cette année, contrairement au cours précédent de programmation par contrainte où vous avez livré des travaux indépendants, vous travaillerez tous de concert sur ce dépôt. Un tronc commun est fourni sous la forme d'une infrastructure d'analyse argumentative multi-agents que vous pourrez explorer à travers les nombreux README du projet.

### Structure du Projet

Le projet est organisé en plusieurs modules principaux :

- **[`argumentiation_analysis/`](./argumentiation_analysis/README.md)** : Dossier principal contenant l'infrastructure d'analyse argumentative multi-agents.
  - **[`agents/`](./argumentiation_analysis/agents/README.md)** : Agents spécialisés pour l'analyse (PM, Informal, PL, Extract).
  - **[`core/`](./argumentiation_analysis/core/README.md)** : Composants fondamentaux partagés (État, LLM, JVM).
  - **[`orchestration/`](./argumentiation_analysis/orchestration/README.md)** : Logique d'exécution de la conversation.
  - **[`ui/`](./argumentiation_analysis/ui/README.md)** : Interface utilisateur pour la configuration des analyses.
  - **[`utils/`](./argumentiation_analysis/utils/README.md)** : Utilitaires généraux et outils de réparation d'extraits.
  - **[`tests/`](./argumentiation_analysis/tests/README.md)** : Tests unitaires et d'intégration.

Chaque module dispose de son propre README détaillé expliquant son fonctionnement et son utilisation.

## Architecture Technique

Cette section présente l'architecture technique du projet d'analyse argumentative multi-agents, expliquant comment les différents composants interagissent pour former un système cohérent.

### Vue d'ensemble

Le projet est construit autour d'une architecture multi-agents où différents agents spécialisés collaborent pour analyser des textes argumentatifs. Cette architecture permet une séparation claire des responsabilités et facilite l'extension du système avec de nouveaux agents ou fonctionnalités.

```
┌─────────────────────────────────────────────────────────────┐
│                      Interface Utilisateur                   │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│                        Orchestration                         │
└───────┬─────────────────┬─────────────────┬─────────────────┘
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  Agent Extract │ │ Agent Informal│ │   Agent PL    │ ...
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
┌───────▼─────────────────▼─────────────────▼───────┐
│                   État Partagé                     │
└───────────────────────────────────────────────────┘
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  LLM Service  │ │  JVM (Tweety) │ │ Autres Services│
└───────────────┘ └───────────────┘ └───────────────┘
```

### Flux de données et cycle de vie d'une analyse

Le cycle de vie d'une analyse argumentative suit les étapes suivantes:

1. **Ingestion des données**: Le texte à analyser est fourni via l'interface utilisateur ou un script.
2. **Extraction des arguments**: L'agent Extract identifie les arguments présents dans le texte.
3. **Analyse informelle**: L'agent Informal analyse les arguments pour détecter les sophismes et évaluer leur qualité.
4. **Analyse formelle**: L'agent PL (Propositional Logic) formalise les arguments en logique propositionnelle et vérifie leur validité.
5. **Synthèse des résultats**: Les résultats des différents agents sont combinés dans l'état partagé.
6. **Présentation**: Les résultats sont formatés et présentés à l'utilisateur.

Chaque étape est gérée par un agent spécialisé, et l'orchestration assure la coordination entre ces agents.

### Approche multi-instance

Le système est conçu pour permettre le déploiement de plusieurs instances d'agents, ce qui offre plusieurs avantages:

- **Parallélisation**: Traitement simultané de différentes parties d'une analyse.
- **Spécialisation**: Instances d'agents configurées pour des tâches spécifiques.
- **Redondance**: Amélioration de la fiabilité grâce à la duplication des agents critiques.
- **Évolutivité**: Ajout dynamique d'instances selon la charge de travail.

Cette approche multi-instance est particulièrement utile pour les analyses complexes ou volumineuses, où différents agents peuvent travailler en parallèle sur différentes parties du texte.

### Gestion de l'état partagé

Le module `core/shared_state.py` implémente un système de gestion d'état partagé qui permet aux différents agents de communiquer et de partager des informations. Ce système:

- Maintient une représentation cohérente de l'état de l'analyse
- Gère les dépendances entre les résultats des différents agents
- Résout les conflits potentiels entre les analyses des agents
- Fournit des mécanismes de persistance pour sauvegarder et restaurer l'état

L'état partagé est structuré comme un graphe de connaissances, où les nœuds représentent des entités (arguments, prémisses, conclusions) et les arêtes représentent des relations (support, attaque, implication).

## Guide de Démarrage Rapide

Ce guide vous permettra de configurer rapidement l'environnement de développement et d'exécuter le projet d'analyse argumentative multi-agents.

### 1. Cloner le dépôt

```bash
git clone https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique.git
cd 2025-Epita-Intelligence-Symbolique
```

### 2. Configurer l'environnement de développement

#### Prérequis

- **Python 3.9+** : Nécessaire pour exécuter le code Python
- **Java JDK 11+** : Requis pour l'intégration avec Tweety via JPype
- **Pip** : Gestionnaire de paquets Python

#### Installation de Java

Le projet utilise JPype pour intégrer la bibliothèque Java Tweety. Assurez-vous d'avoir installé Java JDK 11 ou supérieur :

- **Windows** : Téléchargez et installez depuis [Oracle JDK](https://www.oracle.com/java/technologies/downloads/) ou [OpenJDK](https://adoptium.net/)
- **macOS** : Utilisez Homebrew `brew install --cask temurin` ou téléchargez depuis [Oracle JDK](https://www.oracle.com/java/technologies/downloads/)
- **Linux** : Utilisez votre gestionnaire de paquets, par exemple `sudo apt install openjdk-17-jdk`

Vérifiez l'installation avec :
```bash
java -version
```

#### Configuration de JAVA_HOME

Le système tentera de détecter automatiquement votre installation Java, mais il est recommandé de définir la variable d'environnement JAVA_HOME :

- **Windows** : Ajoutez une variable d'environnement système `JAVA_HOME` pointant vers votre répertoire JDK (ex: `C:\Program Files\Java\jdk-17`)
- **macOS/Linux** : Ajoutez à votre `.bashrc` ou `.zshrc` :
  ```bash
  export JAVA_HOME=/chemin/vers/votre/jdk
  ```

### 3. Installer les dépendances Python

Naviguez vers le dossier principal du projet et installez les dépendances :

```bash
cd argumentiation_analysis
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Créez ou modifiez le fichier `.env` dans le dossier `argumentiation_analysis` avec les informations suivantes :

```
# Service LLM à utiliser (obligatoire)
GLOBAL_LLM_SERVICE="OpenAI"

# Clé API OpenAI (obligatoire si GLOBAL_LLM_SERVICE="OpenAI")
OPENAI_API_KEY="votre-clé-api-openai"

# Modèle OpenAI à utiliser (obligatoire si GLOBAL_LLM_SERVICE="OpenAI")
OPENAI_CHAT_MODEL_ID="gpt-4o-mini"

# Phrase secrète pour le chiffrement des configurations (obligatoire)
TEXT_CONFIG_PASSPHRASE="votre-phrase-secrète"

# Chemin vers l'installation Java (optionnel, détecté automatiquement si non spécifié)
JAVA_HOME="/chemin/vers/votre/jdk"
```

#### Explication des variables d'environnement

- **GLOBAL_LLM_SERVICE**: Définit le service de modèle de langage à utiliser. Actuellement, seul "OpenAI" est pleinement supporté.
  
- **OPENAI_API_KEY**: Votre clé API OpenAI personnelle. Vous pouvez l'obtenir sur [la plateforme OpenAI](https://platform.openai.com/api-keys).
  
- **OPENAI_CHAT_MODEL_ID**: Le modèle OpenAI à utiliser pour les analyses. Les modèles recommandés sont "gpt-4o-mini" (bon équilibre performance/coût) ou "gpt-4o" (performances maximales).
  
- **TEXT_CONFIG_PASSPHRASE**: Phrase secrète utilisée pour chiffrer les configurations sensibles, notamment les extraits de textes et leurs sources. Cette phrase doit être complexe et sécurisée.
  
- **JAVA_HOME**: Chemin vers votre installation Java JDK. Si non spécifié, le système tentera de détecter automatiquement l'installation Java.

#### Sécurité des données

Le système utilise un mécanisme de chiffrement pour protéger les données sensibles:

- Les configurations sont chiffrées avec AES-256 en utilisant la phrase secrète comme clé
- Les fichiers chiffrés ont l'extension `.enc`
- Les utilitaires dans `utils/crypto_service.py` gèrent le chiffrement et le déchiffrement

Pour des environnements de production, il est recommandé de:
1. Ne jamais partager votre fichier `.env`
2. Utiliser un fichier `.env.example` comme modèle sans valeurs sensibles
3. Stocker les clés API comme variables d'environnement système plutôt que dans le fichier `.env`

### 5. Intégration avec Tweety

#### Présentation de Tweety

[TweetyProject](https://tweetyproject.org/) est une collection complète de bibliothèques Java pour l'intelligence artificielle symbolique et la représentation des connaissances. Elle offre des implémentations pour de nombreux formalismes:

- Logiques classiques (propositionnelle, premier ordre, description)
- Logiques non-classiques (modale, conditionnelle, temporelle)
- Frameworks d'argumentation (Dung, ASPIC+, DeLP, ABA, bipolaire, pondéré)
- Révision de croyances et maintenance de la vérité
- Answer Set Programming (ASP)

#### Téléchargement automatique

Lors de la première exécution, le système téléchargera automatiquement les JARs Tweety nécessaires dans le dossier `libs`. Vous n'avez pas besoin de les télécharger manuellement. Les fichiers suivants seront téléchargés:

- `tweety-full.jar`: La bibliothèque Tweety complète
- `tweety-arg-dung.jar`: Module pour les frameworks d'argumentation de Dung
- `tweety-logics-pl.jar`: Module pour la logique propositionnelle
- `tweety-logics-fol.jar`: Module pour la logique du premier ordre
- Et d'autres modules selon les besoins

#### Initialisation de la JVM

L'intégration avec Tweety se fait via JPype, qui permet d'accéder aux classes Java depuis Python. Avant d'utiliser les fonctionnalités de Tweety, vous devez initialiser la JVM:

```python
from core.jvm_setup import initialize_jvm

# Initialiser la JVM pour Tweety
initialize_jvm()
```

Cette initialisation n'est nécessaire qu'une seule fois par session Python.

#### Modules Tweety utilisés

Le projet utilise principalement les modules suivants de Tweety:

- `org.tweetyproject.logics.pl`: Logique propositionnelle
- `org.tweetyproject.arg.dung`: Frameworks d'argumentation abstraits
- `org.tweetyproject.arg.aspic`: Argumentation structurée
- `org.tweetyproject.commons`: Utilitaires communs

#### Exemple d'utilisation dans l'agent PropositionalLogicAgent

L'agent PL utilise Tweety pour formaliser et analyser les arguments en logique propositionnelle:

```python
# Accès aux classes Java via JPype
PlParser = jpype.JClass("org.tweetyproject.logics.pl.parser.PlParser")
PlFormula = jpype.JClass("org.tweetyproject.logics.pl.syntax.PlFormula")

# Créer un parser pour la logique propositionnelle
parser = PlParser()

# Parser une formule
formula = parser.parseFormula("a && (b || !c)")

# Vérifier la satisfiabilité
is_satisfiable = formula.isConsistent()
```

#### Syntaxe pour la logique propositionnelle

La syntaxe utilisée par le parser de Tweety pour la logique propositionnelle est:

- `&&` pour la conjonction (ET)
- `||` pour la disjonction (OU)
- `!` pour la négation (NON)
- `>>` pour l'implication
- `<=>` pour l'équivalence

### 6. Lancer l'application

Plusieurs points d'entrée sont disponibles selon vos besoins et cas d'utilisation. Choisissez celui qui correspond le mieux à votre objectif:

#### Notebook d'orchestration principal

Pour une expérience interactive avec visualisation des résultats et exploration des données:

```bash
jupyter notebook main_orchestrator.ipynb
```

Ce notebook offre:
- Visualisation interactive des résultats
- Exécution pas à pas de l'analyse
- Personnalisation des paramètres en temps réel
- Graphiques et visualisations avancées

#### Interface utilisateur web

Pour une utilisation via interface graphique conviviale:

```bash
python -m ui.app
```

L'interface web permet:
- Configuration intuitive des analyses
- Visualisation des résultats sans code
- Gestion des extraits et des sources
- Sauvegarde et chargement des configurations

#### Analyse via script Python

Pour exécuter une analyse complète via script, idéal pour l'automatisation:

```bash
python run_analysis.py --input votre_texte.txt --output resultats.json
```

Options disponibles:
- `--input`: Chemin vers le fichier texte à analyser (obligatoire)
- `--output`: Chemin pour sauvegarder les résultats (optionnel)
- `--config`: Chemin vers un fichier de configuration personnalisé (optionnel)
- `--verbose`: Niveau de détail des logs (0-3, défaut: 1)

#### Orchestration personnalisée

Pour une orchestration avancée avec des agents personnalisés:

```bash
python run_orchestration.py --config config/custom_orchestration.json
```

#### Éditeur de marqueurs d'extraits

Pour éditer et gérer les marqueurs d'extraits dans les textes:

```bash
python run_extract_editor.py
```

#### Tableau comparatif des points d'entrée

| Point d'entrée | Interactivité | Interface graphique | Automatisation | Personnalisation | Cas d'utilisation typique |
|----------------|---------------|---------------------|----------------|------------------|---------------------------|
| Notebook       | ★★★★★         | ★★★★☆               | ★★☆☆☆          | ★★★★★            | Exploration et analyse détaillée |
| Interface web  | ★★★★☆         | ★★★★★               | ★★☆☆☆          | ★★★☆☆            | Utilisateurs non-techniques |
| Script Python  | ★☆☆☆☆         | ☆☆☆☆☆               | ★★★★★          | ★★★☆☆            | Traitement par lots |
| Orchestration  | ★★☆☆☆         | ☆☆☆☆☆               | ★★★★☆          | ★★★★★            | Workflows personnalisés |
| Extract Editor | ★★★★☆         | ★★★★☆               | ★☆☆☆☆          | ★★★☆☆            | Préparation des données |

### 7. Exemple simple

Voici un exemple minimal pour tester que tout fonctionne correctement :

```python
from core.jvm_setup import initialize_jvm
from core.llm_service import LLMService
from agents.extract.extract_agent import ExtractAgent

# Initialiser la JVM pour Tweety
initialize_jvm()

# Créer un service LLM
llm_service = LLMService()

# Créer un agent d'extraction
extract_agent = ExtractAgent(llm_service)

# Analyser un texte simple
text = "La Terre est plate car l'horizon semble plat. Cependant, les photos satellites montrent clairement que la Terre est sphérique."
result = extract_agent.extract_arguments(text)

print("Arguments extraits :")
for arg in result:
    print(f"- {arg}")
```

Enregistrez ce code dans un fichier `test_extraction.py` et exécutez-le avec `python test_extraction.py`.

## Modalités du projet

### Composition des équipes

Le projet peut être réalisé en équipes de 1 à 4 étudiants, avec un système de bonus/malus selon la taille de l'équipe:
- **Solo** : +3 points (pour les étudiants souhaitant prendre un rôle plus transversal)
- **Binôme** : +1 point
- **Trinôme** : +0 point
- **Quatuor** : -1 point

Cette flexibilité permet à chacun de choisir la configuration qui correspond le mieux à son profil et à ses objectifs d'apprentissage.

### Livrables

Chaque groupe devra contribuer au dépôt principal via des **pull requests** régulières. Ces contributions devront être clairement identifiées et documentées, et pourront inclure :

- Le code source complet, opérationnel, documenté et maintenable (en Python, Java via JPype, ou autre).
- Le matériel complémentaire utilisé pour le projet (datasets, scripts auxiliaires, etc.).
- Les slides utilisés lors de la présentation finale.
- Un notebook explicatif détaillant les étapes du projet, les choix de modélisation, les expérimentations et les résultats obtenus.

Les pull requests devront être régulièrement mises à jour durant toute la durée du projet afin que l'enseignant puisse suivre l'avancement et éventuellement apporter des retours, et que tous les élèves puissent prendre connaissance des travaux des autres groupes avant la soutenance avec évaluation collégiale.

### Présentation

- Présentation orale finale avec support visuel (slides).
- Démonstration de la solution opérationnelle devant la classe.

### Évaluation

- Évaluation collégiale : chaque élève évaluera les autres groupes en complément de l'évaluation réalisée par l'enseignant.
- Critères : clarté, originalité, robustesse de la solution, qualité du code, pertinence des choix méthodologiques et organisation.

## Utilisation des LLMs et IA Symbolique

### Outils à disposition

Pour faciliter la réalisation du projet, vous aurez accès à plusieurs ressources avancées :

- **Plateforme Open-WebUI** : intégrant des modèles d'intelligence artificielle d'OpenAI et locaux très performants, ainsi que des plugins spécifiques et une base de connaissances complète alimentée par la bibliographie du cours.
- **Clés d'API OpenAI et locales** : mise à votre disposition pour exploiter pleinement les capacités des modèles GPT dans vos développements.
- **Notebook Agentique** : un notebook interactif permettant d'automatiser la création ou la finalisation de vos propres notebooks, facilitant ainsi la structuration et l'amélioration de vos solutions.
- **Bibliothèque Tweety** : une bibliothèque Java complète pour l'IA symbolique, intégrée via JPype, offrant de nombreux modules pour différentes logiques (propositionnelle, premier ordre, description, modale, conditionnelle, QBF...) et formalismes d'argumentation (Dung, ASPIC+, DeLP, ABA, ADF, bipolaire, pondéré...). Cette bibliothèque permet d'implémenter des mécanismes de raisonnement avancés comme la révision de croyances et l'analyse d'incohérence.

### Combinaison IA Générative et IA Symbolique

Le projet se concentre sur l'intégration de l'IA générative agentique orchestrée avec des techniques d'IA symbolique, notamment pour l'analyse argumentative. Cette approche hybride permet de combiner la flexibilité et la puissance des LLMs avec la rigueur et la formalisation des méthodes symboliques.

Cette combinaison s'inscrit dans la tendance actuelle de l'IA neurosymbolique, comme décrite dans "Neurosymbolic AI - The 3rd Wave" (2020), qui vise à intégrer les capacités d'apprentissage des réseaux neuronaux avec les capacités de raisonnement des systèmes symboliques. Cette approche permet de bénéficier des avantages des deux paradigmes : l'adaptabilité et la gestion de l'incertitude des approches connexionnistes, et l'explicabilité et la rigueur logique des approches symboliques.
Les travaux récents comme "Learning Explanatory Rules from Noisy Data" (Evans, 2018) et "DeepProbLog: Neural Probabilistic Logic Programming" (2018) montrent comment les techniques d'apprentissage profond peuvent être combinées avec la programmation logique pour résoudre des problèmes complexes nécessitant à la fois des capacités de perception et de raisonnement.

## Sujets de Projets

Les sujets proposés ci-dessous couvrent différents aspects de l'IA symbolique, avec un focus particulier sur l'argumentation et son intégration par l'IA générative agentique orchestrée. Chaque groupe devra choisir un sujet et contribuer à l'amélioration du projet global.

Les projets sont organisés en trois catégories principales :
1. **Fondements théoriques et techniques** : Projets centrés sur les aspects formels, logiques et théoriques de l'argumentation
2. **Développement système et infrastructure** : Projets axés sur l'architecture, l'orchestration et les composants techniques
3. **Expérience utilisateur et applications** : Projets orientés vers les interfaces, visualisations et cas d'usage concrets

Chaque sujet est présenté avec une structure standardisée :
- **Contexte** : Présentation du domaine et de son importance
- **Objectifs** : Ce que le projet vise à accomplir
- **Technologies clés** : Outils, frameworks et concepts essentiels
- **Niveau de difficulté** : ⭐ (Accessible) à ⭐⭐⭐⭐⭐ (Très avancé)
- **Interdépendances** : Liens avec d'autres sujets de projets
- **Références** : Sources et documentation pour approfondir

### 1. Fondements théoriques et techniques

#### 1.1 Logiques formelles et raisonnement

##### 1.1.1 Intégration des logiques propositionnelles avancées
- **Contexte** : La logique propositionnelle constitue la base de nombreux systèmes de raisonnement automatique. Le module `logics.pl` de Tweety offre des fonctionnalités avancées encore peu exploitées dans le projet.
- **Objectifs** : Améliorer l'agent PL existant pour exploiter davantage les fonctionnalités du module, notamment les solveurs SAT (SAT4J interne ou solveurs externes comme Lingeling, CaDiCaL), la conversion DIMACS, et les opérations avancées sur les formules (DNF, CNF, simplification). Implémenter des requêtes plus sophistiquées comme la vérification de satisfiabilité, la recherche de modèles, et l'analyse d'implications logiques.
- **Technologies clés** : Tweety `logics.pl`, solveurs SAT, Java-Python bridge
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Base pour les projets de maintenance de la vérité (1.4) et d'argumentation formelle (1.2)
- **Références** :
  - "SAT_SMT_by_example.pdf" (2023)
  - "Artificial Intelligence: A Modern Approach" (Chapitres sur la logique propositionnelle)
  - Documentation Tweety `logics.pl`

## Directives de Contribution et Organisation

Cette section présente une approche flexible pour contribuer au projet Intelligence Symbolique, favorisant l'auto-organisation des équipes d'étudiants tout en maintenant la qualité et la cohérence du code produit.

### Organisation des Équipes et Gestion de Projet

Plutôt que d'imposer un protocole de contribution strict, nous encourageons les étudiants à s'organiser selon leurs préférences et compétences. Certains étudiants sont invités à prendre en main l'aspect gestion de projet, en assumant des rôles tels que :

- **Chef de projet** : Coordination générale, planification des sprints, suivi de l'avancement
- **Responsable technique** : Architecture, standards de code, revue technique
