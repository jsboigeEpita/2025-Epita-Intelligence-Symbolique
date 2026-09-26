# -*- coding: utf-8 -*-
"""#2588 review-2 (option) — le SUJET du débat décide la langue, une fois.

Un tour généré peut être court : le détecteur n'y tranche alors rien, et la
lisibilité du tour était perdue (``None``). Le sujet, lui, est le texte long et
stable que l'agent détient — c'est à lui de décider.

Ce témoin vit dans son propre fichier, et pas avec les autres témoins #2588 :
il construit un noyau Semantic Kernel, ce que ``tests/conftest.py`` repère pour
marquer ATOUT le fichier ``llm_integration`` (mock LLM désactivé). Les témoins
d'instruments, eux, n'ont aucune raison de perdre leur mock — le marqueur reste
ici, sur le seul test qui touche au noyau.

Aucun appel LLM : la génération est doublée (``_generate_via_kernel``), le
chemin mesuré est l'analyse locale des métriques.
"""

from unittest.mock import AsyncMock, patch

import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from textstat.textstat import textstatistics

from argumentation_analysis.agents.core.debate.debate_agent import DebateAgent
from argumentation_analysis.agents.core.debate.debate_definitions import (
    ArgumentType,
    DebatePhase,
    DebateState,
)

# 21 mots : mesuré « fr » par le détecteur.
FR_TOPIC = (
    "Faut-il réduire les impôts pour relancer l'économie du pays, ou faut-il "
    "au contraire les augmenter pour financer les services publics ?"
)
# 6 mots : mesuré « unknown » — le seuil est de 3 mots-outils. Flesch fr 90.51
# contre en 73.85 : les deux échelles se distinguent sur ce tour.
SHORT_FR_TURN = "Il faut peut-être baisser les impôts."


def _expected_readability(language: str) -> float:
    """L'échelle attendue, mesurée par un instrument INDÉPENDANT.

    Une instance ``textstatistics`` réglée à la main, pas le module sous test :
    le témoin vérifie la valeur, pas la cohérence du module avec lui-même.
    """
    instrument = textstatistics()
    instrument.set_lang(language)
    return max(0.0, min(1.0, instrument.flesch_reading_ease(SHORT_FR_TURN) / 100))


@pytest.fixture
def agent():
    kernel = Kernel()
    # Clé factice : la génération est doublée juste en dessous, rien ne sort.
    kernel.add_service(
        OpenAIChatCompletion(
            service_id="default", ai_model_id="gpt-4", api_key="test-key"
        )
    )
    return DebateAgent(
        kernel=kernel, agent_name="Test", personality="test", position="for"
    )


@pytest.fixture
def state():
    return DebateState(
        topic=FR_TOPIC,
        agents=["Test"],
        arguments=[],
        current_turn=0,
        max_turns=10,
        phase=DebatePhase.MAIN_ARGUMENTS,
    )


async def test_short_turn_inherits_the_topics_flesch_scale(agent, state):
    with patch.object(
        agent,
        "_generate_via_kernel",
        new_callable=AsyncMock,
        return_value=SHORT_FR_TURN,
    ):
        argument = await agent.generate_argument(state, ArgumentType.EVIDENCE)

    assert argument.metrics.readability_score is not None
    assert argument.metrics.readability_score == pytest.approx(
        _expected_readability("fr")
    )
    # ...et l'échelle anglaise rend un autre nombre : la langue est bien celle
    # du sujet, pas un défaut.
    assert argument.metrics.readability_score != pytest.approx(
        _expected_readability("en")
    )


async def test_no_decidable_topic_still_leaves_the_wording_metrics_measured(
    agent,
):
    """Contre-pendule : un sujet indécidable ne fabrique pas de langue.

    Le sujet muet laisse ``lang`` à ``None`` ; la lisibilité d'un tour court
    reste alors absente (aucune formule à choisir, comportement d'origine),
    mais le reste des métriques continue de mesurer — on ne remplace pas une
    absence honnête par une langue devinée.
    """
    undecidable = DebateState(
        topic="zzqq xxvv kkww",
        agents=["Test"],
        arguments=[],
        current_turn=0,
        max_turns=10,
        phase=DebatePhase.MAIN_ARGUMENTS,
    )
    with patch.object(
        agent,
        "_generate_via_kernel",
        new_callable=AsyncMock,
        return_value=SHORT_FR_TURN,
    ):
        argument = await agent.generate_argument(undecidable, ArgumentType.EVIDENCE)

    assert argument.metrics.readability_score is None
    assert argument.metrics.fact_check_score == 0.7
