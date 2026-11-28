"""Live act replay: re-run the three acts of a harvested cycle, write a tag.

    python scripts/panel/replay_acts.py --cycle-dir \\
        argumentation_analysis/evaluation/results/panel_cycles/<cycle> \\
        --dest argumentation_analysis/evaluation/results/panel_cycles/<tag> \\
        --acts live [--panel-file ... | --doc-ids ...]

#3658 item 46c. ``replay_acts.py`` replays the *recorded* acts and proves the
render round-trips. This module is the other half: it **re-runs** Acts I to III
of a cycle's recorded states — one model call per act and per document, the
only paid step of the replay — and writes a directory ``run_cycle --stage
judges`` accepts as a cycle (``--tag <tag>``).

Four properties, in this order, and the order is the instrument.

1. **Nothing is spent before the inputs are proven.** The preflight
   (:mod:`scripts.panel.act_replay_preflight`) answers first, from the files
   alone; the modules that build a judged text and call a model are imported
   after it. This module is deliberately import-light for the same reason: the
   launcher imports it *before* the preflight runs, so anything heavy here
   would be paid before the answer. Tests read a child's ``sys.modules``.

2. **The destination is a tag, not a directory.** ``--dest`` must be
   ``<results_root>/panel_cycles/<name>`` — a sibling of the cycles, a name
   ``run_cycle`` accepts — and must not exist. Before the first call the tag
   receives a ``pipeline.json`` whose ``rc`` is 1: a run that dies mid-panel
   leaves a cycle the judges stage refuses, rather than one it grades. The
   record is rewritten with ``rc`` 0 only once every pair is on disk.

3. **The seat is checked before it is trusted, and the check is free.**
   :func:`gate` refuses a seat whose settings would change what the acts
   produce — ``ACT_MAX_TOKENS`` / ``PHASE_MAX_TOKENS`` / ``LLM_CALL_TIMEOUT_S``
   / ``ARGUMENTATION_SKIP_PHASES`` set in the shell, a cache mode other than
   ``off`` (a cached answer is not a live act), a process under pytest (a mock
   would answer), a missing ``OPAQUE_ID_SALT`` (the signature's sanitiser
   cannot write without it), a route that resolves no model, and any sampling
   pin the recorded run's environment manifest carries with another value. A
   pin the record does *not* carry is a note, not a refusal: the acts are
   produced today, and the tag says so.

4. **The instrument must give back the record before it may write one.**
   The identity control (:func:`identity_control`) runs the *real* executor,
   the real state writers and the real write-back over each recorded state,
   with the execution order and the real writer as the only code, and the
   recorded act payloads served by an in-process provider. Every byte it
   writes — the state dump and the signature — must equal the record's, byte
   for byte, except that a signature whose *only* differing top-level key is
   ``state`` is named a **sanitiser** difference and not an instrument one:
   the state half proves the two snapshots equal, so the only code left
   between the snapshot and the signature is ``sanitize_state``, i.e. the
   seat's opacifying key is not the harvest's. The control costs nothing and
   refuses the run when it does not hold: an instrument that cannot give back
   the record cannot be trusted to render a measurement, and ``--acts live``
   exits 1 before a tag exists.

What is written, per document:

* a **live** document: the recorded state with the three acts (and what Act I
  carries: the interpretive question, the announced checks, the act's degraded
  map) replaced by the live run's, every other key untouched; ``llm_usage``
  keeps the recorded run's non-act buckets and run-level cost fields and takes
  the live act buckets in place — the replay's own accounting rides
  ``act_replay.usage.live_run``, never summed into the recorded total; the
  signature rebuilt from that state, its sanitised subtree re-derived, with
  the replay's provenance (a fresh ``run_started_utc``, today's ``code_sha``,
  today's route) and an ``act_replay`` block naming what ran;
* a **copied** document: the record's own pair, byte for byte — a document
  whose render never reads the acts (``non_argumentative``), one whose mode
  has no acts by design (``conversation_real``, ``hierarchical_delegation``),
  and a document the batch stopped before. Its timeline stays the record's,
  because there is no act of its own to replay.

A failed act is filed as a **degraded arm**, not as a batch failure: the act's
key stays empty (cleared before the run), ``restitution_acts_degraded`` gains
``act_replay.phase_failed`` and the judge's own #3458 rule refuses the panel at
its own threshold. Only an instrument-level integrity failure stops the batch:
a state key outside the written-back and bookkeeping sets changed, an act
completed with text and no accounted call, or a replay of a document whose
three acts all failed (the merged code does not answer — the rest of the panel
would be spent on the same silence).

Report: ``<tag>/act_replay.json``, a JSON object whose first key is
``provenance`` (#2353) — four instruments by content sha256, the command,
counts, per-document rows, the gate, the control, the self-check. Opaque ids,
lengths, counts and sha256 only: no act text, no state text, no passage.
Exit 0 = a tag the judges stage accepts and every self-check held; 1 = nothing
was spent and a named reason says why, or the tag is a refused measurement;
2 = the invocation could not run as asked (nothing is written).
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import io
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402
from scripts.panel import act_replay_preflight as preflight_module  # noqa: E402
from scripts.panel.act_replay_preflight import (  # noqa: E402
    CYCLE_RECORD,
    PIPELINE_RECORD,
    Problem,
    preflight,
)

REPORT = "act_replay.json"
INSTRUMENT = "scripts/panel/act_replay_live.py"
LIVE = "live"
COPIED = "copied"

EXIT_OK, EXIT_REFUSED, EXIT_USAGE = 0, 1, 2

STAGE_PREFLIGHT = "preflight"
STAGE_TAG = "tag"
STAGE_CYCLE = "cycle"
STAGE_RECORDS = "records"
STAGE_GATE = "gate"
STAGE_CONTROL = "identity_control"
STAGE_LIVE = "live"
STAGE_DONE = "done"

#: Stages that stop before a destination exists: nothing is written, nothing
#: is spent, and the exit code says "the invocation could not run as asked".
UNWRITTEN_STAGES = (STAGE_PREFLIGHT, STAGE_TAG, STAGE_CYCLE, STAGE_RECORDS, STAGE_GATE)

#: The state keys a completed act writes. Their live value replaces the
#: record's in the tag; every other key keeps the record's, in the record's
#: order (measured: the c22 record's 67 keys, ``llm_usage`` last).
WRITTEN_BACK: Tuple[str, ...] = (
    "act1_framing",
    "act2_narrative",
    "act3_conclusion",
    "interpretive_question",
    "announced_checks",
    "restitution_acts_degraded",
)

#: Keys the replay's own machinery moves — the run's bookkeeping, not the
#: document's analysis. The record's value is restored and the key is named.
BOOKKEEPING: Tuple[str, ...] = (
    "phases_left_out",
    "rests_on_armed",
    "deanonymized",
    "workflow_results",
    "errors",
)

#: A setting that changes what an act produces. Each one is refused by name:
#: the merged defaults are the fix (46a+b), and a seat-level override would
#: make the tag measure the override.
REFUSE_IF_SET: Tuple[str, ...] = (
    "ACT_MAX_TOKENS",
    "PHASE_MAX_TOKENS",
    "LLM_CALL_TIMEOUT_S",
    "ARGUMENTATION_SKIP_PHASES",
)

#: The sampling pins the signature's environment manifest records
#: (``env_manifest._probe_overrides``), compared with the recorded run's.
ACTING_PINS: Tuple[str, ...] = (
    "LLM_DETERMINISTIC_MODE",
    "LLM_TEMPERATURE",
    "LLM_SEED",
    "LLM_REASONING_EFFORT",
    "LLM_ANTHROPIC_THINKING",
)

#: The codes a live act's gap is filed under, on the closed vocabulary the
#: act's own ``restitution_acts_degraded`` map carries (no prose matched, and
#: none of them ends with the length-stop suffix: a phase failure is not a
#: cut).
CODE_PHASE_FAILED = "act_replay.phase_failed"
CODE_PHASE_SKIPPED = "act_replay.phase_skipped"

#: What the tag's ``llm_usage`` means, written next to the replay's own
#: accounting: two runs share that map, and a reader must not sum their
#: entries into one total that no run spent.
USAGE_NOTE = (
    "the state's llm_usage keeps the recorded run's non-act buckets and "
    "run-level fields; its three act buckets are this replay's, and live_run "
    "is the replay's own accounting"
)

#: The per-document wall budget, production's own default
#: (``run_corpus_batch`` ``timeout=900``): the acts carry 180 s each and two
#: calls at most, so this only catches a provider that ignores cancellation.
WALL_BUDGET_S = 900.0

#: #3658 item 46g — the most model calls one document can cost: Act I makes
#: one, Acts II and III each make a primary call and one bounded retry (#3343).
#: The bound is printed before the first call, so the spend is announced rather
#: than discovered in the bill; the calls actually made are counted apart.
ACT_CALLS_PER_DOCUMENT = 5


class Refused(Exception):
    """The replay cannot run as asked. Named, never silent."""


# ---------------------------------------------------------------------------
# Small helpers — textual, corpus-free
# ---------------------------------------------------------------------------


def _digest(text: str) -> str:
    """The sha256 of a text — the only thing the report keeps of it."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _opt_int(value: Any) -> Optional[int]:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _opt_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) else None


def _inner(record: Mapping[str, Any]) -> Mapping[str, Any]:
    """The level the producers read (``state.get("state") or state``)."""
    nested = record.get("state")
    return nested if isinstance(nested, dict) else record


