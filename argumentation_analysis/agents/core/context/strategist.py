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

#3430 — the read has TWO layers, and the panel measured what merging them costs:
a player's position *as the document states it* is a fact the document can
check, so it must carry its verbatim span (the citation rule, the first
reading's own); everything the reading ADDS — the game, the interests, the
anticipation — stays model knowledge. The wrap-around is that the split cannot
be left to the model: :func:`anchor_player` drops whatever ``basis`` the reply
carried and re-derives it from the document, so a model answering ``"text"``
still cannot launder a deduction into a quotation.
"""

from __future__ import annotations

import itertools
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from argumentation_analysis.agents.core.context import (
    MODEL_KNOWLEDGE_BASIS,
    TEXT_BASIS,
)
from argumentation_analysis.agents.core.governance.social_choice import (
    condorcet_winner,
)
from argumentation_analysis.agents.core.reading import (
    ANCHOR_UNANCHORED,
    ANCHOR_UNRELATED,
    defining_moves,
)

# The one citation rule (#3389), imported from the module that owns it: the
# reading package exports the producers, not this predicate, and #3430 must not
# depend on a surface another change is editing.
from argumentation_analysis.agents.core.reading.first_reading import quote_occurs_in
from argumentation_analysis.core.metadata_prompt import metadata_prompt_value
from argumentation_analysis.core.reading_window import locate_quote, persona_reading

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
- TWO LAYERS, never merged. What your reading ADDS (the game, the interests, the
  anticipation) is MODEL KNOWLEDGE and the report labels it as such. A player's
  position that the DOCUMENT ITSELF states is the text's, and only when you copy
  its verbatim span into "quote". Copy character for character: no translation,
  no paraphrase, no ellipsis, no two passages joined. The pipeline re-checks
  every quote against the document — a quote it does not find is dropped and the
  position is marked unanchored, so an invented quote buys you nothing.
- Omit "quote" whenever the position is yours rather than the document's: a
  player you infer from the situation, a stance you would call normal for that
  role, anything the text does not assert. Omitting it is the honest answer.
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
              "interests": "what this player wants",
              "quote": "the document's own words for this stance (omit when the text does not state it)"}}],
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


def _name_in_text(name: str, raw_text: str) -> Optional[int]:
    """Where ``raw_text`` carries ``name`` as a whole word, if it does.

    Letter boundaries (``(?<!\\w)`` / ``(?!\\w)``), case-insensitive — the
    #2012 lesson, applied to names: a word boundary would let ``Nom`` hide
    inside ``nom_only``, and a plain substring match would hit ``PARTI``
    inside ``PARTICIPATION``. Returns the offset of the first occurrence in
    ``raw_text``, or ``None`` when the name is absent (or empty).
    """
    cleaned = str(name or "").strip()
    if not cleaned or not raw_text:
        return None
    pattern = re.compile(r"(?<!\w)" + re.escape(cleaned) + r"(?!\w)", re.IGNORECASE)
    match = pattern.search(raw_text)
    return match.start() if match else None


#: The punctuation that closes a sentence for the concern check. Kept to the
#: unambiguous set — a mis-split sentence only widens or narrows the window
#: the name is searched in, and both directions are declared misses (#3556).
_SENTENCE_ENDS = ".!?\n"

#: Function words that ride party names but match nothing distinctive. A
#: distinctive word is what is LEFT once these and the sub-4-letter tokens
#: are gone: ``l'association`` → ``association``, ``Judge Douglas`` →
#: ``judge``, ``douglas``. The generous direction of the concern check (#3556).
_NAME_STOP_WORDS = frozenset(
    (
        "the",
        "with",
        "that",
        "from",
        "pour",
        "avec",
        "dans",
        "les",
        "des",
        "une",
        "par",
        "aux",
        "chez",
        "sous",
        "entre",
        "vers",
        "dont",
        "party",
        "parti",
    )
)


def _distinctive_words(value: str) -> List[str]:
    """The tokens of ``value`` that can carry a player's identity."""
    words: List[str] = []
    for token in re.split(r"[^\w']+", str(value or "")):
        cleaned = token.strip("'").casefold()
        if len(cleaned) >= 4 and cleaned not in _NAME_STOP_WORDS:
            words.append(cleaned)
    return words


def _sentence_span(raw_text: str, start: int, end: int) -> Tuple[int, int]:
    """The span of the sentence that carries ``raw_text[start:end]``."""
    lo = max(raw_text.rfind(ch, 0, start) for ch in _SENTENCE_ENDS) + 1
    ends = [raw_text.find(ch, end) for ch in _SENTENCE_ENDS]
    found = [e for e in ends if e >= 0]
    hi = min(found) + 1 if found else len(raw_text)
    return lo, hi


def _passage_concerns(
    player: Dict[str, Any],
    peers: List[Dict[str, Any]],
    raw_text: str,
    quote: str,
    index: int,
) -> bool:
    """#3556 — does the passage at ``index`` concern this player?

    What the reply can establish, with no named-entity pass: the sentence
    that carries the quote, read against the players' own ``name``/``role``
    vocabulary as the reply gives it. The rule is asymmetric on purpose —
    refusing a real anchor costs a verified citation, the feature #3430
    built, so the player is given every word of their own name:

    * the sentence carries this player's whole name or role, or any
      DISTINCTIVE word of them (≥ 4 letters, not a function word — the
      recorded panels anchor ``Judge Douglas``'s stance on sentences that
      say ``Douglas``, and a full-string rule would refuse them) → concerns;
    * a player whose name or role the DOCUMENT never carries keeps every
      located anchor: that is #3430's population — the speaker and the
      parties the excerpt names nowhere — and the reply's vocabulary cannot
      disprove what the document never names → concerns;
    * else the sentence carries ANOTHER player's WHOLE name or role → the
      document does name this player, but not in this passage, and this
      passage names a different player of the same read (the measured
      defect: a quote the document does carry, offered for the player it
      does not name in it) → does not concern;
    * else → concerns: unproven is not disproven.

    The declared misses run both ways: a passage addressed to another party
    through pronouns alone (the cycle-7 doc_E shape — the player named
      seven times in the document, never inside the passage) stays
    anchored, and speech attribution itself is beyond a vocabulary rule.
    The pull request measures each side on the recorded states.
    """
    if index < 0:
        return False
    lo, hi = _sentence_span(raw_text, index, index + len(quote))
    sentence = raw_text[lo:hi]
    for key in ("name", "role"):
        if _name_in_text(str(player.get(key) or ""), sentence) is not None:
            return True
    for key in ("name", "role"):
        for word in _distinctive_words(str(player.get(key) or "")):
            if _name_in_text(word, sentence) is not None:
                return True
    named_in_document = any(
        _name_in_text(str(player.get(key) or ""), raw_text) is not None
        for key in ("name", "role")
    )
    if not named_in_document:
        return True
    for peer in peers or []:
        for key in ("name", "role"):
            peer_value = str(peer.get(key) or "").strip()
            if peer_value and _name_in_text(peer_value, sentence) is not None:
                return False
    return True


def anchor_player(
    player: Dict[str, Any],
    raw_text: str,
    peers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """#3430, #3556 — a player's stance, anchored on the document or labelled as ours.

    A position the text states comes with a verbatim ``quote``. The producer
    re-runs the one citation rule (#3389) on that quote against the document it
    already holds, so the basis is COMPUTED from the text, never asserted by
    the model: whatever ``basis`` the reply carried is dropped before the check.

    ``peers`` are the OTHER players as the reply gave them — the concern check
    reads the same reply's vocabulary, so a passage can be recognised as
    another party's of the SAME read (the measured defect). Without peers the
    check cannot prove a passage concerns anyone else, and #3430's anchor
    stands: unproven is not disproven.

    Five outcomes, the first reading's shape (#3415, #3427):

    * the quote is in the document and the passage concerns the player →
      ``basis="text"``, the quote and its offset kept; the render may quote
      the position as the document's;
    * the quote is in the document but its passage is another player's
      (#3556 — the sentence that carries the quote names a peer, and not
      this player) → the quote and offset are KEPT as the record of what
      was offered, ``anchor="unrelated"``, ``basis`` back to model
      knowledge; the render never quotes the passage as this player's
      position;
    * the quote is absent from the document → the position is KEPT (it may
      still be true, and dropping it would be the pendulum), the quote is
      emptied, ``anchor="unanchored"``; the render never puts the model's
      words between « »;
    * no quote at all → ordinary model knowledge: no ``quote`` key, no
      ``anchor`` key, so a player that carried neither stays byte-identical
      to a pre-#3430 one;
    * no quote, but the document names the player (#3556 — the model's
      omission must not decide what the text says) → same model-knowledge
      basis, plus ``named_offset``, the offset where the text carries the
      name: the player is not "known only from outside the text", though
      the unquoted stance itself stays a reading.

    The model's own keys are never trusted: ``basis``, ``anchor`` and
    ``named_offset`` are removed from the incoming dict and only the
    producer writes them back.
    """
    item = {key: value for key, value in (player or {}).items() if key != "basis"}
    item.pop("anchor", None)
    item.pop("named_offset", None)
    quote = str(item.pop("quote", "") or "").strip()
    if not quote:
        item["basis"] = MODEL_KNOWLEDGE_BASIS
        named = _name_in_text(str(item.get("name") or ""), raw_text or "")
        if named is not None:
            item["named_offset"] = named
        return item
    if raw_text and quote_occurs_in(raw_text, quote):
        index = locate_quote(raw_text, quote)
        item["quote"] = quote
        item["offset"] = index if index >= 0 else None
        if _passage_concerns(item, peers or [], raw_text, quote, index):
            item["basis"] = TEXT_BASIS
        else:
            item["anchor"] = ANCHOR_UNRELATED
            item["basis"] = MODEL_KNOWLEDGE_BASIS
        return item
    item["anchor"] = ANCHOR_UNANCHORED
    item["basis"] = MODEL_KNOWLEDGE_BASIS
    return item


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

    def _labelled_players(self) -> List[Dict[str, Any]]:
        """The players, each with the basis the PRODUCER decided (#3430).

        ``stamp_basis`` is unconditional by design and would erase an anchored
        stance, so the strategist writes this field itself — but from the
        producer's decision, never the reply: ``anchor_player`` already dropped
        whatever ``basis`` the model sent. Re-asserted here so a caller that
        built ``StrategicRead`` by hand cannot smuggle one either: ``text``
        survives only with a non-empty quote AND an offset that locates it.
        """
        labelled: List[Dict[str, Any]] = []
        for player in self.players:
            item = dict(player)
            anchored = (
                item.get("basis") == TEXT_BASIS
                and bool(str(item.get("quote") or "").strip())
                and isinstance(item.get("offset"), int)
                and not isinstance(item.get("offset"), bool)
                # #3556 — a passage marked unrelated to this player can never
                # render as this player's text basis, hand-built or not.
                and item.get("anchor") != ANCHOR_UNRELATED
            )
            item["basis"] = TEXT_BASIS if anchored else MODEL_KNOWLEDGE_BASIS
            labelled.append(item)
        return labelled

    def to_state(self) -> Dict[str, Any]:
        return {
            "players": self._labelled_players(),
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


def _strictly_prefers(ballot: List[str], new_winner: str, baseline: str) -> bool:
    """``ballot`` ranks ``new_winner`` strictly above ``baseline``.

    #3524 — the interest check reads the same scored ballot the enumeration
    uses (matched entries followed by the completed ones, so both options are
    present). A completed option ranks after every declared one, so a
    preference the player never stated can only make the check stricter,
    never looser.
    """
    try:
        return ballot.index(new_winner) < ballot.index(baseline)
    except ValueError:  # absent from the scored ballot: no declared preference
        return False


#: #3530 — the Borda block's two bounds, named because they decide what the
#: block can claim. A Borda misreport is ANY complete ballot, so the
#: single-player space is ``m!`` per player and a pair's is ``(m!)²``. The
#: enumeration is exhaustive while ``m! <= BORDA_PERMUTATION_CAP`` (six options)
#: and while the profiles scored stay under ``BORDA_TRIAL_CAP``; a bound that
#: bites is written on the block (``exhaustive: False``), never silent — a cut
#: enumeration says nothing about the moves it never scored.
BORDA_PERMUTATION_CAP = 720
BORDA_TRIAL_CAP = 50_000


def _borda_contribution(ballot: List[str], options: List[str]) -> Dict[str, int]:
    """What one ballot adds to each option's Borda score (n-1 for top, …)."""
    width = len(options)
    return {
        name: width - index - 1 for index, name in enumerate(ballot) if name in options
    }


def _borda_scores(ballots: List[List[str]], options: List[str]) -> Dict[str, int]:
    scores = {name: 0 for name in options}
    for ballot in ballots:
        for name, value in _borda_contribution(ballot, options).items():
            scores[name] += value
    return scores


def _unique_top(scores: Dict[str, int]) -> Optional[str]:
    """The single highest-scoring option, or ``None`` on a tie at the top."""
    if not scores:
        return None
    top = max(scores.values())
    winners = [name for name, value in scores.items() if value == top]
    return winners[0] if len(winners) == 1 else None


def borda_winner(ballots: List[List[str]], options: List[str]) -> Optional[str]:
    """The honest Borda winner: unique, or ``None`` on a tie at the top.

    #3530 — a tie at the top is "no winner", never an invented tie-break: the
    classic Borda rule names a single winner, and picking the first of several
    tied options would be a choice the profile does not make.

    The agent-based ``governance_methods.borda_count`` stays the adapter the
    plugin dispatches; this is the ballot-list form the strategist's engine
    needs, with the tie made explicit rather than folded into ``max``.
    """
    return _unique_top(_borda_scores(ballots, options))


def _borda_block(
    players: List[str], ballots: List[List[str]], options: List[str]
) -> Dict[str, Any]:
    """#3530 — where the outcome can move if it were settled on points (Borda).

    The Condorcet block above answers the same question for a pairwise
    outcome, and #3524 measured it structurally empty on every profile that has
    a Condorcet winner. The coordinator's decision of 13/11 (option b,
    restricted to Borda) is to keep the Condorcet winner as the outcome and add
    this second rule on top, because Borda is single-voter manipulable where
    Condorcet is not (measured: 6 of 18 recorded profiles carry a witness,
    against 0 of 12 for Condorcet).

    A witness is a misreport that leaves its mover strictly better off — the
    same interest check as the Condorcet block, read on the mover's own honest
    ballot. The enumeration covers EVERY complete ballot (``m!`` per player),
    not only "some option first": a Borda manipulation often works by burying a
    rival, which no promote-first enumeration reaches. A pair is formed only
    when NEITHER member can move the outcome alone — an individual witness is
    the stronger, simpler finding, and a pair behind it adds nothing.

    One witness per ``(player, winner)`` is kept, in permutation order: the
    claim is "this player can install this winner beneficially", not "here are
    all the ballots that do it". Every ballot that moved the winner and failed
    the interest check is counted (``moved_not_kept``; a pair is counted once,
    like the Condorcet block), never silent.
    """
    permutations = [list(perm) for perm in itertools.permutations(options)]
    per_player = len(permutations)
    block: Dict[str, Any] = {
        "winner": None,
        "status": "no_borda_winner",
        "single_player": [],
        "coalitions": [],
        "ballots_examined": 0,
        "moved_not_kept": 0,
        "pairs_examined": 0,
        "pairs_moved_not_kept": 0,
        "permutations_per_player": per_player,
        "exhaustive": True,
        "bound": {
            "permutations_per_player": BORDA_PERMUTATION_CAP,
            "ballots": BORDA_TRIAL_CAP,
        },
        "engine": "governance.social_choice.borda_winner",
    }
    base = _borda_scores(ballots, options)
    baseline = _unique_top(base)
    block["winner"] = baseline
    if baseline is None:
        return block
    needed = per_player * len(players)
    if per_player > BORDA_PERMUTATION_CAP or needed > BORDA_TRIAL_CAP:
        # The bound bites BEFORE any ballot is scored: a partial single-player
        # enumeration would be an arbitrary slice of the space, and the block
        # must not let a reader read "no witness found" as "none exists".
        block["status"] = "capped"
        block["exhaustive"] = False
        block["ballots_required"] = needed
        block["cut"] = "entry"
        return block

    block["status"] = "ok"
    old = [_borda_contribution(ballot, options) for ballot in ballots]
    contributions = [
        _borda_contribution(permutation, options) for permutation in permutations
    ]

    def trial(
        first: int,
        first_contribution: Dict[str, int],
        second: int = -1,
        second_contribution: Optional[Dict[str, int]] = None,
    ) -> Optional[str]:
        scores = dict(base)
        for name, value in old[first].items():
            scores[name] -= value
        for name, value in first_contribution.items():
            scores[name] += value
        if second >= 0 and second_contribution is not None:
            for name, value in old[second].items():
                scores[name] -= value
            for name, value in second_contribution.items():
                scores[name] += value
        return _unique_top(scores)

    examined = 0
    single_players = set()
    for index, player in enumerate(players):
        kept_winners = set()
        for permutation, contribution in zip(permutations, contributions):
            examined += 1
            winner = trial(index, contribution)
            if winner is None or winner == baseline:
                continue
            if _strictly_prefers(ballots[index], winner, baseline):
                if winner not in kept_winners:
                    kept_winners.add(winner)
                    block["single_player"].append(
                        {
                            "player": player,
                            "ballot": list(permutation),
                            "winner": winner,
                        }
                    )
            else:
                block["moved_not_kept"] += 1
        if kept_winners:
            single_players.add(player)
    block["ballots_examined"] = examined

    # Pairs: only where NEITHER member can move the outcome alone (the pair is
    # then the weakest useful finding), and only while the trial budget lasts.
    pairs_examined = 0
    budget = BORDA_TRIAL_CAP - examined
    for first in range(len(players)):
        if players[first] in single_players:
            continue
        for second in range(first + 1, len(players)):
            if players[second] in single_players:
                continue
            moved = False
            found = None
            cut = False
            for first_permutation, first_contribution in zip(
                permutations, contributions
            ):
                for second_permutation, second_contribution in zip(
                    permutations, contributions
                ):
                    if pairs_examined >= budget:
                        cut = True
                        break
                    pairs_examined += 1
                    winner = trial(
                        first, first_contribution, second, second_contribution
                    )
                    if winner is None or winner == baseline:
                        continue
                    moved = True
                    if _strictly_prefers(
                        ballots[first], winner, baseline
                    ) and _strictly_prefers(ballots[second], winner, baseline):
                        found = {
                            "players": [players[first], players[second]],
                            "ballots": [
                                list(first_permutation),
                                list(second_permutation),
                            ],
                            "winner": winner,
                        }
                        break
                if found is not None or cut:
                    break
            if found is not None:
                block["coalitions"].append(found)
            elif moved:
                block["pairs_moved_not_kept"] += 1
            if cut:
                # #3563 review (fix 1) — the pair search can stop on its trial
                # budget without the ENTRY cap biting (six options: 720 × 720
                # pair trials against a 50 000 budget). The single-player pass
                # is complete; only the pairs are cut. Named apart from the
                # entry cap — ``status`` stays ``ok`` because the block DID
                # measure its winner and its single-player space, and the act I
                # render states this cut in its winner branch (the entry cap's
                # ``status == "capped"`` branch would drop those measured
                # lines).
                block["exhaustive"] = False
                block["cut"] = "pair_search"
                block["pairs_budget"] = budget
                break
        if not block["exhaustive"]:
            break
    block["pairs_examined"] = pairs_examined
    return block


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

    #3524 — a witness must be a manipulation its movers have a reason to make.
    The standard definition (Gibbard–Satterthwaite) is a misreport that leaves
    the misreporting player strictly better off: a pivot whose mover ends up
    with a winner they rank BELOW the baseline is not a manipulation, and the
    earlier version recorded those as witnesses (measured: every coalition of
    the c5 and c6 panels had at least one member harmed that way). A single
    pivot is now kept only when the mover's own scored ballot ranks the new
    winner above the baseline; a coalition only when BOTH members do. What the
    interest check removes is counted in ``dropped_against_interest`` — never
    silent.

    The check is load-bearing and, on a profile that HAS a Condorcet winner,
    the kept lists are empty for a structural reason: to install a winner
    ``T`` the movers must make ``T`` beat the baseline pairwise, and a ballot
    contributes more to ``T``-over-baseline than it did honestly only by
    flipping that contest — i.e. only from a player who ranked the baseline
    ABOVE ``T`` (not necessarily first). Every change therefore needs at
    least one mover it harms: a single mover is always harmed, and a pair
    never has two members who gain (one of them may — a pair is kept only
    when BOTH do). So the counter, not the empty list, carries the
    measurement: "N moves exist, each costs at least one of its own movers".
    Measured exhaustively on the complete profiles of 3 options × 3 to 5
    players and 4 options × 3 and 4 players: 133 776 profiles with a winner,
    0 witness kept. The paragraph above the lists must not be read as "no
    manipulation exists at any coalition size" — it is the bound of this
    enumeration (at most two movers, promoting a target first).

    #3530 — the Condorcet block above is structurally empty, so the finding
    that can actually be rendered comes from the second block: ``borda``
    (see :func:`_borda_block`), where a beneficial misreport exists (6 of the
    18 recorded profiles with a Borda winner, against 0 of 12 for Condorcet).
    The Condorcet winner remains the OUTCOME (``winner``); the Borda winner,
    its own witnesses and the enumeration's bound live under ``borda``, and
    the two winners' disagreement is stated where the line is rendered.
    ``dropped_against_interest`` on this dict stays the CONDORCET counter — the
    Borda block counts its own (``moved_not_kept``), because a ballot and a
    promote-first move are not the same unit.

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
        "dropped_against_interest": 0,
        "status": "ok",
        "engine": "governance.social_choice.condorcet_winner",
    }

    if len(players) < 2 or len(options) < 2:
        result["status"] = "insufficient_profile"
        return result

    # #3530 — the Borda block runs on EVERY usable profile, including the ones
    # whose Condorcet contest cycles: the decision of 13/11 keeps the Condorcet
    # winner as the OUTCOME and adds the points rule on top, so a profile with
    # no Condorcet winner can still carry a Borda winner and a Borda witness.
    result["borda"] = _borda_block(players, ballots, options)

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

    dropped = 0

    for index, player in enumerate(players):
        for target in options:
            if target == baseline:
                continue
            trial = list(ballots)
            trial[index] = _reports_first(ballots[index], target)
            winner = condorcet_winner(trial, options)
            if winner is None or winner == baseline:
                continue
            if _strictly_prefers(ballots[index], winner, baseline):
                result["single_player"].append(
                    {"player": player, "reports": target, "winner": winner}
                )
            else:
                dropped += 1

    for first in range(len(players)):
        for second in range(first + 1, len(players)):
            kept = None
            moved = False
            for target in options:
                if target == baseline:
                    continue
                trial = list(ballots)
                trial[first] = _reports_first(ballots[first], target)
                trial[second] = _reports_first(ballots[second], target)
                winner = condorcet_winner(trial, options)
                if winner is None or winner == baseline:
                    continue
                moved = True
                if _strictly_prefers(
                    ballots[first], winner, baseline
                ) and _strictly_prefers(ballots[second], winner, baseline):
                    # One witness per pair: the claim is "this pair can move the
                    # outcome toward a winner BOTH of them prefer", not "here
                    # are all the ways it can".
                    kept = {
                        "players": [players[first], players[second]],
                        "report": target,
                        "winner": winner,
                    }
                    break
            if kept is not None:
                result["coalitions"].append(kept)
            elif moved:
                # The pair can move the outcome, but no target it can install
                # is preferred by both members: counted, never silent.
                dropped += 1

    result["dropped_against_interest"] = dropped
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
    # #3512 — an unrecorded field renders as an instruction, never as the
    # corpus placeholder: the model copies what the prompt shows.
    return STRATEGIST_PROMPT.format(
        speaker=metadata_prompt_value(metadata, "speaker"),
        venue=metadata_prompt_value(metadata, "venue"),
        topic=metadata_prompt_value(metadata, "topic"),
        era=metadata_prompt_value(metadata, "era", "date_or_year"),
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
        # #3556 — the concern check reads the peers the reply itself named,
        # so the passage can be recognised as another party's of this read.
        raw_players = [
            dict(player)
            for player in (parsed.get("players") or [])[:MAX_PLAYERS]
            if isinstance(player, dict) and player.get("name")
        ]
        result.players = [
            anchor_player(player, raw_text, raw_players) for player in raw_players
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
            "%d single pivot(s), %d coalition(s), %d move(s) dropped by the "
            "interest check",
            len(result.players),
            len(result.options),
            result.game.get("winner"),
            len(result.game.get("single_player") or []),
            len(result.game.get("coalitions") or []),
            result.game.get("dropped_against_interest", 0),
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
