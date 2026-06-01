# Audit A-15: Projet 3.1.5 — Interface Mobile

**Issue**: #776 (A-15) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet étudiant `3.1.5_Interface_Mobile/` (~36 fichiers React Native/Expo, 3 auteurs Angela Saade, Armand Blin, Baptiste Arnold, SUIVI 70%) a été **intégré par API proxy** — le backend mobile (`api/mobile_endpoints.py`, 261 LOC, 4 endpoints) est câblé dans FastAPI via le pipeline unifié (`run_unified_analysis` + `SemanticArgumentAnalyzer`), tandis que le frontend React Native reste standalone (dual-mode : backend FastAPI ou OpenAI direct), avec des défauts latents critiques dans les endpoints (`/chat` TypeError, `/validate` type mismatch) et des tests donnant une fausse confiance (try/except large masquant les bugs).

**Verdict**: 🟡 **INTÉGRÉ partiellement (backend câblé, défauts latents)** — l'architecture API proxy est correcte mais les bugs runtime et la couverture de test dégradée réduisent l'effectivité. Le répertoire racine est sanctuarisé (référence pédagogique conservée).

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Le projet étudiant a été digéré en **un backend API proxy** dans le codebase consolidé, avec le frontend restant standalone :

| Fichier consolidé | Origine étudiante | LOC approx | Rôle |
| --- | --- | --- | --- |
| `api/mobile_endpoints.py` | Créé pour le projet | ~261 | 4 endpoints FastAPI : `/api/mobile/{analyze,fallacies,validate,chat}` |
| `api/main.py` | Nouveau | ~2 | Import + montage `mobile_router` |
| `tests/unit/api/test_mobile_endpoints.py` | Nouveau | ~218 | Tests unitaires 4 endpoints |

**Frontend** (reste dans `3.1.5_Interface_Mobile/`) :

- 36 fichiers React Native/Expo (TypeScript)
- `services/api.ts` (206 LOC) : client dual-mode (backend ou OpenAI direct)
- 6 écrans : home, analysis/analyze, analysis/fallacies, analysis/validate, chat
- 6 composants UI : ArgumentCard, FallacyCard, ValidationCard, QualityBadge, etc.

### 1.2 Préservation fonctionnelle

| Fonctionnalité étudiante | Préservée ? | Où | Notes |
| --- | --- | --- | --- |
| Analyse textuelle mobile | ✅ Supérieur | `api/mobile_endpoints.py` `/analyze` | Via `run_unified_analysis("light")` |
| Détection sophismes mobile | ✅ Supérieur | `api/mobile_endpoints.py` `/fallacies` | Via `run_unified_analysis("standard")` |
| Validation logique mobile | ⚠️ Buggé | `api/mobile_endpoints.py` `/validate` | Type mismatch Toulmin fields (objets vs strings) |
| Chat assistant mobile | ⚠️ Buggé | `api/mobile_endpoints.py` `/chat` | `create_llm_service()` sans `service_id` → TypeError |
| Client API dual-mode | ✅ Identique | `3.1.5_Interface_Mobile/services/api.ts` | Backend-first, OpenAI fallback |
| UI React Native (6 écrans) | ✅ Identique | `3.1.5_Interface_Mobile/app/` | Expo Router, TypeScript |
| Composants UI (6) | ✅ Identique | `3.1.5_Interface_Mobile/components/` | Cards, badges, themed primitives |
| Router registration | ✅ Présent | `api/main.py` ligne 7 + 52 | `mobile_router` monté |
| OpenAPI spec | ✅ Présent | `api/openapi.snapshot.json` | Schemas pour 4 routes |
| Tests endpoint | ⚠️ Faux positifs | `test_mobile_endpoints.py` | try/except large → HTTP 200 même en erreur |
| WebSocket/SSE streaming | ❌ Non implémenté | — | `/chat` synchrone uniquement |

**Score de préservation**: 7/11 fonctionnalités préservées (64%). Les 4 problèmes : 2 bugs runtime (chat TypeError, validate type mismatch), 1 fausse couverture de test, 1 gap streaming.

