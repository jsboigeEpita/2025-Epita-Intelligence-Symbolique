# `plugins/semantic_kernel/` — surface SK du JTMS montée par l'API

## Rôle et frontière

Un module : `jtms_plugin.py` (631 lignes) — `JTMSSemanticKernelPlugin` (:36), la surface Semantic Kernel du JTMS. `__init__.py` vide (0 octet) : les consommateurs importent le chemin du module directement. Ce plugin est la seule voie par laquelle les services JTMS deviennent appelables comme fonctions kernel (et donc par un agent).

## Composants publics

5 `@kernel_function` (une par service JTMS) :

- `create_belief` (:124), `add_justification` (:204), `explain_belief` (:294), `query_beliefs` (:373), `get_jtms_state` (:462) ;
- fabrique `create_jtms_plugin` (:612) — injection du service + du session manager.

## Points d'entrée valides

**Routes API dédiées** (montage mesuré) : `api/main.py:104-105` monte `jtms_router` sous `/api/v1` (sous garde `_JTMS_AVAILABLE`, import :31-33) → `argumentation_analysis/api/jtms_endpoints.py` expose les 5 endpoints de commodité `@jtms_router.post("/sk/...")` :787, :812, :839, :862, :885, tous `Depends(get_sk_plugin)` → `create_jtms_plugin` (:93 via :55). Snapshot OpenAPI : `api/openapi.snapshot.json:1281`.

Consommateur secondaire : `evaluation/plugin_benchmark.py:461`.

## Amont / aval

- Amont : `services/jtms_service.py` + `services/jtms_session_manager.py` (:30-31) ; décorateur de repli si SK absent (:20-28).
- Aval : API `/api/v1/jtms/sk/*` ; benchmark d'évaluation.

## Statut d'intégration

**actif** — montage API mesuré (routes listées ci-dessus), 41 tests unitaires. À ne pas confondre avec [`../../integrations/`](../../integrations/README.md) (`semantic_kernel_integration.py`, résiduel, 0 importeur) : **c'est ici** que vit la surface SK JTMS réellement montée.

## Artefacts et lecteurs

Aucun artefact produit. Lecteurs : développeurs API (endpoints `/sk/`), benchmark.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/plugins/test_jtms_sk_plugin.py -v
```

**41 `def test_`** ; complément integration : `tests/integration/triage/test_realite_pure_jtms.py:92`, `test_jtms_imports.py:28`.

## Frères et parent

Parent : `plugins/` (sans README propre — décrits dans le [`README racine`](../../README.md)). Services amont : [`../../services/jtms/`](../../services/jtms/README.md). Faux frère : [`../../integrations/`](../../integrations/README.md) (résiduel).

## Limites connues

- couverture ligne mesurée **0 %** sur runs réels (`docs/reports/coverage_audit_2026_03_07.md:181` : `jtms_plugin.py`, 154 lignes, 0 %) — les 41 tests unitaires n'attestent pas l'exercice en run réel.
