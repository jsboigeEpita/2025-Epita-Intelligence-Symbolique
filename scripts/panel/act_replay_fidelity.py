"""Act-replay fidelity witness: does the recorded state reproduce the render?

    python scripts/panel/act_replay_fidelity.py --cycle-dir \\
        argumentation_analysis/evaluation/results/panel_cycles/c22 \\
        [--renders-dir argumentation_analysis/evaluation/results/campaign_2841_lecture] \\
        [--panel-file argumentation_analysis/evaluation/results/panel_v1/panel.txt] \\
        [--out argumentation_analysis/evaluation/results/panel_cycles/c22/act_replay_fidelity.json]

#3658 item 46c. The act replay re-runs the three acts of a harvested cycle and
judges the render that follows. Before any paid call, this witness answers,
per document, offline — no call, no network, no JVM:

1. **Which inputs the render has.** Each top-level field of the state (then of
   the signature) is perturbed in memory, one key at a time — emptied (zeroed,
   for a number) and given a marker, since one perturbation cannot see a
   conditional input — and the judged text is produced again. A field under
   which the text moves IS an input; the measured set is compared with the
   set read off the producer's source (``DECLARED_*`` below). A field that
   moves the render without being declared is a HIDDEN INPUT — an equality
   that would not survive another seat. A declared field the record does not
   carry is INSERTED for its test (a gate field only reads as an input once
   it is present), and a declared field that moves nothing is reported: on
   that record it carries nothing the render prints — an empty container, or
   a field whose reading another field's value gates.

2. **Whether the harvest round-trips byte for byte.** Three constructions of
   the same text must be the SAME string: the judge's entry point on the
   harvested records, the fiche caller on the same records (``doc_facts`` →
   ``pipeline_full_text``), and the replay path — the records through a JSON
   round trip, the recorded act texts written back at the state's root, which
   is what the driver will hand the judge. With ``--renders-dir`` the
   reference is the harvested FICHE itself: its ``## Le pipeline, en texte
   intégral`` section is the producer's own output, compared with the rebuilt
   text byte for byte (no normalisation, no whitespace folding). On the two
   other engines' records (``conversation_real``, ``hierarchical_delegation``)
   the fiche caller does not route the provenance: the witness names that
   divergence of the two callers instead of certifying one text.

   The full state dump is the ONLY carrier of the act texts: the signature
   embeds the *sanitised* state, where each narrative field is reduced to
   ``{"length": N, "stripped": True}`` (``sanitize_state`` step 7; #2841
   guard 3). Those recorded lengths are a harvest-time witness of their own
   and are compared with the state file's texts.

3. **That the comparison can fail.** A synthetic act is altered in memory,
   a different text is injected through the replay path, and an anchor is
   inserted into one act of an anchored synthetic state — that last one moves
   the SHARED notes block too (#3393's fiche-wide registry), so a mismatch
   caused by renumbering is attributed instead of read as an act's own text.
   The sections that move are named by heading alignment, never by position:
   an act's change can add or remove the ``### `` headings inside its own
   text, which would shift a positional comparison for every later section.

4. **That no input lives outside the records.** Every digest is recomputed in
   a fresh process that inherits the boot variables only — no API key, no
   passphrase, no seat variable — and does not read the checkout's ``.env``:
   stubbing the file would mutate the seat, and dropping a name would not do,
   since the package's import-time auto-load refills it from the same file
   (#3682); so the child stubs the loader's own reader before any import. A
   difference is a hidden input that would make two seats disagree on the
   same cycle. A second child tampers with one act and must move that
   document's digest and no other — the proof that the child's digest really
   derives from the records.

Labels: ``--panel-file`` numbers the documents ``doc_A``… in the panel's
reading order, so stdout can be quoted on a GitHub-indexed surface. Without
it the ids are printed — the opaque ids the other instruments of
``scripts/panel/`` print, never a document's name, title or text.

Nothing is written outside a gitignored path; the report holds counts, key
names and sha256 digests, never a passage of the corpus. It opens with its
provenance header (#2353): the resolved route, the checkout's HEAD sha and
dirty flag, the exact command, the interpreter, the instrument's own sha256
and the model-call count — a cited report that cannot say which code produced
it can only be believed from another seat. Exit 0 = the harvest round-trips
and every control holds; 1 = a mismatch, a hidden input or a control that did
not fire; 2 = the instrument could not run as asked.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Optional, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.panel import _common as c  # noqa: E402

ACTS: Tuple[str, ...] = c.ACTS
SYNTHESIS = "narrative_synthesis"
QUESTION = "interpretive_question"
#: The four fields the producers print as acts sections, then the one printed
#: after both branches (``pipeline_full_text`` reads the question for every
#: document, non-argumentative ones included).
RENDER_INPUTS: Tuple[str, ...] = ACTS + (SYNTHESIS,)
TEXT_INPUTS: Tuple[str, ...] = RENDER_INPUTS + (QUESTION,)

#: The two headings ``render_fiche`` puts around the full-text section. They
#: are literals inside the renderer, not constants: the witness declares them
#: here and a unit test pins them against ``render_fiche``'s own output, so a
#: heading change reddens instead of silently emptying the extraction.
FICHE_SECTION_START = "## Le pipeline, en texte intégral"
FICHE_SECTION_END = "## La réponse zero-shot, intégrale"
NOTES_HEADING = "Notes du pipeline (ancres du run)"

#: The perturbation is a value the corpus cannot produce — it never quotes a
#: document, and it is never printed.
MARKER = " WITNESS_PERTURBATION"
MARKER_KEY = "__witness_perturbation__"

#: FB-18 anchors, as the producer spells them (``_ARTIFACT_ANCHOR_RE``): the
#: same pattern, declared here so the anchor census does not import the
#: renderer's private constant. A unit test compares the two on synthetic text.
ANCHOR_RE = re.compile(r"\[artifact:([^\]\s]+)\]")

BRANCH_ACTS = "acts"
BRANCH_CUT = "cut"
BRANCH_NON_ARGUMENTATIVE = "non_argumentative"
BRANCH_CONVERSATION_REAL = "conversation_real"
BRANCH_HIERARCHICAL_DELEGATION = "hierarchical_delegation"

#: The inputs read off the producer's source, per branch — ``pipeline_full_text``
#: and its two helpers (``render_cut_analysis_material``,
#: ``render_non_argumentative_reader_paragraph``), both other arm producers
#: (``conversation_real_full_text``, ``hierarchical_delegation_full_text``), and
#: the routing in ``judge_panel.pipeline_text_from_state``.
DECLARED_STATE_INPUTS: Dict[str, FrozenSet[str]] = {
    BRANCH_ACTS: frozenset(TEXT_INPUTS),
    # Every act key empty: the cut dump reads the upstream material instead.
    # The acts themselves stay inputs — their emptiness GATES the dump.
    BRANCH_CUT: frozenset(TEXT_INPUTS)
    | {
        "raw_text",
        "identified_arguments",
        "identified_fallacies",
        "stakes_and_stakeholders",
        "strategic_read",
        "historical_context",
    },
    # ``document_classification`` short-circuits the acts entirely; the reader
    # paragraph reads the metadata and the text, and the question still prints.
    BRANCH_NON_ARGUMENTATIVE: frozenset({"raw_text", "source_metadata", QUESTION}),
    BRANCH_CONVERSATION_REAL: frozenset(
        {"fallacies", "fallacies_count", "fol", "analysis_errors"}
    ),
    BRANCH_HIERARCHICAL_DELEGATION: frozenset(
        {
            "tasks",
            "task_counts",
            "objectives",
            "conclusion",
            "degraded",
            "degradation_reasons",
            "partial",
        }
    ),
}

DECLARED_SIGNATURE_INPUTS: Dict[str, FrozenSet[str]] = {
    # ``document_classification`` picks the branch and the non-argumentative
    # paragraph — it rides the signature's root only when the campaign
    # classified the document (#1909 slice 2), and the render reads it if
    # present; ``provenance.mode`` routes the two other engines; ``outcome``
    # only reaches the cut dump's intro.
    BRANCH_ACTS: frozenset({"document_classification", "provenance"}),
    BRANCH_CUT: frozenset({"document_classification", "provenance", "outcome"}),
    BRANCH_NON_ARGUMENTATIVE: frozenset({"document_classification", "provenance"}),
    BRANCH_CONVERSATION_REAL: frozenset({"provenance"}),
    BRANCH_HIERARCHICAL_DELEGATION: frozenset({"provenance"}),
}

#: Two signature fields GATE the producer instead of feeding it. Emptying
#: them leaves an argumentative document on its branch, so the generic
#: perturbation would read them as silent; these are the values that flip the
#: gate. ``provenance`` flips through its ``mode``.
_GATE_FLIPS: Dict[str, Tuple[str, ...]] = {
    "document_classification": (BRANCH_NON_ARGUMENTATIVE,),
    "provenance": (BRANCH_CONVERSATION_REAL, BRANCH_HIERARCHICAL_DELEGATION),
}

#: Passed as an argument, never read by any producer (``pipeline_full_text``
#: takes ``opaque_id`` and does not use it). Named so the report does not read
#: as an omission.
PASSED_UNREAD: Tuple[str, ...] = ("opaque_id",)

#: The two engines the judge's entry point routes to through ``provenance.mode``.
_ENGINE_BRANCHES: Tuple[str, ...] = (
    BRANCH_CONVERSATION_REAL,
    BRANCH_HIERARCHICAL_DELEGATION,
)

#: What the witness says on those engines' records. The fiche caller
#: (``render_fiche`` → ``pipeline_full_text``) does not route the provenance:
#: there the fiche prints the pipeline's acts vocabulary — four absence lines
#: — where the judge reads the engine's own text. That is a divergence of the
#: two callers, not a harvest that fails to round-trip: it is named, never
#: certified as one text.
FICHE_DOES_NOT_ROUTE = (
    "the fiche caller does not route this engine's provenance: the fiche "
    "prints the pipeline's acts vocabulary where the judge reads the "
    "engine's own text"
)

SYNTHETIC_STATE: Dict[str, Any] = {
    "act1_framing": "Acte I synthétique : le cadre inventé du témoin.",
    "act2_narrative": "Acte II synthétique : un récit inventé, sans document.",
    "act3_conclusion": "Acte III synthétique : une conclusion inventée.",
    "narrative_synthesis": "Synthèse synthétique inventée pour le témoin.",
    "interpretive_question": "Question synthétique inventée ?",
    "raw_text": "Texte synthétique inventé pour le témoin, sans corpus.",
}
SYNTHETIC_SIGNATURE: Dict[str, Any] = {
    "opaque_id": "corpus_witness",
    "document_classification": None,
    "outcome": {"status": "ok"},
    "provenance": {},
}

#: An anchored synthetic state: three inputs, three anchors, numbered 1..3 by
#: order of first appearance. Inserting one anchor at the head of act 1
#: renumbers all three and adds a fourth — in the act, in the two later
#: sections that carry one, and in the shared notes block.
ANCHORED_STATE: Dict[str, Any] = {
    "act1_framing": "Un cadre appuyé sur [artifact:alpha].",
    "narrative_synthesis": "Une synthèse appuyée sur [artifact:beta].",
    "interpretive_question": "Une question appuyée sur [artifact:gamma] ?",
}
ANCHOR_INSERTED = "[artifact:zeta] Un cadre appuyé sur [artifact:alpha]."


# ---------------------------------------------------------------------------
# The records
# ---------------------------------------------------------------------------


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _inner(record: Mapping[str, Any]) -> Dict[str, Any]:
    """The state level the producers read (``state.get("state") or state``)."""
    nested = record.get("state")
    return nested if isinstance(nested, dict) else dict(record)


def _present(state: Mapping[str, Any], key: str) -> bool:
    value = _inner(state).get(key)
    return isinstance(value, str) and bool(value)


def _with_root_value(record: Mapping[str, Any], key: str, value: Any) -> Dict[str, Any]:
    """A copy of ``record`` with ``key`` replaced at the level producers read.

    The copy is shallow and the nested state is copied too: the harvested
    record is never mutated by a perturbation.
    """
    candidate = dict(record)
    nested = candidate.get("state")
    if isinstance(nested, dict):
        nested = dict(nested)
        candidate["state"] = nested
        nested[key] = value
    else:
        candidate[key] = value
    return candidate


def load_records(
    cycle_dir: Path,
) -> Tuple[List[str], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """``(docs, states, signatures)`` of a harvested cycle, in id order."""
    cycle_dir = Path(cycle_dir)
    states_dir = cycle_dir / "states"
    signatures_dir = cycle_dir / "signatures"
    docs = c.docs_in(states_dir)
    states: Dict[str, Dict[str, Any]] = {}
    signatures: Dict[str, Dict[str, Any]] = {}
    for doc in docs:
        states[doc] = json.loads(
            c.state_path(states_dir, doc).read_text(encoding="utf-8")
        )
        sig_path = signatures_dir / f"signature_{doc}.json"
        signatures[doc] = (
            json.loads(sig_path.read_text(encoding="utf-8"))
            if sig_path.exists()
            else {}
        )
    return docs, states, signatures


def render_branch(state: Mapping[str, Any], signature: Mapping[str, Any]) -> str:
    """Which producer the judge's entry point routes this record to."""
    mode = ((signature or {}).get("provenance") or {}).get("mode")
    if mode == BRANCH_CONVERSATION_REAL:
        return BRANCH_CONVERSATION_REAL
    if mode == BRANCH_HIERARCHICAL_DELEGATION:
        return BRANCH_HIERARCHICAL_DELEGATION
    if (signature or {}).get("document_classification") == BRANCH_NON_ARGUMENTATIVE:
        return BRANCH_NON_ARGUMENTATIVE
    if any(_present(state, key) for key in RENDER_INPUTS):
        return BRANCH_ACTS
    return BRANCH_CUT


