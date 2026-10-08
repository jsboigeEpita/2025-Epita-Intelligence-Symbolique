# -*- coding: utf-8 -*-
"""#2969 — Guard: every spectacular phase-output READ is a declared dependency.

The executor runs phases level by level and publishes ``phase_<P>_output``
only after the whole level ends, so a consumer whose invoker reads a key
whose producer is not a (transitive) ``depends_on`` dependency reads an empty
dict — silently. That class produced the three measured defects of #2969
(quality aggregated hierarchical_fallacy — 0/8 units penalized on doc_A;
governance voted without its counter/debate/jtms axes; debate could not fill
its RETRACTED BELIEFS block), plus two reads satisfied only by the accident
of levels (jtms→fol/pl, dialogue_reasoning→counter), now declared.

The census is strict, and its known false alerts are CLASSIFIED, never
silenced:

* **docstrings** — excluded by construction (the first-statement string
  literal is skipped); the mechanism is witnessed below by a synthetic
  docstring mention that does not count.
* **variant keys** — the democratech spellings passed to
  ``_resolve_phase_output`` after the canonical key count as reads of the
  canonical phase, which must still be transitively declared
  (``VARIANT_ALIASES``). Checked, not waived: a variant whose canonical
  producer is not declared still reddens.
* **the label-fallback helper** — ``_extract_arguments_from_context`` reads
  ``extract`` first; the quality keys after it are fallback SOURCES of
  argument labels (degrading to sentence-splitting when absent), not quality
  axes being aggregated. The guard re-checks the anchor-first property
  itself, so a chain reorder reddens instead of inheriting the pass. The
  waiver covers the helper's two fallback keys only — an invoker's own
  direct quality read is always fully checked.

Born red on main: quality→hierarchical_fallacy, governance→{counter, debate,
jtms, hierarchical_fallacy}, debate→jtms, dialogue→counter and jtms→{fol, pl}
all violate there (the DAG witnesses at the bottom of this file assert the
edges directly and fail on main).
"""

import ast
import inspect
import re
import textwrap
from typing import Any, Callable, Dict, List, Set, Tuple

from argumentation_analysis.orchestration import invoke_callables
from argumentation_analysis.orchestration.registry_setup import setup_registry
from argumentation_analysis.orchestration.workflows import build_spectacular_workflow

KEY_RE = re.compile(r"^phase_(\w+)_output$")

# Variant spellings resolved by _resolve_phase_output (invoke_callables,
# _invoke_governance's upstream resolution): each variant follows its
# canonical key in the same call, so reading the variant IS reading the
# canonical phase — which must be transitively declared by the consumer.
VARIANT_ALIASES: Dict[str, str] = {
    "adversarial_debate": "debate",
    "counter_arguments": "counter",
    "quality_baseline": "quality",
    "quality_recheck": "quality",
    "fallacy_detection": "hierarchical_fallacy",
    "belief_tracking": "jtms",
}

# The shared label-source helper (#2969's "fallback key after extract"):
# quality keys after the canonical ``extract`` source are label fallbacks,
# not aggregated quality axes. ``extract`` itself stays a real requirement
# for every caller.
LABEL_HELPER = "_extract_arguments_from_context"
LABEL_FALLBACK_KEYS = frozenset({"quality_baseline", "quality"})
LABEL_ANCHOR = "extract"


def _phase_table() -> Dict[str, Tuple[str, List[str]]]:
    """Spectacular phases as {name: (capability, declared deps)}."""
    wf = build_spectacular_workflow()
    phases = getattr(wf, "phases", None)
    items = (
        phases.items() if isinstance(phases, dict) else [(p.name, p) for p in phases]
    )
    return {
        name: (
            str(getattr(p, "capability", "") or ""),
            list(getattr(p, "depends_on", None) or []),
        )
        for name, p in items
    }


def _transitive(deps: Dict[str, List[str]], name: str) -> Set[str]:
    out: Set[str] = set()
    stack: List[str] = list(deps.get(name, []))
    while stack:
        d = stack.pop()
        if d in out:
            continue
        out.add(d)
        stack.extend(deps.get(d, []))
    return out


