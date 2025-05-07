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

Pour une description détaillée de tous les sujets de projets, veuillez consulter le document [**Sujets de Projets Détaillés**](./docs/sujets_projets_detailles.md) qui présente l'ensemble des projets possibles avec leurs spécifications complètes.

Les projets sont organisés en trois catégories principales :
1. **Fondements théoriques et techniques** : Projets centrés sur les aspects formels, logiques et théoriques de l'argumentation
2. **Développement système et infrastructure** : Projets axés sur l'architecture, l'orchestration et les composants techniques
3. **Expérience utilisateur et applications** : Projets orientés vers les interfaces, visualisations et cas d'usage concrets

Chaque sujet est présenté avec une structure standardisée :
- **Contexte** : Présentation du domaine et de son importance
- **Objectifs** : Ce que le projet vise à accomplir
- **Technologies clés** : Outils, frameworks et concepts essentiels
- **Niveau de difficulté** : ⭐ (Accessible) à ⭐⭐⭐⭐⭐ (Très avancé)
- **Estimation d'effort** : Temps de développement estimé en semaines-personnes
- **Interdépendances** : Liens avec d'autres sujets de projets
- **Références** : Sources et documentation pour approfondir
- **Livrables attendus** : Résultats concrets à produire

### 1. Fondements théoriques et techniques

#### 1.1 Logiques formelles et raisonnement

##### 1.1.1 Intégration des logiques propositionnelles avancées
- **Contexte** : La logique propositionnelle constitue la base de nombreux systèmes de raisonnement automatique. Le module `logics.pl` de Tweety offre des fonctionnalités avancées encore peu exploitées dans le projet.
- **Objectifs** : Améliorer l'agent PL existant pour exploiter davantage les fonctionnalités du module, notamment les solveurs SAT (SAT4J interne ou solveurs externes comme Lingeling, CaDiCaL), la conversion DIMACS, et les opérations avancées sur les formules (DNF, CNF, simplification). Implémenter des requêtes plus sophistiquées comme la vérification de satisfiabilité, la recherche de modèles, et l'analyse d'implications logiques. Le notebook Tweety démontre comment manipuler des formules propositionnelles, créer des mondes possibles, et utiliser différents raisonneurs pour vérifier la satisfiabilité et trouver des modèles.
- **Technologies clés** : Tweety `logics.pl`, solveurs SAT, Java-Python bridge
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Base pour les projets de maintenance de la vérité (1.4) et d'argumentation formelle (1.2)
- **Références** :
  - "SAT_SMT_by_example.pdf" (2023)
  - "Artificial Intelligence: A Modern Approach" (Chapitres sur la logique propositionnelle)
  - Documentation Tweety `logics.pl`
##### 1.1.2 Logique du premier ordre (FOL)
- **Contexte** : La logique du premier ordre permet d'exprimer des relations plus complexes que la logique propositionnelle, avec des quantificateurs et des prédicats.
- **Objectifs** : Développer un nouvel agent utilisant le module `logics.fol` de Tweety pour analyser des arguments plus complexes impliquant des quantificateurs (`∀`, `∃`) et des prédicats. Cet agent pourrait tenter de traduire des arguments exprimés en langage naturel (avec quantificateurs) en formules FOL, définir des signatures logiques (types/sorts, constantes, prédicats, fonctions), et utiliser les raisonneurs intégrés (`SimpleFolReasoner`, `EFOLReasoner`). L'intégration d'un prouveur externe comme EProver permettrait de vérifier des implications logiques plus complexes.
- **Technologies clés** : Tweety `logics.fol`, prouveurs FOL, traduction langage naturel vers FOL
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Extension de 1.1.1, base pour 1.2.4 (ABA)
- **Références** :
  - "Artificial Intelligence: A Modern Approach" de Russell & Norvig (Chapitres sur FOL)
  - "Automated Theorem Proving" (2002)
  - Documentation Tweety `logics.fol`

##### 1.1.3 Logique modale
- **Contexte** : Les logiques modales permettent de raisonner sur des notions comme la nécessité, la possibilité, les croyances ou les connaissances.
- **Objectifs** : Créer un agent spécialisé utilisant le module `logics.ml` de Tweety pour raisonner sur des modalités comme la nécessité (`[]`), la possibilité (`<>`), les croyances ou les connaissances. Cet agent pourrait analyser des arguments impliquant des notions de possibilité, nécessité, obligation ou permission, en utilisant SimpleMlReasoner ou SPASSMlReasoner (avec intégration de SPASS).
- **Technologies clés** : Tweety `logics.ml`, raisonneurs modaux, SPASS
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Peut être combiné avec 1.4 (maintenance de la vérité)
- **Références** :
  - "Handbook of Modal Logic"
  - "Artificial Intelligence: A Modern Approach" (Sections sur la logique modale)
  - Documentation Tweety `logics.ml`

##### 1.1.4 Logique de description (DL)
- **Contexte** : Les logiques de description sont utilisées pour représenter des connaissances structurées sous forme de concepts, rôles et individus.
- **Objectifs** : Développer un agent utilisant le module `logics.dl` de Tweety pour modéliser des connaissances structurées. Cet agent pourrait construire des TBox (axiomes terminologiques) et ABox (assertions sur les individus), et raisonner sur la subsomption, l'instanciation et la consistance. Le notebook Tweety montre comment définir des concepts atomiques, des rôles, des individus, et comment construire des axiomes d'équivalence et des assertions pour créer une base de connaissances DL complète.
- **Technologies clés** : Tweety `logics.dl`, ontologies, raisonneurs DL
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.3.1 (ontologies AIF.owl)
- **Références** :
  - "The Description Logic Handbook - Theory, Implementation and Applications" (2003)
  - "What is an Ontology" (2009)
  - "Foundations of Semantic Web Technologies" (2008)

##### 1.1.5 Formules booléennes quantifiées (QBF)
- **Contexte** : Les QBF étendent la logique propositionnelle avec des quantificateurs, permettant de modéliser des problèmes PSPACE-complets.
- **Objectifs** : Explorer l'utilisation du module `logics.qbf` de Tweety pour modéliser et résoudre des problèmes PSPACE-complets. Cet agent pourrait traiter des problèmes de planification conditionnelle, de jeux à deux joueurs, ou de vérification formelle qui dépassent la portée de SAT.
- **Technologies clés** : Tweety `logics.qbf`, solveurs QBF, format QDIMACS
- **Niveau de difficulté** : ⭐⭐⭐⭐⭐
- **Interdépendances** : Extension de 1.1.1, peut être utilisé dans 1.5.2 (vérification formelle)
- **Références** :
  - "SAT_SMT_by_example.pdf" (2023)
  - "Handbook of Satisfiability"
  - Documentation Tweety `logics.qbf`