def read_record(path: Path) -> Dict[str, Any]:
    """One JSON object, or :class:`Refused` naming the file and the type."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(f"{path.name}: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise Refused(f"{path.name}: {type(data).__name__}, not an object")
    return data


def _encoder() -> Any:
    """The production writer's encoder, read from the producer.

    The tag's bytes must be the bytes the batch writes — a local copy of the
    ``set`` rule would drift silently. Imported here, never at module scope:
    importing the producer pulls the pipeline runtime into the process.
    """
    from scripts.dataset.run_corpus_batch import _SafeEncoder

    return _SafeEncoder


def dumps(obj: Any) -> str:
    """One dump, exactly as ``run_corpus_batch`` writes a state or signature."""
    return json.dumps(obj, ensure_ascii=False, indent=2, cls=_encoder())


def writer_bytes(text: str) -> bytes:
    """The bytes ``Path.write_text(..., encoding="utf-8")`` emits here.

    ``write_text`` opens with ``newline=None``: on this seat every ``"\\n"``
    becomes ``"\\r\\n"`` (measured on the c22 harvest: 214 218 pairs in the ten
    state dumps), so a byte comparison must apply the same convention.
    """
    sink = io.BytesIO()
    wrapper = io.TextIOWrapper(sink, encoding="utf-8", newline=None)
    wrapper.write(text)
    wrapper.flush()
    return sink.getvalue()


def _instruments() -> Dict[str, Optional[str]]:
    """The content sha256 of the four instruments, ``None`` when not loaded."""
    here = Path(__file__).resolve()
    out: Dict[str, Optional[str]] = {
        "act_replay_live": hashlib.sha256(here.read_bytes()).hexdigest()
    }
    for name in ("replay_acts", "act_replay_preflight", "act_replay_fidelity"):
        module = sys.modules.get(f"scripts.panel.{name}")
        path = getattr(module, "__file__", None)
        out[name] = (
            hashlib.sha256(Path(path).read_bytes()).hexdigest() if path else None
        )
    return out


def provenance(
    argv: Sequence[str],
    cycle_dir: Path,
    destination: Path,
    panel: Optional[Sequence[str]],
) -> Dict[str, Any]:
    """The header #2353 requires: which code, which records, which command."""
    return {
        "instrument": "live act replay of a harvested cycle",
        "command": ["python", "scripts/panel/replay_acts.py", *argv],
        "code": {
            "root": str(c.REPO_ROOT),
            "head": current_head(),
            "instruments": _instruments(),
            "executable": sys.executable,
        },
        "route": {
            "cycle_dir": str(Path(cycle_dir).resolve()),
            "destination": str(Path(destination).resolve()),
            "panel_size": None if panel is None else len(panel),
        },
        "python": sys.version.split()[0],
        "units": "characters, counts and sha256 only, never text",
    }


def current_head(repo_root: Path = c.REPO_ROOT) -> Optional[str]:
    """``git rev-parse HEAD``, ``None`` when git is absent or the query fails.

    The recorded path's own tolerance: a seat without git still runs, and the
    record then says ``head: null`` rather than a fabricated sha.
    """
    import subprocess

    try:
        done = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


# ---------------------------------------------------------------------------
# The destination: a tag ``run_cycle`` opens
# ---------------------------------------------------------------------------


def tag_problem(
    destination: Path, results_root: Path = c.RESULTS_ROOT
) -> Optional[str]:
    """Why ``--dest`` is not a tag, or ``None``. Uses the cycle's own validator.

    A live tag is ``run_cycle --tag <name>``'s directory: a sibling of the
    cycles, named by the one regex the cycle applies. The check calls the
    cycle's ``Config`` rather than copying its rule, so a tag the judges stage
    would reject is refused here — before a call, not after the panel.
    """
    parent = (results_root / "panel_cycles").resolve()
    resolved = destination.resolve()
    if resolved.parent != parent:
        return (
            f"--dest {destination}: a live tag is a sibling of the cycles "
            f"(<results_root>/panel_cycles/<name>), and run_cycle opens it by "
            f"--tag {destination.name!r} — a directory elsewhere is never judged"
        )
    from scripts.panel.run_cycle import Config

    try:
        cfg = Config(
            tag=resolved.name,
            panel_file=resolved / "unused-panel.txt",
            zeroshot_dir=resolved / "unused-zeroshot",
            results_root=Path(results_root),
        )
    except ValueError as exc:
        return f"--dest {destination}: run_cycle would refuse the tag ({exc})"
    if cfg.cycle_dir.resolve() != resolved:
        return (
            f"--dest {destination}: run_cycle would open "
            f"{cfg.cycle_dir} for this name, not this path"
        )
    return None


# ---------------------------------------------------------------------------
# The seat: observed by name, gated before a call
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Observed:
    """What this seat is, read by *presence*: no pin value is kept here."""

    salt: bool
    cache_mode: str
    in_pytest: bool
    set_knobs: Tuple[str, ...]
    model: Optional[str]
    route_error: Optional[str]
    pins: Mapping[str, Any]


@dataclass(frozen=True)
class Gate:
    """The pre-spend verdict: refusals stop the run, notes ride the report."""

    refusals: Tuple[str, ...]
    notes: Mapping[str, Any]

    @property
    def ok(self) -> bool:
        return not self.refusals

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "refusals": list(self.refusals),
            "notes": dict(self.notes),
        }


def _pin_value(entry: Any) -> Any:
    """A manifest pin: the raw value, or the ``value`` a verdict dict wraps."""
    if isinstance(entry, dict) and "value" in entry:
        return entry["value"]
    return entry


def observe() -> Observed:
    """Read this seat. Every reading is a name or a presence, never a passage."""
    cache_mode = "off"
    try:
        from argumentation_analysis.services.llm_cache import get_cache_mode

        cache_mode = get_cache_mode()
    except Exception as exc:  # noqa: BLE001 — an invalid mode is a datum
        cache_mode = f"invalid:{type(exc).__name__}"
    model: Optional[str] = None
    route_error: Optional[str] = None
    try:
        from argumentation_analysis.evaluation.run_provenance import chat_model_id

        model = chat_model_id()
    except Exception as exc:  # noqa: BLE001 — named, not guessed
        route_error = type(exc).__name__
    pins: Dict[str, Any] = {}
    try:
        from argumentation_analysis.evaluation.env_manifest import (
            environment_manifest,
        )

        manifest = environment_manifest()
        overrides = (manifest.get("overrides") or {}).get("pinned_overrides") or {}
        pins = {
            name: _pin_value(overrides[name])
            for name in ACTING_PINS
            if name in overrides
        }
    except Exception as exc:  # noqa: BLE001
        route_error = route_error or type(exc).__name__
    return Observed(
        salt=bool((os.environ.get("OPAQUE_ID_SALT") or "").strip()),
        cache_mode=cache_mode,
        in_pytest=bool(os.environ.get("PYTEST_CURRENT_TEST"))
        or "pytest" in sys.modules,
        set_knobs=tuple(
            name for name in REFUSE_IF_SET if os.environ.get(name) is not None
        ),
        model=model,
        route_error=route_error,
        pins=pins,
    )


def recorded_settings(
    signatures: Mapping[str, Mapping[str, Any]],
) -> Tuple[Optional[Mapping[str, Any]], Optional[str], List[str]]:
    """``(environment, chat_model_id, problems)`` — one per panel, or refused.

    The gate compares the seat with the run the acts belong to, so the record
    must say one environment and one model for the whole panel. Two of either
    means the documents did not all run the same code or route, and no single
    comparison would be true: named, not averaged.
    """
    problems: List[str] = []
    environments: Dict[str, Mapping[str, Any]] = {}
    models: Dict[str, Optional[str]] = {}
    for doc, signature in signatures.items():
        prov = signature.get("provenance")
        prov = prov if isinstance(prov, dict) else {}
        environment = prov.get("environment")
        if not isinstance(environment, dict):
            problems.append(f"{doc}: the signature records no environment")
            continue
        environments.setdefault(
            json.dumps(environment, sort_keys=True, default=str), environment
        )
        models.setdefault(
            str(prov.get("chat_model_id")), _opt_str(prov.get("chat_model_id"))
        )
    if len(environments) > 1:
        problems.append(
            f"the panel's signatures record {len(environments)} distinct environments"
        )
    if len(models) > 1:
        problems.append(
            f"the panel's signatures record {len(models)} distinct chat models"
        )
    environment = next(iter(environments.values())) if len(environments) == 1 else None
    model = next(iter(models.values())) if len(models) == 1 else None
    return environment, model, problems


