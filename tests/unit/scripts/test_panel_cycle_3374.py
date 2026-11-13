"""#3374 — the panel-cycle instruments (``scripts/panel/``), on synthetic states.

Every instrument here reads a recorded cycle: the pipeline's state dumps and
the judge's rows. These tests build both by hand, so they need no corpus, no
key and no network — and they replay the selection through the SAME
production seams the instruments use (``selection``, the reading's budget,
the priority spans), never through a double of them: a renamed or re-shaped
seam reddens here, not at the next paid cycle.

What is witnessed:

- the tracer gives each judge item the first stage it fails, one witness per
  stage, and reads the population the state was recorded with;
- the fidelity control tells the four kinds apart, and the recorded
  population SIZE decides between two populations that select the same units;
- a state with no extracted argument has no population, anchors included;
- the random controls are deterministic and bounded;
- the replay's totals never borrow a denominator from a document a variant
  does not have;
- a bar on the first reading needs three draws;
- the cycle runner's stops: nothing paid on an unjudgeable cycle, no judge on
  a failed batch, on a moved HEAD or on a stale harvest, no pass paid twice,
  no consensus of fewer passes than planned;
- the credit reader never prints the key, and an unread credit is not zero;
- the classifier's dry-run makes no call;
- no instrument writes corpus text to a tracked path, and none carries a
  document-id-shaped token.
"""

from __future__ import annotations

import inspect
import dataclasses
import io
import json
import os
import random
import re
import sys
import time
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.panel import _common as c  # noqa: E402
from scripts.panel import classify_items  # noqa: E402
from scripts.panel import first_reading_draws  # noqa: E402
from scripts.panel import openrouter_credit  # noqa: E402
from scripts.panel import replay_selection  # noqa: E402
from scripts.panel import run_cycle  # noqa: E402
from scripts.panel import trace_items  # noqa: E402

# ---------------------------------------------------------------------------
# A synthetic recorded state
# ---------------------------------------------------------------------------

WORDS = ("amber", "birch", "cedar", "dune", "ember", "fjord", "glade", "heath")
SENTENCES = 16
UNIT_SENTENCES = tuple(range(14))  # sentences 14 and 15 carry no extracted unit
NAMED_WITHOUT_UNIT = 14  # the first reading names it; the extraction cut none
NEVER_NAMED = 15


def sentence(i: int) -> str:
    return " ".join(f"{word}{i:02d}" for word in WORDS) + "."


def layout(n: int = SENTENCES) -> tuple[str, List[int]]:
    starts, position = [], 0
    for i in range(n):
        starts.append(position)
        position += len(sentence(i)) + 1
    return " ".join(sentence(i) for i in range(n)), starts


def make_state(
    moves_at: Sequence[int] = (NAMED_WITHOUT_UNIT,),
    units_at: Sequence[int] = UNIT_SENTENCES,
    record: Optional[str] = "production",
) -> Dict[str, Any]:
    """A state as the pipeline dumps it, with the selection the production
    selector makes on it recorded as production records it."""
    raw, starts = layout()
    state: Dict[str, Any] = {
        "raw_text": raw,
        "identified_arguments": {
            f"arg_{i + 1}": f"the claim the text makes in its sentence {i:02d}"
            for i in units_at
        },
        "argument_provenance": {
            f"arg_{i + 1}": {
                "producer": "llm_extract",
                "offset": starts[i],
                "source_quote": sentence(i),
            }
            for i in units_at
        },
        "defining_moves": {
            "moves": [{"offset": starts[i], "quote": sentence(i)} for i in moves_at]
        },
        "identified_fallacies": {},
        "coverage_review": {"items": []},
        "act1_framing": "",
        "act2_narrative": "",
        "act3_conclusion": "",
    }
    if record is not None:
        ns = SimpleNamespace(**state)
        population = c.population_of(ns, anchored=(record == "production"))
        selection = c.select(ns, population)
        state["analysis_coverage"] = {
            "fallacy_per_argument": {
                "k": selection.k,
                "N": selection.n_total,
                "unit_ids": [unit.unit_id for unit in selection.selected],
            }
        }
    return state


def sentence_of(unit_id: str) -> int:
    return int(unit_id.split("_")[1]) - 1


def examined_and_not(state: Dict[str, Any]) -> tuple[int, int]:
    """The sentence of one examined extracted unit, and of one left out."""
    selected = set(state["analysis_coverage"]["fallacy_per_argument"]["unit_ids"])
    extracted = set(state["identified_arguments"])
    examined = sorted(extracted & selected)
    left_out = sorted(extracted - selected)
    assert examined and left_out, "the fixture must ration: budget below population"
    return sentence_of(examined[0]), sentence_of(left_out[0])


def add_finding(state: Dict[str, Any], sentence_index: int) -> None:
    state["identified_fallacies"]["fallacy_1"] = {
        "type": "ad_hominem",
        "target_argument_id": f"arg_{sentence_index + 1}",
        "justification": "the speaker is attacked, not the claim",
    }


def m1(quote: str, central: bool = True, support: int = 6) -> Dict[str, Any]:
    return {
        "code": "M1",
        "support": support,
        "on_central_thesis": central,
        "note": "an observation no line of the analysis carries",
        "document_quote": quote,
    }


def write_cycle(
    tmp_path: Path, states: Dict[str, Dict[str, Any]], rows: Dict[str, Dict[str, Any]]
) -> tuple[Path, Path]:
    states_dir, consensus = tmp_path / "states", tmp_path / "family_cons"
    states_dir.mkdir(parents=True)
    consensus.mkdir(parents=True)
    for doc, state in states.items():
        (states_dir / f"state_full_{doc}.json").write_text(
            json.dumps({"state": state}), encoding="utf-8"
        )
    for doc, row in rows.items():
        (consensus / f"{doc}.json").write_text(json.dumps(row), encoding="utf-8")
    (consensus / "META.json").write_text("{}", encoding="utf-8")
    return states_dir, consensus


# ---------------------------------------------------------------------------
# The locator
# ---------------------------------------------------------------------------


class TestLocate:
    def test_a_quote_is_found_through_case_and_punctuation(self):
        raw, starts = layout()
        norm, idx = c.normalized(raw)
        span = c.locate(norm, idx, sentence(3).upper().replace(" ", " ,  "))
        assert span is not None
        assert raw[span[0] : span[1]].rstrip(".") == sentence(3).rstrip(".")
        assert span[0] == starts[3]

    def test_a_quote_trimmed_at_both_ends_is_found_by_its_middle(self):
        raw, _ = layout()
        norm, idx = c.normalized(raw)
        trimmed = "not here " + sentence(5) + " nor this"
        assert norm.find(c.normalized(trimmed)[0].strip()) < 0
        span = c.locate(norm, idx, trimmed)
        assert span is not None
        assert raw[span[0] : span[1]] == sentence(5).rstrip(".")

    def test_a_quote_the_document_does_not_carry_is_not_located(self):
        norm, idx = c.normalized(layout()[0])
        assert c.locate(norm, idx, "words the synthetic document never wrote") is None
        assert c.locate(norm, idx, "") is None
        assert c.locate(norm, idx, None) is None


# ---------------------------------------------------------------------------
# The fidelity control
# ---------------------------------------------------------------------------