##### 1.1.6 Logique conditionnelle (CL)
- **Contexte** : Les logiques conditionnelles permettent de raisonner sur des énoncés de la forme "Si A est vrai, alors B est typiquement vrai".
- **Objectifs** : Implémenter un agent utilisant le module `logics.cl` de Tweety pour raisonner sur des conditionnels. Le notebook Tweety démontre comment créer une base conditionnelle avec des conditionnels comme (f|b), (b|p), (¬f|p), et comment calculer une fonction de classement (ranking) pour évaluer ces conditionnels.
- **Technologies clés** : Tweety `logics.cl`, raisonnement non-monotone
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Peut être combiné avec 1.2 (frameworks d'argumentation)
- **Références** :
  - "Reasoning-with-probabilistic-and-deterministic-graphical-models-exact-algorithms" (2013)
  - Documentation Tweety `logics.cl`
#### 1.2 Frameworks d'argumentation

##### 1.2.1 Cadres d'argumentation abstraits (Dung)
- **Contexte** : Les cadres d'argumentation abstraits (AAF) de Dung sont fondamentaux en théorie de l'argumentation formelle.
- **Objectifs** : Développer un agent utilisant le module `arg.dung` de Tweety pour modéliser et analyser des structures argumentatives abstraites (AAF). Cet agent devrait permettre de construire des graphes d'arguments et d'attaques (`DungTheory`), et surtout de calculer l'acceptabilité des arguments selon différentes sémantiques (admissible, complète, préférée, stable, fondée, idéale, semi-stable, CF2...). Il est crucial de comprendre la signification de chaque sémantique (ex: stable = point de vue cohérent et maximal, fondée = sceptique et bien fondée).
- **Technologies clés** : Tweety `arg.dung`, théorie des graphes, sémantiques d'argumentation
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Base pour tous les autres frameworks d'argumentation (1.2.x)
- **Références** :
  - Article fondateur de P. M. Dung (1995) "On the acceptability of arguments..."
  - Survey de Baroni, Caminada, Giacomin (2011) "An introduction to argumentation semantics"
  - "Implementing KR Approaches with Tweety" (2018)

##### 1.2.2 Argumentation structurée (ASPIC+)
- **Contexte** : ASPIC+ est un framework qui permet de construire des arguments à partir de règles strictes et défaisables.
- **Objectifs** : Créer un agent utilisant le module `arg.aspic` de Tweety pour construire des arguments à partir de règles strictes et défaisables. Cet agent pourrait modéliser des bases de connaissances avec axiomes et règles, gérer les préférences entre règles, et analyser les attaques (rebutting, undercutting, undermining).
- **Technologies clés** : Tweety `arg.aspic`, règles défaisables, préférences
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Basé sur 1.2.1, peut être combiné avec 1.4 (maintenance de la vérité)
- **Références** :
  - "Implementing KR Approaches with Tweety" (2018)
  - "Argumentation in Artificial Intelligence" (Chapitres sur ASPIC+)
  - Documentation Tweety `arg.aspic`

##### 1.2.3 Programmation logique défaisable (DeLP)
- **Contexte** : DeLP combine programmation logique et argumentation pour gérer les connaissances contradictoires.
- **Objectifs** : Implémenter un agent utilisant le module `arg.delp` de Tweety pour raisonner avec des règles strictes et défaisables dans un cadre de programmation logique. Le notebook Tweety démontre comment charger un programme DeLP à partir d'un fichier (comme birds2.txt) et effectuer des requêtes sur ce programme, en utilisant la spécificité généralisée comme critère de comparaison.
- **Technologies clés** : Tweety `arg.delp`, programmation logique, raisonnement dialectique
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.2.2 (ASPIC+) et 1.1.1 (logique propositionnelle)
- **Références** :
  - "Implementing KR Approaches with Tweety" (2018)
  - "Defeasible Logic Programming: An Argumentative Approach"
  - Documentation Tweety `arg.delp`

##### 1.2.4 Argumentation basée sur les hypothèses (ABA)
- **Contexte** : ABA est un framework où certains littéraux sont désignés comme hypothèses pouvant être remises en question.
- **Objectifs** : Développer un agent utilisant le module `arg.aba` de Tweety pour modéliser l'argumentation où certains littéraux sont désignés comme hypothèses. Cet agent pourrait analyser les attaques entre arguments dérivés de ces hypothèses et déterminer leur acceptabilité.
- **Technologies clés** : Tweety `arg.aba`, raisonnement avec hypothèses
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.1.2 (FOL) et 1.2.1 (Dung)
- **Références** :
  - "Implementing KR Approaches with Tweety" (2018)
  - "Assumption-Based Argumentation"
  - Documentation Tweety `arg.aba`

##### 1.2.5 Argumentation déductive
- **Contexte** : L'argumentation déductive représente les arguments comme des paires (Support, Conclusion) où le support implique logiquement la conclusion.
- **Objectifs** : Créer un agent utilisant le module `arg.deductive` de Tweety pour construire des arguments comme des paires (Support, Conclusion) où le support est un sous-ensemble minimal et consistant de la base de connaissances qui implique logiquement la conclusion.
- **Technologies clés** : Tweety `arg.deductive`, logique déductive, catégoriseurs
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Lié à 1.1.1 (logique propositionnelle) et 1.2.1 (Dung)
- **Références** :
  - "Implementing KR Approaches with Tweety" (2018)
  - "Logical Models of Argument"
  - Documentation Tweety `arg.deductive`

##### 1.2.6 Abstract Dialectical Frameworks (ADF)
- **Contexte** : Les ADF généralisent les AAF de Dung en associant à chaque argument une condition d'acceptation.
- **Objectifs** : Implémenter un agent utilisant le module `arg.adf` de Tweety. Les ADF généralisent les AAF de Dung en associant à chaque argument une condition d'acceptation (une formule propositionnelle sur l'état des autres arguments), permettant de modéliser des dépendances plus complexes que la simple attaque (ex: support, attaque conjointe). L'agent devrait permettre de définir ces conditions et de calculer les sémantiques ADF (admissible, complète, préférée, stable, fondée, modèle à 2 valeurs).
- **Technologies clés** : Tweety `arg.adf`, solveurs SAT incrémentaux, formules propositionnelles
- **Niveau de difficulté** : ⭐⭐⭐⭐⭐
- **Interdépendances** : Extension de 1.2.1 (Dung), utilise 1.1.1 (logique propositionnelle)
- **Références** :
  - Article fondateur de Brewka et al. (2013) "Abstract Dialectical Frameworks"
  - "Implementing KR Approaches with Tweety" (2018)
  - Documentation Tweety `arg.adf`

