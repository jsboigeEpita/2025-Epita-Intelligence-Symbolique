"""The formal axes must not be a function of the fallacy axis (#1631, #1637).

Two distinct couplings existed between the upstream hierarchical fallacy phase
and the formal-logic phases, and neither was visible from a test:

* **#1637 — the propositional belief set.** On the template-fallback path (one
  readable atom per argument, reached only when NL->PL translation produced
  nothing), the presence of *any* upstream fallacy appended ``!{last_atom}`` to
  the belief set. The SAT solver then returned UNSAT, so ``satisfiable`` became
  a function of the fallacy axis rather than of the propositional structure —
  and the contradiction landed on the last argument, unrelated to whatever the
  fallacy actually targeted.

* **#1631 — the FOL ``inferences`` field.** It was filled, before any formula
  reached Tweety, with one ``"Argument undermined by <type> fallacy"`` line per
  detected fallacy, and returned on every exit path including those where the
  prover decided nothing.

Why the existing suite could not see either one: ``test_nl_to_logic_wiring.py``
already exercises the PL template-fallback path and already asserts
``len(formulas) == len(args)`` and ``all(_is_pl_atom(f))`` — both of which the
injection would break. They pass because its helper never puts
``phase_hierarchical_fallacy_output`` in the context. The path was covered; the
defect was dormant in the single configuration every fixture instantiated.

That is why :func:`_context` below takes ``fallacies`` as a **required keyword**
argument (#1637 DoD item 3): a future fixture cannot re-create the blind spot by
forgetting it.
"""

import re
from unittest.mock import MagicMock, patch

import pytest

TWEETY_BRIDGE_PATH = (
    "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
)

_ARGS = ["Arg one", "Arg two", "Arg three"]

_FALLACIES = [
    {"type": "ad_hominem", "target_argument": "arg_1"},
    {"type": "straw_man", "target_argument": "arg_2"},
]


def _context(args, *, fallacies, translations=None):
    """Build a phase context.

    ``fallacies`` is intentionally required and keyword-only: the couplings this
    module pins were invisible precisely because every other fixture omitted the
    fallacy phase output. Pass ``[]`` for the control run and a non-empty list
    for the treatment run — never omit the decision.
    """
    ctx = {"phase_extract_output": {"arguments": [{"text": t} for t in args]}}
    ctx["phase_hierarchical_fallacy_output"] = {"fallacies": list(fallacies)}
    if translations is not None:
        ctx["phase_nl_to_logic_output"] = {"translations": translations}
    return ctx


