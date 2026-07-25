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
* :func:`aif_labelling_trajectory` — the **sequential-arrival** layer (#1524):
  arguments land one by one, and after each arrival the projected framework is
  re-labelled and re-verified against both backends.

Static verification vs trajectory
---------------------------------
:func:`verify_aif_to_dung` answers "do the backends agree on *this* framework?".
:func:`aif_labelling_trajectory` answers "how does each argument's status
*evolve* as the discourse delivers its arguments one at a time?" — an argument
accepted early flips ``in -> out`` when its attacker lands later; a member of an
undecided cycle is reinstated ``undec -> in`` when a defender arrives. Every
step of that trajectory carries its own dual-backend verification.

Relationship to :mod:`argumentation_analysis.orchestration.dung_labelling_trajectory`
-------------------------------------------------------------------------------------
That module (#1509) computes the same *concept* over a plain Dung AF. This one
is deliberately **not** importing it: that package's ``__init__`` pulls in the
full orchestration stack (LLM service, crypto, fetch service — measured ~12 s
import), which would make this JVM-free adapter unusable as a lightweight
building block. The two are independent islands with a **compatible output
contract**: the same ``"in"`` / ``"out"`` / ``"undec"`` label vocabulary and the
same ``as_map()`` shape, so a consumer (e.g. a notebook cell) can render either.
No Dung semantics are reimplemented here — the grounded extension always comes
from the backends.

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

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

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


# ---------------------------------------------------------------------------
# Sequential-arrival trajectory (#1524)
# ---------------------------------------------------------------------------

# Label vocabulary — kept identical to
# ``argumentation_analysis.orchestration.dung_labelling_trajectory`` so both
# substrates render the same way downstream (compatible contract, no import).
LABEL_IN = "in"
LABEL_OUT = "out"
LABEL_UNDEC = "undec"

LabellingMap = Dict[str, str]  # arg_id -> "in" | "out" | "undec"


@dataclass(frozen=True)
class AIFLabelling:
    """A grounded labelling of one projected (sub-)framework.

    Attributes
    ----------
    arguments:
        Arguments present in this sub-framework, in arrival order.
    in_args:
        Accepted arguments — the grounded extension **as returned by the
        backend** (never recomputed here).
    out_args:
        Arguments attacked by some accepted argument.
    undec_args:
        The remainder — neither accepted nor rejected (typically cycles).
    source_backend:
        Which backend's grounded extension this labelling was derived from.
        Recorded explicitly because, when the backends disagree, the labelling
        is *one side of a disagreement* rather than a settled verdict — see
        :class:`AIFTrajectoryStep.disagreements` (I5 / #1502).
    """

    arguments: Tuple[str, ...]
    in_args: frozenset[str]
    out_args: frozenset[str]
    undec_args: frozenset[str]
    source_backend: str

    def as_map(self) -> LabellingMap:
        """Return the labelling as ``{arg_id: "in"|"out"|"undec"}``."""
        m: LabellingMap = {}
        for a in self.in_args:
            m[a] = LABEL_IN
        for a in self.out_args:
            m[a] = LABEL_OUT
        for a in self.undec_args:
            m[a] = LABEL_UNDEC
        return m


@dataclass(frozen=True)
class AIFTrajectoryStep:
    """The state of the discourse after ``step`` arguments have arrived.

    Attributes
    ----------
    step:
        1-based arrival index.
    new_argument:
        The argument that landed at this step.
    arrived:
        All arguments arrived so far, in arrival order.
    activated_attacks:
        AIF attacks that became *active* at this step — i.e. whose two
        endpoints are now both present. An attack declared up front stays
        dormant until its source (or target) arrives; that latency is exactly
        what makes the trajectory non-trivial.
    framework:
        The projected Dung framework ``(arguments, attacks)`` at this step.
    labelling:
        The grounded labelling, or ``None`` when no backend produced a grounded
        extension (degraded-honest: no fabricated verdict — anti-#1019).
    agree:
        ``True``/``False`` when both backends ran and were compared; ``None``
        when the comparison is indeterminate (Tweety unavailable, or
        ``verify=False``). ``None`` is *not* ``False``.
    disagreements:
        Backend disagreements for this step, **verbatim and never
        reconciled** (I5 / #1502 invariant).
    verification:
        The full :func:`verify_aif_to_dung` result for this step, or ``None``
        when ``verify=False``.
    """

    step: int
    new_argument: str
    arrived: Tuple[str, ...]
    activated_attacks: Tuple[AIFAttack, ...]
    framework: Framework
    labelling: Optional[AIFLabelling]
    agree: Optional[bool]
    disagreements: Tuple[str, ...]
    verification: Optional[VerifyResult]


def _labelling_from_report(
    arrived: Sequence[str],
    attacks: Sequence[Attack],
    report: BackendReport,
    source_backend: str,
) -> Optional[AIFLabelling]:
    """Derive the in/out/undec partition from a backend's grounded extension.

    The grounded extension is taken **as-is** from ``report`` — this function
    runs no reasoner of its own. It only applies the definition of a labelling:
    ``out`` is whatever an accepted argument attacks, ``undec`` is the rest.

    Returns ``None`` when the report carries no grounded extension (backend
    unavailable or failed): a missing extension yields no labelling rather than
    an invented one.
    """
    extensions = report.get("extensions", {}).get("grounded")
    if not extensions:
        return None

    grounded = set(extensions[0])
    arrived_set = set(arrived)
    out_args = {t for (s, t) in attacks if s in grounded} - grounded
    undec_args = arrived_set - grounded - out_args
    return AIFLabelling(
        arguments=tuple(arrived),
        in_args=frozenset(grounded),
        out_args=frozenset(out_args),
        undec_args=frozenset(undec_args),
        source_backend=source_backend,
    )


def aif_labelling_trajectory(
    arguments_stream: Sequence[str],
    aif_attacks_stream: Iterable[AIFAttack],
    *,
    verify: bool = True,
) -> List[AIFTrajectoryStep]:
    """Compute the labelling trajectory of an AIF discourse under sequential arrival.

    The discourse delivers its arguments one at a time, in the order given by
    ``arguments_stream``. An AIF attack becomes active only once **both** of its
    endpoints have arrived. After each arrival the adapter re-projects the
    active subset onto a Dung framework (:func:`aif_attacks_to_dung_af`),
    re-labels it, and — unless ``verify=False`` — re-verifies it against both
    backends (:func:`verify_aif_to_dung`).

    Parameters
    ----------
    arguments_stream:
        Arrival order of the arguments. Must contain no duplicates (a repeated
        argument would make "the state after step k" ambiguous).
    aif_attacks_stream:
        The AIF attacks of the whole discourse, declared up front. Every
        endpoint must appear in ``arguments_stream``.
    verify:
        When ``True`` (default) each step is cross-checked against both
        backends per the #1502 contract. When ``False`` only the pure-Python
        backend runs: the trajectory is then **unverified**, and every step
        reports ``agree=None`` — never a fabricated agreement.

    Returns
    -------
    One :class:`AIFTrajectoryStep` per arrival, in order.

    Raises
    ------
    ValueError
        If ``arguments_stream`` contains duplicates, if an attack endpoint
        never arrives, or if an attack carries an unknown AIF kind. All three
        are raised up front: a half-computed trajectory silently missing an
        attack would be worse than no trajectory at all.
    """
    arrival = list(arguments_stream)
    if len(set(arrival)) != len(arrival):
        duplicates = sorted({a for a in arrival if arrival.count(a) > 1})
        raise ValueError(f"arguments_stream must not contain duplicates: {duplicates}")

    attacks = list(aif_attacks_stream)
    for aif in attacks:
        _validate_kind(aif.kind)

    arrival_set = set(arrival)
    unknown = sorted(
        {ep for aif in attacks for ep in (aif.source, aif.target)} - arrival_set
    )
    if unknown:
        raise ValueError(
            "every AIF attack endpoint must appear in arguments_stream; "
            f"never arrive: {unknown}"
        )

    steps: List[AIFTrajectoryStep] = []
    arrived: List[str] = []
    active: List[AIFAttack] = []
    activated_idx: set[int] = set()

    for k, argument in enumerate(arrival, start=1):
        arrived.append(argument)
        arrived_so_far = set(arrived)

        # An attack activates on the step where its *second* endpoint lands.
        # Tracked by index, not by value, so exact-duplicate declarations each
        # activate once instead of collapsing into the first occurrence.
        newly: List[AIFAttack] = []
        for i, aif in enumerate(attacks):
            if i in activated_idx:
                continue
            if aif.source in arrived_so_far and aif.target in arrived_so_far:
                activated_idx.add(i)
                newly.append(aif)
        newly_active = tuple(newly)
        active.extend(newly_active)

        framework = aif_attacks_to_dung_af(arrived, active)
        args, atts = framework

        verification: Optional[VerifyResult] = None
        py_report: BackendReport
        agree: Optional[bool]
        disagreements: Tuple[str, ...]

        if verify:
            verification = verify_aif_to_dung(arrived, active)
            py_report = verification["backend_python"]
            agree = verification["agree"]
            disagreements = tuple(verification["disagreements"])
        else:
            py_report = _run_python(args, atts)
            agree = None  # unverified is indeterminate, never "agreed"
            disagreements = ()

        labelling = _labelling_from_report(arrived, atts, py_report, "backend_python")

        steps.append(
            AIFTrajectoryStep(
                step=k,
                new_argument=argument,
                arrived=tuple(arrived),
                activated_attacks=newly_active,
                framework=framework,
                labelling=labelling,
                agree=agree,
                disagreements=disagreements,
                verification=verification,
            )
        )

    return steps


def aif_label_transitions(
    trajectory: Sequence[AIFTrajectoryStep],
) -> Dict[str, Tuple[str, ...]]:
    """Per-argument label sequence, starting at the step where it arrives.

    Returns ``{arg_id: (label_at_arrival, ..., label_at_final_step)}``. This is
    where the dynamics become legible: a sequence like ``("in", "in", "out")``
    is a refutation, ``("undec", "in")`` a reinstatement. Steps whose labelling
    is unavailable (degraded) contribute no entry rather than a placeholder.
    """
    transitions: Dict[str, Tuple[str, ...]] = {}
    for step in trajectory:
        if step.labelling is None:
            continue
        label_map = step.labelling.as_map()
        for argument in step.arrived:
            label = label_map.get(argument)
            if label is None:
                continue
            transitions[argument] = (*transitions.get(argument, ()), label)
    return transitions


def render_aif_trajectory(trajectory: Sequence[AIFTrajectoryStep]) -> str:
    """Human-readable table of the trajectory (step | arrived | in/out/undec | agree).

    Mirrors the rendering of the #1509 substrate so both can be shown
    side-by-side, plus an ``agree`` column carrying the per-step dual-backend
    verdict (``=`` agree, ``!`` disagree, ``?`` indeterminate).
    """
    rows: List[Tuple[str, str, str, str, str, str]] = []
    for step in trajectory:
        mark = "=" if step.agree is True else ("!" if step.agree is False else "?")
        if step.labelling is None:
            in_s = out_s = undec_s = "(degraded)"
        else:
            in_s = ",".join(sorted(step.labelling.in_args)) or "-"
            out_s = ",".join(sorted(step.labelling.out_args)) or "-"
            undec_s = ",".join(sorted(step.labelling.undec_args)) or "-"
        rows.append(
            (str(step.step), ",".join(step.arrived), in_s, out_s, undec_s, mark)
        )

    header = ("step", "arrived", "in", "out", "undec", "agree")
    # Size every column to its widest cell so the table stays aligned whatever
    # the argument ids look like (it is read as-is in a notebook cell).
    widths = [
        max(len(header[i]), max((len(r[i]) for r in rows), default=0))
        for i in range(len(header))
    ]
    lines = [" | ".join(h.ljust(widths[i]) for i, h in enumerate(header))]
    lines.append("-+-".join("-" * w for w in widths))
    for row in rows:
        lines.append(" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)


__all__ = [
    "AIFAttack",
    "AIF_KIND_UNDERCUT",
    "AIF_KIND_UNDERMINE",
    "AIF_KIND_REBUT",
    "AIF_KINDS",
    "LABEL_IN",
    "LABEL_OUT",
    "LABEL_UNDEC",
    "AIFLabelling",
    "AIFTrajectoryStep",
    "aif_attacks_to_dung_af",
    "verify_aif_to_dung",
    "aif_labelling_trajectory",
    "aif_label_transitions",
    "render_aif_trajectory",
    "Framework",
    "Attack",
]
