# Tests Unitaires et d'Intégration - Projet d'Analyse Argumentative

Ce répertoire contient les tests unitaires et d'intégration pour le projet d'analyse argumentative. Les tests sont organisés par module et utilisent principalement le framework `pytest`, avec support pour `unittest`.

## Structure des Tests

Les tests sont organisés comme suit:

### Tests des composants fondamentaux (Core)
- `test_shared_state.py`: Tests pour le module `core.shared_state`
- `test_state_manager_plugin.py`: Tests pour le module `core.state_manager_plugin`
- `test_strategies.py`: Tests pour le module `core.strategies`
- `test_llm_service.py`: Tests pour le module `core.llm_service`

### Tests des modèles
- `test_extract_definition.py`: Tests pour le modèle de définition d'extraits
- `test_extract_result.py`: Tests pour le modèle de résultat d'extraction

### Tests des services
- `test_cache_service.py`: Tests pour le service de cache
- `test_crypto_service.py`: Tests pour le service de chiffrement
- `test_definition_service.py`: Tests pour le service de définition
- `test_extract_service.py`: Tests pour le service d'extraction
- `test_fetch_service.py`: Tests pour le service de récupération

### Tests des agents
- `test_extract_agent.py`: Tests pour l'agent d'extraction
- `test_pl_definitions.py`: Tests pour le module de logique propositionnelle
- `test_informal_agent.py`: Tests pour l'agent d'analyse informelle
- `test_pm_agent.py`: Tests pour l'agent Project Manager

### Tests des scripts
- `test_repair_extract_markers.py`: Tests pour le script de réparation des marqueurs d'extraits
- `test_verify_extracts.py`: Tests pour le script de vérification des extraits

### Tests d'orchestration
- `test_analysis_runner.py`: Tests pour le module d'orchestration

### Tests d'intégration
- `test_integration.py`: Tests d'intégration entre les différents composants
- `test_integration_example.py`: Exemples de tests d'intégration

### Scripts d'exécution des tests
- `run_tests.py`: Script pour exécuter tous les tests avec pytest
- `run_tests.ps1`: Script PowerShell pour exécuter tous les tests
- `run_coverage.py`: Script pour exécuter les tests avec couverture de code
- `async_test_case.py`: Classe de base pour les tests asynchrones
- `conftest.py`: Configuration et fixtures pour pytest

## Exécution des Tests

### Exécuter tous les tests

#### Avec pytest (recommandé)

```bash
cd argumentiation_analysis
python -m pytest
```

Ou avec le script `run_tests.py`:

```bash
cd argumentiation_analysis
python -m tests.run_tests
```

#### Sous Windows (PowerShell)

```powershell
cd argumentiation_analysis
.\tests\run_tests.ps1
```

### Exécuter un test spécifique

Pour exécuter un test spécifique avec pytest:

```bash
cd argumentiation_analysis
python -m pytest tests/test_shared_state.py -v
```

Pour exécuter un groupe de tests spécifique:

```bash
cd argumentiation_analysis
python -m pytest tests/test_*_service.py -v
```

### Exécuter les tests avec couverture de code

Pour exécuter les tests avec couverture de code et générer un rapport détaillé:

```bash
cd argumentiation_analysis
python -m tests.run_coverage
```

Ce script amélioré:
1. Installe automatiquement le module `pytest-cov` s'il n'est pas déjà présent
2. Exécute tous les tests avec mesure de couverture
3. Génère un rapport de couverture dans la console
4. Analyse la couverture par module et affiche un tableau récapitulatif
5. Crée un rapport HTML détaillé dans le répertoire `tests/htmlcov`
6. Crée un rapport XML pour l'intégration CI/CD dans `tests/coverage.xml`
7. Vérifie si l'objectif de couverture minimal (80%) est atteint
8. Ouvre automatiquement le rapport HTML dans le navigateur

## Ajouter de Nouveaux Tests

### Avec pytest (recommandé)

Pour ajouter de nouveaux tests avec pytest, suivez ces étapes:

1. Créez un nouveau fichier de test dans le répertoire `tests` avec le préfixe `test_`.
2. Importez le module `pytest` et les modules à tester.
3. Écrivez des fonctions de test avec le préfixe `test_`.
4. Utilisez les assertions Python standard ou les fonctions d'assertion de pytest.
5. Utilisez des fixtures pour partager la configuration entre les tests.

Exemple avec pytest:

```python
import pytest
from models.extract_definition import Extract

def test_extract_creation():
    """Teste la création d'un extrait."""
    extract = Extract(
        extract_name="Test Extract",
        start_marker="START",
        end_marker="END"
    )
    assert extract.extract_name == "Test Extract"
    assert extract.start_marker == "START"
    assert extract.end_marker == "END"

@pytest.mark.parametrize("start_marker,end_marker", [
    ("START", "END"),
    ("BEGIN", "FINISH"),
    ("DEBUT", "FIN")
])
def test_extract_with_different_markers(start_marker, end_marker):
    """Teste la création d'extraits avec différents marqueurs."""
    extract = Extract(
        extract_name="Test Extract",
        start_marker=start_marker,
        end_marker=end_marker
    )
    assert extract.start_marker == start_marker
    assert extract.end_marker == end_marker
```

### Avec unittest (alternative)

Vous pouvez également utiliser unittest si vous préférez:

```python
import unittest
from models.extract_definition import Extract

class TestExtract(unittest.TestCase):
    def test_extract_creation(self):
        """Teste la création d'un extrait."""
        extract = Extract(
            extract_name="Test Extract",
            start_marker="START",
            end_marker="END"
        )
        self.assertEqual(extract.extract_name, "Test Extract")
        self.assertEqual(extract.start_marker, "START")
        self.assertEqual(extract.end_marker, "END")

if __name__ == '__main__':
    unittest.main()
```

