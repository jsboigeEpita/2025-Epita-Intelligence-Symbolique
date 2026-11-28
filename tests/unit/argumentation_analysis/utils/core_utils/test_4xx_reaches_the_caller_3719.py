"""#3719 — a 4xx the endpoint refuses reaches the act's caller as what it is.

Measured on 28/11 (R1220, ``main`` ``993e169ec``): on the named Anthropic route
the endpoint refused every act with a 400, and the run log read as a network
outage — ``APIConnectionError('Connection error.')`` — while the endpoint's
message appeared nowhere.

Why (#2324's repair stops at the transport): ``LoggingHttpTransport`` raises
``httpx.HTTPStatusError`` with the status and the body, which is right just
above the transport, and the witnesses of #2324 pin it there. But the OpenAI
SDK sits above the httpx client and reads an exception leaving ``send()`` as a
connection failure: it wraps it in ``APIConnectionError('Connection error.')``,
retries it, and the body survives only in ``__cause__``.

Measured on the gate's stack (SK 1.44.0, openai 3.3.0), the chain that reaches
the act's caller is::

    KernelInvokeException
      └─ FunctionExecutionException      ← what SK logs ("Function failed. Error: %s")
           └─ ServiceResponseException
                └─ openai.APIConnectionError('Connection error.')
                     └─ httpx.HTTPStatusError('400 Bad Request: {body}')

and the wire saw **three** requests. The endpoint's message is in the chain's
last node — a node no log line prints: SK prints the ``repr`` of the SDK error
(``"('…failed to complete the prompt', APIConnectionError('Connection error.'))"``),
which is exactly the six lines of the R1220 log, for three acts.

The repair is one outermost layer, ``SdkFacingTransport``: for the statuses the
SDK does not retry it hands the raised error response back, so the SDK raises
its own typed error — status and body — after ONE send. The statuses the SDK
retries (408, 409, 429, 5xx) keep the path they had.

The witnesses of ask 2 go through the stack an act uses — ``create_llm_service``,
a real ``Kernel``, a real ``OpenAIChatCompletion`` — with ``httpx.MockTransport``
as the wire. They are born red on ``main``, in values: the log carries
``Connection error.`` and the endpoint's message, and the wire saw three
requests.
"""

import ast
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import openai
import pytest

from argumentation_analysis.core import llm_service
from argumentation_analysis.core.utils import network_utils
from argumentation_analysis.core.utils.network_utils import network_breaker
from tests.support.tree_walk import iter_tracked_files

# The endpoint's own message, read with a direct request on 28/11 (R1220).
_ENDPOINT_MESSAGE = '"thinking.type.between_tools" is not supported for this model.'

_REFUSAL_400 = {
    "error": {
        "message": _ENDPOINT_MESSAGE,
        "type": "invalid_request_error",
        "param": "thinking.type",
        "code": None,
    }
}

_OVERLOADED = {
    "error": {"message": "The model is overloaded. Retry later.", "type": "overloaded"}
}

# The 400 of the reasoning family, measured on 22/09 (#2324) — the repair of
# #2324/#2827 reads it to decide its one adapted retry.
_REJECTS_NONE = {
    "error": {
        "message": (
            "'reasoning_effort' does not support 'none' with this model. "
            "Supported values: 'minimal', 'low', 'medium', 'high'."
        ),
        "type": "invalid_request_error",
        "param": "reasoning_effort",
        "code": None,
    }
}

_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
_TOOLS = [{"type": "function", "function": {"name": "navigate", "parameters": {}}}]
_OK_BODY = {"id": "resp", "object": "chat.completion"}

REPO_ROOT = Path(__file__).resolve().parents[5]
ROOTS = ("argumentation_analysis", "api", "scripts", "project_core", "config")

_ROUTE_VARS = (
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_CHAT_MODEL_ID",
    "LLM_EXPECTED_ROUTE",
)

RAISING_BUILDER = "get_resilient_async_client"
SDK_FACING_BUILDER = "get_sdk_facing_async_client"
_BUILDERS = (RAISING_BUILDER, SDK_FACING_BUILDER)
#: The one production seat where a client is handed to the OpenAI SDK.
ATTACHMENT_POINT = "argumentation_analysis/core/llm_service.py"


@pytest.fixture(autouse=True)
def _reset_breaker():
    network_breaker.close()
    yield
    network_breaker.close()


def _carries(record: str, message: str) -> bool:
    """Whether ``record`` carries the endpoint's message.

    Each layer that prints a body escapes it its own way — the raw text, the
    JSON text, the repr of either — so the sentence is looked for in the two
    spellings a body actually takes, never in one hard-coded spelling.
    """
    return message in record or json.dumps(message)[1:-1] in record


