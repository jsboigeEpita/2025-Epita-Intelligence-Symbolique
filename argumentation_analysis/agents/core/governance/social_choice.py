"""
Formal social choice theory methods for collective decision-making.

Implements classical voting procedures from computational social choice:
- Approval voting
- Single Transferable Vote (STV / Instant Runoff)
- Copeland's method (pairwise comparison)
- Kemeny-Young (optimal ranking)
- Schulze method (strongest paths)

These work on preference profiles (list of ranked ballots) and complement
the agent-based methods in governance_methods.py.
"""

import itertools
from collections import Counter
from typing import Dict, List, Optional, Tuple


def approval_voting(
    ballots: List[List[str]],
    options: List[str],
    approval_threshold: int = 2,
) -> Tuple[str, Dict[str, int]]:
    """Approval voting: each voter approves top-k candidates.

    Args:
        ballots: List of ranked preference lists (most preferred first).
        options: All candidate options.
        approval_threshold: Number of top candidates each voter approves.

    Returns:
        (winner, approval_counts)
    """
    counts = {o: 0 for o in options}
    for ballot in ballots:
        for candidate in ballot[:approval_threshold]:
            if candidate in counts:
                counts[candidate] += 1
    winner = max(counts, key=counts.get) if counts else None
    return winner, counts


def stv(
    ballots: List[List[str]],
    options: List[str],
    seats: int = 1,
) -> Tuple[List[str], List[dict]]:
    """Single Transferable Vote (Instant Runoff Voting for seats=1).

    Iteratively eliminates the candidate with fewest first-preference
    votes and transfers those votes to the next preference.

    Args:
        ballots: List of ranked preference lists.
        options: All candidate options.
        seats: Number of seats to fill (1 = IRV).

    Returns:
        (winners, elimination_rounds)
    """
    remaining = set(options)
    active_ballots = [list(b) for b in ballots]
    winners = []
    rounds = []
    quota = len(ballots) // (seats + 1) + 1

    while remaining and len(winners) < seats:
        # Count first preferences among remaining candidates
        first_prefs = Counter()
        for ballot in active_ballots:
            # Find first remaining candidate in ballot
            for candidate in ballot:
                if candidate in remaining:
                    first_prefs[candidate] += 1
                    break

        if not first_prefs:
            break

        round_info = {"counts": dict(first_prefs), "remaining": sorted(remaining)}

        # Check if any candidate meets quota
        elected = [c for c, count in first_prefs.items() if count >= quota]
        if elected:
            for c in elected:
                winners.append(c)
                remaining.discard(c)
            round_info["elected"] = elected
            rounds.append(round_info)
            continue

        # No one meets quota — eliminate the lowest
        if len(remaining) <= seats - len(winners):
            # All remaining candidates win
            winners.extend(sorted(remaining))
            round_info["elected"] = sorted(remaining)
            rounds.append(round_info)
            break

        lowest = min(first_prefs, key=first_prefs.get)
        remaining.discard(lowest)
        round_info["eliminated"] = lowest
        rounds.append(round_info)

    return winners, rounds


def copeland(
    ballots: List[List[str]],
    options: List[str],
) -> Tuple[str, Dict[str, int]]:
    """Copeland's method: pairwise majority wins minus losses.

    Args:
        ballots: List of ranked preference lists.
        options: All candidate options.

    Returns:
        (winner, copeland_scores)
    """
    scores = {o: 0 for o in options}
    for a in options:
        for b in options:
            if a == b:
                continue
            a_wins = 0
            b_wins = 0
            for ballot in ballots:
                a_idx = ballot.index(a) if a in ballot else len(ballot)
                b_idx = ballot.index(b) if b in ballot else len(ballot)
                if a_idx < b_idx:
                    a_wins += 1
                elif b_idx < a_idx:
                    b_wins += 1
            if a_wins > b_wins:
                scores[a] += 1
            elif b_wins > a_wins:
                scores[a] -= 1
    winner = max(scores, key=scores.get) if scores else None
    return winner, scores


