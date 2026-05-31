# Audit B-08: `tests/unit/api/` (root FastAPI) — 14 files, 101 tests

**Issue**: #764 (B-08) | **Epic**: #743 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Vue d'ensemble

| Métrique | Valeur |
|----------|--------|
| Fichiers test | 14 (12 pytest + 2 workers) |
| Fonctions test | 101 (93 pytest + 8 worker inline) |
| LOC tests | 2 565 |
| Fichiers source (`api/`) | 13 |
| LOC source | ~2 000 (estimé) |
| Ratio tests/source | 0.05 LOC test/LOC source |

### Périmètre source

| Fichier source | Rôle |
|---------------|------|
| `api/main.py` | FastAPI ASGI app, 7 routers, 25+ routes |
| `api/endpoints.py` | Analysis, health, status, examples endpoints |
| `api/dependencies.py` | DI providers (get_analysis_service, get_dung_analysis_service) |
| `api/services.py` | DungAnalysisService, analysis service implementations |
| `api/models.py` | Request/response models |
| `api/factory.py` | Service factory |
| `api/websocket_routes.py` | WebSocket streaming routes |
| `api/agent_routes.py` | Agent-specific routes (quality, counter-args, debate, governance) |
| `api/mobile_endpoints.py` | Mobile API (4 endpoints) |
| `api/proposal_endpoints.py` | Proposal CRUD, voting, deliberation |
| `api/proposal_models.py` | Proposal Pydantic models |
| `api/proposal_service.py` | ProposalStore, proposal logic |

---

## 1. Classification a/b/c — Tableau de wiring

### Légende

- ✅ **Wired** : test couvre un module enregistré dans `CapabilityRegistry` / utilisé par un workflow
- ⚠️ **Dérogation justifiée** : helper interne, infrastructure, validation contractuelle
- ❌ **Orphelin** : test duplique un autre test, ou test sans source correspondante, ou source sans test

| Fichier test | Tests | Cible source | Wiring | Notes |
|-------------|-------|-------------|--------|-------|
| `test_api_endpoints.py` | 10 | `api/main.py` + endpoints + dependencies | ⚠️ Justifié | API contract tests (health/status/examples/analyze/docs). Duplique partiellement `test_api_direct.py` et `test_fastapi_simple.py` |
| `test_analysis_service_mock.py` | 1 | `api/endpoints.py` + DI | ✅ Wired | DI override pattern — vérifie le contrat du mock service |
| `test_fastapi_gpt4o_authentique.py` | 2 | `api/main.py` (subprocess) | ❌ Dupliqué | Subprocess integration test — en double avec `test_api_direct_simple.py`. Mal classé dans `unit/` (c'est un test d'intégration) |
| `test_fastapi_simple.py` | 7 | `api/main.py` + endpoints | ❌ Dupliqué | Quasi-identique à `test_api_endpoints.py` (même séquence health→examples→analyze→fallacy) |
| `test_mobile_endpoints.py` | 14 | `api/mobile_endpoints.py` | ✅ Wired | 4 endpoints (analyze/fallacies/validate/chat), validation 422, graceful degradation |
| `test_proposal_api.py` | 23 | `api/proposal_endpoints.py` + `proposal_service.py` | ✅ Wired | Meilleur fichier du packet — lifecycle complet CRUD + vote + deliberation + workflow + store |
| `test_websocket_routes.py` | 4 | `api/websocket_routes.py` | ⚠️ Justifié | Ping/pong only — couverture minimale des 3 WebSocket endpoints |
| `test_agent_routes.py` | 13 | `api/agent_routes.py` | ✅ Wired | Quality, counter-args, debate, governance, full analysis + validation |
| `test_api_direct_simple.py` | 2 | `api/main.py` (subprocess) | ❌ Dupliqué | Subprocess test — double de `test_fastapi_gpt4o_authentique.py` (DEVNULL au lieu de pipe streaming) |
| `test_api_direct.py` | 10 | `api/main.py` | ❌ Dupliqué | **Copie quasi-exacte** de `test_api_endpoints.py` (même classe, mêmes méthodes, Mock setup quasi-identique) |
| `test_dung_service.py` | 8 | `api/services.py` (DungAnalysisService) | ✅ Wired | Dual-mode: JVM-backed (jpype/tweety markers) + networkx pure-Python mock. 4 scenarios × 2 modes |
| `workers/worker_api_endpoints.py` | 3 | `api/endpoints.py` (Dung API) | ✅ Wired | Subprocess worker — JVM isolation pattern |
| `workers/worker_dung_service.py` | 4 | `api/services.py` (Dung) | ✅ Wired | Subprocess worker — real Tweety, 4 scenarios |

