"""#3432 (ask 3) — an announced check is closed, never left open in silence.

The panel measured the defect on `5075cd82` (cycle 2, #3374): Acte I's framing
announced a false dilemma **as a point to test**, and Acts II–III never settled
it. The reader is left holding a promise the report never keeps.

The code already carried ONE thing from Acte I to Acte III — the closing
interpretive question (#1914, ``state.interpretive_question``). A point the
framing announces in its prose is a *different* announcement: it rode nowhere,
so no act could close it. This slice adds the missing carrier, symmetric with
the question's:

* Acte I's prompt instructs the conductor to emit, after the question, one
  ``POINT À TRANCHER : <le point>`` line per announced point (at most 3), and
  none when the framing announces none.
* :func:`build_act1_framing` extracts those lines into
  ``Act1Result.announced_checks`` — bounded, de-duplicated, in reading order,
  EMPTY when there is no marker (honest absence, never a fabricated check).
* The carrier is the STATE (``announced_checks``), persisted by BOTH
  orchestration lanes and READ by :func:`build_act3_evidence`.
* The Acte III prompt renders a [POINTS À TRANCHER] block in both states
  (#1941 discipline) and a consigne binding the conclusion: for each announced
  point, either the verdict the analysis establishes, or a plain statement that
  it was not reached.

Born-red discipline (sister of ``test_act1_interpretive_question_1914``): the
symbols born in this PR are imported INSIDE their tests. A module-level import
would turn the whole file into a collection error on the pre-fix tree — a
born-red that measures nothing.
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    Act1Result,
    build_act1_evidence,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# --- extraction: the marker is the carrier, prose is not ---------------------


_MARKED_NARRATIVE = (
    "### Le texte\n"
    "Le locuteur défend une thèse sur l'emploi.\n\n"
    "### La question\n"
    "QUESTION INTERPRÉTATIVE : La thèse tient-elle sur ce corpus ?\n"
    "POINT À TRANCHER : le faux dilemme entre emploi et salaire est-il "
    "réellement posé ?\n"
    "POINT À TRANCHER : la baisse annoncée est-elle établie par le texte ?\n"
)


def _extract(narrative: str):
    """Local import: the extractor is born in this PR (né-rouge discipline)."""
    from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
        _extract_announced_checks,
    )

    return _extract_announced_checks(narrative)


def test_extracts_each_announced_point_in_reading_order():
    checks = _extract(_MARKED_NARRATIVE)
    assert len(checks) == 2, f"expected both announced points, got {checks}"
    assert checks[0].startswith("le faux dilemme"), checks[0]
    assert checks[1].startswith("la baisse annoncée"), checks[1]
    assert all(
        "POINT À TRANCHER" not in c for c in checks
    ), "the marker itself is not part of the point"


def test_markdown_bold_around_the_marker_is_tolerated():
    narrative = "**POINT À TRANCHER : une incohérence à vérifier**\n"
    assert _extract(narrative) == ["une incohérence à vérifier"]


def test_no_marker_yields_the_empty_list():
    """Honest absence: a framing that announced nothing carries nothing —
    the carrier never fabricates a check to look complete."""
    assert _extract("### Le texte\nAucun point annoncé.\n") == []
    assert _extract("") == []


def test_plural_and_colon_variants_are_read():
    assert _extract("POINTS À TRANCHER : deux points distincts\n") == [
        "deux points distincts"
    ]


def test_the_list_is_bounded_and_de_duplicated():
    from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
        ANNOUNCED_CHECKS_CAP,
    )

    narrative = "".join(
        f"POINT À TRANCHER : point {i}\n" for i in range(ANNOUNCED_CHECKS_CAP + 3)
    )
    checks = _extract(narrative)
    assert (
        len(checks) == ANNOUNCED_CHECKS_CAP
    ), f"a framing is not a list: bound is {ANNOUNCED_CHECKS_CAP}, got {checks}"
    assert checks == [
        f"point {i}" for i in range(ANNOUNCED_CHECKS_CAP)
    ], "the bound keeps the first points in reading order"
    repeated = "POINT À TRANCHER : le même\nPOINT À TRANCHER : le même\n"
    assert _extract(repeated) == ["le même"], "a repeated point is carried once"


def test_the_question_extraction_is_unchanged():
    """Non-regression of #1914: adding the new marker must not disturb the
    question it sits beside."""
    from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
        _extract_interpretive_question,
    )

    assert (
        _extract_interpretive_question(_MARKED_NARRATIVE)
        == "La thèse tient-elle sur ce corpus ?"
    )


def test_act1_result_carries_the_field_empty_by_default():
    result = Act1Result(narrative="n", status="woven")
    assert (
        result.announced_checks == []
    ), "the carrier starts empty — a framing that announced nothing"


# --- the carrier: both lanes persist, Acte III reads -------------------------


def _state(**fields: object) -> SimpleNamespace:
    base = dict(
        source_metadata={},
        stakes_and_stakeholders={
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        },
        identified_arguments={},
        act1_framing="",
        interpretive_question="",
        announced_checks=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def test_pipeline_writer_persists_the_announced_checks():
    from argumentation_analysis.orchestration.state_writers import (
        _write_act1_framing_to_state,
    )

    state = _state()
    state.announced_checks = []
    _write_act1_framing_to_state(
        {
            "act1_framing": "narrative",
            "interpretive_question": "Q",
            "announced_checks": ["le dilemme", "la baisse"],
        },
        state,
        {},
    )
    assert state.announced_checks == ["le dilemme", "la baisse"], (
        "#3432: the pipeline lane must persist the announced points for "
        "Acte III to close them"
    )


def test_pipeline_writer_leaves_the_default_when_nothing_was_announced():
    from argumentation_analysis.orchestration.state_writers import (
        _write_act1_framing_to_state,
    )

    state = _state()
    state.announced_checks = []
    _write_act1_framing_to_state(
        {"act1_framing": "narrative", "interpretive_question": "Q"}, state, {}
    )
    assert (
        state.announced_checks == []
    ), "an absent key is an honest absence, never a fabricated empty entry"


def test_conversational_lane_persists_the_announced_checks():
    from argumentation_analysis.reporting.restitution.conversational_adapter import (
        _persist_announced_checks,
    )

    state = _state()
    state.announced_checks = []
    _persist_announced_checks(state, ["le dilemme"])
    assert state.announced_checks == [
        "le dilemme"
    ], "#3432: the two lanes must agree on the carrier"
    # Defensive twin of _persist_act: no attribute, no crash.
    _persist_announced_checks(SimpleNamespace(), ["le dilemme"])  # must not raise
    # Nothing announced → nothing written.
    _persist_announced_checks(state, [])
    assert state.announced_checks == ["le dilemme"]


# --- Acte III: the announced points are READ and the conclusion closes them --


def _act3_state(**fields: object) -> SimpleNamespace:
    base = dict(
        identified_arguments={"arg_1": "these A"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
        interpretive_question="La thèse tient-elle ?",
        announced_checks=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def test_act3_evidence_reads_the_announced_checks_from_state():
    evidence = build_act3_evidence(
        _act3_state(announced_checks=["le dilemme", "la baisse"])
    )
    assert evidence.announced_checks == ["le dilemme", "la baisse"], (
        "#3432: Acte III must READ the announced points from the state — "
        "written by Acte I, closed by Acte III"
    )


def test_act3_prompt_carries_each_announced_point():
    prompt = build_act3_prompt(
        build_act3_evidence(
            _act3_state(
                announced_checks=[
                    "le faux dilemme est-il réellement posé ?",
                    "la baisse annoncée est-elle établie ?",
                ]
            )
        )
    )
    assert "POINTS À TRANCHER" in prompt, "the block must be labelled"
    assert "le faux dilemme est-il réellement posé ?" in prompt
    assert "la baisse annoncée est-elle établie ?" in prompt


def test_a_different_announced_point_produces_a_different_prompt():
    one = build_act3_prompt(
        build_act3_evidence(_act3_state(announced_checks=["le dilemme"]))
    )
    two = build_act3_prompt(
        build_act3_evidence(_act3_state(announced_checks=["la baisse"]))
    )
    assert "le dilemme" in one and "le dilemme" not in two
    assert "la baisse" in two and "la baisse" not in one


def test_act3_prompt_without_announced_points_renders_honest_absence():
    """#1941 discipline: the block renders in BOTH states, so a silence is
    never read as "everything was settled"."""
    prompt = build_act3_prompt(build_act3_evidence(_act3_state()))
    assert "POINTS À TRANCHER" in prompt
    assert "n'a annoncé aucun point" in prompt
    assert "n'en fabrique pas un rétroactif" in prompt


def test_act3_consigne_binds_verdict_or_not_reached():
    """The measured defect was not a missing block: it was that nothing ever
    CLOSED the announced point. The consigne names both admissible outcomes —
    the verdict, or a plain statement that it was not reached — and names the
    silence as the defect being repaired."""
    prompt = build_act3_prompt(
        build_act3_evidence(_act3_state(announced_checks=["le dilemme"]))
    )
    flattened = " ".join(prompt.split())
    assert "Chacun est CLOS, nommément" in flattened
    assert "n'a pas été atteint" in flattened, (
        "the consigne must allow — and require — saying the point was not "
        "reached, not only reporting success"
    )
    assert "annoncé puis passé sous silence" in flattened


def test_act1_prompt_asks_for_the_marker_and_bounds_it():
    """Writer side: the marker only exists if the prompt asks for it, in the
    exact shape the extractor reads, with the same bound."""
    from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
        build_act1_prompt,
    )

    text = build_act1_prompt(build_act1_evidence(_state()))
    assert "POINT À TRANCHER : <le point, en une phrase>" in text
    assert "Au plus 3" in text
    assert "aucune ligne de ce type" in text, (
        "the prompt must say that announcing nothing is legitimate — an "
        "empty list is an honest absence, not a failure"
    )