def gate(
    recorded_environment: Optional[Mapping[str, Any]],
    recorded_model: Optional[str],
    observed: Observed,
) -> Gate:
    """The refusals and the notes, in the order of the module's docstring."""
    refusals: List[str] = []
    notes: Dict[str, Any] = {}
    if observed.route_error:
        refusals.append(f"the LLM route does not resolve ({observed.route_error})")
    if observed.model is None:
        refusals.append(
            "the LLM route resolves no model: nothing would answer the acts"
        )
    if observed.cache_mode != "off":
        refusals.append(
            f"LLM_CACHE_MODE is {observed.cache_mode!r}: a cached answer is not a "
            "live act"
        )
    if observed.in_pytest:
        refusals.append(
            "the process runs under pytest: a mock service would answer the acts"
        )
    if not observed.salt:
        refusals.append(
            "OPAQUE_ID_SALT is absent: the signature's sanitiser cannot opacify a "
            "replayed state"
        )
    if observed.set_knobs:
        refusals.append(
            "set in this shell, and each one changes what the acts produce: "
            + ", ".join(observed.set_knobs)
        )
    pinned: Dict[str, Any] = {}
    if isinstance(recorded_environment, Mapping):
        overrides = recorded_environment.get("overrides")
        if isinstance(overrides, Mapping):
            pinned = overrides.get("pinned_overrides") or {}
    compared: Dict[str, Any] = {}
    for name in ACTING_PINS:
        recorded = name in pinned
        ours = name in observed.pins
        # Compared by value, reported by presence: a sampling setting is not a
        # passage, but the report keeps names and booleans and nothing else.
        equal = recorded and ours and observed.pins[name] == _pin_value(pinned[name])
        row = {"recorded": recorded, "seat": ours, "equal": equal}
        compared[name] = row
        if recorded and not equal:
            refusals.append(
                f"{name} is {'set to another value' if ours else 'unset'} on this "
                "seat and set in the recorded run: the acts would not be sampled "
                "like the analysis they read"
            )
        elif not recorded:
            row["note"] = "not recorded: the acts run under today's default"
    notes["pins"] = compared
    notes["model"] = {
        "recorded": recorded_model is not None,
        "seat": observed.model is not None,
        "equal": recorded_model == observed.model,
    }
    return Gate(tuple(refusals), notes)


# ---------------------------------------------------------------------------
# Hydration, clearing, and the census of what a run moved
# ---------------------------------------------------------------------------


def hydrate(record: Mapping[str, Any], state_class: Any) -> Any:
    """The recorded state, as the object the pipeline wrote it from.

    Measured on the c22 harvest: ``UnifiedAnalysisState(raw_text)`` then
    ``__dict__.update(inner)`` reproduces every dump byte for byte (10 of 10
    via the writer convention of :func:`writer_bytes`), with ``llm_usage`` as
    the record-only key the class does not carry.

    The update is a **deep** copy. Without it the object and the record share
    every nested container, so the run's bookkeeping writes straight into the
    record — the first control run measured it: ``workflow_results`` kept the
    acts-only run's ``completed: 3`` where the file says 47, and the write-back
    restored nothing. ``state.__dict__`` holding the same dict objects as the
    JSON it was loaded from is invisible until something mutates in place.
    """
    inner = _inner(record)
    raw = inner.get("raw_text")
    obj = state_class(raw if isinstance(raw, str) else "")
    obj.__dict__.update(copy.deepcopy(dict(inner)))
    return obj


def clear_acts(state: Any) -> None:
    """Empty the acts and what Act I carries, so a gap stays a gap.

    The writers run only on a COMPLETED phase and never write an empty text,
    so a cleared key that stays empty is the honest record of an act that did
    not produce one. ``restitution_acts_degraded`` is cleared too: the
    recorded motifs describe the recorded acts, and a live act that came out
    whole must not inherit a cut it no longer has.
    """
    state.act1_framing = ""
    state.act2_narrative = ""
    state.act3_conclusion = ""
    state.interpretive_question = ""
    state.announced_checks = []
    if isinstance(getattr(state, "restitution_acts_degraded", None), dict):
        state.restitution_acts_degraded = {}


def snapshot(state: Any) -> Dict[str, Any]:
    snap = state.get_state_snapshot(summarize=False)
    return snap if isinstance(snap, dict) else {}


