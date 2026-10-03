"""#2850 §3.3 — witness: the synthesis briefing's per-field budget spends
stratified, not head-first.

``build_artifact_briefing`` capped args and fallacies at
``max_items_per_field`` in INSERTION order (#2850 census debt): on a long
document the briefing cited the opening's artifacts only. The wiring spends
the same budget through ``select_for_budget`` — args on the merged
population, fallacies inheriting their target argument's offset — and
records both selections. Deterministic, no LLM (the briefing is built, not
sent).
"""

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

_N = 40
_BUDGET = 15


def _spread_state() -> UnifiedAnalysisState:
    """40 arguments over a 40,000-char text, plus 30 fallacies whose
    tail-targeting ones come LAST in insertion order."""
    cells = [f"cell{i:03d} " + "x" * 390 for i in range(_N)]
    state = UnifiedAnalysisState("\n".join(cells))
    for i in range(_N):
        state.add_argument(
            f"argument about cell{i:03d}",
            producer="kb_heuristic",
            source_quote=f"cell{i:03d}",
        )
    # fallacies: the first 20 target HEAD args, the last 10 target TAIL args
    # — insertion order puts the tail-targeting ones beyond the 15 cap.
    for j in range(20):
        state.add_fallacy(
            fallacy_type="Ad hominem",
            justification=f"head fallacy {j}",
            target_arg_id=f"arg_{j + 1}",
        )
    for j in range(10):
        state.add_fallacy(
            fallacy_type="Faux dilemme",
            justification=f"tail fallacy {j}",
            target_arg_id=f"arg_{_N - j}",
        )
    return state


def test_args_budget_spends_stratified():
    state = _spread_state()
    briefing = DeepSynthesisAgent.build_artifact_briefing(
        state, max_items_per_field=_BUDGET
    )
    # 15 arg lines — the cap holds (the pre-existing contract)...
    assert briefing.count("[artifact:identified_arguments.") == _BUDGET
    # ...and the selection is no longer the insertion-order head: on a
    # 40k text with 40 spread units, a stratified 15 must reach the last
    # third. Born red on the pre-wiring head slice.
    tail_ids = {
        arg_id
        for arg_id, prov in (state.argument_provenance or {}).items()
        if (prov.get("offset") or 0) >= 2 * len(state.raw_text) // 3
    }
    cited = {
        line.split("identified_arguments.")[1].split("]")[0]
        for line in briefing.splitlines()
        if "[artifact:identified_arguments." in line
    }
    assert cited & tail_ids, (
        "no last-third argument is cited — the budget still spends on the "
        "insertion-order head"
    )
    cov = (state.analysis_coverage or {}).get("synthesis_args")
    assert cov is not None and cov["k"] == _BUDGET and cov["N"] == _N
    assert cov["bands_covered"] == 3


def test_fallacies_budget_reaches_tail_targets():
    state = _spread_state()
    briefing = DeepSynthesisAgent.build_artifact_briefing(
        state, max_items_per_field=_BUDGET
    )
    # 15 fallacy lines; the tail-targeting fallacies sit at insertion
    # positions 20..29 — beyond the old head slice. Stratified on the
    # target's offset, tail bands are reached.
    assert briefing.count("[artifact:identified_fallacies.") == _BUDGET
    tail_targeted = {f"tail fallacy {j}" for j in range(10)}
    cited_tail = [t for t in tail_targeted if t in briefing]
    assert cited_tail, (
        "no tail-targeting fallacy is cited — fallacies still spend the "
        "budget on the insertion-order head"
    )
    cov = (state.analysis_coverage or {}).get("synthesis_fallacies")
    assert cov is not None and cov["k"] == _BUDGET and cov["N"] == 30
    assert (
        cov["bands_covered"] == 3
    ), "fallacies stratified on their targets' offsets must cover the bands"
