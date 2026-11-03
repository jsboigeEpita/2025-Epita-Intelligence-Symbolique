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
from typing import Any, Awaitable, Callable, Dict, List, Optional

from argumentation_analysis.agents.core.context import (
    MODEL_KNOWLEDGE_BASIS,
    stamp_basis,
)
from argumentation_analysis.agents.core.governance.social_choice import (
    condorcet_winner,
)
from argumentation_analysis.core.reading_window import (
    LLM_EXTRACTION_WINDOW,
    selected_text,
)

logger = logging.getLogger("Strategist")

#: Bounds of the computation, named because they change what the read can say.
#: The pivot test is O(players² × options) Condorcet calls; past these the read
#: would cost more than the phase that consumes it. When a bound bites, the
#: output says so (``capped``) — a silently truncated profile would read as a
#: complete game.
MAX_PLAYERS = 12
MAX_OPTIONS = 8

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
- If the document carries no strategic configuration, return an empty players
  list. An invented game is worse than no game.

Answer in French, with ONLY this JSON, no fences, no commentary:
{{"players": [{{"name": "...", "role": "...", "stance": "for|against|ambivalent|uncommitted",
              "interests": "what this player wants"}}],
  "options": ["framing A", "framing B"],
  "preferences": {{"<player name>": ["option best first", "..."]}},
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
    reading: str = ""
    game: Dict[str, Any] = field(default_factory=dict)
    status: str = "no_llm"
    error: str = ""

    def to_state(self) -> Dict[str, Any]:
        return {
            "players": stamp_basis(self.players),
            "options": list(self.options),
            "preferences": {k: list(v) for k, v in self.preferences.items()},
            "reading": self.reading,
            # ``game`` is OURS, not the model's: it carries its own provenance
            # so a reader can tell a computed verdict from a stated one.
            "game": dict(self.game),
            "status": self.status,
            "basis": MODEL_KNOWLEDGE_BASIS,
        }


def _normalise_ballot(ranking: List[str], options: List[str]) -> List[str]:
    """Complete a player's ranking over ``options``, deterministically.

    ``condorcet_winner`` needs a total order over the declaration: an option the
    player left out cannot be compared, and dropping it silently would make a
    partial ranking look like an indifference. Missing options are appended in
    the declaration order — the least-committal completion, and the same one on
    every run.
    """
    seen: List[str] = []
    for name in ranking or []:
        if name in options and name not in seen:
            seen.append(name)
    for name in options:
        if name not in seen:
            seen.append(name)
    return seen


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
    """
    declared = [name for name, ranking in (preferences or {}).items() if ranking]
    players = declared[:MAX_PLAYERS]
    options = [name for name in (options or [])][:MAX_OPTIONS]

    result: Dict[str, Any] = {
        "players": players,
        "options": options,
        "capped": len(declared) > len(players) or len(options or []) > len(options),
        "winner": None,
        "single_player": [],
        "coalitions": [],
        "status": "ok",
        "engine": "governance.social_choice.condorcet_winner",
    }

    if len(players) < 2 or len(options) < 2:
        result["status"] = "insufficient_profile"
        return result

    ballots = [_normalise_ballot(preferences[name], options) for name in players]
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
    """
    raw_text = getattr(state, "raw_text", "") or ""
    recorder = state if hasattr(state, "record_reading_window") else None
    excerpt = selected_text(raw_text, LLM_EXTRACTION_WINDOW, "strategist", recorder)

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
