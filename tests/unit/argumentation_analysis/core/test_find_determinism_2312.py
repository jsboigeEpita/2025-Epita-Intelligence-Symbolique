# -*- coding: utf-8 -*-
"""#2312 — find_for_capability returns a deterministic, DECLARED order.

The capability index is a ``Dict[str, Set[str]]``; iterating a set of
``str`` follows hash order, salted per-process — the same code and state
could draw different providers (measured 1-in-4 on #2296: a no-invoke SK
plugin drawn before the invocable pipeline service, the phase completing
with output None). #1553 already warned about it in the hierarchy bridge
docstring; this guard pins the contract at the source.

The declared order (API, #2312): providers carrying an ``invoke`` come
first (a capability is exercised at runtime through ``invoke`` — a
provider without one cannot serve a call), then alphabetical by name
among equals. The alphabetical tiebreak is part of the contract: names
are registry keys, the sort makes them an API.

The instrument: a set subclass iterating in REVERSE sorted order,
injected into the index — two opposite iteration orders over the same
capability MUST yield the same result list.
"""

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)


class _ReverseIterSet(set):
    """Test instrument (#2312): iterates in reverse sorted order."""

    def __iter__(self):
        return iter(reversed(sorted(set.__iter__(self))))


async def _noop_invoke(text: str, context: dict) -> None:  # pragma: no cover
    return None


def _registry() -> CapabilityRegistry:
    r = CapabilityRegistry()
    r.register(
        "plug_dead",
        ComponentType.PLUGIN,
        capabilities=["kb_to_tweety"],
    )
    r.register(
        "svc_zeta",
        ComponentType.SERVICE,
        capabilities=["kb_to_tweety"],
        invoke=_noop_invoke,
    )
    r.register(
        "svc_alpha",
        ComponentType.SERVICE,
        capabilities=["kb_to_tweety"],
        invoke=_noop_invoke,
    )
    return r


DECLARED = ["svc_alpha", "svc_zeta", "plug_dead"]


class TestDeclaredOrder:
    def test_invoke_first_then_name(self):
        names = [r.name for r in _registry().find_for_capability("kb_to_tweety")]
        assert names == DECLARED

    def test_typed_variant_follows_the_same_order(self):
        names = [
            r.name for r in _registry().find_services_for_capability("kb_to_tweety")
        ]
        assert names == ["svc_alpha", "svc_zeta"]


class TestOppositeIterationOrdersSameResult:
    """Two opposite iteration orders over the index ⇒ same result.

    The #2312 DoD guard: inject a reverse-iterating set into the
    capability index — before the fix, the result follows the (reversed)
    set order and this reddens deterministically; after, sorting at the
    resolver absorbs any iteration order.
    """

    def test_reversed_index_yields_the_declared_order(self):
        reg = _registry()
        reg._capability_index["kb_to_tweety"] = _ReverseIterSet(
            reg._capability_index["kb_to_tweety"]
        )
        names = [r.name for r in reg.find_for_capability("kb_to_tweety")]
        assert names == DECLARED

    def test_reversed_index_first_provider_is_invocable(self):
        # The measured #2296 shape: [0] must never be the dead plugin,
        # whatever the set iteration draws.
        reg = _registry()
        reg._capability_index["kb_to_tweety"] = _ReverseIterSet(
            reg._capability_index["kb_to_tweety"]
        )
        provider = reg.find_for_capability("kb_to_tweety")[0]
        assert provider.invoke is not None

    def test_typed_variant_absorbs_reversed_index(self):
        reg = _registry()
        reg._capability_index["kb_to_tweety"] = _ReverseIterSet(
            reg._capability_index["kb_to_tweety"]
        )
        names = [r.name for r in reg.find_services_for_capability("kb_to_tweety")]
        assert names == ["svc_alpha", "svc_zeta"]


class TestSingleProvider:
    def test_single_provider_capability_is_stable(self):
        reg = CapabilityRegistry()
        reg.register("solo", ComponentType.SERVICE, capabilities=["solo_cap"])
        names = [r.name for r in reg.find_for_capability("solo_cap")]
        assert names == ["solo"]
