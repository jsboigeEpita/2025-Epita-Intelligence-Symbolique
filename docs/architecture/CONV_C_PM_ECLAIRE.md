# CONV-C — ProjectManager « éclairé » : conduite stratégique de l'analyse conversationnelle

| Field | Value |
|---|---|
| **Epic** | #1331 (Workflow agentique intégral) |
| **Track** | #1334 — CONV-C |
| **Status** | Design (draft, R504) — implementation to follow in separate PRs |
| **Depends on** | CONV-A (#1332, po-2025) for the baseline measurement harness |
| **Feeds** | CONV-D (#1335, restitution de la délibération) — consumes the deliberation trace defined here |
| **Owner** | myia-po-2023 |

> **Direction validated by coordinator (ai-01, R519)** in response to the two
> R503 findings. This document elaborates that direction into an implementation
> contract. The prompt rewrite, trace plumbing, and demonstrative run land in
> follow-up PRs against this design.

---

## 1. Mandate

The conversational path's `ProjectManager` (PM) agent must conduct the analysis
end-to-end as a **mandate-holding conductor** (mandate R376), not a
round-robin scheduler with bolted-on recipes. Concretely the PM must:

1. Hold an **intuition of the beginning and the end** — it opens the analysis
   (mission framing) and judges when the shared state is rich enough to
   converge.
2. Issue **motivated designations** — each `designate_next_agent(name)` is
   accompanied, in the trace, by a 1–2 sentence motivation (« I convene
   FormalAgent *because* InformalAgent surfaced a contradiction on arg_3 »),
   not round-robin rotation.
3. Make **deepening decisions conditioned on intermediate results** — whether
   to push further on a thread is a judgement the PM makes from the delta it
   observes, within a hard cap.
4. Judge the **stop condition** — but under a **hard cap that does NOT move**
   (lesson #708 DAG-runaway: the cap STAYS; the *choice within the cap* becomes
   LLM-driven).

**Anti-pendule (#1019) is load-bearing for this track.** The current PM prompt
is already heavily templatised (EXTRACTION GATE #595 + CROSS-KB ENRICHMENT
#208-I are hard-coded, sequence-dependent recipes). The fix for CONV-C is to
**subtract** that templatisation and replace it with mission + capability map +
motivated-designation requirement — **not** to add more rules on top. Adding
rules would swing the pendulum to a re-mechanised PM; the equilibrium is
reached by subtraction.

---

## 2. Diagnosis of the current state

The PM-conducted mechanism **already exists** mechanically — CONV-C is not
wiring a new control path, it is raising the quality of the existing one.

### 2.1 What exists (load-bearing, keep)

- **PM designation plumbing** — `StateManagerPlugin.designate_next_agent(name)`
  ([`state_manager_plugin.py:344`](../../argumentation_analysis/core/state_manager_plugin.py#L344))
  writes `state._next_agent_designated`
  ([`shared_state.py:242`](../../argumentation_analysis/core/shared_state.py#L242)).
- **Honouring** — `DelegatingSelectionStrategy` (wired in
  [`_run_phase` at conversational_orchestrator.py:1374`](../../argumentation_analysis/orchestration/conversational_orchestrator.py#L1374))
  consumes the designation via `state.consume_next_agent_designation()`
  ([`shared_state.py:279`](../../argumentation_analysis/core/shared_state.py#L279))
  and selects that agent. A round-robin fallback exists
  ([`_select_next_agent:1311`](../../argumentation_analysis/orchestration/conversational_orchestrator.py#L1311))
  for when no designation is set or the designated agent is not in the current
  phase.
- **Eight specialised agents** in `AGENT_CONFIG`
  ([`conversational_orchestrator.py:160`](../../argumentation_analysis/orchestration/conversational_orchestrator.py#L160)):
  `ProjectManager`, `ExtractAgent`, `InformalAgent`, `FormalAgent`,
  `QualityAgent`, `DebateAgent`, `CounterAgent`, `GovernanceAgent`.
- **Cross-KB capability surface** already exposed as kernel functions:
  `add_identified_argument`, `add_identified_fallacy`, `run_guided_analysis`,
  `evaluate_with_cross_kb_context`, `detect_conflicts`, `social_choice_vote`,
  `jtms_create_belief`, `jtms_check_consistency`.

### 2.2 What is templatised (subtract)

The PM prompt
([`conversational_orchestrator.py:163-188`](../../argumentation_analysis/orchestration/conversational_orchestrator.py#L163))
contains two hard-coded, sequence-dependent recipes:

- **EXTRACTION GATE (#595)** — « AVANT toute autre action, vérifie
  `identified_arguments`… Ne passe PAS à InformalAgent tant que vide ». This
  encodes a fixed ordering rule. The *invariant* (specialists write to a shared
  state; an empty state cannot be analysed) is correct and must survive — but
  as an **enunciated fact**, not a prescriptive gate.
- **CROSS-KB ENRICHMENT (#208-I)** — « Après ExtractAgent : … ENSUITE demande
  JTMS », « Après InformalAgent : demande QualityAgent … », etc. This is a full
  scripted choreography of synergies. The PM is being told the sequence rather
  than reasoning about it.

### 2.3 What is missing (add)

1. **No motivation is traced.** `designate_next_agent(name)` accepts only the
   name; the *why* is emitted in prose by the PM and lost (not in the shared
   state, not in any trace structure). This is the central gap — the
   deliberation trace that CONV-D must weave, that the metrics must count, and
   that the #708 audit must bound, does not exist as a data structure.
2. **No hard cap with fail-loud.** `_run_phase` has `max_turns` per phase
   (default 5) and `_bump_sk_budget` raises `LLMBudgetExceeded` on token count
   ([`conversational_orchestrator.py:1403`](../../argumentation_analysis/orchestration/conversational_orchestrator.py#L1403)),
   but there is no **pipeline-global** tour cap and the exhaustion path is not
   surfaced as a structured fail-loud record for the trace.
3. **No delta is recorded.** The PM observes state growth to decide deepening,
   but the before/after fingerprint used internally
   ([`_get_growth_fingerprint`](../../argumentation_analysis/orchestration/conversational_orchestrator.py#L1405))
   is not exposed to the deliberation trace — so the "conditioned on
   intermediate results" judgement is invisible.

---

## 3. Design principles

| # | Principle | Mechanism |
|---|---|---|
| P1 | **Motivated designation** | Each designation carries a 1–2 sentence motivation recorded in the trace. |
| P2 | **Hard cap, immovable** | A pipeline-global tour budget (plus the existing per-phase `max_turns` and LLM token cap) bounds the run. Exceeding it fails loud, recorded in the trace. (#708) |
| P3 | **LLM choice within the cap** | Inside the cap, *which* agent to convene next, *whether* to deepen, and *when* the state is rich enough are the PM's judgement — encoded as mission + capability map, not rules. |
| P4 | **Anti-pendule by subtraction** | The EXTRACTION-GATE and CROSS-KB recipes are removed. #595's invariant survives as a stated fact. The safety net is *measurement* (CONV-A → CONV-C delta), not a re-encoded rule. |
| P5 | **One spine, no second state object** | The strategic layer lives as new fields/methods on the existing `UnifiedAnalysisState` + `StateManagerPlugin` spine. **No bridge to `hierarchical/strategic/state.py`** (Hierarchical is dormant, #1313 — we do not wake a mode by side-effect). |

---

## 4. The deliberation trace (one structure, three consumers)

The trace is the shared material of: (1) CONV-A/CONV-C **metrics** (is the
conduction non-round-robin, demonstrably?), (2) the **#708 anti-runaway audit**
(cap respected, fail-loud on breach), (3) **CONV-D Act II** (the deliberation
narrative woven from real events). Design it once for all three.

### 4.1 Record structure

Each PM turn appends one record to `state.deliberation_trace`:

```python
# On UnifiedAnalysisState (new field)
deliberation_trace: list[DesignationRecord]

@dataclass
class DesignationRecord:
    turn: int                       # pipeline-global turn index
    designated_agent: str           # exact name, e.g. "FormalAgent"
    motivation: str                 # 1–2 sentences, PM-authored, WHY now
    trigger: str                    # "initial" | "deepening" | "synergy" | "convergence"
    state_fingerprint_before: dict  # growth fingerprint (dims covered, counts)
    state_fingerprint_after: dict   # filled when the designated agent returns
    delta_summary: str              # human-readable delta the PM observed
```

### 4.2 Three consumers

- **Metrics (CONV-A/C)** — derive from the trace: designation diversity
  (non-round-robin = the sequence is not a cyclic permutation of the roster),
  motivation presence (every record has a non-empty `motivation`), deepening
  count (records with `trigger="deepening"` conditioned on a non-empty
  `delta_summary`), cap adherence.
- **Audit (#708)** — `trigger` + `turn` vs the hard cap; a breach emits a
  `CapBreachRecord` (fail-loud) appended to the same trace.
- **CONV-D Act II** — the restitution weaves `motivation` + `delta_summary`
  pairs into the deliberation narrative. **It may only narrate events present
  in the trace** (cross-check #1316 extends to these claims — no fabricating
  deliberation that the trace does not contain).

---

## 5. PM prompt rewrite (skeleton)

The rewrite **replaces** the EXTRACTION-GATE and CROSS-KB blocks. It states
mission + capability map + motivation requirement + budget. It does **not**
prescribe sequence.

```
Tu es le chef de projet. Tu conduis l'analyse pour produire un ÉTAT RICHE
(couverture de toutes les dimensions pertinents du texte), pas pour suivre
un script.

A chaque tour :
1. Lis l'etat via get_current_state_snapshot().
2. Décide, en fonction de ce qui manque ou de ce qu'un résultat intermédiaire
   t'apprend, quel spécialiste doit parler ensuite — et POURQUOI.
3. Enregistre ta décision via record_designation(agent, motivation, trigger)
   (la motivation est obligatoire : 1-2 phrases sur ce qui te fait convoquer
   cet agent maintenant).
4. Désigne l'agent via designate_next_agent(nom_exact) et pose-lui une question
   précise.

CARTE DES CAPACITÉS (tu dois savoir que ces synergies existent — c'est à toi
d'en juger l'opportunité, personne ne te l'impose) :
- ExtractAgent — extrait les arguments (add_identified_argument) ; sans
  arguments extraits, l'état est vide et rien d'autre n'a de substrate.
  [Fait : les spécialistes travaillent sur l'état partagé ; tant que
  l'extraction n'a rien enregistré, l'état est vide.]
- InformalAgent — sophismes (run_guided_analysis, add_identified_fallacy).
- FormalAgent — cohérence logique (inconsistances signalées).
- QualityAgent — peut évaluer EN CONTEXTE des sophismes détectés
  (evaluate_with_cross_kb_context).
- CounterAgent — peut cibler les arguments faibles.
- DebateAgent — positions adversariales ; GovernanceAgent — consensus,
  conflits, vote (detect_conflicts, social_choice_vote).
- JTMS — croyances et rétractations (jtms_create_belief,
  jtms_check_consistency) ; une rétractation peut invalider un fil.

BUDGET : tu as au plus {N} tours pour couvrir l'analyse. La couverture prime
sur l'épuisement du budget, mais le budget est dur — si tu l'atteins sans
converger, enregistre-le (le dépassement est tracé, pas silencieux).

CONVERGENCE : quand l'état est suffisamment couvert (dimensions pertinentes
remplies, consensus évalué si des positions divergent), appelle
set_final_conclusion() avec ta synthèse.
```

The bracketed `[Fait : …]` line is the surviving form of #595 — an enunciated
fact the PM reasons about, not a gate it must obey.

---

## 6. Budget guard — hard cap, fail-loud (#708)

- **Per-phase cap** — `max_turns` in `_run_phase` (already present).
- **Pipeline-global cap** — new: a total tour budget across phases (default
  derived from corpus size, surfaced to the PM as `{N}` in the prompt). The
  cap is **not adjusted at runtime** — it is a fixed contract.
- **Token cap** — `_bump_sk_budget` / `LLMBudgetExceeded` (already present,
  [`invoke_callables.py`](../../argumentation_analysis/orchestration/invoke_callables.py)).
- **Fail-loud on breach** — when any cap is hit, a `CapBreachRecord` (cap kind,
  turn, partial trace) is appended to `deliberation_trace` and the run ends
  with a structured status (`BUDGET_EXHAUSTED`), not a silent truncation. The
  PM's stop-condition judgement lives **inside** the cap; the cap itself is the
  non-negotiable backstop.

This is the #708 lesson applied: the cap does not become an LLM variable.

---

## 7. Implementation contract

New surface on the existing spine (`UnifiedAnalysisState` +
`StateManagerPlugin`). No new state object, no import from `hierarchical/`.

### 7.1 `StateManagerPlugin` — new kernel function

```python
@kernel_function(
    description="Enregistre une désignation motivée (agent + pourquoi + type de déclencheur).",
    name="record_designation",
)
def record_designation(self, agent: str, motivation: str, trigger: str) -> str:
    # appends a DesignationRecord to state.deliberation_trace
    # (state_fingerprint_before captured here; _after/delta filled on return)
```

`designate_next_agent(name)` is **kept** (the selection plumbing already reads
it); `record_designation` is the trace-writing companion the PM calls first. We
do not collapse them into one function — the trace record and the selection
signal serve different readers and may decouple (e.g. an audit-only record).

### 7.2 `UnifiedAnalysisState` — new field

```python
deliberation_trace: list[DesignationRecord]  # init in __init__, snapshot in get_state_snapshot
```

`get_state_snapshot` exposes a summarised view so CONV-D and the metrics read
one source of truth.

### 7.3 `_run_phase` — delta backfill

After the designated agent returns, backfill the current `DesignationRecord`'s
`state_fingerprint_after` and `delta_summary` from the growth fingerprint already
computed ([`_get_growth_fingerprint`](../../argumentation_analysis/orchestration/conversational_orchestrator.py#L1405)).
This makes the "conditioned on intermediate results" judgement inspectable
without a new measurement path.

---

## 8. Safety net = measurement, not rules

The #595 extraction-ordering concern existed because early PM runs formalised on
an empty state (the same shape as the `nl_to_logic` starvation). CONV-C does
**not** re-encode the fix as a rule. Instead the tracks themselves are the net:

- **CONV-A (#1332, po-2025)** measures the baseline with the **current**
  templatised prompt on the spectacular harness.
- **CONV-C** applies the de-templatised prompt.
- The **delta on the same harness** is measured. If the de-templatised PM stops
  extracting first, it shows in the metrics (empty early state), and we iterate
  on the **information** given to the PM (the capability map / facts), not on
  rules.

This is the anti-pendule discipline: the protection is empirical visibility,
not a counterweight rule.

---

## 9. DoD

- [ ] PM prompt rewritten per §5 (mission + capability map + motivation
      requirement + budget; EXTRACTION-GATE and CROSS-KB recipes removed;
      #595 survives as enunciated fact).
- [ ] `record_designation` kernel function + `deliberation_trace` field +
      snapshot exposure (§7.1–7.2).
- [ ] `_run_phase` backfills `state_fingerprint_after` / `delta_summary` (§7.3).
- [ ] Pipeline-global tour cap with `CapBreachRecord` fail-loud (§6).
- [ ] **Trace run** demonstrating non-round-robin conduction: ≥1 motivated
      deepening (a `trigger="deepening"` record with non-empty `delta_summary`
      conditioned on an observed result), and a designation sequence that is
      not a cyclic permutation of the roster.
- [ ] No new dependency on `hierarchical/strategic/state.py`.

---

## 10. Risks & non-objectives

- **Non-objective — specialists DECIDE in-conversation.** That is CONV-B
  (#1333), gated on #1339 (SPASS routing at the shared layer so direct
  ModalHandler callers — including future conversational tool-calls — do not
  hit the OOM-prone default). CONV-C makes the PM a better conductor; it does
  not by itself make the specialists' solvers decide. The two tracks compose.
- **Risk — over-subtraction.** Removing the recipes could regress early-turn
  extraction. Mitigation = the CONV-A/C measurement net (§8); if it regresses,
  restore information (not rules).
- **Risk — motivation as theatre.** The PM could emit boilerplate motivations.
  Mitigation = the metrics check that `delta_summary` is non-empty and that the
  designated agent is the one the motivation actually justifies (loose
  coherence check at metric time, not in the prompt).
- **Non-objective — merging with the Sherlock/Moriarty interrogation pattern**
  ([`sherlock_enquete_agent.py`](../../argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py)).
  That pattern is a reference for *motivated questioning*, not a merge target —
  the conversational PM keeps its SK `AgentGroupChat` spine.

---

## 11. References

- Epic #1331; tracks #1332 (CONV-A), #1333 (CONV-B), #1334 (CONV-C, this doc), #1335 (CONV-D).
- #708 (DAG-runaway cap lesson), #1019 (anti-pendule), #595 (extraction invariant), #208-I (cross-KB), #1316 (post-render honesty cross-check).
- #1313 (Hierarchical dormant — reason for no StrategicState bridge).
- #1339 (SPASS routing prerequisite for CONV-B).
- Code: [`conversational_orchestrator.py`](../../argumentation_analysis/orchestration/conversational_orchestrator.py),
  [`state_manager_plugin.py`](../../argumentation_analysis/core/state_manager_plugin.py),
  [`shared_state.py`](../../argumentation_analysis/core/shared_state.py),
  [`strategies.py`](../../argumentation_analysis/core/strategies.py).
