"""#2850 — a long document is analysed on its opening only: the born-red
coverage test.

The audit's father defect, one sentence: a head window, or the first N
items in insertion order, stands for the document. This test pins the DoD
the repair will be held to — on a synthetic ~60k-character document with a
distinct argumentative marker in each third, the analysis state must hold,
for EVERY third, at least one analysed unit AND one specialist result
reaching that third's marker.

Deterministic by construction (0 paid calls):

- the only LLM the pipeline reaches through
  ``_guarded_chat_completion`` is a fake that reads the prompt it is GIVEN,
  extracts the ``ARGT<n>`` markers present in it, and answers the
  extraction JSON carrying exactly those markers — a faithful model would
  do the same: it cannot extract a marker it never received;
- the API-key environment is stripped for the run, so no other path can
  egress;
- the two paths no other fake reaches — the agentic virtue layer's own sync
  client, and the local-LLM availability probe — are answered by the same
  faithful model and by "no local endpoint", respectively (measured before
  the fakes: 2 POSTs to api.openai.com and 1 GET to localhost:5001);
- everything else (heuristics, JVM, scoring) is deterministic.

WHY IT IS RED AT BIRTH (measured on main at birth): the only LLM extraction
reads ``selected_text(input_text, 3000)`` — a window that carries the first
third's marker and no other, so the LLM units carry ``ARGT1`` only. The
heuristic whole-text reader DOES produce units over all thirds (they land
in the same ``identified_arguments`` key — the two-producers-under-one-key
defect), but no specialist ever touches them: on the birth run,
``argument_quality_scores`` held ``arg_1`` alone. The specialist assertion
below therefore fails for thirds 2 and 3 — audit result 2 (0 of 311),
reproduced deterministically.

WHY XFAIL-STRICT AND NOT A HARD RED: a hard red would break the gate for
every unrelated PR until the coverage layer lands. ``xfail(strict=True)``
keeps the contract in the gate, red at birth inside the xfail, and the day
the repair makes it pass, strict turns the XPASS into a failure that forces
this marker — and the debt rows in the census guard — to be revisited.

Privacy: the document is invented prose, no dataset content (#2850 DoD).
"""

import asyncio
import json
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole

INVOKE_PATH = "argumentation_analysis.orchestration.invoke_callables"

_MARKER = re.compile(r"ARGT([123])")

# Neutral invented filler paragraphs (no dataset content). Each third of the
# document is ordinary prose carrying exactly one marked argument.
_FILLER = (
    "The harbour commission publishes its maintenance ledger every spring, "
    "and every spring the same entries reappear with the same amounts. The "
    "cranes are inspected, the breakwater is patched, the ferry ramps are "
    "greased, and the ledger closes with a note about next year's budget. "
    "Nobody disputes the entries; nobody reads them either. "
)

_MARKED = (
    "ARGT{n} The harbour ledger's dredging line has tripled since 2019 "
    "while the channel depth stayed the same, so the dredging budget "
    "deserves a public explanation. "
)


def _build_document() -> str:
    """~60k chars, one marker per third. Marker 1 sits inside the head
    (~500 chars) so the #1909 argumentativity router — itself a head reader
    — lets the argument-dependent phases run; markers 2 and 3 sit at ~30k
    and ~55k, past every reading window."""
    parts: list[str] = []
    total = 0

    def fill_to(target: int) -> None:
        nonlocal total
        while total < target:
            parts.append(_FILLER)
            total += len(_FILLER)

    for n, target in enumerate((500, 30000, 55000), start=1):
        fill_to(target)
        parts.append(_MARKED.format(n=n))
        total += len(_MARKED)
    fill_to(60000)
    return "".join(parts)


def _marker_payload(messages) -> str:
    """The faithful model's answer, read off the prompt it is GIVEN: the
    markers present in it, and no others. One rule, every call shape."""
    user = " ".join(str(m.get("content", "")) for m in messages if isinstance(m, dict))
    found = sorted({t for t in _MARKER.findall(user)})
    payload = {
        "arguments": [
            {"text": f"Marker unit {t}", "source_quote": f"ARGT{t} marker sentence."}
            for t in found
        ],
        "claims": [],
        "fallacies": [],
        "summary": "ok",
    }
    return json.dumps(payload)


def _fake_response(messages):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=_marker_payload(messages)))
        ]
    )


async def _fake_completion(_client=None, **kwargs):
    """The faithful-model fake: extract the markers present in the prompt.

    A marker absent from the prompt cannot be extracted — that is the
    window defect this test measures, expressed as model behaviour.
    """
    return _fake_response(kwargs.get("messages", []))


