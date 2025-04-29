# ✏️ Éditeur de Marqueurs d'Extraits (`ui/extract_editor/`)

Ce module fournit un outil interactif pour éditer les marqueurs de début et de fin des extraits de texte utilisés dans l'analyse rhétorique.

[Retour au README UI](../README.md) | [Retour au README Principal](../../README.md)

## Objectif 🎯

L'éditeur de marqueurs d'extraits permet de:
1. Charger un texte source (depuis une URL, un fichier, ou directement)
2. Visualiser le texte complet
3. Définir précisément les bornes de début et de fin d'un extrait
4. Prévisualiser l'extrait sélectionné
5. Sauvegarder les marqueurs pour une utilisation ultérieure

Cet outil est particulièrement utile pour préparer des extraits de texte spécifiques à analyser par les agents IA.

## Contenu 📁

* **[`extract_marker_editor.py`](./extract_marker_editor.py)** : Module principal contenant la logique de l'éditeur de marqueurs.
* **[`extract_marker_editor.ipynb`](./extract_marker_editor.ipynb)** : Notebook interactif pour utiliser l'éditeur de marqueurs.
* **[`__init__.py`](./__init__.py)** : Marque le dossier comme un package Python.

## Utilisation 🚀

### Via le script de lancement

Le moyen le plus simple d'utiliser l'éditeur est d'exécuter le script à la racine du projet:

```bash
python ../../run_extract_editor.py
```

### Via le notebook

Vous pouvez également ouvrir directement le notebook interactif:

```bash
jupyter notebook extract_marker_editor.ipynb
```

### Intégration dans d'autres modules

Le module peut être importé et utilisé dans d'autres parties du projet:

```python
from ui.extract_editor.extract_marker_editor import launch_extract_marker_editor

# Lancer l'éditeur
launch_extract_marker_editor()
```

## Fonctionnalités 🛠️

- Interface utilisateur intuitive basée sur ipywidgets
- Chargement de texte depuis diverses sources
- Sélection précise des bornes d'extraits
- Prévisualisation en temps réel de l'extrait sélectionné
- Sauvegarde et chargement des configurations d'extraits


## Dépendances 📦

- ipywidgets
- jupyter-ui-poll
- pandas
- requests (pour le chargement depuis URL)