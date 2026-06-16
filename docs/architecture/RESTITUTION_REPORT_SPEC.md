# Restitution Report Specification — the readable 3-act narrative

**Issue**: #1135 — Epic #1134 (Restitution), Track R1 (foundation)
**Purpose**: Turn the spectacular `UnifiedAnalysisState` into a report a non-specialist can read and *use* — a **narration**, not a dimension dump. This spec is the blueprint so that generation (R2 Acte I / R3 Acte II / R4 Acte III / R6 renderer) is **fill-in, not design**.
**Scope**: Structure and contract only. No corpus content, no speaker/document names, no `raw_text`.
**Privacy**: Opaque IDs only (`corpus_A`, `Speaker_A`, `arg_N`, `doc_*`). The public doc and all examples carry zero corpus content; reports on real corpora stay gitignored.

---

## 0. Relation to prior art — **absorb #1008, do not duplicate it**

This spec **extends** [`SPECTACULAR_ANALYSIS_SPEC.md`](SPECTACULAR_ANALYSIS_SPEC.md) (#1008), whose *readability* goal was never reached: the produced artifact (e.g. [`FB37_CAPSTONE_SPECTACULAR_REPORT.md`](../reports/FB37_CAPSTONE_SPECTACULAR_REPORT.md)) is a *run report* — phase tables, corpus-by-corpus dumps, engineering provenance. That is the dimension enumeration the owner called « très difficile à lire ».

**What #1008 got right and we keep** (cite, don't rewrite):
- **Verdict → prose bands** (#1008 §2): `EXCEEDED` / `MATCH` / `PARTIAL` / `BELOW`, each authorizing a *specific* claim — honest, no over-claim. Acte III reuses these verbatim.
- **"Waouh" conclusion contract + non-triviality gates G1–G4** (#1008 §3): the conclusion must not render until arguments exist (G1), ≥1 dimension is non-trivial (G2), a verdict band is computed (G3), and nothing is fabricated (G4). Reused by Acte III.
- **Capability → state-key → phase traceability** (#1008 §4): the wiring contract (look up capability by **snake_case name** via `CapabilityRegistry`, read the shared-state key, degrade honestly if empty). Reused as the *proof-notes* of the narrative (§4 below).
- **Yardstick D1–D10 → subsystem mapping** (#1008 §5): which subsystems back each analytical dimension. Reused to source Acte II's "formal tenue" citations.
- **Generation protocol** (#1008 §6): honest-by-construction, opaque-by-default, fill-in-not-design, privacy-scrub on emit.

**What #1008 got wrong and this spec fixes**: its **skeleton**. #1008 organizes the report *by analytical dimension* (Section A Rhetorical → B Fallacy → C Formal → D Adversarial → E Convergence). That organization **is** the enumeration. This spec reorganizes the **same content** *by argumentative movement* (Acte I framing → Acte II dialectical narrative → Acte III actionable conclusion). The dimensions become footnotes that *prove* story points; they are no longer the chapters.

> **One-line thesis**: the reader follows the argument's story; Tweety, Dung/ASPIC, the taxonomy descent and the virtues are the *citations* that make each beat verifiable — never a standalone list entry (see §6 weaving rule).

---

## 1. The three acts — skeleton

```
┌─────────────────────────────────────────────────────────────┐
│  ACTE I — Mise en situation   (before a single line of text) │
│  ├─ Le texte : genre, rôle du locuteur, canal, contexte      │
│  ├─ Les enjeux : ce qui se joue, pour qui, quelle asymétrie  │
│  ├─ Le terrain de jeu : spectre des sophismes attendus       │
│  └─ Lecture game-theoretic : joueurs, intérêts, coups        │
├─────────────────────────────────────────────────────────────┤
│  ACTE II — Récit dialectique  (the text under the microscope)│
│  Decoupe par MOUVEMENT ARGUMENTATIF (cluster d'arguments),   │
│  pas par dimension. Pour chaque mouvement :                  │
│  ├─ l'argument + sa qualité (vertus détectées)               │
│  ├─ ses failles (sophismes localisés + descente + contrage)  │
│  └─ sa tenue formelle (PL/FOL/Dung citée comme PREUVE)       │
├─────────────────────────────────────────────────────────────┤
│  ACTE III — Conclusion actionnable                           │
│  ├─ Synthèse honnête (verdict gated — reprend #1008 §2/§3)   │
│  ├─ Appréciations : forces ET faiblesses                     │
│  └─ Que faire : contrer / points faibles à viser / what-next │
└─────────────────────────────────────────────────────────────┘
```

The progression is **framing → microscope → action**. Acte I earns the reader's bearings; Acte II walks the argumentative thread (thèse → soutiens → dérapages); Acte III hands back something *usable*. No act is a dimension list.

### 1.1 Acte I — Mise en situation

Everything that makes the rest legible, **before** citing the text. Four beats:

- **Le texte** — discourse genre, speaker role, channel, context. Sourced from metadata (opaque IDs). *Not* a paraphrase of the corpus.
- **Les enjeux** — what is at stake, for whom, what asymmetry. Sourced from `stakes_and_stakeholders`.
- **Le terrain de jeu rhétorique** — the **spectrum of fallacies an informed listener should watch for** given this *genre* of discourse. This is **anticipation from the taxonomy**, not detection: "voici ce qu'un auditeur averti doit guetter". Sourced by walking the fallacy taxonomy for the genre-relevant families.
- **Lecture game-theoretic** — the players, their interests, expected moves, asymmetric information. Sourced from `stakes_and_stakeholders` + the argument inventory's structure (who attacks what).

> Acte I is the only act that may anticipate. Acts II–III report what the pipeline *found*, never what it *expects*.

### 1.2 Acte II — Récit dialectique par mouvement argumentatif

The narrative core. The report follows the **argumentative thread**: thèse → soutiens → dérapages. It is cut **by argumentative movement** (a cluster of related arguments), **not** by analytical dimension.

For each mouvement:
1. **L'argument et sa qualité** — the claim, its supporting structure, and the **virtues detected** (the 9-virtue profile, as *character* of the argument, not a score table).
2. **Ses failles** — the **localized fallacies** (with taxonomy descent path + family) and the **counter-arguments** that attack them (5 strategies). These are the dérapages.
3. **Sa tenue formelle** — the PL/FOL/modal/Dung verdicts cited as **verifiable proof**: "Tweety invalide cette inférence", "le cadre de Dung isole cette attaque comme défaillante". The formal result *backs a story beat*; it is never a standalone subsection.

> The movement is the unit, not the dimension. A single movement may cite a virtue (quality), a fallacy (informal), and a Tweety inconsistency (formal) — woven into one beat, not three parallel lists.

### 1.3 Acte III — Conclusion actionnable

- **Synthèse honnête** — the verdict, **gated** on non-trivial dimensions. Reuses #1008's verdict→prose bands (§2) and the waouh-contract gates G1–G4 (§3). No over-claim.
- **Appréciations** — strengths **and** weaknesses of the discourse (both, honestly).
- **Que faire de l'analyse** — how to **counter** the arguments, the **weak points to target**, and what to **expect next** (the probable follow-on moves — returning to the Acte I game-theoretic framing).

---

## 2. Block → shared-state key → capability mapping

The generator wires each narrative block to a shared-state key and a **capability looked up by snake_case name** (not by class). All keys below are verified present on `UnifiedAnalysisState` (`argumentation_analysis/core/shared_state.py`). When a key is empty/`None`/degraded, the block emits the **honest fallback wording** (right column) — never silent omission (#1019/#369).

| Narrative block | Shared-state key | Feeding capability (snake_case) | Honest fallback if empty/degraded |
|-----------------|------------------|---------------------------------|-----------------------------------|
| **I — Le texte** | `source_metadata` | `fact_extraction` (metadata facet) | "Métadonnées source indisponibles — contexte limité au texte analysé." |
| **I — Les enjeux** | `stakes_and_stakeholders` | `stakes_extraction` | "Enjeux non extraits — cadrage limité au microscope interne." |
| **I — Spectre attendu** | taxonomy walk (genre-relevant families) | `hierarchical_fallacy_detection` (taxonomy preview) | "Spectre anticipé indisponible (taxonomie non chargée) — lire Acte II sans filet d'attente." |
| **I — Game-theoretic** | `stakes_and_stakeholders` + `identified_arguments` structure | `stakes_extraction` + `fact_extraction` | "Cadrage stratégique indisponible." |
| **II — Argument inventory** | `identified_arguments` (`{arg_id: description}`) | `fact_extraction` | "Aucun argument extrait — l'analyse n'a pas de substrat." |
| **II — Qualité (vertus)** | `argument_quality_scores` (`[*.scores_par_vertu]`) | `argument_quality` / `quality_scoring` | "Profil de vertus indisponible (spacy/textstat indisponibles)." |
| **II — Failles : sophismes** | `identified_fallacies` (`family`, `taxonomy_path`, `target_arg_id`, `type`, `justification`) | `hierarchical_fallacy_detection` / `fallacy_detection` | "Aucun sophisme localisé." (honest if none found) |
| **II — Failles : contrage** | `counter_arguments` (`counter_content`, `strategy`) | `counter_argument_generation` | "Contre-arguments non générés." |
| **II — Tenue formelle PL** | `propositional_analysis_results` | `propositional_logic` | "Logique propositionnelle indisponible." |
| **II — Tenue formelle FOL** | `fol_analysis_results` (`consistent`, `formulas`) | `fol_reasoning` | "Logique du premier ordre indisponible." |
| **II — Tenue formelle modale** | `modal_analysis_results` | `modal_logic` | "Logique modale indisponible." |
| **II — Tenue formelle Dung/ASPIC** | `dung_frameworks`, `aspic_results` | `dung_extensions` / `aspic_plus_reasoning` | "Cadre de Dung indisponible — pas de cross-référence d'attaque." |
| **III — Synthèse (narrative)** | `narrative_synthesis` | `narrative_synthesis` | "Synthèse narrative dégradée — reconstruite depuis un contexte partiel." |
| **III — Synthèse (deep)** | `workflow_results` (enriched) | `deep_synthesis` | "Synthèse approfondie indisponible." |
| **III — Synthèse formelle** | `formal_synthesis_reports` | `formal_synthesis` | "Synthèse formelle indisponible." |
| **III — Verdict band** | computed: `_compute_verdict()` (#1008 §2) | (scorer, not a state key) | Gate G3 fails → fallback wording (#1008 §3.3). |
| **III — Cross-ref attaque↔sophisme** | `identified_fallacies` ↔ `dung_frameworks[*].attacks` | `hierarchical_fallacy_detection` + `dung_extensions` | "Cadre de Dung indisponible — pas de cross-référence." |

**Wiring verification rule** (carries over from #1008 §4): for each block, the generator MUST (1) look up the capability by **snake_case name** via `CapabilityRegistry.find_agents_for_capability` / `find_plugins_for_capability` / `find_services_for_capability`; (2) read the shared-state key; (3) if empty/`None`, emit the honest fallback; (4) if the data carries `degraded=True`, append the honest degradation note. **Never fabricate depth to fill a block** (anti-pendule, #1019/#369).

> The capability→state-key→phase→service traceability for *every* subsystem (neural fallacy, external solvers, JTMS/ATMS, governance, debate, dialogue, probabilistic, bipolar, ranking) is already exhaustive in #1008 §4 — **reference it, do not re-list it here**. R2/R3/R4 cite #1008 §4 for any subsystem not in the table above.

---

## 3. Verdict → prose (Acte III) — absorbs #1008 §2

Acte III's "Synthèse honnête" paragraph is **gated on the verdict band**, exactly as #1008 §2 specifies. The four bands and their allowed-claim templates (`EXCEEDED` / `MATCH` / `PARTIAL` / `BELOW`) are **defined in #1008 §2.2** and are not duplicated here. R4 (Acte III generator) MUST import/reference those templates.

**What this spec adds for the readable report**: the verdict paragraph is the *closing beat of a story*, not a comparative benchmark table. Where #1008 framed the conclusion as "pipeline vs external analyst", the restitution report frames it as **"what this discourse is, honestly"** — the verdict band governs how strong that characterisation may be, but the prose is narrative, not a scorecard.

- **EXCEEDED / MATCH** → the report may characterise the analysis as thorough, citing the non-trivial dimensions that earned the band.
- **PARTIAL** → honest, diagnostic: names what was touched and what was missed.
- **BELOW** → honest gap list; MUST NOT blame DLL/timeout without acknowledging the pipeline's graceful-degradation responsibility (#1008 §2.2 BELOW template, §6.3).

### 3.1 Non-triviality gates (carries #1008 §3 verbatim)

The conclusion block MUST NOT render until G1–G4 pass (from #1008 §3.2):

| Gate | Condition |
|------|-----------|
| **G1** | `len(identified_arguments) > 0` |
| **G2** | ≥1 of {fallacies, quality, counter-args, formal, Dung} has non-zero content |
| **G3** | verdict band computed |
| **G4** | all claimed metrics trace to real state keys (no placeholder/fallback) |

On any gate failure → the #1008 §3.3 honest fallback wording (names which gates failed and why). **No fabricated conclusion.**

---

## 4. The weaving rule — the load-bearing anti-énumeration contract

> **For EVERY citation of a formal or informal framework (Tweety, Dung/ASPIC, taxonomy descent, AIF/Walton, virtues), the report MUST provide a narrative anchor**: the framework is the *proof of a story point*, never an isolated list entry.

**Concrete contrast** (the differentiator *structure mécanique vérifiable > nom (latin) > nombre (score)*, told not listed):

- ❌ **Enumeration (forbidden)**: « Sophisme : *ad verecundiam* (score 0.8) » — a name and a number, detached from any story.
- ✅ **Narration (required)**: « L'orateur invoque une autorité ; cette autorité ne satisfait pas la question critique de fiabilité — c'est une **exception** au scheme *ExpertOpinion* (ancrage AIF/Walton), et le solveur Tweety **confirme** l'inconsistance de l'inférence. »

The reader reads a sentence that *says something*; the framework is the footnote that makes it *checkable*.

**Mechanical enforcement for R3/R6**: a framework reference is valid **iff** it is bound to (a) a located textual move (an argument/mouvement it speaks about) and (b) the concrete verdict that framework produced (the Tweety inconsistency, the Dung defeated attack, the taxonomy leaf reached). A framework block with neither anchor is an enumeration and MUST be rejected by the readability gate (R6) or rewritten.

---

## 5. Virtuous-text variant — Acte III titles the virtues

The engine must run on **virtuous texts** — the dataset contains some (possibly too few: *signal it, do not fabricate* — fail-loud). On such a text, where few/no fallacies are localized:

- **Acte III tilts toward the virtues**: robust formal tenue, intellectual honesty, well-held schemes become the headline, not the absence of fallacies.
- **Acte I anticipates differently**: "ce qui *pourrait* déraper mais ne dérape pas" — the expected spectrum vs the (absent) actual dérapages.
- **No fabrication of fallacies** to fill Acte II. If the descent found none, Acte II says so honestly and the report's value is the *virtuous* reading (formal consistency, quality profile), gated on G2 (a non-trivial dimension — here, quality/formal, not fallacies).

The virtuous variant is **not a separate skeleton** — it is the same 3 acts with the emphasis shifted by what the state actually contains. The generator selects emphasis from the *data*, never invents it.

### 5.1 Identifying virtuous inputs (R5)

R5 defines how a corpus input is flagged "virtuous" for this variant: a low (or zero) localized-fallacy count **combined with** a non-trivial formal/quality axis (so an empty run is not misread as "virtuous"). The flag is **derived**, never asserted: a text is virtuous iff the pipeline's own output says so. If the dataset lacks enough virtuous inputs, R5 reports that gap (fail-loud), it does not synthesize one.

---

## 6. What R6 replaces — the current dimensional render

The current report path lives in the [`argumentation_analysis/reporting/`](../../argumentation_analysis/reporting/) package (consolidated during Epic #317; the `scripts/run_real_analysis.py` path cited in some older docs no longer exists):

- `reporting.py:render_markdown_report(template_path, data)` — template-driven markdown emission.
- `document_assembler.py` — `UnifiedReportTemplate` + `ReportMetadata`, assembles sections into a final document.
- `section_formatter.py` — per-section formatting.

These currently produce the dimension-dump artifact (phase tables, corpus-by-corpus engineering provenance — see [`FB37_CAPSTONE_SPECTACULAR_REPORT.md`](../reports/FB37_CAPSTONE_SPECTACULAR_REPORT.md) for the concrete "illisible" shape). **R6's job is to assemble the 3 acts** (from R2/R3/R4 generators) into a single readable Markdown, **replacing** the dimensional dump as the default spectacular output, and to run the **readability gate** (§4 weaving rule: reject framework refs without a narrative anchor). The dimensional render may be retained as an *engineering appendix* (provenance), but it is no longer the report the reader meets first.

---

## 7. Generation protocol

1. Read the completed `UnifiedAnalysisState` from a spectacular run.
2. **Acte I** (R2): frame from metadata + stakes + taxonomy spectrum + game-theoretic read.
3. **Acte II** (R3): cluster `identified_arguments` into mouvements; for each, weave quality + fallacies + counter-args + formal tenue per the §2 mapping and the §4 weaving rule.
4. **Acte III** (R4): run gates G1–G4 (#1008 §3.2); compute verdict band (#1008 §2); emit the gated synthesis + appréciations + que-faire; tilt to virtues if the virtuous variant applies (§5).
5. **R6**: assemble the 3 acts into one Markdown; run the readability gate (§4); privacy-scrub (`_scrub_state_for_export` 11-pass + entity substr pattern, #1008 §6.2 step 7); emit under `docs/reports/` with opaque corpus ID (real-corpus reports stay gitignored).

**Anti-pendule reminders** (carry #1008 §6.3): do not replace `degraded=True` with fabricated variance; do not silently omit empty blocks (emit fallback wording); do not claim EXCEEDED/MATCH when BELOW; do not invent dimensions; **do not turn a narration back into an enumeration** (§4 is the guard).

---

## 8. DoD (this spec, #1135)

- [x] Three-act skeleton documented and unambiguous (§1).
- [x] Block → state-key → capability mapping table with verified keys + honest fallbacks (§2).
- [x] Verdict → prose defined (absorbed from #1008 §2, not duplicated) + non-triviality gates G1–G4 (§3).
- [x] Virtuous-text variant specified (§5).
- [x] Weaving rule — the anti-énumeration contract (§4).
- [x] Explicit reference to #1008 (reused, not duplicated) + #1082 / FB-20 terminal report.
- [x] Opaque IDs only, zero corpus content (structure and contract only).
- [x] Current render path identified for R6 to replace (§6).

## 9. Cross-references

- **#1008** — [`SPECTACULAR_ANALYSIS_SPEC.md`](SPECTACULAR_ANALYSIS_SPEC.md): verdict→prose (§2), waouh-contract G1–G4 (§3), full capability→state-key traceability (§4), yardstick D1–D10 (§5), generation protocol (§6). **The foundation this spec extends.**
- **#1082 / FB-20** — [`FB20_PHASE4_TERMINAL_REPORT.md`](../reports/FB20_PHASE4_TERMINAL_REPORT.md): the terminal report whose synthesis chain (FB-31 fail-loud, FB-33 template removal) feeds Acte III.
- **Shared-state schema** — `argumentation_analysis/core/shared_state.py` (`UnifiedAnalysisState`): all keys in §2 verified present.
- **Current render package** — `argumentation_analysis/reporting/` (`reporting.py`, `document_assembler.py`, `section_formatter.py`): what R6 replaces.
- **Epic #1134** — GitHub issue #1134 (Restitution): the parent epic and 3-act mandate.
- **Roadmap #78** — GitHub issue #78 (project roadmap): this report is the product surface (Democratech).

---

🤖 Spec authored by Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique for Epic #1134 / Track #1135.
