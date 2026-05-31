# Audit A-17: CaseAI / Moriarty

**Issue**: N/A | **SUIVI**: Score 50% | **Date audit**: 2026-05-31

## Status: 🟡 Partial

The Oracle/Moriarty paradigm is deeply integrated into the agent hierarchy, but the visual frontend (Phaser.js game) and Slack bot remain standalone in `CaseAI/` with no connection to the core pipeline.

## What was delivered (student source)

- `CaseAI/` — Slack bot frontend with interactive Cluedo game
- Phaser.js game — Visual detective game interface (14 JavaScript files)
- Oracle/Moriarty agent paradigm for the Cluedo investigation game
- Cluedo dataset for the Sherlock-Watson investigation workflow

## What exists in `argumentation_analysis/`

| Layer | File | Detail |
|---|---|---|
| Oracle base | `agents/core/oracle/oracle_base_agent.py` | `OracleBaseAgent` — base class for oracle-type agents |
| Moriarty agent | `agents/core/oracle/moriarty_interrogator_agent.py` | `MoriartyInterrogatorAgent` + `MoriartyTools` |
| Dataset | `agents/core/oracle/cluedo_dataset.py` | Cluedo dataset with card/character/room data |
| Dataset manager | `agents/core/oracle/dataset_access_manager.py` | Dataset access and permission control |
| Hypothesis tracker | `agents/core/oracle/hypothesis_tracker.py` | Hypothesis management for investigation |
| Permissions | `agents/core/oracle/permissions.py` | Agent permission system |
| Error handling | `agents/core/oracle/error_handling.py` | Oracle-specific error types |
| Interfaces | `agents/core/oracle/interfaces.py` | Abstract interfaces |
| Phase D extensions | `agents/core/oracle/phase_d_extensions.py` | Extended investigation phases |

## What exists standalone in `CaseAI/`

| Component | File(s) | Detail |
|---|---|---|
| Slack bot backend | `CaseAI/static/scripts/back.js` | Slack integration backend |
| Phaser.js game engine | `CaseAI/static/scripts/game.js` | Visual Cluedo game |
| Game map | `CaseAI/static/scripts/map.js` | Game board rendering |
| Canvas rendering | `CaseAI/static/scripts/canvas.js` | Canvas-based graphics |
| UI floating elements | `CaseAI/static/scripts/floating.js` | Floating UI components |
| Testimony system | `CaseAI/static/scripts/testimony.js` | Witness testimony interface |
| Note system | `CaseAI/static/scripts/note.js` | Player notebook |
| Sound system | `CaseAI/static/scripts/sound.js` | Audio playback |
| Settings | `CaseAI/static/scripts/settings.js` | Game settings |
| View management | `CaseAI/static/scripts/view.js` | View/navigation controller |
| Prompt system | `CaseAI/static/scripts/prompt.js` | AI prompt interface |
| Picture assets | `CaseAI/static/scripts/picture.js` | Image handling |
| Global state | `CaseAI/static/scripts/globals.js` | Shared game state |
| Index | `CaseAI/static/scripts/index.js` | Entry point |

## Preservation Assessment

- Moriarty agent logic: **PRESENT** — `MoriartyInterrogatorAgent(OracleBaseAgent)` with full Cluedo strategy
- Moriarty tools: **PRESENT** — `MoriartyTools` with `validate_cluedo_suggestion`, `reveal_card_if_owned`, `provide_game_clue`, `simulate_other_player_response`
- Cluedo dataset: **PRESENT** — Complete dataset with cards, characters, rooms
- Agent hierarchy: **PRESENT** — Inherits from `OracleBaseAgent`, compatible with SK `AgentGroupChat`
- Investigation tracking: **PRESENT** — Hypothesis tracker, permissions, error handling
- Visual game: **STANDALONE** — Phaser.js game in `CaseAI/` has no API connection to Moriarty agent
- Slack bot: **STANDALONE** — No webhook or message bridge between Slack bot and `argumentation_analysis/`

## Gap Analysis

1. **CaseAI/ is completely standalone** — The 14 JavaScript files in `CaseAI/static/scripts/` have no API client connecting to the Moriarty agent endpoints. The visual game cannot interact with the AI agent.

2. **No WebSocket bridge** — The Phaser.js game would need a WebSocket or REST bridge to communicate with the Moriarty agent in real-time. None exists.

3. **Slack bot disconnected** — The Slack bot frontend has no message routing to the `MoriartyInterrogatorAgent`. It operates independently.

4. **No unified Cluedo API** — There is no REST endpoint that exposes the Moriarty agent's game state to an external frontend. The agent is only accessible through the SK agent group chat mechanism.

5. **50% is accurate** — The backend (agent + dataset + tools) is fully integrated (~50% of the project). The frontend (game + Slack) is completely disconnected (~50% of the project).

## Recommended Action

**Low-medium priority.** The backend is solid; the gap is frontend integration.

1. **Short-term**: Document that `CaseAI/` is a standalone demo/prototype, not connected to the live agent. Add a README to `CaseAI/` explaining this.
2. **Medium-term**: Add a `/api/cluedo/` REST/WebSocket endpoint that bridges the Moriarty agent to external frontends. This would allow the Phaser.js game to call the agent.
3. **Alternative**: Archive `CaseAI/` to `docs/archives/` if the visual game is not intended for production use, and focus on the Moriarty agent's integration in the Sherlock-Watson workflow.

## Source Files

- `argumentation_analysis/agents/core/oracle/oracle_base_agent.py`
- `argumentation_analysis/agents/core/oracle/moriarty_interrogator_agent.py`
- `argumentation_analysis/agents/core/oracle/cluedo_dataset.py`
- `argumentation_analysis/agents/core/oracle/dataset_access_manager.py`
- `argumentation_analysis/agents/core/oracle/hypothesis_tracker.py`
- `argumentation_analysis/agents/core/oracle/permissions.py`
- `argumentation_analysis/agents/core/oracle/error_handling.py`
- `argumentation_analysis/agents/core/oracle/interfaces.py`
- `argumentation_analysis/agents/core/oracle/phase_d_extensions.py`
- `CaseAI/static/scripts/` (14 JavaScript files)
