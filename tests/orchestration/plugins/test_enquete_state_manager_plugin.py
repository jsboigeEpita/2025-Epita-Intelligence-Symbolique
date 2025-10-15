# tests/orchestration/plugins/test_enquete_state_manager_plugin.py
import pytest
import json
import semantic_kernel as sk
from semantic_kernel.functions import KernelArguments

from argumentation_analysis.core.enquete_states import (
    EnquetePoliciereState,
    EnqueteCluedoState,
)
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import (
    EnqueteStateManagerPlugin,
)


@pytest.fixture
def kernel() -> sk.Kernel:
    return sk.Kernel()


@pytest.fixture
def enquete_policiere_state_fixture() -> EnquetePoliciereState:
    return EnquetePoliciereState(
        description_cas="Affaire du vol de cookies",
        initial_context={"lieu": "Cuisine", "heure": "Minuit"},
    )


@pytest.fixture
def enquete_cluedo_state_fixture() -> EnqueteCluedoState:
    return EnqueteCluedoState(
        nom_enquete_cluedo="Mystère au Manoir Tudor",
        elements_jeu_cluedo={
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Bibliothèque", "Cuisine"],
        },
        description_cas="Un meurtre a été commis au Manoir Tudor.",
        initial_context={"participants": ["Sherlock", "Watson"]},
        solution_secrete_cluedo={
            "suspect": "Colonel Moutarde",
            "arme": "Poignard",
            "lieu": "Salon",
        },
    )


def test_plugin_initialization_with_enquete_policiere_state(
    kernel: sk.Kernel, enquete_policiere_state_fixture: EnquetePoliciereState
):
    plugin = EnqueteStateManagerPlugin(state=enquete_policiere_state_fixture)
    kernel.add_plugin(plugin, "EnqueteState")
    assert "EnqueteState" in kernel.plugins
    assert kernel.plugins["EnqueteState"] is not None
    # Vérifier la présence de quelques fonctions attendues
    assert "get_case_description" in kernel.plugins["EnqueteState"]
    assert "add_task" in kernel.plugins["EnqueteState"]


def test_plugin_initialization_with_enquete_cluedo_state(
    kernel: sk.Kernel, enquete_cluedo_state_fixture: EnqueteCluedoState
):
    plugin = EnqueteStateManagerPlugin(state=enquete_cluedo_state_fixture)
    kernel.add_plugin(plugin, "CluedoState")
    assert "CluedoState" in kernel.plugins
    assert kernel.plugins["CluedoState"] is not None
    assert "get_case_description" in kernel.plugins["CluedoState"]  # Hérité
    assert "get_cluedo_game_elements" in kernel.plugins["CluedoState"]  # Spécifique


async def test_get_case_description_policiere(
    kernel: sk.Kernel, enquete_policiere_state_fixture: EnquetePoliciereState
):
    plugin = EnqueteStateManagerPlugin(state=enquete_policiere_state_fixture)
    kernel.add_plugin(plugin, "EnqueteState")

    result = await kernel.invoke(kernel.plugins["EnqueteState"]["get_case_description"])
    result_dict = json.loads(str(result))

    assert result_dict["case_description"] == "Affaire du vol de cookies"


async def test_add_task_policiere(
    kernel: sk.Kernel, enquete_policiere_state_fixture: EnquetePoliciereState
):
    plugin = EnqueteStateManagerPlugin(state=enquete_policiere_state_fixture)
    kernel.add_plugin(plugin, "EnqueteState")

    args = KernelArguments(
        description="Interroger le témoin principal", assignee="Watson"
    )
    result = await kernel.invoke(kernel.plugins["EnqueteState"]["add_task"], args)
    result_dict = json.loads(str(result))

    assert "task_id" in result_dict
    assert result_dict["description"] == "Interroger le témoin principal"
    assert result_dict["assignee"] == "Watson"
    assert len(enquete_policiere_state_fixture.tasks) == 1
    assert (
        enquete_policiere_state_fixture.tasks[0]["description"]
        == "Interroger le témoin principal"
    )


async def test_get_cluedo_game_elements(
    kernel: sk.Kernel, enquete_cluedo_state_fixture: EnqueteCluedoState
):
    plugin = EnqueteStateManagerPlugin(state=enquete_cluedo_state_fixture)
    kernel.add_plugin(plugin, "CluedoState")

    result = await kernel.invoke(
        kernel.plugins["CluedoState"]["get_cluedo_game_elements"]
    )
    result_dict = json.loads(str(result))

    assert "suspects" in result_dict
    assert "Colonel Moutarde" in result_dict["suspects"]
    assert len(result_dict["suspects"]) == 3


async def test_designate_next_agent(
    kernel: sk.Kernel, enquete_policiere_state_fixture: EnquetePoliciereState
):
    plugin = EnqueteStateManagerPlugin(state=enquete_policiere_state_fixture)
    kernel.add_plugin(plugin, "EnqueteState")

    agent_name_to_designate = "SherlockAgent"
    args = KernelArguments(agent_name=agent_name_to_designate)
    result = await kernel.invoke(
        kernel.plugins["EnqueteState"]["designate_next_agent"], args
    )
    result_dict = json.loads(str(result))

    assert "message" in result_dict
    assert agent_name_to_designate in result_dict["message"]
    assert (
        enquete_policiere_state_fixture.get_designated_next_agent()
        == agent_name_to_designate
    )

    # Test get_designated_next_agent
    result_get = await kernel.invoke(
        kernel.plugins["EnqueteState"]["get_designated_next_agent"]
    )
    result_get_dict = json.loads(str(result_get))
    assert result_get_dict["next_agent"] == agent_name_to_designate


async def test_add_identified_element_policiere(
    kernel: sk.Kernel, enquete_policiere_state_fixture: EnquetePoliciereState
):
    plugin = EnqueteStateManagerPlugin(state=enquete_policiere_state_fixture)
    kernel.add_plugin(plugin, "EnqueteState")

    args = KernelArguments(
        element_type="preuve",
        description="Plume de canari près de la boîte à biscuits",
        source="Observation directe",
    )
    result = await kernel.invoke(
        kernel.plugins["EnqueteState"]["add_identified_element"], args
    )
    result_dict = json.loads(str(result))

    assert "element_id" in result_dict
    assert result_dict["type"] == "preuve"
    assert result_dict["description"] == "Plume de canari près de la boîte à biscuits"
    assert len(enquete_policiere_state_fixture.elements_identifies) == 1
    assert (
        enquete_policiere_state_fixture.elements_identifies[0]["description"]
        == "Plume de canari près de la boîte à biscuits"
    )


async def test_add_hypothesis_policiere(
    kernel: sk.Kernel, enquete_policiere_state_fixture: EnquetePoliciereState
):
    plugin = EnqueteStateManagerPlugin(state=enquete_policiere_state_fixture)
    kernel.add_plugin(plugin, "EnqueteState")

    args = KernelArguments(text="Le canari est le coupable", confidence_score=0.75)
    result = await kernel.invoke(kernel.plugins["EnqueteState"]["add_hypothesis"], args)
    result_dict = json.loads(str(result))

    assert "hypothesis_id" in result_dict
    assert result_dict["text"] == "Le canari est le coupable"
    assert result_dict["confidence_score"] == 0.75
    assert len(enquete_policiere_state_fixture.hypotheses_enquete) == 1
    assert (
        enquete_policiere_state_fixture.hypotheses_enquete[0]["text"]
        == "Le canari est le coupable"
    )
