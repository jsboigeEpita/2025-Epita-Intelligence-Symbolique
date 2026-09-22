"""#2324 — la marche de la descente devient une fonction pure des réponses.

Mesuré sur le job d'enregistrement 35474667181 (#2323) : la forme de la
marche de la descente guidée était choisie par le LLM **et par le scheduler**
à chaque session — l'entrelacement des branches parallèles du Phase 2 décide
de la supersession croisée et de l'ordre de consommation du budget, donc de
la suite de prompts émise. Une seule session d'enregistrement ne peut pas
produire des cassettes couvrant chaque marche possible : le rejeu en générait
d'autres (8 ``miss_replay``, dont la cascade de fallbacks).

Le pin : ``FALLACY_DESCENT_SEQUENTIAL=1`` séquentialise la marche — candidats
dans l'ordre du wide-net, une branche après l'autre, fan-out compris. La
descent garde LIEU (nœuds visités, LLM consulté à chaque pas) ; seul
l'entrelacement est épinglé. La production reste parallèle par défaut
(contrôle d'accord ci-dessous).

Le né-rouge est **en valeurs d'événements** : sur ``main`` d'avant
réparation, le siège ``FALLACY_DESCENT_SEQUENTIAL=1`` ne change rien — les
trois branches démarrent avant que la première ne finisse (``gather``), et
l'assertion d'ordre échoue en nommant l'entrelacement mesuré.
"""

import asyncio
from typing import List, Tuple

import pytest

from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
    IdentifiedFallacy,
)

# (type, pk) — la trace d'exécution que les doublures remplissent.
_EVENTS: List[Tuple[str, str]] = []

_CANDIDATES = ["pk_1", "pk_2", "pk_3"]


def _plugin() -> FallacyWorkflowPlugin:
    return FallacyWorkflowPlugin(master_kernel=None, llm_service=object())


async def _wide_net(self, argument_text: str) -> List[str]:
    _EVENTS.append(("widenet", ""))
    return list(_CANDIDATES)


async def _branch(self, argument_text, start_pk, slave_kernel, slave_settings, **kw):
    """Une branche qui se met en évidence : démarre, CÈDE LA MAIN, finit.

    Le point de suspension est ce qui rend l'entrelacement observable — sans
    lui, un ``gather`` de coroutines instantanées s'exécute dans l'ordre de
    soumission et le test ne mesurerait rien.
    """
    _EVENTS.append(("start", start_pk))
    await asyncio.sleep(0.02)
    _EVENTS.append(("end", start_pk))
    if start_pk == _CANDIDATES[0]:
        return IdentifiedFallacy(
            fallacy_type="fallacie_de_mesure",
            taxonomy_pk=start_pk,
            taxonomy_path="racine/branche",
            explanation="une identification, pour que la phase 3 ait du grain",
            confidence=0.9,
            navigation_trace=[start_pk],
            family="F",
            depth=2,
        )
    return None


def _slave_kernel(self):
    return None, None


def _arm(monkeypatch) -> None:
    _EVENTS.clear()
    monkeypatch.setattr(FallacyWorkflowPlugin, "_wide_net_candidates", _wide_net)
    monkeypatch.setattr(FallacyWorkflowPlugin, "_explore_single_branch", _branch)
    monkeypatch.setattr(FallacyWorkflowPlugin, "_create_slave_kernel", _slave_kernel)


def _branch_events() -> List[Tuple[str, str]]:
    return [e for e in _EVENTS if e[0] in ("start", "end")]


# ===========================================================================
# 1. La divergence — le siège séquentiel épinglera la marche
# ===========================================================================


async def test_sequential_seat_walks_one_branch_at_a_time(monkeypatch):
    """Le né-rouge de #2324 : ``FALLACY_DESCENT_SEQUENTIAL=1`` ⇒ ordre strict.

    Avant réparation, le siège ne change rien : les trois ``start`` précèdent
    le premier ``end`` (entrelacement du ``gather``). L'échec nomme cet
    entrelacement — échec en valeurs, jamais en import.
    """
    _arm(monkeypatch)
    monkeypatch.setenv("FALLACY_DESCENT_SEQUENTIAL", "1")
    plugin = _plugin()  # construit APRÈS le siège : le plugin lit l'env à l'init

    await plugin.run_guided_analysis("Un texte avec un argument quelconque.")

    # L'ordre strict attendu : widenet, puis (start, end) par candidat.
    strict = [e for pk in _CANDIDATES for e in (("start", pk), ("end", pk))]
    assert (
        _branch_events() == strict
    ), f"la marche n'est pas séquentielle — événements: {_branch_events()}"
    # Non-vacuité : la wide-net a tourné (le Phase 2 a bien été atteint).
    assert ("widenet", "") in _EVENTS


# ===========================================================================
# 2. L'accord — la production reste parallèle sans le siège
# ===========================================================================


async def test_default_seat_still_interleaves(monkeypatch):
    """Sans le siège, le ``gather`` d'origine tient : les trois starts d'abord.

    Contrôle d'accord : la réparation ne déplace PAS la frontière de la
    production — le parallélisme du Phase 2 (bench PR #1067 : ≥2x) reste le
    défaut. Vert avant ET après réparation.
    """
    _arm(monkeypatch)
    monkeypatch.delenv("FALLACY_DESCENT_SEQUENTIAL", raising=False)
    plugin = _plugin()

    await plugin.run_guided_analysis("Un texte avec un argument quelconque.")

    events = _branch_events()
    first_three = [e for e in events[:3]]
    assert all(
        e[0] == "start" for e in first_three
    ), f"le défaut n'entrelace plus — la production a changé de forme: {events}"


# ===========================================================================
# 3. Le fan-out suit la même discipline
# ===========================================================================


async def test_fanout_is_sequential_under_the_seat(monkeypatch):
    """Le fan-out de sous-branches (RA-3 #1048 item 2) est séquentiel aussi.

    Avant réparation : ``asyncio.gather`` sur les sous-branches — mêmes
    départs entrelacés, même miss de couverture.
    """
    _arm(monkeypatch)
    monkeypatch.setenv("FALLACY_DESCENT_SEQUENTIAL", "1")
    plugin = _plugin()

    tracker = FallacyWorkflowPlugin._BranchSupersessionTracker(
        plugin.taxonomy_navigator,
        fanout_budget=plugin.SUBBRANCH_FANOUT_BUDGET,
        descent_call_budget=240,
    )
    sink: List[IdentifiedFallacy] = []
    extras = [("sub_a", {"name": "A"}), ("sub_b", {"name": "B"})]

    await plugin._fanout_subbranches(extras, "texte", None, None, [], tracker, sink)

    strict = [
        ("start", "sub_a"),
        ("end", "sub_a"),
        ("start", "sub_b"),
        ("end", "sub_b"),
    ]
    assert (
        _branch_events() == strict
    ), f"le fan-out n'est pas séquentiel — événements: {_branch_events()}"
    # Le siège a bien pris (l'assertion d'événements couvre déjà le comportement ;
    # celle-ci nomme la cause si un futur montage la perd).
    assert (
        plugin.descent_sequential
    ), "le siège n'a pas pris — construction avant setenv ?"