def mutations(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> Dict[str, List[str]]:
    """The keys a run moved: ``changed`` (value or presence) and ``gone``."""
    changed = [key for key in after if key not in before or before[key] != after[key]]
    gone = [key for key in before if key not in after]
    return {"changed": changed, "gone": gone}


def classify(
    census: Mapping[str, Sequence[str]],
) -> Tuple[List[str], List[str], List[str]]:
    """``(live keys, reverted bookkeeping, unexpected)`` — the census sorted."""
    moved = list(census.get("changed", [])) + list(census.get("gone", []))
    written = [key for key in moved if key in WRITTEN_BACK]
    reverted = [key for key in moved if key in BOOKKEEPING]
    unexpected = [
        key for key in moved if key not in WRITTEN_BACK and key not in BOOKKEEPING
    ]
    return written, reverted, unexpected


# ---------------------------------------------------------------------------
# The recorded payloads, and the provider that serves them
# ---------------------------------------------------------------------------


def recorded_payload(state: Mapping[str, Any], act: str) -> Dict[str, Any]:
    """What the act's invoke returns, rebuilt from the state it wrote.

    The writers read exactly these keys (``state_writers`` 3221-3311): the
    act's text, and the three carriers Act I persists. ``degraded_reasons``
    is the recorded motif map, so an act that was cut (or retried) is filed
    back under the same codes.
    """
    reasons = state.get("restitution_acts_degraded") or {}
    motifs = reasons.get(act) if isinstance(reasons, Mapping) else None
    payload: Dict[str, Any] = {
        act: state.get(act) if isinstance(state.get(act), str) else "",
        "status": "completed",
        "degraded": bool(motifs),
        "degraded_reasons": dict(motifs) if isinstance(motifs, Mapping) else {},
    }
    if act == "act1_framing":
        question = state.get("interpretive_question")
        payload["interpretive_question"] = question if isinstance(question, str) else ""
        announced = state.get("announced_checks")
        payload["announced_checks"] = (
            list(announced) if isinstance(announced, list) else []
        )
    return payload


class OracleProvider:
    """An ``invoke`` that serves one recorded payload, in process, for free."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = dict(payload)
        self.calls = 0

    async def invoke(self, input_text: Any, context: Any = None) -> Any:
        self.calls += 1
        return dict(self._payload)


class StandIn:
    """The seat's real provider for an act, answering with the record.

    Everything the executor reads resolves on the real provider; only
    ``invoke`` is replaced. The parity is by delegation, not by a list of
    attributes: a first control run on a real harvest (zero cost) stopped the
    executor after Act II on a bare object — ``component_used=provider.name``
    — and that is the kind of hole a hand-written double leaves.
    """

    def __init__(self, provider: Any, payload: Mapping[str, Any]) -> None:
        self._provider = provider
        self._oracle = OracleProvider(payload)

    def __getattr__(self, attribute: str) -> Any:
        return getattr(self._provider, attribute)

    @property
    def invoke(self) -> Callable[..., Any]:
        return self._oracle.invoke

    @property
    def calls(self) -> int:
        return self._oracle.calls


class OracleRegistry:
    """The registry the run would use, each act answered by a :class:`StandIn`."""

    def __init__(
        self, registry: Any, payloads: Mapping[str, Mapping[str, Any]]
    ) -> None:
        self._registry = registry
        self._stand_ins: Dict[str, StandIn] = {}
        for act, payload in payloads.items():
            providers = registry.find_for_capability(act)
            if not providers:
                raise Refused(
                    f"the registry serves no provider for {act}: the act has "
                    "nothing to run through"
                )
            runnable = next(
                (
                    provider
                    for provider in providers
                    if getattr(provider, "invoke", None) is not None
                ),
                providers[0],
            )
            self._stand_ins[act] = StandIn(runnable, payload)

    def find_for_capability(
        self, capability: str, *args: Any, **kwargs: Any
    ) -> List[Any]:
        stand_in = self._stand_ins.get(capability)
        if stand_in is not None:
            return [stand_in]
        return list(self._registry.find_for_capability(capability, *args, **kwargs))

    def calls(self) -> Dict[str, int]:
        return {act: stand_in.calls for act, stand_in in self._stand_ins.items()}


def the_registry(runtime: Runtime) -> Any:
    """The registry a live run uses: the injected one, or the pipeline's own."""
    if runtime.registry is not None:
        return runtime.registry
    from argumentation_analysis.orchestration.registry_setup import setup_registry

    return setup_registry()


def oracle_registry(registry: Any, state: Mapping[str, Any]) -> OracleRegistry:
    return OracleRegistry(
        registry, {act: recorded_payload(state, act) for act in c.ACTS}
    )


# ---------------------------------------------------------------------------
# The workflow subset: the acts alone, and nothing else
# ---------------------------------------------------------------------------


def subset(full: Any, acts: Sequence[str] = c.ACTS) -> Tuple[Any, List[str]]:
    """``(the acts-only workflow, the phases left out)`` — asserted, not hoped.

    ``apply_skipped_phases`` is the pipeline's own switch, so the subset a
    replay runs is built by the code the production run uses. An empty skip
    list is refused: ``run_unified_analysis`` then falls back to
    ``ARGUMENTATION_SKIP_PHASES``, and the environment would choose the arm.
    """
    from argumentation_analysis.orchestration.workflows import apply_skipped_phases

    names = [phase.name for phase in full.phases]
    missing = [name for name in acts if name not in names]
    if missing:
        raise Refused(
            f"the workflow {full.name!r} declares no phase {missing}: it is not "
            "the workflow the recorded run used"
        )
    skips = [name for name in names if name not in acts]
    if not skips:
        raise Refused(
            "the workflow is the acts alone: the skip list would be empty and "
            "the environment would choose the arm"
        )
    kept = apply_skipped_phases(full, skips)
    kept_names = [phase.name for phase in kept.phases]
    if sorted(kept_names) != sorted(acts):
        raise Refused(f"the acts-only subset is not the acts: {sorted(kept_names)}")
    return kept, skips


# ---------------------------------------------------------------------------
# The runtime: the pipeline objects, bound once after the preflight
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Runtime:
    """The pipeline objects a replay needs. ``None`` means the real one.

    Injected so the tests can drive the same code with in-process providers
    and a synthetic workflow — no seat of this repo pays a model call in its
    suite.
    """

    state_class: Any
    workflow: Any
    runner: Any
    surplus: Callable[[Any], Any]
    sanitise: Callable[[Mapping[str, Any]], Any]
    registry: Optional[Any] = None
    usage_reset: Optional[Callable[[], Any]] = None
    usage_read: Optional[Callable[[], Dict[str, Any]]] = None


def build_runtime(workflow_name: str) -> Runtime:
    """The real objects, imported after the preflight and never before."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.evaluation.sanitize_state import sanitize_state
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )
    from argumentation_analysis.orchestration.workflows import get_workflow_catalog
    from argumentation_analysis.reporting.restitution.conclusion_salience import (
        projection_from_state,
    )

    catalog = get_workflow_catalog()
    if workflow_name not in catalog:
        raise Refused(
            f"the recorded workflow {workflow_name!r} is not in the catalog "
            f"({sorted(catalog)}): the acts have no place to run"
        )
    return Runtime(
        state_class=UnifiedAnalysisState,
        workflow=catalog[workflow_name],
        runner=run_unified_analysis,
        surplus=projection_from_state,
        sanitise=sanitize_state,
    )


def _usage_reset(runtime: Runtime) -> None:
    if runtime.usage_reset is not None:
        runtime.usage_reset()
        return
    from argumentation_analysis.services.llm_cache import reset_usage_stats

    reset_usage_stats()


def _usage_read(runtime: Runtime) -> Dict[str, Any]:
    if runtime.usage_read is not None:
        return dict(runtime.usage_read())
    from argumentation_analysis.services.llm_cache import get_usage_stats

    stats = get_usage_stats()
    return dict(stats) if isinstance(stats, dict) else {}


# ---------------------------------------------------------------------------
# One document, replayed
# ---------------------------------------------------------------------------


@dataclass
class Replayed:
    """What one run of the acts produced, and what it moved."""

    doc: str
    inner: Dict[str, Any]
    before: Dict[str, Any]
    after: Dict[str, Any]
    state_object: Any
    phases: Dict[str, Dict[str, Any]]
    usage: Dict[str, Any]
    wall_clock_s: float
    error: Optional[str] = None


async def _drive(
    runtime: Runtime,
    state: Any,
    text: str,
    doc: str,
    workflow_name: str,
    skips: Sequence[str],
    rests_on: bool,
    registry: Optional[Any],
) -> Any:
    """One acts-only pipeline run over the recorded state.

    The keyword set mirrors ``run_corpus_batch._run_single``: the same runner,
    the recorded workflow's own name (production's ``workflow`` argument, which
    the pristine-JPype warmup and the result's ``workflow_name`` read), the
    analysed document's opaque id by context (never ``source_metadata`` — #3548
    R1205), no restitution render, and the same single per-document budget.
    """
    context: Dict[str, Any] = {
        "analysed_document_id": doc,
        "skip_phases": list(skips),
        "rests_on": rests_on,
    }
    return await asyncio.wait_for(
        runtime.runner(
            text,
            workflow_name=workflow_name,
            registry=registry if registry is not None else runtime.registry,
            custom_workflow=runtime.workflow,
            context=context,
            state=state,
            create_state=False,
            render_restitution=False,
            deanonymized=True,
        ),
        timeout=WALL_BUDGET_S,
    )


async def run_acts(
    doc: str,
    state_file: Mapping[str, Any],
    signature: Mapping[str, Any],
    runtime: Runtime,
    *,
    registry: Optional[Any] = None,
    usage_reset: Optional[Callable[[], Any]] = None,
    usage_read: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Replayed:
    """Hydrate, clear, run the acts, and report what the run did to the state."""
    # Deep, and the snapshot too: the census is only a census if the two sides
    # cannot share a container with the live object (see :func:`hydrate`).
    inner = copy.deepcopy(dict(_inner(state_file)))
    under = runtime
    if usage_reset is not None or usage_read is not None:
        under = Runtime(
            state_class=runtime.state_class,
            workflow=runtime.workflow,
            runner=runtime.runner,
            surplus=runtime.surplus,
            sanitise=runtime.sanitise,
            registry=runtime.registry,
            usage_reset=usage_reset or runtime.usage_reset,
            usage_read=usage_read or runtime.usage_read,
        )
    obj = hydrate(state_file, runtime.state_class)
    before = copy.deepcopy(snapshot(obj))
    clear_acts(obj)
    _, skips = subset(runtime.workflow)
    rests_on = bool(inner.get("rests_on_armed", False))
    raw = inner.get("raw_text")
    text = raw if isinstance(raw, str) else ""
    _usage_reset(under)
    started = time.perf_counter()
    error: Optional[str] = None
    phases: Dict[str, Dict[str, Any]] = {}
    recorded_name = signature.get("workflow")
    workflow_name = (
        recorded_name
        if isinstance(recorded_name, str) and recorded_name
        else runtime.workflow.name
    )
    try:
        result = await _drive(
            under, obj, text, doc, workflow_name, skips, rests_on, registry
        )
    except asyncio.TimeoutError:
        error = f"wall_budget({WALL_BUDGET_S:g}s)"
        result = None
    except Exception as exc:  # noqa: BLE001 — named, and the census still runs
        # The type and a short head of the message: an exception raised inside
        # a prompt may quote the passage it was building.
        error = f"{type(exc).__name__}: {str(exc)[:120]}"
        result = None
    wall = round(time.perf_counter() - started, 1)
    usage = _usage_read(under)
    if isinstance(result, Mapping):
        found = result.get("phases")
        if isinstance(found, Mapping):
            for act in c.ACTS:
                phase = found.get(act)
                status = getattr(getattr(phase, "status", None), "value", None)
                if status is None:
                    continue
                phases[act] = {
                    "status": status,
                    "error_kind": getattr(phase, "error_kind", None),
                    "attempts": _opt_int(getattr(phase, "attempts", None)),
                }
    return Replayed(
        doc=doc,
        inner=inner,
        before=before,
        after=snapshot(obj),
        state_object=obj,
        phases=phases,
        usage=usage,
        wall_clock_s=wall,
        error=error,
    )


def _is_phase_bucket(value: Any) -> bool:
    """A phase's own bucket: it counts its calls.

    A usage map also carries run-level entries that are dictionaries —
    ``unpriced_calls`` and ``unverified_price_calls`` (``UsageStats.as_dict``) —
    and they are not phases. Read by type alone, they named themselves "a phase
    outside the three acts called the model" on every live run.
    """
    return isinstance(value, Mapping) and _opt_int(value.get("calls")) is not None


def act_buckets(usage: Any) -> Dict[str, Dict[str, Any]]:
    """The three act buckets of a usage map, by act name."""
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(usage, Mapping):
        for act in c.ACTS:
            bucket = usage.get(act)
            if isinstance(bucket, Mapping):
                out[act] = dict(bucket)
    return out


def run_level(usage: Any) -> Dict[str, Any]:
    """The usage map's run-level entries: everything that is not a phase."""
    if not isinstance(usage, Mapping):
        return {}
    return {
        key: copy.deepcopy(value)
        for key, value in usage.items()
        if not _is_phase_bucket(value)
    }


def merged_usage(recorded: Any, live: Any) -> Dict[str, Any]:
    """The record's usage with its act buckets replaced, nothing else moved.

    The recorded non-act buckets describe phases this replay does not run:
    replacing them with the replay's zeros would erase what the state's
    upstream analysis cost. Only the acts are the replay's to account. The
    run-level entries (the run's cost fields) stay the recorded run's for the
    same reason — they price that run; the replay's own are reported apart
    (:func:`run_level`), never summed into a total no run spent.
    """
    out: Dict[str, Any] = dict(recorded) if isinstance(recorded, Mapping) else {}
    for act, bucket in act_buckets(live).items():
        out[act] = bucket
    return out


@dataclass(frozen=True)
class Facts:
    """What a signature's ``provenance`` says about the run that wrote it."""

    run_started_utc: Optional[str]
    code_sha: Optional[str]
    chat_model_id: Optional[str]
    environment: Mapping[str, Any]
    params: Mapping[str, Any]

    @classmethod
    def of(cls, signature: Mapping[str, Any]) -> "Facts":
        prov = signature.get("provenance")
        prov = prov if isinstance(prov, Mapping) else {}
        environment = prov.get("environment")
        params = prov.get("params")
        return cls(
            run_started_utc=_opt_str(prov.get("run_started_utc")),
            code_sha=_opt_str(prov.get("code_sha")),
            chat_model_id=_opt_str(prov.get("chat_model_id")),
            environment=dict(environment) if isinstance(environment, Mapping) else {},
            params=dict(params) if isinstance(params, Mapping) else {},
        )


