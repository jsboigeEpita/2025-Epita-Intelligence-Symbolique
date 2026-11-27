"""#3658 item 46c — the live act replay, measured before a model call is paid.

``scripts/panel/act_replay_live.py`` is the paid half of ``replay_acts.py``: it
re-runs Acts I to III over a cycle's recorded states and writes a tag the
judges stage opens. Five claims carry the weight, each with the control that
makes its reading mean something:

* **The instrument gives the record back.** The identity control replays the
  recorded acts over the record's own states and compares bytes; on the
  invented record below both halves come back equal, and a byte moved by hand
  in either half is caught. The same control names a *sanitiser* difference
  when only the opacifying key changed, and never calls it an instrument
  difference unless the state half held first.
* **The tag is one ``run_cycle`` opens.** ``pipeline.json`` is written refusing
  first, and the final record only turns ``rc`` to 0 once the judges' own entry
  points read the tag back — measured on the record the run is about to write,
  never on the unverified one.
* **The seat is gated before it is trusted.** Every refusal below is a named
  string, the pins are compared by value and reported by presence, and
  ``observe()`` under pytest is the live witness that the pytest refusal is not
  a branch nobody takes.
* **A failed act is a degraded arm.** The act's key stays empty, the closed
  code rides ``restitution_acts_degraded``, and the judge's own #3458 rule is
  what refuses the panel — the batch is not stopped by one act.
* **Nothing is spent on a refusal.** The control runs before the destination
  exists and uses in-process providers; the live providers' call counter is the
  witness that a refused run paid nothing.

Stub seat, no key, no client, no corpus: every fixture is invented here and no
case pays a model call. ``results_root`` is the test's own ``tmp_path``, so
nothing is written under the repository's results tree.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import types
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import pytest

from scripts.panel import _common as c
from scripts.panel import act_replay_fidelity as fidelity
from scripts.panel import act_replay_live as live

DOCS = ("doc_t1", "doc_t2")
MARK = "INVENTED-ACT-live-3658"
REPLAYED_MARK = "INVENTED-ACT-REJOUE-3658"
SALT = "invented-salt-3658"
OTHER_SALT = "another-invented-salt-3658"
WORKFLOW = "spectacular"
RUN_NAME = "spectacular_analysis"
INVENTED_MODEL = "invented-model-3658"
NON_ARGUMENTATIVE = "doc_t3"


# ---------------------------------------------------------------------------
# The invented record: a harvest as the batch writes it, nothing real inside
# ---------------------------------------------------------------------------


def _bucket(calls: int, prompt: int, completion: int, stops: int = 0) -> Dict[str, int]:
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "calls": calls,
        "calls_without_usage": 0,
        "length_stops": stops,
        "calls_without_finish_reason": 0,
    }


def _usage() -> Dict[str, Any]:
    """A recorded usage map: three act buckets, one non-act phase, run-level."""
    return {
        "act1_framing": _bucket(1, 120, 300),
        "act2_narrative": _bucket(2, 260, 640),
        "act3_conclusion": _bucket(1, 180, 420),
        "extract": _bucket(2, 900, 500),
        "cost_usd": 0.012,
        "computed_cost_usd": 0.011,
        "unpriced_calls": {},
        "unverified_price_calls": {INVENTED_MODEL: 5},
    }


def _seed(doc: str) -> Dict[str, Any]:
    """The recorded state, invented. Containers are the shapes the producers
    read: ``identified_arguments`` and ``identified_fallacies`` are dicts keyed
    by id (``projection_from_state`` iterates their keys)."""
    return {
        "raw_text": f"Texte inventé du document {doc}, écrit pour le témoin.",
        "act1_framing": f"{MARK} : cadre inventé pour {doc}.",
        "act2_narrative": f"{MARK} : récit inventé pour {doc}.",
        "act3_conclusion": f"{MARK} : conclusion inventée pour {doc}.",
        "interpretive_question": f"Que cherche à faire l'orateur inventé de {doc} ?",
        "announced_checks": ["un point annoncé inventé", "un second point annoncé"],
        "narrative_synthesis": f"{MARK} : synthèse inventée pour {doc}.",
        "restitution_acts_degraded": {"act2_narrative": {"invented_motif": 2}},
        "identified_arguments": {
            "arg-1": {
                "id": "arg-1",
                "premises": ["une prémisse inventée"],
                "conclusion": "une conclusion inventée",
                "type": "deductive",
            }
        },
        "identified_fallacies": {
            "fallacy-1": {
                "fallacy_type": "ad_hominem",
                "target_argument_id": "arg-1",
                "explanation": "une explication inventée",
            }
        },
        "source_metadata": {
            "speaker": "Orateur inventé",
            "arena": "Arène inventée",
            "epoch": "Époque inventée",
        },
        "phases_left_out": [],
        "rests_on_armed": False,
        "workflow_results": {
            RUN_NAME: {
                "completed": 2,
                "failed": 0,
                "skipped": 0,
                "degraded": False,
                "degraded_phases": [],
                "structured_arg_degraded": [],
                "phases": {"extract": "completed", "act1_framing": "completed"},
                "phase_errors": {},
                "terminal_phases": [],
                "analysis_outcome": {"status": "ok"},
            }
        },
        "errors": [],
    }


def _dump(obj: Any) -> str:
    """The fixture's own writer: the harvest writes ``indent=2`` and non-ASCII
    verbatim, and that is all the fixture needs."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build_cycle(
    results_root: Path,
    docs: Sequence[str] = DOCS,
    *,
    name: str = "c1",
    extra: Iterable[str] = (),
) -> Path:
    """A harvested cycle under ``results_root/panel_cycles/<name>``."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.evaluation.sanitize_state import sanitize_state
    from argumentation_analysis.reporting.restitution.conclusion_salience import (
        projection_from_state,
    )

    cycle = results_root / "panel_cycles" / name
    (cycle / "states").mkdir(parents=True)
    (cycle / "signatures").mkdir()
    for doc in list(docs) + list(extra):
        seed = _seed(doc)
        obj = UnifiedAnalysisState(seed["raw_text"])
        obj.__dict__.update(copy.deepcopy(seed))
        state = obj.get_state_snapshot(summarize=False)
        state["llm_usage"] = _usage()
        (cycle / "states" / f"state_full_{doc}.json").write_text(
            _dump(state), encoding="utf-8"
        )
        signature = {
            "opaque_id": doc,
            "metadata": {},
            "workflow": WORKFLOW,
            "wall_clock_s": 12.5,
            "outcome": {"status": "ok"},
            "state": sanitize_state(state),
            "llm_usage": state["llm_usage"],
            "provenance": {
                "run_started_utc": "2026-01-01T00:00:00Z",
                "code_sha": "b" * 40,
                "chat_model_id": INVENTED_MODEL,
                "environment": {"overrides": {"pinned_overrides": {}}},
                "params": {"workflow": WORKFLOW, "timeout_s": 900},
            },
            "zero_shot_surplus": projection_from_state(obj),
        }
        if doc == NON_ARGUMENTATIVE:
            signature["document_classification"] = fidelity.BRANCH_NON_ARGUMENTATIVE
        (cycle / "signatures" / f"signature_{doc}.json").write_text(
            _dump(signature), encoding="utf-8"
        )
    (cycle / "cycle.json").write_text(
        json.dumps({"panel_size": len(docs) + len(list(extra))}), encoding="utf-8"
    )
    (cycle / "pipeline.json").write_text(
        _dump(
            {
                "rc": 0,
                "head": "a" * 40,
                "head_after": "a" * 40,
                "harvest": {
                    "copied": len(docs) + len(list(extra)),
                    "missing": 0,
                    "stale": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    return cycle


def _path(cycle: Path, doc: str) -> Path:
    return c.state_path(cycle / "states", doc)


def _record(cycle: Path, doc: str, kind: str = "state") -> Dict[str, Any]:
    path = (
        _path(cycle, doc)
        if kind == "state"
        else cycle / "signatures" / f"signature_{doc}.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# In-process providers: the paid path, exercised for free
# ---------------------------------------------------------------------------


class _Provider:
    """What an act's capability returns. ``total`` counts every call, and is
    never reset — the witness that a refused run paid nothing."""

    name = "invented-provider-3658"

    def __init__(self, payload: Any = None) -> None:
        self.payload = payload
        self.calls = 0
        self.total = 0
        self.fail: Optional[BaseException] = None

    async def invoke(self, input_text: Any, context: Any = None) -> Any:
        self.calls += 1
        self.total += 1
        if self.fail is not None:
            raise self.fail
        return dict(self.payload)


class _Registry:
    def __init__(self, providers: Mapping[str, _Provider]) -> None:
        self.providers = dict(providers)

    def find_for_capability(self, capability: str, *args: Any, **kwargs: Any) -> list:
        provider = self.providers.get(capability)
        return [provider] if provider is not None else []


class _Rig:
    """The fake registry and the usage reader, per document."""

    def __init__(self, payloads: Mapping[str, Mapping[str, Any]]) -> None:
        self.providers = {act: _Provider(p) for act, p in payloads.items()}
        self.registry = _Registry(self.providers)

    def reset(self) -> None:
        for provider in self.providers.values():
            provider.calls = 0

    def usage(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            act: _bucket(provider.calls, 100 * provider.calls, 200 * provider.calls)
            for act, provider in self.providers.items()
        }
        out.update(
            cost_usd=0.003,
            computed_cost_usd=0.003,
            unpriced_calls={},
            unverified_price_calls={},
        )
        return out

    def paid(self) -> int:
        return sum(provider.total for provider in self.providers.values())


def live_payloads() -> Dict[str, Dict[str, Any]]:
    """What the live acts answer: a text that is not the record's, so a reader
    can tell the replay from a copy."""
    return {
        "act1_framing": {
            "act1_framing": f"{REPLAYED_MARK} : cadre rejoué par le témoin.",
            "status": "completed",
            "degraded": False,
            "degraded_reasons": {},
            "interpretive_question": "Question rejouée par le témoin ?",
            "announced_checks": ["un point rejoué"],
        },
        "act2_narrative": {
            "act2_narrative": f"{REPLAYED_MARK} : récit rejoué par le témoin.",
            "status": "completed",
            "degraded": False,
            "degraded_reasons": {},
        },
        "act3_conclusion": {
            "act3_conclusion": f"{REPLAYED_MARK} : conclusion rejouée par le témoin.",
            "status": "completed",
            "degraded": False,
            "degraded_reasons": {},
        },
    }


@pytest.fixture(scope="session")
def base() -> live.Runtime:
    """The real pipeline objects, re-pointed at in-process providers: the
    workflow catalog, the state class and the writers are the real ones, and no
    runtime built from this fixture can reach a model."""
    return dataclasses.replace(
        live.build_runtime(WORKFLOW),
        registry=_Registry({act: _Provider() for act in c.ACTS}),
    )


@pytest.fixture()
def rig(base: live.Runtime) -> tuple:
    harness = _Rig(live_payloads())
    runtime = dataclasses.replace(
        base,
        registry=harness.registry,
        usage_reset=harness.reset,
        usage_read=harness.usage,
    )
    return runtime, harness


@pytest.fixture(autouse=True)
def salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """The sanitiser needs a key, and the tests name their own."""
    monkeypatch.setenv("OPAQUE_ID_SALT", SALT)


def seat(**overrides: Any) -> live.Observed:
    values: Dict[str, Any] = {
        "salt": True,
        "cache_mode": "off",
        "in_pytest": False,
        "set_knobs": (),
        "model": INVENTED_MODEL,
        "route_error": None,
        "pins": {},
    }
    values.update(overrides)
    return live.Observed(**values)


# ---------------------------------------------------------------------------
# 1. The destination is a tag ``run_cycle`` opens
# ---------------------------------------------------------------------------


def test_a_tag_beside_the_cycles_is_accepted(tmp_path: Path) -> None:
    assert live.tag_problem(tmp_path / "panel_cycles" / "tag1", tmp_path) is None


def test_a_directory_elsewhere_is_refused_by_name(tmp_path: Path) -> None:
    why = live.tag_problem(tmp_path / "elsewhere" / "tag1", tmp_path)

    assert why is not None
    assert "sibling of the cycles" in why
    assert "panel_cycles" in why


def test_a_name_the_cycle_would_refuse_is_refused_here(tmp_path: Path) -> None:
    """The check is the cycle's own validator, not a copy of its rule."""
    why = live.tag_problem(tmp_path / "panel_cycles" / "tag one", tmp_path)

    assert why is not None
    assert "run_cycle would refuse the tag" in why


