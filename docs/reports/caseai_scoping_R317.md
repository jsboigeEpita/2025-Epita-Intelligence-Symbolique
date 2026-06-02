# CaseAI Scoping Report — R317

**Date**: 2026-06-02
**Author**: po-2023 (worker, non-argparse lane)
**Source**: Issue #901, North-Star parametric integration (#78)

---

## 1. What is CaseAI?

CaseAI is a **Medieval Murder Mystery Detective Game** — a single-page browser application built with Phaser.js 3. The player investigates a procedurally-generated crime in a medieval smithy, questions suspects (powered by OpenAI gpt-4o), gathers alibi/observation notes, and uses a tau-prolog Watson deduction system to identify the liar.

### Architecture

| Component | Technology | Role |
|-----------|-----------|------|
| Game engine | Phaser.js 3 (CDN) | 2D rendering, sprite physics, room navigation |
| Logic engine | tau-prolog 0.3.2 (CDN) | Watson deduction (`liar(Person) :- alibi(P,R1), observed(P,R2), R1 \= R2`) |
| LLM | OpenAI gpt-4o (direct API) | Plot generation, suspect dialogue, fact extraction |
| Audio | Web Audio API | Ambient music, sound effects |
| Assets | Custom fonts, character sprites, map backgrounds | Medieval visual theme |

### Files (31 files, ~180 KB total)

```
CaseAI/
├── index.html           # SPA entry point, loads all scripts via CDN
├── smithy.json          # Level geometry (9 rooms, collision data)
├── favicon.ico
├── static/
│   ├── assets/medieval/smithy/   # 2 map backgrounds (day/night)
│   ├── fonts/                    # 3 custom fonts (BarberChop, JMH Typewriter, WaHandwriting)
│   ├── scripts/                  # 14 JS files (game logic)
│   ├── sounds/                   # 7 audio files (music, SFX)
│   └── style/style.css          # Styling
```

### Game Flow

1. **Init**: User enters OpenAI API key → `generatePlot()` creates random seed → `createPlot()` asks gpt-4o to flesh out scenario
2. **Questioning**: Click suspect on map → type question → `ask()` sends to gpt-4o with suspect-specific prompt → `createMapper()` extracts structured facts → notes appear
3. **Deduction**: After each question, `watsonHasFound()` runs Prolog query against extracted alibi/observation facts
4. **Accusation**: Click "YOU are the murderer!" → compare with `backend.plot.solution.murderer` → show Watson explanation

---

## 2. Integration Status

### Current Wiring: ZERO

| Aspect | Status |
|--------|--------|
| References in `argumentation_analysis/` | **0** (confirmed by grep) |
| REST/WebSocket to Python backend | **None** |
| CapabilityRegistry entry | **None** |
| WorkflowDSL phase | **None** |
| CLI integration | **None** |

### Backend Equivalents Already Integrated

The Cluedo/Oracle system in `argumentation_analysis/` covers the same conceptual ground:

| CaseAI concept | Integrated equivalent | File |
|----------------|----------------------|------|
| Suspect questioning | `MoriartyInterrogatorAgent` | `agents/core/oracle/moriarty_interrogator_agent.py` |
| Cluedo dataset | `CluedoDataset` (634 LOC) | `agents/core/oracle/cluedo_dataset.py` |
| Game state | `CluedoOracleState` (1708 LOC) | `core/cluedo_oracle_state.py` |
| 3-agent workflow | `CluedoExtendedOrchestrator` | `orchestration/cluedo_components/` |
| Pipeline mode | `--mode cluedo` | `run_orchestration.py` |
| Prolog deduction | Tweety/JPype (Java) | `agents/core/logic/` |

**Audit A-17 verdict**: 50% integration score. Backend = fully integrated. Frontend = orphaned.

---

## 3. Integration Options

### Option A: API Bridge (Medium effort, ~300 LOC)

Replace direct OpenAI calls in `back.js` with calls to the project's FastAPI backend:

- **Endpoint**: `POST /api/v1/cluedo/investigate` (new route in `api/main.py`)
- **Replace**: `chatAIHistory()` / `chatAIPrompt()` → HTTP fetch to FastAPI
- **Benefits**: Uses `MoriartyInterrogatorAgent` (strategic lying) instead of flat gpt-4o prompts; uses `CluedoOracleState` for consistent game state
- **SANCTUAIRE**: Only add code in `argumentation_analysis/` + `api/`. CaseAI/ untouched.

### Option B: Capability Exposure (Low effort, ~80 LOC)

Register CaseAI as a **frontend capability** in the registry, making it discoverable:

- Add `caseai_frontend` capability to `CapabilityRegistry` (metadata-only)
- Add a FastAPI route that serves CaseAI's `index.html` with injected API endpoint
- **Benefits**: CaseAI appears in the capability catalog, can be launched via API
- **Limitation**: Still uses direct OpenAI calls, no backend integration

### Option C: Documentation Only (Minimal effort, ~0 LOC)

Mark CaseAI as a **pedagogical reference frontend** — valuable for demonstrations but architecturally separate. No code changes.

- Update `parametric_integration_map.md` §D with "FRONTEND REFERENCE — not a backend candidate"
- Add CaseAI to the project docs as a demo showcase
- **Benefits**: Honest scoping, no wasted effort on forced integration

---

## 4. GO/NO-GO Verdict

### **GO for Option C (Documentation Only)**

**Rationale**:

1. **Orphan architecture**: CaseAI has zero imports, zero API calls, zero runtime connection to `argumentation_analysis/`. Bridging would require rewriting `back.js` to call FastAPI instead of OpenAI — a fundamental rearchitecture of the frontend.

2. **Backend already integrated**: The Cluedo game logic (dataset, state, agents, orchestrator) is already fully wired into the unified pipeline via `--mode cluedo`. CaseAI's frontend adds visual/gameplay value but no analytical capability.

3. **Pedagogical value**: CaseAI is an excellent demo for soutenances — a tangible, visual murder mystery game. It should be preserved as-is and showcased, not refactored to call a different backend.

4. **Cost/benefit**: Option A (API bridge) would take ~300 LOC + significant frontend rewrite for marginal analytical gain. Option B (capability exposure) adds metadata without real integration. Option C is honest and zero-cost.

5. **SANCTUAIRE**: CaseAI is a student project directory. The integration mandate (North-Star R311) says "every non-obsolete component becomes selectable" — but CaseAI is a **frontend visualization**, not a backend component. It doesn't belong in the pipeline; it belongs in demos.

### Recommendation

- **Mark §D of parametric_integration_map.md**: `CaseAI → FRONTEND REFERENCE (pedagogical demo, not pipeline candidate)`
- **Add to `examples/` documentation**: Reference CaseAI as a visual Cluedo demo
- **No code changes** in `argumentation_analysis/` or `CaseAI/`

---

## 5. Dependencies

| Dependency | Version | CDN | Required |
|-----------|---------|-----|----------|
| Phaser.js | 3.x (latest) | jsdelivr | Yes |
| tau-prolog | 0.3.2 | jsdelivr | Yes |
| OpenAI API | gpt-4o | Direct | Yes (user key) |

No Python dependencies. No npm. No build step. Fully static.

---

## Appendix: File Analysis

| File | LOC (est.) | Role |
|------|-----------|------|
| `index.html` | 50 | SPA shell, CDN imports |
| `smithy.json` | 120 | Level geometry |
| `back.js` | 500 | Core backend: API calls, plot gen, Prolog |
| `prompt.js` | 200 | LLM prompt templates |
| `globals.js` | 150 | Game state singleton |
| `game.js` | 180 | Newspaper, play button |
| `view.js` | 120 | View switching |
| `testimony.js` | 150 | Suspect questioning UI |
| `canvas.js` | 100 | Phaser scene init |
| `map.js` | 80 | Wall collision data |
| `floating.js` | 70 | Draggable notes |
| `picture.js` | 60 | Suspect portraits |
| `note.js` | 80 | Note creation |
| `sound.js` | 50 | Audio management |
| `settings.js` | 40 | API key input |
| `style.css` | 200 | Styling |
| **Total JS** | **~1980** | |
