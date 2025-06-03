# 🎨 Interface Utilisateur (`ui/`)

Ce répertoire gère l'interface utilisateur (basée sur `ipywidgets`) permettant à l'utilisateur de configurer la tâche d'analyse avant de lancer la conversation multi-agents.

[Retour au README Principal](../README.md)

## Point d'entrée pour instance VSCode dédiée

Ce README sert de point d'entrée pour une instance VSCode dédiée au développement et à la maintenance de l'interface utilisateur. Cette approche multi-instance permet de travailler spécifiquement sur l'UI sans avoir à gérer l'ensemble du projet.

## Objectif 🎯

L'interface utilisateur a pour but de :
1.  ✅ Sélectionner une source de texte :
    * 📚 Bibliothèque prédéfinie (avec extraits spécifiques).
    * 🌐 URL (traitée par Jina ou Tika).
    * 📄 Fichier local (traité par Tika si nécessaire).
    * ✍️ Texte direct collé par l'utilisateur.
2.  ✂️ Extraire le contenu textuel via [Jina Reader](https://github.com/jina-ai/reader) ou [Apache Tika](https://tika.apache.org/) si la source n'est pas en texte brut.
3.  📐 Appliquer des marqueurs de début/fin pour isoler un extrait spécifique (principalement pour URL/Fichier/Texte Direct). Ces marqueurs s'appliquent au texte source, qui est prioritairement lu depuis le champ `full_text` du fichier `extract_sources.json.gz.enc` si celui-ci est présent.
4.  💾 Gérer un cache fichier (`text_cache/`) pour les textes complets récupérés depuis des sources externes (utilisé lorsque `full_text` n'est pas disponible dans `extract_sources.json.gz.enc`), afin d'éviter les téléchargements/extractions répétés.
5.  🔐 Charger/Sauvegarder la configuration des sources prédéfinies, y compris le nouveau champ `full_text` qui embarque le contenu source, depuis/vers un fichier chiffré (`data/extract_sources.json.gz.enc`) en utilisant une phrase secrète définie dans `.env`. La lecture des sources privilégie désormais le contenu `full_text` embarqué, la récupération dynamique via URL/fichier étant un fallback. La fonction `save_extract_definitions_safely` dans [`extract_utils.py`](./extract_utils.py:1) permet cette sauvegarde. Pour un embarquement systématique de tous les textes sources, le script [`scripts/embed_all_sources.py`](../../scripts/embed_all_sources.py) peut être utilisé.
6.  ➡️ Retourner le texte final préparé (obtenu via `full_text` ou récupération dynamique) au script orchestrateur principal (`main_orchestrator.py`).
7.  🔍 Permettre l'édition et la vérification des marqueurs d'extraits via des outils dédiés, en tenant compte de la source (embarquée ou externe).
8.  📊 Visualiser les résultats d'analyse et les rapports de vérification.

## Structure 🏗️

### Fichiers principaux
* **[`app.py`](./app.py)** : Définit la fonction principale `configure_analysis_task`. C'est elle qui crée les widgets `ipywidgets`, définit les callbacks (logique événementielle), assemble l'interface, l'affiche (`display()`) et gère la boucle d'attente (`jupyter-ui-poll`). Contient aussi `initialize_text_cache` pour le pré-remplissage optionnel du cache.
* **[`config.py`](./config.py)** : Constantes (URLs, chemins), chargement/dérivation de la clé de chiffrement (`ENCRYPTION_KEY`), définition des sources par défaut (`EXTRACT_SOURCES`, `DEFAULT_EXTRACT_SOURCES`).

### Utilitaires
* **[`utils.py`](./utils.py)** : Fonctions utilitaires pour le cache, le chiffrement/déchiffrement, la reconstruction d'URL, le fetch de données (Jina, Tika, direct), et la vérification des marqueurs des sources prédéfinies.
* **[`extract_utils.py`](./extract_utils.py)** : Fonctions utilitaires spécifiques à l'extraction de texte.
* **[`__init__.py`](./__init__.py)** : Marque le dossier comme un package.

### Sous-modules
* **[`extract_editor/`](./extract_editor/README.md)** ✏️ : Sous-module pour l'édition des marqueurs d'extraits.

## Sous-modules

### Éditeur de marqueurs d'extraits (`extract_editor/`) ✏️

Ce sous-module contient les outils pour éditer les marqueurs de début et de fin des extraits de texte:

* **[`extract_marker_editor.py`](./extract_editor/extract_marker_editor.py)** : Module principal pour l'édition des marqueurs.
* **[`extract_marker_editor.ipynb`](./extract_editor/extract_marker_editor.ipynb)** : Notebook interactif pour l'édition des marqueurs.

Pour lancer l'éditeur de marqueurs, vous pouvez utiliser le script à la racine du projet:
```bash
python ../run_extract_editor.py
```

Ou ouvrir directement le notebook:
```bash
jupyter notebook extract_editor/extract_marker_editor.ipynb
```

Pour plus de détails, consultez le [README de l'éditeur de marqueurs](./extract_editor/README.md).

## Développement de l'interface utilisateur

### Test indépendant de l'interface

Pour tester l'interface utilisateur de manière indépendante, vous pouvez créer un script de test dans ce répertoire :

```python
# test_ui.py
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from dotenv import load_dotenv
load_dotenv(override=True)

from ui.app import configure_analysis_task

def main():
    print("Lancement de l'interface utilisateur...")
    text = configure_analysis_task()
    if text:
        print(f"Texte récupéré ({len(text)} caractères)")
        print(f"Aperçu: {text[:100]}...")
    else:
        print("Aucun texte récupéré")

if __name__ == "__main__":
    main()
```

Exécutez le test avec :
```bash
python ui/test_ui.py
```

### Création d'un script d'exécution autonome

Pour faciliter le développement et le test de l'interface utilisateur, vous pouvez créer un script d'exécution autonome :

```python
# run_ui.py
import sys
import os
from pathlib import Path
import argparse

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from dotenv import load_dotenv
load_dotenv(override=True)

from ui.app import configure_analysis_task, initialize_text_cache

def main():
    parser = argparse.ArgumentParser(description="Interface utilisateur pour l'analyse argumentative")
    parser.add_argument("--init-cache", action="store_true", help="Initialiser le cache des textes")
    args = parser.parse_args()
    
    if args.init_cache:
        print("Initialisation du cache des textes...")
        initialize_text_cache()
    
    print("Lancement de l'interface utilisateur...")
    text = configure_analysis_task()
    if text:
        print(f"Texte récupéré ({len(text)} caractères)")
        print(f"Aperçu: {text[:100]}...")
    else:
        print("Aucun texte récupéré")

if __name__ == "__main__":
    main()
```

## Développement avec l'approche multi-instance

1. Ouvrez ce répertoire (`ui/`) comme dossier racine dans une instance VSCode dédiée
2. Travaillez sur l'interface utilisateur sans être distrait par les autres parties du projet
3. Testez vos modifications avec les scripts de test indépendants
4. Une fois les modifications validées, intégrez-les dans le projet principal

## Bonnes pratiques

- Gardez la logique UI séparée de la logique métier
- Utilisez des noms explicites pour les widgets et les fonctions
- Documentez clairement les paramètres et le comportement des fonctions
- Testez l'interface avec différentes sources de texte
- Gérez correctement les erreurs et affichez des messages clairs à l'utilisateur
- Utilisez des commentaires pour expliquer les parties complexes du code
- Maintenez une structure cohérente pour tous les composants UI

## Intégration avec le projet principal

L'interface utilisateur est intégrée au projet principal via la fonction `configure_analysis_task()` qui est appelée par le script orchestrateur principal (`main_orchestrator.py`). Cette fonction retourne le texte préparé qui sera ensuite analysé par les agents.

Pour modifier l'intégration, vous devez :
1. Mettre à jour la fonction `configure_analysis_task()` dans `app.py`
2. Tester les modifications avec le script de test indépendant
3. Vérifier l'intégration avec le script orchestrateur principal

## Fonctionnalités avancées

### Visualisation des résultats d'analyse

L'interface utilisateur permet la visualisation des résultats d'analyse :

- Affichage des arguments identifiés avec mise en évidence dans le texte
- Visualisation des sophismes détectés avec leur description et leur classification
- Représentation graphique des relations entre arguments (attaques, supports)
- Affichage des formules logiques et des résultats de requêtes

### Éditeur de marqueurs

L'éditeur de marqueurs d'extraits offre les fonctionnalités suivantes :

- Recherche avancée dans le texte (expressions régulières)
- Suggestions automatiques de marqueurs basées sur l'analyse du texte
- Prévisualisation en temps réel des extraits sélectionnés
- Validation automatique des marqueurs pour éviter les erreurs

### Intégration avec les outils de vérification

L'interface utilisateur s'intègre avec les outils de vérification des extraits :

- Lancement de la vérification directement depuis l'interface
- Affichage des rapports de vérification avec mise en évidence des problèmes
- Correction assistée des problèmes détectés
- Sauvegarde automatique des corrections

## Exemples d'utilisation avancée

### Lancement de l'interface avec options avancées

```python
from ui.app import configure_analysis_task

# Lancer l'interface avec pré-chargement du cache
text = configure_analysis_task(
    preload_cache=True,
    default_source_type="url",
    default_url="https://example.com/article.html"
)
```

### Intégration avec l'éditeur de marqueurs

```python
from ui.app import configure_analysis_task
from ui.extract_editor.extract_marker_editor import edit_markers

# Configurer le texte
text = configure_analysis_task()

# Ouvrir l'éditeur de marqueurs avec le texte sélectionné
if text:
    markers = edit_markers(text)
    print(f"Marqueurs définis: {markers}")
```