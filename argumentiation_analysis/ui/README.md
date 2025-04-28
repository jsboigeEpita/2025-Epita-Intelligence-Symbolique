# 🎨 Interface Utilisateur (`ui/`)

Ce répertoire gère l'interface utilisateur (basée sur `ipywidgets`) permettant à l'utilisateur de configurer la tâche d'analyse avant de lancer la conversation multi-agents.

[Retour au README Principal](../README.md)

## Objectif 🎯

L'interface utilisateur a pour but de :
1.  ✅ Sélectionner une source de texte :
    * 📚 Bibliothèque prédéfinie (avec extraits spécifiques).
    * 🌐 URL (traitée par Jina ou Tika).
    * 📄 Fichier local (traité par Tika si nécessaire).
    * ✍️ Texte direct collé par l'utilisateur.
2.  ✂️ Extraire le contenu textuel via [Jina Reader](https://github.com/jina-ai/reader) ou [Apache Tika](https://tika.apache.org/) si la source n'est pas en texte brut.
3.  📐 Appliquer des marqueurs de début/fin pour isoler un extrait spécifique (principalement pour URL/Fichier/Texte Direct).
4.  💾 Gérer un cache fichier (`text_cache/`) pour les textes complets récupérés depuis des sources externes, afin d'éviter les téléchargements/extractions répétés.
5.  🔐 Charger/Sauvegarder la configuration des sources prédéfinies depuis/vers un fichier chiffré (`data/extract_sources.json.gz.enc`) en utilisant une phrase secrète définie dans `.env`.
6.  ➡️ Retourner le texte final préparé au notebook orchestrateur principal (`main_orchestrator.ipynb`).

## Structure 🏗️

* **[`config.py`](./config.py)** : Constantes (URLs, chemins), chargement/dérivation de la clé de chiffrement (`ENCRYPTION_KEY`), définition des sources par défaut (`EXTRACT_SOURCES`, `DEFAULT_EXTRACT_SOURCES`).
* **[`utils.py`](./utils.py)** : Fonctions utilitaires pour le cache, le chiffrement/déchiffrement, la reconstruction d'URL, le fetch de données (Jina, Tika, direct), et la vérification des marqueurs des sources prédéfinies.
* **[`app.py`](./app.py)** : Définit la fonction principale `configure_analysis_task`. C'est elle qui crée les widgets `ipywidgets`, définit les callbacks (logique événementielle), assemble l'interface, l'affiche (`display()`) et gère la boucle d'attente (`jupyter-ui-poll`). Contient aussi `initialize_text_cache` pour le pré-remplissage optionnel du cache.
* **[`__init__.py`](./__init__.py)** : Marque le dossier comme un package.

## Fin (Note du Notebook Original)

Ce module `ui` contient la logique nécessaire pour l'interface utilisateur, la gestion des sources, le cache et le chiffrement. Le notebook exécuteur principal importe et utilise la fonction `configure_analysis_task` définie dans `ui.app` pour obtenir le texte préparé.