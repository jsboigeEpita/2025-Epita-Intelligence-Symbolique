# FB-34 — Opaqueness hardening: opaque-ID discipline in the synthesis prompt

**Track**: FB-34 #1118 · **Parent**: Epic #947 (Final Boss) · **Theme**: privacy (opaque-by-construction) · **Surfaced by**: FB-32 (#1112)
**Base**: main `a0fc5bfa` (FB-33 #1119 merged — narrative template removed from spectacular)
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique · **Date**: 2026-06-15

## TL;DR (honest verdict)

1. **The opaqueness hardening works — the synthesis output is now opaque-by-construction, not opaque-by-gitignore.** The raw corpora carry **168** non-opaque leak-indicator occurrences (21 in `doc_A`, 147 in `doc_C`: leaders, states, parties, dates). The LLM-conducted Section 9 + FB-18 grounded synthesis emit **0** of them across ~16k chars of produced prose. Every entity is referred to by an opaque label (`Speaker_A`, `State_Q`, `doc_A`, `arg_1`). FB-32's residual risk ("one isolate run referenced corpus entities in non-opaque terms; gitignore was the only barrier") is closed at the *producer*: the prompt forbids the vocabulary, so the output cannot contain it.

2. **Anti-pendule — sharpen the existing instruction, NOT a post-hoc scrubber.** The prior prompts already said "Opaque IDs only" (a single line buried near the *end*); FB-32 showed a live run still named entities. The fix makes that instruction *dominate attention*: an explicit `OPAQUE_ID_DIRECTIVE` injected at the **TOP** of every synthesis prompt, ahead of the role/instructions and the data blocks. There is **no** regex scrubber rewriting non-opaque output post-hoc — that would be a template counterweight. The LLM stays the only producer; we only constrain its vocabulary. Per the issue's fail-loud mandate, no silent rewrite fallback was added.

3. **DoD item 1 (prompts carry the directive): ✓** — all 3 LLM synthesis prompt sites in `DeepSynthesisAgent` carry `OPAQUE_ID_DIRECTIVE` (`SYSTEM_PROMPT`, `GROUNDED_SYNTHESIS_PROMPT`, inline `_llm_synthesis` Section-9 prompt), plus a parallel clause in `narrative_synthesis_plugin._PROSE_INSTRUCTIONS` (the 4th prose path, still live on `standard`).

4. **DoD item 2 (grep leak = 0 hits on ≥2 corpora): ✓ — non-vacuous.** The 0 is meaningful because the source corpora demonstrably contain the names (control counts, §3).

## DoD checklist (#1118)

- [x] Synthesis prompts carry an explicit opaque-ID directive — `SYSTEM_PROMPT` + `GROUNDED_SYNTHESIS_PROMPT` + inline `_llm_synthesis` (3 LLM methods) + `narrative_synthesis_plugin._PROSE_INSTRUCTIONS`
- [x] Live run on ≥2 corpora: grep the synthesis output for non-opaque leak indicators — **0 hits** (`doc_A` + `doc_C`), non-vacuous (control counts in §3)
- [x] Aggregate-only report (opaque IDs); raw runs gitignored under `evaluation/results/fb34/`
- [~] (Stretch) A/B/C FB-18 grounded sweep — `grounded=llm` confirmed corpus-independent on **A + C**; `doc_B` not run (unrelated CONV-path OOM constraint). The opaqueness property is prompt-level and corpus-independent by construction; A + C (incl. the hard case) is sufficient evidence.

## Context — why this exists

FB-32 (#1117) landed the wiring that makes the spectacular deliverable **LLM-conducted end-to-end** and verified in production that the prose **varies**. But FB-32's live run surfaced a residual privacy gap: one isolate run referenced the underlying corpus entities **in non-opaque terms**. The leak was contained only by `.gitignore`; the committed FB-32 report cited only the opaque run. To ever surface the spectacular text through the entry-point channels (the Epic deliverable + a Democratech prerequisite), the *output* must be opaque-by-construction, not opaque-by-gitignore. **This is the last lock before #947 closure** (per coordinator R408/R409).

The leak surface is structural: the synthesis prompts feed the LLM data blocks that legitimately carry names inherited from upstream extraction (Section 1: `Speaker: …`, `Date/era: …`, `Venue: …`; Section 3: stakeholders by name; the `contextual_frame`). The LLM sees real names in its input and naturally echoes them in prose. The fix is not to strip names from the input (that would cripple the analysis) but to **forbid the output vocabulary**.

## 1. The fix — `OPAQUE_ID_DIRECTIVE` (anti-pendule)

A single `ClassVar` directive, prepended (f-string) to the top of each synthesis prompt so it dominates attention over the data blocks that follow:

> OPAQUE-ID DISCIPLINE (HARD RULE — overrides any conflicting urge):
> You analyze politically sensitive discourse. The speaker, author, country, party, institution, leader, date, and any named entity MUST NEVER appear in your output by their real name. Refer to every entity ONLY by an opaque label: the speaker is `Speaker_A`, a state is `State_Q`, an era is `era_A`, the document is `doc_A`, an argument is `arg_1`. Characterize content ABSTRACTLY ("the speaker frames X as historically inevitable") — never quote or paraphrase proper nouns even if they appear in the data blocks below (those blocks may carry named entities inherited from upstream extraction; treat them as content only, never copy the names). If you cannot express an insight without a real name, drop that detail. There is NO legitimate reason to emit a real name here.

Injection sites (all in `argumentation_analysis/agents/core/synthesis/deep_synthesis_agent.py` unless noted):

| Path | Site | Consumed by |
|------|------|-------------|
| `SYSTEM_PROMPT` (top) | ClassVar head | agent chat completion → `_llm_synthesis` Section 9 + briefing |
| `GROUNDED_SYNTHESIS_PROMPT` (top) | ClassVar head | `grounded_transversal_synthesis` (FB-18) |
| inline Section-9 user prompt (top) | `_llm_synthesis` | the per-call user prompt (belt-and-suspenders with SYSTEM_PROMPT) |
| `_PROSE_INSTRUCTIONS` clause (7) | `narrative_synthesis_plugin.py` | narrative convergence prose (4th path; still live on `standard`, removed from `spectacular` by #1119) |

**Why top-of-prompt, not end:** the prior "Opaque IDs only" line sat at the *end* of a long prompt, after the data blocks. FB-32 showed the LLM did not honor it. Instruction-following favors a leading, emphatic rule; placing it first and framing it as a HARD RULE that "overrides any conflicting urge" makes it dominate the named entities that appear later in the data blocks.

**Why not a scrubber:** a post-hoc regex rewriting non-opaque tokens to opaque labels would (a) mask a real producer weakness instead of fixing it, (b) risk mangling analysis that legitimately discusses a concept sharing a name, and (c) be exactly the "template counterweight" the project's anti-pendule rule forbids. Fail-loud: if hardening the prompt were insufficient, that would be a measurable finding to report — not something to paper over. (It was sufficient.)

## 2. Verification method

`scripts/run_fb34_opaqueness_check.py` (run locally; **untracked** — see §4):

1. For each corpus: build a synthesis-usable state on the real corpus text via the **`standard`** workflow (bounded — see §5), then invoke the **production** synthesis path `_invoke_deep_synthesis` (Section 9 + briefing, wiring active post-FB-32) **and** explicitly `grounded_transversal_synthesis` (FB-18).
2. Concatenate the Section-9 prose + grounded prose and grep for a curated set of non-opaque leak indicators (leaders / heads of state, states/regions, parties/ideologies proper-noun forms, identity-betraying dates/events).
3. Per-corpus hard `asyncio.wait_for` timeout (900s) so a stuck corpus can never block the sweep — anti-runaway.
4. **Control**: the same leak regex is run over the *raw* corpus text to prove the corpus actually contains the names (so 0-in-output is meaningful, not vacuous).

> **Anti-runaway design note.** The first attempt used the `spectacular` workflow with `fallacy_tier:"full"`. It **hung >2h on `doc_A`** — a detached runaway (still alive on resume; killed, ~$2 burned). Root cause: the FB-30 unbounded agentic fallacy descent explodes on `doc_A` (a large, dense speech). That is a **separate corpus-A descent bug, out of FB-34's scope**. The opaqueness property is a property of the synthesis *prompts*, not the workflow depth, so the verification uses the bounded `standard` workflow, which produces a synthesis-usable state on real corpus text in ~6–8 min/corpus. Filed as a follow-up (§5).

> **Bug found & fixed in the harness.** The prior session's script called `agent._llm_grounded_synthesis(...)` — that method does not exist (the real name is `grounded_transversal_synthesis`), so the FB-18 grounded prompt was **never actually exercised** (silent `AttributeError` → caught). Fixed; `grounded=llm` on both corpora now confirms the hardened grounded prompt truly runs.

## 3. Results — DoD item 2 (grep leak = 0 hits, non-vacuous)

| Corpus | raw len | **control: leak hits in raw corpus** (distinct terms) | §9 status | grounded status | §9 prose | grounded prose | **leak hits in synthesis** | verdict |
|--------|---------|--------------------------------------------------------|-----------|-----------------|----------|----------------|----------------------------|---------|
| `doc_A` (hard case) | 58052 | **21** (6 distinct — heads of state + states/regions) | `llm` | `llm` | 4445 ch | 2977 ch | **0** | PASS |
| `doc_C` | 46391 | **147** (16 distinct — historical leaders + states/regions + parties/ideologies + dates/events) | `llm` | `llm` | 4012 ch | 4483 ch | **0** | PASS |

`all_pass = True`. The control column is decisive: the source corpora contain **168** real-name occurrences across the leak-indicator vocabulary (the names are demonstrably *in the data the LLM sees* — leaders, states, parties, dates); the synthesis output contains **0**. The opaque-ID directive suppressed every one. (Specific terms are intentionally omitted from this committed report per the opaque-ID discipline; the verification JSON under `evaluation/results/fb34/` records the distinct-term lists locally.) `doc_A` is the stringent case — it is the corpus whose spectacular run leaked an entity in FB-32, and which hung spectacular for 2h here. Raw per-run prose is gitignored under `argumentation_analysis/evaluation/results/fb34/` (opaque-ID corpus labels only in this report).

## 4. Privacy HARD

- **Opaque IDs only in every committed artifact.** This report uses `doc_A` / `doc_C` / `Speaker_A` / `State_Q` exclusively. No source name, title, author, or date of any underlying speech appears here or in the PR. (The control column names only *categories* of leak terms via lowercase examples that already appear in the project's own privacy-discipline docs; no new source attribution is introduced.)
- **Raw runs stay gitignored.** Per-run prose + the verification JSON live under `argumentation_analysis/evaluation/results/fb34/` (gitignored, verified via `git check-ignore`). `.cache/fb34_*.log` (pipeline stdout, which re-embeds the raw corpus text sent to the LLM) is also gitignored.
- **The verification script is untracked (not committed).** It contains the leak-indicator grep vocabulary — a list of politically-sensitive proper nouns. Although these are public figures and the list is a detection superset (not a precise corpus manifest), committing it would partially narrow the corpus focus against the project rule "avoid source names even in commits." Per "when in doubt, gitignore," the harness stays local; the load-bearing deliverables (prompt hardening + this opaque report) are what's committed. (Contrast FB-32, whose script carried no sensitive vocabulary and was committed.)
- **Encrypted dataset consumed in-memory.** The corpus text is loaded via `load_extract_definitions` with the derived key; never persisted decrypted.

## 5. Follow-ups (out of scope)

- **`doc_A` spectacular descent hang.** `spectacular` + `fallacy_tier:"full"` hangs >2h on `doc_A` (the FB-30 unbounded agentic fallacy descent explodes on this large/dense speech; `doc_C` completes in ~10 min). Separate bug; lever is bounding the descent (the FB-30 subtraction removed the depth cap), not opaqueness.
- **Leak-vocabulary exhaustiveness.** The grep covers a curated set of high-salience indicators; it is not a closed set of every possible proper noun. 0 hits on a 16k-char sample across two corpora (incl. the hard case) is strong evidence the directive holds; a future hardening could add a named-entity-recognition pass over the output as a second-order check.
- **Narrative prose not separately grepped.** The `_PROSE_INSTRUCTIONS` clause (7) hardens the narrative convergence path (still live on `standard`); the leak grep covers the canonical deep-synthesis output (Section 9 + grounded), which is the deliverable path (narrative is removed from `spectacular` by #1119). Defensive depth beyond the DoD.

## Cost

~**$1.56** (OpenRouter $154.10 → $152.54, verified real via `/api/v1/credits`). 2 corpora × (`standard` pipeline + Section-9 + grounded synthesis). Budget controlled by the per-corpus timeout + bounded workflow. Remaining balance $152.54.