### 1.3 Dilutions / Régressions

#### Dilution 1: Endpoint `/chat` TypeError (défaut latent critique)

**Localisation**: `api/mobile_endpoints.py` — `create_llm_service()` appelé sans le paramètre requis `service_id`.
**Impact**: HIGH — l'endpoint crashera avec `TypeError` à chaque appel. Le fallback OpenAI du frontend ne sera jamais atteint via le backend.
**Assessment**: Bug de signature — probablement apparu lors d'un refactoring de `create_llm_service()` qui a ajouté un paramètre requis. Les tests ne le détectent pas car le mock contourne l'appel réel.
**Fix-intent**: `fix(a-15): add service_id parameter to create_llm_service() call in mobile chat endpoint`

#### Dilution 2: Endpoint `/validate` type mismatch (défaut latent)

**Localisation**: `api/mobile_endpoints.py` — les champs du modèle Toulmin sont retournés comme objets structurés mais le contrat mobile attend des strings.
**Impact**: MEDIUM — le frontend mobile reçoit des types inattendus et l'affichage peut échouer ou être incorrect.
**Assessment**: Mismatch de sérialisation — le backend utilise le modèle Toulmin complet alors que le contrat API mobile était simplifié.
**Fix-intent**: `fix(a-15): fix Toulmin field serialization in mobile validate endpoint`

#### Dilution 3: Tests donnant fausse confiance

**Localisation**: `tests/unit/api/test_mobile_endpoints.py` (218 LOC) — utilisation de try/except large qui retourne HTTP 200 même quand la logique endpoint lève une exception.
**Impact**: MEDIUM — les tests passent même quand les endpoints ont des bugs (comme les 2 ci-dessus). Fausses vert.
**Assessment**: Pattern de test dégradé — les tests valident le Happy Path mocké mais ne détectent pas les bugs de signature/type.
**Fix-intent**: `fix(a-15): replace broad try/except in mobile endpoint tests with specific assertions`

#### Pas d'autre dilution majeure

L'architecture proxy (backend API wrapper autour du pipeline unifié) est **correcte** — le frontend mobile est découplé et fonctionne en dual-mode (backend ou OpenAI direct).

### 1.4 Statut du répertoire racine `3.1.5_Interface_Mobile/`

**Verdict**: 🟢 **Sanctuarisé — référence pédagogique conservée** (mandate R300)

- **0 import live Python** — aucun `from 3.1.5` dans le codebase consolidé (frontend React Native, pas Python)
- **API proxy** : `api/mobile_endpoints.py` sert de pont, le frontend appelle ces endpoints via HTTP
- **Frontend standalone** : l'app Expo fonctionne indépendamment avec sa propre clé OpenAI
- **SUIVI** : 70% — "Intégré"

---

## 2. Matrice des capabilities

| Capability | Module | Statut |
| --- | --- | --- |
| Analyse textuelle (mobile) | `api/mobile_endpoints.py` `/analyze` | ✅ Supérieur (pipeline unifié) |
| Détection sophismes (mobile) | `api/mobile_endpoints.py` `/fallacies` | ✅ Supérieur (pipeline unifié) |
| Validation logique (mobile) | `api/mobile_endpoints.py` `/validate` | ⚠️ Buggé (type mismatch) |
| Chat assistant (mobile) | `api/mobile_endpoints.py` `/chat` | ⚠️ Buggé (TypeError) |
| Router registration | `api/main.py` | ✅ Présent |
| OpenAPI spec | `api/openapi.snapshot.json` | ✅ Présent |
| Frontend React Native | `3.1.5_Interface_Mobile/` | ✅ Identique (standalone) |

---

## 3. Cartographie des connections