# ---------------------------------------------------------------------------
# The three constructions of the judged text
# ---------------------------------------------------------------------------


def judge_render(state: Mapping[str, Any], signature: Mapping[str, Any]) -> str:
    """The judge's own entry point (the one call the blind pass makes)."""
    from scripts.dataset.judge_panel import pipeline_text_from_state

    return pipeline_text_from_state(dict(state), dict(signature))


def fiche_render(state: Mapping[str, Any], signature: Mapping[str, Any]) -> str:
    """The fiche caller: ``doc_facts`` supplies the two signature fields."""
    from scripts.dataset.render_campaign_reading_folder import (
        doc_facts,
        pipeline_full_text,
    )

    facts = doc_facts(dict(signature), dict(state))
    return pipeline_full_text(
        _inner(state),
        facts.get("classification"),
        str(facts.get("opaque_id") or ""),
        facts.get("outcome") or {},
        chars=facts["chars"],
    )


def recorded_acts(state: Mapping[str, Any]) -> Dict[str, Any]:
    """The three act texts as the harvested state records them at its root."""
    st = _inner(state)
    return {key: st.get(key) for key in ACTS}


def replayed_state(
    state: Mapping[str, Any], acts: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    """The state a driver hands the judge: a JSON round trip, acts rewritten.

    The driver re-runs the acts and writes its result at the state's root; the
    round trip is what a save-then-reload does. ``acts`` defaults to the
    recorded texts — the identity replay, whose render must be the harvest's.
    """
    replay: Dict[str, Any] = json.loads(json.dumps(state, ensure_ascii=False))
    target = replay.get("state")
    if not isinstance(target, dict):
        target = replay
    target.update(recorded_acts(state) if acts is None else dict(acts))
    return replay


def replay_render(
    state: Mapping[str, Any],
    signature: Mapping[str, Any],
    acts: Optional[Mapping[str, Any]] = None,
) -> str:
    """The judged text the replay path produces for this record."""
    return judge_render(replayed_state(state, acts), signature)


# ---------------------------------------------------------------------------
# Byte-for-byte comparison, and where a difference sits
# ---------------------------------------------------------------------------


def split_sections(text: str) -> List[Tuple[str, str]]:
    """``(heading, body)`` for every ``### `` section, preamble first.

    The acts' own texts carry ``### `` headings of their own, so one act can
    hold several sections — which is why the comparison aligns headings
    instead of positions.
    """
    sections: List[Tuple[str, str]] = []
    heading = "(préambule)"
    lines: List[str] = []
    for line in text.split("\n"):
        if line.startswith("### "):
            sections.append((heading, "\n".join(lines)))
            heading = line[4:].strip()
            lines = [line]
        else:
            lines.append(line)
    sections.append((heading, "\n".join(lines)))
    return sections


def compare(reference: str, rebuilt: str) -> Dict[str, Any]:
    """Byte equality of two renders, with the offset and the sections that move.

    Bytes, not normalised text: a whitespace change, an NFC/NFD difference or
    a re-ordered note are mismatches, exactly as they would be for a reader.
    Sections are aligned BY HEADING (``difflib``) so a section an alteration
    adds or removes inside an act does not shift every later one.
    """
    left = reference.encode("utf-8")
    right = rebuilt.encode("utf-8")
    first_diff: Optional[int] = None
    limit = min(len(left), len(right))
    for offset in range(limit):
        if left[offset] != right[offset]:
            first_diff = offset
            break
    if first_diff is None and len(left) != len(right):
        first_diff = limit
    reference_sections = split_sections(reference)
    rebuilt_sections = split_sections(rebuilt)
    matcher = difflib.SequenceMatcher(
        a=[heading for heading, _ in reference_sections],
        b=[heading for heading, _ in rebuilt_sections],
        autojunk=False,
    )
    differing: List[str] = []
    only_in_reference: List[str] = []
    only_in_rebuilt: List[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                if reference_sections[i][1] != rebuilt_sections[j][1]:
                    differing.append(reference_sections[i][0])
            continue
        paired = min(i2 - i1, j2 - j1)
        for offset in range(paired):
            left_section = reference_sections[i1 + offset]
            right_section = rebuilt_sections[j1 + offset]
            if left_section[1] != right_section[1]:
                differing.append(left_section[0])
        only_in_reference.extend(
            heading for heading, _ in reference_sections[i1 + paired : i2]
        )
        only_in_rebuilt.extend(
            heading for heading, _ in rebuilt_sections[j1 + paired : j2]
        )
    return {
        "equal": left == right,
        "reference_chars": len(reference),
        "rebuilt_chars": len(rebuilt),
        "first_diff_offset": first_diff,
        "sections_differing": differing,
        "sections_only_in_reference": only_in_reference,
        "sections_only_in_rebuilt": only_in_rebuilt,
    }


# ---------------------------------------------------------------------------
# The inputs: measured by perturbation, compared with the declared sets
# ---------------------------------------------------------------------------


def perturbations(value: Any) -> List[Any]:
    """The perturbations tried on one value, each keeping its type.

    TWO of them, because one cannot see a CONDITIONAL input: a field the render
    prints only when a condition holds reads as silent under a perturbation
    that leaves the condition as it was (``raw_text`` decides whether an
    extract is quoted, and appending a marker keeps every extract quoted).
    Appending and emptying are the two cheapest questions "does the render
    read any of this?"; a container is emptied and refilled with a marker, a
    number moves by one and to zero, a boolean flips.
    """
    if isinstance(value, str):
        return [value + MARKER, ""] if value else [MARKER]
    if isinstance(value, dict):
        return [{}, {MARKER_KEY: MARKER}] if value else [{MARKER_KEY: MARKER}]
    if isinstance(value, list):
        return [[], [MARKER]] if value else [[MARKER]]
    if isinstance(value, bool):
        return [not value]
    if isinstance(value, (int, float)):
        # Two of them too: a number is often read as a threshold (``> 0``,
        # ``>= 1``), which ``+ 1`` never crosses from above — zero is a
        # number's emptiness.
        return [value + 1] if value == 0 else [value + 1, type(value)(0)]
    return [MARKER]


def _flip(key: str, value: Any) -> Any:
    """The perturbation that moves a GATE field to its other branch."""
    tokens = _GATE_FLIPS[key]
    if key == "document_classification":
        return tokens[0] if value != tokens[0] else MARKER
    provenance = dict(value) if isinstance(value, dict) else {}
    for token in tokens:
        if provenance.get("mode") != token:
            provenance["mode"] = token
            return provenance
    return provenance


def _read_level(record: Mapping[str, Any], at_read_level: bool) -> Dict[str, Any]:
    """The mapping a perturbation replaces a key in."""
    return dict(_inner(record)) if at_read_level else dict(record)


def _perturb_record(
    record: Mapping[str, Any],
    render_one: Callable[[Mapping[str, Any]], str],
    declared: FrozenSet[str],
    branch_of: Callable[[Mapping[str, Any]], str],
    at_read_level: bool,
) -> Dict[str, Dict[str, Any]]:
    """Per key: does replacing it move the render, or the branch it takes?

    Every key the record carries is tested, and every DECLARED key the record
    does not carry is inserted for its test: a gate the record omits is still
    an input of the render, and its absence must not read as silence. A key is
    sensitive as soon as ONE of its perturbations moves the text.
    """
    baseline = render_one(record)
    branch = branch_of(record)
    level = _read_level(record, at_read_level)
    results: Dict[str, Dict[str, Any]] = {}
    for key in sorted(set(level) | set(declared)):
        inserted = key not in level
        if inserted:
            replacements = [_flip(key, None) if key in _GATE_FLIPS else MARKER]
        elif key in _GATE_FLIPS:
            replacements = [_flip(key, level[key])]
        else:
            replacements = perturbations(level[key])
        sensitive = False
        crash: Optional[str] = None
        branch_changed = False
        for replacement in replacements:
            candidate = (
                _with_root_value(record, key, replacement)
                if at_read_level
                else {**record, key: replacement}
            )
            try:
                rendered = render_one(candidate)
            except Exception as exc:  # noqa: BLE001 — a render that dies read it
                crash = crash or type(exc).__name__
                sensitive = True
                continue
            if rendered != baseline:
                sensitive = True
            branch_changed = branch_changed or branch_of(candidate) != branch
        results[key] = {
            "sensitive": sensitive,
            "crash": crash,
            "inserted": inserted,
            "branch_changed": branch_changed,
        }
    return results


def input_census(
    state: Mapping[str, Any], signature: Mapping[str, Any]
) -> Dict[str, Any]:
    """The measured inputs of the render on one record, against the declared.

    ``undeclared`` is the failure the witness exists to surface: something
    outside the declared producer's inputs reaches the judged text, so the
    text is not a function of the records a replay can carry.
    """
    branch = render_branch(state, signature)
    state_rows = _perturb_record(
        state,
        lambda rec: judge_render(rec, signature),
        DECLARED_STATE_INPUTS[branch],
        lambda rec: render_branch(rec, signature),
        at_read_level=True,
    )
    signature_rows = _perturb_record(
        signature,
        lambda sig: judge_render(state, sig),
        DECLARED_SIGNATURE_INPUTS[branch],
        lambda sig: render_branch(state, sig),
        at_read_level=False,
    )

    def _pack(
        rows: Mapping[str, Dict[str, Any]],
        declared: FrozenSet[str],
        present: FrozenSet[str],
    ) -> Dict[str, Any]:
        sensitive = {key for key, row in rows.items() if row["sensitive"]}
        return {
            "measured": sorted(sensitive),
            "declared": sorted(declared),
            "undeclared": sorted(sensitive - declared),
            "declared_silent": sorted(declared - sensitive),
            "absent_from_record": sorted(declared - present),
            "gate_keys": sorted(
                key for key, row in rows.items() if row.get("branch_changed")
            ),
            "inserted": sorted(key for key, row in rows.items() if row.get("inserted")),
            "crashed": sorted(key for key, row in rows.items() if row.get("crash")),
        }

    return {
        "branch": branch,
        "state": _pack(
            state_rows,
            DECLARED_STATE_INPUTS[branch],
            frozenset(_inner(state)),
        ),
        "signature": _pack(
            signature_rows,
            DECLARED_SIGNATURE_INPUTS[branch],
            frozenset(signature),
        ),
        "passed_unread": [
            key
            for key in PASSED_UNREAD
            if not signature_rows.get(key, {}).get("sensitive")
        ],
    }


# ---------------------------------------------------------------------------
# The signature's own record of the harvest
# ---------------------------------------------------------------------------


def recorded_lengths(
    state: Mapping[str, Any], signature: Mapping[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """The signature's sanitised state against the state file, per text input.

    The full state dump is the only carrier of the act texts (#2841 guard 3):
    the signature embeds ``{"length": N, "stripped": True}`` in their place.
    A recorded length is a harvest-time witness that the dump still holds the
    text the signature was written from; a field the sanitiser does not reduce
    rides verbatim and is compared as text.
    """
    st = _inner(state)
    recorded = signature.get("state")
    recorded = recorded if isinstance(recorded, dict) else {}
    rows: Dict[str, Dict[str, Any]] = {}
    for key in TEXT_INPUTS:
        raw = st.get(key)
        text = raw if isinstance(raw, str) else ""
        entry = recorded.get(key)
        if isinstance(entry, str):
            rows[key] = {
                "kind": "text",
                "state_chars": len(text),
                "signature_chars": len(entry),
                "equal": entry == text,
            }
        elif isinstance(entry, dict) and isinstance(entry.get("length"), int):
            rows[key] = {
                "kind": "length",
                "state_chars": len(text),
                "signature_chars": entry["length"],
                "equal": entry["length"] == len(text),
            }
        else:
            rows[key] = {
                "kind": None,
                "state_chars": len(text),
                "signature_chars": None,
                "equal": None,
            }
    return rows


# ---------------------------------------------------------------------------
# The controls: the comparison must be able to fail
# ---------------------------------------------------------------------------


def synthetic_control() -> Dict[str, Any]:
    """The dispatch's control, on invented material: identity, then alteration.

    Nothing here touches the corpus: a synthetic act is altered in memory, a
    different text is injected in its place through the replay path, and an
    anchor is inserted at the head of an anchored state. The identity replay
    must hold, every alteration must break it, the altered act's own section
    must be the one that moves, and the anchor insertion must move the act
    that carries it, every anchored section after it (each is renumbered) and
    the shared notes block.
    """
    state = dict(SYNTHETIC_STATE)
    signature = dict(SYNTHETIC_SIGNATURE)
    reference = judge_render(state, signature)
    identity = compare(reference, replay_render(state, signature))

    altered = dict(state)
    altered["act2_narrative"] = (
        state["act2_narrative"] + " Une phrase ajoutée en mémoire."
    )
    alteration = compare(reference, judge_render(altered, signature))

    exchanged_acts = {**recorded_acts(state), "act3_conclusion": MARKER}
    exchange = compare(reference, replay_render(state, signature, acts=exchanged_acts))

    anchored = dict(ANCHORED_STATE)
    anchored_reference = judge_render(anchored, signature)
    renumbered = dict(anchored)
    renumbered["act1_framing"] = ANCHOR_INSERTED
    anchor_insertion = compare(anchored_reference, judge_render(renumbered, signature))

    return {
        "identity": identity,
        "altered_act": alteration,
        "exchanged_act": exchange,
        "anchor_inserted": anchor_insertion,
        "ok": (
            identity["equal"]
            and not alteration["equal"]
            and not exchange["equal"]
            and not anchor_insertion["equal"]
            and alteration["sections_differing"] == ["Acte II — récit"]
            and exchange["sections_differing"] == ["Acte III — conclusion"]
            and anchor_insertion["sections_differing"]
            == [
                "Acte I — cadrage",
                "Synthèse narrative",
                "Question interprétative",
                NOTES_HEADING,
            ]
        ),
    }


def branch_controls(
    state: Mapping[str, Any], signature: Mapping[str, Any], reference: str
) -> Dict[str, Any]:
    """Does this record's own branch move when its input is replaced?

    The control of one document is the input its branch actually reads: an act
    for the acts branch, the metadata block for a non-argumentative document.
    An act injected into a non-argumentative document is recorded too — and it
    moves nothing, which is the branch, not a hole in the comparison.
    """
    branch = render_branch(state, signature)
    controls: Dict[str, Any] = {"branch": branch, "per_act": {}}
    for act in ACTS:
        candidate = _with_root_value(state, act, MARKER)
        controls["per_act"][act] = compare(
            reference, judge_render(candidate, signature)
        )

    if branch == BRANCH_NON_ARGUMENTATIVE:
        candidate = _with_root_value(state, "source_metadata", {MARKER_KEY: MARKER})
        controls["branch_control"] = {
            "input": "source_metadata",
            **compare(reference, judge_render(candidate, signature)),
        }
    elif branch in (BRANCH_CONVERSATION_REAL, BRANCH_HIERARCHICAL_DELEGATION):
        # The witness does not perturb these engines' adapter dicts: the act
        # replay is not their path, and the census above still runs on them.
        controls["branch_control"] = {"input": None, "equal": None, "skipped": True}
        controls["ok"] = True
        return controls
    else:
        first_present = next((act for act in ACTS if _present(state, act)), ACTS[0])
        controls["branch_control"] = {
            "input": first_present,
            **controls["per_act"][first_present],
        }

    controls["ok"] = controls["branch_control"]["equal"] is False
    return controls


# ---------------------------------------------------------------------------
# A harvested fiche is the reference, when one exists
# ---------------------------------------------------------------------------


def fiche_full_text(fiche: str) -> Optional[str]:
    """The ``## Le pipeline, en texte intégral`` section of a harvested fiche."""
    start = fiche.find(FICHE_SECTION_START + "\n\n")
    if start < 0:
        return None
    body = fiche[start + len(FICHE_SECTION_START) + 2 :]
    end = body.find("\n" + FICHE_SECTION_END)
    if end < 0:
        return None
    return body[:end]


def find_fiches(renders_dir: Path, doc: str) -> List[Path]:
    """The fiches a reading folder holds for one document (``NN_<id>_<title>``)."""
    matches: List[Path] = []
    for path in sorted(Path(renders_dir).rglob("*.md")):
        stem = path.stem
        if len(stem) > 3 and stem[:2].isdigit() and stem[2] == "_":
            stem = stem[3:]
        if stem == doc or stem.startswith(doc + "_"):
            matches.append(path)
    return matches


# ---------------------------------------------------------------------------
# The purity check: the same digests away from this process
# ---------------------------------------------------------------------------

_CHILD = """
import json, os, sys
import dotenv
_start_env = set(os.environ)
# Before ANY import of the package: the loader's own reader is stubbed, so
# the checkout's .env fills nothing here (the parent's process did fill it).
# The stub is the control's object: without it the import MUST read the file,
# or "read no .env" would be a blind instrument's silence.
if sys.argv[2] == "stub":
    dotenv.dotenv_values = lambda *args, **kwargs: {}
from pathlib import Path
from scripts.panel import act_replay_fidelity as w
inherited = sorted(
    name
    for name in _start_env
    if name not in w._BOOT_ENV_KEYS and not name.startswith("PYTHON")
)
if inherited:
    raise SystemExit("the child inherited a seat variable: " + ",".join(inherited))
job = json.loads(sys.argv[1])
docs, states, signatures = w.load_records(Path(job["cycle_dir"]))
labels = job.get("labels") or {}
tamper = job.get("tamper") or [None, None]
digests = {}
for doc in docs:
    state = states[doc]
    if tamper[0] is not None and doc == tamper[0]:
        state = w._with_root_value(state, tamper[1], w.MARKER)
    digests[labels.get(doc, doc)] = w._digest(w.judge_render(state, signatures[doc]))
print("WITNESS-JSON " + json.dumps({
    "digests": digests,
    "start_env": len(_start_env),
    "added_after_import": sorted(set(os.environ) - _start_env),
}, sort_keys=True))
"""

_CHILD_PREFIX = "WITNESS-JSON "

#: What Python needs to start: never a variable a producer could read.
_BOOT_ENV_KEYS = (
    "SYSTEMROOT",
    "WINDIR",
    "PATH",
    "TEMP",
    "TMP",
    "COMSPEC",
    "PATHEXT",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "HOME",
    "APPDATA",
    "LOCALAPPDATA",
    "LANG",
    "LC_ALL",
    "TZ",
    "NUMBER_OF_PROCESSORS",
)


def dotenv_names() -> List[str]:
    """The variable names the checkout's root ``.env`` can put in ``os.environ``.

    Names only: no value is read into this process, let alone printed.
    """
    from dotenv import dotenv_values

    path = c.REPO_ROOT / ".env"
    if not path.exists():
        return []
    values = dotenv_values(dotenv_path=str(path))
    return sorted(name for name, value in values.items() if value is not None)


def child_env() -> Dict[str, str]:
    """The environment a fresh child starts with: boot variables, nothing else."""
    env = {name: os.environ[name] for name in _BOOT_ENV_KEYS if os.environ.get(name)}
    env["PYTHONPATH"] = str(c.REPO_ROOT)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def fresh_process_digests(
    cycle_dir: Path,
    labels: Mapping[str, str],
    tamper: Optional[Tuple[str, str]] = None,
    stub: bool = True,
    timeout: int = 600,
) -> Dict[str, Any]:
    """The judge's digests recomputed in a child that is not this seat.

    ``stub=False`` lets the child read the checkout's ``.env``: it is the
    control of the stub, never a measurement.
    """
    job = {
        "cycle_dir": str(cycle_dir),
        "labels": dict(labels),
        "tamper": None if tamper is None else list(tamper),
    }
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, json.dumps(job), "stub" if stub else "read"],
        capture_output=True,
        text=True,
        env=child_env(),
        cwd=str(c.REPO_ROOT),
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "the fresh process failed: " + (proc.stderr or "").strip()[-800:]
        )
    lines = [
        line[len(_CHILD_PREFIX) :]
        for line in (proc.stdout or "").splitlines()
        if line.startswith(_CHILD_PREFIX)
    ]
    if not lines:
        raise RuntimeError("the fresh process printed no digest")
    child: Dict[str, Any] = json.loads(lines[-1])
    return child


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------


def text_rows(state: Mapping[str, Any], keys: Tuple[str, ...]) -> Dict[str, Any]:
    """Presence, length, digest and anchor count of each text input, never text."""
    st = _inner(state)
    rows: Dict[str, Any] = {}
    for key in keys:
        raw = st.get(key)
        text = raw if isinstance(raw, str) else ""
        rows[key] = {
            "present": bool(text.strip()),
            "chars": len(text),
            "sha256": _digest(text) if text else None,
            "anchors": len(ANCHOR_RE.findall(text)),
        }
    return rows


def notes_rendered(reference: str) -> int:
    """How many note lines the shared block prints in a render."""
    section = dict(split_sections(reference)).get(NOTES_HEADING, "")
    return sum(1 for line in section.split("\n") if line.startswith("- "))


def witness_document(
    state: Mapping[str, Any],
    signature: Mapping[str, Any],
    fiche_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Everything the witness says about one document."""
    from scripts.dataset.judge_panel import arm_health

    judge_text = judge_render(state, signature)
    fiche_caller = fiche_render(state, signature)
    replay_text = replay_render(state, signature)
    harvested_judge = None if fiche_text is None else compare(fiche_text, judge_text)
    harvested = None if fiche_text is None else compare(fiche_text, replay_text)
    return {
        "branch": render_branch(state, signature),
        "inputs_present": text_rows(state, TEXT_INPUTS),
        "recorded_lengths": recorded_lengths(state, signature),
        "notes_rendered": notes_rendered(judge_text),
        "health": arm_health(dict(state), dict(signature)),
        "reference": {
            "source": (
                "harvested-fiche" if fiche_text is not None else "judge-entry-point"
            ),
            "chars": len(judge_text if fiche_text is None else fiche_text),
            "sha256": _digest(judge_text if fiche_text is None else fiche_text),
        },
        "callers": {
            "judge": {"chars": len(judge_text), "sha256": _digest(judge_text)},
            "fiche": {"chars": len(fiche_caller), "sha256": _digest(fiche_caller)},
            "replay": {"chars": len(replay_text), "sha256": _digest(replay_text)},
        },
        "diff": {
            "judge_vs_replay": compare(judge_text, replay_text),
            "fiche_vs_replay": compare(fiche_caller, replay_text),
            "harvested_vs_judge": harvested_judge,
            "harvested_vs_replay": harvested,
        },
        "equal": {
            "judge_vs_replay": judge_text == replay_text,
            "fiche_vs_replay": fiche_caller == replay_text,
            "harvested_vs_judge": (
                None if harvested_judge is None else harvested_judge["equal"]
            ),
            "harvested_vs_replay": None if harvested is None else harvested["equal"],
        },
        "inputs": input_census(state, signature),
        "controls": branch_controls(state, signature, judge_text),
    }


def _failures(entry: Mapping[str, Any]) -> List[str]:
    """Why one document's witness does not hold (empty = it holds)."""
    reasons: List[str] = []
    for name, equal in entry["equal"].items():
        if equal is not False:
            continue
        if (
            name == "fiche_vs_replay"
            and entry.get("branch") in _ENGINE_BRANCHES
            and entry["equal"].get("judge_vs_replay") is True
        ):
            reasons.append(FICHE_DOES_NOT_ROUTE)
        else:
            reasons.append(f"render mismatch ({name})")
    for scope in ("state", "signature"):
        for key in entry["inputs"][scope]["undeclared"]:
            reasons.append(f"hidden input ({scope}.{key})")
    for scope in ("state", "signature"):
        for key in entry["inputs"][scope]["crashed"]:
            reasons.append(f"render died on the perturbed {scope}.{key}")
    for key, row in entry["recorded_lengths"].items():
        if row["equal"] is False:
            reasons.append(f"the signature recorded another {key}")
    if entry["controls"].get("ok") is not True:
        reasons.append("branch control did not fire")
    return reasons


def _git(root: Path, *args: str) -> Optional[str]:
    """One git query, ``None`` when git is absent or the query fails.

    Attribution is not the measurement: a seat without git still measures, and
    its report says the code identity is unknown instead of omitting it.
    """
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.strip()


def provenance(
    argv: List[str],
    cycle_dir: Path,
    renders_dir: Optional[Path],
    panel_file: Optional[Path],
    labels: bool,
) -> Dict[str, Any]:
    """The header #2353 requires — which code, which route, which command.

    Nothing here is corpus-derived: paths, shas, an interpreter version and a
    count. The report stays quotable on a GitHub-indexed surface.
    """
    root = Path(__file__).resolve().parents[2]
    head = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain")
    try:
        instrument = Path(__file__).resolve().relative_to(root).as_posix()
    except ValueError:  # pragma: no cover — the instrument outside a checkout
        instrument = str(Path(__file__).resolve())
    return {
        "command": ["python", instrument] + list(argv),
        "code": {
            "root": str(root),
            "head": head,
            "dirty": None if status is None else bool(status),
            "instrument_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "executable": sys.executable,
        },
        "route": {
            "cycle_dir": str(cycle_dir.resolve()),
            "renders_dir": None if renders_dir is None else str(renders_dir.resolve()),
            "panel_file": None if panel_file is None else str(panel_file.resolve()),
            "labels": "panel order" if labels else "opaque ids",
        },
        "python": sys.version.split()[0],
        "llm_requests": 0,
        "units": "characters, counts only, never text",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--renders-dir", type=Path, default=None)
    parser.add_argument("--panel-file", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--no-fresh-process", action="store_true")
    args = parser.parse_args(argv)

    if not (args.cycle_dir / "states").is_dir():
        print(f"no states/ under {args.cycle_dir} — nothing to witness")
        return 2
    if args.out is not None:
        try:
            c.ensure_gitignored(args.out)
        except c.OutputRefused as exc:
            print(f"refused: {exc}")
            return 2

    docs, states, signatures = load_records(args.cycle_dir)
    labels: Dict[str, str] = {}
    ordered = docs
    if args.panel_file is not None:
        panel = c.read_panel(args.panel_file) or []
        labels = {
            doc: f"doc_{chr(ord('A') + index)}" for index, doc in enumerate(panel)
        }
        absent = [labels[doc] for doc in panel if doc not in states]
        if absent:
            print(f"panel ids without a harvested state: {absent}")
        ordered = [doc for doc in panel if doc in states] + [
            doc for doc in docs if doc not in panel
        ]

    print(
        f"documents witnessed: {len(docs)}; labels: {'panel order' if labels else 'ids'}"
    )
    if args.renders_dir is None:
        print(
            "reference: the judge's entry point on the harvested records "
            "(no --renders-dir: no harvested fiche is compared)"
        )

    header = provenance(
        list(sys.argv[1:] if argv is None else argv),
        args.cycle_dir,
        args.renders_dir,
        args.panel_file,
        bool(labels),
    )
    report: Dict[str, Any] = {
        "provenance": header,
        "cycle_dir": str(args.cycle_dir),
        "renders_dir": None if args.renders_dir is None else str(args.renders_dir),
        "documents": {},
        "synthetic": synthetic_control(),
        "fresh_process": None,
    }
    head = header["code"]["head"]
    print(
        f"code: {head[:12] if head else 'unknown (git gave no HEAD)'}"
        f"{', uncommitted changes' if header['code']['dirty'] else ''}; "
        f"python {header['python']}; model calls: {header['llm_requests']}"
    )
    print("command: " + " ".join(header["command"]))
    failed = not report["synthetic"]["ok"]
    if failed:
        print("synthetic control: FAILED — the comparison itself is not sound")
    else:
        print("synthetic control: identity holds, the three alterations break it")

    for doc in ordered:
        label = labels.get(doc, doc)
        fiche_text: Optional[str] = None
        if args.renders_dir is not None:
            matches = find_fiches(args.renders_dir, doc)
            if len(matches) == 1:
                fiche_text = fiche_full_text(matches[0].read_text(encoding="utf-8"))
            if fiche_text is None:
                print(
                    f"{label}: no readable fiche ({len(matches)} match(es)) — "
                    "the harvested-fiche comparison did not run on this document"
                )
        entry = witness_document(states[doc], signatures[doc], fiche_text)
        reasons = _failures(entry)
        if args.renders_dir is not None and fiche_text is None:
            reasons.append("no readable harvested fiche")
        entry["failures"] = reasons
        report["documents"][label] = entry
        failed = failed or bool(reasons)
        print(
            label,
            json.dumps(
                {
                    "branch": entry["branch"],
                    "acts_present": sum(
                        1 for key in ACTS if entry["inputs_present"][key]["present"]
                    ),
                    "anchors_in_acts": sum(
                        entry["inputs_present"][key]["anchors"] for key in ACTS
                    ),
                    "notes": entry["notes_rendered"],
                    "degraded": entry["health"]["pipeline_degraded"],
                    "equal": entry["equal"],
                    "undeclared": entry["inputs"]["state"]["undeclared"]
                    + entry["inputs"]["signature"]["undeclared"],
                    "control": entry["controls"].get("ok"),
                    "render_sha256": entry["callers"]["replay"]["sha256"][:12],
                    "failures": reasons,
                },
                ensure_ascii=False,
            ),
        )

    if not args.no_fresh_process and docs:
        try:
            child = fresh_process_digests(args.cycle_dir, labels)
        except Exception as exc:  # noqa: BLE001 — an instrument that cannot run says so
            report["fresh_process"] = {"error": str(exc)[-800:]}
            failed = True
            print(f"fresh process: FAILED — {str(exc)[-300:]}")
        else:
            child_digests: Dict[str, str] = child["digests"]
            same = {
                label: child_digests.get(label) == entry["callers"]["judge"]["sha256"]
                for label, entry in report["documents"].items()
            }
            from_dotenv = sorted(set(child["added_after_import"]) & set(dotenv_names()))
            fresh: Dict[str, Any] = {
                "same": same,
                "start_env": child["start_env"],
                "added_after_import": child["added_after_import"],
                "added_from_dotenv": from_dotenv,
            }
            report["fresh_process"] = fresh
            if from_dotenv:
                failed = True
                print(
                    "fresh process: the child's import read the .env —",
                    from_dotenv,
                )
            if all(same.values()):
                print(
                    f"fresh process: {len(same)} digest(s) reproduced; the child "
                    f"started with {child['start_env']} variable(s) and read no .env "
                    f"({len(dotenv_names())} name(s) declared there)"
                )
            else:
                failed = True
                print(
                    "fresh process: digests DIFFER —",
                    sorted(label for label, ok in same.items() if not ok),
                )
            tamper_doc = next(
                (
                    doc
                    for doc in ordered
                    if render_branch(states[doc], signatures[doc]) == BRANCH_ACTS
                ),
                None,
            )
            if tamper_doc is not None and all(same.values()):
                tamper_label = labels.get(tamper_doc, tamper_doc)
                try:
                    tampered = fresh_process_digests(
                        args.cycle_dir, labels, tamper=(tamper_doc, "act1_framing")
                    )
                except Exception as exc:  # noqa: BLE001
                    fresh["tamper_control"] = {"error": str(exc)[-400:]}
                    failed = True
                    print(f"fresh process tamper control: FAILED — {str(exc)[-200:]}")
                else:
                    tampered_digests: Dict[str, str] = tampered["digests"]
                    others = [label for label in child_digests if label != tamper_label]
                    control = {
                        "label": tamper_label,
                        "input": "act1_framing",
                        "differs": tampered_digests.get(tamper_label)
                        != child_digests.get(tamper_label),
                        "others_unchanged": all(
                            tampered_digests.get(label) == child_digests.get(label)
                            for label in others
                        ),
                    }
                    fresh["tamper_control"] = control
                    if not (control["differs"] and control["others_unchanged"]):
                        failed = True
                        print("fresh process tamper control: FAILED —", control)
                    else:
                        print(
                            f"fresh process tamper control: one act moved "
                            f"{tamper_label}'s digest and no other"
                        )

            names = dotenv_names()
            if names and all(same.values()):
                try:
                    unmasked = fresh_process_digests(args.cycle_dir, labels, stub=False)
                except Exception as exc:  # noqa: BLE001
                    fresh["stub_control"] = {"error": str(exc)[-400:]}
                    failed = True
                    print(f"fresh process stub control: FAILED — {str(exc)[-200:]}")
                else:
                    seen = sorted(set(unmasked["added_after_import"]) & set(names))
                    fresh["stub_control"] = {"names_filled_without_the_stub": seen}
                    if not seen:
                        failed = True
                        print(
                            "fresh process stub control: FAILED — without the stub "
                            "the import still filled no .env name, so reading no "
                            ".env is not measurable here"
                        )
                    else:
                        print(
                            "fresh process stub control: without the stub the "
                            f"import fills {len(seen)} .env name(s) — a read is "
                            "visible to this check"
                        )

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"report: {args.out}")

    if failed:
        print("VERDICT: MISMATCH — read the failures above")
        return 1
    held = len(report["documents"])
    if args.renders_dir is None:
        print(
            f"VERDICT: {held} document(s) — the harvested records give ONE text "
            "through the judge, fiche and replay constructions; every input is "
            "declared and every control fires; no harvested fiche was supplied, "
            "the fiche-file comparison did not run"
        )
    else:
        print(
            f"VERDICT: {held} document(s) — the harvested fiches are reproduced "
            "byte for byte by the replay path"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
