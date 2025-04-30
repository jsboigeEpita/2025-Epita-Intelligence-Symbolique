# Tests Unitaires - Projet d'Analyse Argumentative

Ce répertoire contient les tests unitaires pour le projet d'analyse argumentative. Les tests sont organisés par module et utilisent le framework `unittest` de Python.

## Structure des Tests

Les tests sont organisés comme suit:

### Tests des composants fondamentaux (Core)
- `test_shared_state.py`: Tests pour le module `core.shared_state`
- `test_state_manager_plugin.py`: Tests pour le module `core.state_manager_plugin`
- `test_strategies.py`: Tests pour le module `core.strategies`
- `test_llm_service.py`: Tests pour le module `core.llm_service`

### Tests des agents
- `test_extract_agent.py`: Tests pour l'agent d'extraction
- `test_pl_definitions.py`: Tests pour le module de logique propositionnelle
- `test_informal_agent.py`: Tests pour l'agent d'analyse informelle
- `test_pm_agent.py`: Tests pour l'agent Project Manager

### Tests d'orchestration
- `test_analysis_runner.py`: Tests pour le module d'orchestration

### Tests des utilitaires
- `test_utils.py`: Tests pour les utilitaires du projet
- `test_integration.py`: Tests d'intégration entre les différents composants

### Scripts d'exécution des tests
- `run_tests.py`: Script pour exécuter tous les tests (Linux/macOS)
- `run_tests.ps1`: Script PowerShell pour exécuter tous les tests (Windows)
- `run_coverage.py`: Script pour exécuter les tests avec couverture de code
- `async_test_case.py`: Classe de base pour les tests asynchrones

## Exécution des Tests

### Exécuter tous les tests

#### Sous Windows (PowerShell)

Pour exécuter tous les tests sous Windows avec PowerShell:

```powershell
.\run_tests.ps1
```

#### Sous Linux/macOS (Bash)

Pour exécuter tous les tests sous Linux ou macOS:

```bash
python -m argumentiation_analysis.tests.run_tests
```

Ou simplement:

```bash
python run_tests.py
```

### Exécuter un test spécifique

Pour exécuter un test spécifique, utilisez la commande suivante:

```bash
python -m unittest argumentiation_analysis.tests.test_shared_state
```

### Exécuter les tests avec couverture de code

Pour exécuter les tests avec couverture de code et générer un rapport détaillé, utilisez le script `run_coverage.py`:

```bash
python -m argumentiation_analysis.tests.run_coverage
```

Ce script:
1. Installe automatiquement le module `coverage` s'il n'est pas déjà présent
2. Exécute tous les tests unitaires avec mesure de couverture
3. Génère un rapport de couverture dans la console
4. Crée un rapport HTML détaillé dans le répertoire `tests/htmlcov`
5. Crée un rapport XML pour l'intégration CI/CD dans `tests/coverage.xml`
6. Vérifie si l'objectif de couverture minimal (80%) est atteint
7. Ouvre automatiquement le rapport HTML dans le navigateur

Vous pouvez également utiliser les scripts `run_tests.py` ou `run_tests.ps1` qui détecteront automatiquement la présence du module `coverage`:

```bash
python -m argumentiation_analysis.tests.run_tests
```

ou sous Windows:

```powershell
.\tests\run_tests.ps1
```

## Ajouter de Nouveaux Tests

Pour ajouter de nouveaux tests, suivez ces étapes:

1. Créez un nouveau fichier de test dans le répertoire `tests` avec le préfixe `test_`.
2. Importez le module `unittest` et les modules à tester.
3. Créez une classe de test qui hérite de `unittest.TestCase` (ou `AsyncTestCase` pour les tests asynchrones).
4. Ajoutez des méthodes de test avec le préfixe `test_`.
5. Utilisez les méthodes d'assertion fournies par `unittest.TestCase` pour vérifier les résultats.

### Imports Relatifs

Les tests doivent utiliser des imports relatifs (sans le préfixe `argumentiation_analysis`). Par exemple:

```python
# Correct (import relatif)
from core.shared_state import RhetoricalAnalysisState

# Incorrect (import absolu)
from argumentiation_analysis.core.shared_state import RhetoricalAnalysisState
```

Cela est rendu possible par l'ajout du répertoire parent au chemin de recherche des modules dans les scripts d'exécution (`run_tests.py` et `run_tests.ps1`).

Exemple:

```python
import unittest
from argumentiation_analysis.module_a import ClassA

class TestClassA(unittest.TestCase):
    def setUp(self):
        """Initialisation avant chaque test."""
        self.instance = ClassA()
    
    def test_method_a(self):
        """Teste la méthode A."""
        result = self.instance.method_a()
        self.assertEqual(result, expected_result)
    
    def test_method_b(self):
        """Teste la méthode B."""
        result = self.instance.method_b()
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()
```

## Bonnes Pratiques

- Chaque test doit être indépendant des autres tests.
- Utilisez `setUp` et `tearDown` pour initialiser et nettoyer l'environnement de test.
- Utilisez des mocks pour isoler les dépendances externes.
- Écrivez des tests clairs et concis avec des noms descriptifs.
- Commentez vos tests pour expliquer ce qu'ils testent.
- Visez une couverture de code élevée, mais privilégiez la qualité des tests à la quantité.

### Tests Asynchrones

Pour tester des fonctions asynchrones (async/await), utilisez la classe `AsyncTestCase` comme base pour vos classes de test:

```python
from tests.async_test_case import AsyncTestCase

class TestAsyncFunctions(AsyncTestCase):
    async def test_async_function(self):
        """Teste une fonction asynchrone."""
        result = await async_function()
        self.assertEqual(result, expected_result)
```

La classe `AsyncTestCase` s'occupe d'exécuter les méthodes de test asynchrones dans une boucle d'événements asyncio.

### Tests d'Intégration

Les tests d'intégration vérifient l'interaction entre les différents composants du système. Ils sont définis dans le fichier `test_integration.py` et simulent un flux d'analyse complet.

Pour exécuter uniquement les tests d'intégration:

```bash
python -m unittest argumentiation_analysis.tests.test_integration
```

### Objectifs de Couverture

Le projet vise une couverture de code minimale de 80%. Les modules prioritaires pour la couverture sont:

1. `core`: Modules fondamentaux du système
2. `agents`: Agents d'analyse
3. `orchestration`: Orchestration des agents

Les zones délibérément exclues de la couverture sont:
- Interface utilisateur (`ui`)
- Scripts d'exécution principaux (`main_*.py`, `run_*.py`)
- Code spécifique aux notebooks

### Tests récemment ajoutés

Plusieurs nouveaux tests ont été ajoutés pour couvrir les fonctionnalités récemment développées:

- **Tests d'optimisation de l'agent informel**: Vérifient les outils d'analyse et d'amélioration de l'agent informel.
- **Tests de vérification des extraits**: Testent les fonctionnalités de vérification et de réparation des extraits.
- **Tests d'orchestration à grande échelle**: Évaluent la robustesse du système sur un grand nombre de textes.

Ces tests sont particulièrement importants pour assurer la qualité et la fiabilité des nouvelles fonctionnalités.

### Intégration avec les outils d'analyse

Les tests sont intégrés avec plusieurs outils d'analyse:

- **Coverage.py**: Mesure la couverture de code des tests.
- **Pytest** (optionnel): Peut être utilisé comme alternative à unittest pour une syntaxe plus concise.
- **Pylint**: Analyse statique du code pour détecter les problèmes potentiels.
- **Mypy** (optionnel): Vérification des types pour les annotations de type Python.

Pour exécuter l'analyse statique du code:

```bash
# Installation des outils
pip install pylint mypy

# Exécution de Pylint
pylint argumentiation_analysis

# Exécution de Mypy
mypy argumentiation_analysis
```

### Mocks pour les fonctions asynchrones

Pour les fonctions asynchrones, utilisez `AsyncMock` au lieu de `MagicMock`:

```python
from unittest.mock import AsyncMock

# Pour une fonction asynchrone
mock_async_function = AsyncMock()
mock_async_function.return_value = "résultat"

# Pour simuler un itérateur asynchrone
mock_async_function.return_value = self._create_async_iterator([item1, item2])

# Fonction utilitaire pour créer un itérateur asynchrone
def _create_async_iterator(self, items):
    async def async_iterator():
        for item in items:
            yield item
    return async_iterator()
```

## Ressources

- [Documentation unittest](https://docs.python.org/3/library/unittest.html)
- [Documentation coverage](https://coverage.readthedocs.io/)
- [Python Testing with unittest](https://docs.python.org/3/library/unittest.html)
- [Python Mock Object Library](https://docs.python.org/3/library/unittest.mock.html)