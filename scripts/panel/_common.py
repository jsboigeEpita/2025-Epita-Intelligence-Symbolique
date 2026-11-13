"""Shared seams of the panel-cycle instruments (Epic #3374).

Every instrument of ``scripts/panel/`` reads the same recorded artifacts of a
panel cycle — the pipeline's full state dumps and the judge's rows — and asks
where a passage the judge names stands in that state. This module holds what
they share, so two instruments cannot answer the same question two ways:

- the lenient quote locator (a judge quotes from memory of a blind text);
- the population and the selection of the per-argument pass, replayed through
  the production seams, with the **fidelity control** that makes a replay a
  measure: the replayed selection must equal the one the state recorded;
- the two random controls an overlap count is read against;
- the refusal to write an artifact that carries corpus text to a tracked path.

Privacy: nothing here names a document. Panels, states and judge rows are
passed **by path**; an instrument prints counts and the ids it was given.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RESULTS_ROOT = REPO_ROOT / "argumentation_analysis" / "evaluation" / "results"
ACTS = ("act1_framing", "act2_narrative", "act3_conclusion")
DEFAULT_SEED = 3375

Span = Tuple[int, int]

# How a document's population was resolved (``DocIndex.population_kind``).
POPULATION_PRODUCTION = "production"
POPULATION_MERGED_ONLY = "merged_only"
POPULATION_UNFAITHFUL = "unfaithful"
POPULATION_NO_RECORD = "no_record"


class OutputRefused(RuntimeError):
    """The instrument would write corpus text where git could track it."""


def ensure_gitignored(path: Path, repo_root: Path = REPO_ROOT) -> None:
    """Refuse an output path git would track (privacy rule 3, #2353 rule 1).

    A path outside the repository cannot be tracked by it and is accepted.
    """
    try:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return
    probe = subprocess.run(
        ["git", "check-ignore", "-q", rel], cwd=repo_root, capture_output=True
    )
    if probe.returncode != 0:
        raise OutputRefused(
            f"output path is not gitignored ({rel}): it would carry corpus "
            "text — write under argumentation_analysis/evaluation/results/"
        )


def read_panel(panel_file: Optional[Path]) -> Optional[List[str]]:
    """The panel's ids through the campaign's ONE parser, or ``None``."""
    if panel_file is None:
        return None
    from scripts.dataset.run_corpus_batch import parse_doc_ids

    return parse_doc_ids(None, str(panel_file))


# ---------------------------------------------------------------------------
# Locating a quote
# ---------------------------------------------------------------------------


def normalized(text: str) -> Tuple[str, List[int]]:
    """Lowercase alphanumeric stream, single spaces, and for each character of
    the stream the index it came from in ``text``."""
    out: List[str] = []
    idx: List[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        if ch.isalnum():
            out.append(ch.lower())
            idx.append(i)
            prev_space = False
        elif not prev_space:
            out.append(" ")
            idx.append(i)
            prev_space = True
    return "".join(out), idx


def locate(norm: str, idx: Sequence[int], quote: Optional[str]) -> Optional[Span]:
    """The raw-text span of ``quote`` in a normalised document, or ``None``.

    A judge sometimes trims a quote at either end: when the whole quote is not
    found and it has eight words or more, its middle 60 % is tried.
    """
    q = normalized(quote or "")[0].strip()
    if not q:
        return None
    pos = norm.find(q)
    if pos < 0:
        words = q.split()
        if len(words) >= 8:
            cut = max(2, len(words) // 5)
            middle = " ".join(words[cut:-cut])
            pos = norm.find(middle)
            if pos >= 0:
                q = middle
    if pos < 0:
        return None
    return idx[pos], idx[min(len(idx) - 1, pos + len(q) - 1)] + 1


def word_runs(text: Optional[str], n: int = 6) -> Set[str]:
    """Every run of ``n`` consecutive normalised words of ``text``."""
    words = normalized(text or "")[0].split()
    return {" ".join(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}


def overlaps(a: Span, b: Span) -> bool:
    return a[0] < b[1] and b[0] < a[1]


# ---------------------------------------------------------------------------
# Recorded artifacts
# ---------------------------------------------------------------------------


def state_path(states_dir: Path, doc: str) -> Path:
    return Path(states_dir) / f"state_full_{doc}.json"


def load_state(states_dir: Path, doc: str) -> Dict[str, Any]:
    data = json.loads(state_path(states_dir, doc).read_text(encoding="utf-8"))
    inner = data.get("state")
    return inner if isinstance(inner, dict) else data


def docs_in(states_dir: Path) -> List[str]:
    """The ids of the states a directory holds, sorted."""
    prefix = "state_full_"
    return sorted(
        p.stem[len(prefix) :] for p in Path(states_dir).glob(f"{prefix}*.json")
    )


def iter_judge_items(
    dirs: Sequence[Path],
    codes: Sequence[str] = ("M1", "M2"),
    buckets: Sequence[str] = ("kept", "minority"),
) -> Iterator[Tuple[str, str, str, Dict[str, Any]]]:
    """``(family, doc, bucket, item)`` over pass or consensus directories.

    ``family`` is the directory's name. A pass row lists its items under
    ``kept``; a consensus row adds ``minority`` (listed, never deciding).
    """
    for directory in dirs:
        directory = Path(directory)
        for path in sorted(directory.glob("*.json")):
            if path.name == "META.json":
                continue
            row = json.loads(path.read_text(encoding="utf-8"))
            for bucket in buckets:
                for item in row.get(bucket) or []:
                    if item.get("code") in codes:
                        yield directory.name, path.stem, bucket, item


def central_passages(dirs: Sequence[Path], doc: str) -> List[str]:
    """The document quotes of the kept M1 items on the central thesis — the
    passages the judge says no line of the analysis carries."""
    quotes: List[str] = []
    for directory in dirs:
        path = Path(directory) / f"{doc}.json"
        if not path.exists():
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        for item in row.get("kept") or []:
            if item.get("code") == "M1" and item.get("on_central_thesis"):
                quote = (item.get("document_quote") or "").strip()
                if quote:
                    quotes.append(quote)
    return quotes


# ---------------------------------------------------------------------------
# The per-argument pass, replayed through the production seams
# ---------------------------------------------------------------------------


def _int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def population_of(ns: Any, anchored: bool = True) -> List[Any]:
    """The population the per-argument pass selects from.

    The steps of ``_extract_arguments_for_parallel`` (invoke_callables): the
    merged units above the 20-character gate, plus the units the first
    reading's anchors supply where the extraction cut none (#3518).
    ``anchored=False`` is the population of a state recorded before #3518.
    A state with no extracted argument has no state population at all:
    production takes that branch only on a non-empty ``identified_arguments``,
    so the anchors supply nothing there either.
    This re-assembles production's steps, so it can drift from them: the
    fidelity control of ``resolve_population`` is what says whether it has.
    """
    from argumentation_analysis.orchestration import selection as sel

    identified = getattr(ns, "identified_arguments", None)
    if not (isinstance(identified, dict) and identified):
        return []
    population = [
        u for u in sel.merged_population_units(ns) if len((u.text or "").strip()) > 20
    ]
    if anchored:
        population = population + sel.anchored_units_for_named_moves(ns, population)
    return population


def budget_of(ns: Any) -> int:
    """The per-argument budget production would give this state."""
    from argumentation_analysis.agents.core.reading import examined_unit_budget
    from argumentation_analysis.core.reading_window import per_argument_unit_budget
    from argumentation_analysis.orchestration import selection as sel

    budget = examined_unit_budget(ns)
    if budget is not None:
        return budget
    return per_argument_unit_budget(sel.state_text_length(ns) or 0)


def select(ns: Any, population: Sequence[Any], k: Optional[int] = None) -> Any:
    """The production selector on ``population`` at budget ``k`` (default:
    production's own budget), with production's priority spans."""
    from argumentation_analysis.orchestration import selection as sel
    from argumentation_analysis.orchestration.invoke_callables import (
        _selection_priority_spans,
    )

    return sel.select_for_budget(
        population,
        budget_of(ns) if k is None else k,
        text_length=sel.state_text_length(ns),
        priority_spans=_selection_priority_spans(ns),
    )


def recorded_selection(
    state: Dict[str, Any],
) -> Optional[Tuple[List[str], Optional[int]]]:
    """What the per-argument pass recorded: the unit ids it selected and the
    size of the population it selected from — or ``None`` when the state
    carries no record. Units a later mechanism added (``added_by``) are not
    the selector's and are left out."""
    record = (state.get("analysis_coverage") or {}).get("fallacy_per_argument")
    if not isinstance(record, dict) or "unit_ids" not in record:
        return None
    added = set((record.get("added_by") or {}).keys())
    size = record.get("N")
    return (
        [u for u in record.get("unit_ids") or [] if u not in added],
        size if _int(size) else None,
    )


def resolve_population(state: Dict[str, Any]) -> Tuple[List[Any], str]:
    """The population that reproduces the recorded selection, and its kind.

    The positive control of every replay: a population is the one the run
    used when it has the recorded size AND selecting from it gives back the
    recorded unit ids. The size decides between two populations that select
    the same units: an anchored unit the budget left out changes no id, yet
    it turns a passage "named, no unit" into "unit, not examined". The
    production population is tried first, then the merged-only one (a state
    recorded before #3518). When neither reproduces the record the kind is
    ``unfaithful`` — the state predates the code, or the replay has drifted —
    and what an instrument reads on that document is flagged, not trusted.
    """
    ns = SimpleNamespace(**state)
    recorded = recorded_selection(state)
    production = population_of(ns, anchored=True)
    if recorded is None:
        return production, POPULATION_NO_RECORD
    wanted, size = sorted(recorded[0]), recorded[1]
    for population, kind in (
        (production, POPULATION_PRODUCTION),
        (population_of(ns, anchored=False), POPULATION_MERGED_ONLY),
    ):
        if size is not None and len(population) != size:
            continue
        if sorted(u.unit_id for u in select(ns, population).selected) == wanted:
            return population, kind
    return production, POPULATION_UNFAITHFUL


def positioned_units(population: Sequence[Any]) -> Tuple[List[Any], List[int]]:
    """The units that claim a position, in document order, and the distinct
    starts the selector's nearest-before rule reads."""
    from argumentation_analysis.orchestration import selection as sel

    units = sorted((u for u in population if _int(u.offset)), key=lambda u: u.offset)
    return units, sel._population_starts([(u, u.offset) for u in units])


def units_overlapping(
    units: Sequence[Any], span: Span, starts: Sequence[int]
) -> List[Any]:
    """The units whose evidence overlaps ``span`` — the selector's own rule."""
    from argumentation_analysis.orchestration import selection as sel

    return [
        u
        for u in units
        if _int(u.offset) and sel._unit_overlaps_spans(u, [span], starts)
    ]


@dataclass
class DocIndex:
    """What one recorded state says, indexed for passage lookups."""

    doc: str
    raw: str
    norm: str
    idx: List[int]
    population_kind: str
    units: List[Any]
    starts: List[int]
    examined: Set[str]
    moves: List[Span]
    targets: Counter
    review: List[Span]
    act_runs: Dict[str, Set[str]]
    k: Optional[int]
    n: Optional[int]

    def locate(self, quote: Optional[str]) -> Optional[Span]:
        return locate(self.norm, self.idx, quote)


def build_doc_index(doc: str, state: Dict[str, Any]) -> DocIndex:
    raw = state.get("raw_text") or ""
    norm, idx = normalized(raw)
    population, kind = resolve_population(state)
    units, starts = positioned_units(population)
    record = (state.get("analysis_coverage") or {}).get("fallacy_per_argument") or {}
    moves = [
        (m["offset"], m["offset"] + len(m["quote"]))
        for m in (state.get("defining_moves") or {}).get("moves") or []
        if _int(m.get("offset")) and m.get("quote")
    ]
    targets = Counter(
        v.get("target_argument_id")
        for v in (state.get("identified_fallacies") or {}).values()
        if isinstance(v, dict)
    )
    review = [
        (r["offset"], r["offset"] + len(r["quote"]))
        for r in (state.get("coverage_review") or {}).get("items") or []
        if _int(r.get("offset")) and r.get("quote")
    ]
    return DocIndex(
        doc=doc,
        raw=raw,
        norm=norm,
        idx=idx,
        population_kind=kind,
        units=units,
        starts=starts,
        examined=set(record.get("unit_ids") or []),
        moves=moves,
        targets=targets,
        review=review,
        act_runs={act: word_runs(state.get(act) or "") for act in ACTS},
        k=record.get("k"),
        n=record.get("N"),
    )


# ---------------------------------------------------------------------------
# Random controls: what an overlap count is read against
# ---------------------------------------------------------------------------


def random_passage_expectation(
    passages: Sequence[Span],
    text_length: int,
    hit: Callable[[Span], bool],
    draws: int,
    rng: random.Random,
) -> float:
    """How many passages a predicate would hit if they lay anywhere.

    Each passage is redrawn at a uniform position with its own length;
    the mean number of hits over ``draws`` is the figure "X of Y passages
    examined" is compared with. Without it the count measures density: a
    selection that covers most of a text examines most passages by chance.
    """
    if not passages or draws <= 0:
        return 0.0
    hits = 0
    for _ in range(draws):
        for start, end in passages:
            length = end - start
            at = rng.randrange(0, max(1, text_length - length))
            hits += bool(hit((at, at + length)))
    return hits / draws


def random_anchor_expectation(
    anchors: Sequence[Span],
    passages: Sequence[Span],
    text_length: int,
    draws: int,
    rng: random.Random,
) -> float:
    """How many passages anchors of the same count and lengths would overlap
    if they lay anywhere — the control of "the reading names X passages"."""
    if not anchors or not passages or draws <= 0:
        return 0.0
    hits = 0
    for _ in range(draws):
        redrawn = []
        for start, end in anchors:
            length = end - start
            at = rng.randrange(0, max(1, text_length - length))
            redrawn.append((at, at + length))
        hits += sum(any(overlaps(a, p) for a in redrawn) for p in passages)
    return hits / draws
