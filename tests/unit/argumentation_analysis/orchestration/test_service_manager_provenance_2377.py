"""#2377 — une provenance qui n'est pas une mesure est un mensonge.

Le défaut, mesuré sur ``b5845b6d`` : les deux méthodes d'analyse du
``OrchestrationServiceManager`` rendaient un dict annonçant
``"model": "gpt-5.6-luna"`` — un **littéral local**, jamais ce que le kernel
venait de servir. Un résultat qui nomme un modèle que l'appel n'a pas consulté
est pire qu'un champ absent : la panne de route devient indétectable **depuis le
résultat lui-même**, qui est pourtant la seule surface que lit l'aval (rapports,
artefacts, benchs).

Le contrat (DoD #2377) : le champ est **dérivé de ce que le kernel a servi**, ou
il n'existe pas. Pas de troisième voie — pas de ``None`` non plus, qui se
confond avec « pas de modèle ».

Trois choses sont mesurées ici, et chacune a son contrôle de non-vacuité :

1. **la mesure** (test du haut) : un kernel qui sert un modèle **≠**
   ``gpt-5.6-luna``, les deux méthodes appelées, le dict doit annoncer ce
   modèle-là. Sur ``b5845b6d`` elles annoncent ``gpt-5.6-luna`` — échec **en
   valeur**, jamais en import : ce fichier n'importe aucun symbole neuf au
   niveau module (voir plus bas) ;
2. **l'absence** : rien d'observable ⇒ pas de clé. Chaque cas assert d'abord que
   le résultat est un résultat *complet* (``status == "completed"`` et une
   réponse), sinon l'absence serait celle d'un chemin d'erreur — une garde
   aveugle qui verdit pour la mauvaise raison ;
3. **les gardes structurelles** : aucune provenance alimentée par un littéral
   local, aucun ``model_id`` littéral à la fabrique de service. Toutes deux
   rougissent sur le motif d'origine (contrôles positifs construits à
   l'exécution), et leur périmètre (``argumentation_analysis/``) est **compté**
   à chaque exécution : une absence ne vaut que si la marche a marché.

Le kernel du harnais est un vrai ``sk.Kernel`` (#2389) : la doublure écrite à
la main qu'il remplace implémentait ``create_function_from_prompt``, une API
que ``Kernel`` n'a pas — les tests de provenance verdissaient sur un chemin
mort en production une ligne plus haut.

Aucun symbole introduit par la réparation (``DEFAULT_CHAT_MODEL_ID``,
``_served_model_id``) n'est importé au niveau module : le né-rouge doit être un
échec de **valeur**, pas un ``ImportError`` de collection.
"""

import ast
import json
import os
import re
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import create_autospec

import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.exceptions import KernelServiceNotFoundError

REPO_ROOT = Path(__file__).resolve().parents[4]
CORE_ROOT = "argumentation_analysis"

# #2381 : la marche s'étend aux racines hors noyau où la classe vivait hors
# périmètre — la garde ne certifie que ce qu'elle parcourt.
CORE_ROOTS = ("argumentation_analysis", "api", "scripts", "project_core", "config")

# Les deux méthodes qui rendaient une provenance fabriquée.
_METHODS = ("_run_tactical_analysis", "_run_operational_analysis")

# La réponse que le service factice rend — le témoin que le kernel a servi.
_REPLY = "réponse simulée"

# Un id de modèle, pour les gardes structurelles. Volontairement large : la
# garde doit voir un littéral *neuf* de la même famille, pas seulement ceux
# qu'on vient de retirer.
_MODEL_LIKE = re.compile(
    r"^(gpt-|o1|o3|claude-|openai/|azure/|glm-|qwen|gemini|mistral|deepseek)"
)

# Les clés sous lesquelles un résultat annonce son modèle. ``model_used`` est
# inclus : c'est la même affirmation, dans un dict d'un autre producteur.
_PROVENANCE_KEYS = frozenset(
    {"model", "model_id", "model_name", "model_used", "chat_model", "chat_model_id"}
)