class TestPropositionalBeliefSetIgnoresFallacies:
    """#1637 — the PL belief set is built from the source arguments only."""

    async def test_template_fallback_is_identical_with_and_without_fallacies(self):
        """Same arguments + same solver, fallacies as the only variable.

        Before the fix this produced ``satisfiable=True`` / 3 formulas without
        fallacies and ``satisfiable=False`` / 4 formulas with them. Comparing
        both runs (rather than asserting one expected shape) is what makes the
        test die if the injection is reintroduced anywhere on this path.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        without = await _invoke_propositional_logic(
            "text", _context(_ARGS, fallacies=[])
        )
        with_ = await _invoke_propositional_logic(
            "text", _context(_ARGS, fallacies=_FALLACIES)
        )

        assert with_["formulas"] == without["formulas"], (
            "the belief set changed when only the upstream fallacy axis changed "
            f"(#1637): {without['formulas']} -> {with_['formulas']}"
        )
        assert with_["satisfiable"] == without["satisfiable"], (
            "the SAT verdict changed when only the upstream fallacy axis "
            f"changed (#1637): {without['satisfiable']} -> {with_['satisfiable']}"
        )

    async def test_no_negation_is_planted_in_the_belief_set(self):
        """The fabricated formula was a negated atom; none may appear.

        Complements the equality test above: that one dies if the two runs
        diverge, this one dies if a negation is planted unconditionally (which
        equality alone would not catch).
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        result = await _invoke_propositional_logic(
            "text", _context(_ARGS, fallacies=_FALLACIES)
        )

        negated = [
            f
            for f in result["formulas"]
            if isinstance(f, str) and f.lstrip().startswith("!")
        ]
        assert not negated, f"negation planted in the PL belief set (#1637): {negated}"

    async def test_one_atom_per_argument_even_when_fallacies_were_detected(self):
        """``test_pl_falls_back_to_templates`` asserts this without fallacies.

        The injection was guarded by ``if fallacies and len(prop_vars) >= 2``,
        so the existing assertion held in the only configuration it was ever run
        in. Re-asserting it *with* fallacies present is the missing half.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        result = await _invoke_propositional_logic(
            "text", _context(_ARGS, fallacies=_FALLACIES)
        )

        assert len(result["formulas"]) == len(_ARGS), result["formulas"]
        assert all(
            re.match(r"^[a-z][a-z0-9_]*$", f) for f in result["formulas"]
        ), result["formulas"]


class TestFolInferencesCarryOnlyFormalOutput:
    """#1631 — ``inferences`` holds what the prover produced, or nothing."""

    async def test_no_translation_path_is_identical_with_and_without_fallacies(self):
        """The ``unavailable:no-translation`` early return.

        This is the exit path where the coupling was most damaging: the axis has
        formalized nothing, yet used to return one line per upstream fallacy
        under a heading announcing a Tweety verification.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        without = await _invoke_fol_reasoning("text", _context(_ARGS, fallacies=[]))
        with_ = await _invoke_fol_reasoning(
            "text", _context(_ARGS, fallacies=_FALLACIES)
        )

        assert without["fol_status"] == "unavailable:no-translation"
        assert with_ == without, (
            "FOL output changed when only the upstream fallacy axis changed "
            f"(#1631): {without} -> {with_}"
        )
        assert with_["inferences"] == []

    async def test_decided_path_carries_no_fallacy_derived_inferences(self):
        """The nominal path, where the prover actually returns a verdict.

        The removed block ran before any formula reached Tweety, so it polluted
        the decided path too — an artefact could carry a real verdict alongside
        claims the prover never produced.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        translations = [
            {
                "logic_type": "first_order",
                "formula": "forall X: (Human(X) => Mortal(X))",
                "is_valid": True,
                "original_text": "Arg one",
            },
            {
                "logic_type": "first_order",
                "formula": "Human(socrates)",
                "is_valid": True,
                "original_text": "Arg two",
            },
        ]

        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (True, "Consistent")

        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            without = await _invoke_fol_reasoning(
                "text", _context(_ARGS, fallacies=[], translations=translations)
            )
            with_ = await _invoke_fol_reasoning(
                "text",
                _context(_ARGS, fallacies=_FALLACIES, translations=translations),
            )

        assert with_["inferences"] == [], (
            "fallacy-derived content reappeared in FOL inferences on the decided "
            f"path (#1631): {with_['inferences']}"
        )
        assert with_["inferences"] == without["inferences"]
        assert with_["formulas"] == without["formulas"]


@pytest.mark.parametrize(
    "axis",
    ["_invoke_propositional_logic", "_invoke_fol_reasoning", "_invoke_modal_logic"],
)
def test_formal_axes_do_not_read_the_fallacy_phase(axis):
    """Structural guard: no formal axis reads ``phase_hierarchical_fallacy_output``.

    The behavioural tests above pin the two couplings that existed. This one
    pins the *rule*, so a third coupling — in modal, or on an exit path the
    behavioural tests do not reach — fails here rather than shipping silently.
    Modal is included although it was already clean: the point is to keep it so.
    """
    import inspect

    from argumentation_analysis.orchestration import invoke_callables

    source = inspect.getsource(getattr(invoke_callables, axis))
    offending = [
        line.strip()
        for line in source.splitlines()
        if "phase_hierarchical_fallacy_output" in line
        and not line.lstrip().startswith("#")
    ]
    assert not offending, (
        f"{axis} reads the fallacy phase output (#1631/#1637); the formal axes "
        f"must depend on the source arguments only: {offending}"
    )