def _named_anthropic_route(monkeypatch: pytest.MonkeyPatch) -> None:
    """The route of the R1220 run: a sentinel key, no other route variable."""
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-sentinel")
    monkeypatch.setenv("ANTHROPIC_CHAT_MODEL_ID", "claude-sentinel-model")
    monkeypatch.setenv("LLM_CACHE_MODE", "off")


async def _close(service: Any) -> None:
    """Close the client the factory built (the cache wrapper holds it)."""
    inner = getattr(service, "_inner", service)
    client = getattr(inner, "client", None)
    if client is not None and hasattr(client, "close"):
        await client.close()


async def _act(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    status: int,
    body: Dict[str, Any],
) -> List[httpx.Request]:
    """Run one act on the real stack; return the requests that reached the wire.

    The stack is the one an act uses: ``create_llm_service`` (the named
    Anthropic route), a real ``Kernel``, a real ``OpenAIChatCompletion``; the
    wire is an ``httpx.MockTransport`` answering the status asked for.

    The refusal is NOT raised at the caller: an act swallows it (``weave``,
    fail-loud) and records what it saw. The witness reads that record — the
    log lines the failed invocation writes — so the failure must not escape
    the act either.
    """
    from semantic_kernel import Kernel

    seen: List[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=body)

    monkeypatch.setattr(
        httpx,
        "AsyncHTTPTransport",
        lambda *args, **kwargs: httpx.MockTransport(handle),
    )
    _named_anthropic_route(monkeypatch)

    service = llm_service.create_llm_service(force_authentic=True)
    kernel = Kernel()
    kernel.add_service(service)
    failed = False
    try:
        with caplog.at_level(logging.WARNING):
            try:
                await kernel.invoke_prompt("Dis bonjour.")
            except Exception:  # noqa: BLE001 — the act records the failure
                failed = True
    finally:
        await _close(service)
    assert failed, "the error status did not fail the act: case not measured"
    return seen


# ===========================================================================
# Ask 2 — through the stack an act uses, born red on `main`
# ===========================================================================


async def test_the_logged_failure_carries_the_endpoint_message(monkeypatch, caplog):
    """Born red on `main`: the log carries ``APIConnectionError('Connection
    error.')`` and the endpoint's message appears nowhere.

    What is read here is what the failed act's invocation LOGS — the lines
    SK writes when a function fails ("Function failed. Error: …"), which embed
    the SDK error's repr. It is not a chain the test walks itself: the body
    survives in ``__cause__`` on ``main`` too, and a witness that read it
    there would be green before the repair.
    """
    await _act(monkeypatch, caplog, 400, _REFUSAL_400)

    logged = "\n".join(record.getMessage() for record in caplog.records)
    carriers = [
        record.getMessage()
        for record in caplog.records
        if _carries(record.getMessage(), _ENDPOINT_MESSAGE)
    ]
    assert carriers, (
        "the endpoint's message reaches no log line of the failed act:\n" + logged
    )
    assert any(
        "400" in message for message in carriers
    ), f"the status does not reach the log line that carries the message: {carriers}"


async def test_the_wire_saw_one_request_not_three(monkeypatch, caplog):
    """Born red on `main`: the SDK filed the 400 as a connection failure and
    sent it three times."""
    seen = await _act(monkeypatch, caplog, 400, _REFUSAL_400)

    assert len(seen) == 1, f"a refused request was sent {len(seen)} times"


async def test_the_refusal_is_not_logged_as_a_network_outage(monkeypatch, caplog):
    """Born red on `main`: the log reads ``Connection error.`` — a network
    outage, for a request the API refused with a reason and a remedy."""
    await _act(monkeypatch, caplog, 400, _REFUSAL_400)

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert (
        "Connection error." not in logged
    ), f"the refusal still reads as an outage:\n{logged}"


@pytest.mark.parametrize("status", [429, 503])
async def test_a_status_the_sdk_retries_keeps_its_three_sends(
    monkeypatch, caplog, status
):
    """Agreement, green before and after: 429 and 5xx keep the path they had —
    the SDK's own retries, three sends. The repair moves only what ask 1 names,
    and their outcome (still a connection error) is named in the PR body as the
    residual it is."""
    seen = await _act(monkeypatch, caplog, status, _OVERLOADED)

    assert len(seen) == 3, f"the retries of a {status} moved: {len(seen)} sends"


# ===========================================================================
# The layer, at the transport — what it hands back and what it lets through
# ===========================================================================


