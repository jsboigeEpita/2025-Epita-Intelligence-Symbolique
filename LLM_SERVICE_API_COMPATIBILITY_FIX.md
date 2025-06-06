# Correction de l'incompatibilité de l'interface API du service LLM

## Problème identifié
- **Erreur** : `KeyError: 'api_key'` dans les tests unitaires
- **Cause** : Décalage entre l'implémentation du service LLM et les assertions des tests
- **Impact** : 15% des échecs de tests (environ 31 tests selon l'analyse debug)

## Interface OpenAIChatCompletion
L'interface `semantic_kernel.connectors.ai.open_ai.OpenAIChatCompletion` supporte deux modes d'initialisation :

### Ancienne interface (compatible)
```python
OpenAIChatCompletion(
    service_id="global_llm_service",
    ai_model_id="gpt-4o-mini", 
    api_key="sk-...",
    org_id=None
)
```

### Nouvelle interface (recommandée)
```python
openai_client = AsyncOpenAI(api_key="sk-...", organization=org_id)
OpenAIChatCompletion(
    service_id="global_llm_service",
    ai_model_id="gpt-4o-mini",
    async_client=openai_client
)
```

## Implémentation actuelle 
Le service LLM (`argumentation_analysis/core/llm_service.py`) utilise la **nouvelle interface** avec `async_client` pour permettre :
- Logging HTTP personnalisé via `LoggingHttpTransport`
- Gestion avancée des requêtes et réponses
- Surveillance détaillée des appels API

## Corrections apportées

### Tests mis à jour (`tests/unit/argumentation_analysis/test_llm_service.py`)

#### Avant (tests échouaient)
```python
# Tests vérifiaient l'ancienne interface
mock_openai_class.assert_called_once_with(
    service_id="global_llm_service",
    ai_model_id="gpt-4o-mini",
    api_key=self.api_key,
    org_id=None
)
```

#### Après (tests corrigés)
```python
# Tests vérifient la nouvelle interface
args, kwargs = mock_openai_class.call_args
self.assertEqual(kwargs["service_id"], "global_llm_service")
self.assertEqual(kwargs["ai_model_id"], "gpt-4o-mini")

# Vérifier que async_client est fourni (nouvelle interface)
self.assertIn("async_client", kwargs)
self.assertIsNotNone(kwargs["async_client"])

# Vérifier que api_key et org_id ne sont PAS fournis (ils sont dans async_client)
self.assertNotIn("api_key", kwargs)
self.assertNotIn("org_id", kwargs)
```

## Résultats
- ✅ **5/5 tests LLM passent** (auparavant 3/5)
- ✅ Interface cohérente avec l'implémentation actuelle
- ✅ Logging HTTP personnalisé conservé
- ✅ Compatibilité avec semantic_kernel maintenue

## Tests corrigés
1. `test_create_llm_service_openai` - Vérifie la création du service avec nouvelle interface
2. `test_create_llm_service_custom_model` - Vérifie la création avec modèle personnalisé

## Impact sur le codebase
- **Aucun changement** dans l'implémentation du service LLM
- **Tests alignés** avec l'interface utilisée réellement
- **Fonctionnalité préservée** : logging HTTP, gestion des erreurs, etc.

## Recommandations
1. Maintenir la nouvelle interface `async_client` pour les nouveaux développements
2. Utiliser l'ancienne interface `api_key` uniquement si le logging HTTP n'est pas nécessaire
3. Documenter l'interface utilisée dans les nouveaux modules utilisant le service LLM