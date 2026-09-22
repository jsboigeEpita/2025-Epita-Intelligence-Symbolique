"""#2389 — les analyses tactique et opérationnelle passent par un vrai ``Kernel``.

Le défaut, mesuré sur ``bdc5b618`` : ``_run_tactical_analysis`` et
``_run_operational_analysis`` appelaient ``kernel.create_function_from_prompt``,
qui **n'existe pas** sur ``semantic_kernel.Kernel`` (``False`` en SK 1.35 et
1.40). Chaque analyse rendait ``{"status": "error", "error": "'Kernel' object
has no attribute ..."}`` — une ligne **avant** la provenance de #2377, que ses
tests certifiaient pourtant verte parce que leur doublure de kernel implémentait
l'API absente.

Le harnais est donc l'objet réel : un ``sk.Kernel`` et, à la seule feuille qui
ferait un egress, un service de chat qui **capture** le prompt rendu (même
harnais que ``test_fol_lifecycle_and_dialect_2360.py``). Rien ici ne peut offrir
au code une méthode que ``Kernel`` n'a pas.

Mesuré, et né-rouge sur ``bdc5b618`` **en valeur** (``status == "error"``,
jamais un ``ImportError``) :

1. le texte analysé atteint le prompt que le service reçoit ;
2. un ``{{...}}`` présent dans le texte arrive tel quel — il est un argument,
   pas une expression du moteur de templates ;
3. le prompt est servi par le service que la provenance nomme, même quand un
   autre service est enregistré avant lui (témoin : sans épinglage, SK sert le
   premier) ;
4. un ``llm_service_id`` que le kernel ne tient pas échoue, au lieu de basculer
   en silence sur un autre service ;
5. ``prompt_used`` est le prompt rendu, jamais le template.
"""

import types
from typing import Any, List

import pytest
import semantic_kernel as sk
from pydantic import Field
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

_METHODS = ("_run_tactical_analysis", "_run_operational_analysis")

_REPLY = "réponse capturée #2389"

# Un marqueur que seul le texte d'entrée porte : sa présence dans le prompt
# rendu prouve que l'argument a été transmis, pas que le template a été envoyé.
_MARKER = "Marqueur-synthetique-2389"


class PromptCapturingChatCompletion(ChatCompletionClientBase):
    """Service factice : enregistre chaque prompt reçu, répond un texte fixe."""

    rendered_prompts: List[str] = Field(default_factory=list)

    async def _inner_get_chat_message_contents(
        self, chat_history: ChatHistory, settings: Any
    ) -> List[ChatMessageContent]:
        self.rendered_prompts.append("\n".join(str(m) for m in chat_history.messages))
        return [
            ChatMessageContent(
                role="assistant", content=_REPLY, ai_model_id=self.ai_model_id
            )
        ]


def _service(service_id: str, model_id: str) -> PromptCapturingChatCompletion:
    return PromptCapturingChatCompletion(ai_model_id=model_id, service_id=service_id)


def _kernel(*services: PromptCapturingChatCompletion) -> sk.Kernel:
    kernel = sk.Kernel()
    for service in services:
        kernel.add_service(service)
    return kernel


def _manager(monkeypatch, kernel: sk.Kernel, service_id: str):
    """Un manager sur un kernel réel ; seule la clé lue par les méthodes est posée."""
    from pydantic import SecretStr

    import argumentation_analysis.orchestration.service_manager as sm

    mgr = sm.OrchestrationServiceManager(enable_logging=False)
    # Les méthodes refusent de s'exécuter sans clé OpenAI dans les settings :
    # sans cette doublure, le test mesurerait le .env de la machine.
    monkeypatch.setattr(
        sm,
        "settings",
        types.SimpleNamespace(
            openai=types.SimpleNamespace(api_key=SecretStr("sk-test-not-a-real-key"))
        ),
    )
    mgr.kernel = kernel
    mgr.llm_service_id = service_id
    mgr.tactical_manager = object()
    mgr.operational_manager = object()
    return mgr


def test_the_premise_the_dead_api_is_absent_from_the_real_kernel():
    """La prémisse de #2389, re-mesurée à chaque exécution.

    Si une version de SK ajoutait ``create_function_from_prompt``, le défaut
    réparé ici changerait de nature — ce test le dirait avant qu'un audit ne
    conclue d'une mesure périmée.
    """
    assert not hasattr(sk.Kernel, "create_function_from_prompt")
    assert hasattr(sk.Kernel, "add_function")


