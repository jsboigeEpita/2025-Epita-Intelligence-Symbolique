"""#3558 — the per-argument pass records what it concluded on each unit.

Measured on cycle 7 of the panel: the stage ``examined_no_finding`` held
severe items (doc_C, doc_E) where the per-argument fallacy pass HAD examined
the covering unit and kept no finding — and the render let that judgment of
« propre » read as « jamais examiné » (the doc_E judge note). The coverage
record ``analysis_coverage.fallacy_per_argument`` held ``unit_ids`` (which
units were selected) and never what the pass concluded on each; the
conclusions lived only in ``identified_fallacies``, keyed by target, so an
examined unit with no finding left no trace that it was judged at all.

The repair: the pass records, per ANSWERED walk, the findings it kept on
that unit (0 = examined and clean — a recorded judgment the render and the
tracer can read); the soutiens movement carries the verdict where it names
such an argument and states what it holds in the counted form the
first-reading note uses. A walk that got no answer concludes nothing and
stays out (#3326's ``examined_ids`` rule); a state recorded before the fix
renders byte-identically (no outcome key ⇒ no verdict line, no count line).

Born red on ``main`` ``87044be93``: the record holds no ``per_unit_outcomes``
and the soutiens block carries no verdict and no count. Free witness — no
key, no network, no corpus; synthetic texts only.
"""

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState

SOURCE_TEXT = (
    "Une première unité synthétique assez longue pour être analysée par la "
    "passe par argument, avec un propos tenable. "
    "Une deuxième unité synthétique assez longue pour être analysée par la "
    "passe par argument, elle aussi avec un propos tenable."
)


def _synthetic_state() -> UnifiedAnalysisState:
    """Two offset-carrying units (arg_1, arg_2) — both inside any budget."""
    state = UnifiedAnalysisState(SOURCE_TEXT)
    state.add_argument(
        "Unité synthétique numéro un portant un propos analysable.",
        producer="llm_extract",
        offset=0,
    )
    state.add_argument(
        "Unité synthétique numéro deux portant un propos analysable.",
        producer="llm_extract",
        offset=300,
    )
    return state


def _walk_double():
    """A walker double: one canned finding on arg_1, none on arg_2.

    The double tracks the walk's real signature (#3416/#3428 — document
    statements and frame ride the call; a state without a first reading
    hands [] and {}).
    """
    import argumentation_analysis.orchestration.invoke_callables as ic

    calls: list[str] = []

    async def _walk(
        arg_text,
        arg_id,
        llm_service,
        taxonomy_path,
        document_statements=None,
        document_frame=None,
    ):
        calls.append(arg_id)
        if arg_id == "arg_1":
            return {
                "fallacies": [
                    {
                        "type": "appel_a_la_peur",
                        "fallacy_type": "Appel à la peur",
                        "taxonomy_pk": "appel_a_la_peur",
                        "explanation": "justification synthétique du témoin",
                        "target_argument": arg_id,
                        "confidence": 0.9,
                    }
                ],
                "extraction_method": "guided",
                "source_arg_id": arg_id,
            }
        return {
            "fallacies": [],
            "extraction_method": "guided",
            "source_arg_id": arg_id,
        }

    return calls, _walk, ic


async def _run_pass_and_write(state: UnifiedAnalysisState, monkeypatch, walk):
    """Drive the real invoker, then the real fallacy state writer.

    The writer is the one the pipeline lane uses for this pass's findings
    (``_write_hierarchical_fallacy_to_state`` — the same merge the winner
    reading routes through, #3326), so the finding reaches
    ``identified_fallacies`` exactly as on a run.
    """
    import argumentation_analysis.orchestration.state_writers as sw

    monkeypatch.setattr(
        "argumentation_analysis.orchestration.invoke_callables._walk_single_fallacy_unit",
        walk,
    )
    output = await _ic()._invoke_hierarchical_fallacy_per_argument(
        SOURCE_TEXT, {"_state_object": state}
    )
    sw._write_hierarchical_fallacy_to_state(
        {"fallacies": output.get("fallacies", [])}, state, {}
    )
    return output


def _ic():
    import argumentation_analysis.orchestration.invoke_callables as ic

    return ic


def _prompt(state: UnifiedAnalysisState) -> str:
    from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
        build_act2_evidence,
        build_act2_prompt,
    )

    return build_act2_prompt(build_act2_evidence(state))