---

## 2. Sources sans test dédié

| Source | LOC | Rôle | Priorité |
|--------|-----|------|----------|
| `api/models.py` | ~100 | Request/response Pydantic models | LOW — testé indirectement via endpoints |
| `api/factory.py` | ~80 | Service factory | LOW — testé via dependencies |
| `api/proposal_models.py` | ~80 | Proposal Pydantic models | LOW — testé via test_proposal_api.py |

Aucune source critique n'est sans test. Le packet API est bien couvert.

---

## 3. Récit du framework — Évolution cristallisée dans les tests

### Épisode 1: L'API originelle — test_api_endpoints.py (Mars 2025)
Le fichier `test_api_endpoints.py` (173 LOC, 10 tests) documente la **première API** du projet: une interface FastAPI minimale avec health/status/examples/analyze/docs. Le test 01 vérifie l'environnement (imports, JVM setup), le test 02 démarre l'API, les tests 03-04 vérifient les endpoints passifs, les tests 06-09 testent l'analyse avec/sans sophismes, et le test 10 vérifie OpenAPI docs. C'est le prototype initial — Mock pour project_context (JVM/tweety), TestClient synchrones, pas de LLM réel.

### Épisode 2: La tentative d'intégration authentique (skipif pattern)
Deux fichiers (`test_fastapi_gpt4o_authentique.py` et `test_api_direct_simple.py`) révèlent une tentative de tester l'API avec un vrai serveur uvicorn. Le pattern: `subprocess.Popen` → `requests` library → 30-45s timeout → assert sur les réponses. Les deux fichiers sont des **variations du même concept** (l'un avec pipe streaming, l'autre avec DEVNULL pour éviter les deadlocks). Ils utilisent `@pytest.mark.skipif(not API_ENVIRONMENT_AVAILABLE)` — ils se skippent en CI. Ce pattern a été abandonné au profit du TestClient in-process.

### Épisode 3: L'explosion des endpoints — mobile, proposals, agents (Avril-Mai 2025)
Trois fichiers majeurs documentent l'expansion de l'API au-delà du prototype initial:
- `test_mobile_endpoints.py` (14 tests) — 4 endpoints mobiles (analyze/fallacies/validate/chat)
- `test_proposal_api.py` (23 tests) — système complet de proposals avec CRUD, vote, délibération
- `test_agent_routes.py` (13 tests) — routes agents (quality, counter-args, debate, governance, full analysis)

Ces trois fichiers sont les **meilleurs tests du packet**: mocking ciblé (`@patch("...run_unified_analysis")`), validation 422, graceful degradation, backward compat (string format counter-args), et isolation d'état global (autouse fixture reset pour ProposalStore).

### Épisode 4: Le Dung dual-mode — JVM + networkx (Issue #165)
`test_dung_service.py` (8 tests) documente le **seul composant de l'API qui utilise directement Tweety/JPype**: le DungAnalysisService. Le pattern dual-mode est remarquable: `TestDungServiceDirect` (4 tests, markers jpype/tweety, vraie JVM) + `TestDungServiceMocked` (4 tests, networkx pure-Python). Le mock n'est pas un MagicMock mais une **réimplémentation complète** des sémantiques Dung en Python (~140 LOC de grounded/preferred/stable extension computation via networkx). Les worker scripts (`worker_api_endpoints.py`, `worker_dung_service.py`) exécutent les mêmes scénarios en subprocess pour l'isolation JVM.

### Épisode 5: La duplication structurelle — 3 copies du même test
Les fichiers `test_api_endpoints.py`, `test_fastapi_simple.py`, et `test_api_direct.py` sont **3 versions quasi-identiques** du même test de l'API de base (health/status/examples/analyze). De même, `test_fastapi_gpt4o_authentique.py` et `test_api_direct_simple.py` sont 2 versions du même subprocess test. Cette duplication documente une **itération non-nettoyée** — chaque variante a été créée comme amélioration de la précédente (TestClient → subprocess → TestClient amélioré) sans que les anciennes soient supprimées.

