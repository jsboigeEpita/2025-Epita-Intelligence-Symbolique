# Tests d'Intégration pour le Projet d'Intelligence Symbolique

Ce document explique comment écrire, exécuter et maintenir les tests d'intégration pour le projet d'Intelligence Symbolique.

## Table des Matières

1. [Introduction](#introduction)
2. [Structure des Tests d'Intégration](#structure-des-tests-dintégration)
3. [Modules Prioritaires](#modules-prioritaires)
4. [Approche de Test](#approche-de-test)
5. [Fixtures et Utilitaires](#fixtures-et-utilitaires)
6. [Exécution des Tests](#exécution-des-tests)
7. [Bonnes Pratiques](#bonnes-pratiques)
8. [Exemples](#exemples)

## Introduction

Les tests d'intégration vérifient que les différents modules du système fonctionnent correctement ensemble. Ils sont essentiels pour s'assurer que les interactions entre les composants sont correctes et que le système dans son ensemble fonctionne comme prévu.

### Objectifs des Tests d'Intégration

- Vérifier l'interaction entre les modules prioritaires
- Tester les flux de données entre les différents niveaux hiérarchiques
- Vérifier la communication entre les agents et les outils d'analyse
- Détecter les problèmes d'intégration qui ne sont pas visibles dans les tests unitaires

## Structure des Tests d'Intégration

Les tests d'intégration sont organisés dans le répertoire `tests/integration/`. Chaque fichier de test se concentre sur l'intégration entre des modules spécifiques.

```
tests/integration/
├── __init__.py
├── test_tactical_operational_integration.py    # Intégration entre les niveaux tactique et opérationnel
├── test_agents_tools_integration.py            # Intégration entre les agents et les outils d'analyse
├── test_informal_analysis_integration.py       # Intégration entre les agents informels et les outils d'analyse
```

## Modules Prioritaires

Les modules prioritaires pour les tests d'intégration sont :

1. **orchestration.hierarchical.tactical** (11.78%)
2. **orchestration.hierarchical.operational.adapters** (12.44%)
3. **agents.tools.analysis.enhanced** (12.90%)
4. **agents.core.informal** (16.23%)
5. **agents.tools.analysis** (16.46%)

## Approche de Test

### Approche de Résolution des Dépendances

L'approche recommandée est de résoudre les problèmes de dépendances (numpy, pandas, jpype) en utilisant des versions spécifiques connues pour être compatibles avec notre environnement de test.

```bash
# Windows (PowerShell)
.\scripts\setup\fix_dependencies.ps1

# Linux/macOS
python scripts/setup/fix_dependencies.py
```

### Approche avec Mocks

Dans certains cas, il peut être nécessaire d'utiliser des mocks pour les dépendances problématiques. Utilisez les mocks fournis dans le répertoire `tests/mocks/` et les utilitaires dans `tests/utils/test_helpers.py`.

```python
from tests.utils.test_helpers import mocked_dependencies

def test_with_mocked_dependencies():
    with mocked_dependencies():
        # Code utilisant les dépendances mockées
        result = my_function()
        assert result is not None
```

### Patterns de Test d'Intégration

#### 1. Intégration Tactique-Opérationnel

Ce pattern teste l'interaction entre les composants tactiques (coordinateur, moniteur, résolveur) et les adaptateurs opérationnels.

```python
def test_tactical_operational_integration():
    # Créer les composants tactiques
    tactical_state = TacticalState()
    coordinator = TaskCoordinator(tactical_state=tactical_state, middleware=middleware)
    
    # Créer les adaptateurs opérationnels
    extract_adapter = ExtractAgentAdapter(agent_id="extract_agent", middleware=middleware)
    
    # Tester l'interaction
    task = {...}  # Définir une tâche
    coordinator.assign_task(task, "extract_agent")
    
    # Vérifier que l'adaptateur a reçu la tâche
    assert extract_adapter.has_pending_task(task["id"])
```

#### 2. Intégration Agents-Outils

Ce pattern teste l'interaction entre les agents et leurs outils d'analyse.

```python
def test_agent_tools_integration():
    # Créer les outils d'analyse
    complex_analyzer = ComplexFallacyAnalyzer()
    
    # Créer l'agent avec les outils
    agent = InformalAgent(
        agent_id="informal_agent",
        tools={"complex_analyzer": complex_analyzer}
    )
    
    # Tester l'interaction
    text = "Exemple de texte avec sophismes"
    result = agent.analyze_text(text)
    
    # Vérifier le résultat
    assert "fallacies" in result
```

#### 3. Intégration Informel-Analyse

Ce pattern teste l'interaction entre les agents informels et les différents types d'analyse.

```python
def test_informal_analysis_integration():
    # Créer les définitions de sophismes
    fallacy_definitions = [...]  # Définir des sophismes
    
    # Créer le détecteur de sophismes
    fallacy_detector = FallacyDetector(fallacy_definitions=fallacy_definitions)
    
    # Créer l'agent informel
    agent = InformalAgent(
        agent_id="informal_agent",
        tools={"fallacy_detector": fallacy_detector}
    )
    
    # Tester l'interaction
    text = "Exemple de texte avec sophismes"
    result = agent.analyze_text(text)
    
    # Vérifier le résultat
    assert "fallacies" in result
```

## Fixtures et Utilitaires

### Fixtures pour les Tests d'Intégration

Les fixtures réutilisables pour les tests d'intégration sont définies dans le répertoire `tests/fixtures/`.

```python
import pytest
from tests.fixtures.rhetorical_data_fixtures import example_text, example_fallacies
from tests.fixtures.agent_fixtures import informal_agent, complex_fallacy_analyzer

def test_agent_analyzer_integration(informal_agent, complex_fallacy_analyzer, example_text):
    # Configurer l'agent avec l'analyseur
    informal_agent.tools["complex_analyzer"] = complex_fallacy_analyzer
    
    # Tester l'interaction
    result = informal_agent.analyze_text(example_text)
    
    # Vérifier le résultat
    assert "fallacies" in result
```

### Utilitaires pour les Tests d'Intégration

Les utilitaires pour les tests d'intégration sont définis dans le répertoire `tests/utils/`.

```python
from tests.utils.test_helpers import temp_file, read_json_file
from tests.utils.test_data_generators import generate_text_with_fallacies

def test_file_processing_integration():
    # Générer un texte avec sophismes
    text = generate_text_with_fallacies()
    
    # Créer un fichier temporaire
    with temp_file(text) as file_path:
        # Tester l'intégration
        result = process_and_analyze_file(file_path)
        
        # Vérifier le résultat
        assert "fallacies" in result
```

## Exécution des Tests

### Exécuter Tous les Tests d'Intégration

```bash
pytest tests/integration/
```

### Exécuter un Test d'Intégration Spécifique

```bash
pytest tests/integration/test_tactical_operational_integration.py
```

### Exécuter avec Couverture de Code

```bash
pytest --cov=argumentation_analysis.orchestration.hierarchical tests/integration/
```

### Exécuter avec Verbosité

```bash
pytest -v tests/integration/
```

## Bonnes Pratiques

1. **Isolation des Tests** : Chaque test doit être indépendant des autres tests.
2. **Nettoyage des Ressources** : Assurez-vous de nettoyer les ressources après chaque test.
3. **Tests Progressifs** : Commencez par tester l'intégration de petits modules, puis progressez vers des intégrations plus complexes.
4. **Vérification des Interfaces** : Vérifiez que les interfaces entre les modules sont correctement utilisées.
5. **Gestion des Erreurs** : Testez la gestion des erreurs entre les modules.

Pour plus de détails sur les bonnes pratiques, consultez le fichier [BEST_PRACTICES.md](BEST_PRACTICES.md).

## Exemples

### Exemple 1 : Intégration Tactique-Opérationnel

```python
def test_task_assignment_and_execution():
    """
    Teste l'assignation d'une tâche par le coordinateur tactique
    et son exécution par un agent opérationnel via l'adaptateur.
    """
    # Créer un état tactique
    tactical_state = TacticalState()
    
    # Créer un middleware
    middleware = MessageMiddleware()
    
    # Créer le coordinateur tactique
    coordinator = TaskCoordinator(tactical_state=tactical_state, middleware=middleware)
    
    # Créer un adaptateur d'agent d'extraction
    extract_adapter = ExtractAgentAdapter(agent_id="extract_agent", middleware=middleware)
    
    # Créer une tâche d'extraction
    task = {
        "id": "extract-task-1",
        "description": "Extraire le texte du document",
        "objective_id": "test-objective",
        "estimated_duration": 3600,
        "required_capabilities": ["text_extraction"],
        "parameters": {
            "document_path": "examples/exemple_sophisme.txt",
            "output_format": "text"
        }
    }
    
    # Ajouter la tâche à l'état tactique
    tactical_state.add_task(task)
    
    # Assigner la tâche
    coordinator._assign_pending_tasks()
    
    # Vérifier que la tâche a été assignée
    assert tactical_state.get_task_status(task["id"]) == "assigned"
    
    # Simuler l'exécution de la tâche par l'adaptateur
    extract_result = {
        "text": "Texte extrait du document",
        "metadata": {
            "source": "examples/exemple_sophisme.txt",
            "extraction_time": "2025-05-21T23:30:00"
        }
    }
    
    # Envoyer le résultat
    extract_adapter.send_task_result(task["id"], extract_result, "completed")
    
    # Vérifier que la tâche a été complétée
    assert tactical_state.get_task_status(task["id"]) == "completed"
```

### Exemple 2 : Intégration Agents-Outils

```python
def test_fallacy_detection_and_evaluation():
    """
    Teste la détection et l'évaluation des sophismes par l'agent informel
    en utilisant les outils d'analyse.
    """
    # Créer les outils d'analyse
    complex_analyzer = ComplexFallacyAnalyzer()
    contextual_analyzer = ContextualFallacyAnalyzer()
    severity_evaluator = FallacySeverityEvaluator()
    
    # Créer l'agent informel avec les outils d'analyse
    informal_agent = InformalAgent(
        agent_id="informal_agent_test",
        tools={
            "complex_analyzer": complex_analyzer,
            "contextual_analyzer": contextual_analyzer,
            "severity_evaluator": severity_evaluator
        }
    )
    
    # Texte d'exemple
    text = """
    Le réchauffement climatique est un mythe car il a neigé cet hiver.
    Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
    """
    
    # Exécuter l'analyse
    result = informal_agent.perform_enhanced_analysis(text)
    
    # Vérifier le résultat
    assert "fallacies" in result
    assert "context_analysis" in result
    assert "severity_evaluation" in result
```

### Exemple 3 : Intégration Informel-Analyse

```python
def test_fallacy_categorization():
    """
    Teste la catégorisation des sophismes détectés selon les définitions.
    """
    # Créer les définitions de sophismes
    fallacy_definitions = [
        FallacyDefinition(
            name="généralisation_hâtive",
            category=FallacyCategory.INDUCTION,
            description="Généralise à partir d'un échantillon insuffisant",
            examples=["Il a neigé, donc le réchauffement climatique est un mythe"],
            detection_patterns=["neigé", "froid", "hiver"]
        ),
        FallacyDefinition(
            name="faux_dilemme",
            category=FallacyCategory.STRUCTURE,
            description="Présente seulement deux options alors qu'il en existe d'autres",
            examples=["Soit nous augmentons les impôts, soit l'économie s'effondrera"],
            detection_patterns=["soit...soit", "ou bien...ou bien"]
        )
    ]
    
    # Créer le détecteur de sophismes
    fallacy_detector = FallacyDetector(fallacy_definitions=fallacy_definitions)
    
    # Créer l'agent informel
    informal_agent = InformalAgent(
        agent_id="informal_agent_test",
        tools={"fallacy_detector": fallacy_detector}
    )
    
    # Texte d'exemple
    text = """
    Le réchauffement climatique est un mythe car il a neigé cet hiver.
    Soit nous augmentons les impôts, soit l'économie s'effondrera.
    """
    
    # Exécuter l'analyse et la catégorisation
    result = informal_agent.analyze_and_categorize(text)
    
    # Vérifier le résultat
    assert "fallacies" in result
    assert "categories" in result
    assert FallacyCategory.INDUCTION.name in result["categories"]
    assert FallacyCategory.STRUCTURE.name in result["categories"]
    assert "généralisation_hâtive" in result["categories"][FallacyCategory.INDUCTION.name]
    assert "faux_dilemme" in result["categories"][FallacyCategory.STRUCTURE.name]