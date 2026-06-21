"""FP-11 #1213 — modal KB construction round-trip (REAL, no mock).

``ModalLogicAgent._construct_modal_kb_from_json`` used to emit ``constant <name>``
declarations — a propositional-modal grammar this ``MlParser`` build does NOT
implement. Every modal KB failed to parse
(``ParserException: Missing '=' in sort declaration 'constant X'``), so
consistency was never actually decided: the old handler swallowed the
``JException`` and returned ``False`` ("inconsistent") — modal theater, the same
regression class as #1019/#1196/#1202. #1212 later surfaced the parse failure as
an honest ``None`` (degraded), but the verdict was still never *decided*.

This test proves the fix end-to-end: a synthetic JSON belief set flows through
the GENUINE constructor and DECIDES consistency via ``SimpleMlReasoner``
(pure-Java, query-based — the default ``TWEETY`` reasoner). No external binary
(no SPASS) → it RUNS on CI everywhere, not "green by skipping".

Production path under test:
    ModalLogicAgent._construct_modal_kb_from_json(json)
    -> TweetyBridge.check_consistency(kb, "K")
    -> ModalHandler.is_modal_kb_consistent
    -> SimpleMlReasoner.query  (TWEETY, pure-Java)

Why the builder uses ``__new__`` + a real logger (not an LLM-backed instance):
``_construct_modal_kb_from_json`` is pure string-building — its only ``self``
dependency is ``self.logger`` (debug). ``BaseLogicAgent.__init__`` requires an
LLM service in the kernel, but that service is NEVER consulted by the
constructor. Bypassing ``__init__`` runs the GENUINE construction code (no
method is mocked) while keeping the test free of any API-key dependency, so it
decides — and is not skipped — in CI without keys.

Privacy HARD: synthetic propositions only (``rain``/``wet``). 0 corpus content.
"""

import logging

import pytest

from argumentation_analysis.core.config import settings, ModalSolverChoice
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

# The DoD's canonical synthetic belief set: necessity implies wetness from rain.
CONSISTENT_KB_JSON = {
    "propositions": ["rain", "wet"],
    "modal_formulas": ["[](rain => wet)", "rain"],
}
# A proposition and its negation — must be decided inconsistent.
INCONSISTENT_KB_JSON = {
    "propositions": ["rain"],
    "modal_formulas": ["rain", "!rain"],
}


@pytest.fixture(scope="module")
def modal_bridge():
    """Start the JVM (idempotent) once and build a ``TweetyBridge``. The
    builder (below) only needs ``self.logger``; the bridge is the real
    consistency decision path."""
    initialize_jvm()
    return TweetyBridge()


@pytest.fixture(scope="module")
def modal_kb_builder():
    """A ``ModalLogicAgent`` stub that runs the genuine ``_construct_modal_kb_from_json``
    code. See module docstring for why ``__new__`` (not ``__init__``)."""
    builder = ModalLogicAgent.__new__(ModalLogicAgent)
    builder._agent_logger = logging.getLogger("FP11ModalKBBuilder")
    return builder


@pytest.fixture
def tweety_solver():
    """Force the pure-Java default (``TWEETY``/``SimpleMlReasoner``) — the
    always-available, always-deciding modal path (no external binary)."""
    previous = settings.modal_solver
    settings.modal_solver = ModalSolverChoice.TWEETY
    try:
        yield
    finally:
        settings.modal_solver = previous


class TestConstructModalKbRoundTripDecides:
    """The constructor's output must parse AND decide via SimpleMlReasoner — the
    FP-11 anti-theater guard: the verdict comes from a real reasoner, not a
    parse failure silently reported as 'inconsistent'."""

    def test_consistent_kb_decides_true(
        self, modal_kb_builder, modal_bridge, tweety_solver
    ):
        """A consistent modal KB (``[](rain => wet)`` ∧ ``rain``) built from the
        DoD JSON must yield ``is_consistent = True`` via a REAL query-based
        decision, and the constructed string must declare propositions with
        ``type(prop)`` (the FOL-modal grammar MlParser accepts), NOT ``constant``.
        """
        kb = modal_kb_builder._construct_modal_kb_from_json(CONSISTENT_KB_JSON)
        # The fix: declarations are type(prop), not the unparseable constant prop.
        assert "type(rain)" in kb, f"Expected type(rain) declaration; got:\n{kb}"
        assert "type(wet)" in kb, f"Expected type(wet) declaration; got:\n{kb}"
        assert (
            "constant" not in kb
        ), f"#1213: the unparseable 'constant X' grammar must be gone; got:\n{kb}"
        is_consistent, msg = modal_bridge.check_consistency(kb, "K")
        assert (
            is_consistent is True
        ), f"Consistent modal KB must report consistent; got ({is_consistent!r}, {msg!r})."
        assert "tweety" in msg.lower(), (
            f"Verdict must be traceable to the active reasoner (not a parse "
            f"error); got msg={msg!r}."
        )

    def test_inconsistent_kb_decides_false(
        self, modal_kb_builder, modal_bridge, tweety_solver
    ):
        """An inconsistent modal KB (``rain`` and ``!rain``) built from JSON must
        yield ``is_consistent = False`` via a REAL query-based decision — not the
        historical false 'inconsistent' that masked a parse failure (#1019)."""
        kb = modal_kb_builder._construct_modal_kb_from_json(INCONSISTENT_KB_JSON)
        assert "type(rain)" in kb, f"Expected type(rain) declaration; got:\n{kb}"
        assert (
            "constant" not in kb
        ), f"#1213: the unparseable 'constant X' grammar must be gone; got:\n{kb}"
        is_consistent, msg = modal_bridge.check_consistency(kb, "K")
        assert (
            is_consistent is False
        ), f"Inconsistent modal KB must report inconsistent; got ({is_consistent!r}, {msg!r})."
        assert "tweety" in msg.lower(), (
            f"Verdict must be traceable to the active reasoner (not a parse "
            f"error); got msg={msg!r}."
        )

    def test_constructor_extracts_props_used_in_formulas(self, modal_kb_builder):
        """Propositions used in formulas but absent from the explicit list must
        still be declared — the constructor extracts identifiers from formulas so
        the KB is self-contained and parseable."""
        kb = modal_kb_builder._construct_modal_kb_from_json(
            {"propositions": [], "modal_formulas": ["<>(socrate => wise)", "socrate"]}
        )
        # 'socrate' and 'wise' appear only in formulas — both must be declared.
        assert (
            "type(socrate)" in kb
        ), f"Formula-only prop 'socrate' must be declared:\n{kb}"
        assert "type(wise)" in kb, f"Formula-only prop 'wise' must be declared:\n{kb}"


class TestValidatorStaysCoherent:
    """``_validate_modal_kb_json`` (declared-vs-used check) must stay coherent
    with the new declaration form — it validates the JSON contract, independent
    of how declarations are later emitted."""

    def test_validator_accepts_well_formed_json(self, modal_kb_builder):
        ok, msg = modal_kb_builder._validate_modal_kb_json(CONSISTENT_KB_JSON)
        assert ok is True, f"Well-formed JSON must validate; got: {msg}"

    def test_validator_rejects_undeclared_prop(self, modal_kb_builder):
        bad = {
            "propositions": ["rain"],
            "modal_formulas": ["[](rain => wet)"],  # 'wet' not declared
        }
        ok, msg = modal_kb_builder._validate_modal_kb_json(bad)
        assert (
            ok is False
        ), "An undeclared proposition used in a formula must fail validation."
        assert "wet" in msg
