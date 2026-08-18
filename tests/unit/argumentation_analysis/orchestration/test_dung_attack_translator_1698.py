"""#1698 — the Dung attack graph gets a translator, so its edges land on it.

Measured defect (issue #1698, 3 real corpora): every attack the central Dung
frame received had a target inside the argument inventory and a source
**outside** it — ``BOTH_in = 0`` on 3/3. The frame therefore behaved as *n*
isolated arguments: ``conflict_free`` returned the whole inventory and every
acceptance semantics returned one extension of size ``|arguments|``. Nothing
was ever rejected, under formal authority.

The cause is the producer, not the reasoner. ``_generate_attacks_from_args``
has exactly two branches and both mint a **fabricated** source::

    attacks.append([f"fallacy_{i}_{label}", target_arg])   # invoke_callables:3207
    attacks.append([f"CA: {text[:50]}", arg])              # invoke_callables:3224

Neither source is an inventory member, so ``BOTH_in = 0`` is the only value
this producer *can* yield — independently of the corpus.

The fix is a **sixth sibling** of an existing family of five, not an invention:
``structured_arg_translator`` already derives relations from the text, makes the
model cite them **by id** (``arg1``..``argN``) and drops any relation naming an
id outside the inventory. That is ``BOTH_in`` by construction, with nothing
fabricated. It was wired on bipolar / ABA / ASPIC / SetAF / weighted and absent
from Dung, social, probabilistic and EAF.

What these tests assert, and what they refuse to assert
-------------------------------------------------------
* They assert on **the graph that reaches the reasoner** (captured at the
  handler call), never on a log line. A ``caplog`` assertion would pass against
  a fix that only reworded a message.
* ``BOTH_in > 0`` is expressed as ``_retained_attacks`` returning the submitted
  edges — the same membership test the issue's probe ran on the real states.
* They do **not** assert that something is rejected: a corpus where nothing is
  defeated is a legitimate result. It is the structural *impossibility* of a
  rejection that is the defect. The rejection is measured on real corpora
  (DoD item 2), not here.

Anti-pendules under test (both were green before this change and must stay
green — they are guards, not deliverables):
* the attacker is **never** added to the argument inventory (a fallacy node
  would be an unattacked argument that always wins: "0 rejected on 8 nodes"
  would become "everything rejected on 37 nodes", the symmetrical false green);
* an attack graph supplied by the caller is never overridden.

Privacy HARD: synthetic atoms only (``Alpha`` / ``Beta`` / ``Gamma``), no corpus
tokens, no LLM call, no JVM.
"""

from __future__ import annotations

import sys
import types
from typing import Any, Dict, List

import pytest

from argumentation_analysis.orchestration.structured_arg_translator import (
    CAUSE_EVALUATED,
    CAUSE_NO_GENUINE_RELATIONS,
    CAUSE_TRANSLATOR_FAILED,
    CAUSE_TRANSLATOR_UNCONFIGURED,
    TranslatorUnconfigured,
    _validate_dung_attacks,
    translate_to_dung_attacks,
)

# ``asyncio_mode = auto`` (pytest.ini) — no per-test asyncio marker needed.


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _patch_llm(monkeypatch, payload: Dict[str, Any]) -> None:
    """Redirect the internal LLM call to return ``payload`` (no network)."""

    async def _fake(input_text: str, arguments: List[str], relation_kind: str):
        return payload

    monkeypatch.setattr(
        "argumentation_analysis.orchestration.structured_arg_translator."
        "_llm_extract_relations",
        _fake,
    )


def _patch_llm_raising(monkeypatch, exc: BaseException) -> None:
    async def _fake(input_text: str, arguments: List[str], relation_kind: str):
        raise exc

    monkeypatch.setattr(
        "argumentation_analysis.orchestration.structured_arg_translator."
        "_llm_extract_relations",
        _fake,
    )


