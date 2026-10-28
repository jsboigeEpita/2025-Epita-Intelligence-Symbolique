# -*- coding: utf-8 -*-
"""#3280(b) — la famille d'agents de l'usine n'a PAS un contrat unique.

Chaque agent documente sa forme de retour dans sa propre docstring
``analyze_text`` ; ce témoin la pince en couloir gratuit, parce que le test
famille (``tests/integration/triage/test_agent_family.py``) vit derrière
``requires_api`` et ne tourne que dans la bande :

1. **InformalFallacyAgent rend la completion brute** — le ``FunctionResult``
   de ``kernel.invoke_prompt``, non déroulé. Mesuré : zéro consommateur
   production n'indexe un mapping sur cet agent (l'adaptateur hiérarchique
   déroule lui-même, ``informal_agent_adapter.py:202-217``, étiquette
   ``agent_raw_output`` ; la web API passe par ``invoke`` ; la démo affiche).
2. **SherlockJTMSAgent rend le mapping** ``{"summary", "details",
   "findings"}`` où ``findings`` sont des hypothèses JTMS — une forme
   rétrofiée pour le test famille (ses commentaires l.611-617 l'avouent),
   tenue depuis et documentée pour ce qu'elle est.

Le refus de l'option (a) — fabriquer ``findings[fallacy_name]`` en parsant
la prose — repose sur un fait structurel pincé ici aussi : le plugin
d'identification monté par l'agent INFORMAL n'expose **aucune**
``@kernel_function``. Si quelqu'un lui en ajoute une, ce témoin rougit :
le sol du choix (b) a bougé, #3280 se réévalue.
"""

import ast
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import semantic_kernel as sk
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)
from semantic_kernel.functions.function_result import FunctionResult
from semantic_kernel.functions.kernel_function_metadata import (
    KernelFunctionMetadata,
)

from argumentation_analysis.agents.concrete_agents.informal_fallacy_agent import (
    InformalFallacyAgent,
)
from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import (
    ComplexFallacyAnalyzer,
)


def _informal_agent() -> InformalFallacyAgent:
    """Agent réel sur un kernel vivant au service chat moqué (pattern #2132)."""
    kernel = sk.Kernel()
    mock_service = MagicMock(spec=ChatCompletionClientBase)
    mock_service.get_prompt_execution_settings_class.return_value = (
        PromptExecutionSettings
    )
    mock_service.service_id = "test_service"
    kernel.add_service(mock_service)
    return InformalFallacyAgent(
        kernel=kernel, config_name="simple", llm_service_id="test_service"
    )


def _kernel_function_decorators(source: str) -> list:
    """Les décorateurs ``@kernel_function`` (nus ou qualifiés) du source."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Name)
                    and decorator.id == "kernel_function"
                ) or (
                    isinstance(decorator, ast.Attribute)
                    and decorator.attr == "kernel_function"
                ):
                    found.append(decorator)
    return found


class TestInformalContract:
    """Le contrat d'INFORMAL : la completion du kernel, non déroulée."""

    async def test_analyze_text_returns_the_kernels_result_unmodified(
        self, monkeypatch
    ):
        sentinel = FunctionResult(
            function=KernelFunctionMetadata(name="witness", is_prompt=False),
            value="prose d'analyse",
        )
        agent = _informal_agent()
        # Patch au niveau classe (#1817) : ``Kernel`` est un modèle Pydantic
        # qui refuse l'assignation d'attributs inconnus au niveau instance.
        monkeypatch.setattr(
            sk.Kernel, "invoke_prompt", AsyncMock(return_value=sentinel)
        )

        result = await agent.analyze_text("Un texte à analyser.")

        assert result is sentinel, (
            "Le contrat documenté (#3280(b)) : analyze_text rend le "
            "FunctionResult de invoke_prompt tel quel — le dérouler ici "
            "casserait les consommateurs qui le déroulent eux-mêmes."
        )

    def test_the_mounted_identification_plugin_authors_no_kernel_function(self):
        """Le sol structurel du choix (b) : aucune ``@kernel_function``.

        C'est parce que rien n'auteure de findings structurés que le mapping
        du test famille aurait été de la prose parsée, pas de la structure
        auteureée. Un décorateur ajouté ici change ce sol : #3280 se
        réévalue (l'option (a) redevient réparable sans fabrication).
        """
        source = Path(inspect.getsourcefile(ComplexFallacyAnalyzer)).read_text(
            encoding="utf-8-sig"
        )
        assert _kernel_function_decorators(source) == [], (
            "ComplexFallacyAnalyzer expose désormais des @kernel_function — "
            "le sol du choix #3280(b) a bougé : une couche auteure de la "
            "structure, l'option (a) redevient mesurable."
        )


class TestSherlockContract:
    """Le contrat de SHERLOCK : le mapping documenté, findings = hypothèses."""

    @pytest.fixture
    def agent(self, monkeypatch):
        monkeypatch.setattr(
            sk.Kernel,
            "invoke_prompt",
            AsyncMock(return_value="hypothèse stub"),
        )
        return SherlockJTMSAgent(sk.Kernel(), agent_name="contract_witness")

    async def test_analyze_text_returns_the_documented_mapping(
        self, agent, monkeypatch
    ):
        details = {
            "processed_clues": [{"clue_id": "clue_1"}],
            "generated_hypotheses": [{"hypothesis_id": "hypothesis_1"}],
        }
        monkeypatch.setattr(agent, "analyze_clues", AsyncMock(return_value=details))

        result = await agent.analyze_text("Un texte d'indices.")

        assert set(result) >= {"summary", "details", "findings"}, (
            "Le contrat documenté (#3280(b)) : Sherlock rend le mapping "
            "{'summary', 'details', 'findings'} — c'est la forme que le test "
            "famille asserte sur cette famille."
        )
        assert result["findings"] == details["generated_hypotheses"], (
            "Les findings de Sherlock sont ses hypothèses JTMS — pas des "
            "fallacy_name : aucune famille n'auteure ce champ ici."
        )

    async def test_hypothesis_findings_carry_no_fallacy_name(self, agent):
        """Le test famille n'exige ``fallacy_name`` d'aucune famille — c'est ancré.

        Le jour où un findings de Sherlock porte un ``fallacy_name``, c'est
        qu'une couche l'auteure : le commentaire du test famille et cette
        garde rougissent ensemble.
        """
        hypothesis = await agent.formulate_hypothesis("Un contexte quelconque.")
        assert "fallacy_name" not in hypothesis, (
            "formulate_hypothesis produit une hypothèse JTMS ; un "
            "fallacy_name y serait une fabrication."
        )
