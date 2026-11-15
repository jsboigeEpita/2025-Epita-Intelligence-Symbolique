# -*- coding: utf-8 -*-
"""#3573 — le prompt servi à l'agent informel de l'usine ne nomme que des
fonctions que l'invocation offre réellement.

Mesuré (run 43594335153, 14/11) : sur la chaîne des tests authentiques —
``AgentFactory → InformalFallacyAgent (config "simple") → analyze_text →
invoke_single`` — le modèle recevait le prompt système V15 complet, dont la
section « Fonctions Outils Disponibles » nomme ``StateManager.*`` et
``InformalAnalyzer.*``, alors que la requête partait sans AUCUN outil :
Semantic Kernel n'annonce des fonctions au modèle que si
``function_choice_behavior`` est réglé (site-packages, ``chat_completion_client_base.py``
: ``if settings.function_choice_behavior and kernel: … configure(…)``), et
``invoke_single`` ne le règle pas — les plugins alors montés n'exposent de
toute façon pas ces fonctions. Le modèle a refusé (« Je ne peux pas exécuter
l'analyse demandée … car les fonctions d'outils (`InformalAnalyzer.*` et
`StateManager.*`) ne sont pas disponibles dans cette conversation »).

Le témoin pince la correspondance prompt ↔ outils offerts, sans LLM et sans
clé : il reconstruit l'invocation exacte des tests authentiques (même usine,
même config) en détournant le connecteur à la frontière où Semantic Kernel a
fini d'assembler la requête (``_inner_get_chat_message_contents``, après le
deepcopy des settings et l'éventuel ``configure`` du function choice
behavior), puis exige que chaque fonction que le prompt nomme soit dans
l'ensemble que la requête offre.
"""

import re

import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.agents.factory import AgentFactory, AgentType

# Texte générique synthétique (aucun contenu du corpus, discipline #2841).
SAMPLE_TEXT = (
    "Le porte-parole affirme que ses détracteurs sont de mauvaise foi, donc "
    "leurs critiques sont sans valeur, et conclut qu'il faut soit tout "
    "accepter de son plan, soit tout rejeter."
)

_WITNESS_MODEL = "witness-model"
_WITNESS_SERVICE = "default_llm_service"


class _ConnectorCapture:
    """Fait office de ``_inner_get_chat_message_contents`` : capture la
    requête assemblée (settings finaux + historique) et répond sans réseau."""

    def __init__(self):
        self.settings = None
        self.prompt = None

    async def __call__(self, chat_history, settings):
        self.settings = settings
        self.prompt = "\n".join(
            str(getattr(message, "content", "") or "")
            for message in chat_history.messages
        )
        return [
            ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content="",
                ai_model_id=_WITNESS_MODEL,
            )
        ]


def _factory_agent_with_capture(monkeypatch) -> tuple:
    """L'agent exact des tests authentiques, sur un connecteur détourné."""
    kernel = sk.Kernel()
    service = OpenAIChatCompletion(
        ai_model_id=_WITNESS_MODEL,
        service_id=_WITNESS_SERVICE,
        api_key="witness-no-network",
    )
    kernel.add_service(service)
    capture = _ConnectorCapture()
    monkeypatch.setattr(service, "_inner_get_chat_message_contents", capture)
    agent = AgentFactory(kernel, llm_service_id=_WITNESS_SERVICE).create_agent(
        AgentType.INFORMAL_FALLACY, config_name="simple"
    )
    return agent, capture


_BACKTICKED = re.compile(r"`([^`\n]+)`")
_QUALIFIED = re.compile(r"^([A-Za-z_]\w*)\.([^(\s]+)")
_BARE_NAME = re.compile(r"[A-Za-z_]\w*$")


def _tool_functions_named_in(prompt: str) -> tuple:
    """Les fonctions que le prompt désigne comme outils.

    Rend ``(paires_qualifiées, noms_nus_appelés)`` : un token entre
    backticks compte comme fonction nommée s'il est qualifié
    (``Plugin.fonction`` ou ``Plugin.*``), ou s'il est nu ET appelé avec des
    parenthèses quelque part dans le prompt. Les tokens non appelés
    (``task_id``, ``error``…) ne sont pas des fonctions.
    """
    pairs = set()
    bare_candidates = set()
    for token in _BACKTICKED.findall(prompt):
        qualified = _QUALIFIED.match(token)
        if qualified:
            pairs.add(qualified.groups())
        else:
            name = token.split("(")[0].strip()
            if _BARE_NAME.match(name):
                bare_candidates.add(name)
    called = {
        name
        for name in bare_candidates
        if re.search(rf"\b{re.escape(name)}\s*\(", prompt)
    }
    return pairs, called