def _fake_sync_completion(_client=None, **kwargs):
    """The same faithful model in the SYNCHRONOUS shape (#2324's sync twin).

    The agentic virtue layer builds its own ``openai.OpenAI`` client and
    calls ``cached_raw_chat_completion_sync`` (invoke_callables.py:299) —
    neither the async fake nor the SK double reaches that path. Measured
    without this patch: 2 real POSTs to api.openai.com (the client is built
    with ``max_retries=1``) inside the gate, class ``llm``/``network``.
    """
    return _fake_response(kwargs.get("messages", []))


def _fake_client():
    """A stub OpenAI client for the paths that build their own
    (``build_async_openai_client`` — nl_to_logic and friends): without it a
    dummy key makes those paths EGRESS to the real API for a 401 (measured).
    Same fake, same rule: the model answers from what it is given."""
    create = AsyncMock(side_effect=_fake_completion)
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )


class _FakeSkChatCompletion(ChatCompletionClientBase):
    """A REAL SK chat client whose answer comes from ``_fake_completion``.

    Not a MagicMock — a double richer than the object under test certifies a
    dead path. The pipeline adds this to a kernel and calls it through the SK
    base, so it honours the same contract the built service does: the plural
    ``get_chat_message_contents`` is the interception point, and the singular
    ``get_chat_message_content`` delegates to it inside the SK base (both
    call shapes were measured on the real service).

    It stands in for the ONE service construction no other patch reaches:
    ``create_llm_service(..., force_authentic=True)`` at the two fallacy
    wide-net sites of ``invoke_callables``, which ask for a real service on
    purpose under ``PYTEST_CURRENT_TEST``. Measured without it: 12 requests
    to api.openai.com (real 401 answers) inside the gate.
    """

    async def get_chat_message_contents(self, chat_history, settings=None, **kwargs):
        messages = [
            {
                "role": str(getattr(message, "role", "user")),
                "content": str(message.content),
            }
            for message in chat_history
        ]
        response = await _fake_completion(messages=messages)
        return [
            ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content=response.choices[0].message.content,
                ai_model_id="fake-2850",
            )
        ]

    async def get_streaming_chat_message_contents(
        self, chat_history, settings=None, **kwargs
    ):
        raise AssertionError(
            "the #2850 coverage test is non-streaming; a streaming call means "
            "a path this faithful double was not built for"
        )


def _thirds_in_state(state) -> "dict[str, object]":
    """The measured coverage: which thirds hold an identified argument, and
    which thirds any specialist field reaches — a specialist touches a unit
    when a state field carries the unit's id (``"arg_N"`` quoted, so
    ``arg_1`` cannot match inside ``arg_10``)."""
    identified = getattr(state, "identified_arguments", None) or {}
    if isinstance(identified, dict):
        id_to_text = {str(k): str(v) for k, v in identified.items()}
    else:  # a list of texts — synthesize positional ids
        id_to_text = {f"arg_{i}": str(v) for i, v in enumerate(identified, start=1)}
    third_of_unit: "dict[str, list[str]]" = {t: [] for t in ("1", "2", "3")}
    for unit_id, text in id_to_text.items():
        for t in ("1", "2", "3"):
            if f"ARGT{t}" in text:
                third_of_unit[t].append(unit_id)
    touched: "dict[str, list[str]]" = {t: [] for t in ("1", "2", "3")}
    for attr in dir(state):
        if attr.startswith("_") or attr == "identified_arguments":
            continue
        try:
            value = getattr(state, attr)
        except Exception:  # noqa: BLE001 — state properties may compute
            continue
        if callable(value) or not isinstance(value, (dict, list, tuple)):
            continue
        serialized = json.dumps(value, default=str)
        for t, unit_ids in third_of_unit.items():
            if any(f'"{uid}"' in serialized for uid in unit_ids):
                touched[t].append(attr)
    return {
        "units": {t: third_of_unit[t] for t in ("1", "2", "3")},
        "touched_by": {t: touched[t] for t in ("1", "2", "3")},
        "unit_thirds": sorted(t for t in third_of_unit if third_of_unit[t]),
        "specialist_thirds": sorted(t for t in touched if touched[t]),
    }


