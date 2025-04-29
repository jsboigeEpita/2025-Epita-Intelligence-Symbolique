# 🚀 Analyse Rhétorique Collaborative par Agents IA (v_py) 🧠

Ce projet implémente une analyse rhétorique multi-agents en utilisant Python et le framework Semantic Kernel. Plusieurs agents IA spécialisés collaborent pour analyser un texte fourni par l'utilisateur via une interface web simple intégrée dans Jupyter.

**Objectif Principal :** Analyser un texte sous différents angles (informel via identification d'arguments/sophismes et formel simple via logique propositionnelle avec Tweety) en observant la collaboration des agents via la modification d'un état partagé, avec une orchestration basée sur la désignation explicite de l'agent suivant.

## Navigation Rapide

* [Structure du Projet](#structure-du-projet)
* [Prérequis](#prérequis)
* [Installation](#installation)
* [Exécution](#exécution)
* [Approche Multi-Instance](#approche-multi-instance)
* [Pistes d'Amélioration Futures](#pistes-damélioration-futures)

## Structure du Projet

Le projet est organisé en modules Python pour une meilleure maintenabilité :

* [`main_orchestrator.py`](./main_orchestrator.py) : Script principal d'orchestration (remplace le notebook).
* [`config/`](./config/) : Fichiers de configuration (`.env.template`).
* [`core/`](./core/README.md) 🧱 : Composants fondamentaux partagés (État, StateManager, Stratégies, Setup JVM & LLM).
* [`utils/`](./utils/README.md) 🔧 : Fonctions utilitaires générales.
  * [`utils/extract_repair/`](./utils/extract_repair/) 🔄 : Outils de réparation des bornes d'extraits défectueuses.
* [`ui/`](./ui/README.md) 🎨 : Logique de l'interface utilisateur (configuration du texte).
  * [`ui/extract_editor/`](./ui/extract_editor/) ✏️ : Éditeur de marqueurs d'extraits.
* [`agents/`](./agents/README.md) 🧠 : Définitions des agents spécialisés (PM, Informal, PL).
* [`orchestration/`](./orchestration/README.md) ⚙️ : Logique d'exécution de la conversation (`analysis_runner.py`).
* [`libs/`](./libs/) : Contient les JARs TweetyProject (téléchargés ou manuels).
* [`data/`](./data/) : Données utilisées/générées (config UI sauvegardée, CSV sophismes).
* [`requirements.txt`](./requirements.txt) : Dépendances Python.
* [`run_analysis.py`](./run_analysis.py) : Script pour lancer l'analyse argumentative.
* [`run_extract_editor.py`](./run_extract_editor.py) : Script pour lancer l'éditeur de marqueurs d'extraits.
* [`run_extract_repair.py`](./run_extract_repair.py) : Script pour lancer la réparation des bornes défectueuses.
* [`README.md`](./README.md) : Ce fichier.

## Prérequis

* **Python :** Version 3.10+ recommandée.
* **Java :** JDK >= 11. La variable d'environnement `JAVA_HOME` **doit pointer vers le répertoire racine du JDK** pour une détection fiable par JPype (bien qu'une détection automatique soit tentée). Voir [instructions détaillées](#configuration-java).
* **Dépendances Python :** Installer via `pip install -r requirements.txt`. Inclut `semantic-kernel`, `python-dotenv`, `ipywidgets`, `jupyter-ui-poll`, `requests`, `pandas`, `jpype1`, `cryptography`, `ipykernel`, `nest-asyncio`.
* **Fichier `.env` :** Un fichier `.env` à la racine du projet est **indispensable**. Créez-le à partir de `config/.env.template` et remplissez :
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

1.  Clonez ce dépôt.
2.  Créez un environnement virtuel : `python -m venv venv`
3.  Activez l'environnement :
    * Windows PowerShell : `.\venv\Scripts\activate` (peut nécessiter `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)
    * Windows CMD : `.\venv\Scripts\activate.bat`
    * Linux/macOS : `source venv/bin/activate`
4.  Installez les dépendances : `pip install -r requirements.txt`
5.  Créez et configurez votre fichier `.env` (voir Prérequis).
6.  Assurez-vous que `JAVA_HOME` est correctement configuré.

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

### Utilisation des notebooks (méthode alternative)

Les notebooks originaux sont toujours disponibles pour une utilisation interactive :

1.  Lancez Jupyter Lab ou Notebook depuis la **racine du projet** : `jupyter lab`
2.  Ouvrez le notebook principal : `main_orchestrator.ipynb`
3.  Exécutez les cellules séquentiellement.
4.  L'interface utilisateur apparaîtra. Interagissez pour sélectionner une source, préparer le texte et cliquez sur **"Lancer l'Analyse"**.

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

*(Liste reprise des notebooks)*

* **Activer & Finaliser PL:** Implémenter réellement les appels JPype/Tweety dans `PropositionalLogicPlugin._internal_execute_query`.
* **Affiner Analyse Sophismes:** Améliorer instructions `InformalAnalysisAgent` (profondeur, choix branches...).
* **Externaliser Prompts & Config:** Utiliser fichiers externes (YAML, JSON) via `kernel.import_plugin_from_directory`.
* **Gestion Erreurs Agents:** Renforcer capacité des agents à gérer `FUNC_ERROR:` (clarification, retry...).
* **Nouveaux Agents/Capacités:** Agents FOL, Modale, tâches (résumé, entités), outils (web, DB).
* **État RDF/KG:** Explorer `rdflib` ou base graphe pour état plus sémantique.
* **Interface Utilisateur:** Alternative type Gradio/Streamlit pour visualisation/interaction post-analyse.
* **Amélioration des outils d'édition:** Enrichir les fonctionnalités de l'éditeur de marqueurs et de l'outil de réparation.