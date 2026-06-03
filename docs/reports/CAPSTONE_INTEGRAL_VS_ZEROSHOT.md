# Capstone — Pipeline Intégral vs 0-Shot LLM Baseline

> Created: 2026-06-03 · Epic #923 · Track C2 (po-2023, synthèse)
> Prerequisite: C1 runs (po-2025) — artefacts under `evaluation/results/` (gitignored)
> Privacy: opaque IDs only (`src0_ext0`, `doc_A/B/C`) — no raw text, no speaker names

## Executive Summary

> **TODO: Fill after C1 runs complete.** One-line verdict per corpus + global verdict.

This document compares the **full parametric pipeline** (all components activated, max
configuration) against a **0-shot LLM baseline** (single prompt, no tool calling, no
symbolic reasoning, no multi-agent orchestration) on the same texts.

---

## Methodology

### Pipeline Configuration (C1 — MAX config)

| Selector | Value | Rationale |
|----------|-------|-----------|
| `--workflow` | `spectacular` | 20-phase full chain — maximum coverage |
| `--fallacy-tier` | `full` | All detection modes merged (taxonomy + hybrid + LLM) |
| `--shield-preset` | `advanced` | AI Shield active, non-blocking |
| `--vote-method` | `copeland` | Default social choice |
| `--consensus-threshold` | `0.7` | Standard threshold |
| `--formal-extension` | `all` | All 17 Tweety handlers + 4 core |
| `--fol-solver` | `tweety` | JVM-based (stable) |
| `--counter-strategy` | `all` | All 5 rhetorical strategies |
| Dung provider | `AFHandler` (native) | 11 semantics — maximum formal reasoning |
| Orchestration | `pipeline` | Sequential DAG (reproducible) |

### Baseline (0-Shot LLM)

**Prompt design** (single call, no system prompt beyond role):

```
Tu es un analyste rhétorique expert. Analyse le texte suivant de manière exhaustive.

Pour chaque argument identifié, fournis :
1. La thèse de l'argument
2. Les prémisses explicites et implicites
3. Le type de raisonnement (déductif, inductif, analogique, causal, etc.)
4. Tout sophisme ou erreur de raisonnement détecté (avec la famille : appel à l'autorité, homme de paille, faux dilemme, pente glissante, etc.)
5. La force persuasive de l'argument (1-10)

Ensuite, fournis une évaluation globale :
6. La structure argumentative du texte (nombre et types d'arguments)
7. Les stratégies rhétoriques employées
8. Les points forts et les faiblesses de l'argumentation
9. Une conclusion sur la qualité globale de l'argumentation

Texte :
---
{TEXT}
---
```

**Parameters**: Same model as pipeline (`gpt-5-mini`), temperature=0 (deterministic),
max_tokens=4096. No tool calling, no multi-turn, no chain-of-thought scaffolding.

### Comparison Framework

For each corpus, we compare along these **insight categories**:

| Category | Pipeline captures | 0-shot captures | Unique value |
|----------|-------------------|-----------------|--------------|
| **Argument extraction** | Structured (arg_id, premises, thesis) | Prose description | Structured → comparable |
| **Fallacy detection** | 8-family taxonomy + confidence + per-argument | Named in prose, no taxonomy | Taxonomy → systematic comparison |
| **Formal reasoning** | FOL/Modal formulas + Tweety verification | None | **Pipeline-unique** |
| **Dung argumentation** | 11 semantics, extensions, grounded/preferred/stable | None | **Pipeline-unique** |
| **ASPIC+ analysis** | Structured arguments with rules, undercutters | None | **Pipeline-unique** |
| **Counter-arguments** | 5 strategies, per-weak-argument | Generic prose suggestions | Structured targeting |
| **Quality scoring** | 9 virtues, per-argument, numeric | Subjective prose | Quantified comparison |
| **JTMS beliefs** | Justification chains, retraction cascades | None | **Pipeline-unique** |
| **Governance** | 7 voting methods, consensus metrics | None | **Pipeline-unique** |
| **Debate** | Multi-personality adversarial transcript | None | **Pipeline-unique** |
| **Narrative synthesis** | Cross-method convergence analysis | Single-pass prose | Depth vs breadth |

### Scoring Rubric

Each insight is scored on a **3-point scale**:

| Score | Meaning |
|-------|---------|
| 🔴 **Missed** | Pipeline/0-shot does not capture this class of insight at all |
| 🟡 **Partial** | Captured but incomplete — prose only, no structure, low confidence |
| 🟢 **Strong** | Structured, verified (Tweety/consensus), actionable |

---

## Results

> **TODO: Fill after C1 runs complete.**

### Corpus A (`doc_A`)

**Pipeline integral — summary:**
> TODO

**0-shot baseline — summary:**
> TODO

**Comparison table:**

| Category | Pipeline | 0-shot | Delta |
|----------|----------|--------|-------|
| Arguments identified | TODO | TODO | TODO |
| Fallacies detected | TODO | TODO | TODO |
| Formal reasoning | TODO | 🔴 Missed | **Pipeline-unique** |
| Dung semantics | TODO | 🔴 Missed | **Pipeline-unique** |
| ASPIC+ analysis | TODO | 🔴 Missed | **Pipeline-unique** |
| Counter-arguments | TODO | TODO | TODO |
| Quality scores | TODO | TODO | TODO |
| JTMS beliefs | TODO | 🔴 Missed | **Pipeline-unique** |
| Governance | TODO | 🔴 Missed | **Pipeline-unique** |
| Debate | TODO | 🔴 Missed | **Pipeline-unique** |
| Narrative synthesis | TODO | TODO | TODO |

**Unique insights (pipeline only):**
> TODO — cite by text-ID, describe what the pipeline captured that 0-shot cannot

**Unique insights (0-shot only):**
> TODO — any prose insight the pipeline missed due to phase ordering/scope

**Verdict:** TODO

---

### Corpus B (`doc_B`)

> Same structure as Corpus A

---

### Corpus C (`doc_C`)

> Same structure as Corpus A

---

## Global Synthesis

> **TODO: Fill after all 3 corpus comparisons complete.**

### What the pipeline adds (irreducible value)

1. **Formal verification**: Tweety-backed FOL/Modal/Dung reasoning is structurally
   impossible for a 0-shot LLM — it requires symbolic computation, not prose generation.
2. **Multi-agent debate**: Adversarial cross-examination surfaces weaknesses that a
   single-pass LLM cannot discover by itself.
3. **Quantified quality**: 9-virtue scoring enables objective comparison across texts,
   not just subjective prose.
4. **Justification tracking**: JTMS retraction cascades reveal argument dependency
   failures invisible to 0-shot analysis.
5. **Democratic governance**: Social choice voting over analysis positions produces
   consensus metrics, not just a single opinion.

### What the 0-shot baseline captures

1. **Holistic interpretation**: A single LLM pass can capture rhetorical context and
   implicit meaning that phased analysis may fragment.
2. **Speed**: ~30 seconds vs ~10+ minutes for the full pipeline.
3. **No infrastructure**: No JVM, no Tweety, no agents — just an API call.

### Cost-benefit analysis

| Dimension | Pipeline | 0-shot |
|-----------|----------|--------|
| Depth | Deep (formal verification) | Surface (prose only) |
| Coverage | 20 analysis dimensions | 1 dimension (prose) |
| Reproducibility | Deterministic (temp=0, same config) | Mostly deterministic |
| Time | ~10-15 min per corpus | ~30s per corpus |
| Cost (tokens) | ~50k-100k tokens | ~2k-5k tokens |
| Actionability | Structured data → downstream use | Prose → manual interpretation |

### Conclusion

> TODO: 1-line verdict.

---

## Appendix A: Pipeline Metrics (C1 raw data)

> Reference to JSONL artifacts under `evaluation/results/` (gitignored).
> Summary table of wall-clock, phases completed, field coverage per corpus.

## Appendix B: 0-Shot Raw Outputs

> Stored under `evaluation/results/` (gitignored, scrubbed).

---

## À valider par l'utilisateur

1. **Baseline prompt** — Is the 0-shot prompt above fair? Too generous? Too sparse?
   Should it include a system prompt or remain purely single-turn?
2. **Insight categories** — Are the 11 categories the right comparison axes?
   Missing dimensions?
3. **Scoring rubric** — 3-point (Missed/Partial/Strong) sufficient, or need finer
   granularity (5-point Likert)?
4. **Corpus scope** — 3 corpus documents sufficient, or need more for statistical
   significance?
5. **Cost threshold** — Is the 20-50x cost increase justified by the depth gain?
   Where is the ROI break-even?