def test_a_tag_that_exists_is_not_overwritten(tmp_path: Path) -> None:
    """``tag_problem`` names the layout; the preflight names the collision."""
    cycle = build_cycle(tmp_path)
    tag = tmp_path / "panel_cycles" / "tag1"
    tag.mkdir()

    verdict = live.preflight(cycle, tag, list(DOCS))

    assert verdict.ok is False
    kinds = [problem.kind for problem in verdict.problems]
    assert live.preflight_module.DESTINATION_EXISTS in kinds


# ---------------------------------------------------------------------------
# 2. The seat is gated before it is trusted — each refusal by name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides, named",
    [
        ({"route_error": "RouteError"}, "does not resolve (RouteError)"),
        ({"model": None}, "resolves no model"),
        ({"cache_mode": "read"}, "LLM_CACHE_MODE is 'read'"),
        ({"in_pytest": True}, "under pytest"),
        ({"salt": False}, "OPAQUE_ID_SALT is absent"),
        ({"set_knobs": ("ACT_MAX_TOKENS",)}, "ACT_MAX_TOKENS"),
        (
            {"set_knobs": ("PHASE_MAX_TOKENS", "LLM_CALL_TIMEOUT_S")},
            "PHASE_MAX_TOKENS, LLM_CALL_TIMEOUT_S",
        ),
    ],
)
def test_each_way_a_seat_can_bend_an_act_is_refused_by_name(
    overrides: Dict[str, Any], named: str
) -> None:
    verdict = live.gate(None, INVENTED_MODEL, seat(**overrides))

    assert verdict.ok is False
    assert len(verdict.refusals) == 1, verdict.refusals
    assert named in verdict.refusals[0]