def _wire(
    monkeypatch: pytest.MonkeyPatch, script: List[Tuple[int, Dict[str, Any]]]
) -> Tuple[httpx.AsyncClient, List[dict]]:
    """The production chain over a written scenario.

    Returns the client (in the form the OpenAI SDK drives) and the list of
    the bodies that reached the wire.
    """
    steps = list(script)
    bodies: List[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        status, body = steps.pop(0)
        return httpx.Response(status, json=body)

    monkeypatch.setattr(
        httpx,
        "AsyncHTTPTransport",
        lambda *args, **kwargs: httpx.MockTransport(handle),
    )
    return network_utils.get_sdk_facing_async_client(), bodies


def _chat_payload(model: str, tools=None, extra=None) -> dict:
    payload = {"model": model, "messages": [{"role": "user", "content": "x"}]}
    if tools is not None:
        payload["tools"] = tools
    if extra:
        payload.update(extra)
    return payload


@pytest.mark.parametrize("status", [400, 401, 403, 404, 413, 422])
async def test_a_status_the_sdk_does_not_retry_comes_back_as_a_response(
    monkeypatch, status
):
    """The layer hands the error response back: the SDK above names it."""
    client, bodies = _wire(monkeypatch, [(status, _REFUSAL_400)])
    try:
        response = await client.post(
            _COMPLETIONS_URL, json={"model": "m", "messages": []}
        )
    finally:
        await client.aclose()

    assert response.status_code == status
    assert _carries(response.text, _ENDPOINT_MESSAGE)
    assert len(bodies) == 1
    assert response.request is not None, "the SDK's error reads response.request"


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503])
async def test_a_status_the_sdk_retries_still_raises(monkeypatch, status):
    """408, 409, 429 and 5xx keep the raise: their retries are the SDK's and
    their outcome is not what this repair moves."""
    client, bodies = _wire(monkeypatch, [(status, _REFUSAL_400)])
    try:
        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            await client.post(_COMPLETIONS_URL, json={"model": "m", "messages": []})
    finally:
        await client.aclose()

    assert excinfo.value.response.status_code == status
    assert len(bodies) == 1