def _soutiens_block(prompt: str) -> str:
    """The soutiens movement's block, from its header to the next block.

    The soutiens movement closes the thread, so the slice would otherwise
    run to the prompt's end — through the per-act label legend (#3296),
    which names EVERY unit's letter. The legend is cut like a block.
    """
    marker = "MOUVEMENT « soutiens »"
    start = prompt.find(marker)
    assert start >= 0, "the soutiens movement is missing from the prompt"
    ends = [
        e
        for e in (
            prompt.find("MOUVEMENT «", start + len(marker)),
            prompt.find("LÉGENDE DES DÉSIGNATIONS", start + len(marker)),
        )
        if e >= 0
    ]
    return prompt[start : min(ends)] if ends else prompt[start:]


#: The prompt relabels arg_N by the per-act table (#3296, ``unit_labels``):
#: arg_1 renders as α, arg_2 as β. The witness asserts on the labels the
#: READER meets, never on the raw ids (which the seam exists to hide).
_LABEL_ARG_1 = "α"
_LABEL_ARG_2 = "β"


class TestTheRecordStatesWhatThePassConcluded:
    """Ask 1 — per examined unit, the findings the pass kept, or none."""

    async def test_both_outcomes_are_recorded(self, monkeypatch):
        state = _synthetic_state()
        calls, walk, ic = _walk_double()
        output = await _run_pass_and_write(state, monkeypatch, walk)

        assert sorted(calls) == ["arg_1", "arg_2"]
        cov = state.analysis_coverage["fallacy_per_argument"]
        # The pass's own conclusion: one finding kept on arg_1, none on
        # arg_2 — « examined and clean » is now a recorded judgment.
        assert cov["per_unit_outcomes"] == {"arg_1": 1, "arg_2": 0}
        # The invoker emits the same map on its output (the seam both lanes
        # read).
        assert output["per_unit_outcomes"] == {"arg_1": 1, "arg_2": 0}
        # Positive control: the record still names the SELECTION's units —
        # the witness reads the real record, not a parallel one.
        assert cov["unit_ids"] == ["arg_1", "arg_2"]
        # And the kept finding reached the fallacy surfaces.
        assert list(state.identified_fallacies)

    async def test_a_walk_that_got_no_answer_concludes_nothing(self, monkeypatch):
        state = _synthetic_state()

        async def _walk(
            arg_text,
            arg_id,
            llm_service,
            taxonomy_path,
            document_statements=None,
            document_frame=None,
        ):
            if arg_id == "arg_2":
                # #2540 — a failed call comes back shaped, not raised.
                return {
                    "error": "endpoint indisponible",
                    "fallacies": [],
                    "source_arg_id": arg_id,
                }
            return {
                "fallacies": [
                    {
                        "type": "appel_a_la_peur",
                        "taxonomy_pk": "appel_a_la_peur",
                        "explanation": "j",
                        "target_argument": arg_id,
                        "confidence": 0.9,
                    }
                ],
                "extraction_method": "guided",
                "source_arg_id": arg_id,
            }

        output = await _run_pass_and_write(state, monkeypatch, _walk)
        cov = state.analysis_coverage["fallacy_per_argument"]
        # arg_2 was SELECTED (unit_ids) but its walk got no answer: it
        # concludes nothing — selected is not examined (#3326's rule).
        assert cov["unit_ids"] == ["arg_1", "arg_2"]
        assert cov.get("per_unit_outcomes", {}) == {"arg_1": 1}
        assert output["per_unit_outcomes"] == {"arg_1": 1}


class TestTheRenderCarriesTheVerdict:
    """Asks 2 and 3 — the soutiens movement states what it holds, counted."""

    async def test_the_examined_clean_verdict_rides_the_line(self, monkeypatch):
        state = _synthetic_state()
        calls, walk, ic = _walk_double()
        await _run_pass_and_write(state, monkeypatch, walk)

        prompt = _prompt(state)
        soutiens = _soutiens_block(prompt)
        # Ask 2 — where the render names an examined-clean argument, it
        # carries that verdict: a reader cannot take an examined passage
        # for a never-examined one (the doc_E judge note).
        assert _LABEL_ARG_2 in soutiens
        assert (
            "Examen par argument : procédé cherché, aucun retenu "
            "(verdict enregistré)" in soutiens
        )
        # Ask 3 — the movement states what it holds, in the counted form
        # the first-reading note uses (bare counts, one line).
        assert (
            "1 argument : 1 au verdict enregistré "
            "« examiné, aucun procédé retenu »." in soutiens
        )
        # The unit with a finding is NOT a soutien: it lives in the attack
        # movement its fallacy family names.
        assert _LABEL_ARG_1 not in soutiens
        assert "MOUVEMENT" in prompt  # the attack movement renders too

    async def test_a_unit_without_a_recorded_verdict_gets_no_verdict_line(
        self, monkeypatch
    ):
        """The honesty edge: selected, walk unanswered ⇒ no verdict claimed.

        Also the render control for a mixed movement: no count line when no
        soutiens argument carries a recorded verdict (the count would state
        an empty set).
        """
        state = _synthetic_state()

        async def _walk(
            arg_text,
            arg_id,
            llm_service,
            taxonomy_path,
            document_statements=None,
            document_frame=None,
        ):
            if arg_id == "arg_2":
                return {
                    "error": "endpoint indisponible",
                    "fallacies": [],
                    "source_arg_id": arg_id,
                }
            return {
                "fallacies": [
                    {
                        "type": "appel_a_la_peur",
                        "taxonomy_pk": "appel_a_la_peur",
                        "explanation": "j",
                        "target_argument": arg_id,
                        "confidence": 0.9,
                    }
                ],
                "extraction_method": "guided",
                "source_arg_id": arg_id,
            }

        await _run_pass_and_write(state, monkeypatch, _walk)
        soutiens = _soutiens_block(_prompt(state))
        assert _LABEL_ARG_2 in soutiens  # sample member, no state finding
        assert "Examen par argument" not in soutiens
        assert "verdict enregistré" not in soutiens


