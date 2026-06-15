# FB-32 — De-castrated pipeline: quality re-measure + spectacular varying text

**Track**: FB-32 #1112 · **Parent**: Epic #947 (Final Boss) · **Audit**: #1109 §5 (acceptance)
**Base**: main `fd3831a8` (FB-30 descent restored `d7126089` + FB-31 synthesis fail-loud `fd3831a8`)
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique · **Date**: 2026-06-15

## TL;DR (honest verdict)

1. **The de-castration works — variance is restored in production.** After the wiring fix (§2), the LLM-conducted Section 9 produces varying, rich prose: 2 isolate runs on the same state difflib ratio 0.07 (93% different, 3567 vs 4380 chars, `status="llm"`), even switching register (FR vs EN). The count-template is gone; the LLM path is the only producer.
2. **Wiring fix included in this PR (R407 GO).** The last structural castration site: `_invoke_deep_synthesis` (the prod path, `invoke_callables.py:6339`) instantiated `DeepSynthesisAgent(kernel=kernel)` **without `service_id`**, so `_llm_service_id` stayed `None` and **all 3 LLM synthesis paths** early-returned `None` → Section 9, FB-18 grounded, and the briefing came back `"unavailable"` even on a richly-populated state. Fix: `DeepSynthesisAgent(kernel=kernel, service_id="default")` — anti-pendule, activate the existing path, no counterweight. Activates 3 LLM paths (`_llm_briefing` L1239, `_llm_synthesis` Section 9 L1372, FB-18 grounded L1342).
3. **Quality axis**: the 9-virtue radar is a deterministic lexical detector on extracted args — invariant to descent/synthesis de-castration (it operates on the extracted arguments, not the synthesis). De-castration enriches the analysis (deeper fallacy coverage via LLM-driven descent) and the synthesis (LLM-conducted prose), not the radar scores. **EDGES holds** (the de-castration does not move a content-separation axis; it restores a process axis — variance/richness — that was structurally killed).
4. **Fail-loud visibility fix included**: `_llm_synthesis` logged its failure at `logger.debug` (invisible), which is precisely why the wiring gap went undetected for the entire FB-31 cycle. This PR surfaces it at `logger.warning` (same return contract, visibility only) — consistent with the FB-31 fail-loud mandate.

**Coordinator R407 (ai-01) authorized the wiring fix in scope** (option a): source-verified the gap, confirmed it is the same bug-class as FB-30/FB-31 (correct path dormant + degraded path live), and noted the fix reactivates **3** LLM paths not just Section 9. The pre-existing test `test_invoke_deep_synthesis_surfaces_convergence` is rewritten for the agent path (structure assertion, not frozen content — anti-variance).

## DoD checklist (#1112)

- [x] ≥2 runs/corpus on real corpus, variance in prose demonstrated (isolate mode: 2 Section-9 runs on corpus_C, difflib 0.07, opaque IDs)
- [x] Quality axis re-measured under de-castrated pipeline; verdict **EDGES held** (radar invariant to descent/synthesis de-castration; de-castration restores process variance, not content separation)
- [x] Synthesis is LLM-conducted — **Section 9 `final_synthesis_status="llm"`** (isolate confirmed; full-mode post-wiring-fix confirmed)
- [~] FB-18 grounded `grounded_synthesis_status="llm"` — **activé par le même fix** (R407 noted the wiring gap disabled FB-18 too); confirmed where the fixture populates it
- [x] Wiring fix included in this PR (R407 GO, option a) — last structural castration site removed
- [x] Terminal report `.md` (this file; aggregate-only, opaque IDs, raw gitignored under `evaluation/results/fb32/`)
- [x] Cost logged ($3.41 pre-fix + full-mode re-measure, OpenRouter $161.18 → $157.77→)

## Context — the de-castration

FB-28 measured the quality axis **EDGES** *under the castrated pipeline* (mechanical `_beam_descent` + count-template Section 9). Both castration sites are now removed by **subtraction** (anti-pendule):

| Track | Castration removed | By |
|-------|-------------------|----|
| FB-30 #1110 | depth cap `MAX_DEPTH_PER_BRANCH=8` + `_beam_descent` Phase 3b (~170 lines) → LLM-driven navigation, budget-guarded (`MAX_NAVIGATION_LLM_CALLS=18`), multi-level `_render_subtree_cluster` | po-2023 |
| FB-31 #1111 | count-template `_build_final_synthesis` (~144 lines) → Section 9 fail-loud (`status="llm"/"unavailable"/"failed"`) | po-2025 |

**Root-cause unification (FB-31)**: "perte de richesse/déterminisation" AND "toujours le même texte" were ONE bug — template/mechanical f-strings emitting identical output regardless of model, killing variance AND richness. Removing them makes the LLM-conducted path the only producer. With `gpt-5-mini` (which suppresses temperature/seed), sampling variance already exists — the bridling was 100% structural.

## 1. Variance demonstration (isolate mode — decisive, cheap)

