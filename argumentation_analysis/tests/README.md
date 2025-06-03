# Tests Unitaires et d'Intégration - Projet d'Analyse Argumentative

Ce répertoire contient les tests unitaires et d'intégration pour le projet d'analyse argumentative. Les tests sont organisés par module et utilisent principalement le framework `pytest`, avec support pour `unittest`.

## Structure des Tests

Les tests sont organisés comme suit:

- **Tests des composants fondamentaux (Core)**:
    - `test_shared_state.py`: Tests pour le module `core.shared_state`
    - `test_state_manager_plugin.py`: Tests pour le module `core.state_manager_plugin`
    - `test_strategies.py`: Tests pour le module `core.strategies`
    - `test_llm_service.py`: Tests pour le module `core.llm_service`
- **Tests des modèles**:
    - `test_extract_definition.py`: Tests pour le modèle de définition d'extraits
    - `test_extract_result.py`: Tests pour le modèle de résultat d'extraction
- **Tests des services**:
    - `test_cache_service.py`: Tests pour le service de cache
    - `test_crypto_service.py`: Tests pour le service de chiffrement
    - `test_definition_service.py`: Tests pour le service de définition
    - `test_extract_service.py`: Tests pour le service d'extraction
    - `test_fetch_service.py`: Tests pour le service de récupération
- **Tests des agents**:
    - `test_extract_agent.py`: Tests pour l'agent d'extraction
    - `test_pl_definitions.py`: Tests pour le module de logique propositionnelle
    - `test_informal_agent.py`: Tests pour l'agent d'analyse informelle
    - `test_pm_agent.py`: Tests pour l'agent Project Manager
