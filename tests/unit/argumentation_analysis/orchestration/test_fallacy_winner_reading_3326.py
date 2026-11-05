"""#3326 — the vote winner receives the per-argument fallacy reading.

The quality vote (k=8) and the per-argument fallacy pass (k=10) draw two
stratified selections that share a constant 3 units; the winner came from the
quality population and fell outside the fallacy sample on every measured pass.
Act III then leaned on the one unit whose soundness the run never checked.

The repair (option (a), chosen on the step-1 measurement — issuecomment
6556265967): a post-vote phase walks the cited winners (leader + divergents)
that fall outside ``analysis_coverage["fallacy_per_argument"]["unit_ids"]``,
merges its findings through the existing fallacy surfaces, and grows the
coverage record — k incremented, unit_ids extended, the reason stated in a
closed vocabulary. A winner already in the sample is never read twice; a walk
that fails never lands in the record (anti-theater #1019); the « NON
examinée » label of #3308 stays true for every unit still unexamined.

Born red on ``e86115e49``: neither the capability nor the walker exists.
"""

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState

SOURCE_TEXT = (
    "Une première unité assez longue pour être analysée par la passe. "
    "Une deuxième unité assez longue pour être analysée par la passe. "
    "Une troisième unité assez longue pour être analysée par la passe. "
    "Une quatrième unité assez longue pour être analysée par la passe. "
    "Une cinquième unité assez longue pour être analysée par la passe. "
    "Une sixième unité assez longue pour être analysée par la passe. "
    "Une septième unité assez longue pour être analysée par la passe. "
    "Une huitième unité assez longue pour être analysée par la passe. "
    "Une neuvième unité assez longue pour être analysée par la passe. "
    "Une dixième unité assez longue pour être analysée par la passe. "
    "Une onzième unité assez longue pour être analysée par la passe. "
    "Une douzième unité assez longue pour être analysée par la passe."
)


def _synthetic_state() -> tuple[UnifiedAnalysisState, list[str]]:
    """12 offset-carrying units, arg ids in insertion order (arg_1..arg_12)."""
    state = UnifiedAnalysisState(SOURCE_TEXT)
    for i in range(12):
        state.add_argument(
            f"Unité synthétique numéro {i + 1} portant un propos analysable.",
            producer="llm_extract",
            offset=300 + i * 700,
        )
    ids = sorted(state.identified_arguments, key=lambda a: int(a.split("_")[1]))
    # The per-argument pass already examined 10 of the 12 — neither winner
    # (arg_11, arg_12) among them, exactly the measured doc_A geometry.
    state.record_analysis_coverage(
        "fallacy_per_argument",
        10,
        12,
        3,
        3,
        span=(0.05, 0.9),
        largest_uncovered_stretch=0.18,
        unit_ids=[a for a in ids if a not in ("arg_11", "arg_12")],
    )
    return state, ids


def _vote(state: UnifiedAnalysisState, winner: str, winners: list[str]) -> None:
    state.governance_decisions.append(
        {
            "method": "social_choice",
            "winner": winner,
            "winners": winners,
            "scores": {winner: 5.0},
            "winner_provenance": "vote_aggregate",
        }
    )


def _stub_walk(fallacy_type: str = "appel_a_la_peur"):
    """A walker double: records calls, returns one canned finding per unit.

    #3416 — the double tracks the walk's real signature, which now carries
    ``document_statements``: the winner reading must hand the SAME document
    words the per-argument sample gets. The synthetic state records no first
    reading, so every call carries an empty list — asserted by the caller.
    """
    import argumentation_analysis.orchestration.invoke_callables as ic
    import argumentation_analysis.orchestration.state_writers as sw

    calls: list[str] = []
    statements: list = []

    async def _walk(
        arg_text,
        arg_id,
        llm_service,
        taxonomy_path,
        document_statements=None,
        document_frame=None,
    ):
        calls.append(arg_id)
        statements.append(document_statements)
        return {
            "fallacies": [
                {
                    "type": fallacy_type,
                    "explanation": "justification synthétique du témoin",
                    "target_argument": arg_id,
                    "confidence": 0.9,
                }
            ],
            "extraction_method": "guided",
            "source_arg_id": arg_id,
        }

    return calls, _walk, ic, sw, statements


