# Integration Plan: Service LLM Local (2.3.6)

## 1. Sujet (resume spec professeur)

**Objectif pedagogique** : Integrer des LLMs legers locaux (0.6B-32B params, formats GGUF/ONNX) pour l'analyse argumentative, en complement des APIs cloud.

**Fonctionnalites demandees** :
- Serveur LLM local via llama-cpp-python avec API OpenAI-compatible
- Support multi-modeles (TinyLlama 1.1B → Qwen3 14B)
- 4 cas d'usage : detection de sophismes, evaluation de coherence, classification rhetorique, traduction en logique formelle
- Evaluation comparative des modeles (benchmarks)

**Etudiants** : amine.el-maalouf, aziz.zeghal, lucas.tilly, matthias.laithier, oscar.le-dauphin

## 2. Travail Etudiant (analyse code)

### Structure (`2.3.6_local_llm/`, ~450 LoC)

| Fichier | LoC | Description |
|---------|-----|-------------|
| `local_llm/local_llm.py` | 69 | Wrapper `LocalLlm` autour de `llama_cpp.Llama` |
| `local_llm/constants.py` | 47 | Enum de 9 modeles (TinyLlama → Qwen3 14B) |
| `local_llm/utils.py` | 137 | Prompt engineering + extraction JSON |
| `app.py` | 124 | FastAPI endpoint `/v1/fallacy-detection` |
| `benchmarks.csv` | — | Donnees de performance |

### Points forts
- Support multi-modeles avec enum clean (9 modeles)
- API FastAPI OpenAI-compatible
- Prompt engineering specialise pour la detection de sophismes
- Benchmarks comparatifs

### Limitations
- Charge TOUS les modeles au demarrage (gourmand en memoire)
- Appels synchrones (pas d'async)
- Prompt hardcode pour detection de sophismes uniquement

## 3. Etat Actuel dans le Tronc Commun

### Fichier existant

`argumentation_analysis/services/local_llm_service.py` (112 LoC)

### Ce qui fonctionne

- **`LocalLLMService`** : adaptateur async propre vers n'importe quel endpoint OpenAI-compatible
- `chat_completion(messages, model, max_tokens, temperature)` via httpx POST
- `is_available()` avec health check cache
- Configuration via constructeur OU env vars (`WHISPER_API_URL` etc.)
- Degradation gracieuse si httpx absent ou endpoint injoignable

### Ecarts architecturaux

1. **N'est PAS un service SK** (`ChatCompletionClientBase`) — adaptateur HTTP standalone
2. **Pas d'enregistrement `ServiceDiscovery`** effectif (mentionne en commentaire)
3. **Pas de wiring** dans le kernel par defaut

## 4. Plan de Consolidation

### 4.1 Classification : Service SK

Ce n'est pas un agent ni un plugin — c'est un **fournisseur LLM alternatif** qui devrait etre utilisable de facon transparente par le kernel SK.

### 4.2 Architecture cible

```
services/
└── local_llm_service.py   # ADAPTER — ajouter registration ServiceDiscovery
```

### 4.3 Ce qu'on garde

**Tel quel** :
- `LocalLLMService` — l'adaptateur HTTP est correct et bien concu
- API OpenAI-compatible (decouple du code etudiant llama-cpp)
- Degradation gracieuse

### 4.4 Ce qu'on adapte

1. **ServiceDiscovery registration** : implementer l'enregistrement effectif
2. **SK integration** : option pragmatique — enregistrer comme provider dans ServiceDiscovery pour que les agents puissent l'utiliser via `get_best_provider("llm")`
3. **Alternative full SK** : implementer `ChatCompletionClientBase` (plus lourd, necessaire uniquement si on veut `kernel.add_service()`)

### 4.5 Decision

**Approche pragmatique** : garder le service tel quel + l'enregistrer dans `ServiceDiscovery`. L'implementation full SK (`ChatCompletionClientBase`) est hors scope — elle necessite d'implementer 5+ methodes abstraites pour un gain marginal.

## 5. Cablage Architecture

### 5.1 ServiceDiscovery

```python
from argumentation_analysis.core.capability_registry import ServiceDiscovery
discovery = ServiceDiscovery()
discovery.register_provider(
    name="local_llm", category="llm",
    factory=lambda: LocalLLMService(),
    priority=2  # Fallback apres OpenAI cloud
)
```

### 5.2 CapabilityRegistry

```python
registry.register_service(
    name="LocalLLMService",
    service_class=LocalLLMService,
    capabilities=["llm_chat_completion", "local_inference"],
)
```

## 6. Criteres d'Acceptation

- [ ] Enregistre dans `ServiceDiscovery` comme provider LLM
- [ ] Enregistre dans `CapabilityRegistry` (type SERVICE)
- [ ] `is_available()` fonctionne pour detecter l'endpoint
- [ ] Les agents peuvent le trouver via `get_best_provider("llm")`
- [ ] Degradation gracieuse si endpoint down
- [ ] Tests existants preserves
- [ ] Zero regression

## 7. Notes

### Effort estime : ~30min

Le code est deja bien structure. Il manque uniquement le cablage ServiceDiscovery/CapabilityRegistry.

### Relation avec l'infrastructure

La machine `myia-ai-01` expose deja des endpoints vLLM locaux (ports 5001, 5002). Le `LocalLLMService` est configure par defaut sur `http://localhost:5001/v1`, ce qui correspond a l'infra existante.