def kemeny_young(
    ballots: List[List[str]],
    options: List[str],
) -> Tuple[List[str], int]:
    """Kemeny-Young method: find the ranking minimizing total disagreement.

    Warning: O(n!) complexity — only practical for ≤8 candidates.

    Args:
        ballots: List of ranked preference lists.
        options: All candidate options.

    Returns:
        (optimal_ranking, min_distance)
    """
    if len(options) > 8:
        raise ValueError(
            f"Kemeny-Young is impractical for {len(options)} candidates (max 8)"
        )

    # Build pairwise preference matrix
    pairwise = {}
    for a in options:
        for b in options:
            if a != b:
                count = sum(
                    1 for ballot in ballots
                    if (a in ballot and b in ballot
                        and ballot.index(a) < ballot.index(b))
                )
                pairwise[(a, b)] = count

    best_ranking = None
    best_score = -1

    for perm in itertools.permutations(options):
        score = 0
        for i in range(len(perm)):
            for j in range(i + 1, len(perm)):
                score += pairwise.get((perm[i], perm[j]), 0)
        if score > best_score:
            best_score = score
            best_ranking = list(perm)

    return best_ranking, best_score


def schulze(
    ballots: List[List[str]],
    options: List[str],
) -> Tuple[str, Dict[str, Dict[str, int]]]:
    """Schulze method (Beatpath): strongest path between all pairs.

    Args:
        ballots: List of ranked preference lists.
        options: All candidate options.

    Returns:
        (winner, strongest_paths_matrix)
    """
    n = len(options)
    idx = {o: i for i, o in enumerate(options)}

    # Build pairwise preference counts
    d = [[0] * n for _ in range(n)]
    for ballot in ballots:
        for i, a in enumerate(ballot):
            if a not in idx:
                continue
            for b in ballot[i + 1:]:
                if b not in idx:
                    continue
                d[idx[a]][idx[b]] += 1

    # Floyd-Warshall for strongest paths
    p = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                if d[i][j] > d[j][i]:
                    p[i][j] = d[i][j]

    for k in range(n):
        for i in range(n):
            if i == k:
                continue
            for j in range(n):
                if j == i or j == k:
                    continue
                p[i][j] = max(p[i][j], min(p[i][k], p[k][j]))

    # Winner: candidate who beats all others in strongest paths
    scores = {o: 0 for o in options}
    for i in range(n):
        for j in range(n):
            if i != j and p[i][j] > p[j][i]:
                scores[options[i]] += 1

    winner = max(scores, key=scores.get) if scores else None
    paths = {
        options[i]: {options[j]: p[i][j] for j in range(n) if i != j}
        for i in range(n)
    }
    return winner, paths


# ── Utility functions ────────────────────────────────────────────────


def condorcet_winner(
    ballots: List[List[str]],
    options: List[str],
) -> Optional[str]:
    """Find Condorcet winner if one exists (beats all others pairwise)."""
    for candidate in options:
        beats_all = True
        for other in options:
            if candidate == other:
                continue
            wins = sum(
                1 for b in ballots
                if candidate in b and other in b
                and b.index(candidate) < b.index(other)
            )
            losses = sum(
                1 for b in ballots
                if candidate in b and other in b
                and b.index(other) < b.index(candidate)
            )
            if wins <= losses:
                beats_all = False
                break
        if beats_all:
            return candidate
    return None


def pairwise_matrix(
    ballots: List[List[str]],
    options: List[str],
) -> Dict[str, Dict[str, int]]:
    """Build pairwise preference matrix from ballots."""
    matrix = {a: {b: 0 for b in options if b != a} for a in options}
    for ballot in ballots:
        for i, a in enumerate(ballot):
            if a not in matrix:
                continue
            for b in ballot[i + 1:]:
                if b in matrix.get(a, {}):
                    matrix[a][b] += 1
    return matrix


SOCIAL_CHOICE_METHODS = {
    "approval": approval_voting,
    "stv": stv,
    "copeland": copeland,
    "kemeny_young": kemeny_young,
    "schulze": schulze,
}
