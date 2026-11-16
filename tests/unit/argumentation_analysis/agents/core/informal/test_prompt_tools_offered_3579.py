# -*- coding: utf-8 -*-
"""#3579 — le prompt de ``semantic_AnalyzeFallacies`` ne nomme que des fonctions
que son invocation offre réellement.

Un niveau sous #3573. ``InformalAnalysisAgent.analyze_fallacies`` invoque
``InformalAnalyzer.semantic_AnalyzeFallacies`` avec un simple
``KernelArguments(input=...)``, et la fonction a été enregistrée avec les
settings du service (``prompt_settings``, ``agents/core/semantic_setup.py``),
qui ne portent aucun ``function_choice_behavior``. Semantic Kernel n'annonce
donc AUCUNE fonction au modèle. Le template v3
(``prompt_analyze_fallacies_v3_tool_use``) ordonne pourtant quatre appels
d'outils — ``list_fallacy_categories``, ``list_fallacies_in_category``,
``get_fallacy_details``, ``find_fallacy_definition`` — pour valider le nom
avant de répondre en JSON.

Le témoin reconstruit l'invocation de production sur un connecteur détourné et
capture la requête assemblée à la frontière où Semantic Kernel a fini
d'appliquer le function choice behavior (``_inner_get_chat_message_contents``,
après le deepcopy des settings), puis exige que chaque fonction que le prompt
nomme soit dans l'ensemble que la requête offre. L'extracteur de noms est
celui du témoin #3573 (``test_prompt_tools_offered_3573``) : deux copies d'un
même extracteur dériveraient. Aucun LLM n'est appelé, aucune clé n'est requise.
"""

import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.informal.informal_agent import (
    InformalAnalysisAgent,
)
from argumentation_analysis.agents.core.informal.prompts import (
    prompt_analyze_fallacies_v3_tool_use,
)
from tests.unit.argumentation_analysis.agents.core.informal.test_prompt_tools_offered_3573 import (  # noqa: E501
    _ConnectorCapture,
    _tool_functions_named_in,
    _tools_offered_by,
)

# Texte synthétique (aucun contenu du corpus, discipline #2841).
SAMPLE_TEXT = (
    "Le porte-parole affirme que son contradicteur a tort parce qu'il porte un "
    "chapeau, et conclut qu'il faut soit tout accepter de son plan, soit tout "
    "rejeter."
)

_WITNESS_MODEL = "witness-model"
_WITNESS_SERVICE = "default_llm_service"


def _agent_with_capture(monkeypatch):
    """L'agent du tronc commun câblé par le chemin de production, sur un
    connecteur détourné."""
    kernel = sk.Kernel()
    service = OpenAIChatCompletion(
        ai_model_id=_WITNESS_MODEL,
        service_id=_WITNESS_SERVICE,
        api_key="witness-no-network",
    )
    kernel.add_service(service)
    capture = _ConnectorCapture()
    monkeypatch.setattr(service, "_inner_get_chat_message_contents", capture)
    agent = InformalAnalysisAgent(kernel=kernel, agent_name="witness_3579")
    agent.setup_agent_components(llm_service_id=_WITNESS_SERVICE)
    return agent, capture


async def test_served_prompt_names_only_offered_tools(monkeypatch):
    """Témoin #3579 : chaque fonction nommée par le prompt servi est offerte.

    ROUGE sur main (le template v3 nomme les quatre fonctions d'exploration,
    la requête n'offre rien), VERT avec la variante sans outils.
    """
    agent, capture = _agent_with_capture(monkeypatch)
    await agent.analyze_fallacies(SAMPLE_TEXT)

    assert capture.settings is not None, "l'invocation n'a jamais atteint le connecteur"
    named_pairs, named_bare = _tool_functions_named_in(capture.prompt)
    offered_pairs, offered_bare, offered_plugins = _tools_offered_by(capture.settings)

    missing_pairs = sorted(
        f"{plugin}.{function}"
        for plugin, function in named_pairs
        if not (
            function == "*"
            and plugin in offered_plugins  # joker : le plugin doit être offert
            or (plugin, function) in offered_pairs
        )
    )
    missing_bare = sorted(name for name in named_bare if name not in offered_bare)

    assert not missing_pairs and not missing_bare, (
        "Le prompt servi nomme des fonctions outils que l'invocation "
        f"n'offre pas (offertes : {sorted(offered_pairs) or 'aucune'}) — "
        f"qualifiées manquantes : {missing_pairs} ; "
        f"nues manquantes : {missing_bare}"
    )


async def test_the_semantic_call_offers_no_tools(monkeypatch):
    """La cause mesurée : cette invocation n'offre aucune fonction.

    C'est ce fait qui décide la variante du template (nommer des outils
    n'aurait aucun sens ici). S'il change, le choix se réexamine.
    """
    agent, capture = _agent_with_capture(monkeypatch)
    await agent.analyze_fallacies(SAMPLE_TEXT)

    offered_pairs, offered_bare, offered_plugins = _tools_offered_by(capture.settings)
    assert not offered_pairs and not offered_bare and not offered_plugins, (
        "L'invocation de semantic_AnalyzeFallacies offre des fonctions : "
        f"paires={sorted(offered_pairs)} nues={sorted(offered_bare)} "
        f"plugins={sorted(offered_plugins)}"
    )


async def test_served_prompt_keeps_the_json_contract(monkeypatch):
    """Anti-vacuité : la variante servie garde le contrat JSON que
    ``analyze_fallacies`` parse (``{"sophismes": [{"nom", "justification"}]}``)
    et demande toujours le nom le plus spécifique — vert ne veut pas dire
    prompt vide. Le texte analysé figure dans le prompt : la capture est bien
    la requête réelle, slot ``{{$input}}`` résolu.
    """
    agent, capture = _agent_with_capture(monkeypatch)
    await agent.analyze_fallacies(SAMPLE_TEXT)

    for marker in ('"sophismes"', '"nom"', '"justification"'):
        assert marker in capture.prompt, f"Le prompt servi a perdu la clé {marker}"
    for marker in ("RÈGLE D'OR DE LA SPÉCIFICITÉ", "plus spécifique"):
        assert marker in capture.prompt, f"Le prompt servi a perdu : {marker!r}"
    assert SAMPLE_TEXT in capture.prompt, (
        "Le prompt servi ne contient pas le texte analysé : le slot "
        "{{$input}} n'est pas résolu, la capture ne mesure pas la requête."
    )


def test_tool_use_variant_names_the_four_functions():
    """Contrôle de l'extracteur : le template v3 nomme bien les quatre
    fonctions. Sans lui, le rouge du témoin pourrait être une cécité de
    l'extracteur plutôt que le défaut mesuré.
    """
    _pairs, named_bare = _tool_functions_named_in(prompt_analyze_fallacies_v3_tool_use)
    expected = {
        "list_fallacy_categories",
        "list_fallacies_in_category",
        "get_fallacy_details",
        "find_fallacy_definition",
    }
    assert expected <= named_bare, (
        "L'extracteur ne retrouve pas les fonctions nommées par le template "
        f"v3 — manquantes : {sorted(expected - named_bare)}"
    )
