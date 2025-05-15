# Guide d'exécution des tests et d'analyse de la couverture de code

Ce document explique comment exécuter les tests unitaires et d'intégration du projet d'analyse d'argumentation, et comment analyser les résultats de la couverture de code.

## Prérequis

Avant d'exécuter les tests, assurez-vous d'avoir installé toutes les dépendances nécessaires :

```bash
pip install -r requirements.txt
```

Les packages suivants sont particulièrement importants pour les tests :
- pytest
- pytest-cov
- pytest-asyncio (pour les tests asynchrones)
- coverage

## Exécution des tests

### Exécuter tous les tests

Pour exécuter tous les tests du projet :

```bash
python -m pytest
```

### Exécuter des tests spécifiques

Pour exécuter des tests spécifiques, vous pouvez spécifier le chemin vers le fichier de test :

```bash
python -m pytest tests/test_extract_definition.py
```

Ou utiliser l'option `-k` pour filtrer les tests par nom :

```bash
python -m pytest -k "extract"
```

### Exécuter les tests avec verbosité

Pour afficher plus de détails sur les tests exécutés :

```bash
python -m pytest -v
```

## Mesure de la couverture de code

### Exécuter les tests avec couverture de code

Pour exécuter les tests avec mesure de la couverture de code :

```bash
python -m pytest --cov=. tests/
```

Pour se concentrer sur des modules spécifiques :

```bash
python -m pytest --cov=models --cov=services tests/
```

### Générer des rapports de couverture

Pour générer un rapport de couverture détaillé au format HTML :

```bash
python -m pytest --cov=. --cov-report=html tests/
```

Le rapport sera généré dans le répertoire `htmlcov/`.

Pour générer un rapport au format XML (utile pour l'intégration CI/CD) :

```bash
python -m pytest --cov=. --cov-report=xml tests/
```

Le rapport sera généré dans le fichier `coverage.xml`.

### Utiliser le script run_coverage.py

Le script `run_coverage.py` automatise l'exécution des tests avec couverture de code et la génération de rapports :

```bash
python tests/run_coverage.py
```

Ce script :
1. Exécute tous les tests avec mesure de couverture
2. Génère un rapport de couverture dans la console
3. Analyse la couverture par module et affiche un tableau récapitulatif
4. Crée un rapport HTML détaillé dans le répertoire `tests/htmlcov/`
5. Crée un rapport XML pour l'intégration CI/CD dans `tests/coverage.xml`
6. Vérifie si l'objectif de couverture minimal (80%) est atteint
7. Ouvre automatiquement le rapport HTML dans le navigateur

## Analyse des résultats de couverture

### Comprendre le rapport de couverture

Le rapport de couverture indique pour chaque fichier :
- **Stmts** : Nombre total de lignes de code exécutables
- **Miss** : Nombre de lignes non couvertes par les tests
- **Cover** : Pourcentage de couverture (Stmts - Miss) / Stmts * 100

### Objectifs de couverture

L'objectif de couverture global est de 80%. Les modules prioritaires sont :
1. `models` : Modèles de données
2. `services` : Services de base

### Améliorer la couverture de code

Si la couverture est inférieure à l'objectif, vous pouvez l'améliorer en :
1. Ajoutant des tests pour les lignes non couvertes
2. Utilisant des tests paramétrés pour couvrir différents cas
3. Testant les cas d'erreur et les cas limites

## Intégration CI/CD

Les tests sont automatiquement exécutés dans le pipeline CI/CD configuré avec GitHub Actions. Le workflow est défini dans le fichier `.github/workflows/python-tests.yml`.

Le pipeline :
1. Exécute les tests sur plusieurs versions de Python
2. Génère un rapport de couverture de code
3. Télécharge le rapport sur Codecov
4. Vérifie que la couverture atteint l'objectif minimal de 80%

## Résolution des problèmes courants

### Problèmes d'imports relatifs

Si vous rencontrez des erreurs d'imports relatifs, assurez-vous que :
1. Le répertoire parent est dans le chemin de recherche des modules
2. Les fichiers `__init__.py` sont présents dans tous les répertoires du package
3. Vous exécutez les tests depuis le répertoire racine du projet

### Tests qui échouent en raison de chemins de fichiers

Certains tests peuvent échouer en raison de chemins de fichiers qui n'existent pas dans l'environnement de test. Utilisez des fixtures pour créer des fichiers temporaires ou mocker les opérations de fichiers.

### Tests asynchrones

Pour les tests asynchrones, utilisez le décorateur `@pytest.mark.asyncio` et assurez-vous que le plugin `pytest-asyncio` est installé.