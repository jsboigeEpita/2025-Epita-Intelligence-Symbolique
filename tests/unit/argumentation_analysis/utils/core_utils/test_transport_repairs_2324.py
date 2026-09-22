"""#2324 — les deux réparations du transport LLM, éprouvées sur la chaîne réelle.

Mesuré le 22/09 (#2324) : ``gpt-5.6-luna`` (famille reasoning) rejette 400
tout appel /chat/completions portant des ``tools`` sans ``reasoning_effort``
explicite — « Function tools with reasoning_effort are not supported … set
reasoning_effort to 'none' ». SK 1.35 ne peut pas exprimer le champ
(``extra`` ignoré) ; le transport est le seul point de passage commun.

Le 400 était ensuite masqué : ``LoggingHttpTransport`` appelait
``response.raise_for_status()`` sur une réponse de transport nu (sans
request lié) → ``RuntimeError: Cannot call raise_for_status as the request
instance has not been set`` → l'API le traduisait en
``APIConnectionError('Connection error.')``. Le message de l'API — le
paramètre fautif, la raison, le remède — ne remontait jamais.

Deux réparations, deux né-rouges **en valeurs** :

1. **400 honnête** — sur main d'avant réparation, le test du 400 meurt du
   ``RuntimeError`` d'origine (pas d'``HTTPStatusError``) ; il échoue en
   nommant l'exception réelle levée.
2. **Injection ``reasoning_effort``** — le test pousse la requête à travers
   la chaîne complète de ``get_resilient_async_client()`` (le transport de
   production) ; sur main d'avant réparation, le corps parti sur le fil ne
   porte pas le champ et l'assertion de valeur échoue.

Les quatre contrôles d'accord (modèle non-reasoning, sans tools, champ déjà
présent, hors /chat/completions, corps non-JSON) sont verts avant ET après :
ils épingle que la réparation n'injecte **jamais** hors de son mandat.
"""

import json
import logging

import httpx
import pytest

from argumentation_analysis.core.utils import network_utils
from argumentation_analysis.core.utils.network_utils import (
    LoggingHttpTransport,
    network_breaker,
)

REASONING_MODEL = "gpt-5.6-luna"  # famille reasoning — mesurée #2324
PLAIN_MODEL = "gpt-4-turbo-2024-04-09"  # hors des préfixes reasoning

_TOOLS = [{"type": "function", "function": {"name": "navigate", "parameters": {}}}]

_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


@pytest.fixture(autouse=True)
def _reset_breaker():
    network_breaker.close()
    yield
    network_breaker.close()


class _WireCapture(httpx.AsyncBaseTransport):
    """Faux transport de fond : capture la requête PARTIE SUR LE FIL.

    Classe de remplacement de ``httpx.AsyncHTTPTransport`` — elle accepte
    les mêmes arguments de construction et stocke la dernière requête sur
    un attribut de classe pour que le test puisse la relire.
    """

    last_request: httpx.Request = None

    def __init__(self, *args, **kwargs):
        self.status_code = 200
        self.response_body = {"id": "resp", "object": "chat.completion"}

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        type(self).last_request = request
        return httpx.Response(
            self.status_code, json=self.response_body, request=request
        )


async def _wire_body(
    monkeypatch, payload, url=_COMPLETIONS_URL
) -> tuple[dict, httpx.Response]:
    """Pousse ``payload`` à travers la chaîne de production complète.

    Retourne le corps réellement parti sur le fil (parsé) et la réponse.
    """
    monkeypatch.setattr(httpx, "AsyncHTTPTransport", _WireCapture)
    client = network_utils.get_resilient_async_client()
    try:
        response = await client.post(url, json=payload)
        wire_bytes = await _WireCapture.last_request.aread()
        return json.loads(wire_bytes.decode("utf-8")), response
    finally:
        await client.aclose()


def _chat_payload(model: str, tools=None, extra=None) -> dict:
    payload = {"model": model, "messages": [{"role": "user", "content": "x"}]}
    if tools is not None:
        payload["tools"] = tools
    if extra:
        payload.update(extra)
    return payload


# ===========================================================================
# 1. Le 400 honnête — l'exception dit ce que l'API a dit
# ===========================================================================


class _InnerStatus(httpx.AsyncBaseTransport):
    """Transport de fond qui rend la réponse 400 capturée le 22/09."""

    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self.body = body

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Réponse de transport nu : PAS de request lié — c'est l'état exact
        # dans lequel LoggingHttpTransport recevait le 400 réel.
        return httpx.Response(self.status_code, json=self.body)


_API_400_BODY = {
    "error": {
        "message": (
            "Function tools with reasoning_effort are not supported for "
            "gpt-5.6-luna in /v1/chat/completions. To use function tools, "
            "use /v1/responses or set reasoning_effort to 'none'."
        ),
        "type": "invalid_request_error",
        "param": "reasoning_effort",
        "code": None,
    }
}