def _analyze_function(fn: Callable) -> Tuple[Set[str], bool]:
    """Return (phase keys read in code, calls the label helper).

    The first-statement string literal (the docstring) is skipped by
    construction: a prose mention of ``phase_x_output`` is not a read.
    """
    src = textwrap.dedent(inspect.getsource(fn))
    fdef = ast.parse(src).body[0]
    body = fdef.body  # type: ignore[attr-defined]
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    reads: Set[str] = set()
    calls_helper = False
    for stmt in body:
        for node in ast.walk(stmt):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and KEY_RE.match(node.value)
            ):
                reads.add(KEY_RE.match(node.value).group(1))  # type: ignore[union-attr]
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == LABEL_HELPER
            ):
                calls_helper = True
    return reads, calls_helper


def _check_reads(
    phases: Dict[str, Tuple[str, List[str]]],
    cap_to_fn: Dict[str, Callable],
    helper: Callable = None,  # type: ignore[assignment]
) -> List[str]:
    """Census every read and demand a transitive dependency behind it.

    Returns human-readable violations. A phase reading its OWN key also
    reddens: the executor publishes a phase's output only after its level
    ends, so a self-read sees a key that has not been written.
    """
    deps = {name: dep_list for name, (_cap, dep_list) in phases.items()}
    helper_reads: Set[str] = set()
    if helper is not None:
        helper_reads, _ = _analyze_function(helper)
    violations: List[str] = []
    for name, (cap, _dep_list) in sorted(phases.items()):
        fn = cap_to_fn.get(cap)
        if fn is None:
            violations.append(f"{name}: capability {cap!r} resolves to no invoker")
            continue
        t = _transitive(deps, name)
        try:
            reads, calls_helper = _analyze_function(fn)
        except (OSError, TypeError):
            violations.append(f"{name}: no inspectable source for {fn}")
            continue
        for producer in sorted(reads):
            if producer == name:
                violations.append(
                    f"{name} reads phase_{producer}_output — its own key, "
                    "which is not written until its level ends"
                )
                continue
            canonical = VARIANT_ALIASES.get(producer, producer)
            if canonical in t:
                continue
            violations.append(
                f"{name} reads phase_{producer}_output but {canonical!r} "
                "is not a transitive depends_on dependency"
            )
        if calls_helper:
            for producer in sorted(helper_reads):
                if producer == name:
                    violations.append(f"{name}: label helper reads its own key")
                    continue
                if producer in LABEL_FALLBACK_KEYS:
                    # Classified: label-source fallback AFTER the extract
                    # anchor (property pinned by its own test below).
                    continue
                if producer in t:
                    continue
                violations.append(
                    f"{name} reaches phase_{producer}_output via the label "
                    f"helper but {producer!r} is not a transitive dependency"
                )
    return violations


def _spectacular_cap_to_fn() -> Dict[str, Callable]:
    """Resolve every spectacular capability to its unique invoke function."""
    registry = setup_registry()
    cap_to_fn: Dict[str, Callable] = {}
    for _name, (cap, _deps) in _phase_table().items():
        if not cap or cap in cap_to_fn:
            continue
        providers = registry.find_for_capability(cap)
        fns = {getattr(p, "invoke", None) for p in providers}
        fns.discard(None)
        if len(fns) == 1:
            cap_to_fn[cap] = next(iter(fns))
    return cap_to_fn


class TestSpectacularReadsDeclared:
    """#2969 Expected 2 — the guard itself, over the real workflow."""

    def test_every_read_is_declared_or_classified(self) -> None:
        phases = _phase_table()
        cap_to_fn = _spectacular_cap_to_fn()
        violations = _check_reads(
            phases, cap_to_fn, helper=getattr(invoke_callables, LABEL_HELPER)
        )
        assert violations == [], "\n".join(violations)

    def test_capability_resolution_has_no_hole(self) -> None:
        """No silent skip: every spectacular phase's capability resolves to
        exactly one invoke function (a phase the census cannot read is a
        hole in the guard, not a pass)."""
        phases = _phase_table()
        cap_to_fn = _spectacular_cap_to_fn()
        missing = sorted(
            name for name, (cap, _d) in phases.items() if cap not in cap_to_fn
        )
        assert missing == [], f"unresolved capabilities: {missing}"


