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

### Domaines Fondamentaux

#### Logiques Formelles et Argumentation

- **Intégration des logiques propositionnelles avancées** : Améliorer l'agent PL existant pour exploiter davantage les fonctionnalités du module `logics.pl` de Tweety, notamment les solveurs SAT (SAT4J interne ou solveurs externes comme Lingeling, CaDiCaL), la conversion DIMACS, et les opérations avancées sur les formules (DNF, CNF, simplification). Implémenter des requêtes plus sophistiquées comme la vérification de satisfiabilité, la recherche de modèles, et l'analyse d'implications logiques. Le notebook Tweety démontre comment manipuler des formules propositionnelles, créer des mondes possibles, et utiliser différents raisonneurs pour vérifier la satisfiabilité et trouver des modèles.
  - *Références* : "SAT_SMT_by_example.pdf" (2023), "Artificial Intelligence: A Modern Approach" (Chapitres sur la logique propositionnelle).

- **Logique du premier ordre (FOL)** : Développer un nouvel agent utilisant le module `logics.fol` de Tweety pour analyser des arguments plus complexes impliquant des quantificateurs (`∀`, `∃`) et des prédicats. Cet agent pourrait tenter de traduire des arguments exprimés en langage naturel (avec quantificateurs) en formules FOL, définir des signatures logiques (types/sorts, constantes, prédicats, fonctions), et utiliser les raisonneurs intégrés (`SimpleFolReasoner`, `EFOLReasoner`). Un défi majeur est la traduction robuste du langage naturel vers FOL. L'intégration d'un prouveur externe comme EProver (via `EFOLReasoner`) permettrait de vérifier des implications logiques plus complexes. Le notebook Tweety montre comment définir une signature FOL avec des sorts (types), des constantes, des prédicats, et comment effectuer des requêtes sur une base de connaissances FOL. *Application* : Analyser des arguments généraux portant sur des propriétés d'objets ou des relations entre eux (ex: "Tous les hommes sont mortels", "Certains arguments sont fallacieux").
  - *Références* : "Artificial Intelligence: A Modern Approach" de Russell & Norvig (Chapitres sur FOL), "Automated Theorem Proving" (2002), Documentation Tweety `logics.fol`.

- **Logique modale** : Créer un agent spécialisé utilisant le module `logics.ml` de Tweety pour raisonner sur des modalités comme la nécessité (`[]`), la possibilité (`<>`), les croyances ou les connaissances. Cet agent pourrait analyser des arguments impliquant des notions de possibilité, nécessité, obligation ou permission, en utilisant SimpleMlReasoner ou SPASSMlReasoner (avec intégration de SPASS). Le notebook Tweety illustre comment parser des formules modales et effectuer des raisonnements avec différents prouveurs, y compris l'intégration avec le prouveur externe SPASS. Les applications incluent l'analyse d'arguments déontiques, épistémiques ou temporels.
  - *Références* : "Handbook of Modal Logic", "Artificial Intelligence: A Modern Approach" (Sections sur la logique modale).

- **Logique de description (DL)** : Développer un agent utilisant le module `logics.dl` de Tweety pour modéliser des connaissances structurées sous forme de concepts, rôles et individus. Cet agent pourrait construire des TBox (axiomes terminologiques) et ABox (assertions sur les individus), et raisonner sur la subsomption, l'instanciation et la consistance. Le notebook Tweety montre comment définir des concepts atomiques, des rôles, des individus, et comment construire des axiomes d'équivalence et des assertions pour créer une base de connaissances DL complète. Applications possibles pour la modélisation d'ontologies argumentatives.
  - *Références* : "The Description Logic Handbook - Theory, Implementation and Applications" (2003), "What is an Ontology" (2009), "Foundations of Semantic Web Technologies" (2008).

- **Formules booléennes quantifiées (QBF)** : Explorer l'utilisation du module `logics.qbf` de Tweety pour modéliser et résoudre des problèmes PSPACE-complets. Cet agent pourrait traiter des problèmes de planification conditionnelle, de jeux à deux joueurs, ou de vérification formelle qui dépassent la portée de SAT. Le notebook Tweety présente comment créer des formules QBF avec des quantificateurs existentiels sur des variables propositionnelles et comment les convertir au format QDIMACS standard.
  - *Références* : "SAT_SMT_by_example.pdf" (2023), "Handbook of Satisfiability".

- **Logique conditionnelle (CL)** : Implémenter un agent utilisant le module `logics.cl` de Tweety pour raisonner sur des conditionnels de la forme "Si A est vrai, alors B est typiquement vrai". Le notebook Tweety démontre comment créer une base conditionnelle avec des conditionnels comme (f|b), (b|p), (¬f|p), et comment calculer une fonction de classement (ranking) pour évaluer ces conditionnels. Applications pour le raisonnement non-monotone et la modélisation des défauts dans l'argumentation.
  - *Références* : "Reasoning-with-probabilistic-and-deterministic-graphical-models-exact-algorithms" (2013).

- **Cadres d'argumentation abstraits (Dung)** : Développer un agent utilisant le module `arg.dung` de Tweety pour modéliser et analyser des structures argumentatives abstraites (AAF). Cet agent devrait permettre de construire des graphes d'arguments et d'attaques (`DungTheory`), et surtout de calculer l'acceptabilité des arguments selon différentes sémantiques (admissible, complète, préférée, stable, fondée, idéale, semi-stable, CF2...). Il est crucial de comprendre la signification de chaque sémantique (ex: stable = point de vue cohérent et maximal, fondée = sceptique et bien fondée). Le notebook Tweety illustre en détail comment construire des cadres d'argumentation, ajouter des arguments et des attaques, et calculer les extensions selon différentes sémantiques. Il montre également comment générer des cadres aléatoires et traiter des cas particuliers comme les cycles. L'agent pourrait visualiser ces graphes et les extensions résultantes. *Extensions possibles* : Intégrer des préférences (PAF) ou des valeurs (VAF), bien que Tweety ait des modules dédiés pour certains frameworks étendus.
  - *Références* : Article fondateur de P. M. Dung (1995) "On the acceptability of arguments...", Survey de Baroni, Caminada, Giacomin (2011) "An introduction to argumentation semantics", "Implementing KR Approaches with Tweety" (2018).