@pytest.mark.xfail(
    strict=True,
    reason=(
        "#2850 coverage debt: the extraction window reads ~3000 chars, so "
        "thirds 2 and 3 hold no analysed unit and no specialist result — "
        "red at birth by construction; remove this marker when the coverage "
        "layer lands and both assertions hold"
    ),
)
async def test_each_third_of_a_long_document_is_analysed(monkeypatch):
    # Dummy key: the phase gate skips every LLM phase when NO key is set
    # (measured: 16 skipped, 1 completed), but a dummy one lets the run
    # reach the intercepted call — and an invalid key bills nothing. Every
    # call this test can make is either the fake or a 401.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-deterministic-2850")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    # Endpoint vars go too: the egress net below deliberately allows loopback
    # (Windows' ProactorEventLoop needs it), so a seat whose .env points
    # OPENAI_BASE_URL at 127.0.0.1 would let an unpatched path reach a real
    # local model. Scrubbed, every client the run can build resolves to the
    # default endpoint — and that one is blocked by the net.
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)

    # Socket barrier — with a measured limit, stated: it covers SYNC connects
    # only. On Windows the async clients (the SK service, the OpenAI SDK)
    # connect through the Proactor loop's overlapped ConnectEx, never through
    # ``socket.connect`` — measured on ai-01: 14 real requests sailed past it
    # to api.openai.com. The real nets are therefore the faithful double below
    # and the gate's egress report (#2444), not this barrier.
    # Loopback stays open — Windows' ProactorEventLoop builds its internal
    # socketpair through 127.0.0.1 (a total block kills asyncio itself,
    # measured at birth), which is why the endpoint vars above are scrubbed
    # rather than trusted.
    import socket

    _real_connect = socket.socket.connect

    def _blocked(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else str(address)
        if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0", ""):
            return _real_connect(self, address, *args, **kwargs)
        raise OSError(f"network egress to {host} blocked by the #2850 coverage test")

    monkeypatch.setattr(socket.socket, "connect", _blocked)

    # The fallacy wide-net asks the factory for a REAL service on purpose
    # (``force_authentic=True`` — "never a mock under PYTEST_CURRENT_TEST",
    # invoke_callables.py:6124 and :6663), and no patch above reaches the SK
    # service it builds. The faithful double stands in for exactly those
    # calls; every other caller keeps the factory's own pytest mock.
    from argumentation_analysis.core import llm_service as llm_service_module

    _real_create_llm_service = llm_service_module.create_llm_service

    def _faithful_factory(*args, **kwargs):
        force_authentic = kwargs.get("force_authentic") or (len(args) >= 5 and args[4])
        if force_authentic:
            return _FakeSkChatCompletion(
                service_id="fake-2850", ai_model_id="fake-2850"
            )
        return _real_create_llm_service(*args, **kwargs)

    monkeypatch.setattr(llm_service_module, "create_llm_service", _faithful_factory)
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    document = _build_document()
    assert 55000 < len(document) < 70000, f"document length {len(document)}"
    for n in (1, 2, 3):
        assert document.count(f"ARGT{n}") == 1, f"marker {n} must appear once"

    with (
        patch(f"{INVOKE_PATH}._get_openai_client", return_value=(MagicMock(), "m")),
        patch(
            f"{INVOKE_PATH}._guarded_chat_completion",
            new=AsyncMock(side_effect=_fake_completion),
        ),
        patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        patch(
            "argumentation_analysis.core.utils.network_utils.build_async_openai_client",
            return_value=_fake_client(),
        ),
        # The quality phase's agentic virtue layer does not go through any of
        # the patches above: it builds its own sync ``OpenAI`` client and
        # calls the #2324 sync twin of the cache seam (measured here: 2 real
        # POSTs to api.openai.com, one retry, class llm/network — the gate's
        # failure row). Fake the seam, not the client: the callable keeps its
        # shape and answers from the prompt it was given.
        patch(
            "argumentation_analysis.services.llm_cache.cached_raw_chat_completion_sync",
            new=_fake_sync_completion,
        ),
        # The local-LLM phase probes ``{endpoint}/models`` before doing
        # anything (measured: 1 GET to localhost:5001). No seat of this
        # cluster serves that endpoint; answering "unavailable" without a
        # socket is the truthful double, and it keeps the phase's own
        # degraded path (status skipped, traced) intact.
        patch(
            "argumentation_analysis.services.local_llm_service."
            "LocalLLMService.is_available",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await run_unified_analysis(document, workflow_name="standard")

    state = result.get("unified_state")
    assert state is not None, "state tracking must stay on for the coverage read"
    measured = _thirds_in_state(state)
    for n in ("1", "2", "3"):
        assert (
            n in measured["unit_thirds"]
        ), f"third {n} holds no identified argument at all (measured: {measured})"
        assert n in measured["specialist_thirds"], (
            f"no specialist result reaches third {n}'s unit — the units past "
            f"the reading window are produced (heuristic) but never analysed "
            f"(measured: {measured})"
        )