### Imports et Chemins

Les tests doivent utiliser des imports absolus ou relatifs selon le contexte:

```python
# Import absolu (recommandé pour pytest)
from argumentiation_analysis.models.extract_definition import Extract

# Import relatif (si setup_import_paths() est utilisé)
from models.extract_definition import Extract
```

Le fichier `__init__.py` du package de tests contient une fonction `setup_import_paths()` qui configure correctement les chemins d'importation.

## Bonnes Pratiques

- **Indépendance des tests**: Chaque test doit être indépendant des autres tests.
- **Fixtures**: Utilisez des fixtures pytest pour partager la configuration entre les tests.
- **Mocks**: Utilisez des mocks pour isoler les dépendances externes.
- **Tests paramétrés**: Utilisez `@pytest.mark.parametrize` pour tester plusieurs cas avec une seule fonction.
- **Tests clairs**: Écrivez des tests clairs et concis avec des noms descriptifs.
- **Documentation**: Commentez vos tests pour expliquer ce qu'ils testent.
- **Couverture**: Visez une couverture de code élevée, mais privilégiez la qualité des tests à la quantité.

### Tests Asynchrones

Pour tester des fonctions asynchrones avec pytest:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Teste une fonction asynchrone."""
    result = await async_function()
    assert result == expected_result
```

Vous pouvez également utiliser la classe `AsyncTestCase` pour unittest:

```python
from tests.async_test_case import AsyncTestCase

class TestAsyncFunctions(AsyncTestCase):
    async def test_async_function(self):
        """Teste une fonction asynchrone."""
        result = await async_function()
        self.assertEqual(result, expected_result)
```

### Tests d'Intégration

Les tests d'intégration vérifient l'interaction entre les différents composants du système. Ils sont définis dans les fichiers `test_integration.py` et `test_integration_example.py`.

Pour exécuter uniquement les tests d'intégration:

```bash
cd argumentiation_analysis
python -m pytest tests/test_integration*.py -v
```

### Objectifs de Couverture

Le projet vise une couverture de code minimale de 80%. Les modules prioritaires pour la couverture sont:

1. `models`: Modèles de données
2. `services`: Services de base
3. `core`: Modules fondamentaux du système
4. `scripts`: Scripts utilitaires
5. `agents`: Agents d'analyse
6. `orchestration`: Orchestration des agents
7. `utils`: Utilitaires généraux

Les zones délibérément exclues de la couverture sont:
- Interface utilisateur (`ui`)
- Scripts d'exécution principaux (`main_*.py`, `run_*.py`)
- Code spécifique aux notebooks
- Fichiers de configuration et d'environnement

### Couverture des tests

Le projet comprend une suite complète de tests couvrant les différents aspects du système :

- **Tests des modèles de données**: Vérifient la structure et le comportement des modèles `Extract`, `SourceDefinition`, et `ExtractResult`.
- **Tests des services**: Testent les services de cache, chiffrement, définition, extraction et récupération.
- **Tests d'optimisation de l'agent informel**: Vérifient les outils d'analyse et d'amélioration de l'agent informel.
- **Tests de vérification des extraits**: Testent les fonctionnalités de vérification et de réparation des extraits.
- **Tests d'orchestration à grande échelle**: Évaluent la robustesse du système sur un grand nombre de textes.

### Intégration CI/CD

Le projet est configuré avec GitHub Actions pour l'intégration continue et le déploiement continu. Le workflow exécute automatiquement les tests et vérifie la couverture de code à chaque push et pull request.

Pour voir la configuration CI/CD:
```bash
cat .github/workflows/python-tests.yml
```

Le workflow CI/CD:
1. Exécute les tests sur plusieurs versions de Python
2. Génère un rapport de couverture de code
3. Télécharge le rapport sur Codecov
4. Vérifie que la couverture atteint l'objectif minimal de 80%

### Outils d'analyse et de qualité de code

Les tests sont intégrés avec plusieurs outils d'analyse:

- **pytest**: Framework de test principal
- **pytest-cov**: Mesure la couverture de code des tests
- **Pylint**: Analyse statique du code pour détecter les problèmes potentiels
- **Mypy** (optionnel): Vérification des types pour les annotations de type Python

Pour exécuter l'analyse statique du code:

```bash
# Installation des outils
pip install pylint mypy

# Exécution de Pylint
pylint argumentiation_analysis

# Exécution de Mypy
mypy argumentiation_analysis
```

### Mocks et fixtures

Le projet utilise des mocks et des fixtures pour isoler les composants et simuler les dépendances externes:

```python
# Exemple de mock pour une fonction asynchrone
from unittest.mock import AsyncMock

mock_async_function = AsyncMock()
mock_async_function.return_value = "résultat"

# Exemple de fixture pytest
@pytest.fixture
def sample_extract():
    """Fixture pour un extrait de test."""
    return Extract(
        extract_name="Test Extract",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT"
    )
```

Pour plus de détails sur les fixtures disponibles, consultez le fichier `conftest.py`.

## Ressources

- [Documentation pytest](https://docs.pytest.org/)
- [Documentation pytest-cov](https://pytest-cov.readthedocs.io/)
- [Documentation unittest](https://docs.python.org/3/library/unittest.html)
- [Documentation coverage](https://coverage.readthedocs.io/)
- [Python Mock Object Library](https://docs.python.org/3/library/unittest.mock.html)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)