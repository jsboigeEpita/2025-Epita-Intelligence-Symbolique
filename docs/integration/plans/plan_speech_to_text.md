# Integration Plan: Speech-to-Text + Analyse Arguments (speech-to-text)

## 1. Sujet (resume spec)

**Spec** : `Custom_Speech_to_Text_Analyse_Arguments_Fallacieux.md`

**Objectif** : Pipeline transcription audio → detection de sophismes. Combine Whisper STT avec l'analyse argumentative existante.

**Fonctionnalites demandees** :
- Transcription audio via Whisper (API OpenAI-compatible)
- Detection de sophismes dans le texte transcrit
- API Flask et frontend Vue.js
- Architecture 3-tiers avec fallback

## 2. Travail Etudiant (analyse code)

### Structure (`speech-to-text/`, ~750 LoC + frontend Vue.js)

| Fichier | LoC | Description |
|---------|-----|-------------|
| `services/fallacy_detector.py` | 445 | **Service principal** : 3 tiers (Advanced/Web API/Pattern) |
| `whisper.py` | 77 | Client Gradio pour Whisper WebUI |
| `config_options.py` | 69 | 3 presets de configuration |
| `api/fallacy_api.py` | — | API Flask |
| `api/mock_api_server.py` | — | Serveur mock pour tests |
| `frontend/` | — | App Vue.js + Vuetify |
| `tests/` | 7 | Tests d'integration |

### Points forts
- Architecture 3-tiers clean avec fallback automatique
- Le tier "Advanced" tente d'importer `InformalAnalysisAgent` du tronc commun — bonne intention d'integration
- Pattern matching toujours disponible comme safety net

### Limitations
- Le tier "Advanced" importe directement du tronc commun (couplage fort)
- Frontend Vue.js hors scope du tronc commun

## 3. Etat Actuel dans le Tronc Commun

### Fichier existant

`argumentation_analysis/services/speech_transcription_service.py` (282 LoC)

### Ce qui fonctionne

- **`SpeechTranscriptionService`** : adaptateur HTTP vers Whisper API (OpenAI-compatible)
- `transcribe_file()` et `transcribe_bytes()` avec segments timestamps
- `is_available()` health check
- Configuration via constructeur ou env vars
- Dataclasses propres (`TranscriptionResult`, `TranscriptionSegment`)

### Ecarts

1. **Import casse dans `unified_pipeline.py`** : importe `speech_transcription` au lieu de `speech_transcription_service`
2. **Seule la transcription** est adaptee — la detection de sophismes est deja geree par les agents existants
3. **ServiceDiscovery** pas effectivement enregistre

## 4. Plan de Consolidation

### 4.1 Classification : Service (verification/correction)

L'adaptateur est bien concu. Il manque le cablage effectif.

### 4.2 Actions

1. **Corriger l'import** dans `unified_pipeline.py` : `speech_transcription` → `speech_transcription_service`
2. **Enregistrer dans ServiceDiscovery** comme provider `transcription`
3. **Enregistrer dans CapabilityRegistry** (type SERVICE)

## 5. Criteres d'Acceptation

- [ ] Import `unified_pipeline.py` corrige
- [ ] Enregistre dans `ServiceDiscovery` (provider "transcription")
- [ ] Enregistre dans `CapabilityRegistry` (type SERVICE)
- [ ] `is_available()` fonctionne
- [ ] Tests passent
- [ ] Zero regression

## 6. Notes

### Effort estime : ~15min

Uniquement correction d'import et cablage. Le code est deja correct.