- **Tests des scripts (si pertinents et non couverts par des tests d'intégration plus larges)**:
    - `test_repair_extract_markers.py`: Tests pour le script de réparation des marqueurs d'extraits
    - `test_verify_extracts.py`: Tests pour le script de vérification des extraits
- **Tests d'orchestration**:
    - `test_analysis_runner.py`: Tests pour le module d'orchestration
- **Tests d'intégration**:
    - `test_integration.py`: Tests d'intégration généraux entre les différents composants.
    - `test_integration_example.py`: Exemples de tests d'intégration.
    - `test_integration_balanced_strategy.py`: Tests pour la stratégie d'équilibrage.
    - `test_integration_end_to_end.py`: Tests du flux complet d'analyse.
    - `test_agent_interaction.py`: Tests des interactions entre agents.
    - Pour plus de détails sur les tests d'intégration, les mocks et fixtures, consultez les READMEs spécifiques :
        - [`README_integration_tests.md`](README_integration_tests.md) (mocks et fixtures de base)
        - [`README_integration_tests_extended.md`](README_integration_tests_extended.md) (stratégie d'équilibrage et interactions avancées)
- **Données de test**:
    - Les données de test sont situées dans le sous-dossier [`test_data/`](test_data/). Voir [`test_data/README.md`](test_data/README.md) pour plus de détails sur leur structure et utilisation.
- **Tests des outils d'analyse rhétorique**:
    - Les tests spécifiques aux outils d'analyse rhétorique sont dans le sous-dossier [`tools/`](tools/). Voir [`tools/README.md`](tools/README.md) pour les instructions d'exécution et [`tools/test_data/README.md`](tools/test_data/README.md) pour les données de test associées.
- **Configuration et utilitaires de test**:
    - `async_test_case.py`: Classe de base pour les tests asynchrones `unittest`.
    - `conftest.py`: Configuration et fixtures globales pour `pytest`.
    - `jvm_test_case.py`: Classe de base pour les tests nécessitant une JVM.
- **Scripts d'exécution restants (à évaluer pour suppression/intégration)**:
    - `run_fixed_tests.py`: Script pour exécuter des tests spécifiques avec une logique de fallback.
    - `run_tests.ps1`: Script PowerShell pour exécuter les tests avec `unittest discover` et gérer les JARs.
    - `update_rapport_suivi.py`: (Fonctionnalité à déterminer)

## Exécution des Tests

### Prérequis

Assurez-vous d'avoir installé `pytest` et les dépendances nécessaires :
```bash
pip install pytest pytest-asyncio pytest-cov
# Autres dépendances du projet listées dans requirements.txt
```

### Configuration de Pytest

La configuration de `pytest` (y compris le mode `asyncio`, les chemins, et la couverture) est gérée dans le fichier [`pytest.ini`](../../pytest.ini) à la racine du projet.

### Exécuter tous les tests (recommandé)

Depuis la racine du projet (`c:/dev/2025-Epita-Intelligence-Symbolique`):
```bash
pytest
```
Ou de manière plus explicite pour cibler le package :
```bash
python -m pytest argumentation_analysis/
```

Pour plus de détails (mode verbeux) :
```bash
pytest -v
```

### Exécuter un fichier ou un répertoire de test spécifique

```bash
# Exécuter tous les tests dans un fichier
pytest argumentation_analysis/tests/test_shared_state.py

# Exécuter tous les tests dans un répertoire
pytest argumentation_analysis/tests/services/
```

### Exécuter un test spécifique par nom (mot-clé)

```bash
pytest -k "test_extract_creation" -v
```
Ceci exécutera tous les tests dont le nom contient "test_extract_creation".

### Exécuter des tests avec des marqueurs

Si des marqueurs sont définis (ex: `@pytest.mark.integration`), vous pouvez les utiliser :
```bash
pytest -m integration
```

### Exécution avec le script PowerShell (pour `unittest discover` et gestion des JARs)

Si vous avez besoin de la logique spécifique du script PowerShell (par exemple, pour le téléchargement des JARs pour certains tests `unittest`) :
```powershell
cd argumentation_analysis/tests
.\run_tests.ps1
```

## Couverture de Code

La couverture de code est configurée dans [`pytest.ini`](../../pytest.ini). Pour générer un rapport :

```bash
pytest --cov
```
Cela affichera un résumé dans le terminal.

Pour générer un rapport HTML détaillé (dans `tests/htmlcov/`) :
```bash
pytest --cov --cov-report=html
```
Ouvrez `tests/htmlcov/index.html` dans votre navigateur.

Pour générer un rapport XML (dans `tests/coverage.xml`), utile pour l'intégration continue :
```bash
pytest --cov --cov-report=xml
```

L'objectif de couverture minimal est de 80%.

## Ajouter de Nouveaux Tests

### Avec pytest (recommandé)

1.  Créez un nouveau fichier de test dans le répertoire `argumentation_analysis/tests/` (ou un sous-répertoire approprié) avec le préfixe `test_` (ex: `test_nouveau_module.py`).
2.  Importez `pytest` et les modules à tester.
3.  Écrivez des fonctions de test avec le préfixe `test_` (ex: `def test_ma_fonctionnalite():`).
4.  Utilisez les assertions Python standard (`assert`) ou les fonctions d'assertion de `pytest`.
5.  Utilisez des fixtures (définies dans `conftest.py` ou localement) pour partager la configuration et les données de test.

Exemple :
```python
import pytest
from argumentation_analysis.models.extract_definition import Extract # Assurez-vous que le chemin est correct

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

### Tests Asynchrones avec pytest

Pour tester des fonctions `async` :
```python
import pytest

@pytest.mark.asyncio
async def test_ma_fonction_async():
    result = await ma_fonction_async()
    assert result == "valeur attendue"
```
Assurez-vous que `asyncio_mode = auto` est défini dans [`pytest.ini`](../../pytest.ini).

## Bonnes Pratiques

-   **Indépendance des tests**: Chaque test doit être indépendant.
-   **Fixtures**: Utilisez des fixtures `pytest` pour la configuration et les données.
-   **Mocks**: Utilisez `unittest.mock` ou des fixtures de mock `pytest` pour isoler les dépendances.
-   **Tests paramétrés**: Utilisez `@pytest.mark.parametrize` pour tester plusieurs cas.
-   **Clarté**: Écrivez des tests clairs avec des noms descriptifs.
-   **Documentation**: Commentez vos tests.
-   **Couverture**: Visez une couverture élevée et de qualité.

## Intégration Continue (CI/CD)

Le projet utilise GitHub Actions pour l'intégration continue. Le workflow exécute automatiquement les tests et vérifie la couverture à chaque push et pull request. Voir `.github/workflows/python-tests.yml`.

## Outils d'Analyse et Qualité

-   **pytest**: Framework de test.
-   **pytest-cov**: Mesure de couverture.
-   **Pylint / Flake8**: Analyse statique (configuration à vérifier/ajouter au projet).
-   **Mypy**: Vérification de types (configuration à vérifier/ajouter au projet).

## Résolution des problèmes courants

### Problèmes d'imports
Assurez-vous que `PYTHONPATH` est correctement configuré (généralement géré par `pytest` via `pytest.ini` ou la structure du projet) et que les fichiers `__init__.py` sont présents dans les répertoires de packages. Exécutez `pytest` depuis la racine du projet.

### Tests asynchrones
Vérifiez la configuration `asyncio_mode` dans `pytest.ini` et l'utilisation de `@pytest.mark.asyncio`.

## Ressources
- [Documentation pytest](https://docs.pytest.org/)
- [Documentation pytest-cov](https://pytest-cov.readthedocs.io/)
- [Documentation pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Documentation unittest.mock](https://docs.python.org/3/library/unittest.mock.html)