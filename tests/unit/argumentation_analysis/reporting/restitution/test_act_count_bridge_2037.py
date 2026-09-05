"""#2037 — two numbers under the same syntagme « arguments extraits », no bridge.

Measured (R931, corpus_A/corpus_B): Acte I says « 149 arguments extraits »
(corpus_B) while Acte II says « bâti à partir des neuf arguments extraits » —
same syntagme, two numbers, no bridge. corpus_A carries the same form
(132 vs 6).

Code-side measurement (population, phase, state key per number):

* Acte I inventory — ``len(state.identified_arguments)``, rendered in the
  act1 conducted prompt (« Inventaire argumentatif : N argument(s)
  extrait(s) »), populated by the fact_extraction writer
  (``_write_fact_extraction_to_state`` → ``state.add_argument``).
* Acte II Dung volume — ``len(dung_frameworks[fw]["arguments"])`` on the
  primary native ``verification_*`` entry, fed by
  ``_extract_arguments_from_context`` (extract/quality upstream, caps
  40/8/6, sentence-split fallback) — a DIFFERENT population from the
  inventory even though both are "extracted arguments" in a loose sense.

Both numbers can be true at once; the defect is the shared syntagme with no
named reduction. Anti-pendule (issue): NEVER align the numbers — the fix
names the reduction and differentiates the syntagmes.

Privacy HARD: synthetic opaque sizes only (149/9, 132/6 as shapes, no
corpus text).
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)


def _state(n_identified: int, fw_n_args: int) -> SimpleNamespace:
    """Synthetic state: ``n_identified`` inventory units, a native Dung
    framework whose ``arguments`` list carries ``fw_n_args`` texts."""
    identified = {
        f"arg_{i + 1}": f"Unité argumentative synthétique {i + 1}."
        for i in range(n_identified)
    }
    fw_args = [f"Argument structuré synthétique {i + 1}." for i in range(fw_n_args)]
    return SimpleNamespace(
        identified_arguments=identified,
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={
            "fw_1": {
                "name": "verification_preferred",
                "arguments": fw_args,
                "attacks": [[fw_args[0], fw_args[-1]]] if fw_n_args >= 2 else [],
                "extensions": {"all_members": list(fw_args)},
            }
        },
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        governance_decisions=[],
        debate_transcripts=[],
    )


def _dung_verdict(state: SimpleNamespace) -> str:
    from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
        _collect_formal_findings,
    )

    findings = [f for f in _collect_formal_findings(state) if f.kind == "dung"]
    assert findings, "a decodable native framework must yield its finding"
    return findings[0].verdict


# --- negative controls: the gate reddens the pre-fix artifact shapes -------------


class TestGateSameSyntagmeTwoNumbers:
    """DoD 2 + 4: no rendered body may carry two numbers under « arguments
    extraits » without a bridge — the pre-fix corpus shapes must FAIL."""

    def test_prefix_corpus_b_shape_fails(self):
        # Verbatim shape (counting vocabulary only): Acte I digits + Acte II
        # number WORD under the same syntagme, no bridge.
        body = (
            "### Acte I\n\nLe discours livre 149 arguments extraits, un flux "
            "continu de thèses et d'appuis.\n\n"
            "### Acte II\n\nLe graphe de Dung, bâti à partir des neuf "
            "arguments extraits, réorganise le matériau."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "FAIL", (
            "#2037: two distinct values (149 / neuf) under « arguments "
            f"extraits » must FAIL, got {verdict.band} — {verdict.reasons}"
        )

    def test_prefix_corpus_a_shape_fails(self):
        # corpus_A shape: 132 vs six (digits vs word).
        body = (
            "L'inventaire recense 132 arguments extraits. Le graphe bâti sur "
            "les six arguments extraits ne fragilise rien."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "FAIL"

    def test_bridged_body_passes(self):
        # Post-fix shape: the inventory keeps the syntagme, the graph volume
        # is renamed AND bridged (« retenus pour le graphe », « sur N unités
        # argumentatives identifiées »).
        body = (
            "### Acte I\n\nLe discours livre 149 arguments extraits.\n\n"
            "### Acte II\n\nLe graphe d'attaque construit sur les 9 "
            "arguments retenus pour le graphe, sur 149 unités "
            "argumentatives identifiées, réorganise le matériau."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "PASS", verdict.reasons

    def test_same_value_twice_passes(self):
        # The invariant is TWO DISTINCT values — repetition of one number is
        # coherent, not a contradiction.
        body = (
            "Les 12 arguments extraits here. Plus loin, les 12 arguments "
            "extraits again."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "PASS", verdict.reasons


# --- the digest bridge contract --------------------------------------------------


class TestReaderConsequenceBridgesTheReduction:
    def test_bridged_frame_names_both_populations(self):
        from argumentation_analysis.reporting.restitution.dung_reader import (
            reader_consequence,
        )

        text = reader_consequence(
            n_arguments=9,
            n_attacks=12,
            n_rejected=1,
            semantics_label="preferred",
            n_identified=149,
        )
        # The reduction is NAMED: retained-for-the-graph + identified total.
        assert "9 arguments retenus pour le graphe" in text
        assert "sur 149 unités argumentatives identifiées" in text
        # The bare syntagme no longer carries the graph's number.
        assert "9 arguments extraits" not in text

    def test_equal_populations_keep_the_plain_frame(self):
        from argumentation_analysis.reporting.restitution.dung_reader import (
            reader_consequence,
        )

        # When the graph covers the whole inventory, « arguments extraits »
        # is accurate and matches Acte I — no bridge needed.
        text = reader_consequence(
            n_arguments=9,
            n_attacks=3,
            n_rejected=0,
            semantics_label="preferred",
            n_identified=9,
        )
        assert "9 arguments extraits" in text
        assert "retenus pour le graphe" not in text

    def test_unknown_total_keeps_the_plain_frame(self):
        from argumentation_analysis.reporting.restitution.dung_reader import (
            reader_consequence,
        )

        text = reader_consequence(
            n_arguments=9,
            n_attacks=3,
            n_rejected=1,
            semantics_label="preferred",
        )
        assert "9 arguments extraits" in text

    def test_act2_wires_the_inventory_count(self):
        # End-to-end through the act2 collector: 12 identified units, a
        # 3-argument graph → the finding's verdict carries the bridge.
        verdict = _dung_verdict(_state(n_identified=12, fw_n_args=3))
        assert "3 arguments retenus pour le graphe" in verdict
        assert "sur 12 unités argumentatives identifiées" in verdict
        assert "3 arguments extraits" not in verdict

    def test_act2_equal_counts_unchanged(self):
        verdict = _dung_verdict(_state(n_identified=3, fw_n_args=3))
        assert "3 arguments extraits" in verdict

    def test_number_words_and_digits_are_the_same_value(self):
        # « neuf » and « 9 » are ONE value — the pre-fix corpus_B defect is
        # the PAIR (149, neuf), not a digits-vs-words false alarm.
        body = (
            "Les 149 arguments extraits d'abord. Puis les neuf arguments "
            "extraits du graphe — même population, pont nommé."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "FAIL"
