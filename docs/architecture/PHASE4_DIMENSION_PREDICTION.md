# Phase 4 — Pre-Run Dimension Prediction Grid

**Issue**: #1016 (Epic #947 Phase 4 prep)
**Purpose**: Map each yardstick dimension D1-D10 → producing subsystem → which of the 4 merged fixes (#992/#999 Dung, #993/#1000 Quality, #994/#1001 Narrative, #995/#998 Alias) touches it → predicted post-fix outcome.
**Status**: Pre-run prediction (awaiting re-run #1002 for delta comparison)
**Lane**: po-2023 (docs-only, zero code changes)

---

## 1. Methodology

1. Each dimension is traced from the yardstick (`docs/reports/corpus_x_yardstick.md`) to its producing subsystem via the traceability table in `docs/architecture/SPECTACULAR_ANALYSIS_SPEC.md` (29-row mapping).
2. Each fix is traced to the code it changed (file:line) and then to the dimensions that subsystem produces.
3. Prediction is honest: dimensions where no fix touches the root cause are marked MISSED with explicit "zéro légitime" justification.

---

## 2. Fix → Code Reference Table

| Fix | PR | What changed | Key file:line | Mechanism |
|-----|-----|-------------|---------------|-----------|
| #992 Dung fallback | #999 | Python grounded-extension fallback on timeout/error | `invoke_callables.py:5575` (timeout path), `invoke_callables.py:5650` (error path), `invoke_callables.py:5666` (fallback function) | When JVM/Tweety Dung computation times out (60s default) or AFHandler fails, a pure-Python grounded extension is computed. Result stamped `degraded=True`. |
| #993 Quality fallback | #1000 | Heuristic quality scoring when torch/spacy unavailable | `quality_evaluator.py:31` (`_load_deps`), `quality_evaluator.py:337-339` (degraded flag) | When torch DLL load fails (`WinError 182`), quality evaluator falls back to regex-based 9-virtue detectors. Result stamped `degraded=True`. |
| #994 Narrative rebuild | #1001 | Context-based narrative when state empty | `invoke_callables.py:5830` (sentinel check), `invoke_callables.py:5834-5935` (rebuild from phase outputs), `invoke_callables.py:5953-5955` (degraded flag) | When `build_narrative(state)` returns empty or fallback sentinel, reconstructs narrative from `phase_extract_output`, `phase_hierarchical_fallacy_output`, `phase_counter_output`, etc. |
| #995 Alias scorer | #998 | FR→EN fallacy alias map for FB-8 scorer | `run_benchmark_fb8.py:278-316` (`FALLACY_FR_EN_ALIASES`), `run_benchmark_fb8.py:319-328` (`_normalize_fallacy_type`), `run_benchmark_fb8.py:344-352` (scorer integration) | French pipeline labels (e.g. "appel à l'émotion") are normalized to English canonical markers (e.g. "appeal_to_emotion") before scoring against yardstick. |

---

## 3. Dimension → Subsystem → Fix → Prediction

### D1: Jargon of Systematization (meta-rhetorical framing)

| Field | Value |
|-------|-------|
| #953 outcome | **MISSED** — no circular reasoning detected |
| Primary subsystem | `hierarchical_fallacy_detection` (capability) → `identified_fallacies` (state key) → `hierarchical_fallacy` (phase) |
| Secondary subsystems | `argument_quality` → `argument_quality_scores` → `quality`; `narrative_synthesis` → `narrative_synthesis` → `narrative_synthesis` |
| Fix #992 (Dung) | ❌ No — Dung extensions don't detect rhetorical jargon |
| Fix #993 (Quality) | ⚠️ Marginal — quality heuristic fallback (`quality_evaluator.py:337`) can now score `clarté` even when torch fails. Low clarity is an indirect signal of jargon obfuscation, but not a direct detection of "systematization language concealing value judgments". |
| Fix #994 (Narrative) | ⚠️ Marginal — narrative rebuild (`invoke_callables.py:5834`) can now assemble structural patterns from phase outputs. May produce a paragraph noting jargon patterns. |
| Fix #995 (Alias) | ❌ No — alias mapping normalizes fallacy labels; if no circular reasoning was detected, there is nothing to alias |
| **Prediction** | **MISSED** |
| Justification | The root cause is that `hierarchical_fallacy_detection` did not detect "begging question" or "appeal to authority" patterns in the French systematization jargon. None of the 4 fixes improve the fallacy detector's pattern matching for French rhetorical strategies. Quality fallback gives indirect signal (low clarté) but not a dimension-level MATCH. **Zéro légitime** — the fallacy detector needs French circular-reasoning patterns added to its taxonomy. |

---

### D2: Functional Contradictions (internal logical inconsistency)

| Field | Value |
|-------|-------|
| #953 outcome | **PARTIAL** — 44 formal formulas, 0 Dung extensions |
| Primary subsystem | `dung_extensions` (capability) → `dung_frameworks` (state key) → `dung_extensions` (phase) |
| Secondary subsystems | `propositional_logic` → `propositional_analysis_results` → `pl`; `fol_reasoning` → `fol_analysis_results` → `fol`; `counter_argument_generation` → `counter_arguments` → `counter` |
| Fix #992 (Dung) | ✅ **Direct** — the grounded-extension fallback (`invoke_callables.py:5575`) now produces Dung extensions where #953 had 0. The attack graph and grounded extension reveal self-attacking argument pairs. |
| Fix #993 (Quality) | ❌ No — quality scores don't detect contradictions |
| Fix #994 (Narrative) | ❌ No — narrative doesn't compute extensions |
| Fix #995 (Alias) | ❌ No — scoring, not detection |
| **Prediction** | **MATCH** |
| Justification | The #953 blocker was explicitly "0 Dung extensions" — the formal logic subsystem produced 44 formulas but the Dung framework was completely absent. Fix #992 resolves this: a Python grounded extension is computed on timeout/error (`invoke_callables.py:5575-5578`). With extensions available, the scorer can verify self-attacking argument pairs. Combined with the 44 existing formal formulas, this should reach MATCH for D2. |

---

### D3: Populist Rhetoric from Elite Position

| Field | Value |
|-------|-------|
| #953 outcome | **MISSED** — no ad populum detected |
| Primary subsystem | `hierarchical_fallacy_detection` → `identified_fallacies` → `hierarchical_fallacy`; `argument_quality` → `argument_quality_scores` → `quality` |
| Secondary subsystems | `counter_argument_generation` → `counter_arguments` → `counter` |
| Fix #992 (Dung) | ❌ No |
| Fix #993 (Quality) | ⚠️ Marginal — quality heuristic may score low `fiabilite_sources` (credibility gap). Indirect signal only. |
| Fix #994 (Narrative) | ❌ No |
| Fix #995 (Alias) | ⚠️ Marginal — the alias map includes `"raison de la majorité": "ad_populum"` (`run_benchmark_fb8.py:278-316`). But this only helps if the fallacy detector *detected* ad populum and labeled it in French — in #953, no ad populum was detected at all, so there's nothing to alias. |
| **Prediction** | **MISSED** |
| Justification | The root cause is that `hierarchical_fallacy_detection` did not detect ad populum in the French text. Fix #995 normalizes labels but cannot create detections that never happened. Quality fallback gives indirect signal. **Zéro légitime** — the fallacy detector needs ad populum / elite-populism pattern matching for French political rhetoric. |

---

### D4: Value Instrumentalization (progressive values as cover)

| Field | Value |
|-------|-------|
| #953 outcome | **PARTIAL** — some evidence via contradictions |
| Primary subsystem | `dung_extensions` → `dung_frameworks` → `dung_extensions`; `counter_argument_generation` → `counter_arguments` → `counter` |
| Secondary subsystems | `narrative_synthesis` → `narrative_synthesis` → `narrative_synthesis` |
| Fix #992 (Dung) | ✅ **Direct** — with Dung extensions now available (`invoke_callables.py:5575`), the attack graph can show which arguments based on progressive values are attacked by other arguments in the same text. |
| Fix #993 (Quality) | ❌ No |
| Fix #994 (Narrative) | ✅ **Direct** — narrative rebuild (`invoke_callables.py:5834-5935`) can now synthesize contradiction patterns between stated values and actual proposals. |
| Fix #995 (Alias) | ❌ No |
| **Prediction** | **MATCH** |
| Justification | Already PARTIAL in #953. Two direct fixes converge: Dung extensions now provide the attack-graph evidence (was 0), and narrative synthesis now produces structural contradiction analysis (was empty). The combination should push D4 from PARTIAL to MATCH. |

---

### D5: Historical Parallel (reactionary speech analogy)

| Field | Value |
|-------|-------|
| #953 outcome | **MISSED** — insufficient narrative synthesis |
| Primary subsystem | `narrative_synthesis` → `narrative_synthesis` → `narrative_synthesis`; `dung_extensions` → `dung_frameworks` → `dung_extensions` |
| Secondary subsystems | Convergence engine (5-signal metric) |
| Fix #992 (Dung) | ⚠️ Indirect — Dung extensions may reveal structural isomorphism (self-attacking patterns) that the scorer can note |
| Fix #993 (Quality) | ❌ No |
| Fix #994 (Narrative) | ✅ **Direct** — narrative rebuild (`invoke_callables.py:5834`) now produces synthesis from context, where #953 had none. However, the rebuilt narrative is a structural summary (argument count, fallacy count, counter-arg count), not deep analytical prose detecting historical parallels. |
| Fix #995 (Alias) | ❌ No |
| **Prediction** | **PARTIAL** |
| Justification | The root cause is "insufficient narrative synthesis" — fix #994 directly addresses this by producing a non-empty narrative. However, historical parallel detection requires: (1) recognizing that the text's structure mirrors a specific historical pattern, and (2) synthesis-level insight beyond what degraded narrative produces. The pipeline can now detect structural patterns (self-attacking Dung framework, performative contradictions) but not the historical analogy. Upgrades from MISSED to PARTIAL (some structural evidence via Dung + narrative). |

---

### D6: Circular Self-Justification (critical theory inversion)

| Field | Value |
|-------|-------|
| #953 outcome | **MISSED** — no circular reasoning detected |
| Primary subsystem | `hierarchical_fallacy_detection` → `identified_fallacies` → `hierarchical_fallacy`; `argument_quality` → `argument_quality_scores` → `quality`; `propositional_logic` → `propositional_analysis_results` → `pl` |
| Secondary subsystems | `dung_extensions` → `dung_frameworks` → `dung_extensions` |
| Fix #992 (Dung) | ⚠️ Indirect — Dung extensions may reveal self-attacking structure consistent with circular reasoning |
| Fix #993 (Quality) | ✅ **Direct** — quality heuristic fallback (`quality_evaluator.py:337`) can now score `structure_logique`. Low score on structure_logique is an indirect signal of circular reasoning. |
| Fix #994 (Narrative) | ❌ No — narrative doesn't detect circularity |
| Fix #995 (Alias) | ⚠️ Marginal — alias map includes `"argument circulaire": "circular_reasoning"`. Same issue as D3: only helps if circular reasoning was detected. |
| **Prediction** | **PARTIAL** |
| Justification | The fallacy detector still won't detect petitio principii in French systematization jargon (same gap as D1). However, two indirect signals now exist: (1) quality `structure_logique` score via heuristic fallback, and (2) Dung grounded extension may show self-attacking structure. These indirect signals upgrade from MISSED to PARTIAL but don't reach MATCH because the primary subsystem (`hierarchical_fallacy_detection`) still misses the pattern. |

---

### D7: Drive-Relief Mechanism (affective vs logical truth)

| Field | Value |
|-------|-------|
| #953 outcome | **MISSED** — no emotional appeal markers |
| Primary subsystem | `hierarchical_fallacy_detection` → `identified_fallacies` → `hierarchical_fallacy`; `argument_quality` → `argument_quality_scores` → `quality` |
| Secondary subsystems | `narrative_synthesis` → `narrative_synthesis` → `narrative_synthesis` |
| Fix #992 (Dung) | ❌ No |
| Fix #993 (Quality) | ⚠️ Marginal — quality heuristic can score `pertinence` and `presence_sources`. Low pertinence + low source presence is an indirect signal of emotional substitution. But regex-based detectors don't detect "drive-relief" as a rhetorical mechanism. |
| Fix #994 (Narrative) | ⚠️ Marginal — narrative rebuild assembles phase outputs but doesn't synthesize "emotional substitution" as a pattern |
| Fix #995 (Alias) | ⚠️ Marginal — alias map includes `"appel à l'émotion": "appeal_to_emotion"`. Same issue as D3/D1: only helps if the fallacy was detected. |
| **Prediction** | **MISSED** |
| Justification | The root cause is that the fallacy detector does not detect "appeal to emotion" in French text at the depth required. The "drive-relief mechanism" is a sophisticated analytical concept (truth-claims are affective, not logical) that goes beyond simple emotional-appeal detection. Quality fallback gives indirect `pertinence` scores but doesn't identify the specific pattern. **Zéro légitime** — the fallacy detector needs emotional-rhetoric pattern matching for French, and the narrative synthesizer needs depth to identify "emotional substitution" as a structural pattern. |

---

### D8: Permission Architecture (jargon as consent-manufacture)

| Field | Value |
|-------|-------|
| #953 outcome | **MISSED** — insufficient Dung framework output |
| Primary subsystem | `dung_extensions` → `dung_frameworks` → `dung_extensions`; `narrative_synthesis` → `narrative_synthesis` → `narrative_synthesis` |
| Secondary subsystems | Convergence engine (5-signal metric) |
| Fix #992 (Dung) | ✅ **Direct** — Dung extensions now available. The sequential attack chain in the argument graph can be mapped, revealing the escalation pattern. |
| Fix #993 (Quality) | ❌ No |
| Fix #994 (Narrative) | ✅ **Direct** — narrative rebuild produces structural synthesis from context, potentially detecting escalation patterns across argument frames. |
| Fix #995 (Alias) | ❌ No |
| **Prediction** | **PARTIAL** |
| Justification | The #953 blocker was "insufficient Dung framework output" (0 extensions). Fix #992 resolves the Dung gap. Fix #994 provides narrative synthesis. However, "permission architecture" requires detecting: (1) sequential deployment of incompatible frames, (2) cumulative authority-building, and (3) each frame granting permission for the next escalation. The Dung extensions can show the attack graph structure, and the narrative can summarize it, but the specific "escalation cascade" pattern requires synthesis depth beyond what degraded narrative provides. Upgrades from MISSED to PARTIAL. |

---

### D9: Technofascism Definition-by-Description

| Field | Value |
|-------|-------|
| #953 outcome | **PARTIAL** — 14 args + 25 counter-arguments |
| Primary subsystem | `fact_extraction` → `identified_arguments` → `extract`; `argument_quality` → `argument_quality_scores` → `quality`; `counter_argument_generation` → `counter_arguments` → `counter` |
| Secondary subsystems | `hierarchical_fallacy_detection` → `identified_fallacies` → `hierarchical_fallacy` |
| Fix #992 (Dung) | ❌ No — Dung doesn't affect fact extraction or counter-arg generation |
| Fix #993 (Quality) | ✅ **Direct** — quality heuristic fallback (`quality_evaluator.py:337`) now provides evidence-quality assessment for the 14 extracted arguments. Low `presence_sources` would flag unsubstantiated claims. |
| Fix #994 (Narrative) | ❌ No — narrative doesn't affect fact extraction |
| Fix #995 (Alias) | ✅ **Direct** — FR→EN alias normalization (`run_benchmark_fb8.py:319-328`) ensures fallacy labels from the counter-argument analysis are correctly matched against yardstick markers. Previously, French-labeled fallacies in counter-args may have been invisible to the scorer. |
| **Prediction** | **MATCH** |
| Justification | Already PARTIAL with 14 args + 25 counter-arguments. Two fixes improve: (1) quality evaluation now produces scores (evidence assessment was previously absent due to torch DLL failure), and (2) alias normalization ensures French fallacy labels in counter-arg analysis are scored correctly. The gap between PARTIAL and MATCH was marginal — these two improvements should close it. |

---

### D10: Negation as Method (critical theory prescription)

| Field | Value |
|-------|-------|
| #953 outcome | **MISSED** — insufficient synthesis output |
| Primary subsystem | `narrative_synthesis` → `narrative_synthesis` → `narrative_synthesis`; convergence engine (5-signal metric) |
| Secondary subsystems | — |
| Fix #992 (Dung) | ❌ No |
| Fix #993 (Quality) | ❌ No |
| Fix #994 (Narrative) | ⚠️ Marginal — narrative rebuild produces *something* where #953 had nothing. But "negation method" is a meta-analytical insight: it requires recognizing multi-layer analysis (surface jargon vs deep jargon) and methodological prescriptions. The degraded narrative produces a structural summary, not meta-analytical depth. |
| Fix #995 (Alias) | ❌ No |
| **Prediction** | **MISSED** |
| Justification | The root cause is that D10 requires the convergence engine to detect multi-depth cross-method agreement — a synthesis capability that doesn't exist in the current pipeline architecture. No fix targets this. The narrative rebuild produces a structural summary but not the meta-analytical insight of "which method negates at which depth." **Zéro légitime** — requires convergence-engine depth capability that is architecturally absent. |

---

## 4. Prediction Summary Table

| Dim | #953 | Fix #992 (Dung) | Fix #993 (Quality) | Fix #994 (Narrative) | Fix #995 (Alias) | **Predicted** | Primary driver |
|-----|------|:-:|:-:|:-:|:-:|:---:|---------------|
| D1 Jargon | MISSED | ❌ | ⚠️ | ⚠️ | ❌ | **MISSED** | Fallacy detector gap (no FR circular-reasoning pattern) |
| D2 Contradictions | PARTIAL | ✅ | ❌ | ❌ | ❌ | **MATCH** | Dung grounded fallback → 0→N extensions |
| D3 Populist | MISSED | ❌ | ⚠️ | ❌ | ⚠️ | **MISSED** | Fallacy detector gap (no FR ad populum pattern) |
| D4 Value Instrum. | PARTIAL | ✅ | ❌ | ✅ | ❌ | **MATCH** | Dung extensions + narrative synthesis |
| D5 Historical | MISSED | ⚠️ | ❌ | ✅ | ❌ | **PARTIAL** | Narrative rebuild + Dung structural evidence |
| D6 Circular | MISSED | ⚠️ | ✅ | ❌ | ⚠️ | **PARTIAL** | Quality structure_logique + Dung self-attacking |
| D7 Drive-Relief | MISSED | ❌ | ⚠️ | ⚠️ | ⚠️ | **MISSED** | No emotional-rhetoric detector in French |
| D8 Permission | MISSED | ✅ | ❌ | ✅ | ❌ | **PARTIAL** | Dung extensions + narrative, but lacks escalation depth |
| D9 Technofascism | PARTIAL | ❌ | ✅ | ❌ | ✅ | **MATCH** | Quality scores + alias normalization |
| D10 Negation | MISSED | ❌ | ❌ | ⚠️ | ❌ | **MISSED** | Convergence depth absent architecturally |

**Legend**: ✅ = direct fix, ⚠️ = marginal/indirect, ❌ = no effect

---

## 5. Predicted Verdict Band

| Metric | Value |
|--------|-------|
| Predicted MATCH count | 3 (D2, D4, D9) |
| Predicted PARTIAL count | 3 (D5, D6, D8) |
| Predicted MISSED count | 4 (D1, D3, D7, D10) |
| **MATCH+ total** (MATCH + EXCEEDED) | **3** |
| Verdict band | **BELOW** (≥7 MATCH+ = MATCH band, 5-6 = PARTIAL, <5 = BELOW) |

**Honest assessment**: The 4 fixes (#992-#995) address specific infrastructure gaps (Dung timeout, quality torch DLL, narrative empty-state, scorer alias). They move D2 from PARTIAL→MATCH and D4/D9 from PARTIAL→MATCH. Three dimensions upgrade from MISSED→PARTIAL (D5, D6, D8). But 4 dimensions remain MISSED because no fix touches the fallacy detector's French pattern matching (D1, D3, D7) or the convergence engine's depth capability (D10).

---

## 6. Residual MISSED Dimensions — Zero Légitime vs Bug Résiduel

| Dim | Root cause | Classification | Next step |
|-----|-----------|---------------|-----------|
| D1 Jargon | `hierarchical_fallacy_detection` has no French "begging question in systematization jargon" pattern | **Zéro légitime** — the taxonomy doesn't include this rhetorical strategy as a detectable fallacy family | Add FR circular-reasoning patterns to fallacy taxonomy |
| D3 Populist | `hierarchical_fallacy_detection` has no French "ad populum from elite position" pattern | **Zéro légitime** — ad populum exists in taxonomy but not as elite-populism variant | Add elite-populism rhetorical pattern to fallacy detector |
| D7 Drive-Relief | `hierarchical_fallacy_detection` detects "appeal to emotion" but not "affective truth mechanism" (emotional substitution as structural pattern) | **Zéro légitime** — this is a synthesis-level analytical concept, beyond simple fallacy detection | Add emotional-rhetoric depth analysis to narrative synthesis |
| D10 Negation | Convergence engine has no multi-depth analysis capability (surface vs structural vs meta) | **Zéro légitime** — architecturally absent, would require convergence-engine redesign | Add multi-layer convergence detection to synthesis engine |

**All 4 residual MISSED are zéro légitime** — genuine pipeline capability gaps that require dedicated development, not bug fixes. None are regressions or latent bugs that the 4 fixes missed.

---

## 7. Comparison Protocol (for re-run #1002)

When #1002 produces actual results, compare against this prediction:

1. **For each MATCH prediction**: Verify the actual score. If actual < predicted, the fix may not have landed correctly or the fixture may differ.
2. **For each PARTIAL prediction**: Check if the indirect signals (quality scores, Dung extensions) actually contributed.
3. **For each MISSED prediction**: Confirm the root cause matches (fallacy detector gap, convergence depth gap). If actual > predicted, investigate whether an indirect signal was stronger than expected.
4. **Delta analysis**: Create a predicted-vs-actual table. Any prediction error >1 band (e.g., predicted MISSED, actual MATCH) requires root-cause analysis to ensure it's not a false positive.

---

## 8. Cross-References

- **Yardstick**: `docs/reports/corpus_x_yardstick.md` (D1-D10 definitions)
- **Spectacular spec**: `docs/architecture/SPECTACULAR_ANALYSIS_SPEC.md` (29-row traceability)
- **Dung fallback**: `argumentation_analysis/orchestration/invoke_callables.py:5575` (timeout), `:5650` (error), `:5666` (function)
- **Quality fallback**: `argumentation_analysis/agents/core/quality/quality_evaluator.py:31` (deps), `:337` (degraded flag)
- **Narrative rebuild**: `argumentation_analysis/orchestration/invoke_callables.py:5830` (sentinel), `:5834-5935` (rebuild), `:5953` (degraded flag)
- **Alias scorer**: `scripts/run_benchmark_fb8.py:278` (alias map), `:319` (normalizer), `:344` (integration)
- **Issue #1016**: Prediction grid task
- **Issue #953**: FB-8 BELOW scorecard (reference run)
- **Issue #1002**: Re-run (blocked, will produce actual delta)
