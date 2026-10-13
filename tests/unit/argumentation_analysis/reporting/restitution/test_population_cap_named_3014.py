"""#3014 body item 2 — the 40-node budget cap says « N sur M », never just N.

Measured on the pre-fix tree: ``_population_node_units`` returns ``units[:40]``
and records no total, so on a 94-unit state the frame silently holds 40. The
readers that show the population are the REPORT surfaces — the appendix
machinery line (``appendix._dung_machinery_section``) and the Act II body via
``reader_consequence`` (which already bridges « N retenus sur M identifiées »
but derived M from ``state.identified_arguments``, diverging exactly when the
frame came from a fallback population the inventory does not hold: the cap
then bit silently as « N arguments extraits »).

The fix: the producer records ``population_total`` (pre-cap) on the entry, the
readers prefer the entry's own total, and ``dropped_unresolved`` (the #3024
count of caller names the label→id join could not resolve — written on every
member's payload, read by nothing until now) reaches the appendix as a line
when it is non-zero. Zero stays silent: the payload's census default is not
report noise.

Privacy HARD: synthetic opaque sizes and arg_N ids only, no corpus text.
"""

from __future__ import annotations

from types import SimpleNamespace


def _entry(
    n_args: int,
    population_total: int | None = None,
    dropped_unresolved: int | None = None,
    rejected: int = 1,
) -> dict:
    """A native verification entry: ``n_args`` arg_N nodes, a decodable
    grounded extension accepting all but ``rejected`` of them."""
    args = [f"arg_{i + 1}" for i in range(n_args)]
    accepted = args[: n_args - rejected] if rejected else list(args)
    entry: dict = {
        "name": "verification_preferred",
        "arguments": args,
        "attacks": [[args[0], args[-1]]] if n_args >= 2 else [],
        "extensions": {"all_members": accepted},
    }
    if population_total is not None:
        entry["population_total"] = population_total
    if dropped_unresolved is not None:
        entry["dropped_unresolved"] = dropped_unresolved
    return entry


def _state(entry: dict, n_identified: int = 0) -> SimpleNamespace:
    """A state holding the entry and (by default) an EMPTY inventory — the
    fallback-population shape where the pre-fix state bridge said 0."""
    return SimpleNamespace(
        identified_arguments={
            f"arg_{i + 1}": f"Unité synthétique {i + 1}." for i in range(n_identified)
        },
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={"fw_1": entry},
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


class TestTheWriterPersistsTheCounters:
    """The entry is self-describing: the two counters ride it when set."""

    def test_dung_framework_entry_carries_both_counters(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("Corpus synthétique initial.")
        df_id = state.add_dung_framework(
            name="verification_preferred",
            arguments=["arg_1", "arg_2"],
            attacks=[["arg_1", "arg_2"]],
            extensions={},
            population_total=94,
            dropped_unresolved=3,
        )
        entry = state.dung_frameworks[df_id]
        assert entry["population_total"] == 94
        assert entry["dropped_unresolved"] == 3

    def test_absent_counters_stay_absent(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("Corpus synthétique initial.")
        df_id = state.add_dung_framework(
            name="verification_preferred",
            arguments=["arg_1"],
            attacks=[],
            extensions={},
        )
        entry = state.dung_frameworks[df_id]
        assert "population_total" not in entry
        assert "dropped_unresolved" not in entry


class TestTheAppendixNamesTheCap:
    """The report's machinery line says « 40 retenus sur 94 » when the cap
    bites, and names the dropped names when the join lost some."""

    @staticmethod
    def _machinery(entry: dict) -> str:
        from argumentation_analysis.reporting.restitution.appendix import (
            _dung_machinery_section,
        )

        return "\n".join(
            _dung_machinery_section(
                {"dung_frameworks": {"fw_1": entry}}, include_full=False
            )
        )

    def test_the_cap_is_named_when_it_bites(self):
        text = self._machinery(_entry(n_args=40, population_total=94))
        assert "40 arguments retenus sur 94" in text, text
        assert "(plafond de budget)" in text, text

    def test_no_cap_no_bridge(self):
        # A frame that covers its whole population keeps the plain line —
        # the bridge names a reduction, not a coincidence.
        text = self._machinery(_entry(n_args=3, population_total=3))
        assert "3 arguments," in text, text
        assert "retenus sur" not in text, text

    def test_dropped_names_reach_the_line_when_non_zero(self):
        text = self._machinery(_entry(n_args=3, dropped_unresolved=2))
        assert "écartés du graphe : 2" in text, text

    def test_zero_dropped_stays_silent(self):
        # 0 is the payload's census default — a zero line is report noise.
        text = self._machinery(_entry(n_args=3, dropped_unresolved=0))
        assert "écartés" not in text, text


class TestActTwoPrefersTheEntryTotal:
    """The measured defect: a frame built from a fallback population (empty
    inventory) bit the cap silently — the state bridge said 0, so the prose
    read « N arguments extraits » with no named reduction. The entry's own
    total now wins; the state bridge stays for pre-repair entries."""

    def test_the_entry_total_names_the_reduction(self):
        verdict = _dung_verdict(_state(_entry(n_args=40, population_total=94)))
        assert "40 arguments retenus pour le graphe" in verdict, verdict
        assert "sur 94 unités argumentatives identifiées" in verdict, verdict

    def test_pre_repair_entries_keep_the_state_bridge(self):
        # No total on the entry: the #2037 inventory bridge still applies.
        verdict = _dung_verdict(
            _state(_entry(n_args=3, population_total=None), n_identified=12)
        )
        assert "3 arguments retenus pour le graphe" in verdict, verdict
        assert "sur 12 unités argumentatives identifiées" in verdict, verdict

    def test_the_trace_carries_the_entry_total(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            _collect_dung_trace,
        )

        trace = _collect_dung_trace(_state(_entry(n_args=3, population_total=9)))
        assert trace.population_total == 9
        # A malformed total keeps None — the state bridge decides, never a
        # garbage int.
        bad = _entry(n_args=3)
        bad["population_total"] = "many"
        assert _collect_dung_trace(_state(bad)).population_total is None
