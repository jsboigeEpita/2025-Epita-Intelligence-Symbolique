"""Dung labelling trajectory under sequential argument arrival (Track S6-A2 #1506).

A CoursIA strate-6 **Phase-A candidate substrate (#1)** — "the discourse as a
substrate": a discourse that delivers arguments one by one induces a
**trajectory of labelling states** (in / out / undec) under grounded semantics.
This module computes that trajectory by consuming the existing
:mod:`abs_arg_dung.backends` grounded reasoner; it implements **no** Dung
semantics of its own (anti-pendule: reuse, don't reimplement — I5/po-2025 owns
the backend in ``abs_arg_dung/backends/**``).

Concept
-------
A *labelling* of an argumentation framework (AF) under a semantics is a total
function ``L: Args -> {in, out, undec}``. From the unique grounded extension
``G`` (computed by :func:`abs_arg_dung.backends.compute_grounded`):

* ``in    = G``                              — accepted (defended) arguments
* ``out   = { x : some g in G attacks x }``  — rejected by an accepted argument
* ``undec = Args \\ (in ∪ out)``             — undecided (typically cycles)

A *trajectory* fixes an arrival order over the arguments (the discourse's
rhetorical sequencing) and, for each prefix ``k``, restricts the AF to the
arguments arrived so far and records the grounded labelling. The sequence of
labellings is the substrate: it shows how each argument's status **evolves** as
the discourse unfolds — an argument accepted early may be refuted (in -> out)
when a later attacker arrives; an undecided argument may be reinstated (undec ->
in) when a defender lands.

JVM-free by design
------------------
The trajectory reuses the pure-Python ``compute_grounded`` so it is fully
unit-testable with synthetic opaque atoms and no JVM, no LLM. The CLI
(:mod:`scripts.labelling_trajectory`) adds an optional Tweety cross-check on the
full AF (honest degradation if the JVM is unavailable), reusing the
:mod:`scripts.compare_dung_backends` pattern.

Privacy HARD (S6)
-----------------
The bundled exemplar (:func:`build_discourse_exemplar`) is a **structurally
realistic synthetic AF with opaque ids** (``prop_*`` / ``arg_*`` tokens), NOT a
decrypted corpus. The substrate demonstrated here is the *trajectory-of-labellings
concept*; a corpus-derived AF would be a heavier follow-up (text -> arguments ->
attacks extraction), out of scope for this Phase-A *candidate*. Zero ``raw_text``,
zero source names, zero corpus access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Tuple

# Reuse the existing grounded reasoner (collision-safe: import, do NOT modify
# the backend subpackage — I5/po-2025 owns abs_arg_dung/backends/**).
from abs_arg_dung.backends import compute_grounded

Attack = Tuple[str, str]
LabellingMap = Dict[str, str]  # arg_id -> "in" | "out" | "undec"


@dataclass(frozen=True)
class Labelling:
    """A grounded labelling of one (sub-)framework.

    Attributes:
        arguments: The arguments present in this (sub-)framework, in arrival
            order. Kept so callers can render the labelling in discourse order.
        in_args: Accepted (grounded) arguments.
        out_args: Arguments attacked by some accepted argument.
        undec_args: The remaining arguments (neither in nor out).
    """

    arguments: Tuple[str, ...]
    in_args: frozenset[str]
    out_args: frozenset[str]
    undec_args: frozenset[str]

    def as_map(self) -> LabellingMap:
        """Return the labelling as ``{arg_id: "in"|"out"|"undec"}``."""
        m: LabellingMap = {}
        for a in self.in_args:
            m[a] = "in"
        for a in self.out_args:
            m[a] = "out"
        for a in self.undec_args:
            m[a] = "undec"
        return m


def labelling_from_grounded(
    arguments: Sequence[str], attacks: Iterable[Attack]
) -> Labelling:
    """Compute the grounded labelling of an AF.

    ``in`` = the unique grounded extension (via
    :func:`abs_arg_dung.backends.compute_grounded`); ``out`` = arguments attacked
    by some ``in`` argument; ``undec`` = the rest. Deterministic (the grounded
    extension is unique). Unknown attack endpoints are ignored, matching the
    backend's own defensive handling.
    """

    arg_tuple = tuple(arguments)
    arg_set = set(arg_tuple)
    attack_set = {(s, t) for s, t in attacks if s in arg_set and t in arg_set}

    grounded = set(compute_grounded(list(arg_tuple), list(attack_set)))
    out_args = {t for (s, t) in attack_set if s in grounded}
    # in and out are disjoint by grounded's definition (a grounded argument
    # cannot be attacked by another grounded argument), but we guard anyway.
    out_args -= grounded
    undec_args = arg_set - grounded - out_args
    return Labelling(
        arguments=arg_tuple,
        in_args=frozenset(grounded),
        out_args=frozenset(out_args),
        undec_args=frozenset(undec_args),
    )


@dataclass(frozen=True)
class TrajectoryStep:
    """One step of the labelling trajectory: the labelling after ``k`` arrivals.

    Attributes:
        step: 1-based index of the arrival count (``step == k`` means the first
            ``k`` arguments of the arrival order have landed).
        arrived: The arguments arrived so far, in arrival order.
        labelling: The grounded labelling of the sub-framework restricted to
            ``arrived``.
    """

    step: int
    arrived: Tuple[str, ...]
    labelling: Labelling


def labelling_trajectory(
    arguments: Sequence[str],
    attacks: Iterable[Attack],
    arrival_order: Sequence[str],
) -> List[TrajectoryStep]:
    """Compute the labelling trajectory under sequential argument arrival.

    For each ``k`` in ``1..len(arrival_order)``, restricts the AF to the first
    ``k`` arrived arguments (keeping only attacks whose both endpoints have
    arrived) and records the grounded labelling. The returned list is the
    trajectory — a sequence of labelling states showing how each argument's
    status evolves as the discourse unfolds.

    Args:
        arguments: All arguments of the full AF (used to validate the arrival
            order is a permutation; the trajectory itself only ever touches the
            arrived subset).
        attacks: Attack relation of the full AF.
        arrival_order: A permutation of ``arguments`` — the rhetorical order in
            which the discourse delivers them.

    Returns:
        The trajectory, one :class:`TrajectoryStep` per prefix length.

    Raises:
        ValueError: If ``arrival_order`` is not a permutation of ``arguments``
            (defensive — a mismatched order would silently produce a misleading
            trajectory).
    """

    full = set(arguments)
    if set(arrival_order) != full:
        raise ValueError(
            "arrival_order must be a permutation of arguments: "
            f"missing={full - set(arrival_order)}, "
            f"extra={set(arrival_order) - full}"
        )
    attack_list = list(attacks)

    steps: List[TrajectoryStep] = []
    arrived: List[str] = []
    for k, arg in enumerate(arrival_order, start=1):
        arrived.append(arg)
        arrived_set = set(arrived)
        prefix_attacks = [
            (s, t) for (s, t) in attack_list if s in arrived_set and t in arrived_set
        ]
        lab = labelling_from_grounded(tuple(arrived), prefix_attacks)
        steps.append(TrajectoryStep(step=k, arrived=tuple(arrived), labelling=lab))
    return steps


def label_transitions(
    trajectory: Sequence[TrajectoryStep],
) -> Dict[str, Tuple[str, ...]]:
    """Per-argument label sequence across the trajectory (after its first arrival).

    Returns ``{arg_id: (label_at_step_of_arrival, ..., label_at_final_step)}``.
    An argument's sequence starts at the step where it arrives (its label before
    arrival is undefined). Useful to surface the dynamics (in -> out, undec ->
    in) that make the trajectory a non-trivial substrate.
    """

    transitions: Dict[str, Tuple[str, ...]] = {}
    for step in trajectory:
        m = step.labelling.as_map()
        for arg, label in m.items():
            transitions.setdefault(arg, ())
            if arg in step.arrived:
                transitions[arg] = (*transitions[arg], label)
    return transitions


def render_trajectory(trajectory: Sequence[TrajectoryStep]) -> str:
    """Human-readable table of the trajectory (step | arrived | in/out/undec)."""

    lines = ["step | arrived            | in          | out         | undec"]
    lines.append("-----+-------------------+-------------+-------------+------")
    for step in trajectory:
        lab = step.labelling
        lines.append(
            f" {step.step:>2} | {','.join(step.arrived):<17} | "
            f"{','.join(sorted(lab.in_args)) or '-':<11} | "
            f"{','.join(sorted(lab.out_args)) or '-':<11} | "
            f"{','.join(sorted(lab.undec_args)) or '-'}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Structural exemplar (opaque ids, privacy HARD)                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DiscourseExemplar:
    """A structurally-realistic synthetic AF with opaque ids (privacy HARD).

    The exemplar is NOT a decrypted corpus: it is a hand-crafted framework
    designed to exhibit the full labelling-trajectory dynamics (an argument
    accepted then refuted; an undecided argument reinstated by a defender). The
    substrate is the trajectory *concept*; this instance makes it concrete and
    falsifiable for the CoursIA Phase-A candidate #1.
    """

    arguments: Tuple[str, ...]
    attacks: Tuple[Attack, ...]
    arrival_order: Tuple[str, ...]
    notes: Tuple[str, ...] = field(default_factory=tuple)


def build_discourse_exemplar() -> DiscourseExemplar:
    """Build the canonical S6-A2 discourse exemplar (opaque ids, deterministic).

    Structure (opaque ``prop_*`` ids — no source content, privacy HARD):

    * ``prop_thesis`` — an unattacked opening claim (the discourse's thesis).
    * ``prop_counter`` — an attacker that later refutes the thesis.
    * ``prop_cycle_a`` / ``prop_cycle_b`` — a mutual-attack pair (a 2-cycle),
      undecided in isolation.
    * ``prop_defender`` — an unattacked late argument that attacks the cycle,
      reinstating one member of the pair.

    Arrival order is chosen so the trajectory shows three genuine dynamics:
    acceptance (``prop_thesis`` in), refutation (``prop_thesis`` in -> out when
    ``prop_counter`` lands), and reinstatement (a cycle member undec -> in when
    ``prop_defender`` lands). Returned ids are opaque; ``notes`` describe the
    intended dynamics without any source-revealing content.
    """

    arguments = (
        "prop_thesis",
        "prop_counter",
        "prop_cycle_a",
        "prop_cycle_b",
        "prop_defender",
    )
    attacks = (
        # The counter refutes the thesis (delivered AFTER the thesis).
        ("prop_counter", "prop_thesis"),
        # A mutual-attack 2-cycle: undecided in isolation.
        ("prop_cycle_a", "prop_cycle_b"),
        ("prop_cycle_b", "prop_cycle_a"),
        # A defender (unattacked) attacks one cycle member; under grounded this
        # defends the OTHER member of the pair (reinstatement: undec -> in).
        ("prop_defender", "prop_cycle_a"),
    )
    arrival_order = (
        "prop_thesis",  # step 1: thesis accepted (in).
        "prop_cycle_a",  # step 2: cycle half arrives, alone -> in (unattacked).
        "prop_cycle_b",  # step 3: cycle completes -> both undec.
        "prop_counter",  # step 4: thesis refuted (in -> out).
        "prop_defender",  # step 5: defender lands -> cycle_b reinstated (undec -> in).
    )
    notes = (
        "Structural exemplar only — opaque ids, no source content (privacy HARD).",
        "Dynamics demonstrated: acceptance, refutation (in->out), reinstatement (undec->in).",
    )
    return DiscourseExemplar(
        arguments=arguments, attacks=attacks, arrival_order=arrival_order, notes=notes
    )
