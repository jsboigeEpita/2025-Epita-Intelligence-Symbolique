# web_api/services/ — la couche métier vivante, consommée par le serveur MCP

## Rôle et frontière

Logique métier pure, sans couche HTTP : analyse argumentative complète,
validation heuristique, détection de sophismes, analyse de frameworks Dung,
opérations logiques. Survivante de l'archivage Flask de la couche HTTP
(#217, 2026-03-24 — voir `../__init__.py:4-13`) : ce répertoire et
[../models/](../models/) sont les deux parties vivantes de `web_api`.

Frontière : ce n'est **pas** la couche service de l'API FastAPI moderne —
`api/endpoints.py:26` utilise son propre `DungAnalysisService`
(`api/services.py`). Les consommateurs production sont le serveur MCP
(`../../mcp_server/main.py:27-39`).

## Composants publics

| Service | Fichier | Surface principale |
|---|---|---|
| `AnalysisService` | `analysis_service.py:79` | `analyze_text(request) -> AnalysisResponse` (:251) ; constructeur exige un `llm_service` positionnel (:84) ; s'appuie sur AgentFactory, InformalAnalysisAgent, analyseurs de sophismes, OperationalManager |
| `ValidationService` | `validation_service.py:26` | `validate_argument(request)` (:71) — heuristique prémisses/conclusion (connecteurs français :41-63) ; branche formelle déléguée à LogicService (:94) mais désactivée (cf. limites) |
| `FallacyService` | `fallacy_service.py:41` | détection 3 niveaux : `detect_fallacies` (:316) via analyseur contextuel (:392), analyseur enrichi (:432), motifs regex (:480) ; `get_fallacy_types` (:704), `get_categories` (:724), `is_healthy` (:307) |
| `FrameworkService` | `framework_service.py:14` | `analyze_dung_framework(arguments, attacks)` (:36) via `TweetyBridge.get_instance()` (:27) → `af_handler` (:61-63, sémantique preferred) ; `is_healthy` (:77-88, contrat #1864) |
| `LogicService` | `logic_service.py:48` | Kernel SK + LLM injecté (:57-59), QueryExecutor (:67), belief_sets en mémoire (:69-71) ; `text_to_belief_set` (:89), `execute_query` (:165), `generate_queries` (:242), `interpret_results` (:312), `validate_argument_from_components` (:458) |
| `Fallback*` (5 classes) | `fallback_services.py` | **résiduel** — zéro importeur (seule mention : commentaire `__init__.py:14`) |

`__init__.py:11` déclare `__all__` (4 noms) mais n'importe rien — les
consommateurs importent les modules directement.

## Points d'entrée valides

Import direct des modules (le `__init__` n'exporte rien). Consommateur
production principal : `../../mcp_server/main.py:27-39` importe les 5
services ; conteneur `AppServices` (main.py:67-94), LLM par consommateur via
`create_llm_service` (:80-81, #1864), dict `is_healthy` à 6 clés
(jvm + 5 services, :91-104).
Outils MCP v1 exposant la surface : `analyze_text` (:254), `validate_argument`
(:288), `detect_fallacies` (:349), `analyze_dung_framework` (:422),
`execute_query` (:542), `generate_queries` (:584).

## Amont / aval

- **Amont** : [../models/](../models/) (contrats requête/réponse, importés par
  4 services sur 5 — pas `framework_service.py`, surface dict brut),
  `agents/` et `orchestration/` (via AnalysisService),
  `core/logic/tweety_bridge` (FrameworkService).
- **Aval** : serveur MCP v1 (outils ci-dessus) ;
  `tests/integration/workers/worker_logic_api.py:35` ;
  `scripts/validation/test_web_api_direct.py:107` ;
  `core/argumentation_analyzer.py:18` (cassé — cf. limites).

## Statut d'intégration

| Famille | Statut | Preuve |
|---|---|---|
| `AnalysisService` | **actif** | monté dans `AppServices` (mcp main.py:83) + outil MCP `analyze_text` (:254) |
| `ValidationService` | **actif** | monté (main.py:84) + outil `validate_argument` (:288) ; branche formelle désactivée en son sein |
| `FallacyService` | **actif** | monté (main.py:85) + outil `detect_fallacies` (:349) |
| `FrameworkService` | **actif** | monté (main.py:86) + outil `analyze_dung_framework` (:422) ; initialise le vrai TweetyBridge (framework_service.py:27-28) |
| `LogicService` | **actif** | monté (main.py:82) + outils `execute_query` (:542) / `generate_queries` (:584) |
| — sous-surface `text_to_belief_set`/`interpret_results` | **résiduel** | zéro appelant production (leur seule route, archivée `docs/archives/services_web_api_flask/routes/logic_routes.py:66` ; le MCP ne les expose pas) |
| `fallback_services.py` | **résiduel** | zéro importeur repo-wide |

## Artefacts et lecteurs

Instances Pydantic de [../models/](../models/) sérialisées (`model_dump()`)
dans les réponses d'outils MCP (main.py:256,292,353,501,543,585). Seul état :
`LogicService.belief_sets` en mémoire (logic_service.py:71), perdu au
restart. Lecteurs : clients MCP, suites de tests.

## Tests représentatifs

```bash
# gate porteur (24 tests, relocalisés ici par #1859)
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/unit/services/web_api/test_services.py -v

# tests ciblés par service
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/unit/argumentation_analysis/services/web_api/services/ -v

# montage MCP des services
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/unit/argumentation_analysis/services/test_mcp_server.py -v
```

## Frères et parent

- Parent : [web_api/](../) — README parent : [../README.md](../README.md)
  (**périmé** : décrit l'app Flask archivée).
- Frère : [../models/](../models/README.md) (contrats), [../tests/](../tests/README.md)
  (suite hors gate), [../routes/](../routes/README.md) (tombstones).

## Limites connues

- `core/argumentation_analyzer.py:80` instancie `AnalysisService()` **sans**
  le `llm_service` positionnel requis (`analysis_service.py:84`) → TypeError
  avalée par le try/except (:84-88), `analysis_service=None` silencieux en
  mode dégradé.
- Branche formelle de la validation désactivée : la condition
  (`validation_service.py:84-92`) exige `request.logic_type`, champ que
  `ValidationRequest` ne définit plus — ne s'exécute jamais.
- TODO vivant `fallacy_service.py:60` (« EnhancedContextualFallacyAnalyzer is
  currently disabled in some branches »).
- Double surface Dung parallèle vivante : `FrameworkService` → TweetyBridge
  (MCP) vs `api/services.py DungAnalysisService` (FastAPI,
  `api/endpoints.py:26`) — même capacité, deux câblages.