class TestFidelity:
    def test_the_fixture_rations_and_records_the_population_size(self):
        state = make_state()
        record = state["analysis_coverage"]["fallacy_per_argument"]
        # 14 extracted units plus the one the named move supplies (#3518).
        assert record["N"] == len(UNIT_SENTENCES) + 1
        assert record["k"] < record["N"]
        assert len(record["unit_ids"]) == record["k"]

    def test_a_state_recorded_by_todays_code_is_production(self):
        assert c.resolve_population(make_state())[1] == c.POPULATION_PRODUCTION

    def test_a_state_recorded_before_the_anchors_is_merged_only(self):
        population, kind = c.resolve_population(make_state(record="merged_only"))
        assert kind == c.POPULATION_MERGED_ONLY
        assert len(population) == len(UNIT_SENTENCES)

    def test_a_record_no_population_reproduces_is_unfaithful(self):
        state = make_state()
        record = state["analysis_coverage"]["fallacy_per_argument"]
        left_out = sorted(set(state["identified_arguments"]) - set(record["unit_ids"]))
        record["unit_ids"] = record["unit_ids"][1:] + left_out[:1]
        assert c.resolve_population(state)[1] == c.POPULATION_UNFAITHFUL

    def test_a_state_without_a_record_says_so(self):
        assert (
            c.resolve_population(make_state(record=None))[1] == c.POPULATION_NO_RECORD
        )

    def test_the_size_decides_between_two_populations_selecting_the_same_units(
        self, monkeypatch
    ):
        """An anchored unit the budget left out changes no selected id: only
        the recorded size tells which population the run selected from."""
        state = make_state(record=None)
        ns = SimpleNamespace(**state)
        merged = c.population_of(ns, anchored=False)
        production = c.population_of(ns, anchored=True)
        assert len(production) == len(merged) + 1
        chosen = [unit.unit_id for unit in merged[:5]]
        monkeypatch.setattr(
            c,
            "select",
            lambda _ns, population, k=None: SimpleNamespace(
                selected=[unit for unit in population if unit.unit_id in chosen]
            ),
        )
        record: Dict[str, Any] = {"unit_ids": chosen, "N": len(merged)}
        state["analysis_coverage"] = {"fallacy_per_argument": record}
        assert c.resolve_population(state)[1] == c.POPULATION_MERGED_ONLY
        record["N"] = len(production)
        assert c.resolve_population(state)[1] == c.POPULATION_PRODUCTION

    def test_units_added_after_the_selection_are_not_the_selectors(self):
        state = make_state()
        record = state["analysis_coverage"]["fallacy_per_argument"]
        record["unit_ids"] = record["unit_ids"] + ["late_unit"]
        record["added_by"] = {"late_unit": "coverage_review"}
        assert c.resolve_population(state)[1] == c.POPULATION_PRODUCTION

    def test_no_extracted_argument_means_no_population_anchors_included(self):
        """Production builds the state population only on a non-empty
        ``identified_arguments``: the named moves supply nothing there."""
        state = make_state(units_at=(), record=None)
        assert state["defining_moves"]["moves"], "the reading did name a passage"
        assert c.population_of(SimpleNamespace(**state)) == []
        index = c.build_doc_index("doc_a", state)
        row = trace_items.trace_item(index, m1(sentence(NAMED_WITHOUT_UNIT)))
        assert row["stage"] == trace_items.STAGE_NAMED_NO_UNIT


# ---------------------------------------------------------------------------
# The tracer: one witness per stage
# ---------------------------------------------------------------------------


class TestTracerStages:
    def stage(self, state: Dict[str, Any], item: Dict[str, Any]) -> str:
        return trace_items.trace_item(c.build_doc_index("doc_a", state), item)["stage"]

    def test_unlocated(self):
        item = m1("a passage the document never wrote at all")
        assert self.stage(make_state(), item) == trace_items.STAGE_UNLOCATED

    def test_not_named_no_unit(self):
        assert (
            self.stage(make_state(), m1(sentence(NEVER_NAMED)))
            == trace_items.STAGE_NOT_NAMED_NO_UNIT
        )

    def test_named_no_unit_on_a_state_recorded_before_the_anchors(self):
        state = make_state(record="merged_only")
        assert (
            self.stage(state, m1(sentence(NAMED_WITHOUT_UNIT)))
            == trace_items.STAGE_NAMED_NO_UNIT
        )

    def test_the_same_passage_has_a_unit_once_the_anchors_supply_one(self):
        state = make_state()
        row = trace_items.trace_item(
            c.build_doc_index("doc_a", state), m1(sentence(NAMED_WITHOUT_UNIT))
        )
        assert row["named"] and row["unit"]
        assert row["stage"] != trace_items.STAGE_NAMED_NO_UNIT

    def test_unit_not_examined(self):
        state = make_state()
        _, left_out = examined_and_not(state)
        assert (
            self.stage(state, m1(sentence(left_out)))
            == trace_items.STAGE_UNIT_NOT_EXAMINED
        )

    def test_examined_no_finding(self):
        state = make_state()
        examined, _ = examined_and_not(state)
        assert (
            self.stage(state, m1(sentence(examined)))
            == trace_items.STAGE_EXAMINED_NO_FINDING
        )

    def test_found_not_rendered(self):
        state = make_state()
        examined, _ = examined_and_not(state)
        add_finding(state, examined)
        assert (
            self.stage(state, m1(sentence(examined)))
            == trace_items.STAGE_FOUND_NOT_RENDERED
        )

    def test_rendered_judge_disagrees(self):
        state = make_state()
        examined, _ = examined_and_not(state)
        add_finding(state, examined)
        state["act2_narrative"] = f"The text says: {sentence(examined)} It matters."
        assert (
            self.stage(state, m1(sentence(examined)))
            == trace_items.STAGE_RENDERED_JUDGE_DISAGREES
        )

    def test_a_passage_the_coverage_review_reached_counts_as_found(self):
        state = make_state()
        _, starts = layout()
        state["coverage_review"]["items"] = [
            {"offset": starts[NEVER_NAMED], "quote": sentence(NEVER_NAMED)}
        ]
        assert (
            self.stage(state, m1(sentence(NEVER_NAMED)))
            == trace_items.STAGE_FOUND_NOT_RENDERED
        )

    def test_a_finding_on_a_unit_left_out_is_not_a_finding_on_the_passage(self):
        state = make_state()
        _, left_out = examined_and_not(state)
        add_finding(state, left_out)
        assert (
            self.stage(state, m1(sentence(left_out)))
            == trace_items.STAGE_UNIT_NOT_EXAMINED
        )

    def test_an_m2_names_the_acts_that_carry_the_claim(self):
        state = make_state()
        claim = "the analysis asserts something the document itself contradicts plainly"
        state["act2_narrative"] = f"First. {claim}. Last."
        state["act3_conclusion"] = f"Again: {claim}."
        item = {"code": "M2", "pipeline_quote": claim}
        assert self.stage(state, item) == "m2_in_act2+act3"
        item = {"code": "M2", "pipeline_quote": "a claim that no act of the render has"}
        assert self.stage(state, item) == "m2_in_none"

    def test_every_m1_stage_is_declared(self):
        produced = {
            trace_items.m1_stage(
                {
                    "located": located,
                    "named": named,
                    "unit": unit,
                    "examined": examined,
                    "finding": finding,
                    "reviewed": reviewed,
                    "rendered": rendered,
                }
            )
            for located in (False, True)
            for named in (False, True)
            for unit in (False, True)
            for examined in (False, True)
            for finding in (False, True)
            for reviewed in (False, True)
            for rendered in ([], ["act2_narrative"])
        }
        assert produced == set(trace_items.STAGES)


