"""AIF-attacks → Dung-framework adapter.

Background
----------
The Argument Interchange Format (AIF) is the standard interchange model for
argumentation structures. It distinguishes three families of attack relations
between abstract arguments:

- ``undercut`` (U-): attacks the *inference link* between premises and conclusion.
- ``undermine`` (UM-): attacks a *premise* of an argument.
- ``rebut`` (R-): attacks the *conclusion* of an argument.

Dung's abstract framework is strictly binary: every attack is a directed edge
``(source, target)`` with no semantic enrichment. The reduction from AIF to
Dung is therefore a *projection*: each AIF relation becomes a flat Dung
attack. The information loss is structural — Dung **cannot** distinguish
``undercut`` from ``undermine`` from ``rebut`` once projected.

This adapter provides:

* :func:`aif_attacks_to_dung_af` — pure projection (deterministic, JVM-free).
* :func:`verify_aif_to_dung` — runs the projection through both backends
  (``backend_python`` and the Tweety-backed ``DungAgent``) and compares
  the resulting grounded / complete / stable labellings.

Why this lives here
-------------------
The AIF relation space is a *new input* for our Dung backend — a north-star
capability on the path to a richer argumentation model. The adapter sits
next to the core backends so the comparison script can pick it up the same
way it picks up the ICCMA parser or the synthetic generators.

Anti-pendule
------------
The adapter is purely mechanical — no semantic interpretation of AIF
relations survives the projection. Disagreement between backends on the
projected framework is **never** reconciled (I5 / #1502 invariant); it is
reported verbatim. If a backend is unavailable (no JVM), the report carries
``available=False`` and the comparison degrades honestly.
"""

from __future__ import annotations

from typing import Any, Iterable, List, NamedTuple, Sequence, Tuple

# Reuse the canonical Framework type used by the ICCMA parser.
from .backends.generators import Attack, Framework

# Backend report shape — same as ``scripts/compare_dung_backends.BackendReport``.
# We import the runtime types lazily inside ``_run_python`` / ``_try_run_tweety``
# to avoid a hard dependency on the JVM at import time.
BackendReport = dict[str, Any]
VerifyResult = dict[str, Any]

# AIF relation kinds. Keep the set closed: extending it requires updating
# :func:`aif_attacks_to_dung_af` and the tests.
AIF_KIND_UNDERCUT = "undercut"
AIF_KIND_UNDERMINE = "undermine"
AIF_KIND_REBUT = "rebut"

AIF_KINDS = frozenset({AIF_KIND_UNDERCUT, AIF_KIND_UNDERMINE, AIF_KIND_REBUT})


class AIFAttack(NamedTuple):
    """A single AIF attack relation.

    Attributes
    ----------
    source:
        Identifier of the attacking argument.
    target:
        Identifier of the argument under attack.
    kind:
        One of ``"undercut"``, ``"undermine"``, ``"rebut"``.
    """

    source: str
    target: str
    kind: str


def _validate_kind(kind: str) -> None:
    if kind not in AIF_KINDS:
        raise ValueError(
            f"Unknown AIF attack kind: {kind!r}. "
            f"Expected one of {sorted(AIF_KINDS)}."
        )


def aif_attacks_to_dung_af(
    arguments: Sequence[str],
    aif_attacks: Iterable[AIFAttack],
) -> Framework:
    """Project AIF attacks onto a flat Dung framework.

    Every AIF relation is reduced to a directed edge ``(source, target)``.
    The ``kind`` field is preserved for traceability but does not influence
    the resulting framework's structure — Dung is strictly binary.

    Parameters
    ----------
    arguments:
        Identifiers of the arguments participating in the framework. The
        order is preserved on output for determinism.
    aif_attacks:
        Iterable of :class:`AIFAttack` triples. Duplicates (same source,
        target, kind) are silently de-duplicated.

    Returns
    -------
    ``(sorted_arguments, sorted_attacks)`` — the canonical Dung framework
    shape consumed by :func:`abs_arg_dung.backends.backend_python` and the
    ICCMA parser pathways.
    """
    argument_set = set(arguments)
    seen: set[Tuple[str, str, str]] = set()
    attack_set: set[Tuple[str, str]] = set()

    for aif in aif_attacks:
        _validate_kind(aif.kind)
        if aif.source == aif.target:
            # Self-attacks are well-defined in Dung (the argument is then
            # never in any admissible set). We preserve them rather than
            # silently dropping them — silent drops are a classic
            # anti-#1019 trap.
            pass
        # Register any argument that appears in an attack edge. The
        # ``arguments`` list is the *primary* declaration, but we also
        # accept implicit declarations via attack edges — this matches
        # the behaviour of the ICCMA parser and keeps the adapter
        # permissive without losing information.
        argument_set.add(aif.source)
        argument_set.add(aif.target)
        key = (aif.source, aif.target, aif.kind)
        if key in seen:
            continue
        seen.add(key)
        attack_set.add((aif.source, aif.target))

    return (sorted(argument_set), sorted(attack_set))