##### 1.2.7 Frameworks bipolaires (BAF)
- **Contexte** : Les BAF étendent les AAF en incluant des relations de support en plus des attaques.
- **Objectifs** : Développer un agent utilisant le module `arg.bipolar` de Tweety pour modéliser des cadres d'argumentation incluant à la fois des relations d'attaque et de support entre arguments. Comprendre les différentes interprétations du support (déductif, nécessaire, évidentiel...) et les sémantiques associées proposées dans la littérature et implémentées dans Tweety.
- **Technologies clés** : Tweety `arg.bipolar`, relations de support, graphes bipolaires
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Extension de 1.2.1 (Dung)
- **Références** :
  - Travaux de Cayrol et Lagasquie-Schiex sur les BAF
  - Survey de Cohen et al. (2014) sur l'argumentation bipolaire
  - "Implementing KR Approaches with Tweety" (2018)
  - Documentation Tweety `arg.bipolar`

##### 1.2.8 Frameworks avancés et extensions
- **Contexte** : De nombreuses extensions des frameworks d'argumentation de base ont été proposées pour modéliser des aspects spécifiques.
- **Objectifs** : Explorer et implémenter différentes extensions des frameworks d'argumentation, telles que les frameworks pondérés (WAF), sociaux (SAF), SetAF, frameworks étendus (attaques sur attaques), et les sémantiques basées sur le classement ou probabilistes.
- **Technologies clés** : Modules Tweety `arg.weighted`, `arg.social`, `arg.setaf`, `arg.extended`, `arg.rankings`, `arg.prob`
- **Niveau de difficulté** : ⭐⭐⭐⭐⭐
- **Interdépendances** : Extension de tous les frameworks précédents (1.2.1-1.2.7)
- **Références** :
  - "Implementing KR Approaches with Tweety" (2018)
  - Documentation des modules Tweety correspondants
  - Littérature spécifique à chaque extension
#### 1.3 Ingénierie des connaissances

##### 1.3.1 Intégration d'ontologies AIF.owl
- **Contexte** : L'Argument Interchange Format (AIF) est un standard pour représenter la structure des arguments.
- **Objectifs** : Développer un moteur sémantique basé sur l'ontologie AIF (Argument Interchange Format) en OWL. L'objectif est de représenter la structure fine des arguments extraits (prémisses, conclusion, schémas d'inférence, relations d'attaque/support) en utilisant les classes AIF (I-Nodes, RA-Nodes, CA-Nodes).
- **Technologies clés** : Tweety `logics.dl`, OWL, ontologies, Owlready2
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.1.4 (logique de description) et 1.3.3 (Knowledge Graph)
- **Références** :
  - Spécification AIF (Rahwan, Reed et al.)
  - Documentation AIFdb
  - "Argumentation Mining" de Stede & Schneider (Chapitre sur la représentation)
  - "What is an Ontology" (2009)
  - "Foundations of Semantic Web Technologies" (2008)

##### 1.3.2 Classification des arguments fallacieux
- **Contexte** : Les sophismes sont des erreurs de raisonnement qui peuvent sembler valides mais ne le sont pas.
- **Objectifs** : Corriger, compléter et intégrer l'ontologie des sophismes (inspirée du projet Argumentum ou autre source). L'objectif est de disposer d'une taxonomie formelle des types de sophismes. Utiliser cette ontologie pour guider l'agent de détection de sophismes et pour structurer les résultats de l'analyse.
- **Technologies clés** : Ontologies, taxonomies, logique de description
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Lié à 2.3.2 (agent de détection de sophismes) et 1.3.1 (ontologies AIF)
- **Références** :
  - "Logically Fallacious" de Bo Bennett
  - Taxonomie des sophismes sur Wikipedia
  - Projet Argumentum (si accessible)
  - "Ontology-based systems engineering - a state-of-the-art review" (2019)

##### 1.3.3 Knowledge Graph argumentatif
- **Contexte** : Les graphes de connaissances permettent de représenter des informations complexes et leurs relations.
- **Objectifs** : Remplacer la structure JSON actuelle de l'état partagé par un graphe de connaissances plus expressif et interrogeable, en s'inspirant des structures de graphe utilisées dans les différents frameworks d'argumentation de Tweety.
- **Technologies clés** : Graphes de connaissances, bases de données de graphes, requêtes SPARQL
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.3.1 (ontologies AIF) et 2.1.2 (orchestration des agents)
- **Références** :
  - "Knowledge graphs - 3447772.pdf" (2021)
  - "Making sense of sensory input" (2019)
  - Documentation sur les bases de données de graphes (Neo4j, etc.)

#### 1.4 Maintenance de la vérité et résolution de conflits

##### 1.4.1 Intégration des modules de maintenance de la vérité
- **Contexte** : La maintenance de la vérité est essentielle pour gérer l'évolution des connaissances et résoudre les conflits.
- **Objectifs** : Résoudre les problèmes d'import potentiels des modules `beliefdynamics` de Tweety et les intégrer au système. Ces modules sont cruciaux pour gérer l'évolution des connaissances et la résolution des conflits. Explorer les opérateurs de révision de croyances, de contraction, et d'update.
- **Technologies clés** : Tweety `beliefdynamics`, théorie AGM, opérateurs de révision
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Utilise 1.1.1 (logique propositionnelle), peut être combiné avec 1.4.2 (révision multi-agents)
- **Références** :
  - Théorie AGM (Alchourrón, Gärdenfors, Makinson)
  - Travaux de Katsuno & Mendelzon
  - "Reasoning-with-probabilistic-and-deterministic-graphical-models-exact-algorithms" (2013)
  - Documentation Tweety `beliefdynamics`

