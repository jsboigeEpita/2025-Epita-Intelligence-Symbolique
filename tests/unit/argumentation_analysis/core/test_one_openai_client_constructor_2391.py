"""#2391 — un seul constructeur de client ``AsyncOpenAI``, donc un seul transport.

Le défaut, mesuré sur ``bdc5b618`` (run ``35783217532``) : #2387 a réparé le
400 ``reasoning_effort`` dans ``ReasoningEffortTransport``, mais un transport
n'atteint que les clients construits avec lui. Seul ``create_llm_service`` le
faisait ; dix-huit sites construisaient un ``AsyncOpenAI`` nu. La fixture du
garde de #2322 en copiait un, et restait rouge (N × 400) sur la route par
défaut alors que le pipeline était réparé.

Mesuré ici :

1. **né-rouge en valeur** : le client que rendent deux fabriques de production
   (``invoke_callables._get_openai_client``,
   ``coordinated_logic_plugin._get_openai_client``) passe par
   ``ReasoningEffortTransport``. Sur ``bdc5b618`` son transport est un
   ``AsyncHTTPTransport`` nu : ``isinstance`` rend ``False``, sans aucun appel
   réseau ;
2. **le fil** : un appel à outils vers un modèle reasoning, émis par le client
   du constructeur, part avec ``reasoning_effort: "none"``. Un modèle
   non-reasoning part inchangé (contrôle d'accord), et le même appel sans le
   transport part sans le champ (témoin : c'est le corps du 400) ;
3. **la garde de classe** : aucune construction ``AsyncOpenAI(...)`` dans les
   cinq racines hors des deux sièges admis. Le périmètre parcouru est
   **compté**, les fichiers sautés sont **imprimés**, et un contrôle positif
   construit à l'exécution doit la faire rougir.
"""

import ast
import json
from pathlib import Path
from typing import List, Tuple

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
ROOTS = ("argumentation_analysis", "api", "scripts", "project_core", "config")

REASONING_MODEL = "gpt-5.6-luna"  # famille reasoning — mesurée #2324
_TOOLS = [{"type": "function", "function": {"name": "navigate", "parameters": {}}}]

# Les seuls sièges autorisés à construire un AsyncOpenAI, avec leur compte
# exact : un siège qui disparaît ou se dédouble rougit aussi.
_ADMITTED = {
    "argumentation_analysis/core/utils/network_utils.py": 1,
    "argumentation_analysis/core/llm_service.py": 1,
}

_ROUTE_VARS = (
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
    "LLM_EXPECTED_ROUTE",
)


def _completion(model: str) -> dict:
    return {
        "id": "chatcmpl-2391",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ],
    }