def _fake_module(name: str, **attrs: Any) -> types.ModuleType:
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def _inject_fake_handlers(monkeypatch) -> List[Dict[str, Any]]:
    """Inject fake Tweety handlers for the 4 orphan axes; record their inputs.

    Returns the shared call log: one ``{"axis", "arguments", "attacks"}`` entry
    per handler invocation. This is the *effect* under test — the graph that
    actually reached the reasoner.
    """
    calls: List[Dict[str, Any]] = []

    class _FakeTweetyInitializer:
        pass

    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.tweety_initializer",
        _fake_module(
            "argumentation_analysis.agents.core.logic.tweety_initializer",
            TweetyInitializer=_FakeTweetyInitializer,
            # #1784: production now constructs the initializer via
            # ready_initializer() before building handlers.
            ready_initializer=lambda: _FakeTweetyInitializer(),
        ),
    )

    class _FakeAFHandler:
        def __init__(self, initializer: Any) -> None:
            self.initializer = initializer

        def analyze_multi_semantics(self, arguments, attacks, semantics):
            calls.append({"axis": "dung", "arguments": arguments, "attacks": attacks})
            return {"extensions": {sem: [list(arguments)] for sem in semantics}}

    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.af_handler",
        _fake_module(
            "argumentation_analysis.agents.core.logic.af_handler",
            AFHandler=_FakeAFHandler,
            SEMANTICS_REASONERS={"grounded": None, "preferred": None},
        ),
    )

    class _FakeSocialHandler:
        def __init__(self, initializer: Any) -> None:
            self.initializer = initializer

        def analyze_social_framework(self, args, attacks, votes):
            calls.append({"axis": "social", "arguments": args, "attacks": attacks})
            return {"extensions": [], "statistics": {}}

    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.social_handler",
        _fake_module(
            "argumentation_analysis.agents.core.logic.social_handler",
            SocialHandler=_FakeSocialHandler,
        ),
    )

    class _FakeEAFHandler:
        def __init__(self, initializer: Any) -> None:
            self.initializer = initializer

        def analyze_epistemic_framework(self, args, attacks, beliefs, semantics):
            calls.append({"axis": "eaf", "arguments": args, "attacks": attacks})
            return {"extensions": [], "statistics": {}}

    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.eaf_handler",
        _fake_module(
            "argumentation_analysis.agents.core.logic.eaf_handler",
            EAFHandler=_FakeEAFHandler,
        ),
    )

    class _FakeProbabilisticHandler:
        def analyze_probabilistic_framework(self, args, attacks, probs):
            calls.append(
                {"axis": "probabilistic", "arguments": args, "attacks": attacks}
            )
            return {"extensions": [], "statistics": {}}

    monkeypatch.setitem(
        sys.modules,
        "argumentation_analysis.agents.core.logic.probabilistic_handler",
        _fake_module(
            "argumentation_analysis.agents.core.logic.probabilistic_handler",
            ProbabilisticHandler=_FakeProbabilisticHandler,
        ),
    )
    return calls


# The inventory every wiring test runs on, plus a fallacy detection that the
# synthetic producer resolves — so ``_generate_attacks_from_args`` really does
# mint ``["fallacy_0_ad_hominem", "Alpha"]`` if it is still reached.
_ARGUMENTS = ["Alpha", "Beta", "Gamma"]


def _context_that_feeds_the_synthetic_producer() -> Dict[str, Any]:
    return {
        "phase_extract_output": {"arguments": list(_ARGUMENTS)},
        "phase_hierarchical_fallacy_output": {
            "fallacies": [{"type": "ad_hominem", "target_argument": "arg_1"}]
        },
    }


# The four orphan axes, with the capability name each records its cause under.
_AXES = [
    ("dung", "_invoke_dung_extensions", "dung_extensions"),
    ("social", "_invoke_social", "social_argumentation"),
    ("eaf", "_invoke_eaf", "epistemic_argumentation"),
    ("probabilistic", "_invoke_probabilistic", "probabilistic_argumentation"),
]


async def _run_axis(axis_fn_name: str, ctx: Dict[str, Any]) -> Any:
    from argumentation_analysis.orchestration import invoke_callables

    fn = getattr(invoke_callables, axis_fn_name)
    return await fn("source text", ctx)


# --------------------------------------------------------------------------
# 1. The validator — the anti-théâtre guard, id by id
# --------------------------------------------------------------------------


