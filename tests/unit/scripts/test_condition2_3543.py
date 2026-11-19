"""Witness for #3543: the condition-2 counter is a command, not a hand count.

The per-cycle verdict was applied by hand from two STABILITY.md files: the
DIRECTION of a state change and the rule that both families must agree lived
nowhere in code. This witness builds synthetic consensus directories the way
test_judge_panel_3375 builds stored rows (consensus.votes + fragile, no
document text) and replays every precedent the issue measured.

Free: no key, no network, no corpus — votes planted by hand.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.dataset import judge_panel as jp  # noqa: E402
from scripts.panel import condition2  # noqa: E402
from scripts.panel import run_cycle  # noqa: E402

S = "PIPELINE_SUPPLIES"
WG = "PIPELINE_SUPPLIES_WITH_GAP"
P = "PARITY"
ZW = "ZEROSHOT_WINS"


# --- synthetic consensus rows --------------------------------------------
# Each document's state is decided by its two deciding questions
# (core = a verified supply, severe = a verified severe item), exactly as
# jp.state_from_votes defines it. Fragility is planted, not re-derived.


def _row(doc, *, core, severe, abstain=False, fragile=False):
    parsed, need = 6, 4
    votes = {
        "parsed": parsed,
        "need": need,
        "core": 6 if core else 0,
        "severe": 6 if severe else 0,
        "abstain": 6 if abstain else 0,
    }
    return {
        "opaque_id": doc,
        "reported_state": jp.state_from_votes(votes),
        "kept": [],
        "consensus": {
            "passes": parsed,
            "need": need,
            "parsed": parsed,
            "sources": [],
            "votes": votes,
            "fragile": fragile,
        },
    }


def _write_dir(path, rows, *, run_head="z" * 40):
    path.mkdir(parents=True, exist_ok=True)
    for row in rows:
        (path / f"{row['opaque_id']}.json").write_text(
            json.dumps(row), encoding="utf-8"
        )
    (path / jp.META_FILENAME).write_text(
        json.dumps({"run_head": run_head}), encoding="utf-8"
    )
    return path


def _direction(tmp_path, name, current, previous):
    cur = _write_dir(tmp_path / f"{name}_cur", current)
    prev = _write_dir(tmp_path / f"{name}_prev", previous)
    return condition2.family_direction(cur, prev)


class TestDirection:
    def test_the_declared_order(self):
        assert condition2.STATE_ORDER == (ZW, P, WG, S)

    def test_direction_of_each_step(self):
        assert condition2.state_direction(P, S) == "toward"
        assert condition2.state_direction(S, P) == "away"
        assert condition2.state_direction(S, S) == "unchanged"
        assert condition2.state_direction(WG, P) == "away"

    def test_a_change_into_or_out_of_the_order_is_outside(self):
        assert condition2.state_direction("BOTH_ABSTAIN", S) == "outside"
        assert condition2.state_direction(S, "BOTH_ABSTAIN") == "outside"
        assert condition2.state_direction("UNPARSED", P) == "outside"


class TestTruthTable:
    """The (core, severe) -> state mapping, as judge_panel.state_from_votes
    computes it: severe=True means a severe item is PRESENT (WG), not absent.
    Every fixture below leans on this — pin it once, by execution."""

    def test_the_four_deciding_combinations(self):
        assert (
            jp.state_from_votes(
                {"parsed": 6, "need": 4, "core": 6, "severe": 0, "abstain": 0}
            )
            == S
        )
        assert (
            jp.state_from_votes(
                {"parsed": 6, "need": 4, "core": 6, "severe": 6, "abstain": 0}
            )
            == WG
        )
        assert (
            jp.state_from_votes(
                {"parsed": 6, "need": 4, "core": 0, "severe": 6, "abstain": 0}
            )
            == ZW
        )
        assert (
            jp.state_from_votes(
                {"parsed": 6, "need": 4, "core": 0, "severe": 0, "abstain": 0}
            )
            == P
        )

    def test_abstain_overrides(self):
        # BOTH_ABSTAIN needs the core and severe majorities to fail AND the
        # abstain majority to hold: core=0, severe=0, abstain>parsed/2.
        assert (
            jp.state_from_votes(
                {"parsed": 6, "need": 4, "core": 0, "severe": 0, "abstain": 6}
            )
            == "BOTH_ABSTAIN"
        )
        # With a core majority, abstain does not demote the state.
        assert (
            jp.state_from_votes(
                {"parsed": 6, "need": 4, "core": 6, "severe": 0, "abstain": 6}
            )
            == S
        )


class TestSettled:
    def test_only_documents_non_fragile_in_both_cycles_are_settled(self, tmp_path):
        current = [
            _row("doc_A", core=True, severe=False),
            _row("doc_B", core=True, severe=True, fragile=True),
        ]
        previous = [
            _row("doc_A", core=True, severe=False),
            _row("doc_B", core=False, severe=True),
        ]
        reading = _direction(tmp_path, "settled", current, previous)
        assert reading["settled"] == ["doc_A"]
        assert reading["toward"] == []
        assert reading["away"] == []

    def test_toward_and_away_name_their_documents(self, tmp_path):
        # Truth table (see TestTruthTable): core=T/severe=F=S; T/T=WG; F/T=ZW; F/F=P.
        # doc_A: P -> S = toward. doc_B: S -> WG = away.
        current = [
            _row("doc_A", core=True, severe=False),  # S
            _row("doc_B", core=True, severe=True),  # WG
        ]
        previous = [
            _row("doc_A", core=False, severe=False),  # P
            _row("doc_B", core=True, severe=False),  # S
        ]
        reading = _direction(tmp_path, "named", current, previous)
        assert reading["toward"] == ["doc_A"]
        assert reading["away"] == ["doc_B"]
        assert reading["settled"] == ["doc_A", "doc_B"]


class TestFamilyVerdict:
    def test_progress_needs_toward_and_no_away(self, tmp_path):
        current = [_row("doc_A", core=True, severe=False)]  # S
        previous = [_row("doc_A", core=False, severe=False)]  # P
        assert (
            _direction(tmp_path, "prog", current, previous)["direction"] == "progress"
        )

    def test_two_toward_and_one_away_is_no_progress(self, tmp_path):
        # The looser reading "more toward than away" would call this progress.
        # doc_A: P->S (toward). doc_B: P->S (toward). doc_C: S->WG (away).
        current = [
            _row("doc_A", core=True, severe=False),  # S
            _row("doc_B", core=True, severe=False),  # S
            _row("doc_C", core=True, severe=True),  # WG
        ]
        previous = [
            _row("doc_A", core=False, severe=False),  # P
            _row("doc_B", core=False, severe=False),  # P
            _row("doc_C", core=True, severe=False),  # S
        ]
        assert (
            _direction(tmp_path, "mixed", current, previous)["direction"]
            == "no_progress"
        )

    def test_nothing_settled_is_not_measurable(self, tmp_path):
        current = [_row("doc_A", core=True, severe=True, fragile=True)]
        previous = [_row("doc_A", core=False, severe=True)]
        assert (
            _direction(tmp_path, "none", current, previous)["direction"]
            == "not_measurable"
        )


class TestPrecedents:
    """The five readings the issue re-derived on the stored directories."""

    def test_c1_to_c2_sonnet_no_progress(self, tmp_path):
        # 5 settled, doc_B ZW->WG (toward), doc_J S->WG (away).
        current = [
            _row("doc_B", core=True, severe=True),  # WG
            _row("doc_J", core=True, severe=True),  # WG
            _row("doc_X", core=True, severe=False),  # S, unchanged
            _row("doc_Y", core=True, severe=False),  # S, unchanged
            _row("doc_Z", core=True, severe=False),  # S, unchanged
        ]
        previous = [
            _row("doc_B", core=False, severe=True),  # ZW
            _row("doc_J", core=True, severe=False),  # S
            _row("doc_X", core=True, severe=False),
            _row("doc_Y", core=True, severe=False),
            _row("doc_Z", core=True, severe=False),
        ]
        reading = _direction(tmp_path, "c2", current, previous)
        assert len(reading["settled"]) == 5
        assert reading["toward"] == ["doc_B"]
        assert reading["away"] == ["doc_J"]
        assert reading["direction"] == "no_progress"

    def test_c2_to_c3b_sonnet_no_progress_no_change(self, tmp_path):
        rows = [
            _row("doc_A", core=True, severe=False),
            _row("doc_B", core=False, severe=False),
            _row("doc_C", core=True, severe=True),
        ]
        reading = _direction(tmp_path, "c3b", list(rows), list(rows))
        assert reading["toward"] == []
        assert reading["away"] == []
        assert reading["direction"] == "no_progress"

    def test_c5_to_c6_gemini_no_progress(self, tmp_path):
        # doc_C ZW->WG (toward), doc_E WG->P (away), doc_F S->WG (away).
        current = [
            _row("doc_C", core=True, severe=True),  # WG
            _row("doc_E", core=False, severe=False),  # P
            _row("doc_F", core=True, severe=True),  # WG
        ]
        previous = [
            _row("doc_C", core=False, severe=True),  # ZW
            _row("doc_E", core=True, severe=True),  # WG
            _row("doc_F", core=True, severe=False),  # S
        ]
        reading = _direction(tmp_path, "c6", current, previous)
        assert reading["toward"] == ["doc_C"]
        assert reading["away"] == ["doc_E", "doc_F"]
        assert reading["direction"] == "no_progress"


class TestPositiveControl:
    """The fixture is faithful to the shape compare_passes measures."""

    def test_compare_passes_reads_the_fixture_states(self, tmp_path):
        # compare_passes(prev, cur): state_a=prev, state_b=cur.
        current = [
            _row("doc_A", core=True, severe=True),  # WG
            _row("doc_B", core=False, severe=False, fragile=True),  # P, fragile (cur)
        ]
        previous = [
            _row("doc_A", core=True, severe=False),  # S
            _row("doc_B", core=True, severe=False),  # S
        ]
        cur = _write_dir(tmp_path / "pc_cur", current)
        prev = _write_dir(tmp_path / "pc_prev", previous)
        report = jp.compare_passes(jp.load_rows(prev), jp.load_rows(cur))
        by_doc = {entry["opaque_id"]: entry for entry in report}
        assert by_doc["doc_A"]["state_a"] == S  # previous
        assert by_doc["doc_A"]["state_b"] == WG  # current
        assert by_doc["doc_A"]["fragile_a"] is False
        assert by_doc["doc_B"]["fragile_b"] is True  # current is fragile
        assert by_doc["doc_B"]["state_a"] == S
        assert by_doc["doc_B"]["state_b"] == P

    def test_the_markdown_is_byte_identical_and_the_json_is_written(self, tmp_path):
        # _write_stability's markdown must not move (#3543's DoD); the JSON
        # carries the same report as data.
        cur = _write_dir(tmp_path / "st_cur", [_row("doc_A", core=True, severe=False)])
        prev = _write_dir(
            tmp_path / "st_prev", [_row("doc_A", core=False, severe=False)]
        )
        rows = jp.load_rows(cur)
        expected_md = jp.render_stability(
            jp.compare_passes(rows, jp.load_rows(prev)), cur.name, prev.name
        )
        jp._write_stability(cur, rows, prev, None)
        assert (cur / "STABILITY.md").read_text(encoding="utf-8") == expected_md
        data = json.loads((cur / "STABILITY.json").read_text(encoding="utf-8"))
        assert data["name_a"] == cur.name
        assert data["name_b"] == prev.name
        assert [e["opaque_id"] for e in data["report"]] == ["doc_A"]
        # _write_stability calls compare_passes(rows=cur, other=prev):
        # state_a=cur (S), state_b=prev (P).
        assert data["report"][0]["state_a"] == S
        assert data["report"][0]["state_b"] == P


class TestCrossFamily:
    def _reading(self, direction, **kw):
        return {"direction": direction, **kw}

    def test_progress_when_both_progress(self):
        assert (
            condition2.cross_family(
                {"g": self._reading("progress"), "s": self._reading("progress")}
            )
            == "progress"
        )

    def test_no_progress_when_neither_progresses(self):
        assert (
            condition2.cross_family(
                {"g": self._reading("no_progress"), "s": self._reading("no_progress")}
            )
            == "no_progress"
        )

    def test_disagree_is_the_c4b_precedent(self):
        # gemini no change (no_progress), Sonnet doc_H WG->S (progress).
        assert (
            condition2.cross_family(
                {"g": self._reading("no_progress"), "s": self._reading("progress")}
            )
            == "disagree"
        )

    def test_not_measurable_wins_over_everything(self):
        assert (
            condition2.cross_family(
                {"g": self._reading("progress"), "s": self._reading("not_measurable")}
            )
            == "not_measurable"
        )

    def test_one_family_is_not_a_cross_family_reading(self):
        # The #3639 review: the bar says BOTH families. A single family's
        # direction is diagnostic (it stays in `families`), but it must not
        # become a cross-family verdict — the counter would move on it.
        assert (
            condition2.cross_family({"s": self._reading("progress")})
            == "not_measurable"
        )
        assert (
            condition2.cross_family({"s": self._reading("no_progress")})
            == "not_measurable"
        )


class TestCounter:
    def test_no_progress_adds_one(self):
        assert condition2.next_counter("no_progress", 2) == 3

    def test_progress_resets(self):
        assert condition2.next_counter("progress", 5) == 0

    def test_disagree_and_not_measurable_hold(self):
        assert condition2.next_counter("disagree", 2) == 2
        assert condition2.next_counter("not_measurable", 2) == 2


class TestHeads:
    def test_the_pipeline_head_comes_from_the_cycle_record(self, tmp_path):
        cur = _write_dir(tmp_path / "h_cur", [_row("doc_A", core=True, severe=False)])
        cycle = tmp_path / "cycle"
        cycle.mkdir()
        (cycle / "pipeline.json").write_text(
            json.dumps({"head": "p" * 40}), encoding="utf-8"
        )
        heads = condition2.read_heads(cur, cycle)
        assert heads["pipeline_head"] == "p" * 40
        assert heads["pipeline_head_source"].endswith("pipeline.json")
        assert heads["zeroshot_head"] == "z" * 40  # named as the zero-shot arm's

    def test_without_a_record_the_signatures_carry_the_head(self, tmp_path):
        cur = _write_dir(tmp_path / "h2_cur", [_row("doc_A", core=True, severe=False)])
        cycle = tmp_path / "cycle2"
        (cycle / "signatures").mkdir(parents=True)
        (cycle / "signatures" / "signature_doc_A.json").write_text(
            json.dumps({"provenance": {"code_sha": "q" * 40}}), encoding="utf-8"
        )
        heads = condition2.read_heads(cur, cycle)
        assert heads["pipeline_head"] == "q" * 40
        assert "signature_doc_A.json" in heads["pipeline_head_source"]


class TestTheCommand:
    def test_two_agreeing_families_move_the_counter(self, tmp_path, capsys):
        # The #3639 review's second CLI witness: with BOTH families agreeing
        # (both progress), the counter moves (resets).
        cur = _write_dir(tmp_path / "cli_cur", [_row("doc_A", core=True, severe=False)])
        prev = _write_dir(
            tmp_path / "cli_prev", [_row("doc_A", core=False, severe=False)]
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--family",
                f"s={cur}|{prev}",
                "--family",
                f"g={cur}|{prev}",
                "--counter-before",
                "3",
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["verdict"] == "progress"
        assert result["counter_before"] == 3
        assert result["counter_after"] == 0
        assert result["families"]["s"]["toward"] == ["doc_A"]
        assert result["families"]["g"]["toward"] == ["doc_A"]
        assert result["heads"]["zeroshot_head"] == "z" * 40
        assert "progress" in capsys.readouterr().out

    def test_one_family_holds_the_counter(self, tmp_path, capsys):
        # The #3639 review's first CLI witness: a single family — however
        # strong its direction — is not a cross-family reading. The verdict
        # is not_measurable and the counter HOLDS (3 -> 3, not 3 -> 0).
        cur = _write_dir(tmp_path / "cli_cur", [_row("doc_A", core=True, severe=False)])
        prev = _write_dir(
            tmp_path / "cli_prev", [_row("doc_A", core=False, severe=False)]
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--family",
                f"s={cur}|{prev}",
                "--counter-before",
                "3",
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        # The family's own direction is still reported (diagnostic replay).
        assert result["families"]["s"]["direction"] == "progress"
        assert result["families"]["s"]["toward"] == ["doc_A"]
        # But it does not become the cross-family verdict.
        assert result["verdict"] == "not_measurable"
        assert result["counter_before"] == 3
        assert result["counter_after"] == 3
        assert "not_measurable" in capsys.readouterr().out

    def test_the_previous_cycle_counter_is_read_back(self, tmp_path):
        prev_cycle = tmp_path / "previous_cycle"
        prev_cycle.mkdir()
        (prev_cycle / "condition2.json").write_text(
            json.dumps({"counter_after": 4}), encoding="utf-8"
        )
        assert condition2.read_counter_before(prev_cycle) == 4
        assert condition2.read_counter_before(tmp_path / "absent") is None


class TestRunnerNotWiredYet:
    """The dispatch (#3543) forbids wiring the counter into run_cycle before
    the new-series contract is verified (c21 does not compare to c6–c20).
    This increment is the standalone command + STABILITY.json; the runner
    step belongs to a later increment, after that verification."""

    def test_the_plan_does_not_yet_include_condition2(self, tmp_path):
        cfg = run_cycle.Config(
            tag="w3543",
            panel_file=tmp_path / "panel.json",
            zeroshot_dir=tmp_path / "zeroshot",
            judges=[run_cycle.Judge(name="s", model="m")],
            passes=3,
            results_root=tmp_path / "results",
            compare_with_tag="w3542",
        )
        names = [step.name for step in run_cycle.plan(cfg)]
        assert "condition2" not in names


class TestMutations:
    """Each mutation the dispatch named must redden a witness of its own.

    Three checks: the verdict must not follow a single family; dropping the
    fragile filter must change a verdict; swapping S and WG in the order must
    flip a direction. Each is run as an in-process edit of the module under
    test, on a fixture where the mutation has a different outcome — if the
    verdict was the same with and without the mutation, the witness would
    prove nothing.
    """

    def test_the_verdict_does_not_follow_a_single_family(self):
        # If cross_family returned the first family's direction (mutation),
        # this reading would be "progress" instead of "disagree".
        readings = {
            "g": {"direction": "progress"},
            "s": {"direction": "no_progress"},
        }
        assert condition2.cross_family(readings) == "disagree"

    def test_dropping_the_fragile_filter_changes_the_verdict(
        self, tmp_path, monkeypatch
    ):
        # doc_A is fragile in the current cycle and goes S -> P (away). With
        # the filter, settled is empty -> not_measurable; without it, doc_A
        # is settled and away -> no_progress. Two different outcomes.
        cur = _write_dir(
            tmp_path / "mut_cur",
            [_row("doc_A", core=False, severe=False, fragile=True)],  # P, fragile
        )
        prev = _write_dir(
            tmp_path / "mut_prev",
            [_row("doc_A", core=True, severe=False)],  # S
        )
        with_filter = condition2.family_direction(cur, prev)
        assert with_filter["direction"] == "not_measurable"
        assert with_filter["settled"] == []

        # Mutation: pretend nothing is fragile.
        original = jp.compare_passes

        def no_fragility(rows_a, rows_b):
            report = original(rows_a, rows_b)
            for entry in report:
                entry["fragile_a"] = False
                entry["fragile_b"] = False
            return report

        monkeypatch.setattr(condition2.jp, "compare_passes", no_fragility)
        without_filter = condition2.family_direction(cur, prev)
        assert without_filter["direction"] == "no_progress"
        assert without_filter["settled"] == ["doc_A"]

    def test_swapping_S_and_WG_flips_a_direction(self, tmp_path, monkeypatch):
        # doc_A: P -> WG. With the real order (P < WG < S) that is toward;
        # if S and WG traded places it would still be toward (both above P).
        # Use a transition that actually depends on the S/WG ordering:
        # doc_A: WG -> S is toward under the real order and away if swapped.
        cur = _write_dir(
            tmp_path / "swap_cur", [_row("doc_A", core=True, severe=False)]  # S
        )
        prev = _write_dir(
            tmp_path / "swap_prev", [_row("doc_A", core=True, severe=True)]  # WG
        )
        reading = condition2.family_direction(cur, prev)
        assert reading["direction"] == "progress"
        assert reading["toward"] == ["doc_A"]

        # Mutation: swap S and WG in the order.
        mutated = list(condition2.STATE_ORDER)
        i, j = mutated.index(S), mutated.index(WG)
        mutated[i], mutated[j] = mutated[j], mutated[i]
        monkeypatch.setattr(condition2, "STATE_ORDER", tuple(mutated))
        swapped = condition2.family_direction(cur, prev)
        assert swapped["direction"] == "no_progress"
        assert swapped["away"] == ["doc_A"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