def build_signature(
    recorded: Mapping[str, Any],
    snapshot_: Mapping[str, Any],
    usage: Mapping[str, Any],
    surplus: Any,
    facts: Facts,
    sanitise: Callable[[Mapping[str, Any]], Any],
    replay_block: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """The record's signature with today's state, usage and provenance.

    The record's key order is kept (``dict(recorded)`` then in-place writes),
    so a reader of the tag reads the same schema it reads everywhere; the
    ``act_replay`` block is appended, and only for a live document.
    """
    signature = dict(recorded)
    signature["state"] = sanitise(dict(snapshot_))
    signature["llm_usage"] = dict(usage)
    prov = signature.get("provenance")
    provenance_ = dict(prov) if isinstance(prov, Mapping) else {}
    provenance_["run_started_utc"] = facts.run_started_utc
    provenance_["code_sha"] = facts.code_sha
    provenance_["chat_model_id"] = facts.chat_model_id
    provenance_["environment"] = dict(facts.environment)
    provenance_["params"] = dict(facts.params)
    signature["provenance"] = provenance_
    signature["zero_shot_surplus"] = surplus
    if replay_block is not None:
        signature["act_replay"] = dict(replay_block)
    return signature


@dataclass
class Assembled:
    """One document's tag files, and the row the report keeps of them."""

    doc: str
    state: Dict[str, Any]
    signature: Dict[str, Any]
    row: Dict[str, Any]
    failure: Optional[str] = None


def assemble(
    replayed: Replayed,
    recorded_signature: Mapping[str, Any],
    runtime: Runtime,
    *,
    live: bool,
    facts: Facts,
    source_cycle: str,
    source_head: Optional[str],
    branch: Optional[str] = None,
) -> Assembled:
    """Write back the acts, restore the record's bookkeeping, build the pair.

    ``live=False`` is the identity control: the recorded ``Facts`` and no
    ``act_replay`` block, so the only difference from the record is what the
    instrument itself does.
    """
    written, reverted, unexpected = classify(mutations(replayed.before, replayed.after))
    row: Dict[str, Any] = {
        "doc": replayed.doc,
        "mode": LIVE if live else "control",
        "branch": branch,
        "acts": {},
        "reverted": reverted,
        "unexpected": unexpected,
        "wall_clock_s": replayed.wall_clock_s,
    }
    failure: Optional[str] = None
    if replayed.error:
        failure = f"the run ended with {replayed.error}"
        row["error"] = replayed.error
    if unexpected:
        failure = failure or (
            "a state key outside the written-back and bookkeeping sets moved: "
            + ", ".join(unexpected)
        )
    out = dict(replayed.inner)
    for key in WRITTEN_BACK:
        if key in replayed.after:
            out[key] = replayed.after[key]
    for key in BOOKKEEPING:
        if key in replayed.inner:
            out[key] = replayed.inner[key]
        else:
            out.pop(key, None)
    live_buckets = act_buckets(replayed.usage)
    out["llm_usage"] = merged_usage(replayed.inner.get("llm_usage"), replayed.usage)
    codes: Dict[str, Dict[str, str]] = {}
    degraded: List[str] = []
    stray = sorted(
        key
        for key, value in replayed.usage.items()
        if key not in c.ACTS and _is_phase_bucket(value)
    )
    if live and stray:
        failure = failure or (
            "a phase outside the three acts called the model: " + ", ".join(stray)
        )
    for act in c.ACTS:
        phase = replayed.phases.get(act, {})
        status = phase.get("status")
        bucket = live_buckets.get(act, {})
        calls = _opt_int(bucket.get("calls")) or 0
        before_text = replayed.before.get(act)
        after_text = out.get(act)
        changed = before_text != after_text
        if status is None:
            codes[act] = {CODE_PHASE_FAILED: "unknown"}
        elif status != "completed":
            # A length stop is never filed here: the producer's own cut code
            # (46a) rides the act's degraded map through the writers, and the
            # judge reads that one. This is a phase that did not come back.
            code = CODE_PHASE_FAILED if status == "failed" else CODE_PHASE_SKIPPED
            codes[act] = {code: str(phase.get("error_kind") or status)}
        elif calls == 0 and isinstance(after_text, str) and after_text:
            failure = failure or (
                f"{act} carries a text no call paid for: a cached or mocked "
                "answer is not a live act"
            )
            codes[act] = {CODE_PHASE_FAILED: "no_call"}
        elif calls == 0:
            codes[act] = {CODE_PHASE_FAILED: "no_text"}
        if act in codes:
            degraded.append(act)
        row["acts"][act] = {
            "status": status,
            "attempts": phase.get("attempts"),
            "calls": calls,
            "prompt_tokens": _opt_int(bucket.get("prompt_tokens")),
            "completion_tokens": _opt_int(bucket.get("completion_tokens")),
            "length_stops": _opt_int(bucket.get("length_stops")) or 0,
            "chars": len(after_text) if isinstance(after_text, str) else None,
            "recorded_chars": (
                len(before_text) if isinstance(before_text, str) else None
            ),
            "changed": changed,
            "codes": sorted(codes.get(act, {})),
        }
    if codes:
        rstd = out.get("restitution_acts_degraded")
        rstd = dict(rstd) if isinstance(rstd, Mapping) else {}
        for act, filed in codes.items():
            bucket_ = (
                dict(rstd.get(act) or {}) if isinstance(rstd.get(act), Mapping) else {}
            )
            bucket_.update(filed)
            rstd[act] = bucket_
        out["restitution_acts_degraded"] = rstd
    if degraded and all(act in degraded for act in c.ACTS):
        failure = (
            failure
            or "every act of this document failed: the merged code does not answer"
        )
    # Read from the state the tag carries: the run's own bookkeeping stays on
    # the object it ran through, and the tag does not carry that object.
    surplus = runtime.surplus(hydrate(out, runtime.state_class))
    block: Optional[Dict[str, Any]] = None
    if live:
        block = {
            "instrument": INSTRUMENT,
            "source_cycle": source_cycle,
            "source_head": source_head,
            "acts": {
                act: {
                    key: row["acts"][act][key]
                    for key in (
                        "status",
                        "attempts",
                        "calls",
                        "prompt_tokens",
                        "completion_tokens",
                        "length_stops",
                        "chars",
                        "changed",
                    )
                }
                for act in c.ACTS
            },
            "codes": {act: sorted(filed) for act, filed in codes.items()},
            "wall_clock_s": replayed.wall_clock_s,
            "usage": {
                "live_run": run_level(replayed.usage),
                "llm_usage": USAGE_NOTE,
            },
        }
    signature = build_signature(
        recorded_signature,
        out,
        out["llm_usage"],
        surplus,
        facts,
        runtime.sanitise,
        block,
    )
    keys_before = set(recorded_signature)
    keys_after = set(signature)
    extra = sorted(keys_after - keys_before - {"act_replay"})
    row["signature"] = {
        "keys": len(signature),
        "extra_keys": extra,
        "chars": len(dumps(signature)),
        "digest": _digest(dumps(signature)),
    }
    if extra:
        failure = (
            failure
            or "the signature gained keys the record does not carry: "
            + ", ".join(extra)
        )
    row["usage"] = {
        "live_calls": sum(
            (_opt_int(bucket.get("calls")) or 0) for bucket in live_buckets.values()
        ),
        "live_run": run_level(replayed.usage),
        "recorded_buckets_kept": (
            sorted(
                key
                for key, value in (replayed.inner.get("llm_usage") or {}).items()
                if key not in c.ACTS and _is_phase_bucket(value)
            )
            if isinstance(replayed.inner.get("llm_usage"), Mapping)
            else []
        ),
    }
    row["ok"] = failure is None
    if failure:
        row["failure"] = failure
    return Assembled(
        doc=replayed.doc,
        state=out,
        signature=signature,
        row=row,
        failure=failure,
    )


# ---------------------------------------------------------------------------
# The identity control: give back the record, byte for byte
# ---------------------------------------------------------------------------


def signature_divergence(
    control: Mapping[str, Any], record: Mapping[str, Any]
) -> Dict[str, Any]:
    """Which top-level keys differ, and which sanitised fields inside ``state``.

    Names only. The caller reads ``only_state``: when it is true, the two
    snapshots were proven equal by the state half, so the only code between
    them and the signature is ``sanitize_state`` — a sanitiser difference, not
    an instrument one.
    """
    keys = [key for key in record if key in control and control[key] != record[key]]
    keys += [key for key in record if key not in control]
    keys += [key for key in control if key not in record]
    inside: List[str] = []
    theirs = record.get("state")
    ours = control.get("state")
    if isinstance(theirs, Mapping) and isinstance(ours, Mapping):
        inside = (
            [key for key in theirs if key in ours and ours[key] != theirs[key]]
            + [key for key in theirs if key not in ours]
            + [key for key in ours if key not in theirs]
        )
    return {
        "differing_keys": sorted(set(keys)),
        "differing_state_fields": sorted(set(inside)),
        "only_state": bool(keys) and set(keys) == {"state"},
    }


def identity_control(
    doc: str,
    state_file: Mapping[str, Any],
    signature: Mapping[str, Any],
    runtime: Runtime,
    state_bytes: bytes,
    signature_bytes: bytes,
) -> Dict[str, Any]:
    """Run the acts on the record's own payloads; the bytes must come back.

    The control costs nothing: its providers are in process and its usage
    reader is the record's own act buckets. It measures the instrument — the
    executor's order, the real writers, the write-back, the signature builder
    — not the model.
    """
    inner = _inner(state_file)
    try:
        oracle = oracle_registry(the_registry(runtime), inner)
    except Refused as exc:
        return {
            "doc": doc,
            "ok": False,
            "failure": str(exc),
            "acts_run": 0,
            "calls": {},
        }
    buckets = act_buckets(inner.get("llm_usage"))
    replayed = asyncio.run(
        run_acts(
            doc,
            state_file,
            signature,
            runtime,
            registry=oracle,
            usage_reset=lambda: None,
            usage_read=lambda: buckets,
        )
    )
    assembled = assemble(
        replayed,
        signature,
        runtime,
        live=False,
        facts=Facts.of(signature),
        source_cycle="",
        source_head=None,
    )
    state_text = dumps(assembled.state)
    signature_text = dumps(assembled.signature)
    state_equal = writer_bytes(state_text) == state_bytes
    signature_equal = writer_bytes(signature_text) == signature_bytes
    divergence = signature_divergence(assembled.signature, signature)
    # "sanitiser" only once the state half has held: then the two snapshots are
    # proven equal, and the only code left between them and the signature is
    # ``sanitize_state``. A signature that differs while the state does too is
    # the instrument's doing, whatever keys it names.
    sanitiser = state_equal and (not signature_equal) and divergence["only_state"]
    calls = oracle.calls()
    acts_run = sum(1 for act in c.ACTS if calls.get(act, 0) == 1)
    ok = (
        state_equal
        and (signature_equal or sanitiser)
        and assembled.failure is None
        and acts_run == len(c.ACTS)
    )
    row: Dict[str, Any] = {
        "doc": doc,
        "ok": ok,
        "state": {
            "equal": state_equal,
            "chars": len(state_text),
            "digest": _digest(state_text),
        },
        "signature": {
            "equal": signature_equal,
            "cause": (
                None
                if signature_equal
                else ("sanitiser" if sanitiser else "instrument")
            ),
            "chars": len(signature_text),
            "digest": _digest(signature_text),
            "differing_keys": divergence["differing_keys"],
            "differing_state_fields": divergence["differing_state_fields"],
        },
        "acts_run": acts_run,
        "calls": calls,
        "reverted": assembled.row["reverted"],
        "unexpected": assembled.row["unexpected"],
    }
    if assembled.failure:
        row["failure"] = assembled.failure
    return row


# ---------------------------------------------------------------------------
# The live batch
# ---------------------------------------------------------------------------


def replayable(
    state: Mapping[str, Any], signature: Mapping[str, Any]
) -> Tuple[bool, str]:
    """``(replayed live?, why not)`` — read from the fidelity witness's branch."""
    from scripts.panel import act_replay_fidelity as fidelity

    branch = fidelity.render_branch(state, signature)
    if branch in (fidelity.BRANCH_ACTS, fidelity.BRANCH_CUT):
        return True, ""
    if branch == fidelity.BRANCH_NON_ARGUMENTATIVE:
        return (
            False,
            "non_argumentative: no act ran in the record and the render reads none",
        )
    return False, f"{branch}: this mode has no acts by design"


def _transport_attempts_per_call() -> int:
    """How many transport attempts one model call may cost, read from the
    policy that applies them.

    #3658 item 46g-3 (R1220 d) — the announcement counted the acts' own
    retries and not the transport's. The acts run on the LLM service's client,
    whose ``ResilientAsyncTransport`` retries each request up to
    ``NETWORK_RETRY_STOP_AFTER_ATTEMPT`` times, so a "call" is up to that many
    paid requests. The number is READ from the settings that produce it
    (``argumentation_analysis.config.settings``), never copied into the panel:
    a second literal would drift the day the policy moves.
    """
    from argumentation_analysis.config.settings import settings

    return max(1, int(settings.network.retry_stop_after_attempt))


def run(
    cycle_dir: Path,
    destination: Path,
    panel: Optional[Sequence[str]] = None,
    argv: Sequence[str] = (),
    *,
    observed: Optional[Observed] = None,
    runtime: Optional[Runtime] = None,
    results_root: Path = c.RESULTS_ROOT,
    probe: bool = False,
) -> Dict[str, Any]:
    """The whole live replay: preflight, gate, control, the paid acts, the tag.

    Every return is a plain dictionary; ``stage`` says where it stopped and
    ``ok`` whether the tag is a measurement. Nothing is written before the
    identity control has given the record back, and the tag's first
    ``pipeline.json`` says ``rc`` 1.

    ``probe`` (#3658 item 46g) declares the named panel a subset chosen on
    purpose: only those documents are replayed, the rest of the cycle is named
    in ``report["probe"]`` and in the tag, and the tag carries one document, so
    a judges stage given the whole panel refuses it (``unharvested`` names the
    documents it is missing) instead of grading a probe as a panel.
    """
    cycle_dir, destination = Path(cycle_dir), Path(destination)
    report: Dict[str, Any] = {
        "provenance": provenance(argv, cycle_dir, destination, panel)
    }
    verdict = preflight(cycle_dir, destination, panel, probe=probe)
    if not verdict.ok:
        report.update(
            {"ok": False, "stage": STAGE_PREFLIGHT, "preflight": verdict.as_dict()}
        )
        return report
    # #3658 item 46g — this instrument only READS the cycle, so its inputs must
    # be byte-identical once the acts are done. The map is taken here, before
    # anything of the replay has touched the cycle: the preflight writes
    # nothing and the tag is a separate directory, so a difference past this
    # point means something wrote where nothing was allowed to.
    from scripts.panel.replay_acts import InputsUnreadable, cycle_inputs, input_drift

    try:
        inputs_before = cycle_inputs(cycle_dir)
    except InputsUnreadable as exc:
        report.update(
            {"ok": False, "stage": STAGE_CYCLE, "refused": f"cycle input: {exc}"}
        )
        return report
    problem = tag_problem(destination, results_root)
    if problem is not None:
        report.update(
            {
                "ok": False,
                "stage": STAGE_TAG,
                "refused": problem,
                "preflight": verdict.as_dict(),
            }
        )
        return report
    try:
        record = read_record(cycle_dir / PIPELINE_RECORD)
    except Refused as exc:
        report.update({"ok": False, "stage": STAGE_CYCLE, "refused": str(exc)})
        return report
    from scripts.panel.run_cycle import pipeline_problem

    why = pipeline_problem(record)
    if why is not None:
        report.update({"ok": False, "stage": STAGE_CYCLE, "refused": why})
        return report
    # --- past this line the text builders and the runtime may exist ---
    from scripts.panel import act_replay_fidelity as fidelity

    try:
        docs, states, signatures = fidelity.load_records(cycle_dir)
    except (OSError, ValueError) as exc:
        report.update(
            {"ok": False, "stage": STAGE_RECORDS, "refused": f"{type(exc).__name__}"}
        )
        return report
    probe_scope: Optional[Dict[str, Any]] = None
    if probe:
        # #3658 item 46g — the probe's scope, named: the documents it covers
        # are the ones it named, and the rest of the cycle is declared left out
        # here and in the tag. Nothing is dropped silently.
        named = set(panel or ())
        covered = [doc for doc in docs if doc in named]
        if not covered:
            report.update(
                {
                    "ok": False,
                    "stage": STAGE_RECORDS,
                    "refused": "the probe names no document of this cycle",
                }
            )
            return report
        probe_scope = {
            "named": len(named),
            "covered": covered,
            "left_out": [doc for doc in docs if doc not in named],
            "cycle_documents": len(docs),
        }
        docs = covered
    environment, recorded_model, problems = recorded_settings(signatures)
    seat_input = observed or observe()
    seat = gate(environment, recorded_model, seat_input)
    if problems or not seat.ok:
        report.update(
            {
                "ok": False,
                "stage": STAGE_GATE,
                "refusals": problems + list(seat.refusals),
                "gate": seat.as_dict(),
            }
        )
        return report
    report["gate"] = seat.as_dict()
    try:
        rt = runtime or build_runtime(str(signatures[docs[0]].get("workflow") or ""))
    except Refused as exc:
        report.update({"ok": False, "stage": STAGE_GATE, "refused": str(exc)})
        return report
    try:
        _, phases_left_out = subset(rt.workflow)
    except Refused as exc:
        report.update({"ok": False, "stage": STAGE_GATE, "refused": str(exc)})
        return report
    live_docs: List[str] = []
    copied: Dict[str, str] = {}
    for doc in docs:
        try:
            goes, why_not = replayable(states[doc], signatures[doc])
        except Exception as exc:  # noqa: BLE001 — one record, named
            report.update(
                {
                    "ok": False,
                    "stage": STAGE_RECORDS,
                    "refused": f"{doc}: {type(exc).__name__}",
                }
            )
            return report
        if goes:
            live_docs.append(doc)
        else:
            copied[doc] = why_not
    if not live_docs:
        report.update(
            {
                "ok": False,
                "stage": STAGE_RECORDS,
                "refused": "no document of this cycle reads acts: nothing to replay",
            }
        )
        return report
    # #3658 item 46g-3 (R1220 a) — the documents copied as they are can reach
    # the judges' own threshold on their own. The judges read the whole panel,
    # copies included, so a batch that only counted its live documents would
    # spend the panel on one they refuse. Read here, free: the copies are the
    # cycle's own records, and nothing is created or paid before this refusal.
    from scripts.dataset import judge_panel as judged

    threshold = judged.DEGRADED_ARM_REFUSAL_THRESHOLD
    copied_degraded: List[str] = []
    for doc in copied:
        try:
            row = judged.arm_health(states[doc], signatures[doc])
        except Exception:  # noqa: BLE001 — unreadable is named by the self-check
            continue
        if row.get("pipeline_degraded"):
            copied_degraded.append(doc)
    if len(copied_degraded) >= threshold:
        report.update(
            {
                "ok": False,
                "stage": STAGE_RECORDS,
                "refused": (
                    f"the panel's copied document(s) already reach "
                    f"DEGRADED_ARM_REFUSAL_THRESHOLD={threshold} on their own "
                    f"({', '.join(copied_degraded)}): the judges would refuse "
                    "this panel, so nothing is replayed"
                ),
                "copied_degraded": list(copied_degraded),
            }
        )
        return report
    # ---- the identity control, free, before the destination exists ----
    control_rows: List[Dict[str, Any]] = []
    for doc in live_docs:
        state_path = c.state_path(cycle_dir / "states", doc)
        signature_path = cycle_dir / "signatures" / f"signature_{doc}.json"
        control_rows.append(
            identity_control(
                doc,
                states[doc],
                signatures[doc],
                rt,
                state_path.read_bytes(),
                signature_path.read_bytes(),
            )
        )
    control_ok = all(row["ok"] for row in control_rows)
    report["control"] = {
        "ok": control_ok,
        "documents": len(control_rows),
        "rows": control_rows,
    }
    if not control_ok:
        report.update(
            {
                "ok": False,
                "stage": STAGE_CONTROL,
                "refused": (
                    "the identity control did not give the record back: nothing "
                    "this instrument renders is a measure (#3658 item 46c)"
                ),
            }
        )
        return report
    # ---- the tag: refusing-first, then the acts ----
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "states").mkdir()
    (destination / "signatures").mkdir()
    head_before = current_head()
    started = utc_now()
    _write_pipeline(
        destination, _refusing_record(cycle_dir, head_before, started, len(docs))
    )
    assembled_rows: List[Dict[str, Any]] = []
    stopped: Optional[str] = None
    stop_why: Optional[str] = None
    # #3658 item 46g-3 (R1220 a) — the count the batch stops on is the panel's,
    # not its live documents': the copies are in it from the start.
    degraded_docs: List[str] = list(copied_degraded)
    calls_by_doc: Dict[str, int] = {}
    call_bound = len(live_docs) * ACT_CALLS_PER_DOCUMENT
    # #3658 item 46g-3 (R1220 d) — a "call" is what the acts ask for; each one
    # is replayed by the transport on its own policy, so the spend is announced
    # in the unit the provider bills: requests.
    transport_attempts = _transport_attempts_per_call()
    requests_bound = call_bound * transport_attempts
    # #3658 item 46g — the bound is announced BEFORE the first call, so the
    # spend is a declared one. What the run actually spends is counted below.
    print(
        f"[act_replay] {len(live_docs)} document(s) to replay live: at most "
        f"{ACT_CALLS_PER_DOCUMENT} model calls each (Acts II and III retry once), "
        f"each call replayed by the transport up to {transport_attempts} time(s) "
        f"(NETWORK_RETRY_STOP_AFTER_ATTEMPT), so at most {requests_bound} paid "
        f"request(s) before this run ends.",
        flush=True,
    )
    for doc in live_docs:
        if stopped is not None:
            copied[doc] = f"not_run: the batch stopped at {stopped}"
            continue
        replayed = asyncio.run(run_acts(doc, states[doc], signatures[doc], rt))
        facts = Facts(
            run_started_utc=started,
            code_sha=current_head(),
            chat_model_id=seat_input.model,
            environment=_recorded_environment(signatures[doc]),
            params={
                "workflow": str(signatures[doc].get("workflow") or ""),
                "timeout_s": WALL_BUDGET_S,
                "acts": list(c.ACTS),
                "phases_left_out": len(phases_left_out),
            },
        )
        assembled = assemble(
            replayed,
            signatures[doc],
            rt,
            live=True,
            facts=facts,
            source_cycle=cycle_dir.name,
            source_head=_opt_str(record.get("head")),
            branch=_branch_of(states[doc], signatures[doc]),
        )
        _write_pair(destination, doc, assembled.state, assembled.signature)
        assembled_rows.append(assembled.row)
        # #3658 item 46g — what this document really cost, from the run's own
        # usage map, every phase bucket counted (a call outside the three acts
        # is a call). Counted even when the assembly failed: it was paid.
        calls_by_doc[doc] = sum(
            int(bucket.get("calls") or 0)
            for bucket in replayed.usage.values()
            if _is_phase_bucket(bucket)
        )
        if assembled.failure is not None:
            stopped = doc
            stop_why = f"the replay failed on {doc}: {assembled.failure}"
            continue
        try:
            health = judged.arm_health(assembled.state, assembled.signature)
        except Exception as exc:  # noqa: BLE001 — one document, named, fail closed
            stopped = doc
            stop_why = f"arm health unreadable on {doc}: {type(exc).__name__}"
            continue
        if health.get("pipeline_degraded"):
            # The judges' own rule, applied while the batch runs: one degraded
            # document is tolerated, and at their threshold the panel is one
            # the judges stage would refuse — spending the rest of it would be
            # paying for a refusal.
            degraded_docs.append(doc)
            if len(degraded_docs) >= threshold:
                stopped = doc
                stop_why = (
                    f"the batch stopped: {len(degraded_docs)} degraded document(s) "
                    f"reach DEGRADED_ARM_REFUSAL_THRESHOLD={threshold} — the "
                    "judges' own rule would refuse this panel"
                )
    for doc, reason in copied.items():
        shutil.copyfile(
            cycle_dir / "states" / f"state_full_{doc}.json",
            destination / "states" / f"state_full_{doc}.json",
        )
        shutil.copyfile(
            cycle_dir / "signatures" / f"signature_{doc}.json",
            destination / "signatures" / f"signature_{doc}.json",
        )
        assembled_rows.append(
            {"doc": doc, "mode": COPIED, "reason": reason, "ok": True}
        )

    def _record(count_ok: bool, check: Mapping[str, Any]) -> Dict[str, Any]:
        return _final_record(
            cycle_dir,
            head_before,
            current_head(),
            started,
            utc_now(),
            len(docs),
            assembled_rows,
            check,
            count_ok=count_ok,
            probe=probe_scope,
        )

    # Every pair is on disk, and the record still refuses: a run that dies here
    # leaves a cycle the judges stage refuses, never one it grades. The check
    # below reads the tag through the judges' own entry points, so the record
    # it reads must already carry the completed harvest.
    _write_pipeline(destination, _record(False, {"ok": False, "guard": {}}))
    self_check = _self_check(destination, docs, results_root, _record(True, {}))
    # #3658 item 46g — the cycle was only read: the same map again, past the
    # acts and the copies, and a difference refuses the tag (rc 1) naming the
    # file. A file that cannot be read at all refuses by name too — a
    # fingerprint with a hole in it proves nothing.
    try:
        inputs_after = cycle_inputs(cycle_dir)
    except InputsUnreadable as exc:
        report.update(
            {"ok": False, "stage": STAGE_RECORDS, "refused": f"cycle input: {exc}"}
        )
        return report
    drifted = input_drift(inputs_before, inputs_after)
    # #3658 item 46g-3 (R1220 a) — the guard the judges apply is the guard this
    # record carries: a panel at their threshold is one they would refuse, so a
    # tag calling itself a measurement would be false. ``ok`` says it, and the
    # refusal below names the count instead of leaving it in the self-check.
    guard = self_check.get("guard") or {}
    would_refuse = bool(guard.get("would_refuse"))
    ok = (
        stopped is None
        and self_check["ok"]
        and not drifted
        and not would_refuse
    )
    counts: Dict[str, Any] = {
        "documents": len(docs),
        "live": sum(1 for row in assembled_rows if row.get("mode") == LIVE),
        "copied": len(copied),
        "acts_live": sum(
            1
            for row in assembled_rows
            for act in row.get("acts", {}).values()
            if act.get("status") == "completed"
        ),
        "acts_degraded": [
            row["doc"]
            for row in assembled_rows
            for act in row.get("acts", {}).values()
            if act.get("status") != "completed"
        ],
        "control_documents": len(control_rows),
        "control_ok": sum(1 for row in control_rows if row["ok"]),
        "degraded_arms": self_check["guard"]["degraded_arms"],
        "model_calls": sum(calls_by_doc.values()),
        "call_bound": call_bound,
    }
    _write_pipeline(destination, _record(ok, self_check))
    report.update(
        {
            "ok": ok,
            "stage": STAGE_DONE,
            "counts": counts,
            "probe": probe_scope,
            "call_budget": {
                "documents": len(live_docs),
                "per_document": ACT_CALLS_PER_DOCUMENT,
                "bound": call_bound,
                "transport_attempts_per_call": transport_attempts,
                "bound_requests": requests_bound,
                "made": sum(calls_by_doc.values()),
                "per_document_made": dict(calls_by_doc),
            },
            "cycle_inputs": {
                "files": len(inputs_before),
                "unchanged": not drifted,
                "drifted": drifted,
                "before": inputs_before,
                "after": inputs_after,
            },
            "documents": assembled_rows,
            "self_check": self_check,
        }
    )
    if not ok:
        if stopped is not None:
            report["refused"] = stop_why or f"the batch stopped at {stopped}"
        elif drifted:
            report["refused"] = (
                "the cycle's inputs moved during the measurement: "
                + ", ".join(drifted[:4])
            )
        elif would_refuse:
            report["refused"] = (
                f"the panel the judges would read holds {guard.get('degraded_arms')} "
                f"degraded document(s), at DEGRADED_ARM_REFUSAL_THRESHOLD="
                f"{guard.get('threshold')}: they would refuse it, so this tag is "
                "not a measurement"
            )
        else:
            report["refused"] = "the self-check failed"
    return report


