# 🚀 Analyse Rhétorique Collaborative par Agents IA (v_py) 🧠

Ce projet implémente une analyse rhétorique multi-agents en utilisant Python et le framework Semantic Kernel. Plusieurs agents IA spécialisés collaborent pour analyser un texte fourni par l'utilisateur via une interface web simple intégrée dans Jupyter.

**Objectif Principal :** Analyser un texte sous différents angles (informel via identification d'arguments/sophismes et formel simple via logique propositionnelle avec Tweety) en observant la collaboration des agents via la modification d'un état partagé, avec une orchestration basée sur la désignation explicite de l'agent suivant.

## Navigation Rapide

* [Structure du Projet](#structure-du-projet)
* [Prérequis](#prérequis)
* [Installation](#installation)
* [Exécution](#exécution)
* [Pistes d'Amélioration Futures](#pistes-damélioration-futures)

## Structure du Projet

Le projet est organisé en modules Python pour une meilleure maintenabilité :

* [`main_orchestrator.ipynb`](./main_orchestrator.ipynb) : Point d'entrée principal.
* [`config/`](./config/) : Fichiers de configuration (`.env.template`).
* [`core/`](./core/README.md) 🧱 : Composants fondamentaux partagés (État, StateManager, Stratégies, Setup JVM & LLM).
* [`utils/`](./utils/README.md) 🔧 : Fonctions utilitaires générales.
* [`ui/`](./ui/README.md) 🎨 : Logique de l'interface utilisateur (configuration du texte).
* [`agents/`](./agents/README.md) 🧠 : Définitions des agents spécialisés (PM, Informal, PL).
* [`orchestration/`](./orchestration/README.md) ⚙️ : Logique d'exécution de la conversation (`analysis_runner.py`).
* [`libs/`](./libs/) : Contient les JARs TweetyProject (téléchargés ou manuels).
* [`data/`](./data/) : Données utilisées/générées (config UI sauvegardée, CSV sophismes).
* [`requirements.txt`](./requirements.txt) : Dépendances Python.
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

1.  Lancez Jupyter Lab ou Notebook depuis la **racine du projet** (où se trouve ce README) : `jupyter lab`
2.  Ouvrez le notebook principal : `main_orchestrator.ipynb`
3.  (Recommandé pour la première fois ou après modifs `.py`) Redémarrez le noyau : `Kernel -> Restart Kernel...`
4.  Exécutez les cellules séquentiellement.
5.  L'initialisation de la JVM (Cellule 3) téléchargera les JARs Tweety si nécessaire (peut prendre du temps la première fois).
6.  L'interface utilisateur apparaîtra (Cellule 5). Interagissez pour sélectionner une source, préparer le texte et cliquez sur **"Lancer l'Analyse"**.
7.  La cellule 6 exécutera la conversation multi-agents. Observez les sorties et les logs.
8.  L'état final de l'analyse sera affiché à la fin de l'exécution de la cellule 6.

## Pistes d'Amélioration Futures

*(Liste reprise des notebooks)*

* **Activer & Finaliser PL:** Implémenter réellement les appels JPype/Tweety dans `PropositionalLogicPlugin._internal_execute_query`.
* **Affiner Analyse Sophismes:** Améliorer instructions `InformalAnalysisAgent` (profondeur, choix branches...).
* **Externaliser Prompts & Config:** Utiliser fichiers externes (YAML, JSON) via `kernel.import_plugin_from_directory`.
* **Gestion Erreurs Agents:** Renforcer capacité des agents à gérer `FUNC_ERROR:` (clarification, retry...).
* **Nouveaux Agents/Capacités:** Agents FOL, Modale, tâches (résumé, entités), outils (web, DB).
* **État RDF/KG:** Explorer `rdflib` ou base graphe pour état plus sémantique.
* **Interface Utilisateur:** Alternative type Gradio/Streamlit pour visualisation/interaction post-analyse.