# Toutes les variables dont un résolveur de route pourrait dépendre.
_ROUTE_VARS = (
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL_ID",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL_ID",
)


# ===========================================================================
# Le harnais : un VRAI kernel, dont le modèle servi est CONNU du test
# ===========================================================================
#
# #2389 : ce harnais était une doublure écrite à la main (``_RecordingKernel``)
# qui DÉFINISSAIT ``create_function_from_prompt`` — une méthode que
# ``semantic_kernel.Kernel`` n'a pas. Les tests ci-dessous verdissaient donc sur
# un chemin que la production ne pouvait pas prendre : elle mourait en
# ``AttributeError`` une ligne avant la provenance certifiée. Le kernel est
# désormais l'objet réel ; seule la feuille qui ferait un egress (le service de
# chat) est factice, et elle hérite de la classe réelle.


class _FixedReplyChatCompletion(ChatCompletionClientBase):
    """Service de chat réel par sa classe, factice par sa seule réponse."""

    async def _inner_get_chat_message_contents(
        self, chat_history: Any, settings: Any
    ) -> List[ChatMessageContent]:
        return [
            ChatMessageContent(
                role="assistant", content=_REPLY, ai_model_id=self.ai_model_id
            )
        ]


def _kernel(services: Dict[str, Any]) -> sk.Kernel:
    """Un ``sk.Kernel`` réel tenant ``services`` (id -> service ou id de modèle)."""
    kernel = sk.Kernel()
    for service_id, service in services.items():
        if isinstance(service, str):
            service = _FixedReplyChatCompletion(
                ai_model_id=service, service_id=service_id
            )
        kernel.add_service(service)
    return kernel


def _bare_settings():
    """Un ``settings`` minimal : les méthodes ne lisent que la clé OpenAI.

    Sans cette doublure, le test dépendrait du ``.env`` de la machine — et en
    CI (keyless) les deux méthodes rendraient un dict d'erreur, donc le test
    mesurerait un chemin qui n'a rien à voir.
    """
    return types.SimpleNamespace(
        openai=types.SimpleNamespace(api_key=_secret("sk-test-not-a-real-key"))
    )


def _secret(value: str):
    from pydantic import SecretStr

    return SecretStr(value)


def _manager(monkeypatch, kernel, service_id: Optional[str] = "openai"):
    """Un manager dont le kernel et le champ d'id sont imposés par le test."""
    import argumentation_analysis.orchestration.service_manager as sm

    mgr = sm.OrchestrationServiceManager(enable_logging=False)
    monkeypatch.setattr(sm, "settings", _bare_settings())
    mgr.kernel = kernel
    mgr.llm_service_id = service_id
    # Les deux méthodes refusent de s'exécuter sans leur manager — c'est un
    # autre contrat que celui-ci, on le satisfait sans le simuler.
    mgr.tactical_manager = object()
    mgr.operational_manager = object()
    return mgr


def test_the_harness_offers_nothing_the_real_kernel_lacks():
    """Le contrôle de #2389 DoD 5, en une assertion.

    Le harnais passe au code l'objet ``sk.Kernel`` lui-même : il ne peut donc
    exposer aucune méthode que la classe réelle n'a pas. Si quelqu'un
    réintroduisait une doublure de kernel ici, ce test nommerait l'écart.
    """
    kernel = _kernel({"openai": "modele-quelconque"})
    assert type(kernel) is sk.Kernel
    assert not hasattr(kernel, "create_function_from_prompt")


# ===========================================================================
# 1. La mesure — le champ nomme le modèle servi
# ===========================================================================


