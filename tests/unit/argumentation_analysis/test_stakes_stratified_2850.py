"""#2850 §3.3 — witness: the stakes budget spends stratified, not head-first.

The stakes extractor's site was named debt in the #2850 census
(``stakes_extractor.py`` ``arguments[:30]``): the first 30 arguments in
insertion order reach the prompt, the rest of the document never does. The
wiring (in ``_invoke_stakes_extractor``, the same pattern as jtms/quality/
PL/FOL/NL→logic) spends the same 30 stratified over the text through
``select_for_budget`` and records its coverage under the ``stakes`` phase.

Offline by construction: the LLM call is a capturing fake threaded through
the site's own ``llm_call`` seam; no client, no key, no network.
"""

from types import SimpleNamespace

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_stakes_extractor,
)

_N = 90  # arguments, one per 600-char cell of a 54,000-char text


def _spread_state() -> UnifiedAnalysisState:
    """90 arguments with resolved offsets spread over the whole text."""
    cells = [f"cell{i:03d} " + "x" * 590 for i in range(_N)]
    state = UnifiedAnalysisState("\n".join(cells))
    for i in range(_N):
        state.add_argument(
            f"argument about cell{i:03d}",
            producer="kb_heuristic",
            source_quote=f"cell{i:03d}",
        )
    return state


def _tail_texts(state: UnifiedAnalysisState):
    """Argument TEXTS whose offset sits in the last third of the text."""
    raw = state.raw_text
    lo, hi = 0, len(raw)
    texts = []
    for arg_id, prov in (state.argument_provenance or {}).items():
        off = prov.get("offset")
        if off is not None and off >= lo + 2 * (hi - lo) // 3:
            texts.append(str(state.identified_arguments.get(arg_id, "")))
    return [t for t in texts if t]


async def test_stakes_budget_spends_stratified(monkeypatch):
    state = _spread_state()
    tail = _tail_texts(state)
    assert tail, "fixture must place units in the last third"

    captured = {}

    async def fake_llm_call(client, **kwargs):
        captured["prompt"] = kwargs["messages"][0]["content"]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"stakes": [], "stakeholders": [], '
                            '"rhetorical_register": "", "discursive_arena": ""}'
                        )
                    )
                )
            ]
        )

    monkeypatch.setattr(
        "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
        lambda: (object(), "model-x"),
    )
    monkeypatch.setattr(
        "argumentation_analysis.orchestration.invoke_callables._get_determinism_params",
        lambda: {},
    )
    monkeypatch.setattr(
        "argumentation_analysis.orchestration.invoke_callables._guarded_chat_completion",
        fake_llm_call,
    )

    await _invoke_stakes_extractor(state.raw_text, {"_state_object": state})

    prompt = captured.get("prompt", "")
    assert prompt, "the stakes prompt never reached the llm_call seam"

    # The block must carry units from the LAST third of the text — the head
    # slice never reaches them. Born red on the pre-wiring main.
    block = prompt.split("Arguments identified (indexed 0..N):")[1].split(
        "Source metadata:"
    )[0]
    reached = [t for t in tail if t[:200] in block]
    assert reached, (
        "no last-third unit reached the stakes prompt — the budget is still "
        "spent on the insertion-order head"
    )

    # The selection is recorded: k=30 of 90, all three text bands.
    cov = (getattr(state, "analysis_coverage", None) or {}).get("stakes")
    assert cov is not None, "the stakes selection never recorded its coverage"
    assert cov["k"] == 30 and cov["N"] == _N
    assert cov["bands_covered"] == 3, "a stratified 30/90 must cover every band"