def _recorded_environment(signature: Mapping[str, Any]) -> Mapping[str, Any]:
    prov = signature.get("provenance")
    prov = prov if isinstance(prov, Mapping) else {}
    environment = prov.get("environment")
    return dict(environment) if isinstance(environment, Mapping) else {}


def _branch_of(state: Mapping[str, Any], signature: Mapping[str, Any]) -> Optional[str]:
    from scripts.panel import act_replay_fidelity as fidelity

    try:
        return fidelity.render_branch(state, signature)
    except Exception:  # noqa: BLE001 — the branch is a label, never a gate here
        return None


def _write_pair(
    destination: Path, doc: str, state: Mapping[str, Any], signature: Mapping[str, Any]
) -> None:
    (destination / "states" / f"state_full_{doc}.json").write_text(
        dumps(state), encoding="utf-8"
    )
    (destination / "signatures" / f"signature_{doc}.json").write_text(
        dumps(signature), encoding="utf-8"
    )


def _refusing_record(
    cycle_dir: Path, head: Optional[str], started: str, documents: int
) -> Dict[str, Any]:
    """The first ``pipeline.json``: every exit before the pairs says rc 1."""
    return {
        "rc": 1,
        "stage": LIVE,
        "instrument": INSTRUMENT,
        "source_cycle": cycle_dir.name,
        "started_utc": started,
        "head": head,
        "head_after": head,
        "harvest": {"copied": 0, "missing": documents, "stale": 0},
        "note": (
            "refusing first: this record says rc=1 until the replay has written "
            "every pair — a run that dies here leaves a cycle the judges stage "
            "refuses"
        ),
    }


