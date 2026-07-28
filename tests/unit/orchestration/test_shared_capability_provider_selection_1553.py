# -*- coding: utf-8 -*-
"""Tests for #1553 — the shared-capability provider-selection defect.

Two services declared the SAME capability ``hierarchical_fallacy_detection``:
the complete path (``hierarchical_fallacy_detector`` → wide-net + merge) and a
per-argument enrichment SUB-STEP (``hierarchical_fallacy_per_argument``) whose
own contract says it runs AFTER the wide-net descent and that "the wide-net
result is retained by the caller". Invoked as a terminal provider, that
sub-step has no caller to retain anything — it returns ``fallacies: []`` +
``degraded`` (a silent loss, score 0.0).

The mechanism (established firsthand by the coordinator, R724, and re-verified
here): ``_capability_index`` is a ``Dict[str, Set[str]]``
(capability_registry.py:84); ``find_for_capability`` iterates the set as-is
(:295-296); consumers take ``providers[0]`` believing it is "first registered"
(hierarchy_bridge.py:67-73). The iteration order of a ``set`` of strings
depends on ``hash()``, which CPython salts per-process — so the winner between
the two providers was a coin flip at process start. Intermittent BETWEEN runs
(3/5), stable INSIDE one. That is the tell that pointed at the process, not
the business logic.

The fix is SUBTRACTIVE (anti-pendule): the sub-step ceases to declare
``hierarchical_fallacy_detection`` (and ``fallacy_detection``, same structural
defect — it is no kind of terminal detection provider). It keeps its REAL
capability ``per_argument_fallacy_detection``. It is not deleted: the complete
path still calls it directly at invoke_callables.py:4506. Tri the index was
rejected: it would stabilize the winner on an arbitrary (alphabetic) order —
the complete path would win by luck, not by design, and the sub-step would
still shadow other consumers of ``fallacy_detection``.

These tests are sync and LLM-free. They prove the selection is now
deterministic BY CONSTRUCTION (exactly one provider for
``hierarchical_fallacy_detection`` → the ``providers[0]`` coin flip has only
one face). The mutation guards assert what the pre-fix registration shape
would have failed (two providers) and what must survive (the real capability
is preserved).

They live in a dedicated module WITHOUT ``pytestmark = pytest.mark.asyncio``
so the sync functions do not inherit an asyncio mark they cannot satisfy
(lesson R722).
"""

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)
from argumentation_analysis.orchestration.registry_setup import setup_registry

# ── DoD #1 — the mechanism, measured (not hypothesized) ────────────────────


def test_capability_index_is_a_set_so_order_is_not_guaranteed():
    """The defect carrier: ``_capability_index`` stores a ``Set[str]``, whose
    iteration order depends on ``hash()`` (salted per-process). This is the
    structural fact that made ``providers[0]`` a coin flip when two providers
    shared a capability. Establishing it here (measurement, not hypothesis) is
    DoD #1.
    """
    registry = setup_registry(include_optional=True)
    index = registry._capability_index  # noqa: SLF001 — structural assertion
    # The index maps capability -> set of provider names (a Set, not a list).
    assert isinstance(index["hierarchical_fallacy_detection"], set)


def test_per_process_salt_is_the_variable_neutralized():
    """The intermittence was BETWEEN processes (stable inside one). The fix
    removes the second provider, so the set cardinality is 1 and there is no
    coin to flip regardless of ``PYTHONHASHSEED``. Asserting cardinality 1 here
    IS the reproductibility guarantee (DoD #2) — established structurally
    rather than by 5 LLM runs whose variance would be the model, not the
    selection.
    """
    registry = setup_registry(include_optional=True)
    providers = registry._capability_index[  # noqa: SLF001
        "hierarchical_fallacy_detection"
    ]
    assert len(providers) == 1, (
        f"hierarchical_fallacy_detection has {len(providers)} providers "
        f"({sorted(providers)}) — must be exactly 1 to be deterministic; "
        f"the shared-capability defect (#1553) is not closed"
    )