@pytest.mark.parametrize("method_name", _METHODS)
async def test_the_analysis_text_reaches_the_served_prompt(monkeypatch, method_name):
    service = _service("openai", "modele-capture-2389")
    mgr = _manager(monkeypatch, _kernel(service), "openai")

    result = await getattr(mgr, method_name)(f"Un texte portant {_MARKER}.", None)

    assert result["status"] == "completed", f"analyse non aboutie: {result}"
    assert result["llm_response"] == _REPLY
    assert len(service.rendered_prompts) == 1, service.rendered_prompts
    assert _MARKER in service.rendered_prompts[0]
    # Le slot a été rendu : le template ne part pas tel quel vers le modèle.
    assert "{{$input}}" not in service.rendered_prompts[0]


@pytest.mark.parametrize("method_name", _METHODS)
async def test_a_template_expression_in_the_text_stays_literal(
    monkeypatch, method_name
):
    """Le texte est un argument, jamais une expression du moteur SK.

    Interpolé dans le template avant rendu (l'ancienne f-string), ``{{$input}}``
    aurait été lu par le moteur et remplacé, et une variable inconnue rendue
    vide.
    """
    service = _service("openai", "modele-capture-2389")
    mgr = _manager(monkeypatch, _kernel(service), "openai")
    text = _MARKER + " cite {{$input}} et {{$inconnue}} tels quels."

    result = await getattr(mgr, method_name)(text, None)

    assert result["status"] == "completed", f"analyse non aboutie: {result}"
    assert text in service.rendered_prompts[0]


@pytest.mark.parametrize("method_name", _METHODS)
async def test_the_prompt_is_served_by_the_service_the_provenance_names(
    monkeypatch, method_name
):
    first = _service("premier", "modele-premier")
    pinned = _service("openai", "modele-epingle")
    mgr = _manager(monkeypatch, _kernel(first, pinned), "openai")

    result = await getattr(mgr, method_name)(f"Texte {_MARKER}.", None)

    assert result["status"] == "completed", f"analyse non aboutie: {result}"
    assert len(pinned.rendered_prompts) == 1
    assert first.rendered_prompts == [], "le prompt a été servi par un autre service"
    assert result["model"] == "modele-epingle"


async def test_the_witness_an_unpinned_prompt_goes_to_the_first_service():
    """Témoin : sans épinglage, SK sert le PREMIER service enregistré.

    Sans ce témoin, le test précédent pourrait verdir parce que SK choisirait
    de toute façon le bon service — l'épinglage ne serait alors pas mesuré.
    """
    from semantic_kernel.functions import KernelArguments

    first = _service("premier", "modele-premier")
    pinned = _service("openai", "modele-epingle")
    kernel = _kernel(first, pinned)
    function = kernel.add_function(
        plugin_name="temoin_2389", function_name="temoin", prompt="{{$input}}"
    )

    await kernel.invoke(function, KernelArguments(input=_MARKER))

    assert len(first.rendered_prompts) == 1
    assert pinned.rendered_prompts == []


@pytest.mark.parametrize("method_name", _METHODS)
async def test_an_unknown_service_id_fails_instead_of_switching(
    monkeypatch, method_name
):
    other = _service("autre", "modele-autre")
    mgr = _manager(monkeypatch, _kernel(other), "openai")

    result = await getattr(mgr, method_name)(f"Texte {_MARKER}.", None)

    assert result["status"] == "error", f"bascule silencieuse: {result}"
    # L'échec est celui de l'invocation par le kernel (le service épinglé est
    # introuvable), pas une erreur survenue avant d'atteindre le kernel.
    assert "service_manager_analysis" in result["error"], result["error"]
    assert other.rendered_prompts == [], "un autre service a servi le prompt"
    assert "model" not in result


@pytest.mark.parametrize("method_name", _METHODS)
async def test_prompt_used_is_the_rendered_prompt(monkeypatch, method_name):
    service = _service("openai", "modele-capture-2389")
    mgr = _manager(monkeypatch, _kernel(service), "openai")

    result = await getattr(mgr, method_name)(f"Texte {_MARKER}.", None)

    assert result["status"] == "completed", f"analyse non aboutie: {result}"
    assert _MARKER in result["prompt_used"]
    assert "{{$input}}" not in result["prompt_used"]
