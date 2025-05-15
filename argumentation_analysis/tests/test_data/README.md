# Données de test pour l'analyse d'argumentation

Ce répertoire contient les données de test utilisées pour les tests unitaires et d'intégration du projet d'analyse d'argumentation.

## Structure des répertoires

- `extract_definitions/` : Fichiers de définitions d'extraits (JSON)
  - `valid/` : Définitions d'extraits valides
  - `partial/` : Définitions d'extraits partiellement valides
  - `invalid/` : Définitions d'extraits invalides
- `source_texts/` : Textes sources pour les tests
  - `with_markers/` : Textes sources contenant des marqueurs valides
  - `partial_markers/` : Textes sources avec des marqueurs partiellement présents
  - `no_markers/` : Textes sources sans marqueurs
- `service_configs/` : Configurations pour les services
  - `llm/` : Configurations pour le service LLM
  - `cache/` : Configurations pour le service de cache
  - `crypto/` : Configurations pour le service de chiffrement
- `error_cases/` : Données pour simuler différents cas d'erreur

## Utilisation

Ces données de test sont accessibles via les fixtures pytest définies dans `conftest.py`. Pour utiliser ces données dans vos tests, importez les fixtures appropriées.

Exemple:
```python
def test_extract_definition(valid_extract_definition):
    # Utiliser valid_extract_definition dans le test
    assert valid_extract_definition is not None
```

## Documentation des jeux de données

Chaque jeu de données est documenté dans un fichier README.md dans son répertoire respectif, décrivant:
- L'objectif du jeu de données
- Le contenu et la structure des fichiers
- Les cas de test couverts
- Les instructions d'utilisation spécifiques