@pytest.mark.parametrize("method_name", _METHODS)
@pytest.mark.parametrize("served", ["mock_model", "openai/gpt-5.6-pro"])
async def test_the_result_names_the_model_the_kernel_served(
    monkeypatch, method_name, served
):
    """Le né-rouge de #2377, en une assertion.

    Sur ``b5845b6d`` les deux méthodes rendent ``"model": "gpt-5.6-luna"``
    quelle que soit la valeur servie : les deux paramètres rougissent, en
    valeur de modèle, en nommant la valeur fausse. Sur ``bdc5b618`` (kernel
    réel, #2389) elles rougissent plus tôt : ``status == "error"`` sur
    l'``AttributeError`` que l'ancienne doublure masquait.
    """
    assert served != "gpt-5.6-luna", "un cas qui coïncide ne mesure rien"

    mgr = _manager(monkeypatch, _kernel({"openai": served}))

    result = await getattr(mgr, method_name)("texte synthétique", None)

    assert result["status"] == "completed", f"chemin non mesuré: {result}"
    assert result["llm_response"] == _REPLY, "le kernel n'a pas servi"
    assert result["model"] == served, (
        f"le résultat annonce {result['model']!r} alors que le kernel a servi "
        f"{served!r}"
    )


@pytest.mark.parametrize("method_name", _METHODS)
async def test_the_field_follows_the_real_factory_product(monkeypatch, method_name):
    """Le champ suit le produit de la fabrique réelle, pas une constante du test.

    ``force_mock=True`` prend le chemin réel de ``create_llm_service`` et rend
    un service déterministe : c'est ce service-là, et lui seul, que le résultat
    doit annoncer.
    """
    from argumentation_analysis.core.llm_service import create_llm_service

    service = create_llm_service(service_id="openai", force_mock=True)
    assert service.ai_model_id != "gpt-5.6-luna", "le produit mesuré coïncide"

    mgr = _manager(monkeypatch, _kernel({"openai": service}))

    result = await getattr(mgr, method_name)("texte synthétique", None)

    assert result["status"] == "completed", f"chemin non mesuré: {result}"
    assert result["model"] == service.ai_model_id


# ===========================================================================
# 2. L'absence — rien d'observable ⇒ pas de clé (et pas de vacuité)
# ===========================================================================


@pytest.mark.parametrize("method_name", _METHODS)
async def test_the_field_is_absent_when_no_service_id_is_held(monkeypatch, method_name):
    """Le second terme du contrat : « ou il disparaît ».

    Le chemin nominal reste intact (le kernel répond, le résultat est complet)
    et seule l'observabilité est retirée — sinon l'absence serait celle d'un
    dict d'erreur, et la garde verdirait à vide.

    Le cas « id de service inconnu du kernel » n'est plus ici : depuis #2389 le
    service est épinglé, un id inconnu échoue au lieu de servir par un autre
    service (``test_service_manager_kernel_api_2389.py``).
    """
    mgr = _manager(
        monkeypatch, _kernel({"openai": "openai/gpt-5.6-pro"}), service_id=None
    )

    result = await getattr(mgr, method_name)("texte synthétique", None)

    assert result["status"] == "completed", f"cas vacant: {result}"
    assert result["llm_response"] == _REPLY, f"cas vacant: {result}"
    assert "model" not in result, (
        f"la clé est présente alors que rien n'est observable "
        f"({result.get('model')!r}) — un None se confond avec « pas de modèle »"
    )


@pytest.mark.parametrize(
    "held",
    ["service_without_model_id", "unknown_service_id"],
)
def test_the_observation_is_none_when_the_service_says_nothing(held):
    """``_served_model_id`` n'invente rien quand le service ne dit rien.

    Un service réel ne peut pas être construit sans ``ai_model_id`` (SK le
    refuse) : ce cas se mesure donc sur l'observateur seul, avec un kernel
    **contraint à la classe réelle** (``create_autospec``) — une doublure qui
    ne peut rien offrir que ``Kernel`` n'offre pas.
    """
    import argumentation_analysis.orchestration.service_manager as sm

    kernel = create_autospec(sk.Kernel, instance=True)
    if held == "service_without_model_id":
        kernel.get_service.return_value = types.SimpleNamespace()
    else:
        kernel.get_service.side_effect = KernelServiceNotFoundError("absent")

    mgr = sm.OrchestrationServiceManager(enable_logging=False)
    mgr.kernel = kernel
    mgr.llm_service_id = "openai"

    assert mgr._served_model_id() is None
    kernel.get_service.assert_called_once_with("openai")


