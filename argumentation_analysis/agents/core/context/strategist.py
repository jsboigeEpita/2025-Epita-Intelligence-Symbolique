"""Strategist persona — the game being played (#3377, Epic #3374).

The user's mandate: a strategist "in charge of analysing the stakes in
game-theory terms". The pipeline already had a game-theoretic *read*, produced
inside ``act1_framing``, and no analysis phase depended on it — so it oriented
nothing, and died in the act that produced it.

This producer moves the read upstream into ``state.strategic_read``, and makes
it do what the vocabulary alone cannot: the preference profile the model infers
is handed to the governance engine, which **computes** the outcome and the
manipulability. The 2.1.6 student prototype (``governance/simulation.py``) asks
the same three questions — strategic voting, false coalition, bribery — by
mutating agent objects under numpy randomness. Its adapted form lives in
``argumentation_analysis/agents/core/governance/`` with the randomness removed:
:func:`~argumentation_analysis.agents.core.governance.social_choice.condorcet_winner`
is deterministic, so the same profile always yields the same verdict and a
render can be replayed.

Anti-pendulum: this module never writes a verdict about who *should* win. It
states the configuration (players, options, profile, computed outcome) and where
a single player, or a pair of players, can move the outcome by misreporting.
The same map for every side — that is the user's "neutralising light".
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from argumentation_analysis.agents.core.context import (
    MODEL_KNOWLEDGE_BASIS,
    stamp_basis,
)
from argumentation_analysis.agents.core.governance.social_choice import (
    condorcet_winner,
)
from argumentation_analysis.agents.core.reading import defining_moves
from argumentation_analysis.core.reading_window import persona_reading

logger = logging.getLogger("Strategist")

#: Bounds of the computation, named because they change what the read can say.
#: The pivot test is O(players² × options) Condorcet calls; past these the read
#: would cost more than the phase that consumes it. When a bound bites, the
#: output says so (``capped``) — a silently truncated profile would read as a
#: complete game.
MAX_PLAYERS = 12
MAX_OPTIONS = 8

#: Cap on the blind spot (#3432 ask 2): it rides the Act III prompt, so an
#: unbounded sentence would crowd the conclusion it is there to sharpen.
#: Same order of magnitude as the interpretive question's cap (#1914).
BLIND_SPOT_CAP = 400

STRATEGIST_PROMPT = """You are a strategist. Read the game the document plays,
not the argument it makes: who the players are, what each of them can do, what
each one wants, and which framings are in competition.

Hard rules:
- This is your reading of the document, so it is MODEL KNOWLEDGE: the report
  labels it as such. Do not present it as something the text states.
- The "options" are the competing framings or moves the situation puts in play
  (2 to 6, in the order you judge most salient).
- For each player, give a FULL ranking of the options, best first. Fill every
  option; a partial ranking cannot be scored.
- Keep the reading neutral: the same map for every side. No verdict on who is
  right, no moral ranking. Say where a player gains from a framing, not whether
  the framing is good.
