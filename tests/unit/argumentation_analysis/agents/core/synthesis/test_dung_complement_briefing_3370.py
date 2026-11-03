"""#3370 — the Dung briefing line states the complement the extension left out.

R1136a paid pass (doc_A): the deep synthesis said « … et le dossier ne permet
pas d'isoler les arguments exclus » while Act II named two of the six the
extension left out. ``build_artifact_briefing`` printed the extensions — 34
members of 40 — and let the per-item budget cut the member list; nothing
computed ``arguments − ⋃ extensions``, so the short side the reader needs
never reached the writer.

Born red on the parent commit: no line carries ``outside_all_extensions``,
and the six excluded ids appear nowhere in the briefing.

The fixtures follow the producer's shape (``_write_dung_extensions_to_state``,
#2672/#3008): one ``verification_{sem}`` entry per semantics whose
``extensions`` is ``{"extensions", "count", "sizes", "all_members"}`` — the
keyed shape (``conversational_dung``, ``{"grounded": [...]}``) is the control.
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.reporting.restitution.cited_units import CUT_MARKER

# The issue's own 40 / 34 / 6 measure, synthetic ids: the six the extension
# leaves out, in producer order.
LABELS = [f"arg_{i}" for i in range(1, 41)]
EXCLUDED = ["arg_2", "arg_6", "arg_7", "arg_10", "arg_12", "arg_20"]
INSIDE = [a for a in LABELS if a not in EXCLUDED]
assert len(INSIDE) == 34

# Long labels — the shape a stored run state carries when units are keyed by
# their text. Synthetic prose, one sentence each, so the cut boundary logic
# sees real sentence ends.
SENTENCE_LABELS = [
    f"Unit {i} states a distinct claim in its own sentence." for i in range(1, 11)
]
SENT_INSIDE = SENTENCE_LABELS[:7]
SENT_OUTSIDE = SENTENCE_LABELS[7:]


def _verification(semantics, arguments, extensions, attacks=()):
    """One ``verification_{sem}`` entry as the writer files it (#2672)."""
    return {
        "name": f"verification_{semantics}",
        "arguments": list(arguments),
        "attacks": [list(a) for a in attacks],
        "extensions": {
            "extensions": [list(e) for e in extensions],
            "count": len(extensions),
            "sizes": [len(e) for e in extensions],
            "all_members": sorted({m for e in extensions for m in e}),
        },
    }


def _dung_line(entry, key="dung_3"):
    """The briefing line of the single Dung entry, payload only."""
    state = SimpleNamespace(dung_frameworks={key: entry})
    briefing = DeepSynthesisAgent.build_artifact_briefing(state)
    prefix = f"[artifact:dung_frameworks.{key}] "
    lines = [line for line in briefing.splitlines() if line.startswith(prefix)]
    assert len(lines) == 1, lines
    return lines[0][len(prefix) :]


class TestTheSixExcludedIdsPrintWholeBeforeTheCut:
    """The issue's witness: 40 labels, one extension of 34, 6 outside."""

    def test_the_line_states_the_complement_with_its_count(self):
        line = _dung_line(_verification("preferred", LABELS, [INSIDE]))
        assert f"outside_all_extensions=6 {EXCLUDED!r}" in line

    def test_the_excluded_keep_the_producer_order(self):
        line = _dung_line(_verification("preferred", LABELS, [INSIDE]))
        assert EXCLUDED == ["arg_2", "arg_6", "arg_7", "arg_10", "arg_12", "arg_20"]
        assert f"outside_all_extensions=6 {EXCLUDED!r}" in line

    def test_the_cut_marker_lands_in_the_members_not_in_the_excluded(self):
        line = _dung_line(_verification("preferred", LABELS, [INSIDE]))
        complement = line.index("outside_all_extensions=")
        members = line.index("preferred_extensions=")
        marker = line.index(CUT_MARKER)
        assert complement < members < marker
        # ``repr`` dodges the arg_2 ⊂ arg_20 substring trap: "'arg_2'" is not
        # a token of "'arg_20'".
        for arg in EXCLUDED:
            assert line.index(repr(arg)) < marker

    def test_the_member_list_is_what_got_cut(self):
        line = _dung_line(_verification("preferred", LABELS, [INSIDE]))
        assert CUT_MARKER in line
        # the last member never reaches the writer — 34 ids do not fit, and
        # the budget is not raised to print them (#2967).
        assert repr("arg_40") not in line


class TestCoveringExtensionStatesTheEmptyComplement:
    """The control: none excluded is a measure, so the line says so."""

    def test_the_line_says_none_excluded(self):
        line = _dung_line(
            _verification(
                "preferred", ["arg_1", "arg_2", "arg_3"], [["arg_1", "arg_2", "arg_3"]]
            )
        )
        assert "outside_all_extensions=0 []" in line

    def test_the_complement_still_precedes_the_members(self):
        line = _dung_line(
            _verification(
                "preferred", ["arg_1", "arg_2", "arg_3"], [["arg_1", "arg_2", "arg_3"]]
            )
        )
        assert line.index("outside_all_extensions=") < line.index(
            "preferred_extensions="
        )


class TestOnlyComputedExtensionsCarryAComplement:
    """#2672 — an entry that computed no extension has no complement measure."""

    def test_a_formalism_sidecar_has_no_complement(self):
        sidecar = {
            "name": "delp_analysis",
            "arguments": [],
            "extensions": {"query_results": [{"query": "q"}]},
        }
        line = _dung_line(sidecar, key="delp_analysis")
        assert "outside_all_extensions" not in line

    def test_verification_multi_is_not_a_semantics(self):
        line = _dung_line(_verification("multi", LABELS, [INSIDE]))
        assert "outside_all_extensions" not in line

    def test_an_entry_that_never_computed_extensions_has_no_complement(self):
        entry = {
            "name": "verification_grounded",
            "arguments": LABELS,
            "attacks": [],
            "extensions": {},
        }
        line = _dung_line(entry)
        assert "outside_all_extensions" not in line


class TestTheComplementIsOutsideAllListedExtensions:
    """« outside_all_extensions » is the union complement, not one semantics'."""

    def test_an_argument_in_any_extension_is_not_excluded(self):
        entry = {
            "name": "conversational_dung",
            "arguments": ["a", "b", "c", "d", "e"],
            "attacks": [],
            "extensions": {"grounded": [["a", "b"]], "preferred": [["c"]]},
        }
        line = _dung_line(entry)
        assert "outside_all_extensions=2 ['d', 'e']" in line


class TestLongLabelsKeepTheExcludedWhole:
    """A stored state keyed by unit text: the complement must survive whole."""

    def test_every_excluded_label_prints_whole_with_its_bracket(self):
        line = _dung_line(_verification("preferred", SENTENCE_LABELS, [SENT_INSIDE]))
        assert f"outside_all_extensions=3 {SENT_OUTSIDE!r}" in line

    def test_no_member_text_is_printed_once_the_complement_spent_the_budget(self):
        line = _dung_line(_verification("preferred", SENTENCE_LABELS, [SENT_INSIDE]))
        assert line.index(CUT_MARKER) > line.index(repr(SENT_OUTSIDE[-1]))
        # the omitted members are marked, never silently dropped (#2967).
        assert line.endswith(CUT_MARKER)
        assert repr(SENT_INSIDE[0]) not in line


class TestNoCutWhenNothingNeedsCutting:
    def test_a_line_that_fits_carries_no_marker(self):
        line = _dung_line(
            _verification(
                "preferred", ["arg_1", "arg_2", "arg_3"], [["arg_1", "arg_2"]]
            )
        )
        assert CUT_MARKER not in line
        assert "outside_all_extensions=1 ['arg_3']" in line


class TestTheComplementAndTheMembersAreSeparated:
    """R1137 — the separator lives OUTSIDE the cut.

    ``truncate_at_boundary`` opens with ``str(text).strip()`` (its own
    contract, relied on by every other caller), so the leading space of
    ``_members`` was dropped and the line read
    ``… 'arg_20']preferred_extensions=…``. The first version of these
    witnesses checked order and containment only — a glued line passed all
    thirteen of them.
    """

    def test_the_ids_case_keeps_its_separator(self):
        line = _dung_line(_verification("preferred", LABELS, [INSIDE]))
        assert "] preferred_extensions=" in line
        assert "]preferred_extensions=" not in line

    def test_the_covering_case_keeps_its_separator(self):
        line = _dung_line(
            _verification(
                "preferred", ["arg_1", "arg_2", "arg_3"], [["arg_1", "arg_2", "arg_3"]]
            )
        )
        assert "0 [] preferred_extensions=" in line
        assert "0 []preferred_extensions=" not in line

    def test_the_omitted_members_keep_the_marker_separated(self):
        """Control: the marker branch already starts with its own space — a
        future ``lstrip`` on the tail must not take it."""
        line = _dung_line(_verification("preferred", SENTENCE_LABELS, [SENT_INSIDE]))
        assert line.endswith("]" + CUT_MARKER)