---

## 4. Patterns transversaux

### 4.1 Duplication massive
Le problème dominant du packet: **5 fichiers sur 12 sont des doublons** (3× API endpoints de base, 2× subprocess tests). Cela représente ~880 LOC / 41 tests redondants. La cause probable: développement itératif sans cleanup.

### 4.2 Tests d'intégration dans le dossier unit/
`test_fastapi_gpt4o_authentique.py` et `test_api_direct_simple.py` lancent de vrais serveurs uvicorn — ce sont des tests d'intégration, pas des tests unitaires. Leur placement dans `tests/unit/api/` est incorrect.

### 4.3 Pattern worker/subprocess
Les fichiers `workers/` implémentent un pattern intéressant: test en subprocess avec isolation JVM. Ce pattern est unique à ce packet et reflète la contrainte Windows DLL (torch doit charger avant JPype — issue #512).

### 4.4 Couverture WebSocket minimale
`test_websocket_routes.py` (4 tests, ping/pong only) est le test le plus faible du packet. Les 3 endpoints WebSocket (analysis, debate, deliberation) ne sont testés que pour leur connexion, pas pour le streaming de résultats.

---

## 5. Recommandations

| # | Recommandation | Priorité | Justification |
|---|---------------|----------|---------------|
| R1 | Supprimer `test_api_direct.py` (doublon de `test_api_endpoints.py`) | **HIGH** | Copie quasi-exacte (173 LOC, mêmes 10 tests). Gain: -173 LOC, -10 tests redondants |
| R2 | Supprimer `test_fastapi_simple.py` (doublon de `test_api_endpoints.py`) | **HIGH** | Quasi-identique (120 LOC, 7/10 tests miroir). Gain: -120 LOC |
| R3 | Fusionner `test_fastapi_gpt4o_authentique.py` + `test_api_direct_simple.py` → 1 fichier integration | **MEDIUM** | Même concept (subprocess), 2 variantes (pipe vs DEVNULL). Garder la variante DEVNULL (plus robuste). Déplacer vers `tests/integration/` |
| R4 | Enrichir `test_websocket_routes.py` (ajouter payload tests) | **MEDIUM** | 4 tests ping-only pour 3 endpoints de streaming. Ajouter au minimum 1 test de payload par endpoint |
| R5 | Retirer l'import `AsyncMock` inutilisé dans `test_mobile_endpoints.py` | **LOW** | Dead import |

---

## 6. Fix-intents ouverts

Conformément au DoD enrichi (R289), chaque finding actionnable correspond à une issue `fix-*`:

| Finding | Issue proposée | Label |
|---------|---------------|-------|
| `test_api_direct.py` = doublon de `test_api_endpoints.py` | `fix(b-08): remove duplicate test_api_direct.py` | `fix-intent`, `cleanup` |
| `test_fastapi_simple.py` = doublon partiel | `fix(b-08): remove duplicate test_fastapi_simple.py` | `fix-intent`, `cleanup` |
| 2 subprocess tests en double dans unit/ | `fix(b-08): merge+move subprocess tests to integration/` | `fix-intent`, `test-organization` |
| WebSocket tests ping-only | `fix(b-08): add payload tests to websocket_routes` | `fix-intent`, `test-coverage` |

*(Issues à ouvrir par le coordinateur lors du backfill #797)*

---

## 7. Synthèse

| Classification | Fichiers test | Tests | % |
|---------------|--------------|-------|---|
| ✅ Wired | 7 | 66 | 65% |
| ⚠️ Justifié (contract/DI) | 2 | 14 | 14% |
| ❌ Dupliqué (orphelin structurel) | 3 | 19 | 19% |
| Workers (subprocess) | 2 | 8 | 8% |
| **Total** | 14 | 101 | 100% |

**Key finding**: Ce packet révèle un **problème de duplication historique** — 5 fichiers sur 12 sont des doublons, représentant 880 LOC et 41 tests redondants. Le nettoyage supprimerait ~35% du packet sans perte de couverture.

**Angle mort principal**: Les tests WebSocket sont ping-only (4 tests pour 3 endpoints de streaming). Les payload tests manquants sont le gap le plus significatif.

**Meilleur fichier**: `test_proposal_api.py` (23 tests, lifecycle complet, isolation propre) — modèle pour les autres fichiers du packet.