class TestGuardClassifications:
    """The false alerts the issue named, classified by mechanism + witness."""

    def test_docstring_mention_is_not_a_read(self) -> None:
        """False alert #1 (a docstring): prose mentioning a key does not
        count; the same key read in code does."""

        async def _docstring_only(_t: str, _c: Dict[str, Any]) -> Dict[str, Any]:
            """Prose about phase_b_output — this is NOT a read."""
            return {}

        reads, _ = _analyze_function(_docstring_only)
        assert reads == set()

        async def _code_reader(_t: str, c: Dict[str, Any]) -> Dict[str, Any]:
            """Docstring says nothing."""
            return {"upstream": c.get("phase_b_output", {})}

        reads, _ = _analyze_function(_code_reader)
        assert reads == {"b"}

    def test_guard_flags_sibling_read_and_edge_heals_it(self) -> None:
        """Synthetic born-red witness: a sibling read without an edge
        reddens; declaring the edge is the positive control."""

        async def _reader(_t: str, c: Dict[str, Any]) -> Dict[str, Any]:
            return {"upstream": c.get("phase_b_output", {})}

        async def _producer(_t: str, _c: Dict[str, Any]) -> Dict[str, Any]:
            return {}

        phases = {"a": ("cap_a", ["root"]), "b": ("cap_b", [])}
        cap_to_fn = {"cap_a": _reader, "cap_b": _producer}
        violations = _check_reads(phases, cap_to_fn)
        assert any("phase_b_output" in v for v in violations)

        healed = dict(phases)
        healed["a"] = ("cap_a", ["root", "b"])
        assert _check_reads(healed, cap_to_fn) == []

    def test_self_read_reddens(self) -> None:
        """A phase reading its own key sees an unwritten key — same empty-
        read class, so the guard refuses it too."""

        async def _self_reader(_t: str, c: Dict[str, Any]) -> Dict[str, Any]:
            return {"prev": c.get("phase_a_output", {})}

        phases = {"a": ("cap_a", [])}
        violations = _check_reads(phases, {"cap_a": _self_reader})
        assert any("its own key" in v for v in violations)

    def test_variant_aliases_match_the_governance_invoker(self) -> None:
        """Anti-stale: every alias key really is read by _invoke_governance
        (they come from its _resolve_phase_output calls) and really resolves
        to a declared dependency; no unmapped variant survives there."""
        reads, _ = _analyze_function(invoke_callables._invoke_governance)
        mapped_here = {k for k in reads if k in VARIANT_ALIASES}
        assert mapped_here == set(VARIANT_ALIASES), (
            f"governance reads variants {sorted(mapped_here)} but "
            f"VARIANT_ALIASES covers {sorted(VARIANT_ALIASES)}"
        )
        deps = {n: d for n, (_c, d) in _phase_table().items()}
        t = _transitive(deps, "governance")
        for variant, canonical in sorted(VARIANT_ALIASES.items()):
            assert canonical in t, (
                f"variant {variant} canonicalizes to {canonical!r}, which "
                "governance does not transitively depend on"
            )

    def test_label_fallback_anchor_is_first(self) -> None:
        """The label-fallback classification leans on the helper reading
        ``extract`` BEFORE its fallback keys — the guard re-checks the
        property, so a chain reorder reddens here instead of inheriting
        the pass."""
        helper = getattr(invoke_callables, LABEL_HELPER)
        src = textwrap.dedent(inspect.getsource(helper))
        ordered: List[Tuple[int, str]] = []
        for node in ast.walk(ast.parse(src)):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and KEY_RE.match(node.value)
            ):
                ordered.append((node.lineno, KEY_RE.match(node.value).group(1)))  # type: ignore[union-attr]
        ordered.sort()
        assert ordered, "label helper reads no phase key at all"
        assert ordered[0][1] == LABEL_ANCHOR, (
            f"label helper reads {ordered[0][1]!r} first — the fallback "
            "classification no longer holds"
        )


class TestDeclaredEdges:
    """#2969 Expected 1 — the DAG witnesses (born red on main)."""

    @staticmethod
    def _deps() -> Dict[str, List[str]]:
        return {n: d for n, (_c, d) in _phase_table().items()}

    def test_quality_waits_for_hierarchical_fallacy(self) -> None:
        t = _transitive(self._deps(), "quality")
        assert "hierarchical_fallacy" in t

    def test_governance_aggregates_its_axes(self) -> None:
        t = _transitive(self._deps(), "governance")
        assert {"counter", "debate", "jtms"} <= t

    def test_debate_waits_for_jtms(self) -> None:
        t = _transitive(self._deps(), "debate")
        assert "jtms" in t

    def test_jtms_declares_its_formal_sources(self) -> None:
        """The fol/pl reads only worked by the accident of levels."""
        t = _transitive(self._deps(), "jtms")
        assert {"fol", "pl"} <= t

    def test_dialogue_declares_counter(self) -> None:
        """Same accident-of-levels class: counter-arguments feed the
        opponent positions."""
        t = _transitive(self._deps(), "dialogue_reasoning")
        assert "counter" in t
