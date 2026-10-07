"""#2970 (items 1 and 3) — no formal verdict without an understood input.

Measured on the saved 06/10 doc_A state (the issue's table): the QBF phase
received the first 200 characters of the document — its header, no
quantifier — and wrote "QBF VALID" (``pl_3.satisfiable=True``); DL received
a 0-axiom KB and wrote ``fol_1.consistent=True``; CL had 0 conditionals and
no query and wrote ``pl_2.satisfiable=True``. ``text_to_kb`` stored 87
natural-language sentences under ``logic_type="fol"`` and ``kb_to_tweety``
stored all 87 formulas including the 7 the plugin had marked
``is_valid=False`` — together they were 174 of the 182 "formal findings"
the deep synthesis counted.

Witness discipline: every writer witness runs against the REAL
``UnifiedAnalysisState``. The issue's root pattern was MagicMock states
answering ``hasattr`` True for fields the production state never declares
(the two dead branches this change removes) — a mock where a real state can
stand would rebuild the very blindness being repaired. Born red on main
(each class docstring says what main does); synthetic inputs only; opaque
ids only.
"""

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_cl,
    _invoke_dl,
    _invoke_qbf,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_cl_to_state,
    _write_dl_to_state,
    _write_kb_to_tweety_to_state,
    _write_qbf_to_state,
    _write_text_to_kb_to_state,
)


class TestQbfInvokeRefusesTheDocumentHeader:
    """Main feeds ``input_text[:200]`` to the solver and returns its verdict
    over prose; the fix returns not-evaluated without touching input_text."""

    async def test_no_formula_is_not_evaluated_never_the_header(self):
        result = await _invoke_qbf("Le texte integral du document source…", {})
        assert result["status"] == "not_evaluated"
        assert result["valid"] is None
        # The header itself never becomes the formula (privacy + the #1774
        # definition of done: no positive assertion without a computation on
        # an understood input).
        assert not result.get("formula")

    async def test_a_real_formula_still_reaches_the_solver_path(self):
        """Positive control: an explicit formula is honoured — the guard is
        on the fallback, not on the analysis."""
        result = await _invoke_qbf("irrelevant", {"formula": "forall x: P(x)"})
        assert result.get("status") != "not_evaluated"
        assert result.get("formula") == "forall x: P(x)"


class TestDlClQbfWritersRefuseVacuousVerdicts:
    """Main writes the fabricated True of the 06/10 shapes; the fix writes
    None (not evaluated) — and keeps genuine verdicts."""

    DOC_A_DL_SHAPE = {
        "consistent": True,
        "message": "Knowledge base is consistent",
        "tbox_size": 0,
        "abox_size": 0,
        "input_ontology": {"tbox": [], "abox_concepts": [], "abox_roles": []},
    }

    DOC_A_CL_SHAPE = {
        "entailed": True,
        "message": "No query specified — KB constructed.",
        "num_conditionals": 0,
        "input_conditionals": [],
    }

    def test_dl_empty_kb_writes_none_not_consistent(self):
        state = UnifiedAnalysisState("texte")
        _write_dl_to_state(dict(self.DOC_A_DL_SHAPE), state, {})
        entry = state.fol_analysis_results[-1]
        assert entry["consistent"] is None, (
            "an empty KB is vacuously consistent — that is not a verdict on "
            "the document (#2970)"
        )

    def test_dl_real_ontology_keeps_its_verdict(self):
        state = UnifiedAnalysisState("texte")
        shape = dict(self.DOC_A_DL_SHAPE)
        shape["input_ontology"] = {
            "tbox": ["Person ⊑ ∃.hasName"],
            "abox_concepts": ["Paul:Person"],
            "abox_roles": [],
        }
        _write_dl_to_state(shape, state, {})
        assert state.fol_analysis_results[-1]["consistent"] is True

    def test_cl_no_query_empty_conditionals_writes_none(self):
        state = UnifiedAnalysisState("texte")
        _write_cl_to_state(dict(self.DOC_A_CL_SHAPE), state, {})
        entry = state.propositional_analysis_results[-1]
        assert entry["satisfiable"] is None, (
            "nothing was asked of an empty conditional set — 'No query "
            "specified' is not entailment (#2970)"
        )

    def test_cl_decided_query_keeps_its_verdict(self):
        state = UnifiedAnalysisState("texte")
        shape = dict(self.DOC_A_CL_SHAPE)
        shape["input_conditionals"] = ["bird(X) <= pigeon(X)"]
        shape["num_conditionals"] = 1
        _write_cl_to_state(shape, state, {})
        assert state.propositional_analysis_results[-1]["satisfiable"] is True

    def test_qbf_not_evaluated_producer_is_named_in_the_entry(self):
        state = UnifiedAnalysisState("texte")
        _write_qbf_to_state(
            {
                "status": "not_evaluated",
                "valid": None,
                "quantifiers": [],
                "message": "no formula supplied",
            },
            state,
            {},
        )
        entry = state.propositional_analysis_results[-1]
        assert entry["satisfiable"] is None
        assert "not evaluated" in entry["formulas"][0]


