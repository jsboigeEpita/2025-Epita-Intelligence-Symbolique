# A-Track Fix Verification — R309

**Date**: 2026-06-02
**Author**: Claude Code @ myia-po-2023
**Base**: `bc160caf` (main, post-R309 batch merge)
**Scope**: 4 A-track fixes merged in R309 batch

---

## 0. Synthèse

**La boucle audit→fix A-track est fermée.** Les 4 fix-intents mergés en R309 résolvent réellement les findings de leurs audits respectifs — ce n'est pas juste « du code a bougé ». 51 tests runtime confirment (0 échec, 3.09s). Un résidu cosmétique mineur identifié sur #876 (attribut `model_id` vs `model`), non bloquant.

| PR | Issue(s) | Finding origin | Verdict |
|----|----------|---------------|---------|
| #868 | #857 | A-14 (#775) | ✅ RÉSOLU |
| #869 | #846/#847/#848 | A-15 (bugs runtime) | ✅ RÉSOLU |
| #871 | #858 | A-14 follow-up (Hermes review) | ✅ RÉSOLU |
| #876 | #834 | A-10 (#759) | ✅ RÉSOLU (résidu cosmétique) |

---

## 1. #868/#857 — JTMS Import Guard (A-14)

**Finding** (A-14 #775): L'import hard-coded de `jtms_endpoints` dans `api/main.py` crashait toute l'app FastAPI si le module échouait (SPOF unique).

**Fix mergé**: 4 points de garde dans `api/main.py`:

| Garde | Ligne | Description |
|-------|-------|-------------|
| Try/except import | L13-31 | `except ImportError` → log warning + fallback `None` + flag `_JTMS_AVAILABLE = False` |
| Startup init | L59-70 | Double guard : flag check + inner `try/except Exception` pour runtime JVM failure |
| Router mount | L90-91 | `if _JTMS_AVAILABLE and jtms_router is not None` |
| Fallback values | L29-30 | `jtms_router = None`, `initialize_jtms_services = None` |

**Preuve runtime**: 11 tests dans `tests/unit/api/test_jtms_import_guard.py` — 7 structurels (assertions sur source) + 4 behavioraux (app mockée). Tous PASS.

**Verdict**: ✅ **RÉSOLU** — l'app FastAPI démarre même si jtms_endpoints échoue. Le SPOF est éliminé.

---

## 2. #869/#846-848 — Mobile Endpoint Fixes (A-15)

**Findings** (A-15): 3 bugs runtime sur endpoints mobile.

### #846 — service_id manquant sur /chat

**Fix**: `mobile_endpoints.py:225` — `create_llm_service(service_id="mobile_chat")` (était `create_llm_service()` sans args → `TypeError`).

**Preuve**: `test_mobile_endpoints.py:201-217` — `mock_create.assert_called_once_with(service_id="mobile_chat")`.

### #847 — Toulmin sérialisation objects au lieu de strings

**Fix**: `mobile_endpoints.py:198-205` — extraction `.text` sur `ToulminComponent` avec null-safe guards (`hasattr(d, "text") else str(d)`).

**Preuve**: `test_mobile_endpoints.py:136-172` — `test_validate_toulmin_fields_are_strings` construit un vrai `ToulminAnalysisResult` et assert `isinstance(..., str)` + valeurs exactes.

### #848 — assertions de test incohérentes

**Fix**: Test file réécrit (+130/-64 lignes). Assertions typées (Pydantic models), fixture standalone FastAPI (évite DLL crash torch/JPype).

**Preuve runtime**: 14 tests mobile — tous PASS.

**Verdict**: ✅ **RÉSOLU** — les 3 bugs sont corrigés et les tests sont des gardes de régression authentiques.

---

## 3. #871/#858 — WS Docs + Accent + Env Vars (A-14 follow-up)

**Findings** (R288 follow-up à PR #851): 3 items mineurs.

### WS relay placeholder → documented as unavailable

**Fix**: `interface_web/app.py:164-198` — `ws_proxy()` docstring explicite (« relais WS bidirectionnel non implémenté ») + message d'erreur structuré `ws_relay_unavailable` + close code `1011`. Architecture diagram corrigé (suppression flèche `/ws/* -> FastAPI`).

**Note**: `ws_proxy` est défini mais **non enregistré comme route** — le code d'erreur explicite n'est pas encore atteignable par un client (tomberait sur StaticFiles handler). La limitation est correctement documentée, le code est prêt pour un futur wiring. Non-goal acté (Option-1).

### Accent restauré

**Fix**: `interface_web/app.py:211` — `"mouillée"` (accent restauré, était `"mouillee"`).

### Env vars documentées

**Fix**: `interface_web/app.py:19-24` — bloc `Environment Variables (two-server deployment model)` documentant `FASTAPI_HOST`, `FASTAPI_PORT`, `PORT`, `REACT_APP_BACKEND_URL`.

**Preuve runtime**: 8 tests dans `test_starlette_proxy.py` (3 WS + 1 accent + 4 env) — tous PASS.

**Verdict**: ✅ **RÉSOLU** — accent OK, env vars documentées, WS limitation correctement documentée. Non-goal (relais complet) respecté.

---

## 4. #876/#834 — Local LLM State Writer (A-10)

**Finding** (A-10 #759): Le service local_llm n'écrivait pas ses résultats dans `UnifiedAnalysisState`.

**Fix mergé**: `_invoke_local_llm` dans `invoke_callables.py:2211` écrit dans le state dans les 3 chemins:

| Chemin | Ligne | Action |
|--------|-------|--------|
| Success | L2274-2281 | `state.local_llm_results.append(result)` + `add_trace_entry(phase="local_llm")` |
| Unavailable | L2234-2235 | `state.local_llm_results.append({"status": "skipped"})` |
| Error | L2260-2261 | `state.local_llm_results.append({"status": "error"})` |

**Disponibilité**: `invoke_callables.py:2224` — `await service.is_available()` avec try/except (exception → unavailable).

**Champ state**: `shared_state.py:454` — `self.local_llm_results: List[Dict[str, Any]] = []`.

**Registry**: `registry_setup.py:213-219` — service enregistré avec invoke callable.

**Preuve runtime**: 9 tests dans `test_local_llm_wiring.py` — tous PASS.

### Résidu cosmétique

`invoke_callables.py:2267` lit `service.model_id` mais `LocalLLMService` définit `self.model` (L46), pas `self.model_id`. Le code a un guard `hasattr(service, "model_id") else "local"` — le model configuré n'est jamais surfacé dans les résultats (fallback `"local"` systématique). Non bloquant (le wiring fonctionne), mais l'information du model configuré est perdue.

**Action**: Pas de fix-intent dédié — c'est cosmétique (le champ model dans les résultats est informatif). À noter si un futur rapport LLM a besoin du model name exact.

**Verdict**: ✅ **RÉSOLU** — local_llm écrit bien dans le state. Résidu cosmétique `model_id` non bloquant.

---

## 5. Résumé des tests runtime

```
pytest tests/unit/api/test_jtms_import_guard.py \
       tests/unit/api/test_mobile_endpoints.py \
       tests/unit/api/test_starlette_proxy.py \
       tests/unit/argumentation_analysis/orchestration/test_local_llm_wiring.py \
       -v --tb=short

======================= 51 passed, 9 warnings in 3.09s =======================
```

| Suite | Tests | Résultat |
|-------|-------|----------|
| `test_jtms_import_guard.py` | 11 | ✅ 11 passed |
| `test_mobile_endpoints.py` | 14 | ✅ 14 passed |
| `test_starlette_proxy.py` | 17 | ✅ 17 passed |
| `test_local_llm_wiring.py` | 9 | ✅ 9 passed |

---

## 6. Conclusion

**La boucle audit→fix A-track est fermée.** Les 4 fix-intents A-track mergés en R309 résolvent réellement les findings de leurs audits. Pas de régression, pas de finding PARTIEL non résolu (le résidu `model_id` est cosmétique et ne masque pas une finding).

## À valider par l'utilisateur

RAS — toutes les findings sont RÉSOLUES, pas de décision utilisateur en suspens.