def test_a_clean_seat_passes() -> None:
    verdict = live.gate(None, INVENTED_MODEL, seat())

    assert verdict.ok is True
    assert verdict.refusals == ()
    assert verdict.notes["model"] == {"recorded": True, "seat": True, "equal": True}


def test_the_pytest_refusal_reads_a_real_pytest_process() -> None:
    """The control for the parametrised case above: the branch is taken."""
    observed = live.observe()

    assert observed.in_pytest is True
    assert live.gate(None, INVENTED_MODEL, observed).ok is False


def test_a_knob_set_in_the_shell_is_read_from_the_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert live.observe().set_knobs == ()

    monkeypatch.setenv("LLM_CALL_TIMEOUT_S", "1")
    assert live.observe().set_knobs == ("LLM_CALL_TIMEOUT_S",)


def _recorded_environment(pins: Mapping[str, Any]) -> Dict[str, Any]:
    return {"overrides": {"pinned_overrides": dict(pins)}}


def test_a_pin_is_compared_by_value_not_by_presence() -> None:
    recorded = _recorded_environment({"LLM_TEMPERATURE": 0.0})

    same = live.gate(recorded, INVENTED_MODEL, seat(pins={"LLM_TEMPERATURE": 0.0}))
    other = live.gate(recorded, INVENTED_MODEL, seat(pins={"LLM_TEMPERATURE": 0.7}))
    unset = live.gate(recorded, INVENTED_MODEL, seat(pins={}))

    assert same.ok is True
    assert same.notes["pins"]["LLM_TEMPERATURE"]["equal"] is True
    assert other.ok is False and "set to another value" in other.refusals[0]
    assert unset.ok is False and "unset on this seat" in unset.refusals[0]


def test_a_pin_wrapped_as_a_verdict_is_read_by_its_value() -> None:
    recorded = _recorded_environment({"LLM_SEED": {"value": 7, "source": "env"}})

    verdict = live.gate(recorded, INVENTED_MODEL, seat(pins={"LLM_SEED": 7}))

    assert verdict.ok is True
    assert verdict.notes["pins"]["LLM_SEED"]["equal"] is True


