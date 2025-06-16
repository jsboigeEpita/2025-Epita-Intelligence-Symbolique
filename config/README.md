# Configuration du Projet

Ce répertoire contient les fichiers de configuration utilisés par le projet d'analyse argumentative.

## Fichiers de Configuration

- **`pytest.ini`** : Configuration pour l'exécution des tests avec pytest, définissant les options par défaut et les marqueurs personnalisés.
- **`requirements-test.txt`** : Liste des dépendances Python nécessaires pour exécuter les tests du projet.

## Utilisation

Les fichiers de configuration dans ce répertoire sont utilisés par différents scripts et modules du projet pour maintenir une cohérence dans les paramètres et les environnements d'exécution.

### Configuration des Tests

Le fichier `pytest.ini` définit les paramètres par défaut pour l'exécution des tests avec pytest. Pour utiliser cette configuration :

```bash
# Exécuter les tests avec la configuration par défaut
pytest

# Exécuter les tests avec des options supplémentaires
pytest -v --cov=argumentiation_analysis
```

### Dépendances de Test

Le fichier `requirements-test.txt` liste les dépendances nécessaires pour exécuter les tests. Pour installer ces dépendances :

```bash
# Installer les dépendances de test
pip install -r config/requirements-test.txt
```

## Bonnes Pratiques

1. **Centralisation** : Tous les fichiers de configuration doivent être centralisés dans ce répertoire pour faciliter la maintenance.
2. **Documentation** : Chaque fichier de configuration doit être documenté pour expliquer son rôle et son utilisation.
3. **Versionnement** : Les fichiers de configuration sont versionnés avec le reste du code source pour assurer la cohérence entre les environnements.