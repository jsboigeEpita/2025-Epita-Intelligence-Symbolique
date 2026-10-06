"""#2952 — wire DeLP/EAF/ADF into Acte III: one projector per site, one witness per site.

The three formalism writers (#1648 Wave-2 + #2063) were planted without a
consumer; this file pins their Acte III readers. The DoD the coordinator set:
the state is built by the REAL ``state_writers`` from a handler-shaped output
(``delp_handler.analyze_delp`` / ``eaf_handler.analyze_epistemic_framework`` /
``adf_handler.analyze_adf`` — shapes read at each handler, not invented), and
the rendered sentence is present when the data is there, absent otherwise.

Sites (issue #2952, coordinator arbitration c.6014772201 — wire, not retire):

- 1a DeLP sidecar — ``delp_arguments``/``program_size``/``criterion`` via
  ``_iter_formalism_specific``; **folded into 1b as a prose qualifier (#2963)** —
  the criterion is a constant on the production path, so on its own it would
  print the same sentence on every run (positive control: criterion alone
  without a verdict yields no finding at all);
- 1b DeLP native — ``extensions["delp_query_results"]`` (warranted/defeated);
- 2  EAF sidecar — ``epistemic_beliefs`` (per-agent divergence);
- 3  ADF native — ``extensions["adf_models"]`` (three-valued undecided), with
  the #2063 provenance flag: a degraded run yields to the absence channel.

Privacy HARD: synthetic opaque atoms only (``claim_*``, ``agent_*``, ``p``/``q``)
— the sidecar leaves are the exact surface #1702 opacifies at export, and the
program/rules text must never reach the prose (asserted below). Deterministic:
no JVM, no LLM, no network — the writers are pure dict plumbing.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, List

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_adf_to_state,
    _write_delp_to_state,
    _write_eaf_to_state,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _adf_finding,
    _delp_criterion_qualifier,
    _delp_verdicts_finding,
    _eaf_finding,
    build_act3_evidence,
    build_act3_prompt,
)

# Handler-shaped outputs (measured at each handler — see module docstring).
_DELP_OUTPUT: dict[str, Any] = {
    "program": "claim_alpha <- claim_beta\nclaim_beta <- claim_gamma",
    "program_size": 2,
    "criterion": "generalized_specificity",
    "query_results": [
        {"query": "claim_alpha", "answer": "YES", "message": "warranted"},
        {"query": "claim_beta", "answer": "NO", "message": "defeated by claim_gamma"},
        {"query": "claim_gamma", "answer": "UNDECIDED", "message": "both hold"},
    ],
    "statistics": {"queries_count": 3, "handler": "DeLPHandler"},
}
_EAF_OUTPUT: dict[str, Any] = {
    "semantics": "grounded",
    "arguments": ["claim_alpha", "claim_beta"],
    "attacks": [["claim_beta", "claim_alpha"]],
    "epistemic_beliefs": {"agent_one": ["claim_alpha"], "agent_two": []},
    "extensions": [["claim_beta"]],
    "extensions_count": 1,
    "statistics": {
        "arguments_count": 2,
        "attacks_count": 1,
        "agents_count": 2,
        "handler": "EAFHandler",
    },
}
_ADF_OUTPUT: dict[str, Any] = {
    "semantics": "grounded",
    "statements": ["p", "q"],
    "interpretations": ["{p=T,q=U}"],
    "statistics": {"statements_count": 2, "interpretations_count": 1},
}


def _writer_built_state(
    *builds: Callable[[UnifiedAnalysisState], None]
) -> SimpleNamespace:
    """Run the REAL writers on a real UnifiedAnalysisState, then graft the
    resulting ``dung_frameworks`` onto the Acte III evidence stub.

    The writers need ``add_dung_framework`` (a SimpleNamespace has none), and
    ``build_act3_evidence`` needs the stub's band fields — so the writers build
    the frameworks on the real state and the stub carries them to the evidence
    builder. Nothing is hand-crafted between the two: what the projector reads
    is exactly what the writer wrote.
    """
    real = UnifiedAnalysisState("2952 synthetic probe")
    for build in builds:
        build(real)
    state = SimpleNamespace(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks=real.dung_frameworks,
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )
    return state


def _capabilities(state: SimpleNamespace) -> List[str]:
    return [f.capability for f in build_act3_evidence(state).structured_findings]


class TestDelpCriterionQualifier:
    """#2963 — the criterion is a QUALIFIER of the verdicts, never a projector.

    On the production path nothing poses the ``criterion`` leaf — the handler
    default is what ``invoke_callables.py:5749`` reads — so a projector on it
    would print the same sentence on every DeLP run: a constant dressed as a
    finding. Folded into 1b, it appears only when a verdict does.
    """

    def _state(self, **overrides: Any) -> SimpleNamespace:
        output = {**_DELP_OUTPUT, **overrides}
        return _writer_built_state(lambda real: _write_delp_to_state(output, real, {}))

    def test_criterion_alone_yields_no_finding(self) -> None:
        """POSITIVE CONTROL (coordinator, #2963): the criterion leaf on its
        own — no YES, no NO — renders NO DeLP axis at all. Before the fold
        this state rendered one; the fold is exactly what empties it."""
        state = self._state(query_results=[])
        assert _delp_verdicts_finding(state) is None
        assert "delp_reasoning" not in _capabilities(state)

    def test_criterion_qualifies_the_verdicts(self) -> None:
        finding = _delp_verdicts_finding(self._state())
        assert finding is not None
        assert "selon un critère de spécificité" in finding.statement

    def test_qualifier_carries_the_program_size_as_amplitude(self) -> None:
        finding = _delp_verdicts_finding(self._state())
        assert finding is not None
        assert "sur un programme de 2 lignes" in finding.statement

    def test_verdicts_without_criterion_keep_the_plain_head(self) -> None:
        """1b is not gated on the criterion: absent, the sentence keeps its
        bare form — the qualifier is additive, never a precondition."""
        finding = _delp_verdicts_finding(self._state(criterion=""))
        assert finding is not None
        assert "selon" not in finding.statement
        assert finding.statement.startswith("la dialectique défaisable a tranché : ")

    def test_raw_token_never_reaches_the_statement(self) -> None:
        """The leaf's snake_case label is a code token, not French prose."""
        finding = _delp_verdicts_finding(self._state())
        assert finding is not None
        assert "generalized_specificity" not in finding.statement

    def test_unknown_criterion_falls_back_to_a_generic_qualifier(self) -> None:
        state = self._state(criterion="exotic_mode")
        assert _delp_criterion_qualifier(state) == (
            "selon son critère de comparaison déclaré, sur un programme de 2 lignes"
        )

    def test_malformed_criterion_yields_no_qualifier(self) -> None:
        """A non-str criterion is not a criterion: the verdicts stand, the
        qualifier stays out — no ``str(42)`` leak into the prose."""
        state = self._state(criterion=42)
        assert _delp_criterion_qualifier(state) == ""
        finding = _delp_verdicts_finding(state)
        assert finding is not None
        assert "42" not in finding.statement

    def test_program_text_never_reaches_the_statement(self) -> None:
        """Privacy HARD: the sidecar is the #1702-scrubbed surface."""
        finding = _delp_verdicts_finding(self._state())
        assert finding is not None
        assert "claim_alpha <- claim_beta" not in finding.statement
        assert "<-" not in finding.statement


class TestDelpVerdictsChannel:
    """Site 1b — what DeLP DECIDED, query by query."""

    def _state(self, **overrides: Any) -> SimpleNamespace:
        output = {**_DELP_OUTPUT, **overrides}
        return _writer_built_state(lambda real: _write_delp_to_state(output, real, {}))

    def test_verdicts_become_a_finding(self) -> None:
        finding = _delp_verdicts_finding(self._state())
        assert finding is not None
        assert "claim_alpha" in finding.statement  # warranted, named
        assert "claim_beta" in finding.statement  # defeated, named
        assert "claim_gamma" in finding.statement  # undecided, counted by name

    def test_verdict_queries_alone_trigger_delp(self) -> None:
        """Isolation: 1b fires without the 1a criterion leaf."""
        state = self._state(criterion="")
        assert _delp_verdicts_finding(state) is not None
        assert "delp_reasoning" in _capabilities(state)

    def test_nothing_decided_yields_no_finding(self) -> None:
        state = self._state(
            query_results=[
                {"query": "claim_alpha", "answer": "UNDECIDED", "message": ""}
            ]
        )
        assert _delp_verdicts_finding(state) is None

    def test_empty_queries_yield_no_finding(self) -> None:
        state = self._state(query_results=[])
        assert _delp_verdicts_finding(state) is None

    def test_unknown_is_a_functional_error_never_projected(self) -> None:
        state = self._state(
            query_results=[{"query": "claim_alpha", "answer": "UNKNOWN"}]
        )
        assert _delp_verdicts_finding(state) is None

    def test_handler_messages_never_reach_the_statement(self) -> None:
        finding = _delp_verdicts_finding(self._state())
        assert finding is not None
        assert "defeated by claim_gamma" not in finding.statement


class TestEafChannel:
    """Site 2 — the per-agent belief DIVERGENCE (what no attack-only axis sees)."""

    def _state(self, beliefs: Any) -> SimpleNamespace:
        output = {**_EAF_OUTPUT, "epistemic_beliefs": beliefs}
        return _writer_built_state(lambda real: _write_eaf_to_state(output, real, {}))

    def test_divergent_beliefs_become_a_finding(self) -> None:
        state = self._state({"agent_one": ["claim_alpha"], "agent_two": []})
        finding = _eaf_finding(state)
        assert finding is not None
        assert finding.capability == "eaf_reasoning"
        assert "agent_one" in finding.statement
        assert "agent_two" in finding.statement
        assert "claim_alpha" in finding.statement

    def test_finding_reaches_the_evidence(self) -> None:
        assert "eaf_reasoning" in _capabilities(
            self._state({"agent_one": ["claim_alpha"], "agent_two": []})
        )

    def test_agreeing_agents_yield_nothing(self) -> None:
        """Full agreement carries nothing EAF-specific (honest absence)."""
        state = self._state(
            {"agent_one": ["claim_alpha"], "agent_two": ["claim_alpha"]}
        )
        assert _eaf_finding(state) is None

    def test_single_agent_yields_nothing(self) -> None:
        state = self._state({"agent_one": ["claim_alpha"]})
        assert _eaf_finding(state) is None

    def test_malformed_beliefs_yield_nothing(self) -> None:
        state = self._state("not-a-dict")
        assert _eaf_finding(state) is None


class TestAdfChannel:
    """Site 3 — the three-valued UNDECIDED, with the #2063 provenance flag."""

    def _state(self, **overrides: Any) -> SimpleNamespace:
        output = {**_ADF_OUTPUT, **overrides}
        return _writer_built_state(lambda real: _write_adf_to_state(output, real, {}))

    def test_undecided_statement_becomes_a_finding(self) -> None:
        finding = _adf_finding(self._state())
        assert finding is not None
        assert finding.capability == "adf_reasoning"
        assert "« q »" in finding.statement  # the U-valued statement, named
        assert "indécis" in finding.statement
        assert "p" in finding.statement or "« q »" in finding.statement

    def test_finding_reaches_the_evidence(self) -> None:
        assert "adf_reasoning" in _capabilities(self._state())

    def test_degraded_run_yields_to_the_absence_channel(self) -> None:
        """#2063 provenance combination (#2844 discipline): a degraded ADF run
        is named by the ABSENCE channel and nowhere else — even when its
        interpretations are populated, this projector stays silent, so the two
        readers of one state agree by construction."""
        state = self._state(degraded=True)
        assert _adf_finding(state) is None

    def test_two_valued_single_world_yields_nothing(self) -> None:
        state = self._state(interpretations=["{p=T,q=F}"])
        assert _adf_finding(state) is None

    def test_unparsed_format_falls_back_to_non_unicity(self) -> None:
        """A format change must degrade to the non-unicity figure, never
        fabricate assignments."""
        finding = _adf_finding(
            self._state(interpretations=["monde-alpha", "monde-beta"])
        )
        assert finding is not None
        assert "2 interprétations" in finding.statement

    def test_single_unparsed_model_yields_nothing(self) -> None:
        state = self._state(interpretations=["monde-alpha"])
        assert _adf_finding(state) is None

    def test_empty_models_yield_nothing(self) -> None:
        state = self._state(interpretations=[])
        assert _adf_finding(state) is None


class TestAllFourSitesTogether:
    """The four sites render on ONE state — the wire the dispatch asked for."""

    def test_four_sites_render_on_one_state(self) -> None:
        state = _writer_built_state(
            lambda real: _write_delp_to_state(_DELP_OUTPUT, real, {}),
            lambda real: _write_eaf_to_state(_EAF_OUTPUT, real, {}),
            lambda real: _write_adf_to_state(_ADF_OUTPUT, real, {}),
        )
        caps = set(_capabilities(state))
        assert {"delp_reasoning", "eaf_reasoning", "adf_reasoning"} <= caps

    def test_no_formalism_data_renders_no_new_axis(self) -> None:
        state = _writer_built_state(
            lambda real: _write_delp_to_state({}, real, {}),
            lambda real: _write_eaf_to_state({}, real, {}),
            lambda real: _write_adf_to_state({}, real, {}),
        )
        caps = set(_capabilities(state))
        assert not caps & {"delp_reasoning", "eaf_reasoning", "adf_reasoning"}

    def test_each_site_phrase_reaches_the_prompt(self) -> None:
        """End of the channel: each site's singular sentence reaches the
        Acte III prompt (same channel as the #1667 axes — one witness for
        the four, each named by its own marker)."""
        state = _writer_built_state(
            lambda real: _write_delp_to_state(_DELP_OUTPUT, real, {}),
            lambda real: _write_eaf_to_state(_EAF_OUTPUT, real, {}),
            lambda real: _write_adf_to_state(_ADF_OUTPUT, real, {}),
        )
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert "selon un critère de spécificité" in prompt  # 1a — folded in
        assert "generalized_specificity" not in prompt  # ... never the raw token
        assert "garantie" in prompt  # 1b — the warranted verdict
        assert "pour acquis" in prompt  # 2 — the belief divergence
        assert "indécis" in prompt  # 3 — the three-valued undecided