def test_the_gate_reports_presence_and_never_a_pin_value() -> None:
    recorded = _recorded_environment({"LLM_TEMPERATURE": 0.0})
    verdict = live.gate(recorded, INVENTED_MODEL, seat(pins={"LLM_TEMPERATURE": 0.7}))

    row = verdict.notes["pins"]["LLM_TEMPERATURE"]
    assert set(row) <= {"recorded", "seat", "equal", "note"}
    assert json.dumps(verdict.as_dict()).count("0.7") == 0


def test_a_pin_the_record_does_not_carry_is_a_note() -> None:
    verdict = live.gate(
        _recorded_environment({}), INVENTED_MODEL, seat(pins={"LLM_SEED": 1})
    )

    assert verdict.ok is True
    row = verdict.notes["pins"]["LLM_SEED"]
    assert row["recorded"] is False
    assert row["note"] == "not recorded: the acts run under today's default"


def test_a_panel_recorded_under_two_environments_is_refused() -> None:
    one = {"provenance": {"environment": {"a": 1}, "chat_model_id": INVENTED_MODEL}}
    two = {"provenance": {"environment": {"a": 2}, "chat_model_id": INVENTED_MODEL}}

    environment, model, problems = live.recorded_settings({"d1": one, "d2": two})

    assert environment is None and model is INVENTED_MODEL
    assert any("distinct environments" in problem for problem in problems)


def test_a_signature_without_an_environment_is_refused() -> None:
    environment, _, problems = live.recorded_settings({"d1": {"provenance": {}}})

    assert environment is None
    assert problems == ["d1: the signature records no environment"]


# ---------------------------------------------------------------------------
# 3. The workflow subset: the acts alone, asserted
# ---------------------------------------------------------------------------


def test_the_subset_is_the_three_acts_and_the_rest_is_named(
    base: live.Runtime,
) -> None:
    kept, skips = live.subset(base.workflow)

    assert [phase.name for phase in kept.phases] == list(c.ACTS)
    assert sorted(skips) == sorted(
        phase.name for phase in base.workflow.phases if phase.name not in c.ACTS
    )
    assert len(skips) + len(c.ACTS) == len(base.workflow.phases)


def _workflow(names: Sequence[str]) -> Any:
    return types.SimpleNamespace(
        name="invented-workflow",
        phases=[types.SimpleNamespace(name=name) for name in names],
    )


def test_a_workflow_without_the_acts_is_refused() -> None:
    with pytest.raises(live.Refused) as raised:
        live.subset(_workflow(["extract"]))

    assert "declares no phase" in str(raised.value)


def test_a_workflow_that_is_the_acts_alone_is_refused() -> None:
    """An empty skip list would let the environment choose the arm."""
    with pytest.raises(live.Refused) as raised:
        live.subset(_workflow(list(c.ACTS)))

    assert "the skip list would be empty" in str(raised.value)


# ---------------------------------------------------------------------------
# 4. The identity control: the record comes back, byte for byte
# ---------------------------------------------------------------------------


def _control(cycle: Path, doc: str, runtime: live.Runtime) -> Dict[str, Any]:
    return live.identity_control(
        doc,
        _record(cycle, doc),
        _record(cycle, doc, "signature"),
        runtime,
        _path(cycle, doc).read_bytes(),
        (cycle / "signatures" / f"signature_{doc}.json").read_bytes(),
    )


@pytest.mark.parametrize("doc", DOCS)
def test_the_control_gives_the_record_back_byte_for_byte(
    tmp_path: Path, base: live.Runtime, doc: str
) -> None:
    """Item 46c's fidelity control: with the recorded act texts, the instrument
    writes the recorded harvest's bytes — the state and the signature."""
    cycle = build_cycle(tmp_path)

    row = _control(cycle, doc, base)

    assert row["ok"] is True, row
    assert row["state"]["equal"] is True
    assert row["signature"]["equal"] is True
    assert row["signature"]["cause"] is None
    assert row["acts_run"] == len(c.ACTS)
    assert row["calls"] == {act: 1 for act in c.ACTS}
    assert row["unexpected"] == []


def test_the_control_runs_the_real_writers_and_reverts_the_bookkeeping(
    tmp_path: Path, base: live.Runtime
) -> None:
    cycle = build_cycle(tmp_path)

    row = _control(cycle, DOCS[0], base)

    assert row["reverted"] == ["workflow_results", "phases_left_out"]
    assert set(row["reverted"]) <= set(live.BOOKKEEPING)


def test_a_state_byte_moved_by_hand_fails_the_control(
    tmp_path: Path, base: live.Runtime
) -> None:
    cycle = build_cycle(tmp_path)
    doc = DOCS[0]
    flipped = _path(cycle, doc).read_bytes() + b" "

    row = live.identity_control(
        doc,
        _record(cycle, doc),
        _record(cycle, doc, "signature"),
        base,
        flipped,
        (cycle / "signatures" / f"signature_{doc}.json").read_bytes(),
    )

    assert row["ok"] is False
    assert row["state"]["equal"] is False
    # the signature half is untouched here: the state half is what caught it
    assert row["signature"]["equal"] is True
    assert row["signature"]["cause"] is None


def test_a_signature_byte_moved_by_hand_fails_the_control(
    tmp_path: Path, base: live.Runtime
) -> None:
    """The state half holds, so the difference is the instrument's: the objects
    are equal and only the bytes differ."""
    cycle = build_cycle(tmp_path)
    doc = DOCS[0]

    row = live.identity_control(
        doc,
        _record(cycle, doc),
        _record(cycle, doc, "signature"),
        base,
        _path(cycle, doc).read_bytes(),
        (cycle / "signatures" / f"signature_{doc}.json").read_bytes() + b" ",
    )

    assert row["state"]["equal"] is True
    assert row["signature"]["equal"] is False
    assert row["signature"]["cause"] == "instrument"


