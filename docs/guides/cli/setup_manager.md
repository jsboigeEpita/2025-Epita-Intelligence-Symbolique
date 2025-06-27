# Documentation : setup_manager.py

## Commande fix-deps

La commande `fix-deps` force la réinstallation de paquets Python spécifiques à leurs versions spécifiées. Cela est utile pour réparer des dépendances corrompues ou pour s'assurer qu'un environnement virtuel utilise les bonnes versions des paquets.

### Utilisation

```bash
python scripts/setup_manager.py fix-deps --package <package1> <package2> ...
```

### Exemple

Pour forcer la réinstallation des paquets `numpy` et `pandas` :

```bash
python scripts/setup_manager.py fix-deps --package numpy pandas