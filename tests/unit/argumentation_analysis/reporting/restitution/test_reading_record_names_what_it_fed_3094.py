"""#3094 — the reading record names what each bound fed.

The R1101 defect (paid pass, doc_A): Act II tied a head-read bound to a
judgment produced by whole-unit specialists working mid-document (quality and
counter at 0.42/0.50 of the text), then widened it to "toute conclusion
globale". The father was the block's contract: it listed ONLY the bounded
sites — nothing said what each read had fed, and no line said the run's
whole-text basis (89 units, 83 anchored beyond the head) — while the rule's
fixed example (« sur le début du document… ») was copied verbatim into the
render.

The fix is in the record, not the render: each reading line names what its
read fed (capability + the results resting on it, counts from the state's
own tables), the block carries the whole-text basis from
``argument_provenance`` (units, producers, bands, span), and the rule stops
offering a template phrase. Anti-pendulum: the bounds stay said, the windows
stay bounded, nothing is regexed.

Every assertion is on the prompt string built by the production path
(``build_act2_prompt(build_act2_evidence(state))``) — the #3082 harness:
a reverted production fails on the behaviour, never on an import. Counts
and opaque ids only, synthetic document.
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)
from argumentation_analysis.reporting.restitution.reading_record import (
    READING_BASIS_RULE,
)

_DOC_CHARS = 56_430
_EXTRACT_WINDOW = 3000
_PL_WINDOW = 4000

# Shaped like the R1101 run, scaled to 6 units: the LLM extraction read the
# head (3 units under the 3000 bound), the heuristic splitter anchored units
# at 0.42, 0.50 and 0.89 of the text — the mid-document material the quality
# and counter judgments actually rested on.
_OFFSETS_LLM = (100, 1_500, 2_900)
_OFFSETS_KB = (23_700, 28_200, 50_200)


def _state(with_units=True, llm_offsets=None, kb_offsets=None):
    state = SimpleNamespace()
    state.raw_text = "x" * _DOC_CHARS
    state.source_metadata = {}
    state.stakes_and_stakeholders = {
        "stakes": [],
        "stakeholders": [],
        "rhetorical_register": "",
        "discursive_arena": "",
    }
    state.deanonymized = True
    state.reading_window_status = {
        "fact_extraction": {
            "status": "selected",
            "offset": 0,
            "window": _EXTRACT_WINDOW,
        },
        "propositional_logic": {
            "status": "selected",
            "offset": 0,
            "window": _PL_WINDOW,
        },
        "fol_reasoning": {"status": "selected", "offset": 0, "window": _PL_WINDOW},
        # The fallacy workflow's sites (lot 7): the descent line must name
        # its confirmed findings in the reader's French (R1102 rework).
        "fallacy_widenet": {"status": "selected", "offset": 0, "window": 8000},
        "fallacy_descent": {"status": "selected", "offset": 0, "window": 500},
    }
    if llm_offsets is None:
        llm_offsets = _OFFSETS_LLM
    if kb_offsets is None:
        kb_offsets = _OFFSETS_KB
    if with_units:
        prov = {}
        for i, off in enumerate(llm_offsets):
            prov[f"arg_{i}"] = {
                "producer": "llm_extract",
                "offset": off,
                "offset_basis": "producer-recorded",
            }
        for i, off in enumerate(kb_offsets):
            prov[f"arg_{10 + i}"] = {
                "producer": "kb_heuristic",
                "offset": off,
                "offset_basis": "producer-recorded",
            }
        state.argument_provenance = prov
    else:
        state.argument_provenance = {}
    # The results each capability actually wrote on this synthetic run: the
    # fed phrases must carry their counts from the state, not a hand list.
    # #3105: real states tag each retained fallacy with the path that
    # produced it — an untagged entry is legacy, counted apart from the
    # descent, so this fixture tags its one fallacy as the descent's.
    state.identified_fallacies = {
        "fallacy_1": {
            "type": "Appel à l'autorité",
            "detection_paths": ["fallacy_descent"],
        }
    }
    state.propositional_analysis_results = [{"satisfiable": True}]
    state.fol_analysis_results = [{"satisfiable": True}]
    state.counter_arguments = [{"target": "arg_10"}]
    state.governance_decisions = []
    return state


def _prompts(state):
    return (
        build_act2_prompt(build_act2_evidence(state)),
        build_act3_prompt(build_act3_evidence(state)),
    )


def test_each_bounded_line_names_what_it_fed():
    """(a) The tie the R1101 render lacked: every bounded line says which
    results rest on it — the extraction line names its LLM units against the
    whole population, the logic lines name their formal verdicts."""
    p2, p3 = _prompts(_state())
    for name, p in (("Acte II", p2), ("Acte III", p3)):
        assert "a alimenté" in p, (
            f"{name} carries bounded reading lines that say nothing about "
            "what they fed — the R1101 defect: a bound the reader can attach "
            "to any judgment"
        )
        # The extraction line names its own units (3 llm_extract of 6 total).
        assert "3 unités sur 6" in p, (
            f"{name}: the extraction line must name its LLM units against "
            "the whole population — the split that keeps a head bound from "
            "being read as the run's whole basis"
        )
        # The logic lines name the formal verdicts their translation fed.
        assert "verdict" in p, (
            f"{name}: a logic reading line must name the formal verdicts "
            "that rest on its segment"
        )


def test_the_block_carries_the_whole_text_basis():
    """(b) The line the R1101 render generalized away: the run's material is
    N units spread over the text (bands, span) — a prompt that knows only
    the bounded reads cannot avoid generalizing them."""
    p2, p3 = _prompts(_state())
    for name, p in (("Acte II", p2), ("Acte III", p3)):
        assert "BASE DU RUN" in p and "TEXTE ENTIER" in p, (
            f"{name} carries no whole-text basis line: a reader seeing only "
            "bounded head reads must generalize them to every conclusion"
        )
        assert "6 unités" in p, f"{name}: the basis line must count the units"
        assert "3/3 bandes" in p, (
            f"{name}: the basis line must say the bands the units cover — "
            "the R1101 run covered 3/3 while the render said 'portion limitée'"
        )
        assert "0.89" in p, (
            f"{name}: the basis line must say the span — units anchored at "
            "0.89 of the text are what 'toute conclusion globale' rests on"
        )


def test_the_rule_carries_no_template_phrase():
    """(c) Rule leak guard: READING_BASIS_RULE offers no fixed French
    phrasing the narrative can copy — the R1101 sentence began with the
    rule's own example, verbatim."""
    assert "sur le début du document" not in READING_BASIS_RULE, (
        "the rule's example phrase is the template the R1101 render copied — "
        "the sentence must come from the record's lines, not from the rule"
    )
    p2, p3 = _prompts(_state())
    assert (
        "sur le début du document" not in p2
    ), "same phrase travels in Acte II's prompt"
    assert (
        "sur le début du document" not in p3
    ), "same phrase travels in Acte III's prompt"


