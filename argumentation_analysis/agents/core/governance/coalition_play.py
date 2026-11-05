"""Coalition play over the derived governance profile (#3386).

The governance vote's electors are the quality virtues, each holding a ballot
ranked by its own scores (``_derive_governance_profile``). Until #3386 those
electors were fixed-preference voters: the ``Agent`` machinery they are built
from (personalities, negotiation, coalitions — adapted from the 2.1.6
prototype) never ran, so a coalition could neither form nor change anything.

This module runs that machinery on the derivation's own outputs — there is no
second agent path: the electors are the ones ``_derive_governance_profile``
built, and the play calls the class's own ``negotiate``/``receive_argument``.
The personalities are negotiation stances ONLY: a strategic elector argues its
second preference at the table, but every elector then votes the ballot it
holds after the negotiation. The vote itself stays a fixed-preference vote —
rotating vote-time personalities would move every third elector's vote on
every document without any coalition forming, which is decoration, not play.

Deterministic by construction: stances are assigned by rotation over the
elector list (sorted, as the derivation yields it) and the play uses no RNG
(the ``random`` personality is never assigned). **The rotation reads the
SEAT order, not a measured property** — so one play is a fabricated input
(#3418 R1144): rotating the elector list alone moved the cast winner. The
verdict must therefore never consume the play; ``play_sensitivity`` runs it
under every cyclic shift of the stances and reports the outcome as a
sensitivity, and the caller keeps voting the DECLARED profile.

Anti-pendulum (#3386): a coalition that changes no ballot is a measured fact
recorded on the state, never a rendered result — ``coalition_note`` prints a
flip only when the winner changes AND is the same under every shift, and a
manipulability finding only when the declared profile is actually pivotal.
"""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from argumentation_analysis.agents.core.governance.governance_agent import Agent

# Stances the play assigns, in rotation. ``random`` is excluded on purpose:
# it draws from ``np.random`` and would make the play irreproducible.
PLAY_STANCES = ("stubborn", "flexible", "strategic")
PLAY_ROUNDS = 3


def play_governance_rounds(
    agents: List[Agent],
    options: List[str],
    ballots: List[List[str]],
    rounds: int = PLAY_ROUNDS,
    stance_offset: int = 0,
) -> Dict[str, Any]:
    """Negotiate over the derived profile, then read the coalitions off it.

    The electors negotiate in round-robin: each proposes or argues an option
    (``Agent.negotiate``), and every other elector receives the proposal
    (``Agent.receive_argument`` — a *flexible* elector moves a proposed option
    it ranks to the front of its own ballot; stubborn and strategic electors
    listen but never move). After the rounds, electors sharing the same ballot
    top form a named bloc (``Agent.coalition``).

    The caller's agents and ballots are never mutated: the play runs on
    copies, so the declared profile stays measurable afterwards (the
    manipulability engine and the outcome-change probe both read it).

    Returns a dict with:

    - ``cast_ballots`` / ``cast_agents`` — what the electors vote after the
      negotiation. When nothing moved these ARE the inputs (identity, not a
      copy), so aggregating them is byte-identical to the pre-play vote.
    - ``blocs`` — the coalition structure: one entry per shared top with ≥2
      members.
    - ``moved`` — the electors whose ballot top changed, with from/to.
    - ``stances`` — the negotiation stance each elector drew.

    A bloc that formed without moving any ballot (electors already concordant)
    is still reported in ``blocs`` — it is a measured structure — but it is
    not a change, and the renderer will not print it as one.
    """
    declared = {a.name: list(a.preferences) for a in agents}
    stances: Dict[str, str] = {
        a.name: PLAY_STANCES[(i + stance_offset) % len(PLAY_STANCES)]
        for i, a in enumerate(agents)
    }
    players = [
        Agent(name=a.name, personality=stances[a.name], preferences=list(a.preferences))
        for a in agents
    ]

    for _ in range(max(0, rounds)):
        for player in players:
            action = player.negotiate(options)  # type: ignore[no-untyped-call]  # legacy governance_agent (2.1.6)
            # ``negotiate`` returns (verb, payload); every verb carries the
            # option the elector puts on the table (form_coalition's payload
            # is a partner name — it never fires here, trust starts empty).
            if not isinstance(action, tuple) or len(action) != 2:
                continue
            verb, payload = action
            option = payload if payload in options else player.preferences[0]
            for other in players:
                if other is not player:
                    other.receive_argument(  # type: ignore[no-untyped-call]  # legacy governance_agent (2.1.6)
                        {"agent": player.name, "option": option, "reason": verb}
                    )

    cast_ballots = [list(p.preferences) for p in players]
    moved: List[Dict[str, str]] = []
    for original, played in zip(agents, players):
        before = declared[original.name]
        after = played.preferences
        if after != before:
            moved.append(
                {
                    "elector": original.name,
                    "from": before[0] if before else "",
                    "to": after[0] if after else "",
                }
            )

    blocs: List[Dict[str, Any]] = []
    by_top: Dict[str, List[str]] = {}
    for played in players:
        top = played.preferences[0] if played.preferences else ""
        by_top.setdefault(top, []).append(played.name)
    for top, members in sorted(by_top.items()):
        if len(members) >= 2:
            blocs.append({"option": top, "members": list(members)})
            for played in players:
                if played.name in members:
                    played.coalition = f"bloc_{top}"

    if not moved:
        # Nothing moved: the play changed nothing, and the vote must be the
        # vote the derivation already describes — return the inputs as the
        # cast (identity), so downstream aggregation is byte-identical.
        return {
            "cast_ballots": list(ballots),
            "cast_agents": list(agents),
            "blocs": blocs,
            "moved": [],
            "stances": stances,
            "rounds": max(0, rounds),
        }
    # The ballot an elector casts is the order it holds after the negotiation
    # — voted as cast (stubborn), not re-shaped at the urn.
    cast_agents = [
        Agent(name=a.name, personality="stubborn", preferences=list(b))
        for a, b in zip(agents, cast_ballots)
    ]
    return {
        "cast_ballots": cast_ballots,
        "cast_agents": cast_agents,
        "blocs": blocs,
        "moved": moved,
        "stances": stances,
        "rounds": max(0, rounds),
    }


