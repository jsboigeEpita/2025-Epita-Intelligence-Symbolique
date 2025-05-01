# Tests d'intégration pour le projet d'analyse d'argumentation

Ce document explique comment utiliser les mocks et fixtures pour les tests d'intégration du projet d'analyse d'argumentation.

## Introduction

Les tests d'intégration vérifient que les différents composants du système fonctionnent correctement ensemble. Contrairement aux tests unitaires qui testent des composants isolés, les tests d'intégration testent les interactions entre plusieurs composants.

Pour faciliter l'écriture de tests d'intégration, nous avons mis en place des mocks et fixtures réutilisables qui simulent les dépendances externes et fournissent des données de test cohérentes.

## Structure des mocks et fixtures

Les mocks et fixtures sont définis dans le fichier `conftest.py` et sont automatiquement disponibles pour tous les tests pytest. Ils sont organisés en plusieurs catégories:

### Fixtures pour les services

- `mock_cache_service`: Mock pour le service de cache
- `mock_crypto_service`: Mock pour le service de chiffrement
- `mock_definition_service`: Mock pour le service de définition
- `mock_fetch_service`: Mock pour le service de récupération
- `mock_extract_service`: Mock pour le service d'extraction
- `mock_llm_service`: Mock pour le service LLM

### Fixtures pour les données de test

- `integration_sample_source`: Source d'exemple pour les tests d'intégration
- `integration_sample_definitions`: Définitions d'extraits pour les tests d'intégration
- `integration_extract_results`: Résultats d'extraction pour les tests d'intégration

### Fixtures utilitaires

- `temp_dir`: Répertoire temporaire pour les tests

## Utilisation des mocks et fixtures

### Exemple de test d'intégration simple

```python
def test_extract_service_with_fetch_service(mock_fetch_service, integration_sample_definitions):
    """Test d'intégration entre ExtractService et FetchService."""
    # Créer un vrai service d'extraction (pas un mock)
    extract_service = ExtractService()
    
    # Récupérer la source et l'extrait de test
    source = integration_sample_definitions.sources[0]
    extract = source.extracts[0]
    
    # Récupérer le texte source via le service de récupération mocké
    source_text, url = mock_fetch_service.fetch_text(source.to_dict())
    
    # Vérifier que le texte source a été récupéré
    assert source_text is not None
    
    # Extraire le texte avec les marqueurs
    extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
        source_text, extract.start_marker, extract.end_marker
    )
    
    # Vérifier que l'extraction a réussi
    assert start_found is True
    assert end_found is True
    assert "Extraction réussie" in status
```

### Exemple de test d'intégration avec des scripts

```python
def test_verify_extracts_integration(mock_fetch_service, mock_extract_service, integration_sample_definitions, temp_dir):
    """Test d'intégration pour la fonction verify_extracts."""
    # Exécuter la fonction verify_extracts
    results = verify_extracts(
        integration_sample_definitions,
        mock_fetch_service,
        mock_extract_service
    )
    
    # Vérifier les résultats
    assert len(results) == 2
    
    # Générer un rapport
    report_path = temp_dir / "test_report.html"
    generate_report(results, str(report_path))
    
    # Vérifier que le rapport a été généré
    assert report_path.exists()
```

### Exemple de test d'intégration asynchrone

```python
@patch('scripts.repair_extract_markers.setup_agents')
async def test_repair_extract_markers_integration(self, mock_setup_agents, mock_fetch_service, mock_extract_service, 
                                                 mock_llm_service, integration_sample_definitions):
    """Test d'intégration pour la fonction repair_extract_markers."""
    from scripts.repair_extract_markers import repair_extract_markers
    
    # Configurer le mock pour setup_agents
    kernel_mock = mock_llm_service
    repair_agent_mock = mock_llm_service
    validation_agent_mock = mock_llm_service
    mock_setup_agents.return_value = (kernel_mock, repair_agent_mock, validation_agent_mock)
    
    # Exécuter la fonction repair_extract_markers
    updated_definitions, results = await repair_extract_markers(
        integration_sample_definitions,
        mock_llm_service,
        mock_fetch_service,
        mock_extract_service
    )
    
    # Vérifier les résultats
    assert len(results) == 2
```

## Personnalisation des mocks

Les mocks fournis sont configurés avec des comportements par défaut, mais vous pouvez les personnaliser pour des cas de test spécifiques:

```python
def test_custom_mock_behavior(mock_fetch_service):
    # Personnaliser le comportement du mock
    mock_fetch_service.fetch_text.return_value = ("Texte personnalisé", "https://example.com/custom")
    
    # Utiliser le mock personnalisé
    text, url = mock_fetch_service.fetch_text({})
    
    # Vérifier le comportement personnalisé
    assert text == "Texte personnalisé"
    assert url == "https://example.com/custom"
```

## Résolution des problèmes d'imports relatifs

Pour résoudre les problèmes d'imports relatifs, nous avons mis en place une fonction `setup_import_paths()` dans le fichier `__init__.py` du package de tests. Cette fonction ajoute le répertoire parent au chemin de recherche des modules, ce qui permet d'importer les modules du projet sans utiliser d'imports relatifs.

Si vous rencontrez des problèmes d'imports relatifs dans vos tests, assurez-vous que le fichier `__init__.py` est présent dans le répertoire des tests et que la fonction `setup_import_paths()` est appelée au début de vos fichiers de test:

```python
from tests import setup_import_paths
setup_import_paths()

# Maintenant vous pouvez importer les modules du projet sans imports relatifs
from models.extract_definition import ExtractDefinitions
from services.extract_service import ExtractService
```

## Bonnes pratiques

1. **Utilisez les fixtures existantes**: Réutilisez les fixtures existantes autant que possible pour maintenir la cohérence entre les tests.
2. **Isolez les dépendances externes**: Utilisez des mocks pour isoler les dépendances externes comme les requêtes HTTP, le système de fichiers, etc.
3. **Testez les interactions**: Concentrez-vous sur les interactions entre les composants plutôt que sur les détails d'implémentation.
4. **Utilisez des assertions claires**: Écrivez des assertions claires et spécifiques pour faciliter le débogage en cas d'échec.
5. **Documentez vos tests**: Ajoutez des docstrings à vos tests pour expliquer ce qu'ils testent et comment ils le testent.