class TestTracerRun:
    def test_the_run_traces_kept_and_minority_items_and_writes_the_jsonl(
        self, tmp_path, capsys
    ):
        state = make_state()
        examined, left_out = examined_and_not(state)
        rows = {
            "doc_a": {
                "kept": [m1(sentence(left_out)), {"code": "S1", "note": "not traced"}],
                "minority": [m1(sentence(examined), central=False, support=1)],
            }
        }
        states_dir, consensus = write_cycle(tmp_path, {"doc_a": state}, rows)
        out = tmp_path / "out" / "trace.jsonl"
        rc = trace_items.main(
            [
                "--states-dir",
                str(states_dir),
                "--consensus-dir",
                str(consensus),
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        traced = [json.loads(line) for line in out.read_text("utf-8").splitlines()]
        assert [(r["bucket"], r["stage"]) for r in traced] == [
            ("kept", trace_items.STAGE_UNIT_NOT_EXAMINED),
            ("minority", trace_items.STAGE_EXAMINED_NO_FINDING),
        ]
        assert {r["family"] for r in traced} == {"family_cons"}
        printed = capsys.readouterr().out
        assert "items traced: 2 over 1 document(s)" in printed
        assert "UNFAITHFUL" not in printed

    def test_an_unfaithful_document_is_named(self, tmp_path, capsys):
        state = make_state()
        record = state["analysis_coverage"]["fallacy_per_argument"]
        left_out = sorted(set(state["identified_arguments"]) - set(record["unit_ids"]))
        record["unit_ids"] = record["unit_ids"][1:] + left_out[:1]
        states_dir, consensus = write_cycle(
            tmp_path, {"doc_a": state}, {"doc_a": {"kept": [m1(sentence(2))]}}
        )
        trace_items.main(
            [
                "--states-dir",
                str(states_dir),
                "--consensus-dir",
                str(consensus),
                "--out",
                str(tmp_path / "trace.jsonl"),
            ]
        )
        assert (
            "UNFAITHFUL replay on 1 document(s): ['doc_a']" in capsys.readouterr().out
        )


# ---------------------------------------------------------------------------
# The random controls
# ---------------------------------------------------------------------------


class TestRandomControls:
    PASSAGES = [(0, 50), (100, 180), (400, 430)]

    def test_a_predicate_that_always_hits_scores_every_passage(self):
        rng = random.Random(1)
        assert (
            c.random_passage_expectation(self.PASSAGES, 1000, lambda _: True, 25, rng)
            == 3
        )
        assert (
            c.random_passage_expectation(self.PASSAGES, 1000, lambda _: False, 25, rng)
            == 0
        )

    def test_the_expectation_is_reproducible_and_strictly_between_the_ends(self):
        def first_half(span):
            return span[0] < 500

        a, b = (
            c.random_passage_expectation(
                self.PASSAGES, 1000, first_half, 400, random.Random(c.DEFAULT_SEED)
            )
            for _ in range(2)
        )
        assert a == b
        assert 0 < a < len(self.PASSAGES)

    def test_redrawn_passages_keep_their_length_and_stay_in_the_text(self):
        seen: List[tuple] = []
        c.random_passage_expectation(
            self.PASSAGES, 1000, lambda s: seen.append(s) or False, 50, random.Random(2)
        )
        assert {end - start for start, end in seen} == {50, 80, 30}
        assert all(0 <= start and end <= 1000 for start, end in seen)

    def test_anchors_that_cover_the_text_overlap_every_passage(self):
        rng = random.Random(3)
        assert (
            c.random_anchor_expectation([(0, 1000)], self.PASSAGES, 1000, 10, rng) == 3
        )

    def test_no_anchor_or_no_passage_is_zero(self):
        rng = random.Random(4)
        assert c.random_anchor_expectation([], self.PASSAGES, 1000, 10, rng) == 0
        assert c.random_anchor_expectation([(0, 10)], [], 1000, 10, rng) == 0
        assert c.random_passage_expectation([], 1000, lambda _: True, 10, rng) == 0


# ---------------------------------------------------------------------------
# The selection replay
# ---------------------------------------------------------------------------


class TestReplay:
    def test_todays_selection_reproduces_the_recorded_one_on_a_faithful_state(self):
        state = make_state()
        examined, left_out = examined_and_not(state)
        line = replay_selection.replay_document(
            "doc_a", state, [sentence(examined), sentence(left_out)], draws=20
        )
        assert line["fidelity"] == c.POPULATION_PRODUCTION
        assert line["located"] == 2
        assert line["variants"]["recorded"]["examined"] == 1
        assert line["variants"]["today"]["examined"] == 1
        record = state["analysis_coverage"]["fallacy_per_argument"]
        assert line["variants"]["today"]["selected"] == record["k"]
        assert line["variants"]["today"]["population"] == record["N"]

    def test_a_budget_as_large_as_the_population_examines_every_unit(self):
        state = make_state()
        examined, left_out = examined_and_not(state)
        size = state["analysis_coverage"]["fallacy_per_argument"]["N"]
        line = replay_selection.replay_document(
            "doc_a",
            state,
            [sentence(examined), sentence(left_out)],
            budgets=[size],
            draws=20,
        )
        variant = line["variants"][f"k={size}"]
        assert variant["selected"] == size
        assert variant["examined"] == 2

    def test_a_draw_that_names_a_passage_supplies_the_unit_to_examine(self):
        """The free measure of a reading change: replace the moves, replay."""
        state = make_state(moves_at=())
        _, starts = layout()
        quote = sentence(NEVER_NAMED)
        draw = [{"offset": starts[NEVER_NAMED], "quote": quote}]
        line = replay_selection.replay_document(
            "doc_a", state, [quote], moves_by_dir={"d1": draw}, draws=20
        )
        assert line["variants"]["today"]["examined"] == 0
        assert line["variants"]["d1"]["examined"] == 1
        assert "union" not in line["variants"], "a union needs two draws"

    def test_the_union_of_two_draws_carries_both_passages(self):
        state = make_state(moves_at=())
        _, starts = layout()
        quotes = [sentence(NAMED_WITHOUT_UNIT), sentence(NEVER_NAMED)]
        draws = {
            f"d{n}": [{"offset": starts[i], "quote": sentence(i)}]
            for n, i in enumerate((NAMED_WITHOUT_UNIT, NEVER_NAMED), start=1)
        }
        line = replay_selection.replay_document(
            "doc_a", state, quotes, moves_by_dir=draws, draws=20
        )
        assert line["variants"]["d1"]["examined"] == 1
        assert line["variants"]["d2"]["examined"] == 1
        assert line["variants"]["union"]["examined"] == 2

    def test_union_counts_a_passage_once_and_keeps_what_it_cannot_compare(self):
        first = [{"offset": 0, "quote": "x" * 40}, {"quote": "unpositioned"}]
        second = [
            {"offset": 10, "quote": "y" * 40},  # overlaps the first: same passage
            {"offset": 200, "quote": "z" * 10},
            {"quote": "unpositioned"},
        ]
        union = replay_selection.union_moves([first, second])
        assert [move.get("offset") for move in union] == [0, None, 200, None]

    def test_totals_never_borrow_a_denominator_from_a_document_without_the_variant(
        self,
    ):
        lines = [
            {
                "located": 7,
                "variants": {
                    "today": {"examined": 3, "random": 2.0, "selected": 10},
                    "d1": {"examined": 5, "random": 2.5, "selected": 12},
                },
            },
            {
                "located": 4,
                "variants": {"today": {"examined": 1, "random": 1.0, "selected": 10}},
            },
        ]
        totals = replay_selection.totals(lines)
        assert (totals["today"]["examined"], totals["today"]["located"]) == (4, 11)
        assert (totals["d1"]["examined"], totals["d1"]["located"]) == (5, 7)
        assert totals["d1"]["docs"] == 1

    def test_the_passages_of_a_trace_are_the_m1_rows_at_one_stage(self, tmp_path):
        trace = tmp_path / "trace.jsonl"
        rows = [
            {
                "doc": "doc_a",
                "code": "M1",
                "stage": "unit_not_examined",
                "document_quote": "q1",
            },
            {
                "doc": "doc_a",
                "code": "M1",
                "stage": "examined_no_finding",
                "document_quote": "q2",
            },
            {
                "doc": "doc_b",
                "code": "M2",
                "stage": "unit_not_examined",
                "document_quote": "q3",
            },
            {
                "doc": "doc_b",
                "code": "M1",
                "stage": "unit_not_examined",
                "document_quote": " ",
            },
        ]
        trace.write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
        assert replay_selection.passages_from_trace(trace, "unit_not_examined") == {
            "doc_a": ["q1"]
        }

    def test_the_run_exits_2_on_an_unfaithful_replay(self, tmp_path, capsys):
        faithful = make_state()
        _, left_out = examined_and_not(faithful)
        drifted = make_state()
        record = drifted["analysis_coverage"]["fallacy_per_argument"]
        spare = sorted(set(drifted["identified_arguments"]) - set(record["unit_ids"]))
        record["unit_ids"] = record["unit_ids"][1:] + spare[:1]
        row = {"kept": [m1(sentence(left_out))]}

        states_dir, consensus = write_cycle(
            tmp_path / "ok", {"doc_a": faithful}, {"doc_a": row}
        )
        argv = ["--states-dir", str(states_dir), "--passages-from", str(consensus)]
        assert replay_selection.main(argv + ["--draws", "10"]) == 0
        assert "TOTAL today: 0/1" in capsys.readouterr().out

        states_dir, consensus = write_cycle(
            tmp_path / "ko", {"doc_a": drifted}, {"doc_a": row}
        )
        argv = ["--states-dir", str(states_dir), "--passages-from", str(consensus)]
        assert replay_selection.main(argv + ["--draws", "10"]) == 2
        assert "UNFAITHFUL replay on 1 document(s)" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The first-reading draws
# ---------------------------------------------------------------------------


class TestDraws:
    def test_no_bar_is_read_under_three_draws(self):
        assert first_reading_draws.summarise_draws([]) == {"draws": 0, "enough": False}
        assert first_reading_draws.summarise_draws([26, 11])["enough"] is False
        summary = first_reading_draws.summarise_draws([26, 11, 20])
        assert summary == {
            "draws": 3,
            "min": 11,
            "mean": 19.0,
            "max": 26,
            "spread": 15,
            "enough": True,
        }

    def test_a_passage_is_named_by_a_positioned_or_a_locatable_move(self):
        state = make_state()
        index = c.build_doc_index("doc_a", state)
        _, starts = layout()
        moves = [
            {"offset": starts[2], "quote": sentence(2)},
            {"quote": sentence(4)},  # unpositioned: located by its quote
            {"quote": "a quote the document does not carry"},
        ]
        result = first_reading_draws.count_named(
            index, moves, [sentence(2), sentence(4), sentence(6), "not in the text"]
        )
        assert result == {
            "passages": 4,
            "located": 3,
            "named": 2,
            "moves": 3,
            "positioned": 2,
        }

    def test_the_random_anchor_control_rides_with_the_count(self):
        state = make_state()
        index = c.build_doc_index("doc_a", state)
        _, starts = layout()
        moves = [{"offset": starts[2], "quote": sentence(2)}]
        result = first_reading_draws.count_named(
            index, moves, [sentence(2), sentence(9)], 200, random.Random(5)
        )
        assert result["named"] == 1
        assert 0 < result["random"] < 2

    def test_calibrate_reads_the_recorded_moves_without_a_call(self, tmp_path, capsys):
        state = make_state()
        row = {"kept": [m1(sentence(NAMED_WITHOUT_UNIT)), m1(sentence(NEVER_NAMED))]}
        states_dir, consensus = write_cycle(tmp_path, {"doc_a": state}, {"doc_a": row})
        rc = first_reading_draws.main(
            [
                "calibrate",
                "--states-dir",
                str(states_dir),
                "--passages-from",
                str(consensus),
                "--control-draws",
                "50",
            ]
        )
        assert rc == 0
        total = json.loads(capsys.readouterr().out.split("TOTAL ", 1)[1])
        assert (total["located"], total["named"]) == (2, 1)

    def test_dry_states_the_prompt_bounds_without_a_call(self, tmp_path, capsys):
        states_dir, _ = write_cycle(tmp_path, {"doc_a": make_state()}, {})
        assert first_reading_draws.main(["dry", "--states-dir", str(states_dir)]) == 0
        line = json.loads(capsys.readouterr().out.split("doc_a ", 1)[1])
        assert line["chars"] == len(layout()[0])
        assert line["prompt_chars"] > line["chars"]

    def test_paid_needs_a_gitignored_out_dir(self, tmp_path):
        states_dir, _ = write_cycle(tmp_path, {"doc_a": make_state()}, {})
        with pytest.raises(SystemExit):
            first_reading_draws.main(["paid", "--states-dir", str(states_dir)])

    def test_the_production_seams_the_paid_mode_patches_still_exist(self):
        """The paid mode wraps these by name; a rename must redden here, not
        at the next paid witness."""
        import argumentation_analysis.orchestration.invoke_callables as ic
        from argumentation_analysis.agents.core.reading import build_first_reading

        assert callable(ic._guarded_chat_completion)
        assert hasattr(ic, "_FIRST_READING_MAX_TOKENS")
        parameters = inspect.signature(ic._build_persona_callable).parameters
        assert "max_completion_tokens" in parameters
        assert len(inspect.signature(build_first_reading).parameters) >= 2


# ---------------------------------------------------------------------------
# The cycle runner
# ---------------------------------------------------------------------------

PANEL = ("doc_a", "doc_b")
SYNC = run_cycle.Judge("g", "judge-sync-model", env={"ROUTE_MODEL": "x/y"})
BATCH = run_cycle.Judge("s", "judge-batch-model", batch=True)
HEAD = {"head": "a" * 40, "tree": "b" * 40, "dirty": False}


def judged_row(doc: str, **changes: Any) -> Dict[str, Any]:
    row = {"opaque_id": doc, "status_code": 200, "state": "EQUAL", "kept": []}
    row.update(changes)
    return row


def write_pass(
    out_dir: Path, rows: Iterable[Dict[str, Any]], meta: bool = True
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        (out_dir / f"{row['opaque_id']}.json").write_text(json.dumps(row), "utf-8")
    if meta:
        (out_dir / "META.json").write_text("{}", encoding="utf-8")


class World:
    """A cycle on disk and a runner that plays every command without a call."""

    def __init__(self, tmp_path: Path, judges=(SYNC, BATCH), passes=3, **config: Any):
        self.tmp = tmp_path
        self.panel_file = tmp_path / "panel.txt"
        self.panel_file.write_text("\n".join(PANEL) + "\n", encoding="utf-8")
        self.zeroshot = tmp_path / "zeroshot"
        self.zeroshot.mkdir()
        for doc in PANEL:
            (self.zeroshot / f"{doc}.json").write_text(
                json.dumps({"answer": "a zero-shot reading"}), encoding="utf-8"
            )
        self.cfg = run_cycle.Config(
            tag="t1",
            panel_file=self.panel_file,
            zeroshot_dir=self.zeroshot,
            judges=list(judges),
            passes=passes,
            results_root=tmp_path / "results",
            kb_root=tmp_path / "kb",
            **config,
        )
        self.calls: List[str] = []
        self.steps: Dict[str, run_cycle.Step] = {}
        self.rc: Dict[str, int] = {}
        self.pipeline_writes: Sequence[str] = PANEL
        self.heads = [HEAD]
        self.credits = [
            {"usage": 10.0, "limit": 50.0, "limit_remaining": 40.0},
            {"usage": 21.0, "limit": 50.0, "limit_remaining": 29.0},
            {"usage": 22.5, "limit": 50.0, "limit_remaining": 27.5},
        ]

    def kb_files(self, doc: str) -> List[Path]:
        return [
            self.cfg.kb_root / "state_dumps" / f"state_full_{doc}.json",
            self.cfg.kb_root / "signatures" / f"signature_{doc}.json",
        ]

    def write_kb(self, doc: str, age_seconds: float = 0.0) -> None:
        for path in self.kb_files(doc):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
            if age_seconds:
                old = time.time() - age_seconds
                os.utime(path, (old, old))

    def runner(self, step: run_cycle.Step) -> int:
        self.calls.append(step.name)
        self.steps[step.name] = step
        rc = self.rc.get(step.name, 0)
        step.log.parent.mkdir(parents=True, exist_ok=True)
        if step.name == "pipeline":
            verdict = (
                "PASS (0 documents failed)"
                if rc == 0
                else "FAIL (1 document(s) failed)"
            )
            step.log.write_text(f"noise\nVerdict: {verdict}\n", encoding="utf-8")
            for doc in self.pipeline_writes:
                self.write_kb(doc)
        elif re.fullmatch(r"[a-z]\.p\d+", step.name) and rc == 0:
            out = Path(step.argv[step.argv.index("--out-dir") + 1])
            write_pass(out, [judged_row(doc) for doc in PANEL])
        return rc

    def head(self) -> Dict[str, Any]:
        return self.heads.pop(0) if len(self.heads) > 1 else self.heads[0]

    def credit(self) -> Dict[str, Any]:
        return self.credits.pop(0) if len(self.credits) > 1 else self.credits[0]

    def run(self) -> Dict[str, Any]:
        return run_cycle.run_cycle(
            self.cfg, runner=self.runner, credit=self.credit, head=self.head
        )

    def paid(self) -> List[str]:
        return [name for name in self.calls if self.steps[name].paid]

    def events(self) -> List[str]:
        status = self.cfg.cycle_dir / "status.jsonl"
        return [
            json.loads(line)["event"] for line in status.read_text("utf-8").splitlines()
        ]


class TestJudgeSpec:
    def test_a_spec_carries_the_route_and_its_environment(self):
        judge = run_cycle.parse_judge("g=some-model,env.ROUTE_MODEL=vendor/some-model")
        assert (judge.name, judge.model, judge.batch) == ("g", "some-model", False)
        assert dict(judge.env) == {"ROUTE_MODEL": "vendor/some-model"}
        assert run_cycle.parse_judge("s=other-model,batch").batch is True

    @pytest.mark.parametrize(
        "spec", ["model-alone", "=model", "g=", "g=m,turbo", "a b=m"]
    )
    def test_a_malformed_spec_is_refused(self, spec):
        with pytest.raises(ValueError):
            run_cycle.parse_judge(spec)

    def test_a_config_that_cannot_name_its_directories_is_refused(self, tmp_path):
        for changes in (
            {"tag": "../escape"},
            {"judges": [SYNC, SYNC]},
            {"passes": 3, "partial_consensus": [3]},
            {"passes": 3, "partial_consensus": [1]},
            {"stage": "everything"},
        ):
            with pytest.raises(ValueError):
                run_cycle.Config(
                    **{
                        "tag": "t1",
                        "panel_file": tmp_path / "p",
                        "zeroshot_dir": tmp_path,
                        **changes,
                    }
                )


class TestPlan:
    def test_the_plan_lists_every_command_in_the_order_they_can_run(self, tmp_path):
        world = World(tmp_path, partial_consensus=[2])
        names = [step.name for step in run_cycle.plan(world.cfg)]
        assert names == [
            "pipeline",
            "g.dry",
            "g.p1",
            "g.p2",
            "g.p3",
            "g.cons2",
            "g.cons3",
            "s.dry",
            "s.p1",
            "s.p2",
            "s.p3",
            "s.cons2",
            "s.cons3",
            "trace",
        ]
        paid = [step.name for step in run_cycle.plan(world.cfg) if step.paid]
        assert paid == ["pipeline", "g.p1", "g.p2", "g.p3", "s.p1", "s.p2", "s.p3"]

    def test_a_batch_family_asks_for_the_batch_route_and_a_sync_one_does_not(
        self, tmp_path
    ):
        world = World(tmp_path)
        assert "--anthropic-batch" in run_cycle.pass_step(world.cfg, BATCH, 1).argv
        assert "--anthropic-batch" not in run_cycle.pass_step(world.cfg, SYNC, 1).argv
        assert run_cycle.pass_step(world.cfg, SYNC, 1).env == {"ROUTE_MODEL": "x/y"}
        assert run_cycle.dry_run_step(world.cfg, SYNC).argv[-1] == "--dry-run"

    def test_plan_mode_runs_nothing_and_creates_nothing(self, tmp_path, capsys):
        world = World(tmp_path)
        tag = "plan_only_witness"
        rc = run_cycle.main(
            [
                "--tag",
                tag,
                "--panel-file",
                str(world.panel_file),
                "--zeroshot-dir",
                str(world.zeroshot),
                "--judge",
                "g=judge-sync-model",
                "--passes",
                "2",
                "--plan",
            ]
        )
        printed = capsys.readouterr().out
        assert rc == 0
        assert "[pipeline] PAID" in printed and "[g.cons2]" in printed
        assert printed.rstrip().endswith("plan only: nothing was run")
        assert not (c.RESULTS_ROOT / "panel_cycles" / tag).exists()


class TestCycle:
    def test_a_whole_cycle_runs_in_order_and_records_what_it_spent(self, tmp_path):
        world = World(tmp_path, partial_consensus=[2], compare_with_tag="t0")
        summary = world.run()
        assert summary["exit_code"] == 0 and summary["stopped"] is None
        calls = world.calls
        assert calls[0] == "pipeline" and calls[-1] == "trace"
        for family in ("g", "s"):
            order = [
                calls.index(f"{family}.{name}")
                for name in ("dry", "p1", "cons2", "cons3")
            ]
            assert order == sorted(order)
            assert calls.index(f"{family}.p3") < calls.index(f"{family}.cons2")
        # The synchronous family waits on its first pass.
        assert calls.index("g.p1") < min(calls.index("g.p2"), calls.index("g.p3"))
        assert summary["pipeline"]["harvest"] == {"copied": 2, "missing": 0, "stale": 0}
        assert summary["pipeline"]["verdict"] == "Verdict: PASS (0 documents failed)"
        assert summary["openrouter_spent"] == 12.5
        assert summary["judges"]["g"]["ok"] and summary["judges"]["s"]["ok"]
        assert summary["trace"] == {"rc": 0, "families": ["g", "s"]}
        on_disk = json.loads((world.cfg.cycle_dir / "cycle.json").read_text("utf-8"))
        assert on_disk["head"] == HEAD["head"] and on_disk["panel_size"] == 2
        for doc in PANEL:
            assert (world.cfg.states_dir / f"state_full_{doc}.json").is_file()
            assert (world.cfg.signatures_dir / f"signature_{doc}.json").is_file()
        assert world.events()[0] == "start" and world.events()[-1] == "end"

    def test_the_trace_reads_the_full_consensus_of_each_family(self, tmp_path):
        world = World(tmp_path)
        world.run()
        argv = world.steps["trace"].argv
        cons = argv[argv.index("--consensus-dir") + 1 : argv.index("--out")]
        assert cons == [
            str(world.cfg.consensus_dir(SYNC, 3)),
            str(world.cfg.consensus_dir(BATCH, 3)),
        ]
        assert argv[argv.index("--states-dir") + 1] == str(world.cfg.states_dir)

    def test_a_missing_zero_shot_answer_stops_before_anything_runs(self, tmp_path):
        world = World(tmp_path)
        (world.zeroshot / "doc_b.json").write_text('{"answer": ""}', encoding="utf-8")
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED
        assert world.calls == []
        assert "zero-shot" in summary["stopped"]

    def test_a_key_without_enough_credit_stops_before_the_pipeline(self, tmp_path):
        world = World(tmp_path, min_credit=40.0)
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED
        assert world.calls == []
        assert "--min-credit" in summary["stopped"]

    def test_an_unread_credit_does_not_stop_the_cycle_and_is_not_a_zero_spend(
        self, tmp_path
    ):
        world = World(tmp_path)
        world.credits = [{"unavailable": "the key endpoint is unreachable"}]
        summary = world.run()
        assert summary["exit_code"] == 0
        assert summary["openrouter_spent"] is None

    def test_a_failed_pipeline_runs_no_judge(self, tmp_path):
        world = World(tmp_path)
        world.rc["pipeline"] = 1
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED
        assert world.calls == ["pipeline"]
        assert "R1149" in summary["stopped"]
        assert summary["pipeline"]["verdict"].startswith("Verdict: FAIL")

    def test_a_checkout_during_the_pipeline_runs_no_judge(self, tmp_path):
        world = World(tmp_path)
        world.heads = [HEAD, {**HEAD, "head": "c" * 40}]
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED
        assert world.calls == ["pipeline"]
        assert "HEAD moved" in summary["stopped"]

    def test_a_state_left_by_an_earlier_cycle_is_not_harvested(self, tmp_path):
        world = World(tmp_path)
        world.write_kb("doc_b", age_seconds=3600)
        world.pipeline_writes = ["doc_a"]
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED
        assert world.calls == ["pipeline"]
        assert summary["pipeline"]["harvest"] == {"copied": 1, "missing": 0, "stale": 1}
        assert not (world.cfg.states_dir / "state_full_doc_b.json").exists()

    def test_a_document_the_pipeline_wrote_nothing_for_stops_the_cycle(self, tmp_path):
        world = World(tmp_path)
        world.pipeline_writes = ["doc_a"]
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED
        assert summary["pipeline"]["harvest"] == {"copied": 1, "missing": 1, "stale": 0}
        assert world.paid() == ["pipeline"]

    def test_the_pipeline_stage_stops_after_the_harvest(self, tmp_path):
        world = World(tmp_path, stage="pipeline", judges=())
        summary = world.run()
        assert summary["exit_code"] == 0
        assert world.calls == ["pipeline"]

    def test_the_judges_stage_needs_a_harvested_cycle(self, tmp_path):
        world = World(tmp_path, stage="judges")
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED
        assert world.calls == []
        assert "--stage pipeline" in summary["stopped"]

    def test_a_resumed_cycle_keeps_the_commit_its_states_were_produced_at(
        self, tmp_path
    ):
        world = World(tmp_path, stage="pipeline", judges=())
        world.run()
        later = {**HEAD, "head": "d" * 40}
        world.heads = [later]
        for stage in ("judges", "consensus"):
            world.cfg = dataclasses.replace(world.cfg, judges=[SYNC], stage=stage)
            summary = world.run()
            assert summary["exit_code"] == 0
            on_disk = json.loads(
                (world.cfg.cycle_dir / "cycle.json").read_text("utf-8")
            )
            assert on_disk["head"] == later["head"], "the invocation's commit"
            assert on_disk["pipeline"]["head"] == HEAD["head"], "the states' commit"
            assert on_disk["pipeline"]["harvest"] == {
                "copied": 2,
                "missing": 0,
                "stale": 0,
            }

    @pytest.mark.parametrize(
        "failure, named",
        [
            ({"rc": 1}, "R1149"),
            ({"head_after": "c" * 40}, "HEAD moved"),
            ({"harvest": {"copied": 1, "missing": 1, "stale": 0}}, "harvest"),
        ],
    )
    def test_a_resume_does_not_judge_a_pipeline_recorded_as_failed(
        self, tmp_path, failure, named
    ):
        """The states are all there — an earlier cycle's, or a failed batch's —
        so the harvested-cycle check alone would let the judges be paid."""
        world = World(tmp_path, judges=(SYNC,), stage="judges")
        for doc in PANEL:
            world.write_kb(doc)
        run_cycle.harvest(world.cfg, PANEL, time.time())
        record = {
            **HEAD,
            "head_after": HEAD["head"],
            "rc": 0,
            "harvest": {"copied": 2, "missing": 0, "stale": 0},
            **failure,
        }
        (world.cfg.cycle_dir / run_cycle.PIPELINE_RECORD).write_text(
            json.dumps(record), encoding="utf-8"
        )
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_STOPPED
        assert world.calls == []
        assert "recorded pipeline" in summary["stopped"] and named in summary["stopped"]

    def test_a_cycle_harvested_without_the_runner_says_so(self, tmp_path):
        world = World(tmp_path, judges=(SYNC,), stage="judges")
        for doc in PANEL:
            world.write_kb(doc)
        run_cycle.harvest(world.cfg, PANEL, time.time())
        summary = world.run()
        assert summary["exit_code"] == 0
        assert summary["pipeline"] is None
        assert "pipeline_unrecorded" in world.events()

    def test_the_pipeline_stage_records_a_failed_run_too(self, tmp_path):
        world = World(tmp_path, stage="pipeline", judges=())
        world.rc["pipeline"] = 1
        world.run()
        record = run_cycle.recorded_pipeline(world.cfg)
        assert record["rc"] == 1 and record["head"] == HEAD["head"]
        assert run_cycle.pipeline_problem(record).startswith("pipeline exit 1")

    def test_a_failed_dry_run_pays_no_pass(self, tmp_path):
        world = World(tmp_path, judges=(SYNC,))
        world.rc["g.dry"] = 3
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_JUDGES
        assert world.paid() == ["pipeline"]
        assert "dry-run" in summary["judges"]["g"]["stopped"]

    def test_a_synchronous_family_pays_one_pass_before_the_others(self, tmp_path):
        world = World(tmp_path, judges=(SYNC,))
        world.rc["g.p1"] = 2
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_JUDGES
        assert world.paid() == ["pipeline", "g.p1"]
        assert summary["judges"]["g"]["consensus"] == {}
        assert "trace" not in world.calls

    def test_a_batch_family_submits_its_passes_together(self, tmp_path):
        world = World(tmp_path, judges=(BATCH,))
        world.rc["s.p1"] = 2
        summary = world.run()
        assert sorted(world.paid()) == ["pipeline", "s.p1", "s.p2", "s.p3"]
        assert summary["exit_code"] == run_cycle.EXIT_JUDGES
        assert not any(".cons" in name for name in world.calls)

    def test_a_zero_exit_without_the_rows_is_not_a_complete_pass(self, tmp_path):
        world = World(tmp_path, judges=(BATCH,))
        played = world.runner

        def forgetful(step: run_cycle.Step) -> int:
            rc = played(step)
            if step.name == "s.p2":
                (world.cfg.pass_dir(BATCH, 2) / "doc_b.json").unlink()
            return rc

        summary = run_cycle.run_cycle(
            world.cfg, runner=forgetful, credit=world.credit, head=world.head
        )
        assert summary["exit_code"] == run_cycle.EXIT_JUDGES
        assert summary["judges"]["s"]["passes"]["p2"] == 0
        assert "[2]" in summary["judges"]["s"]["stopped"]
        assert not any(".cons" in name for name in world.calls)

    def test_a_pass_already_judged_is_not_paid_twice(self, tmp_path):
        world = World(tmp_path, judges=(SYNC,), stage="judges")
        for doc in PANEL:
            world.write_kb(doc)
        run_cycle.harvest(world.cfg, PANEL, time.time())
        for number in (1, 2):
            write_pass(world.cfg.pass_dir(SYNC, number), map(judged_row, PANEL))
        summary = world.run()
        assert summary["exit_code"] == 0
        assert world.paid() == ["g.p3"]
        assert world.steps["g.dry"].argv[
            world.steps["g.dry"].argv.index("--out-dir") + 1
        ] == str(world.cfg.pass_dir(SYNC, 3))
        assert summary["judges"]["g"]["passes"]["p1"] == "already complete"

    def test_a_family_already_judged_goes_straight_to_its_consensus(self, tmp_path):
        world = World(tmp_path, judges=(SYNC,), stage="judges")
        for doc in PANEL:
            world.write_kb(doc)
        run_cycle.harvest(world.cfg, PANEL, time.time())
        for number in (1, 2, 3):
            write_pass(world.cfg.pass_dir(SYNC, number), map(judged_row, PANEL))
        world.run()
        assert world.calls == ["g.cons3", "trace"]

    def test_the_consensus_stage_pays_nothing_whatever_it_finds(self, tmp_path):
        world = World(tmp_path, judges=(SYNC, BATCH), stage="consensus")
        for doc in PANEL:
            world.write_kb(doc)
        run_cycle.harvest(world.cfg, PANEL, time.time())
        for number in (1, 2, 3):
            write_pass(world.cfg.pass_dir(SYNC, number), map(judged_row, PANEL))
        write_pass(world.cfg.pass_dir(BATCH, 1), map(judged_row, PANEL))
        summary = world.run()
        assert world.paid() == []
        assert sorted(world.calls) == ["g.cons3", "trace"]
        assert summary["exit_code"] == run_cycle.EXIT_JUDGES
        assert "[2, 3]" in summary["judges"]["s"]["stopped"]
        assert [s.name for s in run_cycle.plan(world.cfg)] == [
            "g.cons3",
            "s.cons3",
            "trace",
        ]

    def test_only_the_families_that_completed_are_traced(self, tmp_path):
        world = World(tmp_path)
        world.rc["s.p2"] = 2
        summary = world.run()
        assert summary["exit_code"] == run_cycle.EXIT_JUDGES
        assert summary["trace"]["families"] == ["g"]
        argv = world.steps["trace"].argv
        assert str(world.cfg.consensus_dir(BATCH, 3)) not in argv

    def test_one_pass_is_not_a_consensus(self, tmp_path):
        world = World(tmp_path, judges=(SYNC,), passes=1)
        summary = world.run()
        assert summary["exit_code"] == 0
        assert world.calls == ["pipeline", "g.dry", "g.p1"]


class TestPassComplete:
    def test_the_judges_own_rule_decides(self, tmp_path):
        complete = tmp_path / "complete"
        write_pass(complete, map(judged_row, PANEL))
        assert run_cycle.pass_complete(complete, PANEL)

        no_meta = tmp_path / "no_meta"
        write_pass(no_meta, map(judged_row, PANEL), meta=False)
        assert not run_cycle.pass_complete(no_meta, PANEL)

        short = tmp_path / "short"
        write_pass(short, [judged_row("doc_a")])
        assert not run_cycle.pass_complete(short, PANEL)

        failed = tmp_path / "failed"
        write_pass(failed, [judged_row("doc_a"), judged_row("doc_b", status_code=529)])
        assert not run_cycle.pass_complete(failed, PANEL)

        cut = tmp_path / "cut"
        write_pass(
            cut,
            [
                judged_row("doc_a"),
                judged_row("doc_b", state="UNPARSED", stop_reason="max_tokens"),
            ],
        )
        assert not run_cycle.pass_complete(cut, PANEL)

        assert not run_cycle.pass_complete(tmp_path / "absent", PANEL)

    def test_the_rule_is_the_one_the_live_pass_exits_on(self):
        from scripts.dataset import judge_panel as jp

        rows = [
            judged_row("doc_a"),
            judged_row("doc_b", status_code=0),
            judged_row("doc_c", state="UNPARSED", stop_reason="length"),
            judged_row("doc_d", state="UNPARSED", stop_reason="end_turn"),
        ]
        assert jp.unjudged_documents(rows) == (["doc_b"], ["doc_c"])


class TestPreviousConsensus:
    def test_the_same_size_first_then_the_largest_then_none(self, tmp_path):
        world = World(tmp_path, compare_with_tag="t0")
        cfg = world.cfg
        assert cfg.previous_consensus(SYNC, 3) is None
        assert "--compare-with" not in run_cycle.consensus_step(cfg, SYNC, 3).argv

        for size in (2, 6):
            cfg.consensus_dir(SYNC, size, "t0").mkdir(parents=True)
        assert cfg.previous_consensus(SYNC, 3) == cfg.consensus_dir(SYNC, 6, "t0")
        cfg.consensus_dir(SYNC, 3, "t0").mkdir()
        assert cfg.previous_consensus(SYNC, 3) == cfg.consensus_dir(SYNC, 3, "t0")
        argv = run_cycle.consensus_step(cfg, SYNC, 3).argv
        assert argv[argv.index("--compare-with") + 1] == str(
            cfg.consensus_dir(SYNC, 3, "t0")
        )
        # Another family's consensus is never borrowed.
        assert cfg.previous_consensus(BATCH, 3) is None

    def test_no_previous_cycle_no_comparison(self, tmp_path):
        assert World(tmp_path).cfg.previous_consensus(SYNC, 3) is None


# ---------------------------------------------------------------------------
# The credit reader
# ---------------------------------------------------------------------------

SECRET = "sk-or-test-not-a-real-key"


class TestCredit:
    def test_the_process_value_wins_over_the_file(self, tmp_path, monkeypatch):
        dotenv = tmp_path / ".env"
        dotenv.write_text("OPENROUTER_API_KEY=from-the-file\n", encoding="utf-8")
        monkeypatch.setenv("OPENROUTER_API_KEY", "from-the-process")
        assert openrouter_credit.resolve_key(dotenv) == ("from-the-process", "process")
        monkeypatch.delenv("OPENROUTER_API_KEY")
        assert openrouter_credit.resolve_key(dotenv) == ("from-the-file", ".env")

    def test_a_process_value_the_file_holds_came_from_the_file(
        self, tmp_path, monkeypatch
    ):
        """The package's loader copies the ``.env`` into the process at import:
        "set in the process" then says nothing about where the key came from."""
        dotenv = tmp_path / ".env"
        dotenv.write_text("OPENROUTER_API_KEY=from-the-file\n", encoding="utf-8")
        monkeypatch.setenv("OPENROUTER_API_KEY", "from-the-file")
        assert openrouter_credit.resolve_key(dotenv) == ("from-the-file", ".env")

    def test_the_reading_keeps_three_figures_and_where_the_key_came_from(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("OPENROUTER_API_KEY", SECRET)
        asked: List[str] = []

        def fetch(key: str) -> Dict[str, Any]:
            asked.append(key)
            return {"usage": 3.5, "limit": 20, "limit_remaining": 16.5, "label": SECRET}

        credit = openrouter_credit.read_credit(fetch, tmp_path / "absent.env")
        assert asked == [SECRET]
        assert credit == {
            "usage": 3.5,
            "limit": 20,
            "limit_remaining": 16.5,
            "key_source": "process",
        }

    def test_no_key_is_reported_not_guessed(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(openrouter_credit.CreditUnavailable):
            openrouter_credit.read_credit(lambda key: {}, tmp_path / "absent.env")

    def test_a_refused_key_is_reported_without_the_key(self, monkeypatch):
        def refuse(request, timeout=0):
            raise urllib.error.HTTPError(
                request.full_url, 401, "unauthorized", {}, io.BytesIO(b"")
            )

        monkeypatch.setattr(openrouter_credit.urllib.request, "urlopen", refuse)
        with pytest.raises(openrouter_credit.CreditUnavailable) as caught:
            openrouter_credit.http_fetch(SECRET)
        assert "401" in str(caught.value)
        assert SECRET not in str(caught.value)
        assert caught.value.__cause__ is None

    def test_an_unread_credit_is_not_a_zero_spend(self):
        before, after = {"usage": 10.0}, {"usage": 21.25}
        assert openrouter_credit.spent_between(before, after) == 11.25
        assert openrouter_credit.spent_between(None, after) is None
        assert openrouter_credit.spent_between(before, {"unavailable": "x"}) is None

    def test_the_command_prints_the_reading_or_the_reason(self, monkeypatch, capsys):
        monkeypatch.setattr(
            openrouter_credit, "read_credit", lambda: {"usage": 1.0, "limit": None}
        )
        assert openrouter_credit.main([]) == 0
        assert json.loads(capsys.readouterr().out) == {"usage": 1.0, "limit": None}

        def unavailable():
            raise openrouter_credit.CreditUnavailable("the key endpoint answered 402")

        monkeypatch.setattr(openrouter_credit, "read_credit", unavailable)
        assert openrouter_credit.main([]) == 1
        assert "402" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The classifier
# ---------------------------------------------------------------------------


class TestClassify:
    def trace_rows(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        examined, left_out = examined_and_not(state)
        index = c.build_doc_index("doc_a", state)
        rows = []
        for item in (
            m1(sentence(left_out)),
            m1(sentence(examined), central=False, support=1),
            {"code": "M2", "pipeline_quote": "a claim the render makes", "support": 1},
        ):
            row = {"family": "family_cons", "doc": "doc_a", "bucket": "minority"}
            row.update(trace_items.trace_item(index, item))
            rows.append(row)
        return rows

    def test_a_lone_minority_item_off_the_thesis_is_not_sent(self):
        rows = self.trace_rows(make_state())
        assert [classify_items.worth_classifying(row) for row in rows] == [
            True,  # central
            False,  # one pass, off the thesis, not kept
            True,  # every M2
        ]
        assert classify_items.worth_classifying({**rows[1], "bucket": "kept"})
        assert classify_items.worth_classifying({**rows[1], "support": 2})

    def test_the_prompt_gives_the_measured_stage_and_the_units_at_the_passage(
        self, tmp_path
    ):
        state = make_state()
        _, left_out = examined_and_not(state)
        add_finding(state, left_out)
        state["act1_framing"] = "The framing of the render."
        states_dir, _ = write_cycle(tmp_path, {"doc_a": state}, {})
        rows = [
            r for r in self.trace_rows(state) if classify_items.worth_classifying(r)
        ]
        prompts, by_doc = classify_items.build_prompts(states_dir, rows)
        assert list(prompts) == ["doc_a"] and len(by_doc["doc_a"]) == 2
        prompt = prompts["doc_a"]
        assert "The framing of the render." in prompt
        assert trace_items.STAGE_UNIT_NOT_EXAMINED in prompt
        assert f"arg_{left_out + 1}" in prompt, "the unit at the passage is shown"
        assert "ad_hominem" in prompt, "with the findings recorded on it"
        for name in classify_items.CLASSES:
            assert name in prompt

    def test_an_answer_is_read_fenced_or_bare(self):
        payload = {"items": [{"i": 0, "class": "BUDGET"}], "doc_pattern": "p"}
        bare = json.dumps(payload)
        assert classify_items.parse_answer(bare) == payload
        assert classify_items.parse_answer(f"```json\n{bare}\n```") == payload
        assert classify_items.parse_answer(f"Here it is:\n{bare}\nDone.") == payload
        with pytest.raises(ValueError):
            classify_items.parse_answer("no object here")

    def test_an_index_the_prompt_never_gave_is_dropped_not_guessed(self):
        # Two rows, so that ``True`` (which is 1) and ``-1`` (the last row) each
        # name a real row to a reader that does not refuse them.
        rows = [
            {"family": "f", "code": "M1", "stage": "unit_not_examined"},
            {"family": "f", "code": "M1", "stage": "examined_no_finding"},
        ]
        parsed = {
            "items": [
                {"i": 0, "class": "BUDGET"},
                {"i": 2, "class": "LENS_MISSED"},
                {"i": True, "class": "WRITER_DROP"},
                {"i": -1, "class": "NO_LENS_ASKS"},
                {"i": "1", "class": "READING_MISS"},
                {"class": "JUDGE_WRONG"},
            ]
        }
        merged = classify_items.merge_answer(parsed, rows)
        assert [(item["class"], item["stage"]) for item in merged] == [
            ("BUDGET", "unit_not_examined")
        ]

    def test_an_unpriced_model_has_no_estimate(self):
        prompts = {"doc_a": "x" * 3000}
        assert classify_items.estimate_cost("a-model-no-table-prices", prompts) is None
        assert classify_items.estimate_cost(classify_items.DEFAULT_MODEL, prompts) > 0

    def test_the_dry_run_makes_no_call_and_writes_nothing(
        self, tmp_path, monkeypatch, capsys
    ):
        state = make_state()
        states_dir, _ = write_cycle(tmp_path, {"doc_a": state}, {})
        trace = tmp_path / "trace.jsonl"
        trace.write_text(
            "\n".join(json.dumps(row) for row in self.trace_rows(state)), "utf-8"
        )

        async def no_call(*_args, **_kwargs):
            raise AssertionError("a dry-run made a call")

        monkeypatch.setattr(classify_items, "call_all", no_call)
        out = tmp_path / "classes.json"
        rc = classify_items.main(
            [
                "--states-dir",
                str(states_dir),
                "--trace",
                str(trace),
                "--out",
                str(out),
                "--dry-run",
            ]
        )
        printed = capsys.readouterr().out
        assert rc == 0
        assert "documents=1 items=2" in printed and "dry-run: no call" in printed
        assert not out.exists()

    def test_the_classes_that_are_not_pipeline_defects_exist(self):
        assert classify_items.NOT_A_PIPELINE_DEFECT <= set(classify_items.CLASSES)


# ---------------------------------------------------------------------------
# Privacy: where an artifact may be written, and what a tracked file may hold
# ---------------------------------------------------------------------------

# A document id of the corpus, optionally with its extract suffix, as a class.
ID_SHAPED = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{8}(?![0-9A-Za-z])")


class TestPrivacy:
    def test_an_output_git_would_track_is_refused(self, tmp_path):
        with pytest.raises(c.OutputRefused):
            c.ensure_gitignored(REPO_ROOT / "docs" / "guides" / "trace.jsonl")
        with pytest.raises(c.OutputRefused):
            c.ensure_gitignored(REPO_ROOT / "scripts" / "panel" / "classes.json")
        c.ensure_gitignored(c.RESULTS_ROOT / "panel_cycles" / "t1" / "trace.jsonl")
        c.ensure_gitignored(tmp_path / "outside_the_repository.jsonl")

    def test_every_writer_refuses_a_tracked_path(self, tmp_path):
        states_dir, consensus = write_cycle(tmp_path, {"doc_a": make_state()}, {})
        tracked = str(REPO_ROOT / "docs" / "panel_artifact")
        with pytest.raises(c.OutputRefused):
            trace_items.main(
                [
                    "--states-dir",
                    str(states_dir),
                    "--consensus-dir",
                    str(consensus),
                    "--out",
                    tracked,
                ]
            )
        with pytest.raises(c.OutputRefused):
            classify_items.main(
                [
                    "--states-dir",
                    str(states_dir),
                    "--trace",
                    str(tmp_path / "t"),
                    "--out",
                    tracked,
                ]
            )
        with pytest.raises(c.OutputRefused):
            run_cycle.run_cycle(
                run_cycle.Config(
                    tag="t1",
                    panel_file=tmp_path / "panel.txt",
                    zeroshot_dir=tmp_path,
                    results_root=REPO_ROOT / "docs",
                )
            )
        assert not (REPO_ROOT / "docs" / "panel_cycles").exists()

    def test_the_id_class_matches_an_id_and_not_a_commit(self):
        made_up = "".join(["ab12", "cd34"])
        assert ID_SHAPED.findall(f"state_full_{made_up}.json") == [made_up]
        assert ID_SHAPED.findall(f"doc {made_up} and {made_up}_ext0") == [made_up] * 2
        assert ID_SHAPED.findall("commit " + made_up + "5") == []

    def test_no_tracked_instrument_carries_a_document_id_shaped_token(self):
        """The panel is passed by path: its composition stays on the seat."""
        files = sorted((REPO_ROOT / "scripts" / "panel").glob("*.py"))
        files += [
            Path(__file__),
            REPO_ROOT / "docs" / "guides" / "PANEL_CYCLE_RUNBOOK.md",
        ]
        assert len(files) >= 9
        offenders = {
            path.name: sorted(set(ID_SHAPED.findall(path.read_text(encoding="utf-8"))))
            for path in files
        }
        assert {name: found for name, found in offenders.items() if found} == {}