##### 1.4.2 Révision de croyances multi-agents
- **Contexte** : Dans un système multi-agents, chaque agent peut avoir ses propres croyances qui doivent être réconciliées.
- **Objectifs** : Développer un agent utilisant le module `beliefdynamics.mas` de Tweety pour modéliser la révision de croyances dans un contexte multi-agents, où chaque information est associée à un agent source et où un ordre de crédibilité existe entre les agents.
- **Technologies clés** : Tweety `beliefdynamics.mas`, révision de croyances, crédibilité des sources
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Extension de 1.4.1, lié à 2.1.6 (gouvernance multi-agents)
- **Références** :
  - "Multi Agent Systems" (2010)
  - "A review of cooperative multi-agent deep reinforcement learning" (2021)
  - Documentation Tweety `beliefdynamics.mas`

##### 1.4.3 Mesures d'incohérence et résolution
- **Contexte** : Quantifier et résoudre les incohérences est crucial pour maintenir la qualité des bases de connaissances.
- **Objectifs** : Intégrer les mesures d'incohérence de Tweety (`logics.pl.analysis`) pour quantifier le degré d'incohérence d'un ensemble d'informations, et implémenter des méthodes de résolution comme l'énumération de MUS (Minimal Unsatisfiable Subsets) et MaxSAT.
- **Technologies clés** : Tweety `logics.pl.analysis`, MUS, MaxSAT, mesures d'incohérence
- **Niveau de difficulté** : ⭐⭐⭐⭐⭐
- **Interdépendances** : Utilise 1.1.1 (logique propositionnelle), lié à 1.4.1 (maintenance de la vérité)
- **Références** :
  - Survey de Hunter et Konieczny sur les mesures d'incohérence
  - "Reasoning-with-probabilistic-and-deterministic-graphical-models-exact-algorithms" (2013)
  - "SAT_SMT_by_example.pdf" (2023)
  - "Handbook of Satisfiability"
  - Documentation Tweety `logics.pl.analysis`

#### 1.5 Planification et vérification formelle

##### 1.5.1 Intégration d'un planificateur symbolique
- **Contexte** : La planification automatique permet de générer des séquences d'actions pour atteindre des objectifs.
- **Objectifs** : Développer un agent capable de générer des plans d'action basés sur des objectifs argumentatifs, en explorant le module `action` de Tweety pour la modélisation des actions et la planification.
- **Technologies clés** : Tweety `action`, planification automatique, PDDL
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Peut utiliser 1.1.5 (QBF) pour la planification conditionnelle
- **Références** :
  - "Automated planning" (2010)
  - "Automated planning and acting - book" (2016)
  - "Integrated Task and motion planning" (2020)
  - Documentation Tweety `action`

##### 1.5.2 Vérification formelle d'arguments
- **Contexte** : La vérification formelle permet de garantir que les arguments respectent certaines propriétés.
- **Objectifs** : Développer des méthodes de vérification formelle pour garantir la validité des arguments dans un contexte contractuel, en utilisant potentiellement les capacités QBF ou FOL de Tweety.
- **Technologies clés** : Vérification formelle, model checking, prouveurs de théorèmes
- **Niveau de difficulté** : ⭐⭐⭐⭐⭐
- **Interdépendances** : Utilise 1.1.1-1.1.5 (logiques formelles), lié à 1.5.3 (contrats argumentatifs)
- **Références** :
  - "The Lean theorem prover" (2015)
  - "The Lean 4 Theorem Prover and Programming Language" (2021)
  - "SAT_SMT_by_example.pdf" (2023)
  - Documentation sur les prouveurs de théorèmes