class _WireCapture(httpx.AsyncBaseTransport):
    """Remplace ``httpx.AsyncHTTPTransport`` : capture le corps parti sur le fil."""

    bodies: List[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body = json.loads((await request.aread()).decode("utf-8"))
        type(self).bodies.append(body)
        return httpx.Response(200, json=_completion(body["model"]), request=request)


@pytest.fixture
def default_route(monkeypatch):
    """La route par défaut de la CI : une clé OpenAI nue, aucune variable de route."""
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-2391-not-a-real-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL_ID", REASONING_MODEL)


def _invoke_callables_client():
    from argumentation_analysis.orchestration.invoke_callables import (
        _get_openai_client,
    )

    client, _model = _get_openai_client()
    return client


def _coordinated_logic_client():
    from argumentation_analysis.plugins.coordinated_logic_plugin import (
        _get_openai_client,
    )

    client, _model, _key = _get_openai_client()
    return client


# ===========================================================================
# 1. Né-rouge — les clients de production passent par le transport
# ===========================================================================


@pytest.mark.parametrize(
    "factory",
    [_invoke_callables_client, _coordinated_logic_client],
    ids=["invoke_callables", "coordinated_logic_plugin"],
)
def test_a_production_client_goes_through_the_reasoning_effort_transport(
    default_route, factory
):
    from argumentation_analysis.core.utils.network_utils import (
        ReasoningEffortTransport,
    )

    client = factory()
    assert client is not None, "la fabrique n'a rendu aucun client : cas non mesuré"

    transport = client._client._transport
    assert isinstance(transport, ReasoningEffortTransport), (
        f"le client de production part par {type(transport).__name__} : "
        "le 400 reasoning_effort réparé par #2387 lui reste ouvert"
    )


# ===========================================================================
# 2. Le fil — ce que le client du constructeur envoie réellement
# ===========================================================================


async def _send_through_constructor(monkeypatch, model: str, tools) -> dict:
    from argumentation_analysis.core.utils.network_utils import (
        build_async_openai_client,
    )

    monkeypatch.setattr(httpx, "AsyncHTTPTransport", _WireCapture)
    _WireCapture.bodies = []
    client = build_async_openai_client(
        api_key="sk-test-2391-not-a-real-key",
        base_url="https://api.openai.com/v1",
        max_retries=0,
    )
    try:
        kwargs = {"model": model, "messages": [{"role": "user", "content": "x"}]}
        if tools is not None:
            kwargs["tools"] = tools
        await client.chat.completions.create(**kwargs)
    finally:
        await client.close()
    assert len(_WireCapture.bodies) == 1, _WireCapture.bodies
    return _WireCapture.bodies[0]


async def test_the_constructor_client_sends_reasoning_effort_with_tools(monkeypatch):
    wire = await _send_through_constructor(monkeypatch, REASONING_MODEL, _TOOLS)

    assert wire.get("reasoning_effort") == "none", sorted(wire)
    assert wire["tools"] == _TOOLS


async def test_a_plain_model_leaves_the_constructor_unchanged(monkeypatch):
    """Contrôle d'accord : l'injection reste bornée à la famille reasoning."""
    wire = await _send_through_constructor(monkeypatch, "gpt-4o-mini", _TOOLS)

    assert "reasoning_effort" not in wire, sorted(wire)


async def test_the_witness_without_the_transport_the_field_is_absent():
    """Témoin : le SDK n'ajoute pas le champ de lui-même.

    Même appel, même modèle, même capture — mais un client construit comme les
    dix-huit sites de ``bdc5b618``, sans le transport. Le corps part sans
    ``reasoning_effort`` : c'est le 400 de #2322. Sans ce témoin, le test du
    fil pourrait verdir parce que l'SDK poserait le champ, et le constructeur
    ne serait pas mesuré.
    """
    from openai import AsyncOpenAI

    _WireCapture.bodies = []
    client = AsyncOpenAI(
        api_key="sk-test-2391-not-a-real-key",
        base_url="https://api.openai.com/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=_WireCapture()),
    )
    try:
        await client.chat.completions.create(
            model=REASONING_MODEL,
            messages=[{"role": "user", "content": "x"}],
            tools=_TOOLS,
        )
    finally:
        await client.close()

    assert len(_WireCapture.bodies) == 1, _WireCapture.bodies
    assert "reasoning_effort" not in _WireCapture.bodies[0]


def test_the_constructor_refuses_a_caller_supplied_http_client():
    from argumentation_analysis.core.utils.network_utils import (
        build_async_openai_client,
    )

    with pytest.raises(TypeError, match="http_client"):
        build_async_openai_client(api_key="sk-test", http_client=httpx.AsyncClient())


# ===========================================================================
# 3. La garde de classe — aucune construction hors des sièges admis
# ===========================================================================


def _constructions(source: str) -> List[int]:
    """Lignes des appels ``AsyncOpenAI(...)`` / ``<x>.AsyncOpenAI(...)``."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.id
            if isinstance(func, ast.Name)
            else func.attr if isinstance(func, ast.Attribute) else None
        )
        if name == "AsyncOpenAI":
            lines.append(node.lineno)
    return lines


def _walk_roots() -> Tuple[dict, int, List[Tuple[str, str]]]:
    found, walked, skipped = {}, 0, []
    for root in ROOTS:
        base = REPO_ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            try:
                source = path.read_text(encoding="utf-8-sig")
                lines = _constructions(source)
            except (OSError, SyntaxError, UnicodeDecodeError) as exc:
                skipped.append((rel, type(exc).__name__))
                continue
            walked += 1
            if lines:
                found[rel] = lines
    return found, walked, skipped


def test_the_guard_catches_both_construction_forms():
    """Contrôle positif : les deux formes d'origine, construites à l'exécution."""
    bare = "from openai import AsyncOpenAI\nc = AsyncOpenAI(api_key='k')\n"
    dotted = "import openai\nc = openai.AsyncOpenAI()\n"
    assert _constructions(bare) == [2]
    assert _constructions(dotted) == [2]
    assert _constructions("c = build_async_openai_client(api_key='k')\n") == []


def test_no_async_openai_is_built_outside_the_admitted_seats():
    found, walked, skipped = _walk_roots()

    # Une absence ne vaut que si la marche a marché.
    assert walked > 800, f"marche amputée : {walked} fichiers parcourus"
    assert not skipped, f"fichiers sautés par la garde : {skipped}"

    outside = {rel: lines for rel, lines in found.items() if rel not in _ADMITTED}
    assert not outside, (
        "AsyncOpenAI construit hors du constructeur unique (#2391) — passer par "
        f"build_async_openai_client : {outside}"
    )
    counts = {rel: len(found.get(rel, [])) for rel in _ADMITTED}
    assert counts == _ADMITTED, f"sièges admis modifiés : {counts}"
