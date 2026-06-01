# Audit A-16: Speech-to-Text Analyse Fallacieux

**Issue**: #777 (A-16) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthese en 1 phrase

Le projet etudiant `speech-to-text/` (~34 fichiers, Whisper + Gradio + Vue.js, SUIVI 75%) a ete integre de maniere **structurellement complete mais substantiellement vide** -- le cablage pipeline est complet (registry + invoke callable + state writer + workflow phase + router + 2 consumers avances), mais linvoke callable est un **stub mort** qui retourne `{"status": "ready"}` sans jamais appeler le `SpeechTranscriptionService`, le backend Gradio na pas ete migre (tier 2 perdu), la transcription YouTube est absente, et le chainage transcription-analyse fallacieuse nest pas implante.

**Verdict**: :yellow_circle: **INTEGRE structurellement (invoke stub mort)** -- le scaffolding pipeline est complet mais la substance est absente. Le repertoire racine est sanctuarise (reference pedagogique conservee).

---

## 1. Cadrage R281c -- 4 etapes

### 1.1 Localiser la version consolidee

| Fichier consolide | LOC approx | Role | Origine |
| --- | --- | --- | --- |
| `services/speech_transcription_service.py` | ~150 | `SpeechTranscriptionService` + `TranscriptionSegment` + `TranscriptionResult` | Adapte de `speech-to-text/` |
| `orchestration/registry_setup.py` | ~16 | SERVICE registration (2 capabilities) | Nouveau |
| `orchestration/invoke_callables.py` | ~8 | `_invoke_speech_transcription` (STUB MORT) | Nouveau |
| `orchestration/state_writers.py` | ~16 | `_write_speech_to_state` | Nouveau |
| `core/shared_state.py` | ~25 | `transcription_segments` list + `add_transcription_segment()` | Nouveau |
| `orchestration/router.py` | ~3 | `speech_transcription` capability metadata | Nouveau |
| `orchestration/workflows.py` | ~5 | Phase `transcribe` dans full workflow | Nouveau |

**Consommateurs cross-pipeline** : `workflows/democratech.py` (phase 1), `workflows/fact_check_pipeline.py` (phase 1).

### 1.2 Preservation fonctionnelle

| Fonctionnalite etudiante | Preservee ? | Ou | Notes |
| --- | --- | --- | --- |
| Transcription Whisper API | :white_check_mark: Identique | `speech_transcription_service.py` | POST vers endpoint Whisper |
| `TranscriptionSegment` dataclass | :white_check_mark: Identique | Meme fichier | Memes champs |
| `TranscriptionResult` dataclass | :white_check_mark: Identique | Meme fichier | + `to_dict()` |
| `transcribe_file(file_path)` | :white_check_mark: Identique | Service | Synchronous `requests.post()` |
| `transcribe_bytes(audio_data)` | :white_check_mark: Identique | Service | Synchronous `requests.post()` |
| Gradio WebUI backend (tier 2) | :x: Non migre | Reste dans `speech-to-text/` | Fallback local perdu |
| Transcription YouTube (yt-dlp) | :x: Non migre | Reste dans `speech-to-text/` | URL parsing perdu |
| FallacyDetectionService (3-tier) | :x: Non migre | Reste dans `speech-to-text/` | Analyse post-transcription perdue |
| Web API Flask (port 5001) | :x: Non migre | Reste dans `speech-to-text/` | Endpoint standalone perdu |
| Frontend Vue.js + Gradio | :x: Non migre | Reste dans `speech-to-text/` | Frontend standalone |
| Capability registry registration | :white_check_mark: Superieur | `registry_setup.py` | 2 capabilities |
| State writer | :white_check_mark: Superieur | `state_writers.py` | Persiste dans `UnifiedAnalysisState` |
| Workflow phase | :white_check_mark: Superieur | `workflows.py` | Phase `transcribe` (optional) |
| Router auto-routing | :white_check_mark: Superieur | `router.py` | `speech_transcription` capability |
| Invoke callable | :warning: STUB MORT | `invoke_callables.py:2244` | Retourne `{"status": "ready"}` sans appeler le service |
| Cross-pipeline consumption | :white_check_mark: Superieur | democratech, fact_check | 2 workflows avances consomment |

**Score de preservation**: 9/16 fonctionnalites preservees ou superieures (56%). Les 5 perdues sont specifiques au projet etudiant. Le gap critique est le stub mort.

### 1.3 Dilutions / Regressions

#### Dilution 1: Invoke callable est un stub mort (CRITIQUE)

**Localisation**: `invoke_callables.py:2244-2251` -- `_invoke_speech_transcription` retourne `{"status": "ready"}` sans jamais appeler `SpeechTranscriptionService`.
**Impact**: HIGH -- la phase `transcribe` dans les workflows passera sans rien faire. Le pipeline est cable mais **fonctionnellement inerte**.
**Assessment**: Le scaffolding existe mais le coeur est un placeholder. Cas unique dintegration "vide".
**Fix-intent**: `fix(a-16): implement _invoke_speech_transcription to call SpeechTranscriptionService`