class TestValidateDungAttacks:
    def test_keeps_valid_pairs_mapped_to_canonical_text(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta", "arg3": "Gamma"}
        data = {
            "attacks": [
                {"source": "arg2", "target": "arg1", "rationale": "r"},
                {"source": "arg3", "target": "arg2", "rationale": "r"},
            ]
        }
        assert _validate_dung_attacks(data, arg_by_id) == [
            ["Beta", "Alpha"],
            ["Gamma", "Beta"],
        ]

    def test_drops_the_pair_whose_source_is_outside_the_inventory(self):
        """The exact shape the synthetic producer mints — and the defect."""
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {
            "attacks": [
                {"source": "fallacy_0_ad_hominem", "target": "arg1"},
                {"source": "CA: some counter", "target": "arg2"},
            ]
        }
        assert _validate_dung_attacks(data, arg_by_id) == []

    def test_drops_the_pair_whose_target_is_outside_the_inventory(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {"attacks": [{"source": "arg1", "target": "arg9"}]}
        assert _validate_dung_attacks(data, arg_by_id) == []

    def test_drops_self_attack(self):
        arg_by_id = {"arg1": "Alpha"}
        data = {"attacks": [{"source": "arg1", "target": "arg1"}]}
        assert _validate_dung_attacks(data, arg_by_id) == []

    def test_dedups_on_source_and_target(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {
            "attacks": [
                {"source": "arg1", "target": "arg2"},
                {"source": "arg1", "target": "arg2", "rationale": "again"},
            ]
        }
        assert _validate_dung_attacks(data, arg_by_id) == [["Alpha", "Beta"]]

    def test_direction_is_preserved_not_symmetrised(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        data = {
            "attacks": [
                {"source": "arg1", "target": "arg2"},
                {"source": "arg2", "target": "arg1"},
            ]
        }
        assert _validate_dung_attacks(data, arg_by_id) == [
            ["Alpha", "Beta"],
            ["Beta", "Alpha"],
        ]

    def test_tolerates_malformed_payloads(self):
        arg_by_id = {"arg1": "Alpha", "arg2": "Beta"}
        assert _validate_dung_attacks({}, arg_by_id) == []
        assert _validate_dung_attacks({"attacks": []}, arg_by_id) == []
        assert _validate_dung_attacks({"attacks": "nope"}, arg_by_id) == []
        assert _validate_dung_attacks({"attacks": [None, 3, "x"]}, arg_by_id) == []
        assert _validate_dung_attacks([], arg_by_id) == []  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# 2. The translator — the same discriminated cause contract as its 5 siblings
# --------------------------------------------------------------------------


class TestDungTranslatorCauseContract:
    async def test_empty_llm_output_is_no_genuine_relations(self, monkeypatch):
        _patch_llm(monkeypatch, {"attacks": []})
        out = await translate_to_dung_attacks("text", ["Alpha", "Beta"])
        assert out.relations == []
        assert out.cause == CAUSE_NO_GENUINE_RELATIONS

    async def test_all_fabricated_dropped_is_still_no_genuine_relations(
        self, monkeypatch
    ):
        _patch_llm(
            monkeypatch,
            {"attacks": [{"source": "phantom", "target": "ghost"}]},
        )
        out = await translate_to_dung_attacks("text", ["Alpha", "Beta"])
        assert out.relations == []
        assert out.cause == CAUSE_NO_GENUINE_RELATIONS

    async def test_genuine_pairs_are_evaluated(self, monkeypatch):
        _patch_llm(
            monkeypatch,
            {
                "attacks": [
                    {"source": "arg2", "target": "arg1"},
                    {"source": "arg1", "target": "arg9"},  # dropped (unknown)
                ]
            },
        )
        out = await translate_to_dung_attacks("text", ["Alpha", "Beta"])
        assert out.relations == [["Beta", "Alpha"]]
        assert out.cause == CAUSE_EVALUATED

    async def test_empty_inventory_short_circuits_without_calling_the_llm(
        self, monkeypatch
    ):
        called = {"n": 0}

        async def _fake(input_text, arguments, relation_kind):
            called["n"] += 1
            return {"attacks": [{"source": "arg1", "target": "arg2"}]}

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "_llm_extract_relations",
            _fake,
        )
        out = await translate_to_dung_attacks("text", [])
        assert out.relations == []
        assert out.cause == CAUSE_NO_GENUINE_RELATIONS
        assert called["n"] == 0

    async def test_unconfigured_is_not_collapsed_onto_no_relations(self, monkeypatch):
        _patch_llm_raising(monkeypatch, TranslatorUnconfigured("no key"))
        out = await translate_to_dung_attacks("text", ["Alpha", "Beta"])
        assert out.relations == []
        assert out.cause == CAUSE_TRANSLATOR_UNCONFIGURED

    async def test_a_raising_call_reports_translator_failed_with_its_type(
        self, monkeypatch
    ):
        _patch_llm_raising(monkeypatch, ValueError("boom"))
        out = await translate_to_dung_attacks("text", ["Alpha", "Beta"])
        assert out.relations == []
        assert out.cause == CAUSE_TRANSLATOR_FAILED
        assert out.error == "ValueError"


# --------------------------------------------------------------------------
# 3. The four orphan axes — measured on what reaches the reasoner
# --------------------------------------------------------------------------


class TestTheFabricatedGraphNoLongerReachesTheReasoner:
    """THE defect. Red before the fix: the synthetic producer still runs and
    hands the reasoner an edge whose source is not a node of the frame."""

    @pytest.mark.parametrize("axis,fn_name,capability", _AXES)
    async def test_nothing_is_submitted_when_no_genuine_relation_exists(
        self, monkeypatch, axis, fn_name, capability
    ):
        calls = _inject_fake_handlers(monkeypatch)
        _patch_llm(monkeypatch, {"attacks": []})  # translator finds nothing

        ctx = _context_that_feeds_the_synthetic_producer()
        await _run_axis(fn_name, ctx)

        submitted = [c for c in calls if c["axis"] == axis]
        assert len(submitted) == 1
        assert submitted[0]["attacks"] == [], (
            "an edge reached the reasoner although no genuine relation was "
            "derived — the synthetic producer is still wired"
        )

    @pytest.mark.parametrize("axis,fn_name,capability", _AXES)
    async def test_no_submitted_edge_has_a_source_outside_the_inventory(
        self, monkeypatch, axis, fn_name, capability
    ):
        """The invariant, stated positively: sources are inventory members."""
        calls = _inject_fake_handlers(monkeypatch)
        _patch_llm(monkeypatch, {"attacks": [{"source": "arg2", "target": "arg1"}]})

        ctx = _context_that_feeds_the_synthetic_producer()
        await _run_axis(fn_name, ctx)

        submitted = [c for c in calls if c["axis"] == axis][0]
        inventory = {str(a) for a in submitted["arguments"]}
        outside = [
            edge
            for edge in submitted["attacks"]
            if str(edge[0]) not in inventory or str(edge[1]) not in inventory
        ]
        assert not outside, f"{len(outside)} edge(s) not grounded in the inventory"

    @pytest.mark.parametrize("axis,fn_name,capability", _AXES)
    async def test_a_genuine_relation_is_submitted_with_both_endpoints_in(
        self, monkeypatch, axis, fn_name, capability
    ):
        """``BOTH_in > 0`` — the same membership test the #1698 probe ran."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _retained_attacks,
        )

        calls = _inject_fake_handlers(monkeypatch)
        _patch_llm(monkeypatch, {"attacks": [{"source": "arg2", "target": "arg1"}]})

        ctx = _context_that_feeds_the_synthetic_producer()
        await _run_axis(fn_name, ctx)

        submitted = [c for c in calls if c["axis"] == axis][0]
        assert submitted["attacks"] == [["Beta", "Alpha"]]
        both_in = _retained_attacks(submitted["arguments"], submitted["attacks"])
        assert len(both_in) == 1

    @pytest.mark.parametrize("axis,fn_name,capability", _AXES)
    async def test_the_cause_is_discriminated_in_context(
        self, monkeypatch, axis, fn_name, capability
    ):
        """An empty graph carries *why* it is empty — never a bare ``[]``."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _structured_arg_cause,
        )

        _inject_fake_handlers(monkeypatch)

        _patch_llm(monkeypatch, {"attacks": []})
        ctx = _context_that_feeds_the_synthetic_producer()
        await _run_axis(fn_name, ctx)
        assert _structured_arg_cause(ctx, capability) == CAUSE_NO_GENUINE_RELATIONS

        _patch_llm_raising(monkeypatch, TranslatorUnconfigured("no key"))
        ctx = _context_that_feeds_the_synthetic_producer()
        await _run_axis(fn_name, ctx)
        assert _structured_arg_cause(ctx, capability) == CAUSE_TRANSLATOR_UNCONFIGURED

        _patch_llm_raising(monkeypatch, RuntimeError("boom"))
        ctx = _context_that_feeds_the_synthetic_producer()
        await _run_axis(fn_name, ctx)
        assert _structured_arg_cause(ctx, capability) == CAUSE_TRANSLATOR_FAILED


class TestTheDerivationIsSharedNotRepeated:
    """The four axes reason over the same inventory, so they translate once.

    Not an optimisation detail: four independent translations of the same text
    could disagree, and four different Dung graphs inside one analysis would be
    an incoherence no reader could see.
    """

    async def test_two_axes_in_one_context_translate_once(self, monkeypatch):
        _inject_fake_handlers(monkeypatch)
        calls = {"n": 0}

        async def _fake(input_text, arguments, relation_kind):
            calls["n"] += 1
            return {"attacks": [{"source": "arg2", "target": "arg1"}]}

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.structured_arg_translator."
            "_llm_extract_relations",
            _fake,
        )
        ctx = _context_that_feeds_the_synthetic_producer()
        await _run_axis("_invoke_dung_extensions", ctx)
        await _run_axis("_invoke_social", ctx)
        assert calls["n"] == 1


# --------------------------------------------------------------------------
# 4. Anti-pendules — green before AND after (guards, not deliverables)
# --------------------------------------------------------------------------


class TestTheAttackerIsNeverPromotedToANode:
    """Adding ``fallacy_*`` to ``arguments`` would turn "0 rejected on 8 nodes"
    into "everything rejected on 37 nodes" — the symmetrical false green named
    in the issue. The inventory submitted must stay the extracted one."""

    @pytest.mark.parametrize("axis,fn_name,capability", _AXES)
    async def test_the_submitted_inventory_is_exactly_the_extracted_one(
        self, monkeypatch, axis, fn_name, capability
    ):
        calls = _inject_fake_handlers(monkeypatch)
        _patch_llm(monkeypatch, {"attacks": [{"source": "arg2", "target": "arg1"}]})

        ctx = _context_that_feeds_the_synthetic_producer()
        await _run_axis(fn_name, ctx)

        submitted = [c for c in calls if c["axis"] == axis][0]
        assert list(submitted["arguments"]) == _ARGUMENTS
        assert not [a for a in submitted["arguments"] if str(a).startswith("fallacy_")]


class TestACallerSuppliedGraphIsNeverOverridden:
    """``context["attacks"]`` keeps precedence on the three axes that honour it
    (``_invoke_dung_extensions`` has never read that key and still does not —
    changing that is a separate decision, not this fix)."""

    @pytest.mark.parametrize(
        "axis,fn_name",
        [
            ("social", "_invoke_social"),
            ("eaf", "_invoke_eaf"),
            ("probabilistic", "_invoke_probabilistic"),
        ],
    )
    async def test_explicit_attacks_win(self, monkeypatch, axis, fn_name):
        calls = _inject_fake_handlers(monkeypatch)
        _patch_llm(monkeypatch, {"attacks": [{"source": "arg2", "target": "arg1"}]})

        ctx = _context_that_feeds_the_synthetic_producer()
        ctx["attacks"] = [["Gamma", "Beta"]]
        await _run_axis(fn_name, ctx)

        submitted = [c for c in calls if c["axis"] == axis][0]
        assert submitted["attacks"] == [["Gamma", "Beta"]]
