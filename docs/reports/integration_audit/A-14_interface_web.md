# Audit A-14: Projet 3.1.1 — Interface Web pour l'Analyse Argumentative

**Issue**: #775 (A-14) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet étudiant `interface_web/` (~1808 LOC Python, 4 modules, 8 templates HTML, auteurs Erwin Rodrigues, Robin de Bastos, SUIVI 65%) a été **partiellement intégré** — l'application Starlette sert le frontend React et expose les routes d'analyse basique, mais les routes JTMS (543 LOC) sont orphelines (Flask Blueprint jamais monté dans Starlette), les routes agents (débat, gouvernance, qualité, contre-arguments) n'existent que dans FastAPI (`api/agent_routes.py`), et les deux serveurs (Starlette :5003 et FastAPI :8095) partagent le même template `dashboard.html` en dupliqué.

**Verdict**: 🟡 **INTÉGRÉ partiellement (dual-serveur fragmenté)** — le frontend est fonctionnel mais l'architecture est scindée entre deux serveurs qui ne partagent pas les routes agents. Le répertoire racine est sanctuarisé (référence pédagogique conservée + template load-bearing).

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Le projet étudiant `interface_web/` est un cas hybride — il contient à la fois du code étudiant et du scaffolding professeur :

| Fichier | LOC approx | Rôle | Origine |
| --- | --- | --- | --- |
| `interface_web/app.py` | ~355 | Starlette ASGI app — sert frontend React + routes analyse | Étudiant (migration Flask → Starlette) |
| `interface_web/routes/jtms_routes.py` | ~543 | Flask Blueprint — 5 routes JTMS (dashboard, playground, sessions, sherlock_watson, tutorial) | Étudiant |
| `interface_web/api/jtms_integration.py` | ~546 | Abstraction layer JTMS backend — session management, belief CRUD | Étudiant |
| `interface_web/services/jtms_websocket.py` | ~364 | WebSocket service — real-time belief propagation | Étudiant |
| `interface_web/templates/` | 8 HTML | dashboard.html (principal) + 6 templates JTMS + index.html | Mixte |
| `api/main.py` | ~120 | FastAPI app — sert même `dashboard.html` + 5 routes agents | Professeur |
| `api/endpoints.py` | ~210 | FastAPI endpoints — analyze, framework, informal, status | Professeur |
| `api/agent_routes.py` | ~393 | FastAPI routes — quality, counter-args, debate, governance, full | Professeur |
| `services/web_api/interface-web-argumentative/` | ~5815 JS | React SPA — 39 fichiers, 9 tabs, D3.js | Professeur |

**Architecture dual-serveur** :

| Serveur | Port | Framework | Routes agents | Sert React |
| --- | --- | --- | --- | --- |
| `interface_web/app.py` | 5003 | Starlette | `/api/analyze`, `/api/v1/framework/analyze` | ✅ (`build/` via StaticFiles) |
| `api/main.py` | 8095 | FastAPI | `/api/v1/agents/*` (quality, debate, governance, counter, full) | ❌ |

### 1.2 Préservation fonctionnelle

| Fonctionnalité étudiante | Préservée ? | Où | Notes |
| --- | --- | --- | --- |
| Application web (Starlette) | ✅ Identique | `interface_web/app.py` | Migration Flask → Starlette par l'étudiant |
| Route analyse textuelle | ✅ Identique | `app.py` `/api/analyze` | Via `ServiceManager.analyze_text()` |
| Route analyse Dung | ✅ Identique | `app.py` `/api/v1/framework/analyze` | Via `ServiceManager.analyze_dung_framework()` |
| Dashboard HTML | ✅ Identique | `templates/dashboard.html` | Servi par Starlette ET FastAPI (dupliqué) |
| Routes JTMS (5 routes) | ⚠️ Orphelines | `routes/jtms_routes.py` | Flask Blueprint — **jamais monté** dans Starlette |
| Intégration JTMS backend | ⚠️ Orpheline | `api/jtms_integration.py` | Flask Blueprint dependency |
| WebSocket belief propagation | ⚠️ Orpheline | `services/jtms_websocket.py` | Non connecté au Starlette app |
| Templates JTMS (6) | ✅ Existent | `templates/jtms/` | Accessibles via filesystem mais routes non montées |
| Frontend React (9 tabs) | ✅ Supérieur | `services/web_api/interface-web-argumentative/` | 5815 LOC, D3.js, 39 fichiers — professeur |
| Routes agents (5) | ✅ Supérieur | `api/agent_routes.py` | quality, counter, debate, governance, full — FastAPI |
| Issue #168 routes web agents | ❌ Non résolu | — | Issue fermée sans implémentation complète |

**Score de préservation**: 6/11 fonctionnalités préservées (55%). Les 5 manquantes sont : 3 routes JTMS orphelines (Flask→Starlette mismatch), 1 WebSocket orphelin, 1 gap routes agents dans Starlette. Le cœur fonctionnel (analyse basique + Dung) est préservé.

