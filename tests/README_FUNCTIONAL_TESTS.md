# Tests Fonctionnels pour le Projet d'Intelligence Symbolique

Ce document explique comment écrire, exécuter et maintenir les tests fonctionnels pour le projet d'Intelligence Symbolique.

## Table des Matières

1. [Introduction](#introduction)
2. [Structure des Tests Fonctionnels](#structure-des-tests-fonctionnels)
3. [Flux de Travail Critiques](#flux-de-travail-critiques)
4. [Approche de Test](#approche-de-test)
5. [Fixtures et Utilitaires](#fixtures-et-utilitaires)
6. [Exécution des Tests](#exécution-des-tests)
7. [Bonnes Pratiques](#bonnes-pratiques)
8. [Exemples](#exemples)

## Introduction

Les tests fonctionnels vérifient que le système répond aux exigences fonctionnelles et se comporte comme prévu du point de vue de l'utilisateur. Ils testent des flux de travail complets et des scénarios d'utilisation réels.

### Objectifs des Tests Fonctionnels

- Vérifier que les flux de travail critiques fonctionnent correctement de bout en bout
- Tester le comportement du système face à différents types de textes
- Valider que les résultats d'analyse sont conformes aux attentes
- Détecter les problèmes qui ne sont pas visibles dans les tests unitaires ou d'intégration

## Structure des Tests Fonctionnels

Les tests fonctionnels sont organisés dans le répertoire `tests/functional/`. Chaque fichier de test se concentre sur un flux de travail spécifique.

```
tests/functional/
├── __init__.py
├── test_rhetorical_analysis_workflow.py    # Flux de travail d'analyse rhétorique
├── test_fallacy_detection_workflow.py      # Flux de travail de détection des sophismes
├── test_agent_collaboration_workflow.py    # Flux de travail de collaboration entre agents
```

## Flux de Travail Critiques

Les flux de travail critiques pour les tests fonctionnels sont :

1. **Analyse Rhétorique** : Extraction du texte, analyse rhétorique, génération de rapport
2. **Détection des Sophismes** : Extraction du texte, détection des sophismes, analyse contextuelle, évaluation de la sévérité
3. **Collaboration entre Agents** : Coordination tactique, assignation des tâches, exécution des tâches, résolution des conflits

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

### Patterns de Test Fonctionnel

#### 1. Pattern de Flux de Travail Complet

Ce pattern teste un flux de travail complet de bout en bout.

```python
def test_complete_workflow():
    # Configurer l'environnement
    setup_environment()
    
    # Étape 1 : Extraction du texte
    text = extract_text_from_file("examples/exemple_sophisme.txt")
    
    # Étape 2 : Analyse des sophismes
    analysis_result = analyze_fallacies(text)
    
    # Étape 3 : Génération du rapport
    report = generate_report(analysis_result)
    
    # Vérifier le résultat final
    assert "fallacies" in analysis_result
    assert len(analysis_result["fallacies"]) > 0
    assert report is not None
    
    # Nettoyer l'environnement
    cleanup_environment()
```

#### 2. Pattern de Scénario d'Utilisation

Ce pattern teste un scénario d'utilisation spécifique.

```python
def test_user_scenario():
    # Configurer le scénario
    setup_scenario()
    
    # Simuler les actions de l'utilisateur
    user_input = "Analyser le texte pour identifier les sophismes"
    objective = create_objective_from_input(user_input)
    tasks = decompose_objective_to_tasks(objective)
    results = execute_tasks(tasks)
    report = generate_report_from_results(results)
    
    # Vérifier le résultat
    assert report is not None
    assert "fallacies" in report
    
    # Nettoyer le scénario
    cleanup_scenario()
```

#### 3. Pattern de Test avec Données Réelles

Ce pattern teste le système avec des données réelles.

```python
def test_with_real_data():
    # Charger des données réelles
    real_texts = load_real_texts()
    
    # Analyser chaque texte
    results = []
    for text in real_texts:
        result = analyze_text(text)
        results.append(result)
    
    # Vérifier les résultats
    for result in results:
        assert "fallacies" in result
        assert len(result["fallacies"]) > 0
```

## Fixtures et Utilitaires

### Fixtures pour les Tests Fonctionnels

Les fixtures réutilisables pour les tests fonctionnels sont définies dans le répertoire `tests/fixtures/`.

```python
import pytest
from tests.fixtures.rhetorical_data_fixtures import example_text_file, example_corpus_files
from tests.fixtures.agent_fixtures import real_extract_agent_adapter, real_informal_agent_adapter

def test_rhetorical_analysis_workflow(example_text_file, real_extract_agent_adapter, real_informal_agent_adapter):
    # Extraire le texte
    text = real_extract_agent_adapter.extract_text_from_file(example_text_file)
    
    # Analyser le texte
    analysis_result = real_informal_agent_adapter.analyze_text(text)
    
    # Vérifier le résultat
    assert "fallacies" in analysis_result
```

### Utilitaires pour les Tests Fonctionnels

Les utilitaires pour les tests fonctionnels sont définis dans le répertoire `tests/utils/`.

```python
from tests.utils.test_helpers import temp_directory, write_json_file
from tests.utils.test_data_generators import generate_enhanced_analysis_result

def test_report_generation():
    # Générer un résultat d'analyse
    analysis_result = generate_enhanced_analysis_result()
    
    # Créer un répertoire temporaire pour les résultats
    with temp_directory() as temp_dir:
        # Sauvegarder le résultat
        result_file = os.path.join(temp_dir, "analysis_result.json")
        write_json_file(analysis_result, result_file)
        
        # Générer le rapport
        report_file = generate_report(result_file, temp_dir)
        
        # Vérifier que le rapport a été généré
        assert os.path.exists(report_file)
```

## Exécution des Tests

### Exécuter Tous les Tests Fonctionnels

```bash
pytest tests/functional/
```

### Exécuter un Test Fonctionnel Spécifique

```bash
pytest tests/functional/test_rhetorical_analysis_workflow.py
```

### Exécuter avec Couverture de Code

```bash
pytest --cov=argumentation_analysis tests/functional/
```

### Exécuter avec Verbosité

```bash
pytest -v tests/functional/
```

## Bonnes Pratiques

1. **Tests de Bout en Bout** : Testez le système de bout en bout, du point de vue de l'utilisateur.
2. **Scénarios Réalistes** : Utilisez des scénarios réalistes pour les tests.
3. **Données Réalistes** : Utilisez des données réalistes pour les tests.
4. **Isolation des Tests** : Chaque test doit être indépendant des autres tests.
5. **Nettoyage des Ressources** : Assurez-vous de nettoyer les ressources après chaque test.

Pour plus de détails sur les bonnes pratiques, consultez le fichier [BEST_PRACTICES.md](BEST_PRACTICES.md).

## Exemples

### Exemple 1 : Flux de Travail d'Analyse Rhétorique

```python
def test_complete_rhetorical_analysis_workflow():
    """
    Teste le flux de travail complet d'analyse rhétorique,
    de l'extraction du texte à la génération du rapport d'analyse.
    """
    # Chemin du fichier d'exemple
    example_file = "examples/exemple_sophisme.txt"
    
    # Vérifier que le fichier existe
    assert os.path.exists(example_file), f"Le fichier d'exemple {example_file} n'existe pas"
    
    # Créer un middleware
    middleware = MessageMiddleware()
    
    # Créer l'adaptateur d'extraction
    extract_adapter = ExtractAgentAdapter(agent_id="extract_agent", middleware=middleware)
    
    # Créer l'agent informel
    informal_agent = InformalAgent(
        agent_id="informal_agent",
        tools={"complex_analyzer": ComplexFallacyAnalyzer()}
    )
    
    # Créer le runner d'analyse rhétorique
    analysis_runner = RhetoricalAnalysisRunner(middleware=middleware)
    
    # Exécuter le flux de travail d'analyse rhétorique
    result_file = analysis_runner.run_analysis(
        input_file=example_file,
        output_dir="results/test",
        agent_type="informal",
        analysis_type="fallacy"
    )
    
    # Vérifier le résultat
    assert result_file is not None
    assert os.path.exists(result_file)
    
    # Lire le résultat
    with open(result_file, 'r', encoding='utf-8') as f:
        result = json.load(f)
    
    # Vérifier le contenu du résultat
    assert "fallacies" in result
    assert len(result["fallacies"]) > 0
```

### Exemple 2 : Flux de Travail de Détection des Sophismes

```python
def test_fallacy_detection_workflow():
    """
    Teste le flux de travail complet de détection des sophismes.
    """
    # Texte d'exemple
    text = """
    Le réchauffement climatique est un mythe car il a neigé cet hiver.
    Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
    Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
    """
    
    # Créer les outils d'analyse
    complex_analyzer = ComplexFallacyAnalyzer()
    contextual_analyzer = ContextualFallacyAnalyzer()
    severity_evaluator = FallacySeverityEvaluator()
    
    # 1. Détecter les sophismes
    fallacies = complex_analyzer.analyze(text)
    
    # Vérifier les sophismes détectés
    assert len(fallacies) > 0
    
    # 2. Analyser le contexte
    context_analysis = contextual_analyzer.analyze_context(fallacies)
    
    # Vérifier l'analyse contextuelle
    assert len(context_analysis) > 0
    
    # 3. Évaluer la sévérité
    severity_evaluation = severity_evaluator.evaluate_severity(fallacies, context_analysis)
    
    # Vérifier l'évaluation de la sévérité
    assert len(severity_evaluation) > 0
    
    # 4. Générer le résultat final
    result = {
        "fallacies": fallacies,
        "context_analysis": context_analysis,
        "severity_evaluation": severity_evaluation,
        "metadata": {
            "timestamp": "2025-05-21T23:30:00",
            "agent_id": "test_agent"
        }
    }
    
    # Vérifier le résultat final
    assert "fallacies" in result
    assert "context_analysis" in result
    assert "severity_evaluation" in result
```

### Exemple 3 : Flux de Travail de Collaboration entre Agents

```python
def test_collaborative_analysis_workflow():
    """
    Teste le flux de travail complet de collaboration entre agents
    pour l'analyse rhétorique et la détection des sophismes.
    """
    # Créer un état tactique
    tactical_state = TacticalState()
    
    # Créer un middleware
    middleware = MessageMiddleware()
    
    # Créer le coordinateur tactique
    coordinator = TaskCoordinator(tactical_state=tactical_state, middleware=middleware)
    
    # Créer l'adaptateur d'extraction
    extract_adapter = ExtractAgentAdapter(agent_id="extract_agent", middleware=middleware)
    
    # Créer l'adaptateur d'agent informel
    informal_adapter = InformalAgentAdapter(agent_id="informal_agent_adapter", middleware=middleware)
    
    # Créer un objectif
    objective = {
        "id": "test-objective",
        "description": "Analyser le texte pour identifier les sophismes",
        "priority": "high",
        "text": "Ceci est un texte d'exemple pour l'analyse des sophismes.",
        "type": "fallacy_analysis"
    }
    
    # Ajouter l'objectif à l'état tactique
    tactical_state.add_assigned_objective(objective)
    
    # Décomposer l'objectif en tâches
    tasks = coordinator._decompose_objective_to_tasks(objective)
    
    # Ajouter les tâches à l'état tactique
    for task in tasks:
        tactical_state.add_task(task)
    
    # Assigner les tâches aux agents
    coordinator._assign_pending_tasks()
    
    # Vérifier que les tâches ont été assignées
    for task in tasks:
        assert tactical_state.get_task_status(task["id"]) == "assigned"
    
    # Simuler l'exécution des tâches
    for task in tasks:
        agent_id = tactical_state.get_task_assignment(task["id"])
        if agent_id == "extract_agent":
            result = {
                "text": "Texte extrait du document",
                "metadata": {
                    "source": "examples/exemple_sophisme.txt",
                    "extraction_time": "2025-05-21T23:30:00"
                }
            }
            extract_adapter.send_task_result(task["id"], result, "completed")
        elif agent_id == "informal_agent":
            result = {
                "fallacies": [
                    {"type": "généralisation_hâtive", "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver", "confidence": 0.92}
                ],
                "analysis_metadata": {
                    "timestamp": "2025-05-21T23:30:00",
                    "agent_id": "informal_agent",
                    "version": "1.0"
                }
            }
            informal_adapter.send_task_result(task["id"], result, "completed")
    
    # Vérifier que toutes les tâches sont complétées
    for task in tasks:
        assert tactical_state.get_task_status(task["id"]) == "completed"