- "blind_spot" answers ONE question (#3432 ask 2): what does the thesis named
  in the excerpt LEAVE OUT, strategically — which player, option or cost its
  framing makes invisible? It is model knowledge too, never a quote, and an
  empty string is a valid answer: an invented omission would render as
  knowledge.
- If the document carries no strategic configuration, return an empty players
  list. An invented game is worse than no game.

Answer in French, with ONLY this JSON, no fences, no commentary:
{{"players": [{{"name": "...", "role": "...", "stance": "for|against|ambivalent|uncommitted",
              "interests": "what this player wants"}}],
  "options": ["framing A", "framing B"],
  "preferences": {{"<player name>": ["option best first", "..."]}},
  "blind_spot": "what the thesis leaves out, strategically — empty string if none",
  "reading": "two to four sentences on the configuration and where it is open"}}

Source metadata: speaker={speaker}, venue={venue}, topic={topic}, era={era}.

Enjeux and parties already extracted from the text (read them, do not restate
them as strategy):
{stakes_block}

Document excerpt:
{excerpt}
"""


@dataclass
class StrategicRead:
    """The strategist's read, plus what the engine computed from it."""

    players: List[Dict[str, Any]] = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    preferences: Dict[str, List[str]] = field(default_factory=dict)
    blind_spot: str = ""
    reading: str = ""
    game: Dict[str, Any] = field(default_factory=dict)
    status: str = "no_llm"
    error: str = ""

    def to_state(self) -> Dict[str, Any]:
        return {
            "players": stamp_basis(self.players),
            "options": list(self.options),
            "preferences": {k: list(v) for k, v in self.preferences.items()},
            "blind_spot": self.blind_spot,
            "reading": self.reading,
            # ``game`` is OURS, not the model's: it carries its own provenance
            # so a reader can tell a computed verdict from a stated one.
            "game": dict(self.game),
            "status": self.status,
            "basis": MODEL_KNOWLEDGE_BASIS,
        }


def _match_key(name: str) -> str:
    """The normalised key an entry must SHARE with an option to match it.

    Casefolded, whitespace-collapsed, with quotes and punctuation stripped at
    the ends — so ``cadre c``, ``"Cadre C"`` and ``Cadre  C`` are the same
    ballot entry as ``Cadre C``. The match on this key is EXACT, never
    approximate: a near-match would be a guess dressed as a read (#3385).
    """
    collapsed = " ".join(str(name or "").casefold().split())
    return collapsed.strip(" \t\"'«»“”‘’`’.,;:!?()[]{}…-–—")


def _normalise_ballot(
    ranking: List[str], options: List[str]
) -> Tuple[List[str], List[str], List[str]]:
    """Match a player's ranking to the options, and report what did not match.

    Returns ``(matched, unmatched, completed)``: the entries that matched an
    option (the player's own order, deduplicated), the entries that matched
    nothing (recorded — an unreadable entry is a fact about the read), and the
    options the player left out. The caller completes the ballot by appending
    ``completed`` in declaration order — a completion that IS a preference
    (the first-declared option), which is why it is recorded in ``game`` and
    said next to the winner, never presented as the player's own ranking
    (#3385: appending silently flipped a computed Condorcet winner while
    ``status`` stayed ``ok``).
    """
    key_to_option = {_match_key(option): option for option in options}
    matched: List[str] = []
    unmatched: List[str] = []
    for entry in ranking or []:
        option = key_to_option.get(_match_key(entry))
        if option is None:
            unmatched.append(str(entry))
        elif option not in matched:
            matched.append(option)
    completed = [option for option in options if option not in matched]
    return matched, unmatched, completed


def _reports_first(ballot: List[str], target: str) -> List[str]:
    """A ballot that reports ``target`` first, keeping the rest in order."""
    return [target] + [name for name in ballot if name != target]


def compute_manipulability(
    preferences: Dict[str, List[str]], options: List[str]
) -> Dict[str, Any]:
    """Compute the outcome and where it can be moved by misreporting.

    Three questions, the three the 2.1.6 prototype asks, answered by
    enumeration instead of by random mutation:

    1. **Outcome** — the Condorcet winner of the declared profile (``None`` when
       the profile cycles; that is a result, not a failure).
    2. **Single-player pivot** — can one player change the outcome by reporting
       some other option first? This is the "strategic voting" scenario.
    3. **Two-player coalition** — can a pair do it jointly? This is the "false
       coalition" scenario.

    Bribery is deliberately absent: it needs a budget the profile cannot supply,
    and inventing one would be the fabrication this issue forbids.

    Pure and deterministic — same profile, same dict. Bounded by
    ``MAX_PLAYERS``; the output states when the bound bit.

    Ballots are matched to the options on a normalised key (#3385), and what
    the matching did is part of the record, never silent: a player none of
    whose entries match is EXCLUDED from the profile (completing them would
    score a ballot the player never gave), a player who matched some entries
    gets the missing options appended in declaration order — recorded in
    ``completed`` and stated by ``status`` — and every unreadable entry is
    kept in ``unmatched``.
    """
    declared = [name for name, ranking in (preferences or {}).items() if ranking]
    capped_players = declared[:MAX_PLAYERS]
    options = [name for name in (options or [])][:MAX_OPTIONS]

    players: List[str] = []
    ballots: List[List[str]] = []
    excluded_players: List[Dict[str, Any]] = []
    unmatched_by_player: Dict[str, List[str]] = {}
    completed_by_player: Dict[str, List[str]] = {}
    for name in capped_players:
        matched, unmatched, completed = _normalise_ballot(preferences[name], options)
        if not matched:
            # Nothing this player wrote names an option: there is no ballot to
            # score, and inventing one from the declaration order is exactly
            # the fabrication #3385 closes. The player leaves the profile and
            # the record says so.
            excluded_players.append({"player": name, "entries": unmatched})
            continue
        players.append(name)
        ballots.append(matched + completed)
        if unmatched:
            unmatched_by_player[name] = unmatched
        if completed:
            completed_by_player[name] = completed

    result: Dict[str, Any] = {
        "players": players,
        "options": options,
        "capped": len(declared) > len(capped_players)
        or len(options or []) > len(options),
        "excluded_players": excluded_players,
        "unmatched": unmatched_by_player,
        "completed": completed_by_player,
        "winner": None,
        "single_player": [],
        "coalitions": [],
        "status": "ok",
        "engine": "governance.social_choice.condorcet_winner",
    }

    if len(players) < 2 or len(options) < 2:
        result["status"] = "insufficient_profile"
        return result

    if completed_by_player:
        # At least one scored ballot carries options the player never ranked:
        # the winner is computed on a completed profile, and the status says
        # so — the writer must not present it as a clean computation.
        result["status"] = "ok_completed"

    baseline = condorcet_winner(ballots, options)
    result["winner"] = baseline
    if baseline is None:
        result["status"] = "no_condorcet_winner"
        return result

    for index, player in enumerate(players):
        for target in options:
            if target == baseline:
                continue
            trial = list(ballots)
            trial[index] = _reports_first(ballots[index], target)
            winner = condorcet_winner(trial, options)
            if winner is not None and winner != baseline:
                result["single_player"].append(
                    {"player": player, "reports": target, "winner": winner}
                )

    for first in range(len(players)):
        for second in range(first + 1, len(players)):
            for target in options:
                if target == baseline:
                    continue
                trial = list(ballots)
                trial[first] = _reports_first(ballots[first], target)
                trial[second] = _reports_first(ballots[second], target)
                winner = condorcet_winner(trial, options)
                if winner is not None and winner != baseline:
                    # One witness per pair: the claim is "this pair can move the
                    # outcome", not "here are all the ways it can".
                    result["coalitions"].append(
                        {
                            "players": [players[first], players[second]],
                            "report": target,
                            "winner": winner,
                        }
                    )
                    break
    return result


def _stakes_block(state: Any) -> str:
    stakes = getattr(state, "stakes_and_stakeholders", {}) or {}
    lines = []
    for stake in (stakes.get("stakes") or [])[:4]:
        if isinstance(stake, dict) and stake.get("description"):
            lines.append(f"- enjeu : {stake['description']}")
    for holder in (stakes.get("stakeholders") or [])[:6]:
        if isinstance(holder, dict) and holder.get("name"):
            lines.append(
                f"- partie : {holder['name']} ({holder.get('role', '?')}, "
                f"{holder.get('stance', '?')})"
            )
    return "\n".join(lines) if lines else "  (aucun enjeu ni partie extraits)"


def build_strategist_prompt(state: Any, excerpt: str) -> str:
    metadata = getattr(state, "source_metadata", {}) or {}
    return STRATEGIST_PROMPT.format(
        speaker=metadata.get("speaker", "unknown"),
        venue=metadata.get("venue", "unknown"),
        topic=metadata.get("topic", "unknown"),
        era=metadata.get("era", metadata.get("date_or_year", "unknown")),
        stakes_block=_stakes_block(state),
        excerpt=excerpt,
    )


async def build_strategic_read(
    state: Any,
    llm_callable: Optional[Callable[[str], Awaitable[str]]] = None,
) -> StrategicRead:
    """Build ``state.strategic_read`` — the configuration, and what it computes.

    The LLM states the configuration (players, options, ranking); the engine
    computes the outcome and the manipulability. A model failure leaves the
    computation empty rather than inventing a profile to compute on — the
    discriminated ``status`` carries the reason to the invoke layer.

    The excerpt is the first reading's anchors (#2850 lot 10): thesis,
    mechanism and moves with their positions, then the passages around them,
    within one call's capacity — the strategic read of a long document no
    longer sees only its opening. Without a usable position the opening
    window survives, recorded as a fallback.
    """
    raw_text = getattr(state, "raw_text", "") or ""
    recorder = state if hasattr(state, "record_reading_window") else None
    excerpt, selection, extra = persona_reading(raw_text, defining_moves(state))
    if recorder is not None:
        recorder.record_reading_window("strategist", selection, extra)

    result = StrategicRead()
    if llm_callable is None:
        logger.debug("Strategist: no LLM callable; returning an empty read.")
        return result

    prompt = build_strategist_prompt(state, excerpt)
    try:
        content = await llm_callable(prompt)
        content = (content or "").strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if not content:
            result.status = "llm_error"
            result.error = "empty completion"
            return result

        parsed = json.loads(content)
        result.options = [
            str(option).strip()
            for option in (parsed.get("options") or [])[:MAX_OPTIONS]
            if str(option).strip()
        ]
        result.players = [
            dict(player)
            for player in (parsed.get("players") or [])[:MAX_PLAYERS]
            if isinstance(player, dict) and player.get("name")
        ]
        raw_preferences = parsed.get("preferences") or {}
        result.preferences = {
            str(name): [str(option) for option in ranking]
            for name, ranking in raw_preferences.items()
            if isinstance(ranking, list)
        }
        result.reading = str(parsed.get("reading", "") or "").strip()
        # #3432 ask 2 — the thesis's strategic blind spot, model knowledge.
        # Capped and stripped: it rides the Act III prompt, and an empty
        # string is the honest "none named".
        result.blind_spot = str(parsed.get("blind_spot", "") or "").strip()[
            :BLIND_SPOT_CAP
        ]
        result.game = compute_manipulability(result.preferences, result.options)
        result.status = "ok"
        logger.info(
            "Strategist: %d player(s), %d option(s), winner=%s, "
            "%d single pivot(s), %d coalition(s)",
            len(result.players),
            len(result.options),
            result.game.get("winner"),
            len(result.game.get("single_player") or []),
            len(result.game.get("coalitions") or []),
        )
    except json.JSONDecodeError as e:
        result.status = "parse_error"
        result.error = f"{type(e).__name__}: {e}"
        logger.warning("Strategist parse error: %s", e)
    except Exception as e:  # pragma: no cover - provider failures
        result.status = "llm_error"
        result.error = f"{type(e).__name__}: {e}"
        logger.warning("Strategist LLM error: %s", e)
    return result


async def extract_strategic_read(**kwargs: Any) -> Dict[str, Any]:
    """State-shaped wrapper: the dict the invoke returns and the writer persists."""
    return (await build_strategic_read(**kwargs)).to_state()