### 1.3 Dilutions / Régressions

#### Dilution 1: Routes JTMS orphelines (Flask → Starlette mismatch)

**Localisation**: `interface_web/routes/jtms_routes.py` (543 LOC) utilise Flask Blueprint (`from flask import Blueprint`). L'application Starlette (`app.py`) ne monte PAS ce blueprint — les routes sont mortes.
**Impact**: HIGH — 543 LOC de code JTMS web (dashboard, playground, sessions, sherlock_watson, tutorial) + 546 LOC d'intégration backend + 364 LOC WebSocket = **~1453 LOC orphelins** (80% du code étudiant).
**Assessment**: Le mismatch Flask/Starlette est un artefact de la migration — les routes existent mais ne sont pas accessibles. La réécriture en routes Starlette est un travail de portage, pas de refonte.
**Fix-intent**: `fix(a-14): port jtms_routes from Flask Blueprint to Starlette routes and mount in app.py`

#### Dilution 2: Dual-serveur fragmenté (routes agents absentes de Starlette)

**Localisation**: `api/agent_routes.py` (393 LOC) expose 5 endpoints agents dans FastAPI, mais `interface_web/app.py` (Starlette) qui sert le React frontend n'a PAS ces routes. Le React frontend ne peut pas atteindre les endpoints agents.
**Impact**: HIGH — le React SPA a des components pour debate, governance, spectacular (39 fichiers, 5815 LOC) mais les endpoints backend correspondants ne sont pas accessibles depuis le même serveur que le frontend.
**Assessment**: C'est le gap identifié par l'issue #168 (fermée sans résolution complète). Les routes existent dans FastAPI mais le CORS/ports différenciés rendent l'accès difficile pour le frontend.
**Fix-intent**: `fix(a-14): add agent routes to Starlette app or proxy FastAPI routes from Starlette`

#### Dilution 3: Template dashboard dupliqué

**Localisation**: `api/main.py:84` référence `interface_web/templates/dashboard.html` directement. Les deux serveurs servent le même fichier.
**Impact**: LOW — fonctionnel mais crée un couplage caché entre `api/` et `interface_web/`. Si le template bouge, FastAPI casse.
**Assessment**: Couplage acceptable mais à documenter.

### 1.4 Statut du répertoire racine `interface_web/`

**Verdict**: 🟢 **Sanctuarisé — référence pédagogique conservée** (mandate R300)

- **5 imports live Python** — `interface_web/app.py` importe `ServiceManager` + `nlp_model_manager`, `interface_web/routes/jtms_routes.py` importe `JTMSService` + `JTMSSessionManager` + modèles
- **1 référence load-bearing** — `api/main.py:84` charge `interface_web/templates/dashboard.html`
- **39 fichiers React** — `services/web_api/interface-web-argumentative/src/` est servi par `interface_web/app.py`
- **SUIVI** : 65% — "Partiellement intégré"

---

## 2. Matrice des capabilities

| Capability | Module | Serveur | Statut |
| --- | --- | --- | --- |
| Analyse textuelle | `interface_web/app.py` | Starlette :5003 | ✅ Identique |
| Analyse Dung framework | `interface_web/app.py` | Starlette :5003 | ✅ Identique |
| Dashboard HTML | `templates/dashboard.html` | Starlette + FastAPI | ✅ Identique (dupliqué) |
| Frontend React (9 tabs) | `services/web_api/.../build/` | Starlette :5003 | ✅ Supérieur |
| JTMS dashboard/playground | `routes/jtms_routes.py` | Flask (non monté) | ⚠️ Orphelin |
| JTMS backend integration | `api/jtms_integration.py` | Flask (non monté) | ⚠️ Orphelin |
| JTMS WebSocket | `services/jtms_websocket.py` | Non connecté | ⚠️ Orphelin |
| Quality endpoint | `api/agent_routes.py` | FastAPI :8095 | ✅ Supérieur |
| Counter-argument endpoint | `api/agent_routes.py` | FastAPI :8095 | ✅ Supérieur |
| Debate endpoint | `api/agent_routes.py` | FastAPI :8095 | ✅ Supérieur |
| Governance endpoint | `api/agent_routes.py` | FastAPI :8095 | ✅ Supérieur |
| Full analysis endpoint | `api/agent_routes.py` | FastAPI :8095 | ✅ Supérieur |

---

## 3. Cartographie des connections

