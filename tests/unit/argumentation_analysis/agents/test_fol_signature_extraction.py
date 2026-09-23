"""Tests for FOL signature extraction with extended symbol support.

Validates extract_fol_metadata handles accented characters, numeric constants,
function symbols, and edge cases. Also tests per-formula isolation retry logic
in the FOL invoke callable.
"""

import pytest

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent


class TestExtractFolMetadataExtended:
    """Test extract_fol_metadata with extended regex patterns."""

    def test_standard_predicates(self):
        """Standard CamelCase predicates with lowercase constants."""
        formulas = ["Mortal(socrates)", "Human(plato)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert "Mortal" in meta["predicates"]
        assert "Human" in meta["predicates"]
        assert meta["predicates"]["Mortal"] == 1
        assert "socrates" in meta["constants"]
        assert "plato" in meta["constants"]

    def test_accented_constants(self):
        """Accented characters in predicate/constant names are sanitized for Tweety."""
        formulas = ["EstPrésident(jean_paul)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        # Predicate name folded to ASCII: EstPrésident -> EstPresident. It was
        # EstPr_sident, which the parser refuses: no underscore in a predicate
        # declaration (#2468).
        assert "EstPresident" in meta["predicates"]
        # Constant sanitized: jean_paul (no accent, stays as-is)
        assert "jean_paul" in meta["constants"]

    def test_numeric_constant_suffixes(self):
        """Numeric suffixes in constants (arg1, fallacy2) should be captured."""
        formulas = ["Asserted(arg1)", "Undermines(fallacy2, arg3)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert "Asserted" in meta["predicates"]
        assert "Undermines" in meta["predicates"]
        assert meta["predicates"]["Undermines"] == 2
        assert "arg1" in meta["constants"]
        assert "fallacy2" in meta["constants"]
        assert "arg3" in meta["constants"]

    def test_multiple_arities(self):
        """Same predicate with different arities — should keep max arity."""
        formulas = ["P(a)", "P(a, b)", "P(x, y, z)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert meta["predicates"]["P"] == 3

    def test_signature_lines_format(self):
        """Signature lines should follow Tweety BNF format."""
        formulas = ["P(a)", "Q(a, b)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)
        sig = meta["signature_lines"]

        # Sort declaration: thing = {a, b}
        assert any("thing" in line and "a" in line and "b" in line for line in sig)
        # Type declarations
        assert any("type(P(thing))" in line for line in sig)
        assert any("type(Q(thing, thing))" in line for line in sig)

    def test_empty_formulas(self):
        """Empty formula list: no predicate, no constant, and a sort Tweety
        accepts. It used to be ``thing = {}``, which Tweety refuses (#2495)."""
        meta = FOLLogicAgent.extract_fol_metadata([])

        assert meta["predicates"] == {}
        assert meta["constants"] == set()
        assert meta["signature_lines"] == ["thing = {witness}"]

    def test_a_set_without_constants_declares_a_witness_in_its_sort_only(self):
        """#2495: the witness is in the sort, never in ``constants`` nor in a
        formula."""
        meta = FOLLogicAgent.extract_fol_metadata(["forall X: (Man(X))"])

        assert meta["sorts"] == {"thing": ["witness"]}
        assert meta["signature_lines"][0] == "thing = {witness}"
        assert meta["constants"] == set()
        assert meta["formulas"] == ["forall X: (Man(X))"]

    def test_the_witness_does_not_take_a_predicate_name(self):
        """#2495: a constant named like a predicate is an input EProver
        refuses, so the witness steps aside."""
        meta = FOLLogicAgent.extract_fol_metadata(
            ["forall X: (witness(X) && witness2(X))"]
        )

        assert meta["sorts"] == {"thing": ["witness3"]}

    def test_a_set_that_names_a_constant_gets_no_witness(self):
        meta = FOLLogicAgent.extract_fol_metadata(["forall X: (Man(X))", "Man(a)"])

        assert meta["sorts"] == {"thing": ["a"]}

    def test_a_lent_domain_takes_the_witness_place(self):
        """#2492's domain already gives the sort an individual; an empty
        domain lends none, and the witness is declared (#2495)."""
        lent = FOLLogicAgent.extract_fol_metadata(["forall X: (Man(X))"], domain={"a"})
        empty = FOLLogicAgent.extract_fol_metadata(["forall X: (Man(X))"], domain=set())

        assert lent["sorts"] == {"thing": ["a"]}
        assert empty["sorts"] == {"thing": ["witness"]}
        assert empty["constants"] == set()

    def test_quantified_formula_with_implication(self):
        """Complex formula with forall, =>, and multiple predicates."""
        formulas = ["forall X: (Fallacious(X) => !FullySupported(X))"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert "Fallacious" in meta["predicates"]
        assert "FullySupported" in meta["predicates"]
        assert len(meta["constants"]) == 0  # No lowercase args

    def test_mixed_formulas_batch(self):
        """Batch of diverse formulas — all symbols extracted correctly."""
        formulas = [
            "Asserted(arg1)",
            "Undermines(fallacy1, arg1)",
            "Fallacious(arg1)",
            "forall X: (Fallacious(X) => !FullySupported(X))",
        ]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert len(meta["predicates"]) >= 4
        assert "arg1" in meta["constants"]
        assert "fallacy1" in meta["constants"]

    def test_predicate_with_underscore(self):
        """Predicates and constants with underscores should be captured. A
        predicate declaration cannot carry the underscore (#2468): the
        predicate is declared ``IsValid``; a constant keeps it."""
        formulas = ["is_valid(test_case)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert meta["predicate_map"] == {"is_valid": "IsValid"}
        assert "IsValid" in meta["predicates"]
        assert "test_case" in meta["constants"]
        assert meta["formulas"] == ["IsValid(test_case)"]

    def test_constant_collision_disambiguation(self):
        """Distinct constants that sanitize to same name get _v2, _v3 suffixes."""
        formulas = ["P(jean-paul, jean paul, foo-bar, foo_bar)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        constants = meta["constants"]
        # 4 distinct surface forms must produce 4 distinct sanitized constants
        assert len(constants) == 4, f"Expected 4 distinct constants, got {constants}"
        # Verify the mapping is returned
        cmap = meta["constant_map"]
        assert len(cmap) == 4
        assert all(v in constants for v in cmap.values())

    def test_constant_collision_suffixes(self):
        """Collision produces ordered _v2, _v3 suffixes."""
        formulas = ["P(a-b, a_b, a b)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        constants = meta["constants"]
        # "a-b", "a_b", "a b" all sanitize to "a_b" → need disambiguation
        assert len(constants) == 3
        sanitized_names = sorted(constants)
        assert sanitized_names[0] == "a_b"
        assert sanitized_names[1] == "a_b_v2"
        assert sanitized_names[2] == "a_b_v3"

    def test_predicate_collision_disambiguation(self):
        """Distinct predicates that sanitize to same name get _v2, _v3 suffixes."""
        formulas = ["Est-Valide(x)", "Est_Valide(y)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        predicates = meta["predicates"]
        # Both sanitize to "Est_Valide" — must be disambiguated
        assert len(predicates) == 2, f"Expected 2 distinct predicates, got {predicates}"
        pmap = meta["predicate_map"]
        assert len(pmap) == 2
        assert all(v in predicates for v in pmap.values())

    def test_no_collision_when_names_already_distinct(self):
        """No suffixes added when sanitized names are naturally distinct."""
        formulas = ["Foo(a)", "Bar(b)"]
        meta = FOLLogicAgent.extract_fol_metadata(formulas)

        assert "Foo" in meta["predicates"]
        assert "Bar" in meta["predicates"]
        cmap = meta["constant_map"]
        assert cmap["a"] == "a"
        assert cmap["b"] == "b"

    def test_a_constant_is_not_named_like_the_sort(self):
        """#2516: Tweety's TPTP writes the sort ``thing`` as a predicate, and
        EProver refuses a name used with two arities."""
        meta = FOLLogicAgent.extract_fol_metadata(["forall X: (Man(X))", "!Man(thing)"])

        assert meta["constant_map"] == {"thing": "thing_v2"}
        assert meta["sorts"] == {"thing": ["thing_v2"]}
        assert meta["formulas"] == ["forall X: (Man(X))", "!Man(thing_v2)"]

    def test_a_constant_is_not_named_like_a_predicate(self):
        """#2516: the predicate keeps its name; the constant is renamed where
        it stands alone."""
        meta = FOLLogicAgent.extract_fol_metadata(["forall X: (p(X))", "!p(p)"])

        assert meta["predicate_map"] == {"p": "p"}
        assert meta["constant_map"] == {"p": "p_v2"}
        assert meta["formulas"] == ["forall X: (p(X))", "!p(p_v2)"]

    def test_a_predicate_is_not_named_like_the_sort(self):
        """#2516: a predicate ``thing`` would be read as membership of the
        sort."""
        meta = FOLLogicAgent.extract_fol_metadata(["!thing(c)", "thing2(c)"])

        assert meta["predicate_map"] == {"thing": "thing3", "thing2": "thing2"}
        assert "type(thing3(thing))" in meta["signature_lines"]
        assert meta["formulas"] == ["!thing3(c)", "thing2(c)"]
