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
(the ``random`` personality is never assigned).

Anti-pendulum (#3386): a coalition that changes no ballot is a measured fact
recorded on the state, never a rendered result — ``coalition_note`` prints a
bloc only when it moved the outcome, and a manipulability finding only when
the declared profile is actually pivotal.
"""

from typing import Any, Dict, List

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
        a.name: PLAY_STANCES[i % len(PLAY_STANCES)] for i, a in enumerate(agents)
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


def coalition_note(decision: Dict[str, Any]) -> str:
    """Render the coalition play's block for the act prompts (#3386).

    Reads a ``governance_decisions`` record (not the raw verdict): the writer
    stores ``coalition`` (blocs + ballots moved + outcome change) and
    ``manipulability`` (a pivot the #3385 engine found on the declared
    profile) only when they exist — honest absence.

    Anti-pendulum: a line is printed ONLY for a change. A bloc that moved no
    ballot, or a negotiation that changed no outcome, stays on the record and
    prints nothing. A pivot names its pair and the winner it would produce —
    a coalition that cannot say what it changes is not rendered.
    """
    lines: List[str] = []
    coalition = decision.get("coalition")
    if isinstance(coalition, dict) and coalition.get("outcome_changed"):
        moved = coalition.get("ballots_moved") or []
        names = ", ".join(str(m) for m in moved[:3])
        extra = f" (+{len(moved) - 3} autres)" if len(moved) > 3 else ""
        blocs = coalition.get("blocs") or []
        bloc_txt = ""
        if blocs:
            members = blocs[0].get("members") or []
            bloc_txt = (
                f" derrière « {blocs[0].get('option', '')} »"
                f" ({', '.join(str(m) for m in members[:3])})"
                if members
                else ""
            )
        lines.append(
            "Jeu de coalitions : {n} électeur(s){bloc} ont déplacé leur "
            "bulletin ({names}{extra}) ; le vainqueur passe de « {w0} » à "
            "« {w1} ».".format(
                n=len(moved),
                bloc=bloc_txt,
                names=names,
                extra=extra,
                w0=coalition.get("winner_declared", ""),
                w1=coalition.get("winner_cast", ""),
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