def _tools_offered_by(settings) -> tuple:
    """L'ensemble que la requête offre, lu sur les settings finaux.

    Rend ``(paires_qualifiées, noms_nus, plugins)`` ; Semantic Kernel sérialise
    chaque fonction offerte en ``Plugin-fonction`` dans ``settings.tools``
    (vide/None quand rien n'est offert — le cas mesuré).
    """
    tools = getattr(settings, "tools", None) or []
    pairs, bare, plugins = set(), set(), set()
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = tool.get("function", {}).get("name", "")
        if not name or "-" not in name:
            continue
        plugin, function = name.split("-", 1)
        pairs.add((plugin, function))
        bare.add(function)
        plugins.add(plugin)
    return pairs, bare, plugins


async def test_served_prompt_names_only_offered_tools(monkeypatch):
    """Témoin #3573 : chaque fonction nommée par le prompt servi est offerte
    par la requête. ROUGE sur main (le prompt nomme StateManager.* et
    InformalAnalyzer.*, la requête n'offre rien), VERT avec la variante sans
    outils."""
    agent, capture = _factory_agent_with_capture(monkeypatch)
    await agent.analyze_text(SAMPLE_TEXT)

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


async def test_served_prompt_still_mandates_the_analysis(monkeypatch):
    """Anti-vacuité : la variante sans outils garde le mandat d'analyse
    (parcours des familles, Règle d'Or) — vert ne veut pas dire prompt vide."""
    agent, capture = _factory_agent_with_capture(monkeypatch)
    await agent.analyze_text(SAMPLE_TEXT)

    for marker in ("PARCOURS SYSTÉMATIQUE", "CHAQUE famille", "Règle d'Or"):
        assert marker in capture.prompt, f"Le prompt servi a perdu : {marker!r}"
    for family in ("Insuffisance", "Influence", "Tricherie", "Obstruction"):
        assert (
            family in capture.prompt
        ), f"Le prompt servi a perdu la famille : {family!r}"


def test_prose_variant_names_no_tool_function():
    """La variante sans outils ne nomme ni plugin ni fonction."""
    from argumentation_analysis.agents.core.informal.informal_definitions import (
        build_informal_agent_instructions,
    )

    prose = build_informal_agent_instructions(tools_available=False)
    pairs, bare = _tool_functions_named_in(prose)
    assert not pairs, f"La variante sans outils nomme des fonctions : {pairs}"
    assert not bare, f"La variante sans outils nomme des fonctions : {bare}"
    assert "StateManager" not in prose
    assert "InformalAnalyzer" not in prose


def test_tool_variant_is_the_module_constant():
    """La variante outils rend exactement la constante du module (substrat
    des gardes existantes : test_informal_taxonomy_injection_600,
    test_taught_designation_targets_2719)."""
    from argumentation_analysis.agents.core.informal.informal_definitions import (
        INFORMAL_AGENT_INSTRUCTIONS,
        build_informal_agent_instructions,
    )

    assert (
        build_informal_agent_instructions(tools_available=True)
        == INFORMAL_AGENT_INSTRUCTIONS
    )


async def test_core_agent_default_instructions_name_no_tools():
    """L'agent du tronc commun sert par défaut la variante sans outils : ses
    invocations (analyze_text → fonctions sémantiques ; chat sans
    function_choice_behavior) n'offrent jamais les fonctions de la V15."""
    from argumentation_analysis.agents.core.informal.informal_agent import (
        InformalAnalysisAgent,
    )

    kernel = sk.Kernel()
    kernel.add_service(
        OpenAIChatCompletion(
            ai_model_id=_WITNESS_MODEL,
            service_id="default",
            api_key="witness-no-network",
        )
    )
    agent = InformalAnalysisAgent(kernel=kernel, agent_name="witness_core")
    pairs, bare = _tool_functions_named_in(agent.instructions)
    assert not pairs, f"Le prompt par défaut nomme des fonctions : {pairs}"
    assert not bare, f"Le prompt par défaut nomme des fonctions : {bare}"
    assert "StateManager" not in agent.instructions
    assert "PARCOURS SYSTÉMATIQUE" in agent.instructions
