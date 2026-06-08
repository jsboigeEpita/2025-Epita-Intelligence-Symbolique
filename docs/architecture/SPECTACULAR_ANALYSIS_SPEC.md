# Spectacular Report Narrative-Structure Specification

**Issue**: #1008 — Epic #947 Phase 4 prep
**Purpose**: Define the report skeleton, verdict→prose mapping, "waouh" conclusion contract, and plugin-to-section traceability so that report generation is a **fill-in** once the FB-8 benchmark re-run (#1002) lands.

**Scope**: Structure and contract only. No raw corpus content, no speaker/document names.
**Privacy**: Opaque IDs (`corpus_A`, `corpus_B`, `corpus_C`, `Speaker_A`) throughout.

---

## 1. Section Skeleton — "Intelligence-Briefing" Register

The report follows an **Identification → Diagnostics → Thèse** progression (memory: empirically reads better than count dumps). Each section maps to specific shared-state dimensions.

### 1.1 Report Structure

```
┌─────────────────────────────────────────────┐
│  HEADER — Identification                     │
│  ├─ Source fingerprint (opaque ID, type)     │
│  ├─ Pipeline config (workflow, model, date)  │
│  └─ Executive summary (2-3 sentences)        │
├─────────────────────────────────────────────┤
│  SECTION A — Rhetorical Architecture         │
│  ├─ Argument extraction inventory            │
│  ├─ Quality profile (9 virtues radar)        │
│  └─ Structural assessment                    │
├─────────────────────────────────────────────┤
│  SECTION B — Fallacy Detection               │
│  ├─ Hierarchical taxonomy mapping            │
│  ├─ Per-fallacy analysis (type, target)      │
│  └─ Cross-reference to formal contradictions │
├─────────────────────────────────────────────┤
│  SECTION C — Formal Logic Analysis           │
│  ├─ Propositional logic (PL) verdicts        │
│  ├─ First-order logic (FOL) consistency      │
│  ├─ Modal logic assessment                   │
│  └─ Abstract argumentation (Dung/ASPIC)      │
├─────────────────────────────────────────────┤
│  SECTION D — Adversarial Testing             │
│  ├─ Counter-argument generation              │
│  ├─ Debate stress-test results               │
│  ├─ Belief dynamics (JTMS/ATMS)              │
│  └─ Governance simulation                    │
├─────────────────────────────────────────────┤
│  SECTION E — Convergence Synthesis           │
│  ├─ 5-signal convergence metric              │
│  ├─ Narrative synthesis prose                │
│  └─ Cross-dimensional correlation map        │
├─────────────────────────────────────────────┤
│  CONCLUSION — "Waouh" Thèse                  │
│  ├─ Honest verdict claim (gated on band)     │
│  ├─ Dimensions where pipeline EXCEEDED       │
│  ├─ Honest degradation disclosure            │
│  └─ Baseline comparison claim                │
└─────────────────────────────────────────────┘
```

### 1.2 Section-to-State Mapping

Each section reads from specific `UnifiedAnalysisState` fields. The generator MUST verify the field is populated before including the corresponding subsection; if empty/degraded, it includes an honest note rather than omitting silently.

| Section | Subsection | State key source | Degraded fallback wording |
|---------|-----------|-----------------|--------------------------|
| **Header** | Source fingerprint | `source_metadata` | — |
| **Header** | Pipeline config | `workflow_results` | — |
| **Header** | Executive summary | `narrative_synthesis` (if present) or auto-generated from counts | "Synthesis unavailable — report is a raw dump." |
| **A — Rhetorical** | Argument inventory | `identified_arguments` | "No arguments extracted." |
| **A — Rhetorical** | Quality profile | `argument_quality_scores` | "Quality scoring degraded (spacy/textstat unavailable)." |
| **A — Rhetorical** | Structural assessment | `argument_quality_scores[*.scores_par_vertu]` → `structure_logique`, `clarte` | "Structure analysis not available." |
| **B — Fallacy** | Taxonomy mapping | `identified_fallacies` → `family`, `taxonomy_path` | "No fallacies detected." |
| **B — Fallacy** | Per-fallacy analysis | `identified_fallacies` → `type`, `justification`, `target` | — |
| **B — Fallacy** | Cross-reference | `identified_fallacies` ↔ `dung_frameworks[*].attacks` | "Dung framework unavailable — no cross-reference." |
| **C — Formal** | PL verdicts | `propositional_analysis_results` | "Propositional logic unavailable." |
| **C — Formal** | FOL consistency | `fol_analysis_results` → `consistent`, `formulas` | "FOL analysis unavailable." |
| **C — Formal** | Modal assessment | `modal_analysis_results` | "Modal logic unavailable." |
| **C — Formal** | Dung/ASPIC | `dung_frameworks`, `aspic_results` | "Dung timeout — framework not computed." / "ASPIC unavailable." |
| **D — Adversarial** | Counter-arguments | `counter_arguments` → `counter_content`, `strategy` | "Counter-argument generation unavailable." |
| **D — Adversarial** | Debate stress-test | `debate_transcripts` | "Debate unavailable." |
| **D — Adversarial** | Belief dynamics | `jtms_beliefs`, `jtms_retraction_chain`, `atms_contexts` | "JTMS/ATMS unavailable." |
| **D — Adversarial** | Governance | `governance_decisions` | "Governance simulation unavailable." |
| **E — Convergence** | 5-signal metric | `identified_fallacies` + `argument_quality_scores` + `counter_arguments` + `jtms_retraction_chain` + `dung_frameworks` | "Convergence incomplete — N/5 signals available." |
| **E — Convergence** | Narrative synthesis | `narrative_synthesis` | "Narrative synthesis degraded — rebuilt from partial context." |
| **E — Convergence** | Cross-dim correlation | Derived from above | — |

---

## 2. Verdict → Prose Mapping

The FB-8 yardstick (`docs/reports/corpus_x_yardstick.md`) scores each of 10 dimensions (D1–D10) and computes a terminal verdict. The report's conclusion paragraph MUST be gated on the verdict band — honest, no over-claim.

### 2.1 Verdict Scale (FB-8 `_compute_verdict()`)

| Band | Condition | Meaning |
|------|-----------|---------|
| **EXCEEDED** | ≥7 MATCH+ with ≥1 EXCEEDED | Pipeline surpasses the external analyst on at least 1 dimension |
| **MATCH** | ≥7 MATCH+ | Pipeline matches the external analyst across most dimensions |
| **PARTIAL** | 5–6 MATCH+ | Pipeline touches most dimensions but misses key aspects |
| **BELOW** | <5 MATCH+ | Pipeline does not reach the analyst's depth on most dimensions |

### 2.2 Per-Band Allowed Claims

The conclusion paragraph is **restricted** to the following wording templates per band. The report generator MUST NOT claim more than the band permits.

#### EXCEEDED

> The integrated analysis pipeline demonstrates **depth surpassing** the reference analysis on **{N} dimension(s)** ({exceeded_dims}), while matching it on **{M}** others. The pipeline's multi-modal approach — combining rhetorical detection, formal logic verification, and adversarial stress-testing — produces insights that go beyond the single-lens external analysis, particularly on {key_exceeded_dim_description}.

Required non-trivial dimensions for this claim: ≥7 dimensions at MATCH+, at least 1 EXCEEDED.

#### MATCH

> The pipeline **matches** the reference analysis across **{N}/10 dimensions**, demonstrating that the multi-agent architecture captures the key analytical dimensions identified by the external specialist. Dimensions where the pipeline approaches but does not exceed the reference include: {partial_dim_list}.

Required non-trivial dimensions for this claim: ≥7 dimensions at MATCH+.

#### PARTIAL

> The pipeline **partially covers** the reference analysis, touching **{N}/10 dimensions** but missing key aspects on {missed_dims}. The pipeline's strengths concentrate on {strong_dims} while gaps remain in {weak_dims} — these represent the dimensions where single-lens specialist analysis still outperforms automated multi-agent approaches.

Required non-trivial dimensions for this claim: 5–6 dimensions at MATCH+. Honest disclosure of missed dimensions mandatory.

#### BELOW

> The pipeline's current output **falls below** the reference analysis depth, covering only **{N}/10 dimensions** adequately. This honest assessment identifies **{M} dimensions where the pipeline produces partial results** and **{K} dimensions where the pipeline misses entirely**. The primary gaps are: {gap_list}. These gaps reflect the current state of the pipeline's integration and calibration rather than fundamental architectural limitations.

Required non-trivial dimensions for this claim: any count. Honest disclosure of all gaps mandatory. The claim MUST NOT blame external factors (DLL crashes, timeouts) without also acknowledging pipeline responsibility for graceful degradation.

### 2.3 Per-Dimension Prose Templates

For each yardstick dimension D1–D10, the report includes a 1-paragraph assessment:

```
**{Dimension Name}** — {MATCH|PARTIAL|MISSED|EXCEEDED}
{Assessment prose based on pipeline output for this dimension's expected subsystems.}
```

Each dimension's assessment is produced by reading the relevant pipeline subsystem outputs (see Section 4 traceability table) and comparing against the yardstick expectation.

---

## 3. "Waouh" Conclusion Contract

### 3.1 The 1-Paragraph Conclusion

The report ends with a single digested paragraph that constitutes the **decision vs baseline**. This paragraph is the only part of the report that makes a comparative claim; all other sections present raw pipeline output.

### 3.2 Non-Triviality Gates for the Conclusion

The conclusion paragraph MUST NOT be generated until ALL of the following gates pass:

| Gate | Condition | Rationale |
|------|-----------|-----------|
| **G1 — Arguments extracted** | `len(identified_arguments) > 0` | Zero arguments = no analysis substrate |
| **G2 — At least 1 analytical dimension non-trivial** | ≥1 of {fallacies, quality, counter-args, formal, Dung} has non-zero content | All-zero = vacuous pipeline |
| **G3 — Verdict computed** | FB-8 `_compute_verdict()` returned a band | No verdict = no basis for claim |
| **G4 — No fabrication** | All claimed metrics trace to actual state keys (not placeholder/fallback text) | Anti-pendule: honest degradation, not fabricated depth |

### 3.3 Fallback Wording

If any gate fails, the conclusion uses this honest fallback:

> The pipeline run on {corpus_id} did not produce sufficient analytical depth for a comparative conclusion. {specific_gates_failed}. This reflects the current calibration of the pipeline and does not constitute a negative judgment on the source material.

Where `specific_gates_failed` lists which gates failed and why (e.g., "G1 failed: 0 arguments extracted from text", "G4 triggered: 3 dimensions used placeholder data").

### 3.4 "Waouh" Bar

The aspirational "waouh" conclusion (comparable to a specialist analyst) requires:

- **EXCEEDED** verdict band, OR
- **MATCH** with ≥2 dimensions where pipeline output is qualitatively richer than the yardstick (e.g., formal logic verification that the analyst did not perform)

At **PARTIAL**, the conclusion is honest and diagnostic.
At **BELOW**, the conclusion is honest and includes a concrete gap list for pipeline improvement.

---

## 4. Plugin-to-Section Traceability Table

This table maps each report section to the pipeline capability (snake_case) that feeds it, the shared-state key, and the workflow phase name. Generator wiring MUST use capability name for lookup (not class name).

| Report Section | Feeding Capability (snake_case) | Shared-State Key | Workflow Phase Name | Registry Service Name |
|---------------|-------------------------------|-----------------|--------------------|--------------------|
| **A — Argument inventory** | `fact_extraction` | `identified_arguments` | `extract` | `fact_extraction_service` |
| **A — Quality profile** | `argument_quality` | `argument_quality_scores` | `quality` | `quality_evaluator` |
| **A — Quality virtues** | `quality_scoring` | `argument_quality_scores[*.scores_par_vertu]` | `quality` | `quality_evaluator` |
| **B — Fallacy detection** | `hierarchical_fallacy_detection` | `identified_fallacies` | `hierarchical_fallacy` | `informal_handler` |
| **B — Neural fallacy** | `neural_fallacy_detection` | `neural_fallacy_scores` | `neural_detect` | `fallacy_detection_service` |
| **B — Fallacy taxonomy** | `fallacy_detection` | `identified_fallacies[*.family]` | `hierarchical_fallacy` | `informal_handler` |
| **C — PL verdicts** | `propositional_logic` | `propositional_analysis_results` | `pl` | `propositional_logic_service` |
| **C — FOL consistency** | `fol_reasoning` | `fol_analysis_results` | `fol` | `fol_reasoning_service` |
| **C — Modal assessment** | `modal_logic` | `modal_analysis_results` | `modal` | `modal_logic_service` |
| **C — Dung extensions** | `dung_extensions` | `dung_frameworks` | `dung_extensions` | `dung_extensions_service` |
| **C — ASPIC** | `aspic_plus_reasoning` | `aspic_results` | `aspic_analysis` | `aspic_handler` |
| **C — External FOL** | `external_fol_solving` | `fol_analysis_results` (augmented) | `fol_solver` | `external_fol_solver_service` |
| **C — External modal** | `external_modal_solving` | `modal_analysis_results` (augmented) | `modal_solver` | `external_modal_solver_service` |
| **C — Formal synthesis** | `formal_synthesis` | `formal_synthesis_reports` | `formal_synthesis` | `formal_synthesis_service` |
| **D — Counter-args** | `counter_argument_generation` | `counter_arguments` | `counter` | `counter_argument_service` |
| **D — Debate** | `adversarial_debate` | `debate_transcripts` | `debate` | `debate_agent` |
| **D — JTMS beliefs** | `belief_maintenance` / `jtms_reasoning` | `jtms_beliefs`, `jtms_retraction_chain` | `jtms` | `jtms_service` |
| **D — ATMS contexts** | `atms_reasoning` | `atms_contexts` | `atms` | `atms_handler` |
| **D — Belief revision** | `belief_revision` | `belief_revision_results` | `belief_revision` | `belief_revision_handler` |
| **D — Governance** | `governance_simulation` | `governance_decisions` | `governance` | `governance_agent` |
| **D — Dialogue** | `dialogue_protocols` | `dialogue_results` | — (standalone) | `dialogue_handler` |
| **D — Probabilistic** | `probabilistic_argumentation` | `probabilistic_results` | `probabilistic` | `probabilistic_handler` |
| **E — Narrative** | `narrative_synthesis` | `narrative_synthesis` | `narrative_synthesis` | `narrative_synthesis_service` |
| **E — Analysis synthesis** | `analysis_synthesis` | `workflow_results` | `synthesis` | `analysis_synthesis_service` |
| **E — Deep synthesis** | `deep_synthesis` | `workflow_results` (enriched) | `deep_synthesis` | `deep_synthesis_service` |
| **E — Stakes** | `stakes_extraction` | `stakes_and_stakeholders` | `stakes` | `stakes_extraction_service` |
| **E — Ranking** | `ranking_semantics` | `ranking_results` | `ranking` | `ranking_handler` |
| **E — Bipolar** | `bipolar_argumentation` | `bipolar_results` | `bipolar` | `bipolar_handler` |
| **Header — Source** | — | `source_metadata` | — (pre-phase) | — |
| **Header — Shield** | `adversarial_protection` | `ai_shield_results` | — (pre-phase) | `ai_shield_service` |

### Verification Rule

For each section, the generator MUST:
1. Look up the capability by **snake_case name** via `registry.find_for_capability(name)`.
2. Read the corresponding **shared-state key** from `UnifiedAnalysisState`.
3. If the key is empty/`None`, insert the **degraded fallback wording** (Section 1.2).
4. If the key contains data flagged `degraded=True`, append the honest degradation note.

---

## 5. Yardstick Dimension → Pipeline Subsystem Mapping

Each of the 10 yardstick dimensions (D1–D10) expects output from specific subsystems. The scorer reads these subsystem outputs to determine MATCH/PARTIAL/MISSED/EXCEEDED.

| Dimension | Expected Subsystems | Primary State Keys | Fallback if Unavailable |
|-----------|--------------------|--------------------|------------------------|
| **D1** Jargon of Systematization | `hierarchical_fallacy_detection`, `argument_quality`, `narrative_synthesis` | `identified_fallacies`, `argument_quality_scores`, `narrative_synthesis` | MISSED |
| **D2** Functional Contradictions | `fol_reasoning`, `dung_extensions`, `counter_argument_generation` | `fol_analysis_results`, `dung_frameworks`, `counter_arguments` | MISSED |
| **D3** Populist Rhetoric from Elite | `hierarchical_fallacy_detection`, `argument_quality`, `counter_argument_generation` | `identified_fallacies`, `argument_quality_scores`, `counter_arguments` | MISSED |
| **D4** Value Instrumentalization | `narrative_synthesis`, `dung_extensions`, `counter_argument_generation` | `narrative_synthesis`, `dung_frameworks`, `counter_arguments` | MISSED |
| **D5** Historical Parallel | `narrative_synthesis`, `dung_extensions`, convergence | `narrative_synthesis`, `dung_frameworks`, `jtms_retraction_chain` | MISSED |
| **D6** Circular Self-Justification | `fol_reasoning`, `hierarchical_fallacy_detection`, `argument_quality` | `fol_analysis_results`, `identified_fallacies`, `argument_quality_scores` | MISSED |
| **D7** Drive-Relief Mechanism | `hierarchical_fallacy_detection`, `argument_quality`, `narrative_synthesis` | `identified_fallacies`, `argument_quality_scores`, `narrative_synthesis` | MISSED |
| **D8** Permission Architecture | `narrative_synthesis`, `dung_extensions`, convergence | `narrative_synthesis`, `dung_frameworks`, `jtms_retraction_chain` | MISSED |
| **D9** Technofascism Def-by-Desc | `fact_extraction`, `argument_quality`, `counter_argument_generation` | `identified_arguments`, `argument_quality_scores`, `counter_arguments` | MISSED |
| **D10** Negation as Method | `narrative_synthesis`, convergence | `narrative_synthesis`, `jtms_retraction_chain` | MISSED |

**Note**: No dimension is automatically scored MATCH because a subsystem is "available". The scorer reads the **actual output content** and checks for substantive analysis relevant to the dimension's description.

---

## 6. Generation Protocol

### 6.1 When to Generate

The spectacular report is generated **after** the FB-8 benchmark re-run (#1002) lands with a verdict. Generation is:

1. **Fill-in, not design** — this spec provides the structure; the generator reads state and produces prose.
2. **Honest by construction** — degradation flags and empty fields produce explicit honest wording, never silent omission.
3. **Opaque by default** — source identity is replaced with opaque IDs; the generator never emits raw corpus content.

### 6.2 Generation Order

1. Read `UnifiedAnalysisState` from the completed pipeline run.
2. Populate each section from the traceability table (Section 4).
3. Compute the FB-8 verdict (call `_compute_verdict()` from `run_benchmark_fb8.py`).
4. Select the conclusion template based on the verdict band (Section 2.2).
5. Run the 4 gates (Section 3.2) — if any fail, use the fallback wording.
6. Assemble the final document in the section skeleton order (Section 1.1).
7. Run privacy scrub (`_scrub_state_for_export` 11-pass + `_ENTITY_SUBSTR_PATTERN`).
8. Emit the report as Markdown under `docs/reports/` with opaque corpus ID.

### 6.3 Anti-Pendule Reminders

- **Do not** replace a `degraded=True` flag with fabricated variance.
- **Do not** silently omit sections with empty data — include the fallback wording.
- **Do not** claim EXCEEDED or MATCH when the verdict is BELOW.
- **Do not** blame DLL crashes or timeouts without also acknowledging the pipeline's responsibility for graceful degradation.
- **Do not** invent dimensions the yardstick does not define.

---

## 7. Cross-References

- **Yardstick dimensions**: `docs/reports/corpus_x_yardstick.md` (D1–D10 definitions)
- **FB-8 benchmark runner**: `scripts/run_benchmark_fb8.py` (`_compute_verdict()`, `_score_dimension()`)
- **Shared state schema**: `argumentation_analysis/core/shared_state.py` (`UnifiedAnalysisState`)
- **Spectacular workflow**: `argumentation_analysis/orchestration/workflows.py` (`build_spectacular_workflow()`)
- **Registry services**: `argumentation_analysis/orchestration/registry_setup.py` (capability→invoke mapping)
- **State writers**: `argumentation_analysis/orchestration/state_writers.py` (capability→state key wiring)
- **Privacy scrub**: `argumentation_analysis/orchestration/unified_pipeline.py` (`_scrub_state_for_export`)
- **Epic #947**: GitHub issue #947 (Final Boss)
- **Roadmap #78**: GitHub issue #78 (project roadmap)
