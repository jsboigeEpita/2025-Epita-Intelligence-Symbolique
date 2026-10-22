"""#3135 — a belief that was not translated is not a formal belief set.

Measured on the saved R1105b state (doc_A, the issue's table): kb_to_tweety's
FOL path named a predicate after each sentence's first word (``<word>(X)``);
Tweety parsed the result (#1777 made ``is_valid`` mean parseability); the
writer stored every parseable one under ``logic_type="fol"``; and
``_build_formal_findings`` counted them — 76 of the deep synthesis's 82
formal findings were these stubs. The coordinator measured the same 76 under
two models: the stub producer is model-free, so the defect is the pipeline's.

The fix removes the first-token template: a belief with no translator is
recorded "not translated" in the #1634 tri-state (``is_valid=None``, no
formula), never stored as a fol belief set, never counted. Witness discipline
follows #2970: the chain runs against the REAL ``UnifiedAnalysisState``,
synthetic inputs only, opaque ids only.

Born red on main: the two ``not_translated``/``formula_count`` asserts fail
everywhere (main fabricates a stub formula per belief); the belief_sets and
findings asserts fail wherever the JVM parses the stub (CI, any seat with the
portable JDK) — each class docstring says what main does.
"""

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_kb_to_tweety,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_kb_to_tweety_to_state,
)

_SYNTHETIC_BELIEFS = [
    "Une phrase de croyance synthetique",
    "Le canal formel ne doit rien fabriquer",
    "Cinq croyances suffisent au temoin",
    "Aucun traducteur n est cable ici",
    "Le stub du premier mot est parti",
]


def _ctx_with_beliefs() -> dict:
    return {
        "phase_text_to_kb_output": {
            "arguments": [],
            "belief_candidates": list(_SYNTHETIC_BELIEFS),
            "fol_signature": {
                "predicates": ["Synthetique"],
                "constants": ["c1"],
            },
        }
    }


class TestStubChannelProducesNoFormalBeliefSets:
    """Main turns each belief into ``<premier mot>(X)``, Tweety parses it and
    the writer stores it as ``fol`` — 76 of 82 findings on the saved run; the
    fix records the beliefs not translated and stores none of them."""

    async def test_five_beliefs_never_become_fol_belief_sets_or_findings(self):
        result = await _invoke_kb_to_tweety("prose ignoree", _ctx_with_beliefs())
        # The phase records what it did NOT do — anti-#1019: a silent 0
        # with no reason is theater, and a fabricated formula is worse.
        assert result.get("not_translated_count") == 5
        assert result["formula_count"] == 0

        state = UnifiedAnalysisState("texte")
        _write_kb_to_tweety_to_state(result, state, {})
        fol_entries = [
            bs for bs in state.belief_sets.values() if bs.get("logic_type") == "fol"
        ]
        assert fol_entries == [], (
            "a belief that was not translated is not a formal belief set " "(#3135)"
        )

        findings = DeepSynthesisAgent._build_formal_findings(state)
        assert findings == [], (
            "the formal-finding count must not include untranscribed "
            "beliefs — on the saved run 76 of 82 findings were first-token "
            "stubs (#3135)"
        )


class TestTranslatedBeliefStillCounts:
    """Positive control: a belief a translator actually produced a quantified
    two-predicate formula for is still stored and still counted — the repair
    removes the fabrication, not the formal channel."""

    def test_quantified_translation_is_still_a_formal_finding(self):
        state = UnifiedAnalysisState("texte")
        _write_kb_to_tweety_to_state(
            {
                "formulas": [
                    {
                        "formula": "forall X (homme(X) => mortel(X))",
                        "logic_type": "fol",
                        "is_valid": True,
                        "signature": {
                            "predicates": ["homme", "mortel"],
                            "constants": [],
                        },
                    }
                ],
                "formula_count": 1,
                "status": "ok",
            },
            state,
            {},
        )
        findings = DeepSynthesisAgent._build_formal_findings(state)
        assert len(findings) == 1
        assert findings[0].logic_type == "fol"
        assert "forall" in findings[0].axioms[0]
        assert findings[0].axioms[0].count("(") >= 2  # two predicates, not <word>(X)