- **Argumentation structurée (ASPIC+)** : Créer un agent utilisant le module `arg.aspic` de Tweety pour construire des arguments à partir de règles strictes et défaisables. Cet agent pourrait modéliser des bases de connaissances avec axiomes et règles, gérer les préférences entre règles, et analyser les attaques (rebutting, undercutting, undermining). Le notebook Tweety montre comment créer une théorie ASPIC+ avec des règles défaisables (=>), des axiomes, et comment la convertir en un cadre de Dung équivalent pour appliquer les sémantiques standard.
  - *Références* : "Implementing KR Approaches with Tweety" (2018), "Argumentation in Artificial Intelligence" (Chapitres sur ASPIC+).

- **Programmation logique défaisable (DeLP)** : Implémenter un agent utilisant le module `arg.delp` de Tweety pour raisonner avec des règles strictes et défaisables dans un cadre de programmation logique. Le notebook Tweety démontre comment charger un programme DeLP à partir d'un fichier (comme birds2.txt) et effectuer des requêtes sur ce programme, en utilisant la spécificité généralisée comme critère de comparaison. Applications pour la résolution de conflits et le raisonnement dialectique.
  - *Références* : "Implementing KR Approaches with Tweety" (2018), "Defeasible Logic Programming: An Argumentative Approach".

- **Argumentation basée sur les hypothèses (ABA)** : Développer un agent utilisant le module `arg.aba` de Tweety pour modéliser l'argumentation où certains littéraux sont désignés comme hypothèses. Cet agent pourrait analyser les attaques entre arguments dérivés de ces hypothèses et déterminer leur acceptabilité. Le notebook Tweety illustre comment charger une théorie ABA à partir de fichiers (comme example2.aba ou smp_fol.aba) et effectuer des requêtes avec différents raisonneurs (FlatAbaReasoner, PreferredReasoner), en utilisant soit la logique propositionnelle soit la logique du premier ordre comme langage sous-jacent.
  - *Références* : "Implementing KR Approaches with Tweety" (2018), "Assumption-Based Argumentation".

- **Argumentation déductive** : Créer un agent utilisant le module `arg.deductive` de Tweety pour construire des arguments comme des paires (Support, Conclusion) où le support est un sous-ensemble minimal et consistant de la base de connaissances qui implique logiquement la conclusion. Le notebook Tweety montre comment créer une base de connaissances déductive, effectuer des requêtes, et utiliser différents catégoriseurs (ClassicalCategorizer) et accumulateurs (SimpleAccumulator) pour évaluer les arguments.
  - *Références* : "Implementing KR Approaches with Tweety" (2018), "Logical Models of Argument".

- **Answer Set Programming (ASP)** : Développer un agent utilisant le module `lp.asp` de Tweety pour modéliser et résoudre des problèmes combinatoires complexes. Cet agent pourrait intégrer Clingo pour le raisonnement ASP et l'appliquer à des problèmes d'argumentation. Le notebook Tweety démontre comment construire des programmes ASP avec des règles, des faits et des contraintes, et comment utiliser ClingoSolver pour calculer les answer sets et effectuer du grounding.
  - *Références* : "Answer Set Programming: A Primer", "Handbook of Knowledge Representation" (Chapitre sur ASP).

#### Frameworks d'Argumentation Avancés

- **Abstract Dialectical Frameworks (ADF)** : Implémenter un agent utilisant le module `arg.adf` de Tweety. Les ADF généralisent les AAF de Dung en associant à chaque argument une condition d'acceptation (une formule propositionnelle sur l'état des autres arguments), permettant de modéliser des dépendances plus complexes que la simple attaque (ex: support, attaque conjointe). L'agent devrait permettre de définir ces conditions et de calculer les sémantiques ADF (admissible, complète, préférée, stable, fondée, modèle à 2 valeurs). Le notebook Tweety explique que le raisonnement ADF nécessite des solveurs SAT incrémentaux natifs (comme NativeMinisatSolver) et comment configurer correctement l'environnement pour les utiliser. *Application* : Modéliser des scénarios argumentatifs où l'acceptation d'un argument dépend de combinaisons spécifiques d'autres arguments.
  - *Références* : Article fondateur de Brewka et al. (2013) "Abstract Dialectical Frameworks", "Implementing KR Approaches with Tweety" (2018), Documentation Tweety `arg.adf`.

- **Frameworks bipolaires (BAF)** : Développer un agent utilisant le module `arg.bipolar` de Tweety pour modéliser des cadres d'argumentation incluant à la fois des relations d'attaque et de support entre arguments. Comprendre les différentes interprétations du support (déductif, nécessaire, évidentiel...) et les sémantiques associées proposées dans la littérature et implémentées dans Tweety. Le notebook Tweety présente plusieurs variantes de frameworks bipolaires : EAF (support simple), PEAF (support probabiliste), Evidential AF (avec arguments prima facie) et Necessity AF (où tous les arguments supportants sont requis). Il montre comment construire ces frameworks et calculer leurs extensions selon différentes sémantiques. L'agent pourrait visualiser ces graphes bipolaires et comparer les résultats des différentes sémantiques.
  - *Références* : Travaux de Cayrol et Lagasquie-Schiex sur les BAF, Survey de Cohen et al. (2014) sur l'argumentation bipolaire, "Implementing KR Approaches with Tweety" (2018), Documentation Tweety `arg.bipolar`.

