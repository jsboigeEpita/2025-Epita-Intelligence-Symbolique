"""#1748 — le bilan de setup_registry doit être honnête et sensible au monde.

Trois propriétés, chacune par substitution dégénérée (on force le mécanisme,
pas l'environnement) :

1. **égalité annoncé == réel** : le compte journalisé doit égaler les
   inscriptions effectivement passées au registre — la propriété est
   l'égalité, jamais la constante (57 bougera au prochain composant).
2. **le bilan sépare les mondes** : quand l'inscription des handlers Tweety
   échoue, ils doivent apparaître en *declared-absent slots*, et la ligne de
   bilan doit **changer**. L'ancien format (`37 registered, 0 skipped`) était
   invariant à travers ces deux états opposés du système (#1019).
3. **l'échec total est visible** : un handler dont même la déclaration de
   slot échoue doit atterrir dans `skipped`, au complet.
"""

import logging
import re
from unittest import mock

from argumentation_analysis.core.capability_registry import CapabilityRegistry
from argumentation_analysis.orchestration import registry_setup

SUMMARY_RE = re.compile(
    r"Registry setup complete: (\d+) registered, "
    r"(\d+) declared-absent slots, "
    r"(\d+) skipped"
)


class _CountingRegistry(CapabilityRegistry):
    """Compte chaque inscription réussie au point de passage unique."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.made = []

    def register(self, *args, **kwargs):
        registration = super().register(*args, **kwargs)
        self.made.append(registration.name)
        return registration


def _tweety_handler_names():
    """Noms des handlers lus sur le producteur — suit les ajouts futurs."""
    recorder = _CountingRegistry()
    registry_setup._declare_tweety_slots(recorder)
    return set(recorder.made)


def _last_summary(caplog):
    line = None
    for record in caplog.records:
        if record.getMessage().startswith("Registry setup complete"):
            line = record.getMessage()
    assert line is not None, "setup_registry n'a pas émis sa ligne de bilan"
    match = SUMMARY_RE.fullmatch(line)
    assert match is not None, f"bilan pas au format 3 populations : {line!r}"
    return tuple(int(group) for group in match.groups())


def _run_setup(caplog):
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="UnifiedPipeline"):
        registry = registry_setup.setup_registry()
    return registry, _last_summary(caplog)


def test_announced_registered_equals_actual_registrations(caplog):
    with mock.patch.object(registry_setup, "CapabilityRegistry", _CountingRegistry):
        registry, summary = _run_setup(caplog)

    announced_registered, announced_slots, _ = summary
    assert announced_registered == len(registry.made)
    assert announced_registered == len(registry._registrations)
    assert announced_slots == len(registry._slots)
    # La garde du ticket : les handlers Tweety comptent dans le bilan annoncé.
    tweety_names = _tweety_handler_names()
    assert tweety_names
    assert tweety_names <= set(registry.made)


def test_summary_separates_tweety_registered_from_declared_absent(caplog):
    tweety_names = _tweety_handler_names()

    class SlotWorldRegistry(_CountingRegistry):
        def register(self, *args, **kwargs):
            name = kwargs.get("name", args[0] if args else None)
            if name in tweety_names:
                raise RuntimeError(f"forced register failure for {name} (#1748)")
            return super().register(*args, **kwargs)

    _, world_registered = _run_setup(caplog)
    with mock.patch.object(registry_setup, "CapabilityRegistry", SlotWorldRegistry):
        registry_slots, world_absent = _run_setup(caplog)

    reg_a, slots_a, _ = world_registered
    reg_b, slots_b, _ = world_absent
    assert reg_b < reg_a, (
        f"le bilan n'a pas bougé quand les handlers formels sont absents : "
        f"{reg_b} registered dans les deux mondes (#1019)"
    )
    assert slots_b > slots_a
    # Le compte annoncé de slots est celui réellement stocké.
    assert slots_b == len(registry_slots._slots)
    assert tweety_names.isdisjoint(registry_slots.made)


def test_handler_where_slot_declaration_also_fails_lands_in_skipped(caplog):
    tweety_names = _tweety_handler_names()
    normal_registry, _ = _run_setup(caplog)
    tweety_capabilities = set()
    for name in tweety_names:
        registration = normal_registry._registrations.get(name)
        assert registration is not None, f"handler {name} absent du monde normal"
        tweety_capabilities.update(registration.capabilities)

    class DoomWorldRegistry(_CountingRegistry):
        def register(self, *args, **kwargs):
            name = kwargs.get("name", args[0] if args else None)
            if name in tweety_names:
                raise RuntimeError(f"forced register failure for {name} (#1748)")
            return super().register(*args, **kwargs)

        def declare_slot(self, *args, **kwargs):
            name = kwargs.get("name", args[0] if args else None)
            if name in tweety_capabilities:
                raise RuntimeError(f"forced slot failure for {name} (#1748)")
            return super().declare_slot(*args, **kwargs)

    with mock.patch.object(registry_setup, "CapabilityRegistry", DoomWorldRegistry):
        registry_doom, world_doom = _run_setup(caplog)

    reg_doom, slots_doom, skipped_doom = world_doom
    assert skipped_doom == len(tweety_names)
    assert slots_doom == 0
    assert reg_doom == len(registry_doom.made)