def test_head_only_control_the_basis_is_the_opening():
    """Control: when only head reads exist (no per-unit results past the
    bound), the block says the analysis basis IS the opening — the bound
    stays sayable when it is true, instead of a whole-text line invented."""
    p2, _ = _prompts(_state(with_units=False))
    assert "l'ouverture du document" in p2, (
        "a run whose only material is the head must say so: the basis line "
        "names the opening, never a fabricated whole-text basis"
    )
    assert "TEXTE ENTIER" not in p2, (
        "no whole-text basis without units beyond the head — the two cases "
        "must not blur"
    )
    # The bounded k-of-N stays sayable in that control.
    assert f"{_EXTRACT_WINDOW} des {_DOC_CHARS}" in p2


def test_the_header_follows_the_measured_bands():
    """R1102 rework: the header's claim follows the measurement (#3073 shape
    — a label never stronger than its fact). Units anchored in the opening
    only (1/3 bands): the line states the measured span, never « TEXTE
    ENTIER »; the corpus campaign hits such documents (extraction stays in
    the head)."""
    # All six units anchored in the opening (max 2 100 / 56 430 = 0.04):
    # 1/3 bands, span 0.00–0.04 — the exact shape the campaign hits when
    # the extraction never leaves the head.
    p2, p3 = _prompts(
        _state(llm_offsets=(100, 1_500, 2_000), kb_offsets=(300, 1_200, 2_100))
    )
    for name, p in (("Acte II", p2), ("Acte III", p3)):
        assert "BASE DU RUN" in p, f"{name}: the basis line stays said"
        assert "TEXTE ENTIER" not in p, (
            f"{name}: 1/3 bandes ancrées — le header ne peut pas réclamer le "
            "texte entier pendant que son propre chiffre dit l'ouverture"
        )
        assert (
            "1/3 bandes" in p and "0.00–0.04" in p
        ), f"{name}: the measured span must be stated alone"


def test_unanchored_units_claim_no_span():
    """R1102 rework, absent-anchor control: units without offsets make no
    span claim at all — no « TEXTE ENTIER », the non-measurement is named."""
    state = _state()
    prov = state.argument_provenance
    for entry in prov.values():
        entry.pop("offset", None)
    p2, _ = _prompts(state)
    assert "TEXTE ENTIER" not in p2
    assert "étendue non dite" in p2


def test_producers_render_under_reader_labels():
    """R1102 rework: raw producer ids never reach a prompt the acts copy
    from (#2980 shape) — one label table, the way sites have theirs; an
    unknown producer keeps its id rather than being dropped."""
    p2, p3 = _prompts(_state())
    for name, p in (("Acte II", p2), ("Acte III", p3)):
        assert (
            "kb_heuristic" not in p and "llm_extract" not in p
        ), f"{name}: raw producer ids are jargon the narrative can copy"
    assert "découpage heuristique" in p2 and "extraction LLM" in p2

    from argumentation_analysis.reporting.restitution.reading_record import (
        _whole_text_basis,
    )

    odd = SimpleNamespace(argument_provenance={"a": {"producer": "producer_mystery"}})
    assert "producer_mystery" in _whole_text_basis(odd, 100)


def test_fallacy_descent_fed_is_reader_french():
    """R1102 rework: « au state » is internal jargon — the descent line names
    its confirmed findings in the reader's French (« retenus »)."""
    p2, p3 = _prompts(_state())
    for name, p in (("Acte II", p2), ("Acte III", p3)):
        assert "au state" not in p, f"{name}: internal jargon in the fed phrase"
        assert (
            "1 retenu" in p or "retenus" in p
        ), f"{name}: the descent's findings must be named readably"