class TestAPreFixStateRendersByteIdentically:
    """The control — a state recorded before the fix changes nothing."""

    def test_no_outcome_key_no_verdict_no_count(self):
        state = _synthetic_state()
        # The pre-#3558 record: unit_ids, no per-unit outcome.
        state.record_analysis_coverage(
            "fallacy_per_argument",
            2,
            2,
            3,
            3,
            span=(0.0, 0.6),
            largest_uncovered_stretch=0.4,
            unit_ids=["arg_1", "arg_2"],
        )
        state.add_fallacy(
            fallacy_type="Appel à la peur",
            justification="justification synthétique du témoin",
            target_arg_id="arg_1",
        )
        soutiens = _soutiens_block(_prompt(state))
        assert _LABEL_ARG_2 in soutiens
        assert "Examen par argument" not in soutiens
        assert "verdict enregistré" not in soutiens
        # The header is the #2966 one, unchanged.
        assert soutiens.startswith(
            "MOUVEMENT « soutiens » — les soutiens qui tiennent "
            "(sophismes cherchés sur chacune, aucun localisé)"
        )


class TestTheWinnerReadingPreservesAndGrowsTheOutcomes:
    """#3326 rebuilds the record — the outcomes must survive it.

    The winner-reading writer re-records the coverage entry from scratch
    (``record_analysis_coverage`` rebuilds, R1164): a key it does not carry
    forward is erased. It must also record ITS OWN examined winners'
    outcomes — the winner reading is the per-argument reading, targeted
    after the vote (#3105 vocabulary).
    """

    def test_outcomes_survive_the_rebuild_and_the_winner_gets_its_count(self):
        import argumentation_analysis.orchestration.state_writers as sw

        state = _synthetic_state()
        state.record_analysis_coverage(
            "fallacy_per_argument",
            2,
            2,
            3,
            3,
            span=(0.0, 0.6),
            largest_uncovered_stretch=0.4,
            unit_ids=["arg_1", "arg_2"],
        )
        # The pass concluded: one finding on arg_1, arg_2 clean.
        state.analysis_coverage["fallacy_per_argument"]["per_unit_outcomes"] = {
            "arg_1": 1,
            "arg_2": 0,
        }
        # A third unit the vote cited — outside the sample, walked clean
        # by the winner reading.
        state.add_argument(
            "Unité synthétique numéro trois portant un propos analysable.",
            producer="llm_extract",
            offset=600,
        )
        state.governance_decisions.append(
            {"method": "social_choice", "winner": "arg_3", "winners": []}
        )
        output = {
            "fallacies": [
                {
                    "type": "appel_a_la_peur",
                    "taxonomy_pk": "appel_a_la_peur",
                    "explanation": "j",
                    "target_argument": "arg_3",
                    "source_arg_id": "arg_3",
                    "confidence": 0.9,
                }
            ],
            "examined_ids": ["arg_3"],
            "already_examined": [],
            "cited_winners": ["arg_3"],
        }
        sw._write_fallacy_winner_reading_to_state(output, state, {})
        cov = state.analysis_coverage["fallacy_per_argument"]
        assert "arg_3" in cov["unit_ids"]
        # Preserved through the rebuild, grown with the winner's outcome.
        assert cov["per_unit_outcomes"] == {"arg_1": 1, "arg_2": 0, "arg_3": 1}
