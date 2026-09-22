# Render reproducibility — the metric mandate's convention (#2353)

The user's metric mandate: **the final judge is the perception of the text** —
read the output, never a report about the output. A PR satisfies it by showing
a real render. This page is the one place where the convention for doing so is
written.

## The rule

**A PR that invokes the metric mandate cites the command that reproduces its
render, not only the result.** A render without a reproducible command does not
count as satisfying the mandate: from any other seat it can only be believed,
which is exactly the "report about the output" the mandate rules out.

Concretely:

1. **The producer is tracked; its output is not.** The script that produces the
   render lives under `scripts/`. What it writes lives under
   `argumentation_analysis/evaluation/results/` (gitignored — dataset privacy
   rule 3). The two rules coexist: the *producer* is what gets shared, never
   the output. A producer must refuse to write to a path git would track.
2. **Every render opens with a provenance header**: resolved route, effective
   model, corpus label (opaque), HEAD sha and dirty flag, the exact command,
   LLM request counts, SDK versions — and the **shape of the units** the
   render judged (word counts, never text). Two renders from two seats are
   comparable only through it; without it, the gap between them cannot be
   interpreted. Measured (#2353): three renders of one document on one seat
   judged units of 1–25 words, and whether 7 of 9 quality virtues were even
   applicable swung with it (#2403).
3. **Reproduction compares a property, not decimals.** LLM output fluctuates.
   What a second seat must find again is the *qualitative* property the PR
   reported (e.g. "units become discernible", "a virtue stops being uniformly
   null"), stated so that it can fail. **One render is not a reproduction**
   when an LLM step sits upstream of the measured one: run it several times
   and report each, or the property describes a session, not the code.
   Count absence apart from zero: a virtue "null" on 1 scored unit and not
   applicable on 6 is not "null on 7".
4. **Use the producer that measures the claimed object.** A neighbouring
   harness with a similar name often measures something else (FB-29 calls the
   agentic detectors directly; it does not measure what the production phase
   builds). Check what an instrument measures before citing it.

## Producers in the tree

| Render | Producer | Path exercised |
|---|---|---|
| Quality phase, wired vs lexical, per unit | `scripts/analysis/render_quality_phase.py --doc B` | `setup_registry → find_for_capability → invoke` for `fact_extraction` then `argument_quality`; the lexical arm is the phase's own named degraded path on the same units |

Add a row when a new render gains a producer. A render cited in a PR with no
row here is the defect #2353 describes.