# ===========================================================================
# 3. Le champ d'id de service ne nomme pas un modèle
# ===========================================================================


def test_the_service_id_field_holds_a_service_id():
    """``llm_service_id`` est une clé de kernel, pas un id de modèle.

    Il valait ``"gpt-5.6-luna"`` — un modèle dans un champ d'id de service, que
    ``initialize()`` écrasait de toute façon par ``"openai"``. Les deux
    assertions ci-dessous sont le contrat : la valeur vient de la même source
    que celle de l'initialisation, et elle se comporte comme un id de service.
    """
    from argumentation_analysis.config.settings import settings
    from argumentation_analysis.core.llm_service import create_llm_service
    from argumentation_analysis.orchestration.service_manager import (
        OrchestrationServiceManager,
    )

    mgr = OrchestrationServiceManager(enable_logging=False)

    assert mgr.llm_service_id == settings.service_manager.default_llm_service_id
    assert not _MODEL_LIKE.match(
        mgr.llm_service_id
    ), f"{mgr.llm_service_id!r} a la forme d'un id de modèle"
    # Non-vacuité : la valeur est bien une clé de service, pas un nom quelconque
    # que le kernel refuserait de servir.
    assert create_llm_service(service_id=mgr.llm_service_id, force_mock=True).service_id


def test_the_default_model_surfaces_agree(monkeypatch):
    """DoD item 4, terme d'accord : les surfaces qui décident le défaut concordent.

    ``gpt-5.6-luna`` vivait sur quatre surfaces hors résolveur. Deux défauts qui
    divergent coupent une flotte en deux modèles sans que rien ne rougisse. Ce
    test est un **contrôle d'accord** : sur ``b5845b6d`` les quatre surfaces
    portaient la même valeur, il est donc vert des deux côtés. Ce qui suit
    mesure la duplication elle-même.
    """
    import inspect

    from argumentation_analysis.config.settings import (
        OpenAISettings,
        ServiceManagerSettings,
    )
    from argumentation_analysis.core.llm_service import resolve_chat_endpoint

    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)

    # Les défauts *de code* : l'env est neutralisé et ``.env`` ignoré, sinon on
    # mesurerait la configuration de la machine au lieu de la déclaration.
    declared = {
        "OpenAISettings.chat_model_id": OpenAISettings(_env_file=None).chat_model_id,
        "ServiceManagerSettings.default_model_id": ServiceManagerSettings(
            _env_file=None
        ).default_model_id,
        "resolve_chat_endpoint(default_model=)": (
            inspect.signature(resolve_chat_endpoint).parameters["default_model"].default
        ),
        "resolve_chat_endpoint() sur un siège vide": resolve_chat_endpoint()[2],
    }

    assert len(set(declared.values())) == 1, declared