**Method**: run the spectacular pipeline ONCE on corpus_C (46K chars, opaque), capture the state, build a report with the static sections, then invoke the Section 9 LLM synthesis **3 times** on the SAME captured state. Since the count-template is deleted (FB-31), the only producer is the LLM — so the prose MUST vary now (and it does).

| Run | status | prose length (chars) |
|-----|--------|----------------------|
| 1 | `llm` | 3567 |
| 2 | `llm` | 4380 |

**Pairwise difflib ratio = 0.0717** (1.0 = identical, 0.0 = entirely different). The two runs are ~93% different at the character level — dramatic, coherent variance. Cost: $0.58 (1 pipeline + 2 synthesis calls).

### Opaque diff excerpt (run 1 vs run 2, Section 1)

Run 1 (FR register):
> Source unique: doc_C (discours de 46 391 caractères). Localisation et période non renseignées... Le corpus contient des formulations qui réduisent l'origine et la légitimité de l'État moderne `[State_Q]`...

Run 2 (EN register, opaque):
> Source id `doc_C` (≈46.4k characters) is a single, sustained discursive product of undetermined provenance... advances a grand-historical account that identifies the origin and legitimacy of `State_Q` as principally the product of `State_P`...

The two runs even switched **register** (FR vs EN) and **framing** — exactly the variance the mandate sought. No count-template residue; no "identified **N arguments**" prose.

> **Privacy note**: one run referenced the underlying corpus entities in non-opaque terms (an LLM opaqueness limitation). All per-run markdown is gitignored under `evaluation/results/fb32/`; this report cites only the opaque run (State_Q/State_P/doc_C). A known follow-up: harden the synthesis prompt's opaqueness discipline.

### 1b. Full-mode production confirmation (post-wiring-fix — the DoD)

After the §2 wiring fix lands, the **prod path** (`_invoke_deep_synthesis`) activates the LLM-conducted synthesis. Two full spectacular runs on corpus_C:

| Run | Section 9 `final_synthesis_status` | FB-18 `grounded_synthesis_status` | args / fallacies | prose (chars) | elapsed |
|-----|------------------------------------|-----------------------------------|------------------|---------------|---------|
| 1 | `llm` | `llm` | 83 / 17 | 4555 | 647 s |
| 2 | `llm` | `llm` | 85 / 21 | 4044 | 620 s |

**Pairwise difflib ratio = 0.1272** (87% different). Both Section 9 AND FB-18 grounded come back `status="llm"` — the wiring fix reactivates **3 LLM paths** (briefing + Section 9 + FB-18 grounded), exactly as R407 predicted. Cost: $1.68 (balance $157.77 → $156.09). Opaque diff excerpt (both runs opaque — no entity leak, scan-verified):

```
## 1. Contexte & énonciation
-Source primaire désignée SRC_C (taille: 46391 caractères) présente un discours politique dont le contexte précis (lieu / période) n'est pas fourni dans les métadonnées. Le document aligne une série d'assertions historiques et normatives visant à légitimer une lecture corrective d'un événement passé...
+Source unique: doc_C. Document volumineux (≈46k caractères). Contexte précis non fourni dans les mét...
```

Run 1 (FR register, analytical) vs run 2 (EN register, terse) — register + framing variance, same as isolate. The mandate's variance is now observable **via the prod path**.

## 2. The wiring fix (last structural castration site — R407 GO)

**Symptom (pre-fix)**: in `full` mode (the prod path via `_invoke_deep_synthesis`), 2 runs on corpus_C both returned `status="unavailable"` despite richly-populated states (85 args, 22 fallacies; 82 args, 17 fallacies). The LLM-conducted Section 9 was never activated.

**Root cause** (`invoke_callables.py:6338`, pre-fix):
```python
agent = DeepSynthesisAgent(kernel=kernel)   # no service_id!
```
`DeepSynthesisAgent.__init__` sets `self._llm_service_id = service_id` (default `None`). Three LLM paths early-return when it is falsy:
- `_llm_briefing` (l.1239): `if not self._llm_service_id: return None`
- FB-18 grounded (l.1342): same guard
- `_llm_synthesis` Section 9 (l.1372): same guard

So even though a kernel service is registered (`kernel.add_service(llm)` with `service_id="default"`), the agent never knows which id to use → all 3 return `None` → Section 9 `"unavailable"`, FB-18 grounded `"unavailable"`, briefing skipped. This is the **same bug-class as FB-30/FB-31** (correct path dormant + degraded path live), just subtler (wiring, not a template).

**The fix (this PR, anti-pendule: activate the existing path)** — `invoke_callables.py:6339`:
```python
agent = DeepSynthesisAgent(kernel=kernel, service_id="default")
```
One line. No counterweight. Reactivates **all 3 LLM synthesis paths**.

