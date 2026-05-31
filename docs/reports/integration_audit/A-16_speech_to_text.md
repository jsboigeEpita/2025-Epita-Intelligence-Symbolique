# Audit A-16: Speech-to-Text

**Issue**: N/A | **SUIVI**: Score 75% | **Date audit**: 2026-05-31

## Status: 🟡 Partial

The speech transcription service is registered and wired into the pipeline, but several advertised features are stubs or have been dropped from the original design.

## What was delivered (student source)

- Speech-to-text service with Whisper API integration
- Original design: 2-tier transcription (Whisper API + Gradio local tier)
- YouTube link transcription support
- Integration with analysis pipeline

## What exists in `argumentation_analysis/`

| Layer | File | Detail |
|---|---|---|
| Service | `services/speech_transcription_service.py` | `SpeechTranscriptionService` + `TranscriptionSegment` + `TranscriptionResult` |
| Registry | `orchestration/registry_setup.py:314-327` | `speech_transcription_service` with capabilities `speech_transcription`, `speech_to_text` |
| Invoke callable | `orchestration/invoke_callables.py:2244` | `_invoke_speech_transcription` async function |
| State writer | `orchestration/state_writers.py:1022` | `_write_speech_to_state` → `transcription_segments` |
| Router | `orchestration/router.py:43,76,420` | `speech_transcription` capability with routing metadata |
| Workflow | `orchestration/workflows.py:154` | `speech_transcription` capability included in workflow definitions |
| Tests | `tests/unit/argumentation_analysis/services/test_speech_transcription_service.py` | 18 tests |

## Preservation Assessment

- Service class: **PRESENT** — `SpeechTranscriptionService` with `transcribe_file()`, `transcribe_bytes()`, `get_status_details()`
- Data model: **PRESENT** — `TranscriptionSegment` and `TranscriptionResult` dataclasses with `to_dict()`
- Registry integration: **PRESENT** — Registered with capability discovery
- State chain: **PRESENT** — Results flow through `state_writers.py` to `transcription_segments`
- Tests: **PRESENT** — 18 unit tests

## Gap Analysis

### Implementation Gaps

1. **Only 1-tier (Whisper API), not 2-tier** — The original design specified a Gradio local tier as fallback. Only the Whisper API tier is implemented. The Gradio tier was dropped during integration.

2. **Async is cosmetic** — The `_invoke_speech_transcription` callable is declared `async` but the actual `SpeechTranscriptionService.transcribe_file()` method is synchronous. The `async` keyword provides no concurrency benefit — it is a stub pattern.

3. **Docstring claims `transcribe_and_analyze` but no such method exists** — The service docstring or comments reference a combined transcription + analysis method that was never implemented. Only `transcribe_file()` and `transcribe_bytes()` exist.

4. **YouTube link transcription lost** — The original student project supported YouTube URL transcription. This capability is absent from the integrated service — no URL parsing, no `yt-dlp` integration, no audio download pipeline.

5. **Invoke callable is a stub that never calls the service** — `_invoke_speech_transcription` in `invoke_callables.py` does not actually invoke `SpeechTranscriptionService.transcribe_file()`. The callable exists for registry compliance but does not perform real transcription.

### Scoring Justification

The 75% score reflects that the service is structurally integrated (registry, state, router, workflow) but the implementation has significant holes. The wiring is complete; the substance is partial.

## Recommended Action

**Medium priority.** The integration scaffolding is solid but the implementation needs completion:

1. **Make async real** — Either make `transcribe_file()` truly async (e.g., `asyncio.to_thread`) or remove the misleading `async` decorator from the invoke callable
2. **Implement the invoke callable** — Connect `_invoke_speech_transcription` to actually call `SpeechTranscriptionService.transcribe_file()`
3. **Drop or document missing features** — Remove docstring references to `transcribe_and_analyze` and YouTube transcription, or implement them
4. **Consider adding Gradio tier** — If local transcription is needed, add the Gradio fallback as originally designed
5. **Add integration test** — Current 18 tests are unit-level. Add at least one test that exercises the full invoke callable path.

## Source Files

- `argumentation_analysis/services/speech_transcription_service.py`
- `argumentation_analysis/orchestration/registry_setup.py` (lines 314-327)
- `argumentation_analysis/orchestration/invoke_callables.py` (line 2244)
- `argumentation_analysis/orchestration/state_writers.py` (line 1022)
- `argumentation_analysis/orchestration/router.py` (lines 43, 76, 420)
- `argumentation_analysis/orchestration/workflows.py` (line 154)
- `tests/unit/argumentation_analysis/services/test_speech_transcription_service.py`