def test_the_default_literal_is_declared_once_in_the_resolver_family():
    """DoD item 4, terme de comptage : le littéral n'est plus recopié.

    Un accord entre copies ne prouve rien sur leur nombre : c'est la
    **duplication** qui rend la divergence possible. Le test compte donc les
    littéraux de modèle dans les deux fichiers de la famille (les déclarations
    de settings et tout le repli de ``core/llm_service.py``) : sur ``b5845b6d``
    il y en avait **7** — trois champs pydantic, les deux cibles de la table
    #1930, le défaut du résolveur, le repli de ``create_llm_service`` — et il
    n'en reste qu'un, la déclaration unique.

    La valeur comparée vient du résolveur lui-même : aucun symbole neuf n'est
    importé, donc ce né-rouge est en **valeur de comptage**, pas en import.
    """
    import inspect

    from argumentation_analysis.core.llm_service import resolve_chat_endpoint

    default = (
        inspect.signature(resolve_chat_endpoint).parameters["default_model"].default
    )
    assert isinstance(default, str) and default
    family = (
        Path(CORE_ROOT) / "config" / "settings.py",
        Path(CORE_ROOT) / "core" / "llm_service.py",
    )

    literals: List[str] = []
    for rel in family:
        source = (REPO_ROOT / rel).read_text(encoding="utf-8-sig")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and node.value == default:
                literals.append(f"{rel}:{node.lineno}")

    assert len(literals) == 1, (
        f"le défaut {default!r} est déclaré {len(literals)} fois dans la famille "
        f"du résolveur : {literals} — deux copies peuvent diverger en silence"
    )


def test_the_single_default_is_a_named_constant(monkeypatch):
    """Le mécanisme, épinglé par son nom : une constante importable.

    Sans cette assertion, supprimer la constante et ré-inliner un unique
    littéral laisserait les deux tests précédents verts — l'unicité
    disparaîtrait avec le nom, et la duplication pourrait recommencer. ``is``
    plutôt que ``==`` : c'est le **même objet**, donc la même déclaration.

    Pré-réparation, ce test échoue en **import** et non en valeur : le symbole
    qu'il épingle est précisément celui que la réparation introduit. C'est le
    seul du fichier dans ce cas, et il ne masque rien — les échecs de valeur
    sont dans les tests qui précèdent.
    """
    from argumentation_analysis.config.settings import (
        DEFAULT_CHAT_MODEL_ID,
        OpenAISettings,
        ServiceManagerSettings,
    )

    # L'environnement prime sur le défaut de classe : sans ce vidage on
    # mesurerait ``OPENAI_CHAT_MODEL_ID`` (posé par le harnais) au lieu de la
    # déclaration. ``_env_file=None`` ne suffit pas — il ferme le fichier, pas
    # ``os.environ``.
    for var in _ROUTE_VARS:
        monkeypatch.delenv(var, raising=False)

    assert OpenAISettings(_env_file=None).chat_model_id is DEFAULT_CHAT_MODEL_ID
    assert (
        ServiceManagerSettings(_env_file=None).default_model_id is DEFAULT_CHAT_MODEL_ID
    )


# ===========================================================================
# 3 bis. La quatrième surface, mesurée dans un processus réel
# ===========================================================================

# ``create_llm_service`` court-circuite vers un mock dès que
# ``PYTEST_CURRENT_TEST`` est posé : le repli de la fabrique ne peut donc pas
# être mesuré *dans* pytest. Le siège est imposé dans un processus jetable,
# après les imports — l'ordre inverse laisserait ``.env`` décider du cas.
#
# Ce driver ne remplace aucun client, délibérément : ``create_llm_service``
# **n'appelle rien**. Il lit l'environnement et construit un client (creation
# d'un ``httpx.AsyncClient``, aucune connexion) ; la seule chose mesurée est le
# ``ai_model_id`` que la fabrique a résolu. Un enregistreur ne mesurerait rien
# de plus, et patcher ``openai.AsyncOpenAI`` après l'import laisserait la
# liaison locale ``from openai import AsyncOpenAI`` (llm_service.py, L12)
# intacte — un siège qui ne s'applique pas.
_SEAT_DRIVER = r"""
import json
import os
import sys
from pathlib import Path

root = Path(os.environ["_SEAT_ROOT"])
sys.path.insert(0, str(root))

from argumentation_analysis.core.llm_service import create_llm_service

for _var in json.loads(os.environ["_SEAT_UNSET"]):
    os.environ.pop(_var, None)
os.environ["OPENAI_API_KEY"] = "sk-not-a-real-key"

service = create_llm_service(service_id="openai")

Path(os.environ["_SEAT_OUT"]).write_text(
    json.dumps({"ai_model_id": service.ai_model_id, "type": type(service).__name__}),
    encoding="utf-8",
)
"""


