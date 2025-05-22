# Guide de Démarrage Rapide - Projet Intelligence Symbolique

Ce guide a pour objectif de vous aider à prendre en main rapidement le projet d'Intelligence Symbolique. Il vous guidera à travers les étapes essentielles pour comprendre, installer et commencer à utiliser le système d'analyse argumentative multi-agents.

## Table des Matières

1. [Introduction au Projet](#introduction-au-projet)
2. [Prérequis et Installation](#prérequis-et-installation)
3. [Structure du Projet](#structure-du-projet)
4. [Premier Pas avec le Système](#premier-pas-avec-le-système)
5. [Parcours Recommandé pour Découvrir le Dépôt](#parcours-recommandé-pour-découvrir-le-dépôt)
6. [Exemples Pratiques](#exemples-pratiques)
7. [Ressources Importantes](#ressources-importantes)
8. [Dépannage et FAQ](#dépannage-et-faq)

## Introduction au Projet

### Présentation du Projet d'Intelligence Symbolique

Le projet Intelligence Symbolique est conçu pour vous permettre d'appliquer concrètement les méthodes et outils vus en cours sur l'intelligence symbolique. Contrairement aux cours précédents où vous avez livré des travaux indépendants, vous travaillerez tous ensemble sur ce dépôt commun.

Le cœur du projet est une infrastructure d'analyse argumentative multi-agents qui permet d'analyser des textes sous différents angles :
- Analyse informelle via l'identification d'arguments et de sophismes
- Analyse formelle via la logique propositionnelle (avec Tweety)

### Objectifs Principaux

- Appliquer les techniques d'intelligence symbolique à des problèmes concrets
- Comprendre et développer un système multi-agents collaboratif
- Analyser des textes argumentatifs de manière approfondie
- Combiner les approches d'IA symbolique et de grands modèles de langage (LLMs)

### Vue d'Ensemble de l'Architecture Multi-Agents

Le système est construit autour d'une architecture multi-agents où différents agents spécialisés collaborent pour analyser des textes argumentatifs :

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

Le cycle de vie d'une analyse argumentative suit les étapes suivantes :
1. **Ingestion des données** : Le texte à analyser est fourni via l'interface utilisateur ou un script
2. **Extraction des arguments** : L'agent Extract identifie les arguments présents dans le texte
3. **Analyse informelle** : L'agent Informal analyse les arguments pour détecter les sophismes et évaluer leur qualité
4. **Analyse formelle** : L'agent PL (Propositional Logic) formalise les arguments en logique propositionnelle et vérifie leur validité
5. **Synthèse des résultats** : Les résultats des différents agents sont combinés dans l'état partagé
6. **Présentation** : Les résultats sont formatés et présentés à l'utilisateur

## Prérequis et Installation

### Configuration de l'Environnement de Développement

#### Prérequis

- **Python 3.10+** : Nécessaire pour exécuter le code Python
- **Java JDK 11+** : Requis pour l'intégration avec Tweety via JPype
- **Git** : Pour cloner le dépôt et gérer les versions

#### Étapes d'Installation

1. **Créez un fork du dépôt principal** :
   - Connectez-vous à votre compte GitHub
   - Accédez au dépôt principal : [https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique](https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique)
   - Cliquez sur le bouton "Fork" en haut à droite de la page
   - Sélectionnez votre compte comme destination du fork

2. **Clonez votre fork** :
   ```bash
   git clone https://github.com/VOTRE_NOM_UTILISATEUR/2025-Epita-Intelligence-Symbolique.git
   cd 2025-Epita-Intelligence-Symbolique
   ```

3. **Créez un environnement virtuel** :
   ```bash
   python -m venv venv
   ```

4. **Activez l'environnement** :
   - Windows PowerShell : `..\venv\Scripts\activate` (peut nécessiter `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)
   - Windows CMD : `..\venv\Scripts\activate.bat`
   - Linux/macOS : `source venv/bin/activate`

### Installation des Dépendances

Naviguez vers le dossier principal du projet et installez les dépendances :

```bash
cd argumentation_analysis
pip install -r requirements.txt
```

Les dépendances principales incluent :
- `semantic-kernel` : Pour la gestion des agents IA
- `python-dotenv` : Pour la gestion des variables d'environnement
- `jpype1` : Pour l'intégration Java-Python (Tweety)
- `ipywidgets` et `jupyter-ui-poll` : Pour l'interface utilisateur interactive
- Et d'autres bibliothèques utilitaires

### Configuration des Variables d'Environnement

1. **Créez un fichier `.env`** dans le dossier `argumentation_analysis` en vous basant sur le fichier `.env.example` :
   ```bash
   cp .env.example .env
   ```

2. **Modifiez le fichier `.env`** avec vos propres informations :
   - Vos clés API LLM (OpenAI ou Azure OpenAI)
   - Vos identifiants de modèle/déploiement (`OPENAI_CHAT_MODEL_ID`, `OPENAI_ENDPOINT` si Azure)
   - Une phrase secrète pour chiffrer la configuration UI (`TEXT_CONFIG_PASSPHRASE`)

3. **Configurez `JAVA_HOME`** pour pointer vers votre installation JDK :
   - Windows : ex: `C:\Program Files\Java\jdk-17` (Adaptez). Ajoutez aux variables d'environnement système/utilisateur.
   - Linux/macOS : ex: `/usr/lib/jvm/java-17-openjdk-amd64`. Ajoutez `export JAVA_HOME=/chemin/vers/jdk` à votre `~/.bashrc` ou `~/.zshrc`.
   - **Important** : Redémarrez votre terminal/IDE après avoir défini `JAVA_HOME`.

## Structure du Projet

### Explication de l'Organisation des Dossiers

Le projet est organisé en plusieurs modules principaux :

- **`argumentation_analysis/`** : Dossier principal contenant l'infrastructure d'analyse argumentative multi-agents
  - **`agents/`** : Agents spécialisés pour l'analyse (PM, Informal, PL, Extract)
  - **`core/`** : Composants fondamentaux partagés (État, LLM, JVM)
  - **`orchestration/`** : Logique d'exécution de la conversation
  - **`ui/`** : Interface utilisateur pour la configuration des analyses
  - **`utils/`** : Utilitaires généraux et outils de réparation d'extraits
  - **`models/`** : Modèles de données du projet
  - **`services/`** : Services partagés (cache, crypto, extraction, etc.)
  - **`tests/`** : Tests unitaires et d'intégration

- **`scripts/`** : Scripts utilitaires pour le projet
  - **`cleanup/`** : Scripts de nettoyage du projet
  - **`execution/`** : Scripts d'exécution des fonctionnalités principales
  - **`utils/`** : Utilitaires pour les scripts
  - **`validation/`** : Scripts de validation du projet

- **`docs/`** : Documentation supplémentaire du projet
  - **`architecture/`** : Documentation de l'architecture du système
  - **`projets/`** : Présentation des sujets de projets
  - **`reference/`** : Documentation de référence pour les API

- **`examples/`** : Exemples de textes pour les tests et démonstrations
- **`results/`** : Résultats des analyses et des tests
- **`tutorials/`** : Tutoriels pour prendre en main le système

### Clarification des Dossiers Dupliqués

Il existe des dossiers avec des noms identiques mais des fonctions distinctes :

#### Dossiers `examples/` et `argumentation_analysis/examples/`

| Dossier | Contenu | Fonction |
|---------|---------|----------|
| **examples/** | Fichiers texte (`.txt`) | Contient des **exemples de textes et données** pour tester le système d'analyse argumentative |
| **argumentation_analysis/examples/** | Fichiers Python (`.py`) | Contient des **exemples de code** démontrant l'utilisation et l'implémentation du système |

#### Dossiers `results/` et `argumentation_analysis/results/`

| Dossier | Contenu | Fonction |
|---------|---------|----------|
| **results/** | Analyses, rapports, visualisations | Stocke les **résultats d'analyse de textes** effectuées sur différents corpus |
| **argumentation_analysis/results/** | Tests de performance | Contient les **résultats d'évaluation du système** lui-même (performance, précision, etc.) |

### Modules Principaux et Leur Rôle

- **Agents** : Composants autonomes spécialisés dans différentes tâches d'analyse
  - **Agent Extract** : Identifie et extrait les arguments du texte
  - **Agent Informal** : Analyse les sophismes et la qualité argumentative
  - **Agent PL** : Formalise les arguments en logique propositionnelle
  - **Agent PM** : Gère le projet et coordonne les autres agents

- **Core** : Fournit les fonctionnalités fondamentales partagées
  - **État** : Stocke et gère l'état partagé entre les agents
  - **LLM Service** : Interface avec les grands modèles de langage
  - **JVM Setup** : Configure l'environnement Java pour Tweety

- **Orchestration** : Gère le flux d'exécution et la coordination des agents
  - **Analysis Runner** : Exécute l'analyse complète
  - **Hierarchical Orchestration** : Implémente l'orchestration hiérarchique

- **UI** : Fournit des interfaces utilisateur pour interagir avec le système
  - **Extract Editor** : Éditeur de marqueurs d'extraits
  - **Configuration UI** : Interface pour configurer les analyses

## Premier Pas avec le Système

### Comment Exécuter une Analyse Simple

Pour lancer une analyse argumentative simple, vous pouvez utiliser le script `run_analysis.py` :

```bash
# Avec l'interface utilisateur
python run_analysis.py --ui

# Avec un fichier texte
python run_analysis.py --file chemin/vers/fichier.txt

# Avec du texte direct
python run_analysis.py --text "Votre texte à analyser ici"

# Avec logs détaillés
python run_analysis.py --ui --verbose
```

### Utilisation des Scripts Principaux

Le projet propose plusieurs scripts pour différentes fonctionnalités :

#### Orchestrateur Principal

```bash
# Avec l'interface utilisateur (comportement par défaut)
python main_orchestrator.py

# Sans l'interface, avec un fichier texte
python main_orchestrator.py --skip-ui --text-file chemin/vers/fichier.txt
```

#### Outils d'Édition et de Réparation des Extraits

```bash
# Éditeur de marqueurs d'extraits
python run_extract_editor.py

# Réparation des bornes défectueuses
python run_extract_repair.py
```

### Interprétation des Résultats

Après avoir exécuté une analyse, les résultats seront affichés dans la console et/ou sauvegardés dans le dossier `results/`. Les résultats comprennent généralement :

- **Sophismes détectés** : Liste des sophismes identifiés avec leur type, l'extrait concerné et une explication
- **Structure argumentative** : Représentation de la structure des arguments dans le texte
- **Analyse formelle** : Résultats de l'analyse en logique propositionnelle (si applicable)
- **Métriques** : Statistiques sur la qualité argumentative du texte

Pour une analyse plus approfondie, vous pouvez consulter les fichiers JSON générés dans le dossier `results/`.

## Parcours Recommandé pour Découvrir le Dépôt

Pour une prise en main optimale du projet, nous vous recommandons de suivre ce parcours :

### Ordre Suggéré pour Explorer les Différentes Parties du Projet

1. **Commencez par les tutoriels** : Le dossier `tutorials/` contient des guides progressifs pour apprendre à utiliser le système
   - `01_prise_en_main.md` : Installation et configuration
   - `02_analyse_discours_simple.md` : Première analyse simple
   - `03_analyse_discours_complexe.md` : Analyses plus avancées

2. **Explorez les exemples** : Le dossier `examples/` contient des textes d'exemple que vous pouvez utiliser pour tester le système

3. **Comprenez l'architecture** : Consultez la documentation dans `docs/architecture/` pour comprendre comment les différents composants interagissent

4. **Examinez le code des agents** : Le dossier `argumentation_analysis/agents/` contient l'implémentation des différents agents spécialisés

5. **Découvrez les outils d'analyse** : Explorez les outils disponibles dans `argumentation_analysis/agents/tools/`

### Points d'Entrée Importants

- **`main_orchestrator.py`** : Point d'entrée principal pour l'orchestration des agents
- **`run_analysis.py`** : Script simplifié pour lancer une analyse
- **`argumentation_analysis/core/state.py`** : Définition de l'état partagé entre les agents
- **`argumentation_analysis/agents/core/`** : Implémentation des agents spécialistes

### Tutoriels Disponibles

Le dossier `tutorials/` contient une série de tutoriels pour vous aider à prendre en main le système :

1. **Prise en Main** : Installation et configuration de l'environnement
2. **Analyse de Discours Simple** : Guide pour effectuer une analyse basique
3. **Analyse de Discours Complexe** : Techniques avancées d'analyse
4. **Ajout d'un Nouvel Agent** : Instructions pour étendre le système
5. **Extension des Outils d'Analyse** : Guide pour développer de nouveaux outils

## Exemples Pratiques

### Présentation des Exemples Disponibles

Le dossier `examples/` contient plusieurs exemples de textes que vous pouvez utiliser pour tester le système :

1. **exemple_sophisme.txt** : Texte contenant plusieurs sophismes sur le thème de la régulation de l'intelligence artificielle
2. **texte_sans_marqueurs.txt** : Texte informatif sur la pensée critique sans sophismes évidents
3. **article_scientifique.txt** : Article académique sur l'analyse d'arguments par NLP avec une structure formelle
4. **discours_politique.txt** : Discours politique avec une structure rhétorique claire
5. **discours_avec_template.txt** : Allocution présidentielle avec des marqueurs explicites de structure

### Comment Utiliser les Exemples pour Tester le Système

Vous pouvez utiliser ces exemples de plusieurs façons :

```bash
# Analyse d'un exemple avec l'interface utilisateur
python run_analysis.py --ui
# Puis sélectionnez le fichier dans l'interface

# Analyse directe d'un exemple
python run_analysis.py --file examples/exemple_sophisme.txt

# Analyse avec un agent spécifique
python -c "from argumentation_analysis.agents.informal.informal_agent import InformalAgent; \
           from argumentation_analysis.core.llm_service import LLMService; \
           llm = LLMService(); \
           agent = InformalAgent(llm); \
           with open('examples/exemple_sophisme.txt', 'r') as f: \
               text = f.read(); \
           result = agent.analyze_informal_fallacies(text); \
           print(result)"
```

### Cas d'Utilisation Typiques

1. **Analyse de Sophismes** : Utilisez `exemple_sophisme.txt` pour tester la détection de sophismes
   ```bash
   python run_analysis.py --file examples/exemple_sophisme.txt
   ```

2. **Analyse Structurelle** : Utilisez `article_scientifique.txt` pour tester l'analyse de structure
   ```bash
   python scripts/execution/run_analysis.py --file examples/article_scientifique.txt --mode structure
   ```

3. **Analyse Rhétorique** : Utilisez `discours_politique.txt` pour tester l'analyse rhétorique
   ```bash
   python scripts/execution/run_analysis.py --file examples/discours_politique.txt --mode rhetorique
   ```

4. **Extraction de Structure** : Utilisez `discours_avec_template.txt` pour tester l'extraction de structure
   ```bash
   python scripts/execution/run_analysis.py --file examples/discours_avec_template.txt --mode extraction
   ```

## Ressources Importantes

### Documentation de Référence

- **README Principal** : `README.md` à la racine du projet
- **Documentation d'Architecture** : `docs/architecture/README.md`
- **Documentation des Agents** : `argumentation_analysis/agents/README.md`
- **Documentation de l'Orchestration** : `argumentation_analysis/orchestration/README.md`
- **Documentation de l'Interface Utilisateur** : `argumentation_analysis/ui/README.md`

### Tutoriels

Le dossier `tutorials/` contient des tutoriels détaillés pour vous aider à prendre en main le système :

- **Tutoriels de Base** : Installation, configuration, premières analyses
- **Tutoriels Avancés** : Développement d'agents, extension du système
- **Exemples Pratiques** : Cas d'utilisation concrets avec code

### Guides de Contribution

Pour contribuer au projet, consultez les ressources suivantes :

- **Guide de Contribution** : Section "Guide de Contribution" dans le README principal
- **Workflow de Contribution** : Instructions pour créer des branches, soumettre des PR, etc.
- **Conventions de Code** : Conventions de nommage, style de code, etc.

## Dépannage et FAQ

### Problèmes Courants et Solutions

#### Problème : Erreur lors de l'initialisation de JPype

**Symptôme** : Message d'erreur indiquant que JPype ne peut pas trouver la JVM.

**Solution** :
1. Vérifiez que `JAVA_HOME` est correctement configuré
2. Redémarrez votre terminal/IDE après avoir défini `JAVA_HOME`
3. Vérifiez que vous avez installé JDK 11+ (et non JRE)

#### Problème : Erreur de clé API LLM

**Symptôme** : Message d'erreur indiquant que la clé API est invalide ou manquante.

**Solution** :
1. Vérifiez que vous avez créé un fichier `.env` dans le dossier `argumentation_analysis`
2. Assurez-vous que les variables `OPENAI_API_KEY` ou `AZURE_OPENAI_API_KEY` sont correctement définies
3. Si vous utilisez Azure OpenAI, vérifiez également `OPENAI_ENDPOINT` et `OPENAI_CHAT_MODEL_ID`

#### Problème : Les JARs Tweety ne sont pas téléchargés automatiquement

**Symptôme** : Message d'erreur indiquant que les JARs Tweety sont manquants.

**Solution** :
1. Exécutez manuellement le script de téléchargement : `python -c "from argumentation_analysis.core.jvm_setup import download_tweety_jars; download_tweety_jars()"`
2. Vérifiez que vous avez une connexion Internet active
3. Si le téléchargement échoue, téléchargez manuellement les JARs depuis [TweetyProject](https://tweetyproject.org/download.html) et placez-les dans le dossier `argumentation_analysis/libs/`

### Où Trouver de l'Aide

Si vous rencontrez des difficultés ou avez des questions :

1. **Consultez la documentation** : La plupart des problèmes courants sont documentés dans les README des différents modules
2. **Explorez les tutoriels** : Les tutoriels contiennent des instructions détaillées pour les tâches courantes
3. **Vérifiez les issues GitHub** : D'autres étudiants ont peut-être rencontré le même problème
4. **Créez une issue** : Si vous ne trouvez pas de solution, créez une issue sur GitHub avec une description détaillée du problème

---

Ce guide de démarrage rapide vous a fourni les informations essentielles pour commencer à utiliser le projet d'Intelligence Symbolique. Pour des informations plus détaillées, n'hésitez pas à consulter la documentation complète et les tutoriels disponibles dans le dépôt.

Bonne exploration et bon développement !