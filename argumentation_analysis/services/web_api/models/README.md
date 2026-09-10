# web_api/models/ — contrats Pydantic requête/réponse des services web_api

## Rôle et frontière

Contrats Pydantic V2 (validation d'entrée, sérialisation de sortie) de l'API
Flask historique — toujours la couche validation/sérialisation des services
métier [../services/](../services/) et des outils MCP v1. La couche HTTP
d'origine est archivée (#217, `../__init__.py:4-13`).

La frontière exclut : les contrats de l'API FastAPI moderne (`api/models.py`,
qui définit son **propre** `FrameworkAnalysisRequest` — cf. limites), la
logique métier (frère `../services/`), la couche Flask (archive
`docs/archives/services_web_api_flask/`).

## Composants publics

**`request_models.py`** (validation métier par `@field_validator`) :

| Groupe | Modèles | Lignes |
|---|---|---|
| Analyse | `AnalysisOptions`, `AnalysisRequest` | :19, :35 |
| Validation | `ValidationRequest` | :51 |
| Sophismes | `FallacyOptions`, `FallacyRequest` | :88, :112 |
| Framework Dung | `Argument` (unicité IDs + références attacks/supports :190-210), `FrameworkOptions`, `FrameworkRequest`, `FrameworkAnalysisRequest` | :128, :155, :180, :339 |
| Logique | `LogicOptions`, `LogicBeliefSetRequest`, `LogicQueryRequest`, `LogicGenerateQueriesRequest` | :216, :230, :259, :298 |

**`response_models.py`** : `AnalysisResponse` (:48), `ValidationResponse`
(:108), `FallacyResponse` (:130), `FrameworkResponse` (:199),
`LogicQueryResult` (:261, tri-état `Optional[bool]` :265),
`LogicQueryResponse` (:308), `LogicGenerateQueriesResponse` (:330),
`LogicInterpretationResponse` (:352), `ErrorResponse` (:244),
`SuccessResponse` (:380) et leurs sous-structures. `__init__.py:8-21`
ré-exporte 9 noms.

## Points d'entrée valides

Module importé, jamais exécuté. Importateurs production : 4 services sur 5 —
`analysis_service.py:67,70`, `validation_service.py:14,17`,
`logic_service.py:31,38`, `fallacy_service.py:35-36` (imports relatifs
`..models`) ; **pas** `framework_service.py` (surface dict brut). Plus le
serveur MCP v1 (`../../mcp_server/main.py:42-59,387`). L'API FastAPI
`api/` n'importe rien d'ici.

## Amont / aval

- **Amont** : Pydantic V2 uniquement.
- **Aval** : [../services/](../services/) → outils MCP v1 → clients MCP ;
  anciennement routes Flask (archive
  `docs/archives/services_web_api_flask/routes/*.py:9-13`) ;
  `tests/integration/workers/worker_logic_api.py:36-41`.

## Statut d'intégration

| Famille | Statut | Preuve |
|---|---|---|
| Analyse / Sophismes / Validation / Logique (req + resp) | **actif** | consommés par les 4 services + MCP v1 (main.py:42-52) ; dans le gate CI (`tests/unit/services/web_api/`, `tests/unit/argumentation_analysis/services/`) |
| `Argument` | **actif** | seul survivant framework côté production (outil MCP `build_framework`, main.py:387-404) |
| `FrameworkRequest` / `FrameworkOptions` | **compatibilité** (test-only) | plus aucun consommateur production depuis #1864 — bypass documenté main.py:404-414 (`build_framework(FrameworkRequest)` était une « interface fantôme ») ; tests `test_web_api_models_and_services.py:252-322` |
| `FrameworkResponse` | **résiduel** | importé jamais utilisé (main.py:57) |
| `FrameworkAnalysisRequest` (web_api) | **résiduel** | test-only (:325) ; la route vivante utilise l'homonyme `api/models.py:48` |
| `LogicInterpretationResponse` | **résiduel** | unique consommateur `logic_service.interpret_results` (logic_service.py:312,371), lui-même sans appelant production |
| `SuccessResponse` / `ErrorResponse` | **résiduel** | consommateurs uniquement archives (`framework_routes.py:13,43`) et tests |

## Artefacts et lecteurs

Instances Pydantic → `result.model_dump()` dans les réponses d'outils MCP
(main.py:256,292,353,501,543,585). Lecteurs : clients MCP, suites de tests.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/unit/argumentation_analysis/services/web_api/models/ \
  tests/unit/argumentation_analysis/services/test_web_api_models_and_services.py \
  tests/unit/services/web_api/ -v
```

(47 tests directs `test_response_models.py`, 113 dans
`test_web_api_models_and_services.py`, 24 relocalisés #1859.)

## Frères et parent

- Parent : [web_api/](../) — README parent : [../README.md](../README.md)
  (**périmé**).
- Frère : [../services/](../services/README.md) (le consommateur principal).

## Limites connues

- Collision de noms `FrameworkAnalysisRequest` : deux contrats distincts
  portent le même nom (`request_models.py:339` vs `api/models.py:48`,
  consommé par `api/endpoints.py:90`) — ambiguïté à l'import.
- Chaîne morte documentée : `logic_service.interpret_results`
  (logic_service.py:312) + `LogicInterpretationResponse` — méthode publique
  sans aucun appelant production (ni outil MCP ni route).
- Imports morts dans `request_models.py:8-16` (`Dict`, `Any`, `validator` V1,
  `ExtractDefinitions`) — tolérés par `.flake8` (F401 ignoré), donc invisibles
  au lint.
- `main.py:53-59` importe 5 modèles de réponse jamais référencés (contrat
  documentaire implicite).
