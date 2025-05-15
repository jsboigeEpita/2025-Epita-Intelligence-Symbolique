# 🚀 Analyse Rhétorique Collaborative par Agents IA (v_py) 🧠

Ce projet implémente une analyse rhétorique multi-agents en utilisant Python et le framework Semantic Kernel. Plusieurs agents IA spécialisés collaborent pour analyser un texte fourni par l'utilisateur via une interface web simple intégrée dans Jupyter.

**Objectif Principal :** Analyser un texte sous différents angles (informel via identification d'arguments/sophismes et formel simple via logique propositionnelle avec Tweety) en observant la collaboration des agents via la modification d'un état partagé, avec une orchestration basée sur la désignation explicite de l'agent suivant.

## Navigation Rapide

* [Structure du Projet](#structure-du-projet)
* [Prérequis](#prérequis)
* [Installation](#installation)
* [Exécution](#exécution)
* [Guide de Contribution pour Étudiants](#guide-de-contribution-pour-étudiants)
* [Approche Multi-Instance](#approche-multi-instance)
* [Pistes d'Amélioration Futures](#pistes-damélioration-futures)

## Structure du Projet

Le projet est organisé en modules Python pour une meilleure maintenabilité :

### Scripts Principaux
* [`main_orchestrator.py`](./main_orchestrator.py) : Script principal d'orchestration (version Python du notebook).
* [`main_orchestrator.ipynb`](./main_orchestrator.ipynb) : Notebook interactif pour l'orchestration.
* [`run_analysis.py`](./run_analysis.py) : Script pour lancer l'analyse argumentative.
* [`run_extract_editor.py`](./run_extract_editor.py) : Script pour lancer l'éditeur de marqueurs d'extraits.
* [`run_extract_repair.py`](./run_extract_repair.py) : Script pour lancer la réparation des bornes défectueuses.
* [`run_orchestration.py`](./run_orchestration.py) : Script pour lancer l'orchestration des agents.

### Modules Principaux
* [`core/`](./core/README.md) 🧱 : Composants fondamentaux partagés (État, StateManager, Stratégies, Setup JVM & LLM).
* [`core/communication/`](./core/communication/) 📡 : Système de communication entre agents.
* [`agents/`](./agents/README.md) 🧠 : Définitions des agents spécialisés (PM, Informal, PL, Extract).
* [`agents/core/`](./agents/core/) 🧠 : Implémentations des agents spécialistes.
  * [`agents/extract/`](./agents/extract/) 📋 : Module de redirection vers agents.core.extract.
  * [`agents/tools/`](./agents/tools/) 🛠️ : Outils utilisés par les agents.
  * [`agents/tools/encryption/`](./agents/tools/encryption/README_encryption_system.md) 🔒 : Outils de gestion des configurations chiffrées.
* [`orchestration/hierarchical/`](./orchestration/hierarchical/) 🔄 : Implémentation de l'orchestration hiérarchique.
* [`orchestration/`](./orchestration/README.md) ⚙️ : Logique d'exécution de la conversation (`analysis_runner.py`).
* [`ui/`](./ui/README.md) 🎨 : Logique de l'interface utilisateur (configuration du texte).
  * [`ui/extract_editor/`](./ui/extract_editor/README.md) ✏️ : Éditeur de marqueurs d'extraits.
* [`utils/`](./utils/README.md) 🔧 : Fonctions utilitaires générales.
  * [`utils/extract_repair/`](./utils/extract_repair/README.md) 🔄 : Outils de réparation des bornes d'extraits défectueuses.
* [`tests/`](./tests/) 🧪 : Tests unitaires et d'intégration.
* [`tests/tools/`](./tests/tools/README.md) 🧪 : Tests des outils rhétoriques.
* [`models/`](./models/README.md) 📊 : Modèles de données du projet.
* [`services/`](./services/README.md) 🔌 : Services partagés (cache, crypto, extraction, etc.).
* [`examples/`](./examples/README.md) 📝 : Exemples d'utilisation du système.
* [`results/`](./results/README.md) 📈 : Résultats des analyses.
* [`temp_downloads/`](./temp_downloads/README.md) 📥 : Répertoire de téléchargements temporaires.
* [`text_cache/`](./text_cache/README.md) 📋 : Répertoire de cache de textes.
* [`scripts/`](./scripts/README.md) 📜 : Scripts utilitaires pour le projet.

### Ressources et Configuration
* [`config/`](./config/) : Fichiers de configuration (`.env.template`).
* [`libs/`](./libs/) : Contient les JARs TweetyProject (téléchargés ou manuels).
* [`data/`](./data/README.md) : Données utilisées/générées (config UI sauvegardée, CSV sophismes).
* [`requirements.txt`](./requirements.txt) : Dépendances Python.
* [`.env`](./.env) : Fichier de configuration des variables d'environnement (à créer à partir de `.env.template`).

### Rapports et Documentation
* [`rapport_verification.html`](./rapport_verification.html) : Rapport de vérification des extraits.
* [`repair_report.html`](./repair_report.html) : Rapport de réparation des extraits.
* [`README.md`](./README.md) : Ce fichier.

## Prérequis

* **Python :** Version 3.10+ recommandée.
* **Java :** JDK >= 11. La variable d'environnement `JAVA_HOME` **doit pointer vers le répertoire racine du JDK** pour une détection fiable par JPype (bien qu'une détection automatique soit tentée). Voir [instructions détaillées](#configuration-java).
* **Dépendances Python :** Installer via `pip install -r requirements.txt`. Inclut `semantic-kernel`, `python-dotenv`, `ipywidgets`, `jupyter-ui-poll`, `requests`, `pandas`, `jpype1`, `cryptography`, `ipykernel`, `nest-asyncio`.
* **Fichier `.env` :** Un fichier `.env` à la racine du projet est **indispensable**. Créez-le à partir de `.env.example` et remplissez :
    * Vos clés API LLM (OpenAI ou Azure OpenAI).
    * Vos identifiants de modèle/déploiement (`OPENAI_CHAT_MODEL_ID`, `OPENAI_ENDPOINT` si Azure).
    * Une phrase secrète pour chiffrer la configuration UI (`TEXT_CONFIG_PASSPHRASE`).
* **JARs Tweety :** Doivent être présents dans le dossier `libs/`. Le script d'initialisation (`core/jvm_setup.py`) tentera de télécharger la version `1.28` (Core + modules + binaires natifs) si le dossier est vide ou les fichiers manquants. Vous pouvez aussi les placer manuellement.
* **(Optionnel) Fichier Config UI :** Le fichier `data/extract_sources.json.gz.enc` sera créé lors de la première sauvegarde via l'interface.

<details>
<summary>Configuration JAVA_HOME (Détails)</summary>

* **Windows :** ex: `C:\Program Files\Java\jdk-17` (Adaptez). Ajoutez aux variables d'environnement système/utilisateur.
* **Linux/macOS :** ex: `/usr/lib/jvm/java-17-openjdk-amd64` ou `/Library/Java/JavaVirtualMachines/zulu-17.jdk/Contents/Home`. Ajoutez `export JAVA_HOME=/chemin/vers/jdk` à votre `~/.bashrc`, `~/.zshrc` ou profil équivalent.
* **Redémarrage OBLIGATOIRE :** Après avoir défini `JAVA_HOME`, **redémarrez votre terminal/IDE et votre serveur Jupyter** pour qu'elle soit prise en compte.

</details>

## Installation

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

5. **Installez les dépendances** :
   ```bash
   cd argumentation_analysis
   pip install -r requirements.txt
   ```

6. **Créez et configurez votre fichier `.env`** :
   ```bash
   cp .env.example .env
   ```
   Puis modifiez le fichier `.env` avec vos propres informations (clés API, etc.).

7. **Assurez-vous que `JAVA_HOME` est correctement configuré**.

## Exécution

### Utilisation des scripts Python

Le projet a été transformé pour utiliser des scripts Python dédiés au lieu des notebooks, ce qui permet une meilleure intégration avec VSCode et une approche multi-instance.

#### Analyse Argumentative

Pour lancer l'analyse argumentative :

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

#### Orchestrateur Principal

Pour lancer l'orchestrateur principal (équivalent au notebook) :

```bash
# Avec l'interface utilisateur (comportement par défaut)
python main_orchestrator.py

# Sans l'interface, avec un fichier texte
python main_orchestrator.py --skip-ui --text-file chemin/vers/fichier.txt
```

#### Outils d'édition et de réparation des extraits

```bash
# Éditeur de marqueurs d'extraits
python run_extract_editor.py

# Réparation des bornes défectueuses
python run_extract_repair.py
```

#### Outils de gestion des configurations chiffrées

Les outils de gestion des configurations chiffrées sont maintenant disponibles dans le répertoire `agents/tools/encryption/` :

```bash
# Créer et archiver une configuration chiffrée complète
python -m agents.tools.encryption.create_and_archive_encrypted_config

# Créer une configuration chiffrée complète
python -m agents.tools.encryption.create_complete_encrypted_config

# Charger une configuration chiffrée
python -m agents.tools.encryption.load_complete_encrypted_config

# Nettoyer les fichiers après chiffrement
python -m agents.tools.encryption.cleanup_after_encryption

# Inspecter un fichier chiffré
python -m agents.tools.encryption.inspect_encrypted_file

# Vérifier une configuration chiffrée
python -m agents.tools.encryption.verify_encrypted_config
```

### Utilisation des notebooks (méthode alternative)

Les notebooks originaux sont toujours disponibles pour une utilisation interactive :

1. Lancez Jupyter Lab ou Notebook depuis la **racine du projet** : `jupyter lab`
2. Ouvrez le notebook principal : `main_orchestrator.ipynb`
3. Exécutez les cellules séquentiellement.
4. L'interface utilisateur apparaîtra. Interagissez pour sélectionner une source, préparer le texte et cliquez sur **"Lancer l'Analyse"**.

## Guide de Contribution pour Étudiants

Cette section explique comment contribuer efficacement au projet en tant qu'étudiant, que vous travailliez seul ou en groupe.

### Préparation de l'environnement de travail

1. **Assurez-vous d'avoir créé un fork** du dépôt principal comme expliqué dans la section [Installation](#installation)
2. **Configurez votre environnement de développement** en suivant les instructions détaillées
3. **Familiarisez-vous avec la structure du projet** en explorant les différents modules et leurs README

### Workflow de contribution

1. **Créez une branche** pour votre fonctionnalité ou correction :
   ```bash
   git checkout -b feature/nom-de-votre-fonctionnalite
   ```

2. **Développez votre fonctionnalité** en suivant les bonnes pratiques :
   - Respectez les conventions de nommage existantes
   - Commentez votre code de manière claire
   - Écrivez des tests pour vos fonctionnalités

3. **Committez vos changements** avec des messages descriptifs :
   ```bash
   git add .
   git commit -m "Description claire de vos modifications"
   ```

4. **Poussez votre branche** vers votre fork :
   ```bash
   git push origin feature/nom-de-votre-fonctionnalite
   ```

5. **Créez une Pull Request (PR)** depuis votre branche vers le dépôt principal :
   - Accédez à votre fork sur GitHub
   - Cliquez sur "Pull Request"
   - Sélectionnez votre branche et le dépôt principal comme cible
   - Remplissez le formulaire avec une description détaillée de vos modifications

### Conseils pour le travail en groupe

#### Groupe de 2 étudiants
- Répartissez clairement les tâches entre les membres
- Utilisez des branches distinctes pour travailler en parallèle
- Faites des revues de code mutuelles avant de soumettre une PR

#### Groupe de 3-4 étudiants
- Désignez un chef de projet pour coordonner le travail
- Divisez le projet en sous-modules indépendants
- Utilisez les issues GitHub pour suivre l'avancement
- Organisez des réunions régulières pour synchroniser le travail

### Bonnes pratiques

- **Maintenez votre fork à jour** avec le dépôt principal :
  ```bash
  git remote add upstream https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique.git
  git fetch upstream
  git merge upstream/main
  ```
- **Testez vos modifications** avant de soumettre une PR
- **Documentez vos changements** dans les README appropriés
- **Communiquez clairement** dans vos messages de commit et descriptions de PR

## Approche Multi-Instance

La nouvelle structure du projet permet une approche multi-instance dans VSCode, où chaque sous-module peut être exécuté indépendamment dans sa propre instance VSCode. Cela facilite le développement parallèle et la maintenance des différentes parties du projet.

### Organisation des instances

Chaque sous-répertoire contient un README.md qui sert de point d'entrée pour une instance VSCode dédiée :

* **Instance principale** : Racine du projet, pour l'orchestration globale
* **Instance Agents** : Dossier `agents/`, pour le développement des agents spécialisés
* **Instance UI** : Dossier `ui/`, pour le développement de l'interface utilisateur
* **Instance Extract Editor** : Dossier `ui/extract_editor/`, pour l'éditeur de marqueurs
* **Instance Extract Repair** : Dossier `utils/extract_repair/`, pour la réparation des bornes

### Avantages de l'approche multi-instance

* **Développement parallèle** : Plusieurs développeurs peuvent travailler simultanément sur différentes parties du projet
* **Isolation des dépendances** : Chaque module peut avoir ses propres dépendances spécifiques
* **Meilleure organisation** : Séparation claire des responsabilités et des fonctionnalités
* **Mise à jour incrémentielle** : Les modules peuvent être mis à jour indépendamment les uns des autres

## Outils d'édition et de réparation des extraits

Le projet inclut des outils spécialisés pour l'édition et la réparation des extraits de texte:

### Éditeur de marqueurs d'extraits

L'éditeur de marqueurs permet de définir et modifier les bornes des extraits de texte à analyser:

```bash
python run_extract_editor.py
```

Ou ouvrez le notebook interactif:
```bash
jupyter notebook ui/extract_editor/extract_marker_editor.ipynb
```

### Réparation des bornes défectueuses

L'outil de réparation permet de corriger automatiquement les bornes d'extraits défectueuses:

```bash
python run_extract_repair.py
```

Ou ouvrez le notebook interactif:
```bash
jupyter notebook utils/extract_repair/repair_extract_markers.ipynb
```

Pour plus de détails, consultez les README spécifiques:
- [Éditeur de marqueurs d'extraits](./ui/extract_editor/README.md)
- [Réparation des bornes défectueuses](./utils/extract_repair/README.md)

## Pistes d'Amélioration Futures

### Améliorations des Agents Existants
* **Activer & Finaliser PL:** Implémenter réellement les appels JPype/Tweety dans `PropositionalLogicPlugin._internal_execute_query`.
* **Affiner Analyse Sophismes:** Améliorer instructions `InformalAnalysisAgent` (profondeur, choix branches...).
* **Optimisation de l'Agent Informel:** Utiliser les outils dans `agents/utils/informal_optimization/` pour améliorer les performances.

### Architecture et Infrastructure
* **Externaliser Prompts & Config:** Utiliser fichiers externes (YAML, JSON) via `kernel.import_plugin_from_directory`.
* **Gestion Erreurs Agents:** Renforcer capacité des agents à gérer `FUNC_ERROR:` (clarification, retry...).
* **État RDF/KG:** Explorer `rdflib` ou base graphe pour état plus sémantique.
* **Orchestration Avancée:** Implémenter des stratégies d'orchestration plus sophistiquées.

### Nouveaux Agents et Fonctionnalités
* **Nouveaux Agents Logiques:** Agents FOL, Logique Modale, Logique de Description, etc.
* **Agents de Tâches Spécifiques:** Agents pour résumé, extraction d'entités, etc.
* **Intégration d'Outils Externes:** Web, bases de données, etc.

### Interface Utilisateur et Expérience Utilisateur
* **Interface Web Avancée:** Alternative type Gradio/Streamlit pour visualisation/interaction post-analyse.
* **Amélioration des Outils d'Édition:** Enrichir les fonctionnalités de l'éditeur de marqueurs et de l'outil de réparation.
* **Visualisation des Résultats:** Améliorer la visualisation des résultats d'analyse (graphes, tableaux, etc.).

### Tests et Évaluation
* **Tests à Grande Échelle:** Étendre les tests d'orchestration à grande échelle.
* **Métriques d'Évaluation:** Développer des métriques pour évaluer la qualité des analyses.
* **Benchmarks:** Créer des benchmarks pour comparer différentes configurations d'agents.