```text
3.1.5_Interface_Mobile/                    argumentation_analysis/
├── services/api.ts ─────────────────────► api/mobile_endpoints.py
│   (dual-mode: backend ou OpenAI direct)   (4 endpoints FastAPI)
│                                            │
│   ├── analyzeText() ──► /api/mobile/analyze
│   │                       └──► run_unified_analysis("light")
│   ├── detectFallacies() ─► /api/mobile/fallacies
│   │                       └──► run_unified_analysis("standard")
│   ├── validateArgument() ► /api/mobile/validate
│   │                       └──► SemanticArgumentAnalyzer ⚠️ type mismatch
│   └── sendChatMessage() ─► /api/mobile/chat
│                           └──► create_llm_service() ⚠️ TypeError
│
├── app/ (6 écrans React Native)
├── components/ (6 composants UI)
└── constants/llm.ts (prompts + config)

                                    Tests:
                                    ├── tests/unit/api/test_mobile_endpoints.py
                                    │   (218 LOC — ⚠️ false positive coverage)
                                    └── tests/integration/api/test_openapi_contract.py
                                        (mobile_router referenced)
```

---

## 4. Fix-intents

| # | Issue proposée | Priorité | Action |
| --- | --- | --- | --- |
| F1 | `fix(a-15): add service_id parameter to create_llm_service() in mobile chat endpoint` | **HIGH** | Corriger le TypeError dans `/api/mobile/chat` |
| F2 | `fix(a-15): fix Toulmin field serialization in mobile validate endpoint` | **MEDIUM** | Sérialiser les champs Toulmin en strings pour le contrat mobile |
| F3 | `fix(a-15): replace broad try/except in mobile endpoint tests` | **MEDIUM** | Utiliser des assertions spécifiques au lieu de try/except large |

---

## 5. Conclusion

Le projet 3.1.5 est **partiellement intégré** — l'architecture API proxy est correcte et le frontend React Native est bien conçu (dual-mode backend/OpenAI, 6 écrans, 6 composants). Cependant, **2 bugs runtime critiques** dans les endpoints (`/chat` TypeError, `/validate` type mismatch) et **1 problème de couverture de test** (faux positifs) dégradent significativement l'effectivité de l'intégration.

**Contraste avec A-14 (Interface Web)** : A-15 a une architecture plus propre — un seul serveur (FastAPI), un seul endpoint layer (`mobile_endpoints.py`), pas de dual-serveur. Mais les bugs latents sont plus graves (2 endpoints cassés sur 4).

**Contraste avec les audits métier (A-07 à A-12)** : A-15 est un audit **frontend/proxy** plutôt que métier. Le câblage pipeline est présent (`run_unified_analysis` + `SemanticArgumentAnalyzer`) mais les bugs de signature empêchent l'utilisation réelle.

**Cas d'usage soutenance** : le frontend React Native est un bon point d'entrée mobile — après correction des 2 bugs, la démo serait complète (analyse, fallacies, validation, chat).

**Test coverage** : `test_mobile_endpoints.py` (218 LOC) couvre les 4 endpoints mais avec des patterns de test dégradés. La couverture est **nominale** (les tests passent) mais **ineffective** (ils ne détectent pas les bugs).

**Le répertoire `3.1.5_Interface_Mobile/` est sanctuarisé** (mandate R300) — conservé comme référence pédagogique + frontend standalone.

---

## 6. Fichiers sources

- `api/mobile_endpoints.py` — 4 endpoints FastAPI mobile (261 LOC)
- `api/main.py` — Router registration (mobile_router)
- `3.1.5_Interface_Mobile/services/api.ts` — Client API dual-mode (206 LOC)
- `3.1.5_Interface_Mobile/app/` — 6 écrans React Native/Expo
- `3.1.5_Interface_Mobile/components/` — 6 composants UI
- `tests/unit/api/test_mobile_endpoints.py` — Tests unitaires (218 LOC)
- `api/openapi.snapshot.json` — OpenAPI spec (4 routes mobile)

## À valider par l'utilisateur

- Endpoint `/chat` TypeError (HIGH) — correction immédiate recommandée
- Endpoint `/validate` type mismatch (MEDIUM) — impact sur l'affichage mobile
- Pattern de test dégradé (MEDIUM) — les tests masquent les bugs existants