def _measure_factory_fallback(tmp_path: Path) -> Dict[str, Any]:
    unset = list(_ROUTE_VARS) + ["LLM_CACHE_MODE"]
    out = tmp_path / "seat_2377.json"
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in unset and not key.startswith("PYTEST_")
    }
    env.update(
        {
            "_SEAT_ROOT": str(REPO_ROOT),
            "_SEAT_OUT": str(out),
            "_SEAT_UNSET": json.dumps(unset),
            "PYTHONPATH": str(REPO_ROOT),
        }
    )
    proc = subprocess.run(
        [sys.executable, "-c", _SEAT_DRIVER],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert out.exists(), (
        f"le driver de siège n'a rien écrit (rc={proc.returncode}).\n"
        f"--- stdout ---\n{proc.stdout[-2000:]}\n--- stderr ---\n{proc.stderr[-4000:]}"
    )
    return json.loads(out.read_text(encoding="utf-8"))


def test_the_factory_fallback_renders_the_same_default(tmp_path):
    """Le repli de ``create_llm_service`` rend le défaut unique, pas un autre.

    C'est aussi le contrôle d'accord : ce chemin était déjà correct avant la
    réparation (la copie portait la même valeur), donc ce test est vert des
    deux côtés — sa fonction est d'empêcher la re-divergence, pas de rougir.
    """
    from argumentation_analysis.config.settings import DEFAULT_CHAT_MODEL_ID

    measured = _measure_factory_fallback(tmp_path)

    # Non-vacuité : la fabrique a bien rendu un service porteur de ce champ
    # (le cache LLM est neutralisé, sinon on mesurerait l'enveloppe).
    assert measured["ai_model_id"], measured
    assert not measured["type"].startswith("Cached"), measured
    assert measured["ai_model_id"] == DEFAULT_CHAT_MODEL_ID
    assert measured["ai_model_id"] != "default", (
        "un littéral « default » est arrivé jusqu'à ai_model_id : c'est le nom "
        "de modèle que le site de câblage envoyait à l'API"
    )


# ===========================================================================
# 4. Les gardes structurelles
# ===========================================================================


def _core_sources() -> List[Tuple[str, str]]:
    """Les sources suivies des cinq racines du dépôt.

    #2377 naissait sur ``argumentation_analysis/`` seule ; #2381 étend la marche
    à ``api/``, ``scripts/``, ``project_core/`` et ``config/`` : la classe
    provenance-par-littéral y vivait hors périmètre, ni réparée ni silencieuse.
    ``git ls-files`` et non la marche disque (le dossier de travail contient des
    artefacts ignorés), et ``utf-8-sig`` : trois fichiers du dépôt portent un BOM
    et un lecteur en ``utf-8`` meurt dessus au lieu de mesurer (#2373).
    """
    sources: List[Tuple[str, str]] = []
    for root in CORE_ROOTS:
        listed = subprocess.run(
            ["git", "ls-files", "--", root],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        sources.extend(
            (rel, (REPO_ROOT / rel).read_text(encoding="utf-8-sig"))
            for rel in listed
            if rel.endswith(".py")
        )
    return sources


def _model_like(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and bool(_MODEL_LIKE.match(node.value))
    )


def _provenance_from_local_literal(source: str, path: str) -> List[str]:
    """Les dicts dont une clé de provenance vient d'un littéral de modèle local.

    Deux formes, la seconde étant celle de #2377 : la valeur est un *nom*, et ce
    nom a été lié dans la même fonction à un littéral de modèle. Interdire la
    seule forme littérale aurait laissé passer le motif exact qu'on répare.
    """
    hits: List[str] = []
    for func in ast.walk(ast.parse(source)):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        bound: Dict[str, str] = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and _model_like(node.value):
                    bound[target.id] = node.value.value
        for node in ast.walk(func):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if not (
                    isinstance(key, ast.Constant) and key.value in _PROVENANCE_KEYS
                ):
                    continue
                if _model_like(value):
                    hits.append(
                        f"{path}:{value.lineno} {key.value!r} = {value.value!r}"
                    )
                elif isinstance(value, ast.Name) and value.id in bound:
                    hits.append(
                        f"{path}:{value.lineno} {key.value!r} = {value.id} "
                        f"(lié à {bound[value.id]!r} ligne {value.lineno})"
                    )
    return hits


def _fabricated_factory_models(source: str, path: str) -> List[str]:
    """Les ``create_llm_service(..., model_id="littéral")``.

    Un id de modèle écrit en dur à la fabrique est un modèle que **aucun**
    résolveur n'a choisi : la configuration ne peut plus le changer, et la
    provenance qu'il produit est vraie par accident. Le siège se règle par
    l'environnement, jamais par un argument littéral.
    """
    hits: List[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        )
        if name != "create_llm_service":
            continue
        for keyword in node.keywords:
            if keyword.arg == "model_id" and isinstance(keyword.value, ast.Constant):
                hits.append(f"{path}:{keyword.value.lineno} = {keyword.value.value!r}")
    return hits


# --- contrôles positifs : la garde voit le motif qu'elle remplace ----------

_PRISTINE_PROVENANCE = """
def analysis(kernel):
    model = "gpt-5.6-luna"
    return {"status": "completed", "model": model}
"""

_PRISTINE_WIRING = """
service = create_llm_service(service_id="default", model_id="gpt-4-turbo-2024-04-09")
"""


def test_the_provenance_guard_catches_the_pattern_it_replaced():
    hits = _provenance_from_local_literal(_PRISTINE_PROVENANCE, "<control>")

    assert len(hits) == 1, hits
    assert "model" in hits[0] and "gpt-5.6-luna" in hits[0], hits


def test_the_provenance_guard_catches_the_literal_form_too():
    """La forme directe, qu'aucun site ne portait encore : la garde la voit."""
    source = 'def f():\n    return {"model_used": "gpt-5.6-luna"}\n'

    assert _provenance_from_local_literal(source, "<control>")


def test_the_provenance_guard_spares_an_observed_value():
    """Contrôle négatif : une provenance observée n'est pas un littéral."""
    source = 'def f(kernel):\n    return {"model": kernel.ai_model_id}\n'

    assert _provenance_from_local_literal(source, "<control>") == []


def test_the_factory_guard_catches_a_hardcoded_model():
    hits = _fabricated_factory_models(_PRISTINE_WIRING, "<control>")

    assert len(hits) == 1 and "gpt-4-turbo" in hits[0], hits


# --- les gardes elles-mêmes ------------------------------------------------


def test_no_result_dict_takes_its_provenance_from_a_local_literal():
    sources = _core_sources()
    # #2381 : la marche couvre les cinq racines (989 fichiers mesurés à
    # l'adoption — 569 pour le seul noyau avant extension).
    assert len(sources) > 800, (
        f"la marche n'a vu que {len(sources)} fichiers — une marche cassée ne "
        "certifie aucune absence"
    )

    hits = [h for rel, src in sources for h in _provenance_from_local_literal(src, rel)]

    assert hits == [], (
        "une provenance est alimentée par un littéral local au lieu d'être "
        f"observée (#2377) : {hits}"
    )


def test_no_factory_call_hardcodes_a_model_id():
    sources = _core_sources()

    hits = [h for rel, src in sources for h in _fabricated_factory_models(src, rel)]

    assert hits == [], f"un modèle est figé à la fabrique de service (#2377) : {hits}"
