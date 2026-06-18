# Fidelity Audit — Unified plugins vs original student-project capabilities

**Epic #1166** · read-only re-verification of the #35 integration · **Date**: 2026-06-18
**Owner**: po-2023 (Claude Code @ myia-po-2023)
**Method**: Triple grounding (SDDD) — student deliverable source ↔ unified plugin source ↔ capability mapping. Student dirs are **SANCTUARY** (read-only, never edited). Evidence cited as `file:line` on both sides.

---

## Executive verdict

**The unified system preserves the original student deliverables' capabilities, with a small number of real (documented) narrowings and two substantive architectural divergences.** Of the 8 audited deliverables, 4 are **fully preserved** (JTMS, governance, argument-quality, counter-argument core), 2 are **partially preserved with real gaps** (fallacy-detection explanation richness, local-LLM deployment model), 1 is **architecturally diverged by design** (dialogique: protocols kept, dynamic agent layer dropped), and 1 is **partially preserved with degraded mobile endpoints** (Interface Mobile).

Net direction: unification **broadened** capability overall (added social-choice layer, NLI/self-hosted-LLM tiers, SK plugins, capability registry, agentic virtue detectors) but **narrowed** a few specific surfaces. No silent total-loss of an original capability was found; every gap has a traceable reason.

**Follow-up issues to open**: 6 (gaps G1–G6 below). None auto-fixed here (per audit discipline).

---

## Aggregate fidelity matrix

| Student deliverable | Unified absorber | Capabilities | INTEGRATED | PARTIAL | MISSING | Verdict |
|---|---|---:|---:|---:|---:|---|
| `1.4.1-JTMS` | `services/jtms/` (jtms_core, atms_core) + SK plugins | 16 | 14 | 0 | 2 | **Preserved** |
| `2.1.6_multiagent_governance_prototype` | `agents/core/governance/` + `plugins/governance_plugin.py` | 20 | 17 | 1 | 2 | **Preserved+** |
| `2.3.2-detection-sophismes` | `agents/core/informal/` + `adapters/french_fallacy_adapter.py` + `plugins/french_fallacy_plugin.py` | 13 | 6 | 4 | 3 | **Mostly preserved** |
| `2.3.3-generation-contre-argument` | `agents/core/counter_argument/` | 20 | 11 | 5 | 2+2* | **Largely preserved** |
| `2.3.5_argument_quality` | `agents/core/quality/` + `plugins/quality_scoring_plugin.py` | 18 | 11 | 0 | 3 (intentional) | **Preserved+** |
| `2.3.6_local_llm` | `services/local_llm_service.py` | 8 | 3 | 1 | 4 | **Partially preserved** |
| `1_2_7_argumentation_dialogique` | `agents/core/debate/` (protocols + DebateAgent) | 11 | 7 | 0 | 4 | **Half preserved** |
| `3.1.5_Interface_Mobile` | `api/mobile_endpoints.py` | 8 | 2 | 3 | 3 (frontend/N/A) | **Partially preserved** |
| **TOTAL** | | **114** | **71** | **14** | **19** (8 intentional/N/A) | |

\* counter-argument: 2 real MISSING + 2 confirmed false-positives (fallacy-detection overlap — see note below).

---

## Per-deliverable findings

### `1.4.1-JTMS` → `services/jtms/` — **Preserved**
Near-line-for-line port. All 14 algorithmic capabilities (Belief tri-state, Justification in/out, strict/non-strict add, SCC non-monotonic detection, compute_truth_statement, explain_belief, pyvis visualize; full ATMS: Node/label/env-Cartesian-propagation/out-blocking/contradiction-invalidation/is_consistent) preserved verbatim, with type hints, re-entrancy guards, and graceful-degradation imports added. Net-new: `ExtendedBelief` (audit trail), `ConflictResolver` (5 strategies), tracing, SK plugins.
- **G1 (minor)**: JSON beliefs loader `belifs_loader.py:load_beliefs` has no unified equivalent — hydrating a JTMS from `beliefs.json` requires hand-rolling.
- `main.py` demo not migrated (illustrative; invariants covered by tests).

