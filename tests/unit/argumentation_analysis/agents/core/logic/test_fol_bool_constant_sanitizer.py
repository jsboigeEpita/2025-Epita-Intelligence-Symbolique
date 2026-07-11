"""#1441 Bug B — FOL ``T``/``F`` boolean-constant sanitization tests.

Firsthand-reproduced (probe, JVM up) against the Tweety FOL BNF
(``tweety_fol_bnf.md``, confirmed vs ``FolParser.java``): Top/Bottom are
``+``/``-``, NOT ``T``/``F``. An LLM-emitted formula like
``forall X: (P(X) => T)`` raises ``ParserException: Unrecognized formula type
'T'`` and the formula is lost (ATT-3 firsthand finding, corpus C). The
sanitizer maps bare uppercase ``T``/``F`` tokens (word-boundary) to ``+``/``-``
so the formula parses.

The transform is unit-tested without a JVM (the core fix guard). The
end-to-end real-parse recovery is covered by the ``tweety``-marked test below
via the production path ``create_belief_set_programmatically`` (which calls
``parse_fol_formula`` per formula — exactly where the bug fired).
"""

import pytest

from argumentation_analysis.agents.core.logic.fol_handler import (
    _sanitize_fol_bool_constants,
)


class TestSanitizeFolBoolConstants:
    """The per-formula ``T``/``F`` -> ``+``/``-`` transform (#1441 Bug B)."""

    def test_bare_T_maps_to_top(self):
        assert _sanitize_fol_bool_constants("P(X) => T") == "P(X) => +"

    def test_bare_F_maps_to_bottom(self):
        assert _sanitize_fol_bool_constants("P(X) && F") == "P(X) && -"

    def test_both_T_and_F_in_one_formula(self):
        assert _sanitize_fol_bool_constants("(T || F)") == "(+ || -)"

    def test_identifier_Table_is_not_mangled(self):
        # Word-boundary: T inside an identifier survives.
        assert _sanitize_fol_bool_constants("Table(X)") == "Table(X)"

    def test_t1_atom_is_not_mangled(self):
        assert _sanitize_fol_bool_constants("T1(X)") == "T1(X)"

    def test_lowercase_t_is_not_mangled(self):
        assert _sanitize_fol_bool_constants("t(X)") == "t(X)"

    def test_no_bool_constants_is_noop(self):
        assert _sanitize_fol_bool_constants("forall X: (P(X) => Q(X))") == (
            "forall X: (P(X) => Q(X))"
        )

    def test_idempotent(self):
        once = _sanitize_fol_bool_constants("P(X) => T")
        twice = _sanitize_fol_bool_constants(once)
        assert once == twice == "P(X) => +"


@pytest.mark.tweety
class TestBoolConstantSanitizerRealParse:
    """End-to-end via the production path: a formula with ``T`` that previously
    ParserException'd now parses after sanitization (JVM required, marker
    ``tweety``). Uses ``create_belief_set_programmatically`` which calls
    ``parse_fol_formula`` per formula — exactly where the bug fired (#1441)."""

    def test_T_formula_parses_after_sanitization(self):
        from argumentation_analysis.core import jvm_setup

        jvm_setup.initialize_jvm()
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        TweetyInitializer().ensure_jvm_and_components_are_ready()

        from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler

        handler = FOLHandler()
        # Minimal builder data: one sort, one predicate over it, one formula
        # containing a bare 'T' (the ATT-3 corpus-C shape). Before the fix,
        # parse_fol_formula raised on 'T'; after sanitization it parses.
        builder_data = {
            "_sorts": {"thing": ["socrate"]},
            "_predicates": {"Mortal": ["thing"]},
            "_formulas": ["forall X: (Mortal(X) => T)"],
        }
        # No exception is raised — the 'T' was sanitized to '+' (Top).
        belief_set, _signature = handler.create_belief_set_programmatically(
            builder_data
        )
        assert belief_set is not None
        assert belief_set.size() >= 1
