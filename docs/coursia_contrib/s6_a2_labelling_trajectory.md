# S6-A2 — Discourse as a substrate: Dung labelling trajectory

**Track**: S6-A2 (issue #1506) · **Epic**: CoursIA strate-6 ICT.
**CoursIA gate**: Phase-A candidate **#1** for seed
[`jsboige/CoursIA#7289`](https://github.com/jsboige/CoursIA/issues/7289) —
"the discourse as a substrate" — one of the ≥2 independent falsifiability
substrates required by contract [`jsboige/CoursIA#7291`](https://github.com/jsboige/CoursIA/issues/7291).
**Engine**: [`argumentation_analysis/orchestration/dung_labelling_trajectory.py`](../../argumentation_analysis/orchestration/dung_labelling_trajectory.py) ·
**CLI**: [`scripts/labelling_trajectory.py`](../../scripts/labelling_trajectory.py).

## The thesis

A discourse does not arrive all at once — it delivers arguments one by one, in a
rhetorical order. Under Dung's grounded semantics, each prefix of the arrival
sequence induces a **labelling** of the arguments seen so far:

- **in** — accepted (defended) arguments,
- **out** — arguments attacked by some accepted argument,
- **undec** — the rest (typically cycles, undecided in isolation).

The sequence of labellings across the arrival is a **trajectory of states**. As
the discourse unfolds, an argument's status *evolves*: a claim accepted early is
**refuted** (`in → out`) when a later attacker lands; a cycle member that was
**undecided** is **reinstated** (`undec → in`) when a defender arrives. This
trajectory is the substrate: it turns a static abstract argumentation framework
into a *process* that a downstream model (e.g. a belief-state transition matrix,
the sibling S6-A1 substrate) can read off.

## The canonical exemplar

A structurally-realistic synthetic framework with **opaque ids** (privacy HARD)
exhibiting all three dynamics:

| step | arrived | in | out | undec |
|-----:|---------|----|----|-------|
| 1 | `prop_thesis` | `prop_thesis` | — | — |
| 2 | …`prop_cycle_a` | +`prop_cycle_a` | — | — |
| 3 | …`prop_cycle_b` | `prop_thesis` | — | `prop_cycle_a, prop_cycle_b` |
| 4 | …`prop_counter` | `prop_counter` | `prop_thesis` | `prop_cycle_a, prop_cycle_b` |
| 5 | …`prop_defender` | `prop_counter, prop_defender, prop_cycle_b` | `prop_thesis, prop_cycle_a` | — |

Dynamics, verified firsthand (`pytest tests/unit/argumentation_analysis/orchestration/test_dung_labelling_trajectory.py`):

- **Refutation**: `prop_thesis` `in` (steps 1–3) → `out` (step 4) when
  `prop_counter` lands and is itself accepted.
- **Reinstatement**: `prop_cycle_b` `undec` (steps 3–4) → `in` (step 5) when
  `prop_defender` attacks `prop_cycle_a`, thereby defending `prop_cycle_b`.

## Reproduce

```bash
# Render the trajectory table + transitions
python scripts/labelling_trajectory.py --exemplar discourse

# Cross-check the native grounded extension against Tweety on the full AF
# (honest degradation if the JVM is unavailable)
python scripts/labelling_trajectory.py --exemplar discourse --cross-check-tweety

# JSON export
python scripts/labelling_trajectory.py --json trajectory.json
```

## Backends & anti-théâtre

The trajectory reuses the pure-Python
[`abs_arg_dung.backends.compute_grounded`](../../abs_arg_dung/backends/native.py)
reasoner (the I5 #1502 multi-backend comparison's native side, with the direction
inversion fixed on `main`). No Dung semantics are reimplemented here
(anti-pendule). The CLI offers an optional native-vs-Tweety grounded cross-check
on the full AF: the two backends must agree, or the disagreement is reported
verbatim — never auto-reconciled (anti-théâtre #1019). If the JVM is unavailable,
the trajectory (computed JVM-free) still stands; the cross-check degrades
honestly.

## Scope & honesty (what this is, and is not)

- **What it is**: a Phase-A *candidate substrate* — the trajectory-of-labellings
  concept, made executable and falsifiable on a structural exemplar.
- **What it is not (yet)**: a corpus-derived AF. Deriving an AF from a real
  discourse requires the text → arguments → attacks extraction pipeline and is
  privacy-sensitive; it is a deliberate follow-up, out of scope for this
  candidate. The exemplar uses **opaque `prop_*` ids** with **no source content**
  and **no corpus access** — privacy HARD.
- **Falsifiability**: the trajectory is deterministic and machine-checked. If
  grounded semantics on the exemplar did not produce the refutation/reinstatement
  dynamics above, the substrate would be falsified — it is not asserted, it is
  computed.

## Relation to the sibling substrate

S6-A1 (po-2025) produces candidate **#2** — a transition matrix over *belief
states* extracted from a real source. This candidate **#1** is its symbolic
complement: a trajectory over *labelling states* from abstract argumentation. The
two are independent (one reasons over belief states, the other over Dung
labellings), satisfying the contract's ≥2-substrate requirement.

— Track S6-A2 · worker myia-po-2023 · #1506