def test_another_opacifying_key_is_named_a_sanitiser_difference(
    tmp_path: Path, base: live.Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The record was sanitised under another key: the state half still holds,
    and the label says sanitiser — not instrument."""
    cycle = build_cycle(tmp_path)
    doc = DOCS[0]
    monkeypatch.setenv("OPAQUE_ID_SALT", OTHER_SALT)

    row = _control(cycle, doc, base)

    assert row["state"]["equal"] is True
    assert row["signature"]["equal"] is False
    assert row["signature"]["cause"] == "sanitiser"
    assert row["signature"]["differing_keys"] == ["state"]
    assert row["ok"] is True


# ---------------------------------------------------------------------------
# 5. Hydration is deep: the record is not the object the run writes through
# ---------------------------------------------------------------------------


def test_the_hydrated_object_shares_no_container_with_the_record(
    tmp_path: Path, base: live.Runtime
) -> None:
    """The regression witness for the aliasing defect: mutating the object in
    place must leave the record's dict untouched."""
    cycle = build_cycle(tmp_path)
    record = _record(cycle, DOCS[0])
    kept = copy.deepcopy(record["workflow_results"])

    obj = live.hydrate(record, base.state_class)
    obj.workflow_results[RUN_NAME]["completed"] = 99

    assert record["workflow_results"] == kept


async def test_a_run_leaves_the_record_it_was_given_untouched(
    tmp_path: Path, rig: tuple
) -> None:
    runtime, _ = rig
    cycle = build_cycle(tmp_path)
    state, signature = _record(cycle, DOCS[0]), _record(cycle, DOCS[0], "signature")
    kept_state, kept_signature = copy.deepcopy(state), copy.deepcopy(signature)

    await live.run_acts(DOCS[0], state, signature, runtime)

    assert state == kept_state
    assert signature == kept_signature


# ---------------------------------------------------------------------------
# 6. The usage map: two runs, told apart
# ---------------------------------------------------------------------------


def test_a_run_level_entry_is_not_a_phase() -> None:
    """``unpriced_calls`` and ``unverified_price_calls`` are dicts and are not
    phases — read by type alone they would refuse every paid run."""
    usage = _usage()

    phases = sorted(key for key, value in usage.items() if live._is_phase_bucket(value))

    assert phases == sorted(list(c.ACTS) + ["extract"])
    assert sorted(live.run_level(usage)) == [
        "computed_cost_usd",
        "cost_usd",
        "unpriced_calls",
        "unverified_price_calls",
    ]


async def test_the_tag_keeps_the_recorded_buckets_and_takes_the_replayed_ones(
    tmp_path: Path, rig: tuple
) -> None:
    runtime, _ = rig
    cycle = build_cycle(tmp_path)
    state, signature = _record(cycle, DOCS[0]), _record(cycle, DOCS[0], "signature")

    replayed = await live.run_acts(DOCS[0], state, signature, runtime)
    assembled = live.assemble(
        replayed,
        signature,
        runtime,
        live=True,
        facts=live.Facts.of(signature),
        source_cycle="c1",
        source_head="a" * 40,
    )

    usage = assembled.state["llm_usage"]
    assert all(usage[act]["calls"] == 1 for act in c.ACTS)
    assert usage["extract"] == state["llm_usage"]["extract"]
    assert usage["cost_usd"] == state["llm_usage"]["cost_usd"]
    assert (
        usage["unverified_price_calls"] == state["llm_usage"]["unverified_price_calls"]
    )
    assert assembled.row["usage"]["recorded_buckets_kept"] == ["extract"]
    assert assembled.row["usage"]["live_calls"] == len(c.ACTS)
    assert assembled.failure is None


async def test_a_non_act_phase_that_called_the_model_is_a_failure(
    tmp_path: Path, base: live.Runtime
) -> None:
    """The complement of the reading above: a real phase bucket outside the
    acts is what the guard exists for."""
    cycle = build_cycle(tmp_path)
    state, signature = _record(cycle, DOCS[0]), _record(cycle, DOCS[0], "signature")
    harness = _Rig(live_payloads())
    usage: Dict[str, Any] = {act: _bucket(1, 100, 200) for act in c.ACTS}
    usage["extract"] = _bucket(2, 10, 10)
    usage.update(
        cost_usd=0.0,
        computed_cost_usd=0.0,
        unpriced_calls={},
        unverified_price_calls={},
    )
    runtime = dataclasses.replace(
        base,
        registry=harness.registry,
        usage_reset=lambda: None,
        usage_read=lambda: usage,
    )

    replayed = await live.run_acts(DOCS[0], state, signature, runtime)
    assembled = live.assemble(
        replayed,
        signature,
        runtime,
        live=True,
        facts=live.Facts.of(signature),
        source_cycle="c1",
        source_head=None,
    )

    assert assembled.failure is not None
    assert (
        "a phase outside the three acts called the model: extract" in assembled.failure
    )


# ---------------------------------------------------------------------------
# 7. A failed act is a degraded arm, not a batch failure
# ---------------------------------------------------------------------------


async def test_a_failed_act_is_filed_as_a_degraded_arm(
    tmp_path: Path, rig: tuple
) -> None:
    runtime, harness = rig
    harness.providers["act2_narrative"].fail = RuntimeError("invented failure")
    cycle = build_cycle(tmp_path)
    state, signature = _record(cycle, DOCS[0]), _record(cycle, DOCS[0], "signature")

    replayed = await live.run_acts(DOCS[0], state, signature, runtime)
    assembled = live.assemble(
        replayed,
        signature,
        runtime,
        live=True,
        facts=live.Facts.of(signature),
        source_cycle="c1",
        source_head=None,
    )

    assert assembled.failure is None
    assert assembled.state["act2_narrative"] == ""
    assert assembled.state["restitution_acts_degraded"]["act2_narrative"] == {
        live.CODE_PHASE_FAILED: "exception"
    }
    row = assembled.row["acts"]["act2_narrative"]
    assert row["status"] == "failed" and row["codes"] == [live.CODE_PHASE_FAILED]
    assert assembled.row["ok"] is True


async def test_a_degraded_arm_is_what_the_judges_own_rule_refuses(
    tmp_path: Path, rig: tuple
) -> None:
    from scripts.dataset import judge_panel as judged

    runtime, harness = rig
    harness.providers["act2_narrative"].fail = RuntimeError("invented failure")
    cycle = build_cycle(tmp_path)
    state, signature = _record(cycle, DOCS[0]), _record(cycle, DOCS[0], "signature")

    replayed = await live.run_acts(DOCS[0], state, signature, runtime)
    assembled = live.assemble(
        replayed,
        signature,
        runtime,
        live=True,
        facts=live.Facts.of(signature),
        source_cycle="c1",
        source_head=None,
    )
    health = judged.arm_health(assembled.state, assembled.signature)

    assert health["pipeline_degraded"] is True
    assert health["empty_acts"] == ["act2_narrative"]


async def test_every_act_failing_stops_the_batch(tmp_path: Path, rig: tuple) -> None:
    """Three silent acts mean the merged code does not answer: spending the rest
    of the panel on the same silence is the waste this stops."""
    runtime, harness = rig
    for provider in harness.providers.values():
        provider.fail = RuntimeError("invented failure")
    cycle = build_cycle(tmp_path)
    state, signature = _record(cycle, DOCS[0]), _record(cycle, DOCS[0], "signature")

    replayed = await live.run_acts(DOCS[0], state, signature, runtime)
    assembled = live.assemble(
        replayed,
        signature,
        runtime,
        live=True,
        facts=live.Facts.of(signature),
        source_cycle="c1",
        source_head=None,
    )

    assert assembled.failure is not None
    assert "every act of this document failed" in assembled.failure


async def test_a_text_no_call_paid_for_is_not_a_live_act(
    tmp_path: Path, base: live.Runtime
) -> None:
    harness = _Rig(live_payloads())
    cycle = build_cycle(tmp_path)
    state, signature = _record(cycle, DOCS[0]), _record(cycle, DOCS[0], "signature")
    runtime = dataclasses.replace(
        base,
        registry=harness.registry,
        usage_reset=lambda: None,
        usage_read=lambda: {},  # nothing was accounted
    )

    replayed = await live.run_acts(DOCS[0], state, signature, runtime)
    assembled = live.assemble(
        replayed,
        signature,
        runtime,
        live=True,
        facts=live.Facts.of(signature),
        source_cycle="c1",
        source_head=None,
    )

    assert assembled.failure is not None
    assert "carries a text no call paid for" in assembled.failure
    assert assembled.row["acts"]["act1_framing"]["codes"] == [live.CODE_PHASE_FAILED]


# ---------------------------------------------------------------------------
# 8. The whole run: a tag the judges stage opens
# ---------------------------------------------------------------------------


def _judge_config(tag: Path, results_root: Path) -> Any:
    from scripts.panel.run_cycle import Config

    return Config(
        tag=tag.name,
        panel_file=tag / "unused-panel.txt",
        zeroshot_dir=tag / "unused-zeroshot",
        results_root=results_root,
    )


def test_the_run_writes_a_tag_the_judges_stage_reads(
    tmp_path: Path, rig: tuple
) -> None:
    from scripts.panel.run_cycle import (
        pipeline_problem,
        recorded_pipeline,
        unharvested,
    )

    runtime, harness = rig
    cycle = build_cycle(tmp_path)
    tag = tmp_path / "panel_cycles" / "tag1"

    report = live.run(
        cycle,
        tag,
        list(DOCS),
        ["--acts", "live"],
        observed=seat(),
        runtime=runtime,
        results_root=tmp_path,
    )

    assert report["ok"] is True, (report.get("refused"), report.get("self_check"))
    assert report["stage"] == live.STAGE_DONE
    assert list(report)[0] == "provenance"
    assert report["counts"] == {
        "documents": len(DOCS),
        "live": len(DOCS),
        "copied": 0,
        "acts_live": len(DOCS) * len(c.ACTS),
        "acts_degraded": [],
        "control_documents": len(DOCS),
        "control_ok": len(DOCS),
        "degraded_arms": 0,
    }
    # the paid step: one call per act and per document, measured
    assert harness.paid() == len(DOCS) * len(c.ACTS)
    cfg = _judge_config(tag, tmp_path)
    assert recorded_pipeline(cfg) is not None
    assert pipeline_problem(dict(recorded_pipeline(cfg) or {})) is None
    assert unharvested(cfg, list(DOCS)) == []
    assert report["self_check"]["problems"] == []
    assert report["self_check"]["guard"]["would_refuse"] is False


def test_the_final_record_says_rc_zero_only_once_the_check_holds(
    tmp_path: Path, rig: tuple
) -> None:
    runtime, _ = rig
    cycle = build_cycle(tmp_path)
    tag = tmp_path / "panel_cycles" / "tag1"

    live.run(
        cycle,
        tag,
        list(DOCS),
        [],
        observed=seat(),
        runtime=runtime,
        results_root=tmp_path,
    )

    record = json.loads((tag / "pipeline.json").read_text(encoding="utf-8"))
    assert record["rc"] == 0
    assert record["harvest"] == {"copied": len(DOCS), "missing": 0, "stale": 0}
    assert record["verdict"] == {
        "self_check": True,
        "guard_degraded_arms": 0,
        "guard_would_refuse": False,
    }
    assert record["head"] == record["head_after"]


def test_a_tag_whose_self_check_fails_keeps_rc_one(
    tmp_path: Path, rig: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail closed: a tag the instrument itself cannot read back is written
    rc 1, so the judges stage refuses it instead of grading it."""
    runtime, _ = rig
    cycle = build_cycle(tmp_path)
    tag = tmp_path / "panel_cycles" / "tag1"

    def _broken(destination: Path, doc: str, state: Any, signature: Any) -> None:
        (destination / "states" / f"state_full_{doc}.json").write_text(
            "[1, 2]", encoding="utf-8"
        )
        (destination / "signatures" / f"signature_{doc}.json").write_text(
            live.dumps(signature), encoding="utf-8"
        )

    monkeypatch.setattr(live, "_write_pair", _broken)

    report = live.run(
        cycle,
        tag,
        list(DOCS),
        [],
        observed=seat(),
        runtime=runtime,
        results_root=tmp_path,
    )

    assert report["ok"] is False
    assert report["stage"] == live.STAGE_DONE
    assert report["refused"] == "the self-check failed"
    assert report["self_check"]["problems"]
    assert json.loads((tag / "pipeline.json").read_text(encoding="utf-8"))["rc"] == 1


def test_a_copy_of_the_record_is_a_pair_the_judges_stage_reads(
    tmp_path: Path, rig: tuple
) -> None:
    """A document whose render reads no act keeps its own timeline."""
    runtime, harness = rig
    cycle = build_cycle(tmp_path, extra=[NON_ARGUMENTATIVE])
    tag = tmp_path / "panel_cycles" / "tag1"

    report = live.run(
        cycle,
        tag,
        list(DOCS) + [NON_ARGUMENTATIVE],
        [],
        observed=seat(),
        runtime=runtime,
        results_root=tmp_path,
    )

    assert report["ok"] is True, report.get("self_check")
    assert report["counts"]["live"] == len(DOCS)
    assert report["counts"]["copied"] == 1
    assert harness.paid() == len(DOCS) * len(c.ACTS)
    for kind, name in (("states", "state_full"), ("signatures", "signature")):
        copied = (tag / kind / f"{name}_{NON_ARGUMENTATIVE}.json").read_bytes()
        source = (cycle / kind / f"{name}_{NON_ARGUMENTATIVE}.json").read_bytes()
        assert copied == source
    rows = {row["doc"]: row for row in report["documents"]}
    assert rows[NON_ARGUMENTATIVE]["mode"] == live.COPIED
    assert "non_argumentative" in rows[NON_ARGUMENTATIVE]["reason"]


def test_the_tag_carries_the_replayed_acts_and_the_record_everywhere_else(
    tmp_path: Path, rig: tuple
) -> None:
    runtime, _ = rig
    cycle = build_cycle(tmp_path)
    tag = tmp_path / "panel_cycles" / "tag1"

    live.run(
        cycle,
        tag,
        list(DOCS),
        [],
        observed=seat(),
        runtime=runtime,
        results_root=tmp_path,
    )

    doc = DOCS[0]
    recorded = _record(cycle, doc)
    written = _record(tag, doc)
    for key in recorded:
        if key in live.WRITTEN_BACK:
            continue
        if key == "llm_usage":
            assert written[key]["extract"] == recorded[key]["extract"]
            continue
        assert written[key] == recorded[key], key
    assert written["act2_narrative"].startswith(REPLAYED_MARK)
    assert list(written) == list(recorded)

    signature = _record(tag, doc, "signature")
    assert list(signature) == list(_record(cycle, doc, "signature")) + ["act_replay"]
    block = signature["act_replay"]
    assert block["source_cycle"] == cycle.name
    assert block["acts"]["act2_narrative"]["calls"] == 1
    assert set(block["usage"]) == {"live_run", "llm_usage"}
    assert block["usage"]["live_run"]["cost_usd"] == 0.003


def test_the_report_never_carries_an_act_text(tmp_path: Path, rig: tuple) -> None:
    runtime, _ = rig
    cycle = build_cycle(tmp_path)
    tag = tmp_path / "panel_cycles" / "tag1"

    report = live.run(
        cycle,
        tag,
        list(DOCS),
        [],
        observed=seat(),
        runtime=runtime,
        results_root=tmp_path,
    )

    written = json.dumps(report, ensure_ascii=False)
    assert MARK not in written
    assert REPLAYED_MARK not in written
    assert "Orateur inventé" not in written
    assert "Texte inventé du document" not in written


def test_the_tag_is_written_refusing_first(tmp_path: Path, rig: tuple) -> None:
    """What a run that dies mid-panel leaves behind: the refusing record."""
    cycle = build_cycle(tmp_path)
    record = live._refusing_record(cycle, "c" * 40, live.utc_now(), len(DOCS))

    assert record["rc"] == 1
    assert record["harvest"] == {"copied": 0, "missing": len(DOCS), "stale": 0}
    assert record["head"] == record["head_after"] == "c" * 40
    assert "refusing first" in record["note"]


# ---------------------------------------------------------------------------
# 9. Nothing is spent on a refusal
# ---------------------------------------------------------------------------


def test_a_control_that_does_not_hold_writes_no_tag_and_pays_nothing(
    tmp_path: Path, rig: tuple
) -> None:
    runtime, harness = rig
    cycle = build_cycle(tmp_path)
    _path(cycle, DOCS[0]).write_bytes(_path(cycle, DOCS[0]).read_bytes() + b" ")
    tag = tmp_path / "panel_cycles" / "tag1"

    report = live.run(
        cycle,
        tag,
        list(DOCS),
        [],
        observed=seat(),
        runtime=runtime,
        results_root=tmp_path,
    )

    assert report["ok"] is False
    assert report["stage"] == live.STAGE_CONTROL
    assert "did not give the record back" in report["refused"]
    assert report["control"]["ok"] is False
    assert not tag.exists()
    assert harness.paid() == 0


def test_a_gated_seat_writes_no_tag_and_pays_nothing(
    tmp_path: Path, rig: tuple
) -> None:
    runtime, harness = rig
    cycle = build_cycle(tmp_path)
    tag = tmp_path / "panel_cycles" / "tag1"

    report = live.run(
        cycle,
        tag,
        list(DOCS),
        [],
        observed=seat(in_pytest=True),
        runtime=runtime,
        results_root=tmp_path,
    )

    assert report["ok"] is False
    assert report["stage"] == live.STAGE_GATE
    assert any("under pytest" in refusal for refusal in report["refusals"])
    assert not tag.exists()
    assert harness.paid() == 0


def test_a_cycle_the_preflight_refuses_writes_nothing(
    tmp_path: Path, rig: tuple
) -> None:
    runtime, harness = rig
    cycle = build_cycle(tmp_path)
    (cycle / "pipeline.json").unlink()
    tag = tmp_path / "panel_cycles" / "tag1"

    report = live.run(
        cycle,
        tag,
        list(DOCS),
        [],
        observed=seat(),
        runtime=runtime,
        results_root=tmp_path,
    )

    assert report["stage"] == live.STAGE_PREFLIGHT
    assert report["preflight"]["ok"] is False
    assert not tag.exists()
    assert harness.paid() == 0


def test_a_cycle_whose_batch_failed_is_refused_before_the_control(
    tmp_path: Path, rig: tuple
) -> None:
    runtime, harness = rig
    cycle = build_cycle(tmp_path)
    (cycle / "pipeline.json").write_text(
        _dump(
            {
                "rc": 1,
                "head": "a" * 40,
                "head_after": "a" * 40,
                "harvest": {"copied": len(DOCS), "missing": 0, "stale": 0},
            }
        ),
        encoding="utf-8",
    )
    tag = tmp_path / "panel_cycles" / "tag1"

    report = live.run(
        cycle,
        tag,
        list(DOCS),
        [],
        observed=seat(),
        runtime=runtime,
        results_root=tmp_path,
    )

    assert report["stage"] == live.STAGE_CYCLE
    assert "exit 1" in report["refused"]
    assert not tag.exists()
    assert harness.paid() == 0


def test_the_preflight_answers_before_the_runtime_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken cycle must be refused without binding the pipeline objects."""
    cycle = build_cycle(tmp_path)
    (cycle / "pipeline.json").unlink()
    reached: List[str] = []

    def _never(name: str) -> Any:
        def _factory(*args: Any, **kwargs: Any) -> Any:
            reached.append(name)
            raise AssertionError(f"{name} was bound before the preflight answered")

        return _factory

    monkeypatch.setattr(live, "build_runtime", _never("build_runtime"))
    monkeypatch.setattr(live, "identity_control", _never("identity_control"))

    report = live.run(
        cycle,
        tmp_path / "panel_cycles" / "tag1",
        list(DOCS),
        [],
        observed=seat(),
        results_root=tmp_path,
    )

    assert report["stage"] == live.STAGE_PREFLIGHT
    assert reached == []


# ---------------------------------------------------------------------------
# 10. The command line: exit codes that say where it stopped
# ---------------------------------------------------------------------------


def test_the_command_line_exits_two_when_nothing_was_written(
    tmp_path: Path, rig: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, harness = rig
    cycle = build_cycle(tmp_path)
    monkeypatch.setattr(live, "observe", lambda: seat(in_pytest=True))
    monkeypatch.setattr(live, "build_runtime", lambda name: runtime)
    tag = tmp_path / "panel_cycles" / "tag1"

    assert live.main(cycle, tag, list(DOCS), ["--acts", "live"]) == live.EXIT_USAGE
    assert not tag.exists()
    assert harness.paid() == 0


def test_the_command_line_writes_the_report_next_to_the_tag(
    tmp_path: Path, rig: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, _ = rig
    cycle = build_cycle(tmp_path)
    monkeypatch.setattr(live, "observe", lambda: seat())
    monkeypatch.setattr(live, "build_runtime", lambda name: runtime)
    tag = tmp_path / "panel_cycles" / "tag1"

    assert (
        live.main(cycle, tag, list(DOCS), ["--acts", "live"], results_root=tmp_path)
        == live.EXIT_OK
    )

    report = json.loads((tag / live.REPORT).read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert list(report)[0] == "provenance"
    assert report["provenance"]["units"].startswith("characters")
    assert report["provenance"]["code"]["instruments"]["act_replay_live"]
