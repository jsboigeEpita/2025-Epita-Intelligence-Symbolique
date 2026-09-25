# -*- coding: utf-8 -*-
"""#2415 — le chemin middleware de la tâche opérationnelle est un circuit mort : retiré, pas réparé.

Preuve de non-utilité (mesurée sur `main`, issue #2415) :

- l'émetteur réel (`TaskCoordinator.assign_task_to_operational`) adresse
  ``informal_analyzer`` & co sur SON middleware ; le registre construit chaque
  agent sur SON PROPRE middleware sous un nom ``{type}Agent`` — la commande
  n'atteint jamais un agent ;
- même livré, ``_process_task_async`` appelle des méthodes **fantômes** de
  ``OperationalAdapter`` (``send_status_update``, ``send_task_result`` ×2,
  ``request_tactical_guidance``, ``share_operational_data``) — et son chemin
  d'échec lève aussi, l'exception s'échappant en tâche non récupérée ;
- le consommateur du résultat **n'existe pas** : ``handle_task_result`` n'a
  aucun appelant, ``TacticalAdapter.receive_task_result`` /
  ``subscribe_to_operational_updates`` n'ont aucun appelant de production ;
- les deux chemins d'exécution réels contournent l'abonnement : M3
  (``DelegationOrchestrator``) exécute par le seam ``operational_executor`` ;
  le ServiceManager legacy par la file + ``Future`` de
  ``OperationalManager._worker``.

Réparer les trois couches laisserait le circuit ouvert au bout (résultats
sans lecteur) ; une réparation complète construirait un 4ᵉ segment en doublon
deux chemins vivants. DoD exécutée ici (branche retrait) :

1. garde AST : chaque ``self.adapter.<m>(`` de ``agent_interface.py`` existe
   sur ``OperationalAdapter`` (contrôle positif du marcheur inclus) ;
2. le circuit mort n'est plus dans l'arbre ;
3. ce qui restait porteur dans ``assign_task_to_operational`` — l'écriture
   d'état #1735 T3 (qui + pourquoi) — survit, et la directive middleware
   morte n'est plus émise ;
4. témoins : la traduction T→O construit toujours la commande (sans
   l'émettre), et le rapport de complétion du chemin live part toujours
   (méthode réelle ``send_result``).
"""

import ast
from pathlib import Path

import pytest

from argumentation_analysis.core.communication import MessageType
from argumentation_analysis.core.communication.operational_adapter import (
    OperationalAdapter,
)
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import (
    TacticalOperationalInterface,
)
from argumentation_analysis.orchestration.hierarchical.operational import (
    agent_interface,
)
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import (
    TaskCoordinator,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)

AGENT_INTERFACE = Path(agent_interface.__file__).read_text(encoding="utf-8-sig")


def _adapter_calls(source: str, attr: str = "adapter") -> list:
    """Marcheur AST : chaque ``self.<attr>.<meth>(`` du source."""
    calls = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            func = node.func
            if (
                isinstance(func.value, ast.Attribute)
                and func.value.attr == attr
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "self"
            ):
                calls.append(func.attr)
    return calls


def test_adapter_call_walker_finds_known_calls():
    """Contrôle positif du marcheur : sur un littéral qui appelle une méthode
    réelle, il la trouve — sans lui, la garde vide serait invacuite."""
    source = "class X:\n    def f(self):\n        self.adapter.send_result(1)\n"
    assert _adapter_calls(source) == ["send_result"]
    assert hasattr(OperationalAdapter, "send_result")


def test_every_adapter_call_in_agent_interface_exists():
    """NÉ-ROUGE : sur main, agent_interface.py appelle 4 méthodes fantômes
    (send_status_update, send_task_result, request_tactical_guidance,
    share_operational_data) qu'OperationalAdapter ne porte pas."""
    calls = _adapter_calls(AGENT_INTERFACE)
    missing = [m for m in calls if not hasattr(OperationalAdapter, m)]
    assert not missing, (
        f"agent_interface.py appelle des méthodes absentes d'OperationalAdapter : "
        f"{missing} (appelées : {calls})"
    )