async def test_a_transport_failure_is_not_turned_into_a_response():
    """Agreement: a refused connection stays an exception — the SDK keeps its
    connection retries, and ``provider_failure`` (#2832) keeps finding it."""

    class _RefusingWire(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

    client = httpx.AsyncClient(
        transport=network_utils.SdkFacingTransport(_RefusingWire())
    )
    try:
        with pytest.raises(httpx.ConnectError):
            await client.post(_COMPLETIONS_URL, json={})
    finally:
        await client.aclose()


# ===========================================================================
# #2324's repair — it must keep acting through the SDK-facing client
# ===========================================================================


async def test_the_reasoning_effort_repair_still_acts(monkeypatch):
    """#2324 reads a 400 to decide its one adapted retry. The SDK-facing layer
    is the OUTERMOST one, so that 400 still reaches the transport that knows
    how to adapt it — the repair is not shadowed by the layer above it."""
    client, bodies = _wire(monkeypatch, [(400, _REJECTS_NONE), (200, _OK_BODY)])
    try:
        response = await client.post(
            _COMPLETIONS_URL, json=_chat_payload("gpt-5-mini", tools=_TOOLS)
        )
    finally:
        await client.aclose()

    assert response.status_code == 200, "the adapted retry did not pass"
    assert len(bodies) == 2, "one retry only, no loop"
    assert bodies[0]["reasoning_effort"] == "none"
    assert "reasoning_effort" not in bodies[1]


async def test_a_second_rejection_comes_back_with_its_body(monkeypatch):
    """A second rejection propagates with its body — the SDK above names it
    instead of the SDK wrapping it as a connection failure."""
    client, bodies = _wire(monkeypatch, [(400, _REJECTS_NONE), (400, _REJECTS_NONE)])
    try:
        response = await client.post(
            _COMPLETIONS_URL, json=_chat_payload("gpt-5-mini", tools=_TOOLS)
        )
    finally:
        await client.aclose()

    assert response.status_code == 400
    assert len(bodies) == 2
    assert "reasoning_effort" in response.text


async def test_the_bare_chain_already_names_the_error(monkeypatch):
    """Agreement, green before and after: ``build_async_openai_client`` — the
    constructor of the 18 other sites (#2391) — carries no layer that raises.
    A 400 reaches the SDK there as a response, and the SDK already names it.
    The change does not reach those sites; this pins that it does not have to,
    and reddens if a raising layer is added under that constructor without the
    SDK-facing one above it.
    """
    seen: List[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(400, json=_REFUSAL_400)

    monkeypatch.setattr(
        httpx,
        "AsyncHTTPTransport",
        lambda *args, **kwargs: httpx.MockTransport(handle),
    )
    sdk = network_utils.build_async_openai_client(api_key="sk-sentinel")
    try:
        with pytest.raises(openai.BadRequestError) as excinfo:
            await sdk.chat.completions.create(
                model="claude-sentinel-model",
                messages=[{"role": "user", "content": "Dis bonjour."}],
            )
    finally:
        await sdk.close()

    assert _carries(str(excinfo.value), _ENDPOINT_MESSAGE)
    assert "400" in str(excinfo.value)
    assert len(seen) == 1, f"a refused request was sent {len(seen)} times"


# ===========================================================================
# Ask 3 — the population, counted in the AST
# ===========================================================================


def _builder_calls(source: str) -> List[Tuple[int, str]]:
    """(line, builder) of every call that constructs one of the two clients.

    A call is counted through the name it uses AND through the alias its
    import gave it — a census that only read the plain name would miss
    ``from … import get_resilient_async_client as rac``.
    """
    tree = ast.parse(source)
    aliases: Dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in _BUILDERS and alias.asname:
                    aliases[alias.asname] = alias.name
    calls: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.id
            if isinstance(func, ast.Name)
            else func.attr if isinstance(func, ast.Attribute) else None
        )
        builder = aliases.get(name, name)
        if builder in _BUILDERS:
            calls.append((node.lineno, builder))
    return calls


def _census() -> Tuple[Dict[str, Dict[str, List[int]]], int, List[Tuple[str, str]]]:
    """The population of the five production roots, read from the git index."""
    found: Dict[str, Dict[str, List[int]]] = {}
    walked = 0
    skipped: List[Tuple[str, str]] = []
    for root in ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for path in iter_tracked_files(base, "*.py"):
            rel = path.relative_to(REPO_ROOT).as_posix()
            try:
                source = path.read_text(encoding="utf-8-sig")
                calls = _builder_calls(source)
            except (OSError, SyntaxError, UnicodeDecodeError) as exc:
                skipped.append((rel, type(exc).__name__))
                continue
            walked += 1
            if calls:
                per_builder: Dict[str, List[int]] = {}
                for line, builder in calls:
                    per_builder.setdefault(builder, []).append(line)
                found[rel] = per_builder
    return found, walked, skipped


def test_the_census_counts_a_call_by_its_name_and_by_its_alias():
    """Positive control: the census sees the three forms of a construction —
    the plain name, the aliased import, the attribute — and does not mistake
    a definition or a mention for a call."""
    assert _builder_calls("c = get_resilient_async_client()\n") == [
        (1, RAISING_BUILDER)
    ]
    assert _builder_calls(
        "from m import get_sdk_facing_async_client as facing\nc = facing()\n"
    ) == [(2, SDK_FACING_BUILDER)]
    assert _builder_calls("import m\nc = m.get_resilient_async_client()\n") == [
        (2, RAISING_BUILDER)
    ]
    assert _builder_calls("def get_resilient_async_client():\n    pass\n") == []
    assert (
        _builder_calls("x = get_resilient_async_client  # a name, not a call\n") == []
    )


def test_the_sdk_is_never_handed_the_raising_client():
    """The raising client hands the status error to the SDK as an EXCEPTION,
    which the SDK reads as a connection failure (#3719). The client handed to
    the SDK is the SDK-facing one; the census says how many seats there are
    and names them."""
    found, walked, skipped = _census()

    # An absence only counts if the walk walked.
    assert walked > 800, f"marche amputée : {walked} fichiers parcourus"
    assert not skipped, f"fichiers sautés par la garde : {skipped}"

    raising = {
        rel: builders[RAISING_BUILDER]
        for rel, builders in found.items()
        if RAISING_BUILDER in builders
    }
    assert not raising, (
        "le client qui LÈVE le statut d'erreur est encore confié au SDK "
        f"({RAISING_BUILDER}) : {raising} — passer par {SDK_FACING_BUILDER}"
    )

    facing = {
        rel: builders[SDK_FACING_BUILDER]
        for rel, builders in found.items()
        if SDK_FACING_BUILDER in builders
    }
    assert set(facing) == {ATTACHMENT_POINT}, (
        f"le client confié au SDK est construit ailleurs qu'à {ATTACHMENT_POINT} : "
        f"{facing}"
    )
    assert (
        len(facing[ATTACHMENT_POINT]) == 1
    ), f"le siège d'attache a {len(facing[ATTACHMENT_POINT])} constructions : {facing}"
