# ✏️ Éditeur de Marqueurs d'Extraits (`ui/extract_editor/`)

Ce module fournit un outil interactif pour éditer les marqueurs de début et de fin des extraits de texte utilisés dans l'analyse rhétorique.

[Retour au README UI](../README.md) | [Retour au README Principal](../../README.md)

## Point d'entrée pour instance VSCode dédiée

Ce README sert de point d'entrée pour une instance VSCode dédiée au développement et à la maintenance de l'éditeur de marqueurs d'extraits. Cette approche multi-instance permet de travailler spécifiquement sur cet outil sans avoir à gérer l'ensemble du projet.

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
from ui.extract_editor.extract_marker_editor import main as editor_main

# Lancer l'éditeur
editor_main()
```

## Développement de l'éditeur de marqueurs

### Création d'un script de test indépendant

Pour tester l'éditeur de marqueurs de manière indépendante, vous pouvez créer un script de test dans ce répertoire :

```python
# test_editor.py
import sys
import os
from pathlib import Path

# Ajouter les répertoires parents au chemin de recherche des modules
current_dir = Path(__file__).parent
ui_dir = current_dir.parent
project_dir = ui_dir.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from dotenv import load_dotenv
load_dotenv(override=True)

# Import du module à tester
from ui.extract_editor.extract_marker_editor import main as editor_main

def run_test():
    """Fonction de test pour l'éditeur de marqueurs"""
    print("Lancement de l'éditeur de marqueurs d'extraits...")
    editor_main()
    print("Test terminé.")

if __name__ == "__main__":
    run_test()
```

Exécutez le test avec :
```bash
python ui/extract_editor/test_editor.py
```

### Développement de nouvelles fonctionnalités

Pour ajouter de nouvelles fonctionnalités à l'éditeur de marqueurs, suivez ces étapes :

1. Identifiez clairement la fonctionnalité à ajouter
2. Modifiez le fichier `extract_marker_editor.py` pour implémenter la fonctionnalité
3. Testez la fonctionnalité avec le script de test indépendant
4. Mettez à jour le notebook `extract_marker_editor.ipynb` si nécessaire
5. Documentez la nouvelle fonctionnalité dans ce README

### Exemple de nouvelle fonctionnalité

Voici un exemple d'ajout d'une fonctionnalité pour exporter les extraits au format Markdown :

```python
def export_to_markdown(extract_info, output_path):
    """
    Exporte les informations d'un extrait au format Markdown
    
    Args:
        extract_info (dict): Informations sur l'extrait
        output_path (str): Chemin du fichier de sortie
    
    Returns:
        bool: True si l'export a réussi, False sinon
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {extract_info.get('extract_name', 'Extrait sans nom')}\n\n")
            f.write(f"Source: {extract_info.get('source_name', 'Source inconnue')}\n\n")
            f.write("## Marqueurs\n\n")
            f.write(f"- Début: `{extract_info.get('start_marker', '')}`\n")
            f.write(f"- Fin: `{extract_info.get('end_marker', '')}`\n")
            if 'template_start' in extract_info and extract_info['template_start']:
                f.write(f"- Template: `{extract_info['template_start']}`\n")
            f.write("\n## Contenu\n\n")
            f.write(f"```\n{extract_info.get('extracted_text', '')}\n```\n")
        return True
    except Exception as e:
        print(f"Erreur lors de l'export au format Markdown: {e}")
        return False
```

## Développement avec l'approche multi-instance

1. Ouvrez ce répertoire (`ui/extract_editor/`) comme dossier racine dans une instance VSCode dédiée
2. Travaillez sur l'éditeur de marqueurs sans être distrait par les autres parties du projet
3. Testez vos modifications avec le script de test indépendant
4. Une fois les modifications validées, intégrez-les dans le projet principal

## Fonctionnalités 🛠️

- Interface utilisateur intuitive basée sur ipywidgets
- Chargement de texte depuis diverses sources
- Sélection précise des bornes d'extraits
- Prévisualisation en temps réel de l'extrait sélectionné
- Sauvegarde et chargement des configurations d'extraits
- Recherche de texte dans le document source
- Navigation dans les textes longs
- Suggestions automatiques pour les marqueurs

## Dépendances 📦

- ipywidgets
- jupyter-ui-poll
- pandas
- requests (pour le chargement depuis URL)

## Bonnes pratiques

- Gardez l'interface utilisateur simple et intuitive
- Documentez clairement les fonctionnalités et les paramètres
- Utilisez des noms explicites pour les fonctions et les variables
- Gérez correctement les erreurs et affichez des messages clairs à l'utilisateur
- Testez l'éditeur avec différents types de textes et de marqueurs
- Maintenez une séparation claire entre la logique UI et la logique métier