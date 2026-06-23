# Structured-Argumentation Translator — Scoping & Go/No-Go Gate (FP-17 #1236)

**Status:** scoping only — the translator is **NOT built**. This document converts
the structured-argumentation blind-spot (Epic #1191) into a *decidable* user/coord
gate. It is the companion to the honest-absent surfacing delivered in the same
track (#1236): the report and state snapshot now label these axes
`absent_no_translator` instead of emitting a silent empty list.

**Parent:** Epic #1191 (formal depth-parity). **Predecessor diagnostic:** FP-4
(#1201, MERGED). **Anti-pendule (#1019):** honest-absent is the correct output
until the gate is decided — we do **not** fabricate extensions to manufacture
"parity".

---

## 1. The gap, precisely

FP-4 (#1201) root-caused why **ASPIC+ / ABA / SETAF / weighted / bipolar** produce
**0 extensions** on real corpora while Dung-core yields genuine ones:

> The handlers and orchestrator shapers are correctly wired and **fail-loud**
> (FP-2 #1193). But the pipeline **never feeds them genuine structured input** —
> defeasible rules, assumptions+contraries, collective attacks, attack weights,
> support relations are never extracted from the text. The handlers run real
> Tweety on **auto-shaped synthetic input** derived from the bare argument graph,
> which collapses to a trivial framework → empty/degenerate result.

This is a **translation-gap**, not a reasoner bug. Dung-core works because a binary
attack graph *can* be auto-shaped from pairwise argument relations; the richer
formalisms need structure that simply is not in the argument graph.

What `_extract_arguments_from_context` + the `_*_from_context` shapers produce today
(see `orchestration/invoke_callables.py`) is the synthetic stand-in. The genuine
input each handler *expects* already exists as a context key (a future translator
would populate it):

| Formalism | Capability | Genuine-input context key | Auto-shaped stand-in today |
|---|---|---|---|
| ASPIC+ | `aspic_plus_reasoning` | `strict_rules`, `defeasible_rules` | rules synthesised from claims/args (`_invoke_aspic`) |
| ABA | `aba_reasoning` | `contraries` (+ assumptions) | rules from arg graph, `contraries=None` (`_invoke_aba`) |
| SetAF | `setaf_reasoning` | `set_attacks` (collective/joint) | pairwise attacks lifted to singletons (`_setaf_attacks_from_pairs`) |
| Weighted | `weighted_argumentation` | `weighted_attacks` (s,t,w triples) | pairwise attacks at neutral weight 0.5 (`_weighted_attacks_from_pairs`) |
| Bipolar | `bipolar_argumentation` | `supports` | `supports=[]` (`_invoke_bipolar`) |

The honest-absent surfacing (#1236) keys off exactly these context keys: when none
is present, the capability is `absent_no_translator`; when a caller (or a future
translator) supplies them, the status flips to `evaluated` automatically — no
further wiring needed.

---

## 2. Per-formalism input contract & extraction requirements

For each formalism: **(a)** the handler's existing input contract (what it already
accepts), and **(b)** what a text→structured translator would have to extract to
make the extensions genuine. Examples use opaque IDs only (`doc_A`, `arg_1`).

### 2.1 ASPIC+ (`aspic_plus_reasoning`)
- **Contract:** strict rules + defeasible rules as `{head, body:[...]}` dicts over
  PL atoms; an optional preference order over defeasible rules.
- **Extraction needed:**
  1. **Strict rules** — entailments the author treats as indefeasible
     ("by definition", "necessarily").
  2. **Defeasible rules** — typical/presumptive inferences ("generally",
     "usually", "tends to").
  3. **Preferences** — which rule wins when two conflict (priority cues:
     "more importantly", "but above all").
- **Why auto-shaping fails:** synthesising strict rules from extracted claims gives
  rules with no real defeat relation → grounded extension = all of it, no genuine
  ASPIC+ dialectic.

### 2.2 ABA (`aba_reasoning`)
- **Contract:** a set of assumptions, inference rules `{head, body}`, and a
  `contraries` map (assumption → its contrary literal).
- **Extraction needed:**
  1. **Assumptions** — defeasible premises taken for granted.
  2. **Contraries** — what would defeat each assumption (the crux; without it ABA
     degenerates to flat inference).
  3. **Rules** linking assumptions to conclusions.
- **Why auto-shaping fails:** `contraries=None` ⇒ no assumption can be attacked ⇒
  every assumption-set is trivially "admissible".

### 2.3 SetAF (`setaf_reasoning`)
- **Contract:** arguments + **collective** attacks `{attackers:[...], target}` where
  a *set* of arguments jointly attacks a target (no single one suffices).
- **Extraction needed:** identify joint-attack structure — "X and Y *together*
  refute Z". Pairwise extraction cannot represent this.
- **Why auto-shaping fails:** lifting pairwise attacks to singleton sets makes SetAF
  collapse to ordinary Dung — the collective semantics never engages.

### 2.4 Weighted AF (`weighted_argumentation`)
- **Contract:** arguments + weighted attacks `(source, target, weight)` + an
  inconsistency budget γ.
- **Extraction needed:** a **strength/confidence** per attack (hedging cues, evidence
  quality) and a defensible γ.
- **Why auto-shaping fails:** a uniform 0.5 weight (no fabricated confidence, #1019)
  carries no information → weighted semantics ≡ unweighted.

### 2.5 Bipolar AF (`bipolar_argumentation`)
- **Contract:** arguments + attacks + **supports** `(supporter, supported)`, under a
  chosen support interpretation (necessity / deductive / evidential).
- **Extraction needed:** **support relations** — "X backs Y", "this reinforces" —
  distinct from attacks, plus the intended support semantics.
- **Why auto-shaping fails:** `supports=[]` ⇒ the bipolar layer is inert; result ≡
  the underlying Dung framework.

---

## 3. Phased plan (only if the gate says GO)

Each phase is independently shippable and independently honest (a partial translator
upgrades *some* axes from `absent_no_translator` to `evaluated`; the rest stay
honestly absent).

- **Phase 0 — harness (no LLM).** A `StructuredArgInput` contract object + a
  pass-through that lets a caller inject genuine structured input via the existing
  context keys. Lets tests drive `evaluated` paths with hand-authored synthetic
  structure. *This is the seam #1236 already targets — the status flips for free.*
- **Phase 1 — bipolar + weighted (lowest extraction cost).** Support-cue and
  hedging-cue extraction (deterministic lexicon first, LLM-assisted second). These
  need one new relation/scalar each, no rule algebra.
- **Phase 2 — ABA (assumptions + contraries).** Contrary extraction is the unit of
  value; reuse the fallacy/claim layer for assumptions.
- **Phase 3 — ASPIC+ (strict/defeasible + preferences).** Largest surface: a
  rule-mining pass over claims with strict/defeasible classification + preference
  cues.
- **Phase 4 — SetAF (collective attacks).** Hardest extraction (joint-attack
  detection); lowest expected corpus frequency — sequence last.

Cross-cutting: every phase keeps the per-backend / per-axis honesty invariant
(#1019) — a translator that is *uncertain* must yield `absent`/`degraded`, never a
fabricated rule. Privacy: translator I/O is opaque-ID-only; raw structured artifacts
derived from corpus stay gitignored under `evaluation/results/`.

---

## 4. Go/No-Go question for the user

> **Do we build the text→structured-argument translator (Section 3), and if so, how
> far?** Options:
>
> - **No-Go (status quo):** keep all five axes `absent_no_translator`. Honest, zero
>   new LLM cost, no risk of fabricated structure. The report already says so.
> - **Go — Phase 0 only:** ship the injection harness so genuine structured input
>   *can* be supplied (by tests, or by an external caller) and is then genuinely
>   evaluated — without committing to extraction.
> - **Go — Phases 0–N:** build extraction up to a chosen formalism, accepting the
>   per-phase LLM cost and the extraction-quality risk (mitigated by the #1019
>   honest-uncertain rule).
>
> Default recommendation absent a decision: **No-Go**, because honest-absent is a
> correct and complete answer to "is this axis genuine?" — and the surfacing in
> #1236 makes that answer visible. The translator is value-add, not a correctness
> fix.

---

## 5. What #1236 delivered (this track, non-gated)

- `UnifiedAnalysisState.structured_arg_status` + `add_structured_arg_status()` —
  per-capability `{status, degraded, reason, extension_count}`, in the state
  snapshot (summarized **and** full).
- `state_writers._record_structured_arg_status()` wired into the five structured-arg
  writers — labels `absent_no_translator` (degraded) vs `evaluated` from the genuine
  context keys in §1.
- The restitution appendix (`reporting/restitution/appendix.py`) surfaces an
  `arg_structuree` line: `aspic_plus_reasoning=absent (aucun traducteur structuré); …`
  — so a reader can tell "absent (no translator)" from "evaluated, empty". No silent
  `[]` (#1019).
- This scoping doc.

Out of scope (unchanged): the translator itself, and the modal/FOL invoke callables
(serialization — `invoke_callables.py` is held by FP-19/FP-20).
