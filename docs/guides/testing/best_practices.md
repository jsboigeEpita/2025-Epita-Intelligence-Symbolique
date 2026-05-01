# Bonnes Pratiques pour les Tests d'Intégration et Fonctionnels

Ce document présente les bonnes pratiques à suivre pour l'écriture et l'exécution des tests d'intégration et fonctionnels dans le projet d'Intelligence Symbolique.

## Table des Matières

1. [Principes Généraux](#principes-généraux)
2. [Organisation des Tests](#organisation-des-tests)
3. [Gestion des Dépendances](#gestion-des-dépendances)
4. [Fixtures et Utilitaires](#fixtures-et-utilitaires)
5. [Tests d'Intégration](#tests-dintégration)
6. [Tests Fonctionnels](#tests-fonctionnels)
7. [Exécution des Tests](#exécution-des-tests)
8. [Résolution des Problèmes Courants](#résolution-des-problèmes-courants)

## Principes Généraux

### Objectifs des Tests

- **Tests d'intégration** : Vérifier que les différents modules du système fonctionnent correctement ensemble.
- **Tests fonctionnels** : Vérifier que le système répond aux exigences fonctionnelles et se comporte comme prévu du point de vue de l'utilisateur.

### Bonnes Pratiques Générales

1. **Isolation** : Chaque test doit être indépendant des autres tests.
2. **Reproductibilité** : Les tests doivent être reproductibles et donner les mêmes résultats à chaque exécution.
3. **Clarté** : Les tests doivent être clairs et faciles à comprendre.
4. **Maintenabilité** : Les tests doivent être faciles à maintenir et à mettre à jour.
5. **Couverture** : Les tests doivent couvrir les cas normaux, les cas limites et les cas d'erreur.

## Organisation des Tests

### Structure des Répertoires

```
tests/
├── __init__.py
├── conftest.py                    # Configuration globale pour pytest
├── test_*.py                      # Tests unitaires
├── integration/                   # Tests d'intégration
│   ├── __init__.py
│   ├── test_*_integration.py      # Tests d'intégration spécifiques
├── functional/                    # Tests fonctionnels
│   ├── __init__.py
│   ├── test_*_workflow.py         # Tests de flux de travail
├── fixtures/                      # Fixtures réutilisables
│   ├── __init__.py
│   ├── *_fixtures.py              # Fixtures spécifiques
├── utils/                         # Utilitaires pour les tests
│   ├── __init__.py
│   ├── test_*.py                  # Utilitaires spécifiques
├── mocks/                         # Mocks pour les dépendances
│   ├── __init__.py
│   ├── *_mock.py                  # Mocks spécifiques
```

### Conventions de Nommage

- **Tests d'intégration** : `test_*_integration.py`
- **Tests fonctionnels** : `test_*_workflow.py`
- **Fixtures** : `*_fixtures.py`
- **Utilitaires** : `test_*.py`
- **Mocks** : `*_mock.py`

### Tests Asynchrones

Pour les tests nécessitant des opérations asynchrones, le projet utilise `pytest-asyncio`. Les tests asynchrones doivent être marqués avec `@pytest.mark.anyio`.

Exemple :
```python
import pytest

@pytest.mark.anyio
async def test_ma_fonction_asynchrone():
    # ... code du test ...
    result = await ma_fonction_asynchrone()
    assert result == "valeur attendue"
```
L'ancienne classe utilitaire `AsyncTestCase` est obsolète et a été retirée du projet.
## Gestion des Dépendances

### Approche de Résolution des Dépendances

L'approche recommandée est de résoudre les problèmes de dépendances (numpy, pandas, jpype) en utilisant des versions spécifiques connues pour être compatibles avec notre environnement de test.

```bash
# Windows (PowerShell)
.\scripts\setup\fix_dependencies.ps1

# Linux/macOS
python scripts/setup/fix_dependencies.py
```

### Vérification des Dépendances

Avant d'exécuter les tests, vérifiez que les dépendances sont correctement installées :

```bash
# Windows (PowerShell)
.\scripts\setup\test_dependencies.ps1

# Linux/macOS
python scripts/setup/test_dependencies.py
```

### Utilisation des Mocks

Dans certains cas, il peut être nécessaire d'utiliser des mocks pour les dépendances problématiques. Utilisez les mocks fournis dans le répertoire `tests/mocks/` :

```python
from tests.utils.test_helpers import mocked_dependencies

with mocked_dependencies():
    # Code utilisant les dépendances mockées
    result = my_function()
```

## Fixtures et Utilitaires

### Utilisation des Fixtures

Les fixtures sont des fonctions qui fournissent des données ou des objets réutilisables pour les tests. Utilisez les fixtures fournies dans le répertoire `tests/fixtures/` :

```python
import pytest
from tests.fixtures.rhetorical_data_fixtures import example_text, example_fallacies

def test_fallacy_detection(example_text, example_fallacies):
    # Utiliser example_text et example_fallacies dans le test
    pass
```

### Utilitaires de Test

Les utilitaires de test sont des fonctions qui facilitent l'écriture et l'exécution des tests. Utilisez les utilitaires fournis dans le répertoire `tests/utils/` :

```python
from tests.utils.test_helpers import temp_file, read_json_file

def test_file_processing():
    with temp_file("Contenu de test") as file_path:
        # Utiliser file_path dans le test
        result = process_file(file_path)
        assert result is not None
```

### Générateurs de Données

Les générateurs de données sont des fonctions qui génèrent des données de test. Utilisez les générateurs fournis dans le répertoire `tests/utils/` :

```python
from tests.utils.test_data_generators import generate_text_with_fallacies

def test_fallacy_analysis():
    text = generate_text_with_fallacies(fallacy_types=["ad_hominem", "faux_dilemme"])
    # Utiliser text dans le test
    result = analyze_fallacies(text)
    assert len(result["fallacies"]) > 0
```

## Tests d'Intégration

### Patterns pour les Tests d'Intégration

1. **Pattern d'Intégration de Modules** : Tester l'interaction entre deux modules adjacents.

```python
def test_module_integration():
    # Créer les modules
    module1 = Module1()
    module2 = Module2()
    
    # Configurer l'interaction
    module1.connect(module2)
    
    # Exécuter l'opération
    result = module1.process_with_module2("input")
    
    # Vérifier le résultat
    assert result == "expected output"
```

2. **Pattern d'Intégration de Composants** : Tester l'interaction entre plusieurs composants.

```python
def test_component_integration():
    # Créer les composants
    component1 = Component1()
    component2 = Component2()
    component3 = Component3()
    
    # Configurer l'interaction
    system = System([component1, component2, component3])
    
    # Exécuter l'opération
    result = system.process("input")
    
    # Vérifier le résultat
    assert result == "expected output"
```

3. **Pattern d'Intégration de Sous-systèmes** : Tester l'interaction entre des sous-systèmes.

```python
def test_subsystem_integration():
    # Créer les sous-systèmes
    subsystem1 = Subsystem1()
    subsystem2 = Subsystem2()
    
    # Configurer l'interaction
    system = System(subsystem1, subsystem2)
    
    # Exécuter l'opération
    result = system.process("input")
    
    # Vérifier le résultat
    assert result == "expected output"
```

### Bonnes Pratiques pour les Tests d'Intégration

1. **Isolation des Dépendances Externes** : Utilisez des mocks ou des stubs pour isoler les dépendances externes.
2. **Tests Progressifs** : Commencez par tester l'intégration de petits modules, puis progressez vers des intégrations plus complexes.
3. **Vérification des Interfaces** : Vérifiez que les interfaces entre les modules sont correctement utilisées.
4. **Gestion des Erreurs** : Testez la gestion des erreurs entre les modules.
5. **Nettoyage** : Assurez-vous de nettoyer les ressources après chaque test.

### Comment tester un agent logique qui dépend de la JVM ?

Tout test impliquant un agent logique (comme `PropositionalLogicAgent` ou d'autres agents basés sur `TweetyBridge`) nécessite que la JVM soit démarrée. Pour garantir cela de manière propre et centralisée, utilisez la fixture `jvm_session`.

**Comment faire :**

Ajoutez le décorateur `@pytest.mark.usefixtures("jvm_session")` au-dessus de votre classe de test.

**Exemple :**

```python
import pytest

# Assure que la JVM est initialisée avant l'exécution de ces tests.
@pytest.mark.usefixtures("jvm_session")
class TestMonAgentLogique:
    def test_une_fonction_qui_utilise_la_jvm(self):
        # Ce test s'exécutera avec la garantie que la JVM est prête.
        assert True
```

Cette pratique évite les erreurs `RuntimeError: JVM not ready` et centralise la gestion du cycle de vie de la JVM pour toute la session de test.

## Tests Fonctionnels

### Patterns pour les Tests Fonctionnels

1. **Pattern de Flux de Travail** : Tester un flux de travail complet du point de vue de l'utilisateur.

```python
def test_workflow():
    # Configurer l'environnement
    setup_environment()
    
    # Exécuter les étapes du flux de travail
    step1_result = execute_step1("input1")
    step2_result = execute_step2(step1_result, "input2")
    final_result = execute_step3(step2_result)
    
    # Vérifier le résultat final
    assert final_result == "expected output"
    
    # Nettoyer l'environnement
    cleanup_environment()
```

2. **Pattern de Scénario** : Tester un scénario spécifique.

```python
def test_scenario():
    # Configurer le scénario
    setup_scenario()
    
    # Exécuter le scénario
    result = execute_scenario("input")
    
    # Vérifier le résultat
    assert result == "expected output"
    
    # Nettoyer le scénario
    cleanup_scenario()
```

3. **Pattern de Cas d'Utilisation** : Tester un cas d'utilisation spécifique.

```python
def test_use_case():
    # Configurer le cas d'utilisation
    setup_use_case()
    
    # Exécuter le cas d'utilisation
    result = execute_use_case("input")
    
    # Vérifier le résultat
    assert result == "expected output"
    
    # Nettoyer le cas d'utilisation
    cleanup_use_case()
```

### Bonnes Pratiques pour les Tests Fonctionnels

1. **Tests de Bout en Bout** : Testez le système de bout en bout, du point de vue de l'utilisateur.
2. **Scénarios Réalistes** : Utilisez des scénarios réalistes pour les tests.
3. **Données Réalistes** : Utilisez des données réalistes pour les tests.
4. **Vérification des Résultats** : Vérifiez que les résultats correspondent aux attentes de l'utilisateur.
5. **Documentation** : Documentez les scénarios de test pour faciliter leur compréhension et leur maintenance.

## Exécution des Tests

### Exécution des Tests d'Intégration

```bash
# Exécuter tous les tests d'intégration
pytest tests/integration/

# Exécuter un test d'intégration spécifique
pytest tests/integration/test_tactical_operational_integration.py
```

### Exécution des Tests Fonctionnels

```bash
# Exécuter tous les tests fonctionnels
pytest tests/functional/

# Exécuter un test fonctionnel spécifique
pytest tests/functional/test_rhetorical_analysis_workflow.py
```

### Exécution avec Couverture de Code

```bash
# Exécuter les tests avec couverture de code
pytest --cov=argumentation_analysis tests/integration/ tests/functional/

# Générer un rapport HTML de couverture
pytest --cov=argumentation_analysis --cov-report=html tests/integration/ tests/functional/
```

## Résolution des Problèmes Courants

### Problèmes de Dépendances

Si vous rencontrez des problèmes avec les dépendances, essayez les solutions suivantes :

1. **Réinstaller les dépendances** :

```bash
# Windows (PowerShell)
.\scripts\setup\fix_dependencies.ps1

# Linux/macOS
python scripts/setup/fix_dependencies.py
```

2. **Utiliser les mocks** :

```python
from tests.utils.test_helpers import mocked_dependencies

with mocked_dependencies():
    # Code utilisant les dépendances mockées
    result = my_function()
```

### Problèmes d'Isolation des Tests

Si les tests ne sont pas correctement isolés, essayez les solutions suivantes :

1. **Utiliser des fixtures avec portée de fonction** :

```python
@pytest.fixture(scope="function")
def my_fixture():
    # Configurer la fixture
    yield my_object
    # Nettoyer la fixture
```

2. **Utiliser des répertoires temporaires** :

```python
from tests.utils.test_helpers import temp_directory

def test_file_operations():
    with temp_directory() as temp_dir:
        # Utiliser temp_dir pour les opérations de fichier
        pass
```

### Problèmes de Reproductibilité

Si les tests ne sont pas reproductibles, essayez les solutions suivantes :

1. **Fixer les graines aléatoires** :

```python
import random
import numpy as np

def test_random_operations():
    # Fixer les graines aléatoires
    random.seed(42)
    np.random.seed(42)
    
    # Exécuter les opérations aléatoires
    result = my_random_function()
    
    # Vérifier le résultat
    assert result == "expected output"
```

2. **Utiliser des données de test fixes** :

```python
from tests.fixtures.rhetorical_data_fixtures import example_text

def test_text_analysis(example_text):
    # Utiliser example_text au lieu de générer du texte aléatoire
    result = analyze_text(example_text)
    assert result is not None
```

## Conclusion

En suivant ces bonnes pratiques, vous pourrez écrire des tests d'intégration et fonctionnels efficaces, maintenables et reproductibles. Ces tests vous aideront à garantir la qualité et la fiabilité du système d'analyse rhétorique et de détection des sophismes.