async def test_400_raises_the_api_body_not_a_runtime_error():
    """Né-rouge #2324 : avant réparation, ``RuntimeError`` (raise_for_status
    sans request lié) — jamais l'``HTTPStatusError`` portant le message API.
    """
    transport = LoggingHttpTransport(
        logging.getLogger("test_2324"),
        wrapped_transport=_InnerStatus(400, _API_400_BODY),
    )
    request = httpx.Request(
        "POST",
        _COMPLETIONS_URL,
        content=json.dumps(_chat_payload(REASONING_MODEL, tools=_TOOLS)).encode(
            "utf-8"
        ),
        headers={"content-type": "application/json"},
    )

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        await transport.handle_async_request(request)

    message = str(excinfo.value)
    # Le verdict de l'API remonte : le paramètre fautif et le remède.
    assert (
        "Function tools" in message
    ), f"le corps du 400 de l'API ne remonte pas : {message!r}"
    assert (
        "reasoning_effort" in message
    ), f"le paramètre fautif ne remonte pas : {message!r}"
    assert "400" in message and "Bad Request" in message
    # L'exception est liée à ses deux extrémités — pas un masque « Connection error ».
    assert excinfo.value.request is request
    assert excinfo.value.response is not None
    assert excinfo.value.response.status_code == 400


async def test_success_response_passes_through_untouched():
    """Accord : 200 → réponse rendue telle quelle, aucune exception."""
    transport = LoggingHttpTransport(
        logging.getLogger("test_2324"),
        wrapped_transport=_InnerStatus(200, {"ok": True}),
    )
    request = httpx.Request(
        "POST",
        _COMPLETIONS_URL,
        content=b"{}",
        headers={"content-type": "application/json"},
    )
    response = await transport.handle_async_request(request)
    assert response.status_code == 200


# ===========================================================================
# 2. L'injection reasoning_effort — à travers la chaîne de production
# ===========================================================================


async def test_chain_injects_none_for_reasoning_model_with_tools(monkeypatch):
    """Né-rouge #2324 : avant réparation, aucun transport n'injecte — le
    corps sur le fil ne porte pas le champ, et l'appel meurt en 400 côté API.
    """
    wire, response = await _wire_body(
        monkeypatch, _chat_payload(REASONING_MODEL, tools=_TOOLS)
    )
    assert response.status_code == 200
    assert (
        wire.get("reasoning_effort") == "none"
    ), f"le champ injecté attendu manque sur le fil : {sorted(wire)}"
    # Le reste du payload survit à l'injection.
    assert wire["model"] == REASONING_MODEL
    assert wire["tools"] == _TOOLS
    assert len(wire["messages"]) == 1
    # Le content-length annoncé est celui du corps réellement parti.
    sent = _WireCapture.last_request
    assert int(sent.headers["content-length"]) == len(
        (await sent.aread())
    ), "content-length désynchronisé du corps injecté"


# --- Contrôles d'accord : hors mandat, jamais d'injection -------------------


async def test_plain_model_gets_no_injection(monkeypatch):
    """Un modèle non-reasoning ne doit PAS recevoir le paramètre."""
    wire, _ = await _wire_body(monkeypatch, _chat_payload(PLAIN_MODEL, tools=_TOOLS))
    assert (
        "reasoning_effort" not in wire
    ), f"injection hors mandat (modèle non-reasoning) : {wire}"


async def test_no_tools_gets_no_injection(monkeypatch):
    """Un appel sans tools (chat simple) ne doit PAS recevoir le paramètre."""
    wire, _ = await _wire_body(monkeypatch, _chat_payload(REASONING_MODEL, tools=None))
    assert "reasoning_effort" not in wire


async def test_existing_effort_is_preserved(monkeypatch):
    """Un appel qui exprime DÉJÀ son effort garde sa valeur — l'injection
    ne vient jamais écraser un choix explicite."""
    wire, _ = await _wire_body(
        monkeypatch,
        _chat_payload(
            REASONING_MODEL, tools=_TOOLS, extra={"reasoning_effort": "high"}
        ),
    )
    assert wire["reasoning_effort"] == "high"


async def test_other_endpoint_gets_no_injection(monkeypatch):
    """Hors /chat/completions (embeddings), le corps est intouché."""
    wire, _ = await _wire_body(
        monkeypatch,
        {"model": "text-embedding-3-small", "input": "x"},
        url="https://api.openai.com/v1/embeddings",
    )
    assert "reasoning_effort" not in wire


async def test_non_json_chat_body_passes_through(monkeypatch):
    """Un corps non-JSON sur /chat/completions ne fait pas exploser le transport."""
    monkeypatch.setattr(httpx, "AsyncHTTPTransport", _WireCapture)
    client = network_utils.get_resilient_async_client()
    try:
        response = await client.post(
            _COMPLETIONS_URL,
            content=b"ceci n'est pas du json",
            headers={"content-type": "text/plain"},
        )
        assert response.status_code == 200
        sent = _WireCapture.last_request
        assert (await sent.aread()) == b"ceci n'est pas du json"
    finally:
        await client.aclose()
