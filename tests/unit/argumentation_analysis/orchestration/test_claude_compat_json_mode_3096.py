"""#3096 — born-red witnesses: the measured Anthropic wire contract reaches
every JSON-mode site through ONE decision.

The dispatch's DoD (verbatim): "Born red on 0607d05d9: a loopback endpoint
that answers ``json_object`` with Anthropic's 400 body (and ``json_schema``
strict with a valid reply) → the five translators must come out ``evaluated``.
Today they come out ``translator_failed``. Stakes: the injected ``llm_call``
raises → the phase is degraded, with the error in ``state.errors``. Today it
says ``completed``, with nothing recorded. Mutation: restore ``json_object``
at the translator site → the translator witness goes red."

The loopback below speaks the contract measured on the real endpoint
(``https://api.anthropic.com/v1/``, probes 20/10, claude-haiku-5-5):

* ``response_format {"type": "json_object"}`` → 400 "Input should be
  'json_schema'";
* ``temperature`` in the body → 400 "`temperature` is deprecated for this
  model" (the silent cause of the empty-stakes phase that reported
  ``completed``);
* ``json_schema`` (strict) → 200 with a valid reply for the named schema.

On the pre-fix tree the translators send ``json_object`` → the loopback's 400
raises inside ``_guarded_chat_completion`` → cause ``translator_failed``; the
stakes extractor sends its hardcoded ``temperature=0.3`` → 400 → swallowed by
the broad ``except`` → "completed" with zero stakes and nothing recorded.
Both witnesses are therefore born red on 0607d05d9 (verified by stash: red
pre-fix, green post-fix).

The loopback is classified as the anthropic row of the decision table by
pointing ``_ANTHROPIC_MARKER`` at its host:port — the same classification the
real base_url gets from containing ``api.anthropic.com``.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List

import pytest

from argumentation_analysis.core import endpoint_compat
from argumentation_analysis.orchestration import invoke_callables as ic
from argumentation_analysis.orchestration import structured_arg_translator as sat
from argumentation_analysis.orchestration.state_writers import (
    _write_probabilistic_to_state,
)

# --- The measured Anthropic error bodies -----------------------------------

_ANTHROPIC_400_JSON_OBJECT = {
    "error": {
        "type": "invalid_request_error",
        "message": "response_format.type: Input should be 'json_schema'.",
    }
}
_ANTHROPIC_400_TEMPERATURE = {
    "error": {
        "type": "invalid_request_error",
        "message": "`temperature` is deprecated for this model.",
    }
}


def _completion(content: str) -> Dict[str, Any]:
    """A minimal valid chat-completion reply the OpenAI SDK can parse."""
    return {
        "id": "chatcmpl-loopback-3096",
        "object": "chat.completion",
        "created": 1770000000,
        "model": "loopback-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    }


# Valid strict-schema replies, one per schema name. Every id cites arg1/arg2
# — the inventory two arguments build — so the anti-theatre validators keep
# the relation instead of dropping it as fabricated.
_RELATION_REPLIES: Dict[str, str] = {
    "structured_arg_supports": json.dumps(
        {
            "supports": [
                {
                    "source": "arg1",
                    "target": "arg2",
                    "rationale": "the first claim grounds the second",
                }
            ]
        }
    ),
    "structured_arg_contraries": json.dumps(
        {
            "contraries": [
                {
                    "assumption": "arg1",
                    "contrary": "the transport cost stays local",
                    "rationale": "direct negation of the assumption",
                }
            ]
        }
    ),
    "structured_arg_aspic_rules": json.dumps(
        {
            "rules": [
                {
                    "premises": ["arg1"],
                    "conclusion": "arg2",
                    "name": "rule1",
                    "rationale": "defeasible inference",
                }
            ],
            "contradictions": [
                {
                    "attacker": "arg2",
                    "target": "arg1",
                    "rationale": "reason against",
                }
            ],
            "undercuts": [
                {
                    "attacker": "arg2",
                    "target_rule": "rule1",
                    "rationale": "contests the inference itself",
                }
            ],
        }
    ),
    "structured_arg_setaf_attacks": json.dumps(
        {
            "attacks": [
                {
                    "attackers": ["arg1"],
                    "target": "arg2",
                    "rationale": "jointly defeats",
                }
            ]
        }
    ),
    "structured_arg_dung_attacks": json.dumps(
        {
            "attacks": [
                {
                    "source": "arg1",
                    "target": "arg2",
                    "rationale": "defeats the conclusion",
                }
            ]
        }
    ),
    "structured_arg_weighted_attacks": json.dumps(
        {
            "attacks": [
                {
                    "source": "arg1",
                    "target": "arg2",
                    "weight": 0.8,
                    "rationale": "strong defeat",
                }
            ]
        }
    ),
}

# A prompt-only JSON call (anthropic row without a schema — the stakes shape)
# gets a valid stakes reply.
_STAKES_REPLY = json.dumps(
    {
        "stakes": [
            {
                "stake_type": "political",
                "description": "who decides regional transport funding",
                "evidence_indices": [0],
            }
        ],
        "stakeholders": [
            {
                "name": "Speaker_A",
                "role": "speaker",
                "stance": "for",
                "evidence_indices": [0],
            }
        ],
        "rhetorical_register": "legitimation",
        "discursive_arena": "parliamentary debate",
    }
)


class _LoopbackHandler(BaseHTTPRequestHandler):
    """Answers POSTs with the measured Anthropic wire contract."""

    def do_POST(self) -> None:  # noqa: N802 — http.server API
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {}
        self.server.requests.append(body)  # type: ignore[attr-defined]
        response_format = body.get("response_format") or {}
        if response_format.get("type") == "json_object":
            self._send(400, _ANTHROPIC_400_JSON_OBJECT)
            return
        if "temperature" in body:
            self._send(400, _ANTHROPIC_400_TEMPERATURE)
            return
        if response_format.get("type") == "json_schema":
            name = (response_format.get("json_schema") or {}).get("name", "")
            content = _RELATION_REPLIES.get(name, "{}")
        else:
            content = _STAKES_REPLY
        self._send(200, _completion(content))

    def _send(self, code: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args: Any) -> None:  # silence the test log
        pass


class _LoopbackServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.requests: List[Dict[str, Any]] = []


@pytest.fixture()
def anthropic_like(monkeypatch: pytest.MonkeyPatch) -> _LoopbackServer:
    """An endpoint speaking the measured Anthropic contract, on localhost.

    ``_ANTHROPIC_MARKER`` is pointed at the server's host:port so the ONE
    decision classifies it in the anthropic row — the same classification the
    real base_url gets from containing ``api.anthropic.com``.
    """
    server = _LoopbackServer(("127.0.0.1", 0), _LoopbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-3096")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", "loopback-model")
    monkeypatch.setattr(endpoint_compat, "_ANTHROPIC_MARKER", f"127.0.0.1:{port}")
    yield server
    server.shutdown()
    server.server_close()


_ARGS = [
    "The reform reduces regional inequalities.",
    "Cities absorb most of the transport cost.",
]

# The five formal-axis translators + the sixth sibling (dung attacks, feeding
# the probabilistic axis) — all six go through the same JSON-mode decision
# site inside _llm_extract_relations.
_TRANSLATORS = [
    ("bipolar", sat.translate_to_bipolar_supports),
    ("aba", sat.translate_to_aba_contraries),
    ("aspic", sat.translate_to_aspic_rules),
    ("setaf", sat.translate_to_setaf_attacks),
    ("weighted", sat.translate_to_weighted_attacks),
    ("dung", sat.translate_to_dung_attacks),
]


class TestTranslatorsThroughJsonSchema:
    """The translators reach ``evaluated`` on an endpoint that 400s json_object.

    Born red on 0607d05d9: every site sent ``json_object`` unconditionally →
    the loopback's 400 → ``translator_failed`` on all six.
    """

    @pytest.mark.parametrize("axis", [name for name, _fn in _TRANSLATORS])
    async def test_translator_evaluated(
        self, anthropic_like: _LoopbackServer, axis: str
    ) -> None:
        fn = dict(_TRANSLATORS)[axis]
        result = await fn("Source text excerpt.", _ARGS)
        assert (
            result.cause == sat.CAUSE_EVALUATED
        ), f"{axis}: cause={result.cause} error={getattr(result, 'error', '')}"
        assert result.relations, f"{axis}: no relation survived validation"

    async def test_every_call_used_json_schema_strict(
        self, anthropic_like: _LoopbackServer
    ) -> None:
        """The wire form actually sent is json_schema + strict, per name."""
        for _axis, fn in _TRANSLATORS:
            await fn("Source text excerpt.", _ARGS)
        assert anthropic_like.requests, "the loopback saw no request"
        for body in anthropic_like.requests:
            rf = body.get("response_format") or {}
            assert rf.get("type") == "json_schema", f"response_format sent: {rf!r}"
            assert (rf.get("json_schema") or {}).get("strict") is True
            assert (rf.get("json_schema") or {}).get("name") in _RELATION_REPLIES


class TestMutationControl:
    """The witness sees the DECISION, not a passing shape by accident."""

    async def test_restored_json_object_goes_red(
        self, anthropic_like: _LoopbackServer, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mutation: the decision answers json_object again → translator_failed."""
        monkeypatch.setattr(
            endpoint_compat,
            "json_response_format",
            lambda base_url, schema_name=None, schema=None: {"type": "json_object"},
        )
        result = await sat.translate_to_bipolar_supports("Source text excerpt.", _ARGS)
        assert result.cause == sat.CAUSE_TRANSLATOR_FAILED