# ---------------------------------------------------------------------------
# Backend verification (mirrors scripts/compare_dung_backends.py pattern)
# ---------------------------------------------------------------------------


def _run_python(args: List[str], atts: List[Attack]) -> BackendReport:
    """Run the pure-Python backend and return its report."""
    from .backends import backend_python

    # ``_BackendResult`` is a TypedDict which mypy treats as a distinct
    # nominal type; wrap into a plain dict so the declared
    # ``BackendReport`` (used by callers / verification) matches.
    result = backend_python(args, atts)
    return dict(result)


def _try_run_tweety(
    args: List[str], atts: List[Attack]
) -> Tuple[bool, BackendReport | None]:
    """Run the Tweety backend (JVM-dependent). Returns ``(ok, report)``.

    If the JVM bridge is unavailable, returns ``(False, None)`` and the
    comparison degrades honestly to pure-Python only. The caller is
    responsible for reporting this in the final output.
    """
    try:
        from abs_arg_dung.agent import DungAgent  # sanctuary #893
        from argumentation_analysis.core.jvm_setup import initialize_jvm
    except Exception:
        return False, None

    try:
        if not initialize_jvm():
            return False, {
                "backend": "tweety",
                "available": False,
                "note": "JVM unavailable (initialize_jvm returned False)",
            }
        agent = DungAgent()  # type: ignore[no-untyped-call]
        for a in args:
            agent.add_argument(a)
        for src, tgt in atts:
            agent.add_attack(src, tgt)
        return True, {
            "backend": "tweety",
            "available": True,
            "note": "abs_arg_dung.DungAgent via JPype (Tweety 1.28)",
            "extensions": {
                "grounded": [sorted(agent.get_grounded_extension())],
                "complete": [sorted(ext) for ext in agent.get_complete_extensions()],
                "stable": [sorted(ext) for ext in agent.get_stable_extensions()],
            },
            "elapsed_ms": 0.0,
        }
    except Exception as exc:  # pragma: no cover — JVM-dependent
        return False, {
            "backend": "tweety",
            "available": False,
            "note": f"error: {exc}",
        }


def _extensions_match(a: BackendReport, b: BackendReport) -> bool:
    """Compare two backend reports semantic-by-semantic.

    A disagreement is reported by the caller (the verification summary);
    this helper never silently coerces one side to the other.
    """
    for key in ("grounded", "complete", "stable"):
        ext_a = a.get("extensions", {}).get(key, [])
        ext_b = b.get("extensions", {}).get(key, [])
        if sorted(ext_a) != sorted(ext_b):
            return False
    return True


def verify_aif_to_dung(
    arguments: Sequence[str],
    aif_attacks: Iterable[AIFAttack],
) -> VerifyResult:
    """Project AIF attacks onto Dung and verify both backends agree.

    Returns a summary dict with the following keys:

    - ``framework``: the projected ``(arguments, attacks)`` tuple.
    - ``backend_python``: the pure-Python backend report.
    - ``backend_tweety``: the Tweety backend report (or ``None`` if JVM
      unavailable).
    - ``agree``: True iff both backends ran successfully and produced
      identical extension sets. When Tweety is unavailable, ``agree`` is
      ``None`` (indeterminate — not the same as False).
    - ``disagreements``: list of human-readable disagreement strings,
      empty when both backends agree.
    """
    args, atts = aif_attacks_to_dung_af(arguments, aif_attacks)

    py_report = _run_python(args, atts)
    tweety_ok, tweety_report = _try_run_tweety(args, atts)

    disagreements: List[str] = []
    agree: bool | None

    if not tweety_ok or tweety_report is None:
        # Degraded mode: pure-Python only. Honest reporting.
        agree = None
    else:
        agree = _extensions_match(py_report, tweety_report)
        if not agree:
            for key in ("grounded", "complete", "stable"):
                py_ext = py_report.get("extensions", {}).get(key, [])
                tw_ext = tweety_report.get("extensions", {}).get(key, [])
                if sorted(py_ext) != sorted(tw_ext):
                    disagreements.append(
                        f"{key}: python={sorted(py_ext)} vs tweety={sorted(tw_ext)}"
                    )

    return {
        "framework": (args, atts),
        "backend_python": py_report,
        "backend_tweety": tweety_report,
        "agree": agree,
        "disagreements": disagreements,
    }


__all__ = [
    "AIFAttack",
    "AIF_KIND_UNDERCUT",
    "AIF_KIND_UNDERMINE",
    "AIF_KIND_REBUT",
    "AIF_KINDS",
    "aif_attacks_to_dung_af",
    "verify_aif_to_dung",
    "Framework",
    "Attack",
]