- **Frameworks pondérés (WAF)** : Créer un agent utilisant le module `arg.weighted` de Tweety pour modéliser des cadres où les attaques ont des poids/forces. Cet agent pourrait utiliser différents semi-anneaux (WeightedSemiring, FuzzySemiring, ProbabilisticSemiring) et raisonneurs pondérés. Le notebook Tweety montre comment créer un WAF avec des attaques pondérées numériquement, et comment utiliser différents raisonneurs pondérés (SimpleWeightedConflictFreeReasoner, SimpleWeightedAdmissibleReasoner, etc.) avec des seuils alpha et gamma pour déterminer quand un argument est "suffisamment défendu" ou quand une attaque est "suffisamment forte".

- **Frameworks sociaux (SAF)** : Implémenter un agent utilisant le module `arg.social` de Tweety pour modéliser des cadres où les arguments reçoivent des votes (positifs/négatifs). Le notebook Tweety illustre comment créer un SAF, ajouter des votes positifs et négatifs aux arguments, et utiliser IssReasoner avec SimpleProductSemantics pour calculer des scores d'acceptabilité basés sur ces votes. Applications pour l'analyse d'arguments dans des contextes sociaux ou collaboratifs.

- **Set Argumentation Frameworks (SetAF)** : Développer un agent utilisant le module `arg.setaf` de Tweety pour modéliser des cadres où des ensembles d'arguments attaquent collectivement d'autres arguments. Le notebook Tweety montre comment créer un SetAF, définir des attaques d'ensemble (où un ensemble d'arguments attaque collectivement un argument), et calculer les extensions selon différentes sémantiques (fondée, admissible, préférée).

- **Frameworks étendus (attaques sur attaques)** : Créer un agent utilisant le module `arg.extended` de Tweety pour modéliser des cadres où les arguments peuvent attaquer des attaques (EAF) ou récursivement des attaques sur des attaques (REAF). Le notebook Tweety présente ces deux variantes : EAF où un argument peut attaquer une relation d'attaque, et REAF qui permet des attaques récursives sur des attaques (jusqu'au niveau 2 dans l'exemple). Il montre comment construire ces frameworks et calculer leurs extensions complètes.

- **Sémantiques basées sur le classement** : Implémenter un agent utilisant le module `arg.rankings` de Tweety pour établir un ordre entre les arguments (du plus acceptable au moins acceptable) plutôt qu'une simple acceptation/rejet. Le notebook Tweety présente de nombreuses approches de classement : Categorizer, Burden-Based, Discussion-Based, Tuples*, Strategy-Based (Matt & Toni), SAF-Based, Counting Semantics, Propagation Semantics, et Iterated Graded Defense. Il montre comment appliquer ces différents raisonneurs à des cadres d'argumentation et comparer leurs résultats.

- **Argumentation probabiliste** : Développer un agent utilisant le module `arg.prob` de Tweety pour modéliser l'incertitude dans les cadres d'argumentation, soit sur l'existence des arguments/attaques, soit sur leur acceptabilité. Le notebook Tweety se concentre sur les distributions de probabilité sur les sous-graphes (SubgraphProbabilityFunction), le calcul de probabilités d'acceptation d'arguments selon différentes sémantiques, et les loteries d'argumentation (ArgumentationLottery) avec fonctions d'utilité pour la prise de décision sous incertitude.

#### Planification et Raisonnement

- **Intégration d'un planificateur symbolique** : Développer un agent capable de générer des plans d'action basés sur des objectifs argumentatifs, en explorant le module `action` de Tweety pour la modélisation des actions et la planification. Ce travail pourrait s'appuyer sur les techniques de planification automatique décrites dans "Automated planning" (2010) et "Automated planning and acting - book" (2016), en les adaptant spécifiquement au contexte de l'argumentation. L'agent pourrait générer des plans pour atteindre des objectifs comme "faire accepter un argument spécifique" ou "réfuter un ensemble d'arguments adverses".
  - *Références* : "Automated planning" (2010), "Automated planning and acting - book" (2016), "Integrated Task and motion planning" (2020).

- **Logiques sociales et planification** : Explorer l'intégration du module `arg.social` de Tweety avec des techniques de planification pour modéliser des interactions argumentatives multi-agents, en utilisant la sémantique ISS (Iterated Schema Semantics) pour calculer des scores d'acceptabilité évolutifs. Cette approche permettrait de simuler l'évolution d'un débat ou d'une négociation au fil du temps, en tenant compte des stratégies des différents participants.
  - *Références* : "Multi Agent Systems" (2010), "A review of cooperative multi-agent deep reinforcement learning" (2021).

#### Ingénierie des Connaissances

- **Intégration d'ontologies AIF.owl** : Développer un moteur sémantique basé sur l'ontologie AIF (Argument Interchange Format) en OWL. L'objectif est de représenter la structure fine des arguments extraits (prémisses, conclusion, schémas d'inférence, relations d'attaque/support) en utilisant les classes AIF (I-Nodes, RA-Nodes, CA-Nodes). Utiliser le module `logics.dl` de Tweety ou une bibliothèque OWL externe (comme Owlready2) pour manipuler l'ontologie, vérifier sa consistance, et potentiellement inférer de nouvelles relations. *Défi* : Mapper de manière fiable les arguments extraits (souvent informels) vers la structure formelle AIF.
  - *Références* : Spécification AIF (Rahwan, Reed et al.), Documentation AIFdb, "Argumentation Mining" de Stede & Schneider (Chapitre sur la représentation), "What is an Ontology" (2009), "Foundations of Semantic Web Technologies" (2008).