##### 1.5.3 Formalisation de contrats argumentatifs
- **Contexte** : Les smart contracts peuvent être utilisés pour formaliser et exécuter des protocoles d'argumentation.
- **Objectifs** : Explorer l'utilisation de smart contracts pour formaliser et exécuter des protocoles d'argumentation, en s'appuyant sur les différents formalismes d'argumentation disponibles dans Tweety.
- **Technologies clés** : Smart contracts, blockchain, protocoles d'argumentation
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.2 (frameworks d'argumentation) et 1.5.2 (vérification formelle)
- **Références** :
  - "Bitcoin and Beyond - Cryptocurrencies, blockchain and global governance" (2018)
  - "Survey on blockchain based smart contracts - Applications, opportunities and challenges" (2021)
  - Documentation sur les plateformes de smart contracts (Ethereum, etc.)
### 2. Développement système et infrastructure

#### 2.1 Architecture et orchestration

##### 2.1.1 Gestion de projet agile
- **Contexte** : Une méthodologie de gestion de projet adaptée est essentielle pour coordonner efficacement les contributions.
- **Objectifs** : Mettre en place une méthodologie agile adaptée au contexte du projet, avec définition des rôles, des cérémonies et des artefacts. Implémenter un système de suivi basé sur Scrum ou Kanban, avec des sprints adaptés au calendrier académique.
- **Technologies clés** : Jira, Trello, GitHub Projects, méthodologies agiles
- **Niveau de difficulté** : ⭐⭐
- **Interdépendances** : Base pour tous les autres projets, particulièrement 2.1.5 (intégration continue)
- **Références** :
  - "Agile Practice Guide" du PMI
  - "Scrum: The Art of Doing Twice the Work in Half the Time" de Jeff Sutherland
  - Framework SAFe pour l'agilité à l'échelle

##### 2.1.2 Orchestration des agents spécialisés
- **Contexte** : La coordination efficace des agents spécialisés est cruciale pour le bon fonctionnement du système.
- **Objectifs** : Développer un système d'orchestration avancé permettant de coordonner efficacement les différents agents spécialisés. S'inspirer des architectures de microservices et des patterns d'orchestration comme le Saga pattern ou le Choreography pattern. Implémenter un mécanisme de communication asynchrone entre agents basé sur des événements.
- **Technologies clés** : Architecture event-driven, patterns d'orchestration, communication asynchrone
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 2.3 (moteur agentique) et 2.1.6 (gouvernance multi-agents)
- **Références** :
  - "Building Microservices" de Sam Newman
  - "Designing Data-Intensive Applications" de Martin Kleppmann
  - "Enterprise Integration Patterns" de Gregor Hohpe et Bobby Woolf

##### 2.1.3 Monitoring et évaluation
- **Contexte** : Le suivi des performances et la détection des problèmes sont essentiels pour maintenir la qualité du système.
- **Objectifs** : Créer des outils de suivi et d'évaluation des performances du système multi-agents. Développer des métriques spécifiques pour mesurer l'efficacité de l'analyse argumentative, la qualité des extractions, et la performance globale du système. Implémenter un système de logging avancé et des dashboards de visualisation.
- **Technologies clés** : Prometheus, Grafana, ELK Stack, métriques personnalisées
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Lié à 3.1.2 (dashboard de monitoring)
- **Références** :
  - "Site Reliability Engineering" de Google
  - "Prometheus: Up & Running" de Brian Brazil
  - Documentation sur les systèmes de monitoring

##### 2.1.4 Documentation et transfert de connaissances
- **Contexte** : Une documentation claire et complète est essentielle pour la maintenance et l'évolution du projet.
- **Objectifs** : Mettre en place un système de documentation continue et de partage des connaissances entre les différentes équipes. Créer une documentation technique détaillée, des guides d'utilisation, et des tutoriels pour faciliter l'onboarding de nouveaux contributeurs.
- **Technologies clés** : Notion, Confluence, GitBook, GitHub Pages
- **Niveau de difficulté** : ⭐⭐
- **Interdépendances** : Transversal à tous les projets
- **Références** :
  - "Documentation System" de Divio
  - "Building a Second Brain" de Tiago Forte
  - Bonnes pratiques de documentation technique

##### 2.1.5 Intégration continue et déploiement
- **Contexte** : L'automatisation des tests et du déploiement permet d'assurer la qualité et la disponibilité du système.
- **Objectifs** : Développer un pipeline CI/CD adapté au contexte du projet pour faciliter l'intégration des contributions et le déploiement des nouvelles fonctionnalités. Automatiser les tests, la vérification de la qualité du code, et le déploiement des différentes composantes du système.
- **Technologies clés** : GitHub Actions, Jenkins, GitLab CI/CD
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Lié à 2.1.1 (gestion de projet) et 2.5 (automatisation)
- **Références** :
  - "Continuous Delivery" de Jez Humble et David Farley
  - "DevOps Handbook" de Gene Kim et al.
  - Documentation sur les outils CI/CD

##### 2.1.6 Gouvernance multi-agents
- **Contexte** : La coordination de multiples agents nécessite des mécanismes de gouvernance pour résoudre les conflits et assurer la cohérence.
- **Objectifs** : Concevoir un système de gouvernance pour gérer les conflits entre agents, établir des priorités, et assurer la cohérence globale du système. S'inspirer des modèles de gouvernance des systèmes distribués et des organisations autonomes décentralisées (DAO).
- **Technologies clés** : Systèmes multi-agents, mécanismes de consensus, résolution de conflits
- **Niveau de difficulté** : ⭐⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.4.2 (révision de croyances multi-agents) et 2.1.2 (orchestration)
- **Références** :
  - "Governing the Commons" d'Elinor Ostrom
  - Recherches sur les systèmes multi-agents (SMA) du LIRMM et du LIP6
  - Littérature sur les mécanismes de gouvernance distribuée

#### 2.2 Gestion des sources et données

##### 2.2.1 Amélioration du moteur d'extraction
- **Contexte** : L'extraction précise des sources est fondamentale pour l'analyse argumentative.
- **Objectifs** : Perfectionner le système actuel qui combine paramétrage d'extraits et sources correspondantes. Améliorer la robustesse, la précision et la performance du moteur d'extraction.
- **Technologies clés** : Extraction de texte, parsing, gestion de métadonnées
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Base pour l'analyse argumentative, lié à 2.2.2 (formats étendus)
- **Références** :
  - Documentation sur les techniques d'extraction de texte
  - Littérature sur les systèmes de gestion de corpus
  - Bonnes pratiques en matière d'extraction de données

##### 2.2.2 Support de formats étendus
- **Contexte** : La diversité des sources nécessite la prise en charge de multiples formats de fichiers.
- **Objectifs** : Étendre les capacités du moteur d'extraction pour supporter davantage de formats de fichiers (PDF, DOCX, HTML, etc.) et de sources web. Implémenter des parsers spécifiques pour chaque format et assurer une extraction cohérente des données.
- **Technologies clés** : Bibliothèques de parsing (PyPDF2, python-docx, BeautifulSoup), OCR
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Extension de 2.2.1 (moteur d'extraction)
- **Références** :
  - Documentation des bibliothèques de parsing
  - Littérature sur l'extraction de texte structuré
  - Bonnes pratiques en matière de conversion de formats

##### 2.2.3 Sécurisation des données
- **Contexte** : La protection des données sensibles est essentielle, particulièrement pour les sources confidentielles.
- **Objectifs** : Améliorer le système de chiffrement des sources et configurations d'extraits pour garantir la confidentialité. Implémenter des mécanismes de contrôle d'accès, d'audit, et de gestion des clés.
- **Technologies clés** : Cryptographie (AES, RSA), gestion de clés, contrôle d'accès
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Transversal à tous les projets manipulant des données
- **Références** :
  - "Cryptography Engineering" de Ferguson, Schneier et Kohno
  - Documentation sur les bibliothèques cryptographiques
  - Standards de sécurité des données (NIST, ISO 27001)
#### 2.3 Moteur agentique et agents spécialistes

##### 2.3.1 Abstraction du moteur agentique
- **Contexte** : Un moteur agentique flexible permet d'intégrer différents frameworks et modèles.
- **Objectifs** : Créer une couche d'abstraction permettant d'utiliser différents frameworks agentiques (au-delà de Semantic Kernel). Implémenter des adaptateurs pour différents frameworks et assurer une interface commune.
- **Technologies clés** : Semantic Kernel, LangChain, AutoGen, design patterns d'abstraction
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Base pour 2.3.2-2.3.5 (agents spécialistes)
- **Références** :
  - Documentation Semantic Kernel, LangChain, AutoGen
  - "Design Patterns" de Gamma et al. (patterns d'abstraction)
  - Littérature sur les architectures agentiques

##### 2.3.2 Agent de détection de sophismes
- **Contexte** : La détection des sophismes est essentielle pour évaluer la qualité argumentative.
- **Objectifs** : Améliorer la détection et la classification des sophismes dans les textes. Développer des techniques spécifiques pour chaque type de sophisme et intégrer l'ontologie des sophismes (1.3.2).
- **Technologies clés** : NLP, classification, taxonomie des sophismes
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Utilise 1.3.2 (classification des sophismes)
- **Références** :
  - "Logically Fallacious" de Bo Bennett
  - Littérature sur la détection automatique de sophismes
  - Recherches en argumentation computationnelle

##### 2.3.3 Agent de génération de contre-arguments
- **Contexte** : La génération de contre-arguments permet d'évaluer la robustesse des arguments.
- **Objectifs** : Créer un agent capable de générer des contre-arguments pertinents et solides en réponse à des arguments donnés. Implémenter différentes stratégies de contre-argumentation basées sur les frameworks formels.
- **Technologies clés** : LLMs, frameworks d'argumentation, stratégies dialectiques
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.2 (frameworks d'argumentation) et 2.3.2 (détection de sophismes)
- **Références** :
  - "Computational Models of Argument" (COMMA)
  - Littérature sur les systèmes dialectiques
  - Recherches sur la génération d'arguments

##### 2.3.4 Agents de logique formelle
- **Contexte** : Les agents de logique formelle permettent d'analyser rigoureusement la validité des arguments.
- **Objectifs** : Développer de nouveaux agents spécialisés utilisant différentes parties de Tweety pour l'analyse logique formelle des arguments. Étendre les capacités de l'agent PL existant et créer des agents pour d'autres logiques (FOL, modale, etc.).
- **Technologies clés** : Tweety, logiques formelles, raisonneurs automatiques
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Utilise 1.1 (logiques formelles)
- **Références** :
  - Documentation Tweety
  - "Handbook of Practical Logic and Automated Reasoning"
  - Littérature sur les assistants de preuve

##### 2.3.5 Intégration de LLMs locaux légers
- **Contexte** : Les LLMs locaux permettent une analyse plus rapide et confidentielle.
- **Objectifs** : Explorer l'utilisation de modèles de langage locaux de petite taille pour effectuer l'analyse argumentative, en particulier les modèles Qwen 3 récemment sortis. Cette approche permettrait de réduire la dépendance aux API externes, d'améliorer la confidentialité des données et potentiellement d'accélérer le traitement.
- **Technologies clés** : Qwen 3, llama.cpp, GGUF, quantization
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 2.3.1 (abstraction du moteur agentique)
- **Références** :
  - Documentation Qwen 3
  - Benchmarks HELM
  - Recherches sur la distillation de modèles et l'optimisation pour l'inférence

#### 2.4 Indexation sémantique

##### 2.4.1 Index sémantique d'arguments
- **Contexte** : L'indexation sémantique permet de rechercher efficacement des arguments similaires.
- **Objectifs** : Indexer les définitions, exemples et instances d'arguments fallacieux pour permettre des recherches par proximité sémantique. Implémenter un système d'embedding et de recherche vectorielle pour les arguments.
- **Technologies clés** : Embeddings, bases de données vectorielles, similarité sémantique
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Lié à 2.4.2 (vecteurs de types d'arguments)
- **Références** :
  - "Vector Databases: The New Way to Store and Query Data" (2023)
  - Documentation sur les bases de données vectorielles (Pinecone, Weaviate, etc.)
  - Littérature sur les embeddings sémantiques

##### 2.4.2 Vecteurs de types d'arguments
- **Contexte** : La représentation vectorielle des types d'arguments facilite leur classification et découverte.
- **Objectifs** : Définir par assemblage des vecteurs de types d'arguments fallacieux pour faciliter la découverte de nouvelles instances. Créer un espace vectoriel où les arguments similaires sont proches les uns des autres.
- **Technologies clés** : Embeddings spécialisés, clustering, réduction de dimensionnalité
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Extension de 2.4.1 (index sémantique)
- **Références** :
  - "Embeddings in Natural Language Processing" (2021)
  - Littérature sur les représentations vectorielles spécialisées
  - Recherches sur les espaces sémantiques

#### 2.5 Automatisation et intégration MCP

##### 2.5.1 Automatisation de l'analyse
- **Contexte** : L'automatisation permet de traiter efficacement de grands volumes de textes.
- **Objectifs** : Développer des outils pour lancer l'équivalent du notebook d'analyse dans le cadre d'automates longs sur des corpus. Créer des scripts de traitement par lots et des mécanismes de parallélisation.
- **Technologies clés** : Automatisation de notebooks, traitement par lots, parallélisation
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Lié à 2.5.2 (pipeline de traitement)
- **Références** :
  - Documentation sur l'automatisation de notebooks (Papermill, etc.)
  - Littérature sur le traitement parallèle
  - Bonnes pratiques en matière d'automatisation

##### 2.5.2 Pipeline de traitement
- **Contexte** : Un pipeline complet permet d'intégrer toutes les étapes de l'analyse argumentative.
- **Objectifs** : Créer un pipeline complet pour l'ingestion, l'analyse et la visualisation des résultats d'analyse argumentative. Implémenter des mécanismes de reprise sur erreur, de monitoring, et de reporting.
- **Technologies clés** : Pipelines de données, workflow engines, ETL
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Intègre 2.5.1 (automatisation) et 3.1 (interfaces utilisateurs)
- **Références** :
  - "Building Data Pipelines with Python" (2021)
  - Documentation sur les outils de workflow (Airflow, Luigi, etc.)
  - Littérature sur les architectures de pipelines de données

##### 2.5.3 Développement d'un serveur MCP pour l'analyse argumentative
- **Contexte** : Le Model Context Protocol (MCP) permet d'exposer des capacités d'IA à d'autres applications.
- **Objectifs** : Publier le travail collectif sous forme d'un serveur MCP utilisable dans des applications comme Roo, Claude Desktop ou Semantic Kernel. Implémenter les spécifications MCP pour exposer les fonctionnalités d'analyse argumentative.
- **Technologies clés** : MCP, API REST/WebSocket, JSON Schema
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Intègre toutes les fonctionnalités d'analyse argumentative
- **Références** :
  - Spécification du protocole MCP
  - Documentation sur le développement de serveurs HTTP/WebSocket
  - Exemples de serveurs MCP existants

##### 2.5.4 Outils et ressources MCP pour l'argumentation
- **Contexte** : Des outils et ressources MCP spécifiques enrichissent les capacités d'analyse argumentative.
- **Objectifs** : Créer des outils MCP spécifiques pour l'extraction d'arguments, la détection de sophismes, la formalisation logique, et l'évaluation de la qualité argumentative. Développer des ressources MCP donnant accès à des taxonomies de sophismes, des exemples d'arguments, et des schémas d'argumentation.
- **Technologies clés** : MCP, JSON Schema, conception d'API
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Extension de 2.5.3 (serveur MCP)
- **Références** :
  - Spécification du protocole MCP
  - Documentation sur la conception d'API
  - Exemples d'outils et ressources MCP existants
### 3. Expérience utilisateur et applications

#### 3.1 Interfaces utilisateurs

##### 3.1.1 Interface web pour l'analyse argumentative
- **Contexte** : Une interface web intuitive facilite l'utilisation du système d'analyse argumentative.
- **Objectifs** : Développer une interface web moderne et intuitive permettant de visualiser et d'interagir avec les analyses argumentatives. Créer une expérience utilisateur fluide pour naviguer dans les structures argumentatives complexes, avec possibilité de filtrage, recherche et annotation.
- **Technologies clés** : React/Vue.js/Angular, D3.js, Cytoscape.js
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Intègre les fonctionnalités d'analyse argumentative, lié à 3.1.4 (visualisation)
- **Références** :
  - "Argument Visualization Tools in the Classroom" de Scheuer et al.
  - Interfaces de Kialo ou Arguman comme inspiration
  - Documentation sur les frameworks web modernes

##### 3.1.2 Dashboard de monitoring
- **Contexte** : Un tableau de bord permet de suivre l'activité du système et d'identifier les problèmes.
- **Objectifs** : Créer un tableau de bord permettant de suivre en temps réel l'activité des différents agents et l'état du système. Visualiser les métriques clés, les goulots d'étranglement, et l'utilisation des ressources. Implémenter des alertes et des notifications pour les événements critiques.
- **Technologies clés** : Grafana, Tableau, D3.js
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Utilise 2.1.3 (monitoring et évaluation)
- **Références** :
  - "Information Dashboard Design" de Stephen Few
  - Dashboards de Datadog ou New Relic comme inspiration
  - Documentation sur la visualisation de données

##### 3.1.3 Éditeur visuel d'arguments
- **Contexte** : Un éditeur visuel facilite la construction et la manipulation de structures argumentatives.
- **Objectifs** : Concevoir un éditeur permettant de construire et de manipuler visuellement des structures argumentatives. Permettre la création, l'édition et la connexion d'arguments, de prémisses et de conclusions de manière intuitive, avec support pour différents formalismes argumentatifs.
- **Technologies clés** : JointJS, mxGraph (draw.io), GoJS
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.2 (frameworks d'argumentation) et 3.1.4 (visualisation)
- **Références** :
  - "Argument Mapping" de Tim van Gelder
  - Outils comme Rationale ou Argunaut
  - Documentation sur les frameworks de diagrammes

##### 3.1.4 Visualisation de graphes d'argumentation
- **Contexte** : La visualisation des graphes d'argumentation aide à comprendre les relations entre arguments.
- **Objectifs** : Développer des outils de visualisation avancés pour les différents frameworks d'argumentation (Dung, bipolaire, pondéré, etc.). Implémenter des algorithmes de layout optimisés pour les graphes argumentatifs, avec support pour l'interaction et l'exploration.
- **Technologies clés** : Sigma.js, Cytoscape.js, vis.js
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Lié à 1.2 (frameworks d'argumentation)
- **Références** :
  - "Computational Models of Argument: Proceedings of COMMA" (conférences biennales)
  - Travaux de Floris Bex sur la visualisation d'arguments
  - Documentation sur les bibliothèques de visualisation de graphes

##### 3.1.5 Interface mobile
- **Contexte** : Une interface mobile permet d'accéder au système d'analyse argumentative en déplacement.
- **Objectifs** : Adapter l'interface utilisateur pour une utilisation sur appareils mobiles. Concevoir une expérience responsive ou développer une application mobile native/hybride permettant d'accéder aux fonctionnalités principales du système d'analyse argumentative.
- **Technologies clés** : React Native, Flutter, PWA
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Extension de 3.1.1 (interface web)
- **Références** :
  - "Mobile First" de Luke Wroblewski
  - "Responsive Web Design" d'Ethan Marcotte
  - Documentation sur le développement mobile

##### 3.1.6 Accessibilité
- **Contexte** : L'accessibilité garantit que le système peut être utilisé par tous, y compris les personnes en situation de handicap.
- **Objectifs** : Améliorer l'accessibilité des interfaces pour les personnes en situation de handicap. Implémenter les standards WCAG 2.1 AA, avec support pour les lecteurs d'écran, la navigation au clavier, et les contrastes adaptés.
- **Technologies clés** : ARIA, axe-core, pa11y
- **Niveau de difficulté** : ⭐⭐⭐
- **Interdépendances** : Transversal à toutes les interfaces (3.1.x)
- **Références** :
  - "Inclusive Design Patterns" de Heydon Pickering
  - Ressources du W3C Web Accessibility Initiative (WAI)
  - Documentation sur les standards d'accessibilité

##### 3.1.7 Système de collaboration en temps réel
- **Contexte** : La collaboration en temps réel permet à plusieurs utilisateurs de travailler ensemble sur une analyse.
- **Objectifs** : Développer des fonctionnalités permettant à plusieurs utilisateurs de travailler simultanément sur la même analyse argumentative, avec gestion des conflits et visualisation des contributions de chacun.
- **Technologies clés** : Socket.io, Yjs, ShareDB
- **Niveau de difficulté** : ⭐⭐⭐⭐⭐
- **Interdépendances** : Extension de 3.1.1 (interface web) et 3.1.3 (éditeur)
- **Références** :
  - "Building Real-time Applications with WebSockets" de Vanessa Wang et al.
  - Systèmes comme Google Docs ou Figma comme inspiration
  - Documentation sur les technologies de collaboration en temps réel

#### 3.2 Projets intégrateurs

##### 3.2.1 Système de débat assisté par IA
- **Contexte** : Un système de débat assisté par IA peut aider à structurer et améliorer les échanges argumentatifs.
- **Objectifs** : Développer une application complète permettant à des utilisateurs de débattre avec l'assistance d'agents IA qui analysent et améliorent leurs arguments. Le système pourrait identifier les faiblesses argumentatives, suggérer des contre-arguments, et aider à structurer les débats de manière constructive.
- **Technologies clés** : LLMs, frameworks d'argumentation, interface interactive
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Intègre 1.2 (frameworks d'argumentation), 2.3 (agents spécialistes), 3.1 (interfaces)
- **Références** :
  - "Computational Models of Argument" (COMMA)
  - Plateforme Kialo
  - Recherches de Chris Reed sur les technologies d'argumentation

##### 3.2.2 Plateforme d'éducation à l'argumentation
- **Contexte** : Une plateforme éducative peut aider à développer les compétences argumentatives.
- **Objectifs** : Créer un outil éducatif pour enseigner les principes de l'argumentation et aider à identifier les sophismes. Intégrer des tutoriels interactifs, des exercices pratiques, et un système de feedback automatisé basé sur l'analyse argumentative.
- **Technologies clés** : Gamification, visualisation d'arguments, agents pédagogiques
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Utilise 1.3.2 (classification des sophismes), 2.3.2 (détection de sophismes), 3.1 (interfaces)
- **Références** :
  - "Critical Thinking: A Concise Guide" de Tracy Bowell et Gary Kemp
  - "Argumentation Mining" de Stede et Schneider
  - Plateforme ArgTeach

##### 3.2.3 Système d'aide à la décision argumentative
- **Contexte** : Un système d'aide à la décision basé sur l'argumentation peut faciliter la prise de décisions complexes.
- **Objectifs** : Développer un système qui aide à la prise de décision en analysant et évaluant les arguments pour et contre différentes options. Implémenter des méthodes de pondération des arguments, d'analyse multicritère, et de visualisation des compromis.
- **Technologies clés** : Frameworks d'argumentation pondérés, méthodes MCDM, visualisation interactive
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Utilise 1.2.8 (frameworks avancés), 3.1.4 (visualisation)
- **Références** :
  - "Decision Support Systems" de Power et Sharda
  - "Argumentation-based Decision Support" de Karacapilidis et Papadias
  - Outils comme Rationale ou bCisive

##### 3.2.4 Plateforme collaborative d'analyse de textes
- **Contexte** : Une plateforme collaborative facilite l'analyse argumentative de textes complexes par plusieurs utilisateurs.
- **Objectifs** : Créer un environnement permettant à plusieurs utilisateurs de collaborer sur l'analyse argumentative de textes complexes. Intégrer des fonctionnalités de partage, d'annotation, de commentaire, et de révision collaborative.
- **Technologies clés** : Collaboration en temps réel, gestion de versions, annotation de documents
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Utilise 3.1.7 (collaboration en temps réel)
- **Références** :
  - "Computer Supported Cooperative Work" de Grudin
  - Systèmes comme Hypothesis, PeerLibrary, ou CommentPress
  - Littérature sur les systèmes d'annotation collaborative

##### 3.2.5 Assistant d'écriture argumentative
- **Contexte** : Un assistant d'écriture peut aider à améliorer la qualité argumentative des textes.
- **Objectifs** : Développer un outil d'aide à la rédaction qui suggère des améliorations pour renforcer la qualité argumentative des textes. Analyser la structure argumentative, identifier les faiblesses logiques, et proposer des reformulations ou des arguments supplémentaires.
- **Technologies clés** : NLP avancé, analyse rhétorique automatisée, génération de texte
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Interdépendances** : Utilise 2.3.2 (détection de sophismes), 2.3.3 (génération de contre-arguments)
- **Références** :
  - "Automated Essay Scoring" de Shermis et Burstein
  - Recherches sur l'argumentation computationnelle de l'ARG-tech Centre
  - Outils comme Grammarly ou Hemingway comme inspiration

##### 3.2.6 Système d'analyse de débats politiques
- **Contexte** : L'analyse des débats politiques peut aider à évaluer objectivement la qualité argumentative des discours.
- **Objectifs** : Développer un outil d'analyse des débats politiques en temps réel, capable d'identifier les arguments, les sophismes, et les stratégies rhétoriques utilisées par les participants. Fournir une évaluation objective de la qualité argumentative et factuelle des interventions.
- **Technologies clés** : Traitement du langage en temps réel, fact-checking automatisé, analyse de sentiment
- **Niveau de difficulté** : ⭐⭐⭐⭐⭐
- **Interdépendances** : Utilise 2.3.2 (détection de sophismes), 2.4 (indexation sémantique)
- **Références** :
  - "Computational Approaches to Analyzing Political Discourse" de Hovy et Lim
  - Projets comme FactCheck.org ou PolitiFact
  - Littérature sur l'analyse automatique du discours politique

##### 3.2.7 Plateforme de délibération citoyenne
- **Contexte** : Une plateforme de délibération peut faciliter la participation citoyenne aux décisions publiques.
- **Objectifs** : Créer un espace numérique pour faciliter les délibérations citoyennes sur des sujets complexes, en structurant les échanges selon des principes argumentatifs rigoureux et en favorisant la construction collaborative de consensus.
- **Technologies clés** : Modération assistée par IA, visualisation d'opinions, mécanismes de vote et de consensus
- **Niveau de difficulté** : ⭐⭐⭐⭐⭐
- **Interdépendances** : Intègre 3.2.1 (débat assisté), 3.2.3 (aide à la décision)
- **Références** :
  - "Democracy in the Digital Age" de Wilhelm
  - Plateformes comme Decidim, Consul, ou vTaiwan
  - Littérature sur la démocratie délibérative



Cette section présente une approche flexible pour contribuer au projet Intelligence Symbolique, favorisant l'auto-organisation des équipes d'étudiants tout en maintenant la qualité et la cohérence du code produit.

### Organisation des Équipes et Gestion de Projet

Plutôt que d'imposer un protocole de contribution strict, nous encourageons les étudiants à s'organiser selon leurs préférences et compétences. Certains étudiants sont invités à prendre en main l'aspect gestion de projet, en assumant des rôles tels que :

- **Chef de projet** : Coordination générale, planification des sprints, suivi de l'avancement
- **Responsable technique** : Architecture, standards de code, revue technique