class TestBeliefSetPopulationCarriesValidity:
    """Main stores prose as "fol" and unparsable formulas as valid belief
    sets; the fix stores neither without losing the real ones."""

    def test_invalid_formula_never_reaches_belief_sets(self):
        state = UnifiedAnalysisState("texte")
        _write_kb_to_tweety_to_state(
            {
                "formulas": [
                    {"formula": "P(a)", "logic_type": "fol", "is_valid": True},
                    {
                        "formula": "%%unparsable%%",
                        "logic_type": "fol",
                        "is_valid": False,
                    },
                    {"formula": "Q(b)", "logic_type": "propositional"},
                ],
                "formula_count": 3,
                "status": "ok",
            },
            state,
            {},
        )
        contents = [bs["content"] for bs in state.belief_sets.values()]
        assert "%%unparsable%%" not in contents
        assert sorted(contents) == ["P(a)", "Q(b)"]

    def test_nl_candidates_are_not_stored_as_fol(self):
        state = UnifiedAnalysisState("texte")
        _write_text_to_kb_to_state(
            {
                "arguments": [{"text": "arg1"}],
                "belief_candidates": ["une phrase en langage naturel"],
            },
            state,
            {},
        )
        (entry,) = state.belief_sets.values()
        assert (
            entry["logic_type"] != "fol"
        ), "a natural-language sentence is not a fol belief set (#2970)"


class TestFormalFindingsCountExcludesNonResults:
    """Main counts every belief_sets entry — prose, unknown and invalid
    alike (174 of the 182 findings on doc_A); the fix counts only what
    ``canonical_logic_type`` recognises and no producer marked invalid."""

    def _state_with_noise(self) -> UnifiedAnalysisState:
        state = UnifiedAnalysisState("texte")
        state.belief_sets = {
            "bs_nl": {"logic_type": "nl", "content": "prose candidate"},
            "bs_fol": {"logic_type": "fol", "content": "P(a)"},
            "bs_invalid": {
                "logic_type": "fol",
                "content": "%%x%%",
                "is_valid": False,
            },
            "bs_pl_capital": {"logic_type": "Propositional", "content": "p & q"},
        }
        return state

    def test_only_formal_valid_belief_sets_are_counted(self):
        findings = DeepSynthesisAgent._build_formal_findings(self._state_with_noise())
        # The state carries no PL/FOL/Modal container entries, so every
        # finding comes from belief_sets: "Propositional" is a real spelling
        # of a formal logic (the canonical resolver answers it) — it counts;
        # "nl" and the invalid entry do not.
        assert len(findings) == 2
        counted = {f.axioms[0] for f in findings}
        assert counted == {"P(a)", "p & q"}