```text
interface_web/                            argumentation_analysis/
├── app.py (Starlette) ──────────────────► orchestration/service_manager.py
│   ├── /api/analyze ──► ServiceManager.analyze_text()
│   ├── /api/v1/framework ──► analyze_dung_framework()
│   ├── /dashboard ──► templates/dashboard.html
│   └── /static ──► services/web_api/.../build/ (React SPA)
│
├── routes/jtms_routes.py (Flask) ─── ⚠️ ORPHELIN
│   (543 LOC Flask Blueprint — non monté dans Starlette)
│
├── api/jtms_integration.py ───────── ⚠️ ORPHELIN
│   (546 LOC — dépend de Flask Blueprint)
│
├── services/jtms_websocket.py ─────── ⚠️ ORPHELIN
│   (364 LOC WebSocket — non connecté)
│
└── templates/
    ├── dashboard.html ───────────────► Aussi servi par api/main.py (FastAPI)
    └── jtms/*.html ──────────────────► 6 templates JTMS (routes non montées)

api/ (FastAPI, professeur)
├── main.py ──► GET /dashboard (sert interface_web/templates/dashboard.html)
├── endpoints.py ──► /api/analyze, /api/status, /api/v1/framework, /api/v1/informal
├── agent_routes.py ──► /api/v1/agents/{quality,counter,debate,governance,full}
└── websocket_routes.py ──► WebSocket router

services/web_api/interface-web-argumentative/ (React, professeur)
└── src/ (39 fichiers JS)
    ├── components/ (6) : ArgumentAnalyzer, FallacyDetector, etc.
    ├── components/debate/ (6) : DebateArena, AgentPanel, etc.
    ├── components/governance/ (7) : GovernanceDashboard, VotingPanel, etc.
    ├── components/spectacular/ (10) : DungGraph, JtmsBeliefTree, etc.
    └── services/ (7) : api.js, debateApi.js, proposalApi.js, etc.
```

---

## 4. Fix-intents

| # | Issue proposée | Priorité | Action |
| --- | --- | --- | --- |
| F1 | `fix(a-14): port JTMS routes from Flask Blueprint to Starlette and mount in app.py` | **MEDIUM** | Réécrire `jtms_routes.py` en routes Starlette, monter dans `app.py`. Débloque ~1453 LOC orphelin |
| F2 | `fix(a-14): add agent routes to Starlette or proxy FastAPI routes` | **MEDIUM** | Ajouter les 5 endpoints agents (quality, counter, debate, governance, full) au Starlette app OU configurer un reverse proxy |
| F3 | `fix(a-14): deduplicate dashboard.html serving between FastAPI and Starlette` | **LOW** | Documenter le couplage ou centraliser le template |

---

## 5. Conclusion

Le projet 3.1.1 est **partiellement intégré** — l'application Starlette sert le frontend React et expose les routes d'analyse basique, mais la majorité du code étudiant (JTMS routes + integration + WebSocket = ~1453 LOC, 80%) est **orpheline** suite au mismatch Flask/Starlette. Les routes agents (5 endpoints) n'existent que dans FastAPI, pas dans le Starlette qui sert le frontend.

**Architecture dual-serveur** : le système fonctionne en pratique avec deux serveurs parallèles (Starlette :5003 pour le frontend, FastAPI :8095 pour l'API complète), mais cette fragmentation empêche le frontend React d'accéder aux endpoints agents qui ne sont pas sur le même serveur.

**Contraste avec les autres audits** : A-14 est le seul audit qui porte sur un **frontend/UI** plutôt que sur un agent métier ou un service infrastructure. Le verdict 🟡 reflète la nature hybride du projet — le scaffolding professeur (React SPA, FastAPI) est supérieur, mais le code étudiant (JTMS web) est orphelin.

**Cas d'usage soutenance** : le frontend React avec ses 9 tabs est un excellent point d'entrée pour la démo — mais les tabs debate/governance/spectacular nécessitent que les endpoints FastAPI soient accessibles (soit par proxy, soit par ajout au Starlette).

**Test coverage** : `tests/unit/test_interface_web_starlette.py` couvre le Starlette app basique.

**Le répertoire `interface_web/` est sanctuarisé** (mandate R300) — conservé comme référence pédagogique + template load-bearing (dashboard.html servi par FastAPI).

---

## 6. Fichiers sources

- `interface_web/app.py` — Starlette ASGI app (355 LOC)
- `interface_web/routes/jtms_routes.py` — Flask Blueprint JTMS routes (543 LOC, orphelin)
- `interface_web/api/jtms_integration.py` — JTMS backend abstraction (546 LOC, orphelin)
- `interface_web/services/jtms_websocket.py` — WebSocket belief propagation (364 LOC, orphelin)
- `interface_web/templates/` — 8 HTML templates
- `api/main.py` — FastAPI app (sert dashboard.html)
- `api/agent_routes.py` — 5 endpoints agents (393 LOC)
- `services/web_api/interface-web-argumentative/` — React SPA (5815 LOC JS)
- `docs/projets/sujets/3.1.1_Interface_Web_Analyse_Argumentative.md` — Sujet spec

## À valider par l'utilisateur

- Architecture dual-serveur (Starlette :5003 + FastAPI :8095) — est-ce intentionnel ou un gap à résoudre ?
- Les routes JTMS Flask orphelines (~1453 LOC) — faut-il les porter en Starlette ou les marquer comme legacy ?
- Issue #168 fermée sans résolution complète — confirmer que les routes agents restent dans FastAPI uniquement