def test_dead_task_circuit_is_gone():
    """NÉ-ROUGE : le circuit mort (abonnement, traitement, méthodes
    orphelines) doit sortir de l'arbre avec la directive qui l'alimentait.
    La garde est AST (noms de fonctions définies) : un commentaire qui
    documente le retrait ne doit pas la faire rougir."""
    from argumentation_analysis.orchestration.hierarchical.tactical import (
        coordinator as tactical_coordinator_module,
    )

    defined = {
        node.name
        for node in ast.walk(ast.parse(AGENT_INTERFACE))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for dead_symbol in (
        "_subscribe_to_tasks",
        "_process_task_async",
        "execute_technique",
        "request_resource",
        "share_intermediate_result",
        "subscribe_to_results",
    ):
        assert dead_symbol not in defined, (
            f"{dead_symbol} vit encore comme fonction de agent_interface.py : "
            f"plus aucun appelant dans l'arbre (#2415)"
        )
    coordinator_source = Path(tactical_coordinator_module.__file__).read_text(
        encoding="utf-8-sig"
    )
    assert "self.adapter.assign_task(" not in coordinator_source, (
        "assign_task_to_operational émet encore la directive middleware morte : "
        "son seul récepteur possible (l'abonnement des agents) est retiré"
    )


def _capturing_command_recorder(interface):
    """Abonne un enregistreur aux COMMAND hiérarchiques du middleware."""
    from argumentation_analysis.core.communication import ChannelType

    captured = []
    channel = interface.middleware.get_channel(ChannelType.HIERARCHICAL)
    assert (
        channel is not None
    ), "le middleware de test doit porter le canal hiérarchique"
    channel.subscribe(
        subscriber_id="recorder_2415",
        callback=captured.append,
        filter_criteria={"message_type": MessageType.COMMAND.value},
    )
    return captured


def test_allocation_is_recorded_without_dead_directive():
    """NÉ-ROUGE (2 mesures) : sur main, assign_task_to_operational émet une
    COMMAND que aucun agent ne peut recevoir ; l'écriture d'état #1735 T3
    (qui + pourquoi) doit survivre au retrait de la directive."""
    coordinator = TaskCoordinator(tactical_state=TacticalState())
    captured = _capturing_command_recorder(coordinator)

    task = {
        "id": "task-2415",
        "description": "analyser la structure",
        "required_capabilities": ["informal_analysis"],
        "priority": "high",
    }
    # ``state.assign_task`` réanime une tâche existante (#1735) : l'amorcer
    # d'abord, comme le fait ``process_strategic_objectives``.
    coordinator.state.add_task(task)
    coordinator.assign_task_to_operational(task)

    assert coordinator.state.task_assignments.get(
        "task-2415"
    ), "l'allocation doit rester écrite dans l'état tactique (#1735 T3)"
    motivation = coordinator.state.task_assignments_motivation.get("task-2415", "")
    assert motivation.strip(), "l'allocation doit garder sa motivation (#1735 T3)"
    assert captured == [], (
        f"la directive middleware morte est encore émise : "
        f"{[(m.recipient, m.content.get('command_type')) for m in captured]}"
    )


def test_translate_task_to_command_builds_without_emitting():
    """NÉ-ROUGE : la traduction T→O (chemin live : manager + M3) construit la
    commande ; son émission middleware morte doit partir avec le circuit."""
    interface = TacticalOperationalInterface(tactical_state=TacticalState())
    captured = _capturing_command_recorder(interface)

    task = {
        "id": "tt-2415",
        "objective_id": "obj-1",
        "description": "extraire",
        "required_capabilities": ["text_extraction"],
        "priority": "medium",
    }
    command = interface.translate_task_to_command(task)

    assert command["tactical_task_id"] == "tt-2415"
    assert command["id"].startswith("op-tt-2415")
    assert captured == [], (
        f"translate_task_to_command émet encore une directive morte : "
        f"{[m.recipient for m in captured]}"
    )


def test_completion_report_still_flows_live_path(monkeypatch):
    """Témoin (vert avant et après) : le rapport de complétion du chemin live
    part toujours par la méthode réelle ``send_result`` — le retrait du
    circuit mort ne touche pas le chemin qui vit."""
    interface = TacticalOperationalInterface(tactical_state=TacticalState())
    monkeypatch.setattr(interface, "_save_result_to_file", lambda report: None)

    from argumentation_analysis.core.communication import ChannelType

    captured = []
    channel = interface.middleware.get_channel(ChannelType.HIERARCHICAL)
    channel.subscribe(
        subscriber_id="recorder_2415_report",
        callback=captured.append,
        filter_criteria={"message_type": MessageType.INFORMATION.value},
    )

    report = interface.process_operational_result(
        {"id": "ot-1", "tactical_task_id": "tt-1"},
        {"status": "completed", "outputs": {"extracts": [{"v": 1}]}},
    )

    assert report["completion_status"] == "completed"
    assert captured, (
        "le rapport de complétion (chemin live, consommé côté tactique par "
        "TacticalAdapter.get_pending_task_results) ne part plus"
    )
    # Contrat du writer réel (OperationalAdapter.send_result) : le marqueur
    # de rapport vit sous ``result_type``, ``info_type`` porte ``task_result``.
    # #2520 : le lecteur opérationnel qui épinglait ``info_type == "
    # task_completion_report"`` est retiré — sa clé ne matchait jamais ce
    # writer et sa Future était résolue avant publication (voir l'issue).
    assert captured[0].content["info_type"] == "task_result"
    assert captured[0].content["result_type"] == "task_completion_report"