def play_sensitivity(
    agents: List[Agent],
    options: List[str],
    ballots: List[List[str]],
    aggregate: Callable[[List[Any], List[str], List[List[str]]], Dict[str, Any]],
    rounds: int = PLAY_ROUNDS,
) -> Dict[str, Any]:
    """The play as a SENSITIVITY, never as the verdict (#3418 R1144).

    TWO arbitrary inputs decide a play, not one, and an earlier revision of
    this function varied only the first:

    - the **seat order**, which the code assigns stances over
      (``PLAY_STANCES[(i + shift) % 3]``) AND which fixes the round-robin —
      who negotiates before whom, hence who hears which proposal last, hence
      where a flexible elector's ballot lands;
    - the **stance shift**, the offset into that rotation.

    Measured on the planted profile (review 2, coordinator): holding the
    shift family fixed and rotating the seats gives ``arg_3 ×3`` then
    ``arg_3, arg_1, arg_2`` then ``arg_1, arg_2, arg_2`` then ``arg_2 ×3``
    then ``arg_2, arg_3, arg_3`` — all three arguments win somewhere, so a
    line printed off one seat rotation is a fact about the alphabet.

    The family is therefore ``len(agents) × len(PLAY_STANCES)`` deterministic
    plays — every seat rotation against every stance shift — and the outcome
    is reported as a sensitivity of the DECLARED verdict:

    - ``plays`` / ``rotations`` / ``shifts`` — the family's size and its two
      axes, so the record says what was enumerated;
    - ``winners`` — ``winners[rotation][shift]``, the cast winner of each play;
    - ``outcome_changed`` — true only when the winner moves AND is the same
      across the whole family (a robust flip, not an artefact of either axis);
    - ``stance_dependent`` — true when any two plays disagree; nothing renders;
    - ``uniform_winner`` — the winner when every play agrees, else ``None``;
    - ``ballots_moved`` — electors whose ballot moved in EVERY play (the
      stable movers; the per-play movers are not summed or averaged);
    - ``blocs`` — blocs present in every play (stable structure).

    The family is still a SUBSET of every possible assignment: it is exactly
    what the code itself introduces, enumerated. No RNG, no sampling, no
    majority — one disagreeing play is enough.

    ``aggregate`` is the caller's own aggregation function, injected: this
    module must not import the orchestration layer that calls it.
    """
    declared_winner = aggregate(agents, options, ballots).get("winner")
    rotations = max(1, len(agents))
    shifts = len(PLAY_STANCES)
    winners: List[List[Optional[str]]] = []
    moved_sets: List[Set[str]] = []
    bloc_sets: List[Set[Tuple[str, Tuple[str, ...]]]] = []
    for rotation in range(rotations):
        rotated = agents[rotation:] + agents[:rotation]
        # The DECLARED ballots rotate with their electors (#3418 review 3):
        # ``ballots`` is what the caller aggregates, so rebuilding the list
        # from ``a.preferences`` would play a different election whenever the
        # two disagree. A length mismatch is a CALLER error and raises (#3418
        # review 4, R1144c): silently falling back to ``a.preferences`` here
        # would play that different election without saying so — the exact
        # drift the rotation was introduced to prevent.
        if len(ballots) != len(agents):
            raise ValueError(
                "play_sensitivity: ballots and agents must be aligned "
                f"list-by-list ({len(ballots)} ballot(s) for {len(agents)} "
                "agent(s)) — the declared ballots rotate with their electors"
            )
        rotated_ballots = list(ballots[rotation:]) + list(ballots[:rotation])
        row: List[Optional[str]] = []
        for shift in range(shifts):
            play = play_governance_rounds(
                rotated,
                options,
                rotated_ballots,
                rounds=rounds,
                stance_offset=shift,
            )
            cast = aggregate(play["cast_agents"], options, play["cast_ballots"])
            row.append(None if cast.get("winner") is None else str(cast["winner"]))
            moved_sets.append({str(m["elector"]) for m in play["moved"]})
            bloc_sets.append(
                {
                    (str(b["option"]), tuple(sorted(str(x) for x in b["members"])))
                    for b in play["blocs"]
                }
            )
        winners.append(row)

    flat = [w for row in winners for w in row]
    uniform = flat[0] if flat and len(set(flat)) == 1 else None
    stance_dependent = len(set(flat)) > 1
    stable_movers = sorted(set.intersection(*moved_sets)) if moved_sets else []
    stable_blocs: List[Tuple[str, Tuple[str, ...]]] = (
        sorted(set.intersection(*bloc_sets)) if bloc_sets else []
    )
    return {
        "plays": rotations * shifts,
        "rotations": rotations,
        "shifts": shifts,
        "winners": winners,
        "winner_declared": None if declared_winner is None else str(declared_winner),
        "uniform_winner": uniform,
        "outcome_changed": uniform is not None and uniform != declared_winner,
        "stance_dependent": stance_dependent,
        "ballots_moved": stable_movers,
        "blocs": [
            {"option": option, "members": list(members)}
            for option, members in stable_blocs
        ],
    }


