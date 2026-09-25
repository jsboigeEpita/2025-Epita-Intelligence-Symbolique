# -*- coding: utf-8 -*-
"""Construction réelle de ``ExtractAgent`` — kernel requis, ``name``/``description`` inexistants.

Remplace ``test_setup_extract_agent_real.py`` (#2218). Ce fichier portait cinq
tests qui ne mesuraient rien :

- le seul qui touchait ``ExtractAgent`` le construisait sous une forme fantôme
  (``ExtractAgent(name=..., description=...)``) ; le ``TypeError`` tombait dans
  un ``except Exception: return False``, et ``unittest`` ne lit jamais la valeur
  de retour d'une méthode de test — le test ne pouvait donc pas rougir ;
- les quatre autres n'importaient aucun code du projet (``re.findall``, un dict,
  ``open()``, ``str.split``).

Les tests ci-dessous sont des fonctions pytest : une fonction de test ne rend
pas de booléen, donc la forme qui rendait le problème invisible ne peut pas
réapparaître ici. Ils n'invoquent aucun modèle — relever un service sur le
kernel ne contacte personne.
"""

import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent


def _kernel() -> Kernel:
    """Un kernel porteur d'un service LLM — le constructeur l'exige.

    Mesuré : ``ExtractAgent(kernel=Kernel())`` lève
    ``ValueError: Agent 'ExtractAgent': no LLM service 'default' in the kernel,
    which holds [] ...`` (#2627). La clé est
    factice et n'est jamais utilisée : rien dans ce fichier n'appelle le modèle.
    """
    kernel = Kernel()
    kernel.add_service(
        OpenAIChatCompletion(
            service_id="default", ai_model_id="gpt-4", api_key="test-key"
        )
    )
    return kernel


def test_constructs_with_the_real_signature() -> None:
    """Le constructeur réel prend ``kernel`` et rend un agent nommé par défaut."""
    agent = ExtractAgent(kernel=_kernel())
    assert agent.agent_name == "ExtractAgent"


def test_agent_name_is_honoured() -> None:
    agent = ExtractAgent(kernel=_kernel(), agent_name="ProbeAgent")
    assert agent.agent_name == "ProbeAgent"


def test_the_phantom_signature_is_rejected() -> None:
    """Épingle la forme sous laquelle ce dossier est devenu vert sans mesurer.

    L'ancien test appelait ``ExtractAgent(name=..., description=...)``. Cette
    forme doit continuer de lever : si un alias de compatibilité la réintroduit,
    la « surface fantôme » ``setup_extract_agent`` renaît (#2122).
    """
    with pytest.raises(TypeError):
        ExtractAgent(name="x", description="y")  # type: ignore[call-arg]