- **Classification des arguments fallacieux** : Corriger, compléter et intégrer l'ontologie des sophismes (inspirée du projet Argumentum ou autre source). L'objectif est de disposer d'une taxonomie formelle des types de sophismes. Utiliser cette ontologie pour guider l'agent de détection de sophismes et pour structurer les résultats de l'analyse. Exploiter les capacités de modélisation ontologique (ex: `logics.dl` de Tweety) pour définir les propriétés de chaque sophisme et les relations entre eux. *Ressources nécessaires* : Accès à l'ontologie existante et à sa documentation si elle existe.
  - *Références* : "Logically Fallacious" de Bo Bennett, Taxonomie des sophismes sur Wikipedia, Projet Argumentum (si accessible), "Ontology-based systems engineering - a state-of-the-art review" (2019).

- **Knowledge Graph argumentatif** : Remplacer la structure JSON actuelle de l'état partagé par un graphe de connaissances plus expressif et interrogeable, en s'inspirant des structures de graphe utilisées dans les différents frameworks d'argumentation de Tweety. Cette approche permettrait une représentation plus riche des relations entre arguments et faciliterait les requêtes complexes sur la structure argumentative.
  - *Références* : "Knowledge graphs - 3447772.pdf" (2021), "Making sense of sensory input" (2019).

#### Maintenance de la Vérité

- **Intégration des modules de maintenance de la vérité** : Résoudre les problèmes d'import potentiels des modules `beliefdynamics` de Tweety et les intégrer au système. Ces modules sont cruciaux pour gérer l'évolution des connaissances et la résolution des conflits. Explorer les opérateurs de révision de croyances (pour intégrer de nouvelles informations en préservant la cohérence, ex: `LeviMultipleBaseRevisionOperator`), de contraction (pour retirer une croyance, ex: `KernelContractionOperator`), et d'update. Le notebook Tweety souligne l'importance de configurer correctement l'environnement Java et les chemins des JARs pour éviter les problèmes d'import avec ces modules. *Application* : Mettre à jour l'état partagé du système lorsque de nouvelles analyses d'agents arrivent, en gérant les contradictions potentielles. *Ressources nécessaires* : Informations sur les problèmes d'import spécifiques rencontrés.
  - *Références* : Théorie AGM (Alchourrón, Gärdenfors, Makinson), Travaux de Katsuno & Mendelzon, "Reasoning-with-probabilistic-and-deterministic-graphical-models-exact-algorithms" (2013), Documentation Tweety `beliefdynamics`.