#### Dilution 2: Backend Gradio non migre (tier 2 perdu)

**Localisation**: Le service etudiant avait un fallback Gradio WebUI pour la transcription locale.
**Impact**: MEDIUM -- sans cle API Whisper, la transcription est indisponible.
**Assessment**: Perte acceptable -- le fallback necessitait un serveur separe.

#### Dilution 3: Chainage transcription-fallacies non implante

**Localisation**: Le projet etudiant enchainait automatiquement : audio -> transcribe -> detect fallacies.
**Impact**: MEDIUM -- lusage principal nest pas un workflow integre.
**Assessment**: Les deux briques existent mais ne sont pas connectees.

### 1.4 Statut du repertoire racine `speech-to-text/`

**Verdict**: :green_circle: **Sanctuarise -- reference pedagogique conservee** (mandate R300)

- **0 import live Python** -- aucun `from speech_to_text` dans le codebase consolide
- **Fichiers non-migres** : Gradio WebUI, YouTube transcription, FallacyDetectionService, Flask API, Vue.js frontend
- **SUIVI** : 75% -- "Integre"

---

## 2. Matrice des capabilities

| Capability | Module consolide | Statut |
| --- | --- | --- |
| Transcription Whisper API | `services/speech_transcription_service.py` | :white_check_mark: Identique |
| Capability registry (2 caps) | `orchestration/registry_setup.py` | :white_check_mark: Superieur |
| State writer | `orchestration/state_writers.py` | :white_check_mark: Superieur |
| Workflow phase `transcribe` | `orchestration/workflows.py` | :white_check_mark: Superieur |
| Router metadata | `orchestration/router.py` | :white_check_mark: Superieur |
| Cross-pipeline consumption | democratech + fact_check | :white_check_mark: Superieur |
| Invoke callable | `orchestration/invoke_callables.py` | :warning: STUB MORT |
| Gradio fallback | AUCUN | :x: Non migre |
| YouTube transcription | AUCUN | :x: Non migre |
| Post-transcription fallacies | AUCUN | :x: Non cable |

---

## 3. Cartographie des connections

``text
speech-to-text/                            argumentation_analysis/
+-- services/whisper.py --------------> services/speech_transcription_service.py
|   (Whisper API + Gradio)                 (Whisper API seul, Gradio dropped)
+-- services/fallacy_detector.py ------ (NON migre -- 3-tier fallacy)
+-- api/fallacy_api.py ---------------- (NON migre -- Flask API port 5001)
+-- frontend/ ------------------------- (NON migre -- Vue.js + Gradio)

                                           CONSOLIDE (pipeline wiring complet):
                                           +-- orchestration/registry_setup.py (2 caps)
                                           +-- orchestration/invoke_callables.py :warning: STUB
                                           +-- orchestration/state_writers.py
                                           +-- orchestration/workflows.py (phase "transcribe")
                                           +-- orchestration/router.py
                                           +-- core/shared_state.py (transcription_segments)
                                           +-- consumers: democratech.py + fact_check_pipeline.py
``

---

## 4. Fix-intents

| # | Issue proposee | Priorite | Action |
| --- | --- | --- | --- |
| F1 | `fix(a-16): implement _invoke_speech_transcription to call SpeechTranscriptionService` | **HIGH** | Remplacer le stub par un appel reel via `asyncio.to_thread()` |
| F2 | `fix(a-16): add post-transcription fallacy analysis workflow chaining` | **MEDIUM** | Workflow `transcribe_then_analyze` |
| F3 | `fix(a-16): add Gradio WebUI as fallback tier for offline transcription` | **LOW** | Fallback dans le service |

---

## 5. Conclusion

Le projet Speech-to-Text est **structurellement integre mais substantiellement vide** -- le paradoxe de lintegration A-16. Le cablage pipeline est le plus complet de tous les audits :yellow_circle: : registry, invoke, state writer, workflow, router, shared state, 2 consumers. Mais linvoke callable est un **stub mort** -- le pipeline "passe" silencieusement.

**Contraste** : A-10 (dormant, invoke reel), A-13 (pas cable), A-16 (cablage COMPLET mais stub mort -- pire car silencieux).

**Le repertoire `speech-to-text/` est sanctuarise** (mandate R300).

---

## 6. Fichiers sources

- `argumentation_analysis/services/speech_transcription_service.py` -- Service + dataclasses
- `argumentation_analysis/orchestration/invoke_callables.py:2244-2251` -- STUB
- `argumentation_analysis/orchestration/state_writers.py` -- State writer
- `argumentation_analysis/orchestration/registry_setup.py` -- 2 caps
- `argumentation_analysis/orchestration/workflows.py` -- Phase "transcribe"
- `argumentation_analysis/workflows/democratech.py` -- Consumer
- `argumentation_analysis/workflows/fact_check_pipeline.py` -- Consumer
- `tests/unit/argumentation_analysis/services/test_speech_transcription_service.py` -- 18 tests

## A valider par lutilisateur

RAS -- stub mort identifie (HIGH). Decision : implementer ou documenter comme service opt-in non cable ?