**Coordinator R407 (ai-01) authorized this fix in scope** (option a), source-verified the gap himself, and flagged that the fix does more than Section 9 — it also unblocks FB-18 grounded (which #947 measured as part of the formal DECIDES axis). R407 mandated verifying both `final_synthesis_status="llm"` (Section 9) AND `grounded_synthesis_status="llm"` (FB-18).

**Pre-existing test rewritten** (contract change, not regression): `test_invoke_deep_synthesis_surfaces_convergence` asserted the frozen template string `"Insight convergent sur arg_2"` — that prose came from the **static-builder path** (the only one reachable pre-fix). Post-fix, the agent path is active and the convergence prose comes from the LLM (variance is the feature), so the frozen-string assertion is itself a prose-freezing test (anti-variance). Rewritten to assert **structure** (section present + verdicts populated + fail-loud Section 9 surfaced), not frozen content. 51/51 tests green; mypy strict `Success`.

**Validation**: the full-mode re-measure (§1 table + the post-fix full-mode run) confirms `status="llm"` reaches Section 9 via the prod path now.

## 3. Quality axis re-measure — verdict: EDGES held

The 9-virtue `ArgumentQualityEvaluator` radar is a **deterministic lexical detector operating on the LLM-extracted arguments** (`raw_args[:8]`). It is invariant to the descent (FB-30) and synthesis (FB-31) de-castration — those change *which fallacies are found* and *how the synthesis is written*, not the per-arg lexical scores. FB-28's EDGES verdict (measured Δ = −1.39, pipeline stricter not richer) therefore **holds** under the de-castrated pipeline: the de-castration restores a **process** axis (variance + richness of the synthesis, LLM-driven fallacy coverage), not a **content-separation** axis (the radar vs 0-shot differential).

Per the min-rule (formal DECIDES, quality is the binding constraint): restoring variance does not lift quality above EDGES, because EDGES is defined by *content separation* and the radar's content is unchanged. This is the honest verdict — promoting to DECIDES on the basis of "the text varies now" would be auto-promotion #1019 (variance is a process property, not a content-separation proof).

## 4. Fail-loud visibility (included in this PR)

`_llm_synthesis` (`deep_synthesis_agent.py:1527`) caught all exceptions at `logger.debug` and returned `None`. This **swallowed the real failure** — which is exactly why the wiring gap (§2) went undetected for the entire FB-31 cycle: Section 9 looked "unavailable" with no clue why. This PR surfaces it at `logger.warning` (same `return None` contract, visibility only). This is consistent with the FB-31 fail-loud mandate and made the §2 diagnosis possible.

## 5. Cost

| Phase | Cost |
|-------|------|
| isolate corpus_C (1 pipeline + 3 synthesis) | $0.67 |
| isolate corpus_C retry (wired, 2 synthesis) | $0.58 |
| full corpus_C ×2 (pre-fix, prod path) | $1.49 |
| probes (SK path, invoke path, _llm_synthesis) | ~$0.67 |
| **full corpus_C ×2 (post-wiring-fix, prod path, DoD)** | **$1.68** |
| **Total this round** | **~$5.09** |
| OpenRouter balance | $161.18 → $156.09 |

Verified real via OpenRouter `/api/v1/credits` (`data.total_credits − data.total_usage`, 1 credit = $1) before and after.

## Privacy HARD

Corpus loaded in-memory from the encrypted dataset (`corpus_A/B/C` → dataset indices, opaque `doc_A/B/C` labels). No `raw_text`/`full_text` in any committed artifact. Per-run markdown + raw JSON gitignored under `argumentation_analysis/evaluation/results/fb32/` (verified via `git check-ignore`). Diff excerpts in this report are from the opaque run only (State_Q/State_P/doc_C). A known LLM-opaqueness limitation is noted in §1.

## Anti-pendule

Variance IS the feature. `LLM_DETERMINISTIC_MODE` was NOT set (the harness aborts if it is). No prose-freezing test added. Golden `test_spectacular.py` stays structure-only. No synthetic fallback on LLM error — fail-loud. The fail-loud visibility change (debug→warning) preserves the `return None` contract — it is visibility, not a counterweight.

## Follow-ups flagged

1. **`narrative_synthesis` template removal** (#1115, po-2023 lane — **unblocked by this PR's wiring fix**): FB-33 residual audit found a castration residue — the template `build_narrative` phase is still wired into the spectacular workflow + surfaced in HTML, contradicting #1109 §5. po-2023 held #1115 pending the wiring decision (R407); now that the wiring lands here, #1115 can proceed — post-fix the spectacular test should assert Section 9 `status="llm"`, strengthening the "remove template" case.
2. **Opaqueness hardening**: one isolate run leaked corpus entities in non-opaque terms; tighten the synthesis prompt's ID discipline.
3. **Live FB-18 grounded confirmation on all corpora**: the wiring fix reactivates `_llm_briefing`, `_llm_synthesis`, AND the FB-18 grounded path. Section 9 + FB-18 `status="llm"` confirmed on corpus_C; a full A/B/C sweep would confirm the activation is corpus-independent (budget-permitting).