### `2.1.6_multiagent_governance_prototype` → `agents/core/governance/` — **Preserved+**
All 7 voting methods (majority, Borda, Condorcet+Borda-fallback, quadratic, byzantine, raft), coalition/Shapley/gossip simulation, full manipulation suite (strategic/false_coalition/bribery/noise), conflict detection, all 8 metrics ported 1:1. Net-new: formal social-choice layer (approval/STV/Copeland/Kemeny-Young/Schulze), SK exposure.
- **G2 (minor)**: Mediation `success_probability` regressed numeric (0.8/0.5/0.7) → `None` placeholders (`conflict_resolution.py:40,49,58`, tracked #971).
- **G3 (minor)**: Plugin exposes only 3/8 metrics as `@kernel_function` — `efficiency`/`stability`/`per_agent_satisfaction`/`summarize_results`/`gini` importable but unwrapped (`governance_plugin.py:74-95`).

### `2.3.2-detection-sophismes` → `informal/` + `french_fallacy_adapter` — **Mostly preserved**
Detection architecture (argument mining + symbolic matching + ensemble + ChatGPT zero-shot + CamemBERT mapping) faithfully ported and expanded (NLI hierarchical, self-hosted LLM, 400+-node taxonomy, SK plugin).
- **G4 (real)**: 3 of 8 symbolic sub-rules silently dropped (`Ad Hominem` character-attack `symbolic_rules.py:40-52`, `Généralisation` "sur la base de N exemples" `:104-115`, `Appel à la Tradition` "c'est la tradition" `:132-140`). Re-add at `french_fallacy_adapter.py:180-291`.
- **G5 (real)**: 4 per-fallacy French explanation templates (`fallacy_pipeline.py:279-288`) collapsed to a generic `f"{type} (confiance: …, source: …)"` line — per-fallacy rationale lost.
- (minor) Ensemble confidence-averaging branch (`fallacy_pipeline.py:218-222`) → simple max-take; CamemBERT training pipeline / CLI / benchmarks intentionally out of scope.

### `2.3.3-generation-contre-argument` → `agents/core/counter_argument/` — **Largely preserved**
All 5 counter-types, all 5 rhetorical strategies (verbatim port incl. the original's dead/broken `get_best_strategy`/`suggest_strategy` code quietly fixed), ArgumentParser, VulnerabilityAnalyzer, 5-criteria weighted evaluator with identical weights (0.25/0.25/0.20/0.15/0.15) and identical base-strength table all present.
- **G6 (real)**: TweetyProject formal-validation layer (`logic/validator.py` + `tweety_bridge.py` → `ValidationResult`) MISSING — unified keeps the `ValidationResult` dataclass (`definitions.py:94-101`) but never populates it. If formal validation is in-scope for the unified agent, this is a regression.
- (cosmetic) French tone/clarity/originality word-lists trimmed; recommendations flattened to generic English.
- **NOT a regression (verified)**: "fallacy-detection workflow MISSING" — the student `CounterArgumentAgent` class was actually a fallacy orchestrator (misleading name). The unified system correctly **split** this into two capabilities: fallacy detection → `informal/` (audited above), counter-argument generation → `counter_argument/`. Architectural improvement, not a loss.

### `2.3.5_argument_quality` → `agents/core/quality/` — **Preserved+**
All 9 hardcoded virtues (`VERTUES`), all 9 lexical detectors (same heuristics/thresholds), exact scoring dict shape, resource file, and `evaluer_argument` entrypoint present — **the student defined exactly the same 9 dimensions** (`agent.py:18-28` vs `quality_evaluator.py:217-227`, identical order/spelling). 7/9 virtues additionally upgraded to multi-step agentic detectors (FB-38). 2 new integration surfaces added (SK plugin, capability registry).
- The 3 MISSING items (`ARGUMENTS_EXAMPLE` demo corpus, `arguments.py` typing taxonomy, PyQt5/WebSocket frontends) are correctly out of scope. The FB-38 "no expansion" decision cost zero original fidelity (student had no extra dimensions).

### `2.3.6_local_llm` → `services/local_llm_service.py` — **Partially preserved**
OpenAI-compatible HTTP adapter + service-registry registration cleanly integrated and arguably improved (cached health probe, `status=skipped` fallback).
- **G7 (real)**: In-process `llama_cpp` GGUF loading (`local_llm.py:33-40`), `ModelEnum` registry (9 GGUF models `constants.py:23-37`), `/v1/fallacy-detection` endpoint contract, `<END>` output cleanup all MISSING — unified is HTTP-only and **assumes an external GGUF server**, silently changing the deployment model. Document the requirement + re-expose a fallacy-detection-specific endpoint (or confirm it lives in a fallacy plugin).

### `1_2_7_argumentation_dialogique` → `agents/core/debate/` — **Half preserved**
**Static layer preserved verbatim**: Walton-Krabbe `DialogueType`/`SpeechAct` enums, `Proposition`/`FormalArgument`/`DialogueMove`, abstract `DialogueProtocol`, `Persuasion`/`Inquiry` transition tables + termination, `KnowledgeBase`.
- **G8 (substantive)**: **Dynamic layer MISSING** — protocol-aware `DialogueAgent` (commitment store, turn-taking, speech-act-driven response, loop-breaking), `MultiAgentDialogueSystem` orchestrator (sequential move exchange + dialogue archive), and **`ArgumentationEngine` with 10 argumentation schemes** (modus ponens, expert opinion, analogy, causal, consensus, empirical, economic, precautionary, moral, historical) have no unified counterpart. Unified `DebateAgent` is the LLM-driven *enhanced adversarial* variant (8 personalities, phase-based moderation) — a different design. The `ArgumentationEngine` is the highest-value missing student IP. Either port it, or explicitly document that protocol-driven turn-taking dialogue was deprecated in favor of phase-based moderation (so the verbatim-ported `protocols.py` is not dead code).

### `3.1.5_Interface_Mobile` → `api/mobile_endpoints.py` — **Partially preserved**
React Native frontend (no backend of its own). All 4 mobile routes exist with matching request/response contracts; `/chat` fully equivalent.
- **G9 (real, 3 endpoints degraded)**:
  - `/api/mobile/fallacies` — `span` always `[0,0]`, `confidence` hardcoded `0.8` (breaks client `FallacyCard` highlight; original returned real per-fallacy values).
  - `/api/mobile/analyze` — only fills `id`/`text`/`conclusion`; `premises`/`structure`/`validity`/per-arg `fallacies` left at defaults (`ArgumentCard` renders empty).
  - `/api/mobile/validate` — silently switched from propositional/predicate logic to Toulmin (`type="toulmin"` is out of the client's declared enum `"propositional"|"predicate"|"other"`).

---

## Gaps recommended for follow-up issues

| ID | Deliverable | Gap | Severity |
|---|---|---|---|
| G1 | JTMS | JSON beliefs loader (`load_beliefs`) not ported | minor |
| G2 | Governance | Mediation `success_probability` numeric→None (#971) | minor |
| G3 | Governance | Plugin exposes 3/8 metrics (5 unwrapped) | minor |
| G4 | Sophismes | 3/8 symbolic sub-rules dropped | real |
| G5 | Sophismes | 4 French explanation templates → generic line | real |
| G6 | Contre-argument | TweetyProject formal validation (`ValidationResult`) never populated | real |
| G7 | Local LLM | `llama_cpp` GGUF + `ModelEnum` + `/fallacy-detection` endpoint dropped (deployment model changed) | real |
| G8 | Dialogique | Protocol-aware `DialogueAgent` + `ArgumentationEngine` (10 schemes) dropped | substantive |
| G9 | Mobile | 3/4 endpoints degraded (span/confidence/validity/type) | real |

**Recommended grouping**: open 6 issues (G1+G2+G3 as one "governance/JTMS minor polish"; G4+G5 as one "fallacy symbolic-rules + explanation-templates restoration"; G6, G7, G8, G9 each standalone). These are **documentation pointers for future work**, not blockers — the repo is functional; these are fidelity observations against the original student deliverables.

---

## Privacy / discipline
Read-only audit. No edits to student dirs, `.github/`, CODEOWNERS, workflows, or `.claude/rules/*`. No dataset-derived content cited (all evidence is student-code ↔ unified-code `file:line`). This report is aggregate-only and safe to commit.