class _FakeState:
    """The minimum _invoke_stakes_extractor touches on a state object."""

    def __init__(self) -> None:
        self.identified_arguments = {
            "arg_1": _ARGS[0],
            "arg_2": _ARGS[1],
        }
        self.argument_provenance: Dict[str, Dict[str, Any]] = {}
        self.raw_text = "Source text excerpt."
        self.source_metadata: Dict[str, str] = {}
        self.stakes_and_stakeholders: Dict[str, Any] = {}
        self.deanonymized = False
        self.errors: List[Dict[str, Any]] = []
        self.coverage: List[Any] = []

    def log_error(self, agent_name: str, message: str) -> str:
        entry = {
            "id": f"error_{len(self.errors)}",
            "agent_name": agent_name,
            "message": message,
        }
        self.errors.append(entry)
        return entry["id"]

    def record_analysis_coverage(self, *args: Any, **kwargs: Any) -> None:
        self.coverage.append((args, kwargs))


class TestStakesFailLoud:
    """An LLM failure degrades the phase and records the error (born red).

    On 0607d05d9 the raising call was swallowed by the extractor's broad
    ``except`` → the phase reported ``completed`` with zero stakes, nothing in
    ``state.errors``.
    """

    async def test_raising_llm_call_degrades_and_records(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _FakeState()

        async def _raising_call(client: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("loopback exploded (injected 3096)")

        monkeypatch.setattr(
            ic, "_get_openai_client", lambda: (object(), "loopback-model")
        )
        monkeypatch.setattr(ic, "_guarded_chat_completion", _raising_call)
        output = await ic._invoke_stakes_extractor(
            "Source text excerpt.",
            {
                "_state_object": state,
            },
        )
        assert output.get("degraded") is True, f"phase output not degraded: {output!r}"
        assert "stakes extraction" in str(output.get("degraded_reason", ""))
        recorded = [e for e in state.errors if e.get("agent_name") == "StakesExtractor"]
        assert recorded, f"no StakesExtractor entry in state.errors: {state.errors!r}"

    async def test_temperature_never_reaches_anthropic_like_endpoint(
        self, anthropic_like: _LoopbackServer
    ) -> None:
        """End-to-end: the stakes call succeeds on an endpoint that 400s it.

        The loopback rejects ``temperature`` with the measured 400; the fixed
        path strips it (``sampling_kwargs``) and the extraction completes. On
        0607d05d9 the hardcoded 0.3 died on this 400 and the phase still said
        ``completed`` with zero stakes.
        """
        state = _FakeState()
        output = await ic._invoke_stakes_extractor(
            "Source text excerpt.",
            {
                "_state_object": state,
            },
        )
        assert "degraded" not in output, f"unexpectedly degraded: {output!r}"
        assert output.get("stakes"), "no stakes extracted from a valid reply"
        assert anthropic_like.requests, "the loopback saw no stakes request"
        stakes_call = next(
            (
                b
                for b in anthropic_like.requests
                if (b.get("response_format") or {}).get("type") != "json_schema"
            ),
            None,
        )
        assert (
            stakes_call is not None
        ), "no prompt-only stakes call reached the loopback"
        assert (
            "temperature" not in stakes_call
        ), f"temperature reached the endpoint: {stakes_call!r}"


class TestDecisionTable:
    """Pure controls over the ONE decision (no network)."""

    def test_openai_compatible_keeps_json_object(self) -> None:
        fmt = endpoint_compat.json_response_format(
            "https://openrouter.ai/api/v1/",
            "any_name",
            {"type": "object"},
        )
        assert fmt == {"type": "json_object"}

    def test_anthropic_with_schema_gets_strict_json_schema(self) -> None:
        schema = {"type": "object", "properties": {}, "required": []}
        fmt = endpoint_compat.json_response_format(
            "https://api.anthropic.com/v1/", "n", schema
        )
        assert fmt == {
            "type": "json_schema",
            "json_schema": {"name": "n", "schema": schema, "strict": True},
        }

    def test_anthropic_without_schema_is_prompt_only(self) -> None:
        fmt = endpoint_compat.json_response_format("https://api.anthropic.com/v1/")
        assert fmt is None

    def test_sampling_kwargs_strips_temperature_keeps_seed(self) -> None:
        kept = endpoint_compat.sampling_kwargs(
            "https://api.anthropic.com/v1/", {"temperature": 0.3, "seed": 42}
        )
        assert kept == {"seed": 42}

    def test_sampling_kwargs_keeps_everything_on_openai_compatible(self) -> None:
        kept = endpoint_compat.sampling_kwargs(
            "https://openrouter.ai/api/v1/", {"temperature": 0.3, "seed": 42}
        )
        assert kept == {"temperature": 0.3, "seed": 42}


class TestProbabilisticSourceLabeled:
    """Item 3 — the 0.5 defaults' source is named in the state entry.

    Born red on 0607d05d9: the writer passed no such parameter, so the entry
    never named where its numbers came from.
    """

    def _fake_state(self) -> Any:
        class _S:
            def __init__(self) -> None:
                self.probabilistic_results: List[Dict[str, Any]] = []

            def add_probabilistic_result(self, arguments, acceptance_probs, **kwargs):
                entry = {
                    "id": f"prob_{len(self.probabilistic_results)}",
                    "arguments": arguments,
                    "acceptance_probabilities": acceptance_probs,
                }
                # Mirrors the real state method: optional fields are stored
                # only when set (None = honest absence, not a stored None).
                source = kwargs.pop("probabilities_source", None)
                if source is not None:
                    entry["probabilities_source"] = source
                entry.update(kwargs)
                self.probabilistic_results.append(entry)
                return entry["id"]

        return _S()

    def test_default_prior_is_labeled(self) -> None:
        state = self._fake_state()
        _write_probabilistic_to_state(
            {
                "arguments": ["arg_1", "arg_2"],
                "acceptance_probabilities": {"arg_1": 0.5, "arg_2": 0.5},
                "probabilities_source": "default_0.5",
            },
            state,
            {},
        )
        assert state.probabilistic_results, "no probabilistic entry written"
        assert (
            state.probabilistic_results[-1].get("probabilities_source") == "default_0.5"
        )

    def test_absent_source_stays_absent(self) -> None:
        state = self._fake_state()
        _write_probabilistic_to_state(
            {
                "arguments": ["arg_1"],
                "acceptance_probabilities": {"arg_1": 0.7},
            },
            state,
            {},
        )
        entry = state.probabilistic_results[-1]
        assert "probabilities_source" not in entry, f"unexpected source key: {entry!r}"