class TestTheWinnerIsReadAfterTheVote:
    async def test_a_winner_outside_the_sample_is_walked_and_recorded(
        self, monkeypatch
    ):
        state, ids = _synthetic_state()
        _vote(state, "arg_11", ["arg_11", "arg_12"])
        calls, walk, ic, sw, statements = _stub_walk()
        monkeypatch.setattr(ic, "_walk_single_fallacy_unit", walk)

        output = await ic._invoke_fallacy_winner_reading(
            SOURCE_TEXT, {"_state_object": state}
        )
        assert output["examined_ids"] == ["arg_11", "arg_12"]
        assert calls == ["arg_11", "arg_12"]
        # #3416 — the winner reading hands each walk the document's own
        # words; this state records no first reading, so every call carries
        # an EMPTY list (never None, never a guess).
        assert statements == [[], []]

        sw._write_fallacy_winner_reading_to_state(output, state, {})
        cov = state.analysis_coverage["fallacy_per_argument"]
        assert cov["k"] == 12
        assert "arg_11" in cov["unit_ids"] and "arg_12" in cov["unit_ids"]
        assert cov["added_by"] == {
            "arg_11": "vote_winner_reading",
            "arg_12": "vote_winner_reading",
        }
        # The walked finding reached the fallacy surfaces Act III reads.
        assert len(state.identified_fallacies) == 2
        entry = next(iter(state.identified_fallacies.values()))
        assert entry["detection_paths"] == ["fallacy_per_argument"]

    async def test_control_a_winner_already_in_the_sample_is_not_read_twice(
        self, monkeypatch
    ):
        state, ids = _synthetic_state()
        _vote(state, "arg_3", ["arg_3", "arg_11"])  # arg_3 is already examined
        calls, walk, ic, sw, statements = _stub_walk()
        monkeypatch.setattr(ic, "_walk_single_fallacy_unit", walk)

        output = await ic._invoke_fallacy_winner_reading(
            SOURCE_TEXT, {"_state_object": state}
        )
        assert output["examined_ids"] == ["arg_11"]
        assert calls == ["arg_11"]  # arg_3 was NOT walked again
        assert output["already_examined"] == ["arg_3"]

        sw._write_fallacy_winner_reading_to_state(output, state, {})
        cov = state.analysis_coverage["fallacy_per_argument"]
        assert cov["k"] == 11  # 10 + arg_11 only
        assert "arg_3" not in cov["added_by"]

    async def test_a_failed_walk_does_not_extend_the_record(self, monkeypatch):
        state, ids = _synthetic_state()
        _vote(state, "arg_11", [])
        import argumentation_analysis.orchestration.invoke_callables as ic
        import argumentation_analysis.orchestration.state_writers as sw

        async def _boom(
            arg_text,
            arg_id,
            llm_service,
            taxonomy_path,
            document_statements=None,
            document_frame=None,
        ):
            raise RuntimeError("endpoint indisponible")

        monkeypatch.setattr(ic, "_walk_single_fallacy_unit", _boom)
        output = await ic._invoke_fallacy_winner_reading(
            SOURCE_TEXT, {"_state_object": state}
        )
        assert output["examined_ids"] == []
        assert output["degraded"] is True

        sw._write_fallacy_winner_reading_to_state(output, state, {})
        cov = state.analysis_coverage["fallacy_per_argument"]
        assert cov["k"] == 10  # unchanged — a failed walk is not coverage
        assert "added_by" not in cov

    async def test_no_vote_no_reading(self, monkeypatch):
        state, ids = _synthetic_state()
        calls, walk, ic, sw, statements = _stub_walk()
        monkeypatch.setattr(ic, "_walk_single_fallacy_unit", walk)

        output = await ic._invoke_fallacy_winner_reading(
            SOURCE_TEXT, {"_state_object": state}
        )
        assert output["examined_ids"] == []
        assert calls == []
        sw._write_fallacy_winner_reading_to_state(output, state, {})
        assert state.analysis_coverage["fallacy_per_argument"]["k"] == 10
        assert not state.identified_fallacies

    def test_the_reason_is_a_closed_vocabulary_literal(self, monkeypatch):
        """#3249 discipline: the record carries a code literal, never prose."""
        state, ids = _synthetic_state()
        _vote(state, "arg_11", [])
        output = {
            "fallacies": [],
            "examined_ids": ["arg_11"],
            "already_examined": [],
            "cited_winners": ["arg_11"],
        }
        import argumentation_analysis.orchestration.invoke_callables as ic
        import argumentation_analysis.orchestration.state_writers as sw

        sw._write_fallacy_winner_reading_to_state(output, state, {})
        added = state.analysis_coverage["fallacy_per_argument"]["added_by"]
        assert set(added.values()) == {"vote_winner_reading"}
        assert len("vote_winner_reading") < 40  # a literal, not a sentence


class TestThePhaseIsWiredAfterTheVote:
    def test_the_three_workflows_wire_the_reading_after_governance(self):
        from argumentation_analysis.orchestration.workflows import (
            build_standard_workflow,
            build_full_workflow,
            build_spectacular_workflow,
        )

        for build in (
            build_standard_workflow,
            build_full_workflow,
            build_spectacular_workflow,
        ):
            wf = build()
            phase = next(
                (p for p in wf.phases if p.capability == "fallacy_winner_reading"),
                None,
            )
            assert phase is not None, f"{wf.name}: the phase is missing"
            assert phase.depends_on == ["governance"]
            assert phase.optional is True

            levels = wf.get_execution_order()
            flat = [name for lvl in levels for name in lvl]
            gov = next(i for i, lvl in enumerate(levels) if "governance" in lvl)
            mine = next(i for i, lvl in enumerate(levels) if phase.name in lvl)
            assert mine > gov, f"{wf.name}: must run after the vote"
            # The report still reads it: narrative synthesis runs later.
            narrative = next(
                (i for i, lvl in enumerate(levels) if "narrative_synthesis" in lvl),
                None,
            )
            if narrative is not None:
                assert narrative > mine

    def test_the_capability_resolves_to_a_provider_and_a_writer(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
        )

        registry = setup_registry()
        providers = registry.find_for_capability("fallacy_winner_reading")
        assert providers, "fallacy_winner_reading has no provider"
        assert "fallacy_winner_reading" in CAPABILITY_STATE_WRITERS