def coalition_note(decision: Dict[str, Any]) -> str:
    """Render the coalition play's block for the act prompts (#3386).

    Reads a ``governance_decisions`` record (not the raw verdict): the writer
    stores ``coalition`` (the stance sensitivity ``play_sensitivity``
    computed) and ``manipulability`` (a pivot the #3385 engine found on the
    declared profile) only when they exist — honest absence.

    Anti-pendulum (#3418 R1144): a flip line is printed ONLY when the winner
    changes AND is the same across the WHOLE enumerated family — every seat
    rotation against every stance shift (``outcome_changed``, never
    ``stance_dependent``). A play whose result depends on the seat order or on
    the shift is not a finding, it is the fabricated input itself.

    The wording is scoped to what was enumerated (« sous les N attributions
    testées »), never to « whatever the assignment »: the family is the set of
    arbitrary inputs the code introduces, not every possible one. A pivot names
    its pair and the winner it would produce, unchanged.
    """
    lines: List[str] = []
    coalition = decision.get("coalition")
    if (
        isinstance(coalition, dict)
        and coalition.get("outcome_changed")
        and not coalition.get("stance_dependent")
    ):
        moved = coalition.get("ballots_moved") or []
        blocs = coalition.get("blocs") or []
        shifts = coalition.get("shifts") or 0
        rotations = coalition.get("rotations") or 0
        plays = coalition.get("plays") or (rotations * shifts)
        family = (
            f"{plays} attributions testées ({rotations} ordres de parole × "
            f"{shifts} décalages de posture)"
            if rotations and shifts
            else f"{plays} attributions testées"
        )
        if moved:
            names = ", ".join(str(m) for m in moved[:3])
            extra = f" (+{len(moved) - 3} autres)" if len(moved) > 3 else ""
            verb = (
                "déplace son bulletin" if len(moved) == 1 else "déplacent leur bulletin"
            )
            movers = f" ; {len(moved)} électeur(s) {verb} dans toutes les attributions ({names}{extra})"
            if blocs:
                members = blocs[0].get("members") or []
                if members:
                    movers += (
                        f" derrière « {blocs[0].get('option', '')} »"
                        f" ({', '.join(str(m) for m in members[:3])})"
                    )
        else:
            movers = " ; les électeurs qui bougent dépendent de l'attribution"
        lines.append(
            "Jeu de coalitions : sous les {family}, "
            "le vainqueur passe de « {w0} » à « {w1} »{movers}.".format(
                family=family,
                w0=coalition.get("winner_declared", ""),
                w1=coalition.get("uniform_winner", ""),
                movers=movers,
            )
        )
    manipulability = decision.get("manipulability")
    if isinstance(manipulability, dict) and manipulability.get("players"):
        players = [str(p) for p in manipulability["players"]]
        pair = " et ".join(players)
        verb = "fait" if len(players) == 1 else "font"
        lines.append(
            "Manipulabilité du profil déclaré ({kind}, moteur de #3385) : "
            "{pair} portant « {report} » en tête {verb} gagner « {winner} » "
            "au lieu de « {baseline} ».".format(
                kind=str(manipulability.get("kind", "coalition")),
                pair=pair,
                verb=verb,
                report=manipulability.get("report", ""),
                winner=manipulability.get("winner", ""),
                baseline=manipulability.get("baseline", ""),
            )
        )
    return "\n".join(lines)