def _final_record(
    cycle_dir: Path,
    head_before: Optional[str],
    head_after: Optional[str],
    started: str,
    finished: str,
    documents: int,
    rows: Sequence[Mapping[str, Any]],
    self_check: Mapping[str, Any],
    count_ok: bool,
    probe: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    live_rows = [row for row in rows if row.get("mode") == LIVE]
    record: Dict[str, Any] = {
        "rc": 0 if count_ok and head_before == head_after else 1,
        "stage": LIVE,
        "instrument": INSTRUMENT,
        "source_cycle": cycle_dir.name,
        "started_utc": started,
        "finished_utc": finished,
        "head": head_before,
        "head_after": head_after,
        "harvest": {"copied": documents, "missing": 0, "stale": 0},
        "replayed": {
            "live": len(live_rows),
            "copied": documents - len(live_rows),
            "acts_completed": sum(
                1
                for row in live_rows
                for act in row.get("acts", {}).values()
                if act.get("status") == "completed"
            ),
        },
        "verdict": {
            "self_check": bool(self_check.get("ok")),
            "guard_degraded_arms": self_check.get("guard", {}).get("degraded_arms"),
            "guard_would_refuse": self_check.get("guard", {}).get("would_refuse"),
        },
    }
    if probe is not None:
        # The tag says it is a probe, in the file the judges read: a tag that
        # covered one document of a ten-document cycle must never look like a
        # panel that happened to hold one.
        record["probe"] = dict(probe)
    return record


def _write_pipeline(destination: Path, record: Mapping[str, Any]) -> None:
    (destination / PIPELINE_RECORD).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _self_check(
    destination: Path,
    docs: Sequence[str],
    results_root: Path = c.RESULTS_ROOT,
    candidate: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Read the tag back through the cycle's and the judge's own entry points.

    ``candidate`` is the ``pipeline.json`` this run writes once the check holds.
    The record on disk at this moment is the unverified one (rc 1, harvest
    complete), so the rc/head verdict is taken on ``candidate`` — the caller
    decides rc from this check's outcome, and splitting the two readings is what
    keeps the check from grading its own writer's last act.
    """
    problems: List[str] = []
    probe = destination.parent / f"{destination.name}.probe"
    verdict = preflight(destination, probe, list(docs))
    unexpected = [
        problem.as_dict()
        for problem in verdict.problems
        if not (
            problem.kind == preflight_module.RECORD_MISSING
            and problem.detail == CYCLE_RECORD
        )
    ]
    if unexpected:
        problems.append(f"the preflight does not read the tag: {unexpected[:4]}")
    from scripts.panel.run_cycle import (
        Config,
        pipeline_problem,
        recorded_pipeline,
        unharvested,
    )

    cfg = Config(
        tag=destination.name,
        panel_file=destination / "unused-panel.txt",
        zeroshot_dir=destination / "unused-zeroshot",
        results_root=Path(results_root),
    )
    record = recorded_pipeline(cfg)
    if record is None:
        problems.append(f"{PIPELINE_RECORD} unreadable: the judges stage would stop")
    else:
        read = candidate if candidate is not None else record
        why = pipeline_problem(dict(read))
        if why is not None:
            problems.append(why)
    missing = unharvested(cfg, list(docs))
    if missing:
        problems.append(f"{len(missing)} document(s) unharvested: {', '.join(missing)}")
    from scripts.dataset import judge_panel as judged

    health: Dict[str, Any] = {}
    degraded: List[str] = []
    for doc in docs:
        try:
            state = read_record(cfg.states_dir / f"state_full_{doc}.json")
            signature = read_record(cfg.signatures_dir / f"signature_{doc}.json")
            text = judged.pipeline_text_from_state(state, signature)
            row = judged.arm_health(state, signature)
        except Refused as exc:
            problems.append(f"{doc}: {exc}")
            continue
        health[doc] = {
            "chars": len(text),
            "digest": _digest(text),
            "pipeline_degraded": bool(row.get("pipeline_degraded")),
            "cut_acts": row.get("cut_acts"),
            "empty_acts": row.get("empty_acts"),
        }
        if row.get("pipeline_degraded"):
            degraded.append(doc)
    threshold = judged.DEGRADED_ARM_REFUSAL_THRESHOLD
    return {
        "ok": not problems,
        "problems": problems,
        "preflight_problems": len(verdict.problems),
        "documents": len(health),
        "health": health,
        "guard": {
            "degraded_arms": len(degraded),
            "degraded": degraded,
            "threshold": threshold,
            "would_refuse": len(degraded) >= threshold,
        },
    }


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------


def main(
    cycle_dir: Path,
    destination: Path,
    panel: Optional[Sequence[str]] = None,
    argv: Optional[Sequence[str]] = None,
    *,
    results_root: Path = c.RESULTS_ROOT,
    probe: bool = False,
) -> int:
    """Run the replay and print its summary; the report follows the tag.

    ``results_root`` is the run's own seam (:func:`run` already carries it): the
    launcher passes the cycle's, and no production caller passes anything.
    ``probe`` says the named panel is a declared subset (:func:`run`), which the
    preflight has to know before it can let a partial panel through.
    """
    invoked = list(sys.argv[1:] if argv is None else argv)
    report = run(
        Path(cycle_dir),
        Path(destination),
        panel,
        invoked,
        results_root=results_root,
        probe=probe,
    )
    tag = Path(destination)
    if tag.is_dir():
        (tag / REPORT).write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        summary = {
            key: report.get(key)
            for key in ("ok", "stage", "counts", "probe", "refused", "refusals")
            if report.get(key) is not None
        }
        print(json.dumps(summary, indent=1, sort_keys=True))
        return EXIT_OK if report.get("ok") else EXIT_REFUSED
    print(
        json.dumps(
            {
                key: report.get(key)
                for key in ("ok", "stage", "refused", "refusals", "preflight", "gate")
                if report.get(key) is not None
            },
            indent=1,
            sort_keys=True,
        )
    )
    stage = report.get("stage")
    return EXIT_USAGE if stage in UNWRITTEN_STAGES else EXIT_REFUSED


def cli(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Live act replay of a harvested cycle: the acts re-run on the "
            "recorded states, and a tag the judges stage accepts."
        )
    )
    parser.add_argument("--cycle-dir", required=True, type=Path)
    parser.add_argument(
        "--dest",
        required=True,
        type=Path,
        help="<results_root>/panel_cycles/<name>, a directory that does not exist yet",
    )
    parser.add_argument("--panel-file", default=None, type=Path)
    parser.add_argument("--doc-ids", default=None)
    parser.add_argument(
        "--probe",
        action="store_true",
        help=(
            "the named panel is a declared subset of the cycle: the documents "
            "left out are named instead of refusing the run (the tag then "
            "carries one document, and a judges stage given the whole panel "
            "refuses it as unharvested)"
        ),
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    panel: Optional[List[str]] = None
    if args.panel_file is not None or args.doc_ids is not None:
        from scripts.dataset.panel_ids import parse_doc_ids

        panel = parse_doc_ids(
            args.doc_ids, None if args.panel_file is None else str(args.panel_file)
        )
        if not panel:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "stage": STAGE_PREFLIGHT,
                        "refused": (
                            "--panel-file/--doc-ids named no document: an empty "
                            "panel checks nothing"
                        ),
                    },
                    indent=1,
                    sort_keys=True,
                )
            )
            return EXIT_USAGE
    if args.probe and not panel:
        parser.error("--probe: needs --panel-file or --doc-ids to name the subset")
    return main(args.cycle_dir, args.dest, panel, sys.argv[1:], probe=bool(args.probe))


if __name__ == "__main__":
    sys.exit(cli())