# ── DoD #3 — the sub-step can no longer be a terminal provider ─────────────


def test_only_the_complete_path_provides_hierarchical_fallacy_detection():
    """After the fix, ``find_for_capability('hierarchical_fallacy_detection')``
    returns exactly one provider: ``hierarchical_fallacy_detector`` (the
    complete wide-net + merge path). The per-argument sub-step no longer
    shadows it.
    """
    registry = setup_registry(include_optional=True)
    providers = registry.find_for_capability("hierarchical_fallacy_detection")
    names = [p.name for p in providers]
    assert names == ["hierarchical_fallacy_detector"], names


def test_sub_step_no_longer_declares_terminal_detection_capabilities():
    """Mutation guard: the per-argument sub-step must NOT declare
    ``hierarchical_fallacy_detection`` nor ``fallacy_detection`` — those are
    terminal-detection capabilities, and it is an enrichment sub-step. The
    pre-fix registration declared both; this assertion would have failed then.
    """
    registry = setup_registry(include_optional=True)
    for terminal_cap in (
        "hierarchical_fallacy_detection",
        "fallacy_detection",
    ):
        providers = registry.find_for_capability(terminal_cap)
        names = [p.name for p in providers]
        assert "hierarchical_fallacy_per_argument" not in names, (
            f"sub-step still declares terminal capability {terminal_cap!r} — "
            f"#1553 regression (it would shadow the complete path again)"
        )


def test_sub_step_keeps_its_real_capability():
    """Anti-pendule guard: the sub-step is NOT deleted — it keeps its REAL
    capability ``per_argument_fallacy_detection``. The complete path still
    invokes it directly (invoke_callables.py:4506) for the recall lift. The
    defect was the SHARING of the terminal capability, not the sub-step's
    existence.
    """
    registry = setup_registry(include_optional=True)
    providers = registry.find_for_capability("per_argument_fallacy_detection")
    names = [p.name for p in providers]
    assert "hierarchical_fallacy_per_argument" in names, (
        "sub-step lost per_argument_fallacy_detection — the fix deleted the "
        "sub-step instead of subtracting the shared capability (anti-pendule)"
    )


def test_resolution_is_invariant_under_hash_seed_by_construction():
    """DoD #2 (reproductibility) read as a structural property: with exactly
    one provider, resolving N times in the same process trivially yields the
    same provider every time — but the point is to assert the absence of the
    second face of the coin, not to re-run an LLM 5 times. Simulating the
    pre-fix shape (two providers) shows the non-determinism the fix removes.
    """
    # Post-fix real registry: one provider, deterministic by construction.
    registry = setup_registry(include_optional=True)
    resolved = [
        registry.find_for_capability("hierarchical_fallacy_detection")[0].name
        for _ in range(8)
    ]
    assert all(name == "hierarchical_fallacy_detector" for name in resolved)

    # The pre-fix shape, reproduced on a throwaway registry: two providers
    # under the same capability. find_for_capability returns BOTH (order not
    # guaranteed); consumers taking [0] would see either. This is the
    # variable the subtractive fix removes — documented, not re-introduced.
    twin = CapabilityRegistry()
    twin.register(
        name="complete_path",
        component_type=ComponentType.SERVICE,
        capabilities=["hierarchical_fallacy_detection"],
    )
    twin.register(
        name="enrichment_sub_step",
        component_type=ComponentType.SERVICE,
        capabilities=["hierarchical_fallacy_detection"],
    )
    twin_providers = twin.find_for_capability("hierarchical_fallacy_detection")
    assert len(twin_providers) == 2, (
        "expected the pre-fix shape (2 providers sharing the capability) to "
        "reproduce the non-determinism carrier — if this fails, the registry "
        "changed and the test's premise needs revisiting"
    )
