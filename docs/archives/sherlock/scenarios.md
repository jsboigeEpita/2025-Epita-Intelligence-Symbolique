# Sherlock Modern — Investigation Scenarios

> Privacy: All scenarios use opaque IDs (`doc_A`, `doc_B`, `doc_C`).
> No plaintext content from the encrypted dataset appears in this file.

## Scenario 1: doc_A — Rhetorical Strategy Identification

| Field | Value |
|-------|-------|
| **Document** | `doc_A` |
| **Query** | Identify rhetorical strategies and fallacy patterns |
| **Expected** | >=2 fallacies detected, >=1 hypothesis retracted |

### Investigation Pipeline

1. **Extraction** — Identify factual claims and argumentative structures
2. **Fallacy Detection** — Classify detected fallacies by family (ad hominem, hasty generalization, etc.)
3. **Quality Evaluation** — Score argument quality on 10-point scale
4. **Cross-Examination** — Generate counter-arguments using rhetorical strategies
5. **Belief Tracking** — JTMS records beliefs and retractions
6. **Hypothesis Branching** — ATMS tests >=3 hypotheses (full trust, skeptical, conservative)
7. **Narrative Synthesis** — Produce investigation summary

### Expected Outcome

Under the "full trust" hypothesis, the author's claims hold but quality is low.
Under the "skeptical" hypothesis, fallacies undermine key claims.
The "conservative" hypothesis may survive as the most coherent.

---

## Scenario 2: doc_B — Cross-Examination Focus

| Field | Value |
|-------|-------|
| **Document** | `doc_B` |
| **Query** | Cross-examine argument quality and counter-arguments |
| **Expected** | Quality score <=5/10, >=1 counter-argument generated |

### Investigation Pipeline

Same 7-phase pipeline as Scenario 1, with emphasis on phases 3-4.

### Expected Outcome

Counter-arguments expose weaknesses in the original argumentation.
Quality score should reflect rhetorical vulnerability.
At least one hypothesis should be retracted based on counter-evidence.

---

## Scenario 3: doc_C — Full Hypothesis Branching

| Field | Value |
|-------|-------|
| **Document** | `doc_C` |
| **Query** | Full investigation with hypothesis branching |
| **Expected** | >=3 hypotheses, >=1 coherent, >=1 incoherent |

### Investigation Pipeline

Full pipeline with ATMS hypothesis branching as the focal point.

### Expected Outcome

Three or more hypotheses tested simultaneously.
Evidence-driven retraction of incoherent hypotheses with visible reasons.
Final attribution narrative distinguishing coherent from collapsed hypotheses.

---

## Running Scenarios

```bash
conda activate projet-is-roo-new
python examples/03_demos_overflow/sherlock_modern/run_scenarios.py
```

## Architecture Reference

- `SherlockModernOrchestrator` — 7-phase investigation pipeline (#357)
- `OpenDomainInvestigator` — Whodunit-style attribution analysis (#358)
- `HypothesisTracker` — ATMS-based hypothesis branching (#359)