- **Révision de croyances multi-agents** : Développer un agent utilisant le module `beliefdynamics.mas` de Tweety pour modéliser la révision de croyances dans un contexte multi-agents, où chaque information est associée à un agent source et où un ordre de crédibilité existe entre les agents. Implémenter différents opérateurs de révision: CrMasRevisionWrapper (priorisé), CrMasSimpleRevisionOperator (non-priorisé), CrMasArgumentativeRevisionOperator (basé sur l'argumentation). Cette approche est particulièrement pertinente dans un contexte d'analyse argumentative où différents agents spécialisés peuvent avoir des niveaux de confiance variables selon leur domaine d'expertise.
  - *Références* : "Multi Agent Systems" (2010), "A review of cooperative multi-agent deep reinforcement learning" (2021).

- **Mesures d'incohérence** : Intégrer les mesures d'incohérence de Tweety (`logics.pl.analysis`) pour quantifier le degré d'incohérence d'un ensemble d'informations (ex: les conclusions des différents agents sur un même texte). Comprendre les différentes approches (basées sur les MUS, les modèles partiels, etc.) et leur signification (ex: `ContensionInconsistencyMeasure`, `DSumInconsistencyMeasure`). *Application* : Utiliser ces mesures pour évaluer la fiabilité d'une analyse, déclencher des processus de résolution de conflits, ou guider la révision de croyances.
  - *Références* : Survey de Hunter et Konieczny sur les mesures d'incohérence, "Reasoning-with-probabilistic-and-deterministic-graphical-models-exact-algorithms" (2013), Documentation Tweety `logics.pl.analysis`.

- **Énumération de MUS (Minimal Unsatisfiable Subsets)** : Implémenter un agent capable d'identifier les sous-ensembles minimaux inconsistants d'une base de connaissances, en utilisant NaiveMusEnumerator ou MarcoMusEnumerator (avec intégration de MARCO). Cette fonctionnalité est essentielle pour diagnostiquer précisément les sources d'incohérence dans une base de connaissances argumentative complexe.
  - *Références* : "SAT_SMT_by_example.pdf" (2023), "Handbook of Satisfiability".

- **MaxSAT pour la résolution d'incohérences** : Développer un agent utilisant les capacités MaxSAT de Tweety (via OpenWboSolver) pour trouver des assignations qui satisfont toutes les clauses "dures" et minimisent le coût des clauses "molles" violées, permettant ainsi de résoudre des incohérences de manière optimale. Cette approche permet de préserver au maximum l'information tout en restaurant la cohérence.
  - *Références* : "SAT_SMT_by_example.pdf" (2023), "Constraint Integer Programming" (2011).

#### Smart Contracts

- **Formalisation de contrats argumentatifs** : Explorer l'utilisation de smart contracts pour formaliser et exécuter des protocoles d'argumentation, en s'appuyant sur les différents formalismes d'argumentation disponibles dans Tweety. Cette approche permettrait d'automatiser l'exécution de débats structurés ou de processus de résolution de conflits selon des règles prédéfinies et vérifiables.
  - *Références* : "Bitcoin and Beyond - Cryptocurrencies, blockchain and global governance" (2018), "Survey on blockchain based smart contracts - Applications, opportunities and challenges" (2021).

- **Vérification formelle d'arguments** : Développer des méthodes de vérification formelle pour garantir la validité des arguments dans un contexte contractuel, en utilisant potentiellement les capacités QBF ou FOL de Tweety. L'objectif est d'assurer que les arguments utilisés dans un contrat respectent certaines propriétés formelles (cohérence, non-circularité, etc.) avant leur exécution.
  - *Références* : "The Lean theorem prover" (2015), "The Lean 4 Theorem Prover and Programming Language" (2021), "SAT_SMT_by_example.pdf" (2023).

### Développements Transversaux

#### Conduite de Projet et Orchestration

- **Gestion de projet agile** : Mettre en place une méthodologie agile adaptée au contexte du projet, avec définition des rôles, des cérémonies et des artefacts. Implémenter un système de suivi basé sur Scrum ou Kanban, avec des sprints adaptés au calendrier académique. Utiliser des outils comme Jira, Trello ou GitHub Projects pour la gestion des tâches et le suivi de l'avancement.
  - *Références* : "Agile Practice Guide" du PMI, "Scrum: The Art of Doing Twice the Work in Half the Time" de Jeff Sutherland, Framework SAFe pour l'agilité à l'échelle.

- **Orchestration des agents spécialisés** : Développer un système d'orchestration avancé permettant de coordonner efficacement les différents agents spécialisés. S'inspirer des architectures de microservices et des patterns d'orchestration comme le Saga pattern ou le Choreography pattern. Implémenter un mécanisme de communication asynchrone entre agents basé sur des événements (Event-driven architecture).
  - *Références* : "Building Microservices" de Sam Newman, "Designing Data-Intensive Applications" de Martin Kleppmann, "Enterprise Integration Patterns" de Gregor Hohpe et Bobby Woolf.
  - *Outils* : Apache Kafka, RabbitMQ, ou implémentation personnalisée basée sur le module `orchestration` existant.

- **Monitoring et évaluation** : Créer des outils de suivi et d'évaluation des performances du système multi-agents. Développer des métriques spécifiques pour mesurer l'efficacité de l'analyse argumentative, la qualité des extractions, et la performance globale du système. Implémenter un système de logging avancé et des dashboards de visualisation.
  - *Références* : "Site Reliability Engineering" de Google, "Prometheus: Up & Running" de Brian Brazil.
  - *Outils* : Prometheus, Grafana, ELK Stack (Elasticsearch, Logstash, Kibana), ou solution personnalisée intégrée.

- **Documentation et transfert de connaissances** : Mettre en place un système de documentation continue et de partage des connaissances entre les différentes équipes. Créer une documentation technique détaillée, des guides d'utilisation, et des tutoriels pour faciliter l'onboarding de nouveaux contributeurs. Organiser des sessions de partage de connaissances et de retours d'expérience.
  - *Références* : "Documentation System" de Divio, "Building a Second Brain" de Tiago Forte.
  - *Outils* : Notion, Confluence, GitBook, ou solution basée sur GitHub Pages avec Jekyll/MkDocs.

- **Intégration continue et déploiement** : Développer un pipeline CI/CD adapté au contexte du projet pour faciliter l'intégration des contributions et le déploiement des nouvelles fonctionnalités. Automatiser les tests, la vérification de la qualité du code, et le déploiement des différentes composantes du système.
  - *Références* : "Continuous Delivery" de Jez Humble et David Farley, "DevOps Handbook" de Gene Kim et al.
  - *Outils* : GitHub Actions, Jenkins, GitLab CI/CD, ou solution personnalisée.

- **Gouvernance multi-agents** : Concevoir un système de gouvernance pour gérer les conflits entre agents, établir des priorités, et assurer la cohérence globale du système. S'inspirer des modèles de gouvernance des systèmes distribués et des organisations autonomes décentralisées (DAO).
  - *Références* : "Governing the Commons" d'Elinor Ostrom, recherches sur les systèmes multi-agents (SMA) du LIRMM et du LIP6.

#### Gestion des Sources

- **Amélioration du moteur d'extraction** : Perfectionner le système actuel qui combine paramétrage d'extraits et sources correspondantes.
- **Support de formats étendus** : Étendre les capacités du moteur d'extraction pour supporter davantage de formats de fichiers et de sources web.
- **Sécurisation des données** : Améliorer le système de chiffrement des sources et configurations d'extraits pour garantir la confidentialité.

#### Moteur Agentique

- **Abstraction du moteur agentique** : Créer une couche d'abstraction permettant d'utiliser différents frameworks agentiques (au-delà de Semantic Kernel).
- **Orchestration avancée** : Développer des stratégies d'orchestration plus sophistiquées pour la collaboration entre agents.
- **Mécanismes de résolution de conflits** : Implémenter des méthodes pour résoudre les désaccords entre agents lors de l'analyse argumentative.

#### Intégration MCP (Model Context Protocol)

##### Qu'est-ce que le Model Context Protocol (MCP) ?

Le Model Context Protocol (MCP) est un protocole ouvert standardisé qui permet aux applications d'IA de se connecter à des sources de données externes et des outils. Comparable à un "USB-C pour l'IA", il standardise la façon dont les modèles d'IA interagissent avec différentes sources de données et outils.

Le MCP offre plusieurs avantages clés:
- **Interopérabilité**: Connexion standardisée entre modèles et outils
- **Extensibilité**: Ajout facile de nouvelles capacités aux systèmes d'IA
- **Sécurité**: Contrôle précis des accès aux ressources externes
- **Flexibilité**: Support de différents mécanismes de transport

##### Projets d'intégration MCP proposés

- **Développement d'un serveur MCP pour l'analyse argumentative**: Publier le travail collectif sous forme d'un serveur MCP utilisable dans des applications comme Roo, Claude Desktop ou Semantic Kernel.

- **Outils MCP pour l'analyse argumentative**: Créer des outils MCP spécifiques pour:
  - Extraction d'arguments à partir de textes
  - Détection de sophismes
  - Formalisation logique d'arguments
  - Évaluation de la qualité argumentative

- **Ressources MCP pour l'argumentation**: Développer des ressources MCP donnant accès à:
  - Taxonomies de sophismes
  - Exemples d'arguments formels et informels
  - Schémas d'argumentation

##### Exemple d'utilisation avec un client MCP

```python
# Exemple d'utilisation du serveur MCP d'analyse argumentative
from mcp_client import MCPClient

# Connexion au serveur MCP
client = MCPClient("http://localhost:8080")

# Utilisation de l'outil d'extraction d'arguments
result = client.use_tool(
    "extract_arguments",
    {
        "text": "La Terre est plate car l'horizon semble plat. Cependant, les photos satellites montrent clairement que la Terre est sphérique."
    }
)

# Affichage des arguments extraits
for arg in result["arguments"]:
    print(f"- {arg['conclusion']} car {', '.join(arg['premises'])}")
```

##### Implémentation future

L'implémentation du serveur MCP est prévue comme l'un des projets intégrateurs, permettant de rendre les capacités d'analyse argumentative accessibles à un large éventail d'applications d'IA. Les étudiants intéressés par ce projet devront se familiariser avec:

- La spécification du protocole MCP
- Le développement de serveurs HTTP/WebSocket
- La sérialisation/désérialisation JSON
- La gestion des requêtes asynchrones

#### Agents Spécialistes

- **Agents de logique formelle** : Développer de nouveaux agents spécialisés utilisant différentes parties de Tweety.
- **Agent de détection de sophismes** : Améliorer la détection et la classification des sophismes dans les textes.
- **Agent de génération de contre-arguments** : Créer un agent capable de générer des contre-arguments pertinents.
- **Intégration de LLMs locaux légers** : Explorer l'utilisation de modèles de langage locaux de petite taille pour effectuer l'analyse argumentative, en particulier les modèles Qwen 3 récemment sortis. Cette approche permettrait de réduire la dépendance aux API externes, d'améliorer la confidentialité des données et potentiellement d'accélérer le traitement. Le projet pourrait inclure une comparaison des performances entre différents modèles locaux et les grands modèles via API, ainsi que des stratégies d'optimisation pour les cas d'usage spécifiques à l'analyse argumentative.
  - *Technologies clés* : Qwen 3, llama.cpp, GGUF, quantization, techniques d'optimisation pour l'inférence locale.
  - *Références* : Documentation Qwen 3, benchmarks HELM, recherches sur la distillation de modèles et l'optimisation pour l'inférence.

#### Indexation Sémantique

- **Index sémantique d'arguments** : Indexer les définitions, exemples et instances d'arguments fallacieux pour permettre des recherches par proximité sémantique.
- **Vecteurs de types d'arguments** : Définir par assemblage des vecteurs de types d'arguments fallacieux pour faciliter la découverte de nouvelles instances.

#### Automatisation

- **Automatisation de l'analyse** : Développer des outils pour lancer l'équivalent du notebook d'analyse dans le cadre d'automates longs sur des corpus.
- **Pipeline de traitement** : Créer un pipeline complet pour l'ingestion, l'analyse et la visualisation des résultats d'analyse argumentative.

#### Développement d'Interfaces Utilisateurs

- **Interface web pour l'analyse argumentative** : Développer une interface web moderne et intuitive permettant de visualiser et d'interagir avec les analyses argumentatives. Créer une expérience utilisateur fluide pour naviguer dans les structures argumentatives complexes, avec possibilité de filtrage, recherche et annotation.
  - *Technologies recommandées* : React/Vue.js/Angular pour le frontend, avec des bibliothèques comme D3.js ou Cytoscape.js pour la visualisation.
  - *Références* : "Argument Visualization Tools in the Classroom" de Scheuer et al., interfaces de Kialo ou Arguman comme inspiration.

- **Dashboard de monitoring** : Créer un tableau de bord permettant de suivre en temps réel l'activité des différents agents et l'état du système. Visualiser les métriques clés, les goulots d'étranglement, et l'utilisation des ressources. Implémenter des alertes et des notifications pour les événements critiques.
  - *Technologies recommandées* : Grafana, Tableau, ou solution personnalisée avec React et D3.js.
  - *Références* : "Information Dashboard Design" de Stephen Few, dashboards de Datadog ou New Relic comme inspiration.

- **Éditeur visuel d'arguments** : Concevoir un éditeur permettant de construire et de manipuler visuellement des structures argumentatives. Permettre la création, l'édition et la connexion d'arguments, de prémisses et de conclusions de manière intuitive, avec support pour différents formalismes argumentatifs.
  - *Technologies recommandées* : Framework de diagrammes comme JointJS, mxGraph (utilisé par draw.io), ou GoJS.
  - *Références* : "Argument Mapping" de Tim van Gelder, outils comme Rationale ou Argunet.

- **Visualisation de graphes d'argumentation** : Développer des outils de visualisation avancés pour les différents frameworks d'argumentation (Dung, bipolaire, pondéré, etc.). Implémenter des algorithmes de layout optimisés pour les graphes argumentatifs, avec support pour l'interaction et l'exploration.
  - *Technologies recommandées* : Bibliothèques spécialisées comme Sigma.js, Cytoscape.js, ou vis.js.
  - *Références* : "Computational Models of Argument: Proceedings of COMMA" (conférences biennales), travaux de Floris Bex sur la visualisation d'arguments.

- **Interface mobile** : Adapter l'interface utilisateur pour une utilisation sur appareils mobiles. Concevoir une expérience responsive ou développer une application mobile native/hybride permettant d'accéder aux fonctionnalités principales du système d'analyse argumentative.
  - *Technologies recommandées* : React Native, Flutter, ou PWA (Progressive Web App).
  - *Références* : "Mobile First" de Luke Wroblewski, "Responsive Web Design" d'Ethan Marcotte.

- **Accessibilité** : Améliorer l'accessibilité des interfaces pour les personnes en situation de handicap. Implémenter les standards WCAG 2.1 AA, avec support pour les lecteurs d'écran, la navigation au clavier, et les contrastes adaptés.
  - *Technologies recommandées* : Bibliothèques comme axe-core, pa11y, ou react-axe pour les tests d'accessibilité.
  - *Références* : "Inclusive Design Patterns" de Heydon Pickering, ressources du W3C Web Accessibility Initiative (WAI).

- **Système de collaboration en temps réel** : Développer des fonctionnalités permettant à plusieurs utilisateurs de travailler simultanément sur la même analyse argumentative, avec gestion des conflits et visualisation des contributions de chacun.
  - *Technologies recommandées* : Bibliothèques comme Socket.io, Yjs, ou ShareDB pour la collaboration en temps réel.
  - *Références* : "Building Real-time Applications with WebSockets" de Vanessa Wang et al., systèmes comme Google Docs ou Figma comme inspiration.

### Projets Intégrateurs

- **Système de débat assisté par IA** : Développer une application complète permettant à des utilisateurs de débattre avec l'assistance d'agents IA qui analysent et améliorent leurs arguments. Le système pourrait identifier les faiblesses argumentatives, suggérer des contre-arguments, et aider à structurer les débats de manière constructive.
  - *Technologies clés* : LLMs pour l'analyse et la génération d'arguments, frameworks d'argumentation de Tweety pour l'évaluation formelle, interface web interactive.
  - *Références* : "Computational Models of Argument" (COMMA), plateforme Kialo, recherches de Chris Reed sur les technologies d'argumentation.

- **Plateforme d'éducation à l'argumentation** : Créer un outil éducatif pour enseigner les principes de l'argumentation et aider à identifier les sophismes. Intégrer des tutoriels interactifs, des exercices pratiques, et un système de feedback automatisé basé sur l'analyse argumentative.
  - *Technologies clés* : Gamification, visualisation d'arguments, agents pédagogiques.
  - *Références* : "Critical Thinking: A Concise Guide" de Tracy Bowell et Gary Kemp, "Argumentation Mining" de Stede et Schneider, plateforme ArgTeach.

- **Système d'aide à la décision argumentative** : Développer un système qui aide à la prise de décision en analysant et évaluant les arguments pour et contre différentes options. Implémenter des méthodes de pondération des arguments, d'analyse multicritère, et de visualisation des compromis.
  - *Technologies clés* : Frameworks d'argumentation pondérés, méthodes d'aide à la décision multicritère (MCDM), visualisation interactive.
  - *Références* : "Decision Support Systems" de Power et Sharda, "Argumentation-based Decision Support" de Karacapilidis et Papadias, outils comme Rationale ou bCisive.

- **Plateforme collaborative d'analyse de textes** : Créer un environnement permettant à plusieurs utilisateurs de collaborer sur l'analyse argumentative de textes complexes. Intégrer des fonctionnalités de partage, d'annotation, de commentaire, et de révision collaborative.
  - *Technologies clés* : Collaboration en temps réel, gestion de versions, annotation de documents.
  - *Références* : "Computer Supported Cooperative Work" de Grudin, systèmes comme Hypothesis, PeerLibrary, ou CommentPress.

- **Assistant d'écriture argumentative** : Développer un outil d'aide à la rédaction qui suggère des améliorations pour renforcer la qualité argumentative des textes. Analyser la structure argumentative, identifier les faiblesses logiques, et proposer des reformulations ou des arguments supplémentaires.
  - *Technologies clés* : NLP avancé, analyse rhétorique automatisée, génération de texte.
  - *Références* : "Automated Essay Scoring" de Shermis et Burstein, recherches sur l'argumentation computationnelle de l'ARG-tech Centre, outils comme Grammarly ou Hemingway comme inspiration.

- **Système d'analyse de débats politiques** : Développer un outil d'analyse des débats politiques en temps réel, capable d'identifier les arguments, les sophismes, et les stratégies rhétoriques utilisées par les participants. Fournir une évaluation objective de la qualité argumentative et factuelle des interventions.
  - *Technologies clés* : Traitement du langage en temps réel, fact-checking automatisé, analyse de sentiment.
  - *Références* : "Computational Approaches to Analyzing Political Discourse" de Hovy et Lim, projets comme FactCheck.org ou PolitiFact.

- **Plateforme de délibération citoyenne** : Créer un espace numérique pour faciliter les délibérations citoyennes sur des sujets complexes, en structurant les échanges selon des principes argumentatifs rigoureux et en favorisant la construction collaborative de consensus.
  - *Technologies clés* : Modération assistée par IA, visualisation d'opinions, mécanismes de vote et de consensus.
  - *Références* : "Democracy in the Digital Age" de Wilhelm, plateformes comme Decidim, Consul, ou vTaiwan.

## Directives de Contribution et Organisation

Cette section présente une approche flexible pour contribuer au projet Intelligence Symbolique, favorisant l'auto-organisation des équipes d'étudiants tout en maintenant la qualité et la cohérence du code produit.

### Organisation des Équipes et Gestion de Projet

Plutôt que d'imposer un protocole de contribution strict, nous encourageons les étudiants à s'organiser selon leurs préférences et compétences. Certains étudiants sont invités à prendre en main l'aspect gestion de projet, en assumant des rôles tels que :

- **Chef de projet** : Coordination générale, planification des sprints, suivi de l'avancement
- **Responsable technique** : Architecture, standards de code, revue technique
- **Responsable qualité** : Tests, documentation, processus de revue
- **Responsable intégration** : Gestion des pull requests, résolution des conflits, déploiements

**Les étudiants qui démontreront des compétences en gestion de projet et en coordination d'équipe se verront attribuer des droits d'administrateur sur le dépôt principal**, leur permettant de faciliter le processus d'intégration des contributions.

### Principes de Base pour la Contribution

Bien que nous privilégions l'auto-organisation, voici quelques principes fondamentaux pour assurer une collaboration efficace :

#### Workflow Git Recommandé

1. **Fork et clone** : Créez un fork du dépôt principal et clonez-le localement
2. **Branches thématiques** : Créez des branches dédiées à chaque fonctionnalité ou correction
3. **Pull Requests régulières** : Soumettez des PR fréquentes pour faciliter l'intégration continue
4. **Communication** : Documentez clairement l'objectif et les changements de chaque contribution

#### Standards de Code Suggérés

- **Lisibilité** : Privilégiez un code clair et bien commenté
- **Cohérence** : Respectez les conventions existantes du projet
- **Tests** : Incluez des tests appropriés pour vos contributions
- **Documentation** : Mettez à jour la documentation concernée

### Documentation et Partage de Connaissances

La documentation est essentielle pour la collaboration et la pérennité du projet :

- **READMEs** : Chaque module devrait avoir une documentation claire de son fonctionnement
- **Exemples** : Fournissez des exemples d'utilisation pour les fonctionnalités complexes
- **Partage d'expérience** : Organisez des sessions de partage de connaissances entre équipes

### Revue et Intégration

Le processus de revue devrait être collaboratif et constructif :

- **Revue par les pairs** : Encouragez la revue de code entre équipes
- **Feedback constructif** : Formulez des commentaires précis et bienveillants
- **Amélioration continue** : Utilisez les retours pour améliorer vos contributions futures

### Contexte Académique

En tant que projet académique, certaines spécificités s'appliquent :

- **Attribution** : Identifiez clairement les contributeurs de chaque partie du code
- **Apprentissage** : Les revues de code sont aussi des opportunités d'apprentissage
- **Évaluation** : La qualité des contributions et l'implication dans la gestion de projet font partie de l'évaluation
- **Échéances** : Respectez le calendrier académique pour vos contributions

### Ressources pour la Gestion de Projet

Pour les étudiants souhaitant prendre en charge la gestion de projet, voici quelques ressources utiles :

- **Outils** : GitHub Projects, Trello, Jira (version académique gratuite)
- **Méthodologies** : Scrum, Kanban, ou approches hybrides adaptées au contexte académique
- **Documentation** : Templates de documentation, guides de contribution, checklists de revue

Les étudiants intéressés par la prise en charge de la gestion de projet sont invités à se manifester auprès de l'équipe enseignante pour discuter des responsabilités et des droits d'administration sur le dépôt.

## Ressources et Documentation

Pour vous aider dans la réalisation de votre projet, vous trouverez dans ce dépôt :

- Des README détaillés pour chaque composant du système
- Des notebooks explicatifs et interactifs
- Des exemples d'utilisation des différentes bibliothèques
- Une documentation sur l'architecture du système

N'hésitez pas à explorer les différents répertoires du projet pour mieux comprendre son fonctionnement et identifier les opportunités d'amélioration.

## Fichiers Récemment Ajoutés

Voici les fichiers récemment ajoutés au projet qui méritent une attention particulière :

### Optimisation de l'Agent Informel

- **[`agents/utils/informal_optimization/`](./argumentiation_analysis/agents/utils/informal_optimization/README.md)** : Outils pour l'optimisation de l'agent d'analyse informelle.
  - **[`analyze_taxonomy_usage.py`](./argumentiation_analysis/agents/utils/informal_optimization/analyze_taxonomy_usage.py)** : Analyse l'utilisation de la taxonomie des sophismes.
  - **[`improve_informal_agent.py`](./argumentiation_analysis/agents/utils/informal_optimization/improve_informal_agent.py)** : Améliore les performances de l'agent informel.
  - **[`optimize_informal_agent.py`](./argumentiation_analysis/agents/utils/informal_optimization/optimize_informal_agent.py)** : Optimise les prompts et définitions de l'agent informel.
  - **[`taxonomy_analysis/`](./argumentiation_analysis/agents/utils/informal_optimization/taxonomy_analysis/)** : Visualisations et analyses de la taxonomie des sophismes.

### Tests et Orchestration à Grande Échelle

- **[`agents/test_orchestration_scale.py`](./argumentiation_analysis/agents/test_orchestration_scale.py)** : Test d'orchestration à grande échelle.
- **[`agents/test_informal_agent.py`](./argumentiation_analysis/agents/test_informal_agent.py)** : Test spécifique de l'agent d'analyse informelle.
- **[`agents/rapport_test_orchestration_echelle.md`](./argumentiation_analysis/agents/rapport_test_orchestration_echelle.md)** : Rapport sur les tests d'orchestration à grande échelle.

### Outils de Vérification et Réparation

- **[`utils/run_verify_extracts.py`](./argumentiation_analysis/utils/run_verify_extracts.py)** : Script pour vérifier la validité des extraits.
- **[`utils/extract_repair/verify_extracts.py`](./argumentiation_analysis/utils/extract_repair/verify_extracts.py)** : Vérifie la validité des extraits de texte.
- **[`utils/extract_repair/verify_extracts_with_llm.py`](./argumentiation_analysis/utils/extract_repair/verify_extracts_with_llm.py)** : Utilise un LLM pour vérifier les extraits.
- **[`utils/extract_repair/fix_missing_first_letter.py`](./argumentiation_analysis/utils/extract_repair/fix_missing_first_letter.py)** : Corrige le problème de première lettre manquante dans les extraits.

### Scripts d'Exécution

- **[`run_analysis.py`](./argumentiation_analysis/run_analysis.py)** : Script principal pour lancer l'analyse argumentative.
- **[`run_extract_editor.py`](./argumentiation_analysis/run_extract_editor.py)** : Lance l'éditeur de marqueurs d'extraits.
- **[`run_extract_repair.py`](./argumentiation_analysis/run_extract_repair.py)** : Lance la réparation des bornes défectueuses.
- **[`run_orchestration.py`](./argumentiation_analysis/run_orchestration.py)** : Lance l'orchestration des agents.

### Rapports et Documentation

- **[`rapport_verification.html`](./argumentiation_analysis/rapport_verification.html)** : Rapport de vérification des extraits.
- **[`repair_report.html`](./argumentiation_analysis/repair_report.html)** : Rapport de réparation des extraits.
