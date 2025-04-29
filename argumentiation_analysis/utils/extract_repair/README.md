# 🔄 Réparation des Bornes d'Extraits (`utils/extract_repair/`)

Ce module fournit des outils pour la réparation automatique des bornes défectueuses dans les extraits de texte utilisés pour l'analyse rhétorique.

[Retour au README Utils](../README.md) | [Retour au README Principal](../../README.md)

## Objectif 🎯

L'outil de réparation des bornes d'extraits permet de:
1. Détecter les bornes défectueuses dans les extraits de texte
2. Proposer des corrections automatiques pour ces bornes
3. Appliquer les corrections et sauvegarder les extraits réparés
4. Générer des rapports détaillés sur les réparations effectuées

Cet outil est essentiel pour maintenir la qualité des extraits utilisés dans l'analyse rhétorique, en s'assurant que les bornes sont correctement définies et correspondent au texte source.

## Contenu 📁

* **[`repair_extract_markers.py`](./repair_extract_markers.py)** : Script principal pour la réparation automatique des bornes.
* **[`repair_extract_markers.ipynb`](./repair_extract_markers.ipynb)** : Notebook interactif pour la réparation des bornes.
* **[`__init__.py`](./__init__.py)** : Marque le dossier comme un package Python.
* **[`docs/`](./docs/)** : Documentation et rapports générés:
  * **[`repair_extract_markers_report.md`](./docs/repair_extract_markers_report.md)** : Documentation détaillée sur la réparation des bornes.
  * **[`repair_report.html`](./docs/repair_report.html)** : Rapport HTML généré par le script de réparation.

## Utilisation 🚀

### Via le script de lancement

Le moyen le plus simple d'utiliser l'outil de réparation est d'exécuter le script à la racine du projet:

```bash
python ../../run_extract_repair.py
```

### Via le notebook

Vous pouvez également ouvrir directement le notebook interactif:

```bash
jupyter notebook repair_extract_markers.ipynb
```

### Intégration dans d'autres modules

Le module peut être importé et utilisé dans d'autres parties du projet:

```python
from utils.extract_repair.repair_extract_markers import repair_all_extracts

# Lancer la réparation
repair_all_extracts()
```

## Fonctionnalités 🛠️

- Détection automatique des bornes défectueuses
- Algorithmes de correction intelligents basés sur la correspondance de texte
- Génération de rapports détaillés sur les réparations effectuées
- Interface utilisateur interactive via notebook Jupyter
- Sauvegarde automatique des extraits réparés

## Documentation 📚

La documentation détaillée sur le fonctionnement de l'outil de réparation est disponible dans le dossier `docs/`:

- [Documentation sur la réparation des bornes](./docs/repair_extract_markers_report.md)
- [Exemple de rapport de réparation](./docs/repair_report.html)


## Dépendances 📦

- pandas
- difflib (pour la comparaison de texte)
- jinja2 (pour la génération de rapports HTML)