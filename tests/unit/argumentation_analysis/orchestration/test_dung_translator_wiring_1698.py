"""#1698 — the four orphan Dung-family axes derive attacks via the
id-validated translator, never from the synthetic generator.

Measured history (issue #1698): ``_generate_attacks_from_args`` has exactly two
branches and both mint a FABRICATED source (``fallacy_{i}_{label}`` /
``CA: {…}``) while targets are always inventory members — so ``BOTH_in = 0``
was the only result that producer could ever render, on every corpus, for
Dung/social/probabilistic/EAF (the four axes with no translator). SetAF and
weighted already go through id-validated translators; this PR gives the four
orphans the same sixth brother (``translate_to_dung_attacks``).

Contracts pinned here (each red-before-fix was EXECUTED on the pre-fix tree;
see the PR for the triage):

1. ``test_translator_edges_reach_the_handler`` (RED before, per axis) —
   id-validated pairs derived from the text reach the handler's attack
   argument. Before: the submitted graph was the synthetic producer's output
   (empty with no fallacies in context) — an assertion about the SUBMITTED
   GRAPH, not a signature change.
2. ``test_arbitrated_empty_yields_empty_graph_and_cause`` (RED before) — when
   the translator ran and found nothing (``no_genuine_relations``), the graph
   submitted is empty AND the discriminated cause is written into the pipeline
   context. Before: no cause key was ever written for these axes.
3. ``test_no_synthetic_source_survives_an_arbitration`` (RED before) — the
   anti-pendule: with fallacies in context and the arbitrator answering
   "none", NO ``fallacy_*`` edge is submitted. Before: the synthetic producer
   minted them.
4. Counter-controls, GREEN before AND after (forbid the false fix):
   - ``test_caller_provided_attacks_pass_through`` — genuine caller input is
     never overridden (the 3 axes that already honoured ``context["attacks"]``).
   - ``test_honest_absent_door_untouched`` — JVM-down still returns the
     degraded honest-absent dict on the Dung axis.

The behavioural verdict (``BOTH_in > 0`` + a semantics that excludes
something, on the 3 real corpora) is NOT testable hermetically — it needs the
Tweety reasoner — and lives in the #1698 measurement script + its real-run
artifacts (gitignored).
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

INVOKE = "argumentation_analysis.orchestration.invoke_callables"
LOGIC = "argumentation_analysis.agents.core.logic"

_ARGS = [
    "Claim alpha: the tram line will save the district money",
    "Claim beta: the tram line will cost far more than it returns",
    "Claim gamma: the district budget already runs a deficit",
]
# arg9 does not exist in the 3-argument inventory → dropped at validation.
_LLM_VALID = (
    '{"attacks": [{"source": "arg1", "target": "arg2", "rationale": "r"}, '
    '{"source": "arg9", "target": "arg1", "rationale": "fabricated id"}]}'
)
_LLM_EMPTY = '{"attacks": []}'
_EXPECTED_PAIR = [_ARGS[0], _ARGS[1]]

# axis key in the pipeline context → (invoke fn, handler module, handler class,
# analyze method name, needs TweetyInitializer, runs _annotate_attack_retention)
_AXES = {
    "dung_extensions": (
        "_invoke_dung_extensions",
        "af_handler",
        "AFHandler",
        "analyze_multi_semantics",
    ),
    "probabilistic_argumentation": (
        "_invoke_probabilistic",
        "probabilistic_handler",
        "ProbabilisticHandler",
        "analyze_probabilistic_framework",
    ),
    "social_argumentation": (
        "_invoke_social",
        "social_handler",
        "SocialHandler",
        "analyze_social_framework",
    ),
    "epistemic_argumentation": (
        "_invoke_eaf",
        "eaf_handler",
        "EAFHandler",
        "analyze_epistemic_framework",
    ),
}

# The three axes that already honoured caller-provided attacks before this PR
# (the Dung site did not — it is out of the green-before counter-control).
_PASSTHROUGH_AXES = (
    "probabilistic_argumentation",
    "social_argumentation",
    "epistemic_argumentation",
)


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _resp(payload: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=payload))]
    )


@contextmanager
def _translator_llm(payload: str):
    """Patch the LLM call the translator performs.

    ``_llm_extract_relations`` lazy-imports its helpers FROM invoke_callables
    at call time (lesson #1742: patch the site of definition, not a facade),
    so patching these module attributes reaches the translator.
    """
    with (
        patch(f"{INVOKE}._get_openai_client", return_value=(MagicMock(), "m")),
        patch(f"{INVOKE}._get_determinism_params", return_value={}),
        patch(
            f"{INVOKE}._guarded_chat_completion",
            new=AsyncMock(return_value=_resp(payload)),
        ),
        patch(
            f"{INVOKE}._parse_json_from_llm",
            side_effect=lambda raw: __import__("json").loads(raw),
        ),
    ):
        yield


@contextmanager
def _handler_capturing(axis_key: str, handler_output: dict | None = None):
    """Patch the axis's Tweety handler; yield the capture of `attacks`."""
    _, mod_name, cls, method = _AXES[axis_key]
    handler = MagicMock()
    getattr(handler, method).return_value = dict(handler_output or {})
    with (
        patch(f"{LOGIC}.{mod_name}.{cls}", return_value=handler),
        patch(
            f"{LOGIC}.tweety_initializer.TweetyInitializer", return_value=MagicMock()
        ),
    ):
        yield handler


def _submitted_attacks(axis_key: str, handler: MagicMock):
    _, _, _, method = _AXES[axis_key]
    args = getattr(handler, method).call_args[0]
    return args[1]  # (arguments, ATTACKS, ...) in every one of the four sites


def _base_context(**extra) -> dict:
    """Context carrying the inventory where EVERY site reads it.

    The three sibling sites read top-level ``context["arguments"]`` first; the
    Dung site reads ONLY ``_extract_arguments_from_context`` (phase outputs,
    never the top-level key — measured pre-fix: a top-level-only context made
    the Dung graph run over ``["corpus-text-placeholder"]``). Providing both
    exercises each site through its real argument door.
    """
    ctx = {
        "arguments": list(_ARGS),
        "phase_extract_output": {"arguments": list(_ARGS)},
        "_state_object": None,
    }
    ctx.update(extra)
    return ctx


def _invoke(axis_key: str, context: dict) -> dict:
    from importlib import import_module

    mod = import_module(INVOKE)
    fn = getattr(mod, _AXES[axis_key][0])
    return _run(fn("corpus-text-placeholder", context))


# ---------------------------------------------------------------------------
# 1 — translator-derived edges reach the handler (RED before the wiring)
# ---------------------------------------------------------------------------


class TestTranslatorEdgesReachTheHandler:

    @pytest.mark.parametrize("axis_key", list(_AXES))
    def test_translator_edges_reach_the_handler(self, axis_key):
        """Id-validated pairs are the graph actually submitted to the handler."""
        context = _base_context()
        with _translator_llm(_LLM_VALID), _handler_capturing(
            axis_key, {"extensions": {"grounded": [[]]}}
        ) as handler:
            _invoke(axis_key, context)
        submitted = _submitted_attacks(axis_key, handler)
        assert _EXPECTED_PAIR in submitted, (
            f"[{axis_key}] the handler was not handed the id-validated pair "
            f"derived from the text — the Dung-family translator wiring "
            "(#1698) is not in effect"
        )


# ---------------------------------------------------------------------------
# 2 — arbitrated empty: empty graph + discriminated cause (RED before)
# ---------------------------------------------------------------------------


class TestArbitratedEmptyYieldsCause:

    @pytest.mark.parametrize("axis_key", list(_AXES))
    def test_arbitrated_empty_yields_empty_graph_and_cause(self, axis_key):
        """Translator ran, found nothing → [] submitted + cause written."""
        context = _base_context()
        with _translator_llm(_LLM_EMPTY), _handler_capturing(
            axis_key, {"extensions": {"grounded": [[]]}}
        ) as handler:
            _invoke(axis_key, context)
        submitted = _submitted_attacks(axis_key, handler)
        cause_key = f"_structured_arg_cause:{axis_key}"
        assert submitted == [], (
            f"[{axis_key}] arbitrator found no genuine relations yet the "
            f"submitted graph is not empty: {submitted!r}"
        )
        assert context.get(cause_key) == "no_genuine_relations", (
            f"[{axis_key}] discriminated cause not written to context — "
            "an empty graph without its cause is indistinguishable from a "
            "silent producer (#1019)"
        )


# ---------------------------------------------------------------------------
# 3 — anti-pendule: no synthetic source survives an arbitration (RED before)
# ---------------------------------------------------------------------------


class TestNoSyntheticSourceSurvivesArbitration:

    @pytest.mark.parametrize("axis_key", list(_AXES))
    def test_no_synthetic_source_survives_an_arbitration(self, axis_key):
        """Fallacies in context + arbitrator says 'none' → no fallacy_* edge.

        This forbids the false fix the issue names: minting fallacy nodes (or
        keeping the synthetic producer as a fallback) would produce edges that
        drop 100% at the handler guard — the exact inert-graph defect.
        """
        context = _base_context(
            phase_hierarchical_fallacy_output={
                "fallacies": [
                    # arg_N ids as minted by shared_state._generate_id (#1629).
                    {"type": "hasty", "target_argument": "arg_1"},
                    {"type": "appeal", "target_argument": "arg_2"},
                ]
            },
        )
        with _translator_llm(_LLM_EMPTY), _handler_capturing(
            axis_key, {"extensions": {"grounded": [[]]}}
        ) as handler:
            _invoke(axis_key, context)
        submitted = _submitted_attacks(axis_key, handler)
        synthetic = [
            a
            for a in submitted
            if isinstance(a, (list, tuple)) and str(a[0]).startswith("fallacy_")
        ]
        assert not synthetic, (
            f"[{axis_key}] synthetic fallacy_* sources reached the submitted "
            f"graph alongside the translator's arbitration — mixing producers "
            "forbids attributing an edge to its source (#1698 anti-pendule)"
        )


# ---------------------------------------------------------------------------
# 4 — counter-controls, GREEN before AND after (forbid the false fix)
# ---------------------------------------------------------------------------


class TestCounterControls:

    @pytest.mark.parametrize("axis_key", _PASSTHROUGH_AXES)
    def test_caller_provided_attacks_pass_through(self, axis_key):
        """Genuine caller input is never overridden by the translator.

        Green before this PR (these three sites already read
        ``context["attacks"]``) and must stay green after: the wiring only
        fires when the context brings nothing genuine.
        """
        genuine = [[_ARGS[2], _ARGS[0]]]
        context = _base_context(attacks=list(genuine))
        # LLM would propose a DIFFERENT pair — the caller's must win anyway.
        with _translator_llm(_LLM_VALID), _handler_capturing(
            axis_key, {"extensions": {"grounded": [[]]}}
        ) as handler:
            _invoke(axis_key, context)
        submitted = _submitted_attacks(axis_key, handler)
        assert submitted == genuine, (
            f"[{axis_key}] caller-provided genuine attacks were overridden: "
            f"{submitted!r}"
        )

    def test_honest_absent_door_untouched(self):
        """JVM down → degraded honest-absent dict on the Dung axis.

        Green before and after: the honest-absent door is not modified by the
        translator wiring (#1698 DoD).
        """
        context = _base_context()
        with _translator_llm(_LLM_VALID):
            with patch(
                f"{LOGIC}.af_handler.AFHandler",
                side_effect=RuntimeError("no JVM"),
            ):
                result = _invoke("dung_extensions", context)
        assert result.get("degraded") is True
        assert result.get("semantics") == "unavailable"
        assert "honest-absent" in result.get("note", "")
