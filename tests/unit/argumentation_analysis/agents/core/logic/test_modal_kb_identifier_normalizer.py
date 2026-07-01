"""Unit tests for ``ModalIdentifierNormalizer`` (#1326) — no JVM, runs in CI.

Root cause (#1326, firsthand-reproduced): Tweety ``MlParser`` rejects
underscored predicate declarations with ``ParserException: Illegal characters
in predicate definition 'joke_teleprompter'; declaration must conform to
[a-z,A-Z]([a-z,A-Z,0-9])*``. Producers like the spectacular-path
``_construct_modal_kb_from_json`` emit raw ``type(joke_teleprompter)``, so the
KB never parsed and consistency was never decided (R519: 3/3 modal axes
undecided → axis degraded to honest ``None``). The normalizer maps such atoms
to MlParser-legal PascalCase identifiers, applied at the parse point in
``ModalHandler`` (defense-in-depth).

These tests guard the transform itself; the end-to-end real-solver decision is
covered by the integration test ``test_spass_real.TestUnderscoredKbDecides``.
"""

import pytest

from argumentation_analysis.agents.core.logic.modal_kb_identifier_normalizer import (
    ModalIdentifierNormalizer,
)


class TestLegalize:
    """The per-atom transform (#1260 camelCase logic, #1326 collision guard)."""

    def test_underscored_atom_becomes_pascalcase(self):
        n = ModalIdentifierNormalizer()
        assert n.legalize("joke_teleprompter") == "JokeTeleprompter"
        assert n.legalize("heavy_rain") == "HeavyRain"

    def test_already_legal_atom_passes_through(self):
        n = ModalIdentifierNormalizer()
        # Idempotency: the nl path pre-sanitizes; the second pass is a no-op.
        assert n.legalize("Rain") == "Rain"
        assert n.legalize("JokeTeleprompter") == "JokeTeleprompter"
        assert n.legalize("a1") == "a1"

    def test_modal_keywords_are_preserved(self):
        n = ModalIdentifierNormalizer()
        for kw in ("type", "forall", "exists", "true", "false", "implies", "and"):
            assert n.legalize(kw) == kw

    def test_legalize_is_memoized(self):
        n = ModalIdentifierNormalizer()
        first = n.legalize("heavy_rain")
        second = n.legalize("heavy_rain")
        assert first == second == "HeavyRain"


class TestSoundness:
    """The map must be sound — no two distinct atoms collapse to one symbol."""

    def test_atom_and_its_negation_share_a_symbol(self):
        """The contradiction ``heavy_rain`` ∧ ``!heavy_rain`` must be detectable:
        both occurrences map to the SAME symbol, so a reasoner sees
        ``HeavyRain ∧ !HeavyRain`` (inconsistent), not two unrelated atoms."""
        n = ModalIdentifierNormalizer()
        kb = "type(heavy_rain)\n\nheavy_rain\n!heavy_rain\n"
        normalized, _ = n.normalize_belief_set(kb)
        # Both heavy_rain occurrences became the same symbol.
        assert normalized.count("HeavyRain") == 3  # type(...) + atom + negation
        assert "heavy_rain" not in normalized

    def test_distinct_separator_variants_do_not_collapse(self):
        """Soundness guard absent from the original #1260 inline closure: two
        atoms that PascalCase to the same stem (``heavy_rain`` vs ``heavy-rain``)
        must be DISAMBIGUATED, not collapsed. Collapsing distinct atoms would
        fabricate a contradiction (or hide one) — a #1019 theater risk."""
        n = ModalIdentifierNormalizer()
        a = n.legalize("heavy_rain")
        b = n.legalize("heavy-rain")
        assert a != b, (
            f"Distinct source atoms must map to distinct symbols; got {a!r}=={b!r}."
        )
        assert a == "HeavyRain"
        assert b == "HeavyRain1"

    def test_degenerate_atom_falls_back_to_mpatom(self):
        n = ModalIdentifierNormalizer()
        # Only separators → empty stem → MpAtom fallback.
        assert n.legalize("___") == "MpAtom"


class TestNormalizeBeliefSet:
    """Whole-KB normalization + reverse map for readability."""

    def test_declarations_and_body_normalized_consistently(self):
        n = ModalIdentifierNormalizer()
        kb = (
            "type(heavy_rain)\ntype(wet_ground)\n\n"
            "[](heavy_rain => wet_ground)\nheavy_rain\n"
        )
        normalized, reverse = n.normalize_belief_set(kb)
        assert "type(HeavyRain)" in normalized
        assert "type(WetGround)" in normalized
        assert "[](HeavyRain => WetGround)" in normalized
        assert "HeavyRain\n" in normalized
        assert reverse == {"HeavyRain": "heavy_rain", "WetGround": "wet_ground"}

    def test_already_legal_kb_is_unchanged(self):
        n = ModalIdentifierNormalizer()
        kb = "type(Rain)\ntype(Wet)\n\n[](Rain => Wet)\nRain\n"
        normalized, reverse = n.normalize_belief_set(kb)
        assert normalized == kb
        assert reverse == {}

    def test_type_keyword_not_mangled(self):
        """The ``type`` declaration keyword must survive normalization."""
        n = ModalIdentifierNormalizer()
        normalized, _ = n.normalize_belief_set("type(heavy_rain)\nheavy_rain\n")
        assert normalized.startswith("type(")
        assert normalized == "type(HeavyRain)\nHeavyRain\n"

    def test_reserved_seeds_prevent_collision_with_real_atom(self):
        """A generated symbol must never shadow a pre-existing legal atom."""
        # Pre-existing legal atom "HeavyRain" in the KB.
        n = ModalIdentifierNormalizer(reserved={"HeavyRain"})
        # An underscored atom that would PascalCase to HeavyRain must disambiguate.
        assert n.legalize("heavy_rain") == "HeavyRain1"
