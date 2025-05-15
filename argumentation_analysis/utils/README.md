# 🔧 Utilitaires (`utils/`)

Ce répertoire contient des fonctions utilitaires générales non spécifiques à un domaine particulier de l'application.

[Retour au README Principal](../README.md)

## Contenu

* **[`system_utils.py`](./system_utils.py)** :
    * `check_and_install`: Fonction (reprise de l'ancien notebook) pour vérifier/installer des packages Python via pip. Utilité limitée maintenant que `requirements.txt` est utilisé, mais peut servir pour des dépendances optionnelles.
* **[`extract_repair/`](./extract_repair/README.md)** 🔄 : Sous-module pour la réparation des bornes d'extraits défectueuses.

## Sous-modules

### Réparation des bornes d'extraits (`extract_repair/`) 🔄

Ce sous-module contient les outils pour réparer automatiquement les bornes défectueuses des extraits de texte:

* **[`repair_extract_markers.py`](./extract_repair/repair_extract_markers.py)** : Script de réparation automatique des bornes.
* **[`repair_extract_markers.ipynb`](./extract_repair/repair_extract_markers.ipynb)** : Notebook interactif pour la réparation des bornes.
* **[`docs/repair_extract_markers_report.md`](./extract_repair/docs/repair_extract_markers_report.md)** : Documentation sur la réparation des bornes.
* **[`docs/repair_report.html`](./extract_repair/docs/repair_report.html)** : Rapport HTML généré par le script de réparation.

Pour lancer l'outil de réparation, vous pouvez utiliser le script à la racine du projet:
```bash
python ../run_extract_repair.py
```

Ou ouvrir directement le notebook:
```bash
jupyter notebook extract_repair/repair_extract_markers.ipynb
```

Pour plus de détails, consultez le [README de l'outil de réparation](./extract_repair/README.md).
