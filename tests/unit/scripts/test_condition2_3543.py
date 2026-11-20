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


def _write_dir(
    path,
    rows,
    *,
    run_head="z" * 40,
    series_model="openai/gpt-5.6-luna",
    series_family="openai",
    seed=3375,
    judge_family=None,
    judge_model=None,
    pipeline_run=None,
):
    path.mkdir(parents=True, exist_ok=True)
    for row in rows:
        (path / f"{row['opaque_id']}.json").write_text(
            json.dumps(row), encoding="utf-8"
        )
    meta = {"seed": seed}
    if run_head is not None:
        meta["run_head"] = run_head
    if series_model is not None:
        meta["pipeline_model"] = series_model
        meta["pipeline_family"] = series_family
    if judge_family is not None:
        meta["judge_family"] = judge_family
        meta["judge_model"] = judge_model or "judge-model"
    if pipeline_run is not None:
        # The field's name, as judge_panel.py records it (#3639 review v4).
        meta["pipeline_run"] = {"run_id": pipeline_run}
    (path / jp.META_FILENAME).write_text(json.dumps(meta), encoding="utf-8")
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
        # (both progress), the counter moves (resets). The two families use
        # DISTINCT directory pairs AND two distinct RECORDED judge families
        # (anthropic and google, as the stored META carry them) — reusing one
        # pair under two labels is rejected (TestReusedDirectories), and two
        # labels of one recorded judge family cannot move the counter
        # (TestRecordedProvenance), and both roles must record ONE pipeline
        # run each, the current run differing from the previous (review v4).
        cur_s = _write_dir(
            tmp_path / "cli_cur_s",
            [_row("doc_A", core=True, severe=False)],
            judge_family="anthropic",
            judge_model="claude-sonnet-5-5",
            pipeline_run="run-cur",
        )
        prev_s = _write_dir(
            tmp_path / "cli_prev_s",
            [_row("doc_A", core=False, severe=False)],
            judge_family="anthropic",
            judge_model="claude-sonnet-5-5",
            pipeline_run="run-prev",
        )
        cur_g = _write_dir(
            tmp_path / "cli_cur_g",
            [_row("doc_A", core=True, severe=False)],
            judge_family="google",
            judge_model="gemini-4-argon",
            pipeline_run="run-cur",
        )
        prev_g = _write_dir(
            tmp_path / "cli_prev_g",
            [_row("doc_A", core=False, severe=False)],
            judge_family="google",
            judge_model="gemini-4-argon",
            pipeline_run="run-prev",
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--family",
                f"s={cur_s}|{prev_s}",
                "--family",
                f"g={cur_g}|{prev_g}",
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
        assert result["provenance"]["official"] is True
        assert result["provenance"]["holds"] == []
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


class TestReusedDirectories:
    """The #3639 review v2: the same consensus directories supplied under
    two labels passed the two-family guard and reset the official counter.
    Two labels are not two independent readings — the command rejects any
    consensus directory reused across families, including equivalent path
    spellings."""

    def test_the_same_pair_under_two_labels_is_rejected(self, tmp_path):
        cur = _write_dir(tmp_path / "cur", [_row("doc_A", core=True, severe=False)])
        prev = _write_dir(tmp_path / "prev", [_row("doc_A", core=False, severe=False)])
        with pytest.raises(SystemExit, match="reused"):
            condition2.main(
                [
                    "--family",
                    f"s={cur}|{prev}",
                    "--family",
                    f"g={cur}|{prev}",
                    "--counter-before",
                    "3",
                ]
            )

    def test_an_equivalent_spelling_of_the_same_directory_is_rejected(self, tmp_path):
        # `cur` spelled through a `..` detour resolves to the same directory.
        (tmp_path / "sub").mkdir()
        cur = _write_dir(tmp_path / "cur", [_row("doc_A", core=True, severe=False)])
        prev = _write_dir(tmp_path / "prev", [_row("doc_A", core=False, severe=False)])
        cur_spelled = tmp_path / "sub" / ".." / "cur"
        assert cur_spelled.resolve() == cur.resolve()  # the spelling is equivalent
        with pytest.raises(SystemExit, match="reused"):
            condition2.main(
                [
                    "--family",
                    f"s={cur}|{prev}",
                    "--family",
                    f"g={cur_spelled}|{prev}",
                ]
            )

    def test_two_distinct_pairs_are_accepted(self, tmp_path):
        cur_s = _write_dir(
            tmp_path / "cs",
            [_row("doc_A", core=True, severe=False)],
            judge_family="anthropic",
            pipeline_run="run-cur",
        )
        prev_s = _write_dir(
            tmp_path / "ps",
            [_row("doc_A", core=False, severe=False)],
            judge_family="anthropic",
            pipeline_run="run-prev",
        )
        cur_g = _write_dir(
            tmp_path / "cg",
            [_row("doc_A", core=True, severe=False)],
            judge_family="google",
            pipeline_run="run-cur",
        )
        prev_g = _write_dir(
            tmp_path / "pg",
            [_row("doc_A", core=False, severe=False)],
            judge_family="google",
            pipeline_run="run-prev",
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--family",
                f"s={cur_s}|{prev_s}",
                "--family",
                f"g={cur_g}|{prev_g}",
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        assert json.loads(out.read_text(encoding="utf-8"))["verdict"] == "progress"

    def test_the_previous_cycle_counter_is_read_back(self, tmp_path):
        prev_cycle = tmp_path / "previous_cycle"
        prev_cycle.mkdir()
        (prev_cycle / "condition2.json").write_text(
            json.dumps({"counter_after": 4}), encoding="utf-8"
        )
        assert condition2.read_counter_before(prev_cycle) == 4
        assert condition2.read_counter_before(tmp_path / "absent") is None


class TestSeriesContract:
    """The new-series contract (verified on the artifacts before this
    increment): a series is the ARMS — ``pipeline_model``/``pipeline_family``
    in the consensus META, which come from the zero-shot record's provenance
    (#3138's single resolver) under the same-model doctrine. A judge change
    WITHIN a series is not a break (the doctrine says so; the panel ledger
    records no such comparison yet — the skip-a-break numbering below is
    hypothetical, not a published cycle pair); a pair that spans a series
    break reads no verdict — the official predecessor is the same-series
    cycle, skipping any newer cycles of other series — and a new series'
    first cycle is its own baseline, the counter restarting at 1 (the
    coordinator's c21 entry)."""

    def test_a_pair_spanning_a_series_break_is_refused(self, tmp_path):
        # c21's arms (Sonnet) paired with c20's (luna): the cross-series pair
        # must be refused, not read as a verdict or a silent hold — the
        # official pair for the next luna cycle was c22 -> c20, skipping c21.
        cur = _write_dir(
            tmp_path / "cur",
            [_row("doc_A", core=True, severe=False)],
            series_model="anthropic/claude-sonnet-5-5",
            series_family="anthropic",
        )
        prev = _write_dir(tmp_path / "prev", [_row("doc_A", core=False, severe=False)])
        with pytest.raises(SystemExit, match="series break"):
            condition2.main(["--family", f"s={cur}|{prev}", "--counter-before", "3"])

    def test_families_judging_different_runs_are_refused(self, tmp_path):
        # Two families whose CURRENT consensus META disagree on the arms are
        # not two readings of one cycle — they judged two different runs, and
        # a cross-family verdict over them would read one run against another.
        # Each family keeps its OWN previous directory (distinct pairs), so
        # the reused-directories guard stays out of the way.
        cur_s = _write_dir(tmp_path / "cur_s", [_row("doc_A", core=True, severe=False)])
        cur_g = _write_dir(
            tmp_path / "cur_g",
            [_row("doc_A", core=True, severe=False)],
            series_model="anthropic/claude-sonnet-5-5",
            series_family="anthropic",
        )
        prev_s = _write_dir(
            tmp_path / "prev_s", [_row("doc_A", core=False, severe=False)]
        )
        prev_g = _write_dir(
            tmp_path / "prev_g", [_row("doc_A", core=False, severe=False)]
        )
        with pytest.raises(SystemExit, match="different runs"):
            condition2.main(
                [
                    "--family",
                    f"s={cur_s}|{prev_s}",
                    "--family",
                    f"g={cur_g}|{prev_g}",
                ]
            )

    def test_a_meta_without_the_series_key_is_refused(self, tmp_path):
        # #3138's doctrine: the model is never guessed. A consensus META that
        # names no pipeline_model is a named exit, not a default.
        cur = _write_dir(
            tmp_path / "cur",
            [_row("doc_A", core=True, severe=False)],
            series_model=None,
        )
        prev = _write_dir(tmp_path / "prev", [_row("doc_A", core=False, severe=False)])
        with pytest.raises(SystemExit, match="cannot be guessed"):
            condition2.main(["--family", f"s={cur}|{prev}"])

    def test_a_new_series_is_its_own_baseline(self, tmp_path, capsys):
        # c21: "condition 2 restarts at 1 on this series (c21 is its own
        # baseline)". No comparison, whatever the previous series' counter
        # was — the baseline names the series and its heads so the NEXT
        # cycle's pair is verifiable against it.
        cur = _write_dir(
            tmp_path / "cur",
            [_row("doc_A", core=True, severe=False)],
            series_model="anthropic/claude-sonnet-5-5",
            series_family="anthropic",
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            ["--new-series", "--family", f"s={cur}", "--out", str(out)]
        )
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["verdict"] == "new_series"
        assert result["counter_before"] is None
        assert result["counter_after"] == 1
        assert result["series"] == {
            "model": "anthropic/claude-sonnet-5-5",
            "family": "anthropic",
        }
        assert result["heads"]["zeroshot_head"] == "z" * 40
        assert "new_series" in capsys.readouterr().out

    def test_a_new_series_baseline_takes_no_previous_half(self, tmp_path):
        cur = _write_dir(tmp_path / "cur", [_row("doc_A", core=True, severe=False)])
        prev = _write_dir(tmp_path / "prev", [_row("doc_A", core=False, severe=False)])
        with pytest.raises(SystemExit, match="no previous half"):
            condition2.main(["--new-series", "--family", f"s={cur}|{prev}"])

    def test_tag_mode_declares_a_new_series(self, tmp_path):
        root = tmp_path / "results"
        _write_dir(
            root / "judge_panel_3375_c21_l_cons6",
            [_row("doc_A", core=True, severe=False)],
            series_model="anthropic/claude-sonnet-5-5",
            series_family="anthropic",
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--new-series",
                "--tag",
                "c21",
                "--judge",
                "l",
                "--results-root",
                str(root),
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["verdict"] == "new_series"
        assert result["counter_after"] == 1
        assert result["families"]["l"]["current_dir"].endswith("c21_l_cons6")

    def test_the_report_carries_the_series(self, tmp_path):
        cur = _write_dir(tmp_path / "cur", [_row("doc_A", core=True, severe=False)])
        prev = _write_dir(tmp_path / "prev", [_row("doc_A", core=False, severe=False)])
        out = tmp_path / "condition2.json"
        rc = condition2.main(["--family", f"s={cur}|{prev}", "--out", str(out)])
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["series"] == {"model": "openai/gpt-5.6-luna", "family": "openai"}


class TestRecordedProvenance:
    """The #3639 review v3: two guarantees the CLI labels and the directory
    names cannot give.

    (1) JUDGE INDEPENDENCE is counted over the RECORDED ``judge_family`` of
    each consensus META — the same judge's results under two labels (or two
    consensus sizes of one family) are one reading, not two. Missing judge
    provenance is diagnostic only.

    (2) EXECUTION BINDING: the families of one cycle must be bound to the
    same measured execution — ``seed`` and ``run_head`` recorded and agreeing
    per role — and the inherited counter must come from the selected
    predecessor (the previous condition2.json's series). A reading that fails
    either guarantee keeps its per-family diagnosis and the counter holds."""

    def test_one_recorded_judge_family_under_two_labels_cannot_move_the_counter(
        self, tmp_path
    ):
        # Two distinct directory pairs, both recording judge_family "google"
        # (two models of the same family — the same shape as two consensus
        # sizes of one judge). Both read progress, but one judge's consensus
        # under two labels is one reading: the verdict is not official and
        # the counter HOLDS (3 -> 3).
        cur_s = _write_dir(
            tmp_path / "cs",
            [_row("doc_A", core=True, severe=False)],
            judge_family="google",
            judge_model="gemini-4-argon",
        )
        prev_s = _write_dir(
            tmp_path / "ps",
            [_row("doc_A", core=False, severe=False)],
            judge_family="google",
            judge_model="gemini-4-argon",
        )
        cur_g = _write_dir(
            tmp_path / "cg",
            [_row("doc_A", core=True, severe=False)],
            judge_family="google",
            judge_model="gemini-4-boron",
        )
        prev_g = _write_dir(
            tmp_path / "pg",
            [_row("doc_A", core=False, severe=False)],
            judge_family="google",
            judge_model="gemini-4-boron",
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--family",
                f"s={cur_s}|{prev_s}",
                "--family",
                f"g={cur_g}|{prev_g}",
                "--counter-before",
                "3",
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        # The per-family diagnosis is preserved (both families read progress)...
        assert result["families"]["s"]["direction"] == "progress"
        assert result["families"]["g"]["direction"] == "progress"
        # ...but the reading is not official: verdict not_measurable, hold.
        assert result["verdict"] == "not_measurable"
        assert result["counter_before"] == 3
        assert result["counter_after"] == 3
        assert result["provenance"]["official"] is False
        assert any(
            "one recorded judge family" in h for h in result["provenance"]["holds"]
        )

    def test_missing_judge_provenance_is_diagnostic_only(self, tmp_path):
        # No judge_family recorded (a historical META): independence cannot be
        # proven — the reading is diagnostic, no exit, the counter holds.
        cur_s = _write_dir(tmp_path / "cs", [_row("doc_A", core=True, severe=False)])
        prev_s = _write_dir(tmp_path / "ps", [_row("doc_A", core=False, severe=False)])
        cur_g = _write_dir(tmp_path / "cg", [_row("doc_A", core=True, severe=False)])
        prev_g = _write_dir(tmp_path / "pg", [_row("doc_A", core=False, severe=False)])
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--family",
                f"s={cur_s}|{prev_s}",
                "--family",
                f"g={cur_g}|{prev_g}",
                "--counter-before",
                "2",
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["verdict"] == "not_measurable"
        assert result["counter_after"] == 2
        assert any(
            "judge provenance missing" in h for h in result["provenance"]["holds"]
        )

    def test_the_same_model_with_different_executions_cannot_move_the_counter(
        self, tmp_path
    ):
        # Same arms, same seed, DIFFERENT run_head between the two current
        # consensus: they judged two executions of the same model — a verdict
        # reads ONE execution. Same-series, so no exit: the diagnosis is
        # preserved and the counter holds.
        cur_s = _write_dir(
            tmp_path / "cs",
            [_row("doc_A", core=True, severe=False)],
            run_head="a" * 40,
            judge_family="anthropic",
        )
        prev_s = _write_dir(
            tmp_path / "ps",
            [_row("doc_A", core=False, severe=False)],
            judge_family="anthropic",
        )
        cur_g = _write_dir(
            tmp_path / "cg",
            [_row("doc_A", core=True, severe=False)],
            run_head="b" * 40,
            judge_family="google",
        )
        prev_g = _write_dir(
            tmp_path / "pg",
            [_row("doc_A", core=False, severe=False)],
            judge_family="google",
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--family",
                f"s={cur_s}|{prev_s}",
                "--family",
                f"g={cur_g}|{prev_g}",
                "--counter-before",
                "3",
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["families"]["s"]["direction"] == "progress"
        assert result["families"]["g"]["direction"] == "progress"
        assert result["verdict"] == "not_measurable"
        assert result["counter_after"] == 3
        assert any("different executions" in h for h in result["provenance"]["holds"])

    def test_an_unrecorded_execution_binding_keeps_the_counter(self, tmp_path):
        # A current META without run_head (historical provenance) cannot bind
        # the role to one execution — diagnostic only, the counter holds.
        cur_s = _write_dir(
            tmp_path / "cs",
            [_row("doc_A", core=True, severe=False)],
            run_head=None,
            judge_family="anthropic",
        )
        prev_s = _write_dir(
            tmp_path / "ps",
            [_row("doc_A", core=False, severe=False)],
            judge_family="anthropic",
        )
        cur_g = _write_dir(
            tmp_path / "cg",
            [_row("doc_A", core=True, severe=False)],
            judge_family="google",
        )
        prev_g = _write_dir(
            tmp_path / "pg",
            [_row("doc_A", core=False, severe=False)],
            judge_family="google",
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--family",
                f"s={cur_s}|{prev_s}",
                "--family",
                f"g={cur_g}|{prev_g}",
                "--counter-before",
                "5",
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["verdict"] == "not_measurable"
        assert result["counter_after"] == 5
        assert any("unproven" in h for h in result["provenance"]["holds"])

    def test_the_inherited_counter_must_come_from_the_selected_predecessor(
        self, tmp_path
    ):
        # The previous cycle's condition2.json names the series it counted.
        # Inheriting a luna counter into a Sonnet pair wires the counter to
        # the WRONG predecessor — an input error, refused by name.
        cur = _write_dir(
            tmp_path / "cur",
            [_row("doc_A", core=True, severe=False)],
            series_model="anthropic/claude-sonnet-5-5",
            series_family="anthropic",
            judge_family="anthropic",
        )
        prev = _write_dir(
            tmp_path / "prev",
            [_row("doc_A", core=False, severe=False)],
            series_model="anthropic/claude-sonnet-5-5",
            series_family="anthropic",
            judge_family="anthropic",
        )
        prev_cycle = tmp_path / "prev_cycle"
        prev_cycle.mkdir()
        (prev_cycle / "condition2.json").write_text(
            json.dumps(
                {
                    "counter_after": 4,
                    "series": {"model": "openai/gpt-5.6-luna", "family": "openai"},
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(SystemExit, match="selected predecessor"):
            condition2.main(
                [
                    "--family",
                    f"s={cur}|{prev}",
                    "--previous-cycle-dir",
                    str(prev_cycle),
                ]
            )

    def test_a_counter_of_the_same_series_is_inherited(self, tmp_path):
        # The positive side: the counter file's series matches the pair's —
        # the counter is inherited and can move (here: reset on progress).
        cur = _write_dir(
            tmp_path / "cur",
            [_row("doc_A", core=True, severe=False)],
            judge_family="anthropic",
        )
        prev = _write_dir(
            tmp_path / "prev",
            [_row("doc_A", core=False, severe=False)],
            judge_family="anthropic",
        )
        prev_cycle = tmp_path / "prev_cycle"
        prev_cycle.mkdir()
        (prev_cycle / "condition2.json").write_text(
            json.dumps(
                {
                    "counter_after": 4,
                    "series": {"model": "openai/gpt-5.6-luna", "family": "openai"},
                }
            ),
            encoding="utf-8",
        )
        out = tmp_path / "condition2.json"
        rc = condition2.main(
            [
                "--family",
                f"s={cur}|{prev}",
                "--previous-cycle-dir",
                str(prev_cycle),
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        result = json.loads(out.read_text(encoding="utf-8"))
        assert result["counter_before"] == 4
        assert result["verdict"] == "not_measurable"  # one family: diagnostic
        assert result["counter_after"] == 4  # single-family readings hold

    def test_a_baseline_over_two_executions_is_refused(self, tmp_path):
        # --new-series declares ONE execution of the new arms: two consensus
        # recording different runs of the same model cannot both be it.
        cur_s = _write_dir(
            tmp_path / "cs",
            [_row("doc_A", core=True, severe=False)],
            run_head="a" * 40,
        )
        cur_g = _write_dir(
            tmp_path / "cg",
            [_row("doc_A", core=True, severe=False)],
            run_head="b" * 40,
        )
        with pytest.raises(SystemExit, match="different executions"):
            condition2.main(
                ["--new-series", "--family", f"s={cur_s}", "--family", f"g={cur_g}"]
            )


class TestPipelineRunBinding:
    """The #3639 review v4, measured on the stored META: c2-c20 ALL record
    the same (model, family, seed, run_head) — that binding proves neither
    "two cycles of the same series" nor "one cycle read against itself"
    (cons6 vs cons3 -> no_progress -> the counter ticks +1). The judge now
    records WHICH pipeline run it read (pipeline_run in META); the counter
    links on THAT field: one pipeline run per role AND the current run is
    not the previous one. A META without it (c2-c21) is unproven:
    diagnostic only, the counter holds."""

    def _two_official_families(self, tmp_path, *, cur_record, prev_record):
        dirs = {}
        for name, family in (("s", "anthropic"), ("g", "google")):
            cur = _write_dir(
                tmp_path / f"{name}_cur",
                [_row("doc_A", core=True, severe=False)],
                judge_family=family,
                pipeline_run=cur_record,
            )
            prev = _write_dir(
                tmp_path / f"{name}_prev",
                [_row("doc_A", core=False, severe=False)],
                judge_family=family,
                pipeline_run=prev_record,
            )
            dirs[name] = (cur, prev)
        return dirs

    def _run(self, dirs, tmp_path):
        out = tmp_path / "condition2.json"
        args = []
        for name, (cur, prev) in dirs.items():
            args += ["--family", f"{name}={cur}|{prev}"]
        args += ["--counter-before", "3", "--out", str(out)]
        rc = condition2.main(args)
        assert rc == 0
        return json.loads(out.read_text(encoding="utf-8"))

    def test_two_pipeline_runs_of_one_series_are_official(self, tmp_path):
        # The positive shape: one pipeline run per role, and the current run
        # differs from the previous one — the verdict is official, 3 -> 0.
        dirs = self._two_official_families(
            tmp_path, cur_record="run-cur", prev_record="run-prev"
        )
        result = self._run(dirs, tmp_path)
        assert result["verdict"] == "progress"
        assert result["counter_after"] == 0
        assert result["provenance"]["official"] is True
        assert result["provenance"]["holds"] == []

    def test_two_cycles_sharing_one_pipeline_run_hold_the_counter(self, tmp_path):
        # Same model, seed, run_head AND pipeline run in both roles: a cycle
        # read against itself (cons6 vs cons3) yields no_progress — the
        # counter would tick. The reading is not official.
        dirs = self._two_official_families(
            tmp_path, cur_record="run-a", prev_record="run-a"
        )
        result = self._run(dirs, tmp_path)
        assert result["verdict"] == "not_measurable"
        assert result["counter_after"] == 3
        assert any("same pipeline run" in h for h in result["provenance"]["holds"])

    def test_one_role_mixing_two_pipeline_runs_holds_the_counter(self, tmp_path):
        # The current role mixes two pipeline runs (one per family): the
        # verdict would read two runs against one — diagnostic only.
        dirs = self._two_official_families(
            tmp_path, cur_record="run-cur", prev_record="run-prev"
        )
        # Overwrite only the "g" family's current META: another run.
        _write_dir(
            dirs["g"][0],
            [_row("doc_A", core=True, severe=False)],
            judge_family="google",
            pipeline_run="run-other",
        )
        result = self._run(dirs, tmp_path)
        assert result["verdict"] == "not_measurable"
        assert result["counter_after"] == 3
        assert any(
            "different pipeline runs" in h for h in result["provenance"]["holds"]
        )

    def test_an_unrecorded_pipeline_run_is_diagnostic_only(self, tmp_path):
        # c2-c21's stored shape: everything recorded except pipeline_run —
        # the binding is unproven, the counter holds even though both
        # families progress and the judge families are distinct.
        dirs = self._two_official_families(tmp_path, cur_record=None, prev_record=None)
        result = self._run(dirs, tmp_path)
        assert result["families"]["s"]["direction"] == "progress"
        assert result["verdict"] == "not_measurable"
        assert result["counter_after"] == 3
        assert any(
            "pipeline run" in h and "unproven" in h
            for h in result["provenance"]["holds"]
        )


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
