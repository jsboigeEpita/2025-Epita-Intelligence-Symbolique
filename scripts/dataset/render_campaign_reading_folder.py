"""#2841 — the reading folder of the corpus campaign, for a human reader.

The campaign's own artifacts (stripped signatures, full state dumps,
zero-shot records) are machine shapes: the acts live in one file, the
counts in another, the answers in a third. This producer assembles them
into ONE folder a reader opens and reads without a tool — the metric
mandate's final judge is the perception of the text, and the campaign
report alone is a report ABOUT the output (#2353).

No network, no LLM, no re-run: the folder presents the campaign AS IT
RAN (anti-pendule, coordinator dispatch R1105). Every number is read
from an artifact — nothing is copied from a report — and per-document
costs are recomputed from the measured per-phase tokens through the
#3095 price table, the same instrument the campaign's usage line used.

Usage (PYTHONPATH is required — the repo root is not on sys.path for a
plain script run):

    PYTHONPATH=. python scripts/dataset/render_campaign_reading_folder.py \
        [--out argumentation_analysis/evaluation/results/campaign_2841_lecture]

Inputs (all local, all gitignored):

    analysis_kb/state_dumps/state_full_<opaque_id>.json   (the complete state — the ONLY place the acts survive in full)
    analysis_kb/signatures/signature_<opaque_id>.json     (counts, metadata, wall-clock, outcome)
    argumentation_analysis/evaluation/results/zeroshot_2841/<opaque_id>.json  (the zero-shot answer, verbatim)

Output layout (gitignored — and this producer refuses to write anywhere
a tracked path could live):

    <out>/
        00_LIRE_D_ABORD.md        — what the campaign is, what it establishes, reading order
        01_tableau_corpus.md      — one line per document, outliers flagged
        02_rendus/NN_<opaque>.md  — the readable render, reading order, acts + zero-shot side by side
        03_defauts_connus.md      — already-tracked defects, so the reader does not rediscover them
        04_annexes/               — signatures + full states + zero-shot records, for verification
        inondation_extraction.md  — extracted arguments vs document length (the flood, measured)

The output is PRIVATE: real speaker names and titles are allowed in it
(dataset privacy rule 4 — the frontier is GitHub indexation, and this
tree never reaches git). The SCRIPT itself carries opaque ids only.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

STATES_DIR = REPO_ROOT / "analysis_kb" / "state_dumps"
SIGNATURES_DIR = REPO_ROOT / "analysis_kb" / "signatures"
ZEROSHOT_DIR = (
    REPO_ROOT / "argumentation_analysis" / "evaluation" / "results" / "zeroshot_2841"
)
DEFAULT_OUT = (
    REPO_ROOT
    / "argumentation_analysis"
    / "evaluation"
    / "results"
    / "campaign_2841_lecture"
)
# The only tree this producer may write to (#2353 rule 1: a producer must
# refuse to write to a path git would track).
RESULTS_ROOT = REPO_ROOT / "argumentation_analysis" / "evaluation" / "results"

# #3393 — the workflow name is an internal identifier (the runner's own
# vocabulary); the fiche's header line says what the run DID, in reader
# words. A name the table does not carry keeps the raw id — traceable,
# never dropped.
WORKFLOW_LABELS_FR = {
    "spectacular": "restitution en quatre actes",
    "light": "analyse allégée",
    "standard": "analyse standard",
    "full": "analyse complète",
}

#: The run's terminal status, under the reader's vocabulary (#3392). The
#: classification id is machine grammar (`non_argumentative`); the reader
#: of that fiche meets it in the very header. The raw id stays as the
#: fallback — traceable, never dropped.
STATUS_LABELS_FR = {
    "ok": "analysé",
    "non_argumentative": "document non-argumentatif",
    "failed": "échec",
    "blocked": "bloqué",
    "skipped": "ignoré",
}

# The pricing key default for direct calls. main() never uses it as a
# fallback: the run's model is resolved from the zero-shot provenance
# before the first fact is built, and a provenance that names no model is
# a named exit — a silent fallback here priced a sonnet-tier campaign at
# the haiku row, exactly 20x its accountant's total (#3138).
PRICING_MODEL_ID = "claude-haiku-5-5"

# The 8 tier-1 re-examination designations, in the report's order. The
# renders are numbered in this order first (coordinator dispatch R1105:
# "les 8 désignés du palier 1 d'abord"). Reasons cite measured facts only.
DESIGNATED_ORDER: List[Tuple[str, str]] = [
    (
        "a53fc485_ext0",
        "classified non-argumentative after 1 call and skipped 20 phases; its sibling segments each find 14-18 arguments — the cheapest re-examination at maximal leverage",
    ),
    (
        "00b283cf_ext9",
        "worst extraction flood of the corpus: 6013 'arguments', two orders of magnitude above the table's median — a higher tier must rank, not enumerate",
    ),
    (
        "00b283cf_ext7",
        "second member of the flood family (1998) — says whether the flood is the document or the tier",
    ),
    (
        "e9f74d6d_ext3",
        "thinnest complete run (5 arguments, 4 fallacies, the cheapest doc) — under-extraction at the poor end",
    ),
    (
        "3ef9c0c6_ext3",
        "facts window = short_input, never seen on a real input — does a higher tier judge the segment too short?",
    ),
    (
        "00b283cf_ext1",
        "facts window = no_punctuated_span_found: span search is a judgment, one strong pass deserves it",
    ),
    (
        "d6a33d9c",
        "anchor: the richest normal run (134 arguments, 16 fallacies, 10 extracts) — calibrates what the tier changes on a well-served document",
    ),
    (
        "eeaef25b",
        "cheapest fully-treated doc (132 calls, 6 arguments) — the low end of the cost/density curve",
    ),
]

# Render-affecting defects already tracked (coordinator dispatch R1105:
# the reader must not rediscover a known defect). Opaque wording only.
# Ordered by visibility in the render: the formal-verdict family first.
KNOWN_DEFECTS: List[Tuple[str, str]] = [
    (
        "#3135",
        "76 of the 82 formal findings in the deep synthesis are untranslated stubs of the shape <first-word>(X) — the formal-verdict columns count them as results",
    ),
    (
        "#3136",
        "logic lines credit FOL/propositional verdicts to the document's first 4000 characters only",
    ),
    (
        "#3137",
        "Act III's 'best score' is a maximum over 8 arguments, not a corpus-wide figure",
    ),
    (
        "#3134",
        "the restitution quotes a 500-character descent as the fallacy-detection bound",
    ),
    (
        "#3133",
        "Convergence double-counts the fallacy signal the acts already carry",
    ),
    (
        "#3121",
        "modal analysis: one analysis per formula set — a render may show a single modal verdict where earlier renders showed several partial ones",
    ),
    (
        "#3122",
        "propositional-logic UNSAT entries: the entry states its cause and a minimal core — older renders said only 'UNSAT'",
    ),
    (
        "#3123",
        "formal-result stubs of the shape <first-word>(X): parsable but untranslated — see inondation_extraction.md's neighbor, the formal-verdict column counts them as results",
    ),
    (
        "#3131",
        "local_llm_results had no reader before the bounds-line wiring — renders prior to it carry no local-tier fact",
    ),
    (
        "#3125",
        "thread-liveness detector false negative under CPU load — a phase reported hung may have finished",
    ),
]


def git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        ).stdout.strip()
    except OSError:
        return "unavailable"


def guard_output_path(out: Path) -> None:
    """#2353: refuse to write outside the gitignored results tree."""
    resolved = out.resolve()
    root = RESULTS_ROOT.resolve()
    if not resolved.is_relative_to(root):
        raise SystemExit(
            f"refusing to write outside {root} (got {resolved}) — the reading"
            " folder carries real corpus names and must stay gitignored"
        )


def load_json(path: Path) -> Dict[str, Any]:
    parsed: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return parsed


def safe_name(text: str, max_len: int = 40) -> str:
    """An ASCII-safe slug for a render filename (real title, private tree)."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:max_len]
    return slug or "sans-titre"


def doc_cost_usd(
    usage: Dict[str, Any], pricing_model: str = PRICING_MODEL_ID
) -> Optional[float]:
    """Recompute a document's pipeline cost from measured per-phase tokens.

    Same instrument as the campaign's usage line (#3095 price table), at the
    STANDARD row of ``pricing_model`` — the run's model, resolved from its
    zero-shot provenance by ``resolve_run_pricing``; the module constant is
    only the direct-call default (#3138). The signature records per-PHASE
    aggregates, not per-call sizes: pricing an aggregate through
    ``price_tokens`` would bill any phase whose calls sum past 100k tokens at
    the long-prompt tier (measured on this campaign: 21.94 $ instead of
    8.17 $) while the campaign's own measurement found no single call above
    the threshold (mean ~2.6k prompt/call). The standard row on aggregates
    reproduces the accountant's total exactly. None (never a fabricated 0)
    when the model is not priced.
    """
    from argumentation_analysis.services.model_prices import resolve_price_row

    row = resolve_price_row(pricing_model, 0)
    if row is None:
        return None
    total = 0.0
    priced = False
    for value in usage.values():
        if not isinstance(value, dict) or "prompt_tokens" not in value:
            continue
        total += (
            value.get("prompt_tokens", 0) / 1_000_000 * row.input_per_mtok
            + value.get("completion_tokens", 0) / 1_000_000 * row.output_per_mtok
        )
        priced = True
    return round(total, 4) if priced else None


def zeroshot_cost_usd(record: Dict[str, Any]) -> Optional[float]:
    """One zero-shot record's cost, priced at the model ITS provenance names.

    A record that names no model exits by name: pricing it at the module
    constant is the silent fallback that priced the sonnet tier at the haiku
    row (#3138).
    """
    from argumentation_analysis.services.model_prices import price_tokens

    model = (record.get("provenance") or {}).get("model")
    if not model:
        raise SystemExit(
            f"the zero-shot record of {record.get('opaque_id', '?')} carries"
            " no provenance model — its cost cannot be priced at a guessed"
            f" row; refusing to fall back to {PRICING_MODEL_ID} (#3138)"
        )
    usage = record.get("usage") or {}
    cost = price_tokens(
        model,
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )
    return round(cost, 4) if cost is not None else None


def _count(value: Any) -> int:
    """Collection state fields count as their length; anything else as 0.

    The real campaign states carry ``identified_arguments`` as a dict
    ``{arg_N: text}`` (measured: 134 entries on the anchor doc) and the
    formal results as lists — a list-only counter zeroed the whole numbers
    layer of the first real render (caught by the reading-folder QC, not by
    the synthetic witnesses, which had planted lists).
    """
    if isinstance(value, (list, dict)):
        return len(value)
    return 0


def doc_facts(
    sig: Dict[str, Any],
    state: Dict[str, Any],
    pricing_model: str = PRICING_MODEL_ID,
) -> Dict[str, Any]:
    """The measured facts of one document, read from its artifacts."""
    st = state.get("state") or state
    usage = sig.get("llm_usage") or {}
    return {
        "opaque_id": sig.get("opaque_id", ""),
        "title": (sig.get("metadata") or {}).get("title", "titre inconnu"),
        "speaker": (sig.get("metadata") or {}).get("speaker", "locuteur inconnu"),
        "year": (sig.get("metadata") or {}).get("date_or_year", ""),
        "chars": document_chars(st),
        "args": _count(st.get("identified_arguments")),
        "fallacies": _count(st.get("identified_fallacies")),
        "fol": _count(st.get("fol_analysis_results")),
        "pl": _count(st.get("propositional_analysis_results")),
        "modal": _count(st.get("modal_analysis_results")),
        "wall_s": sig.get("wall_clock_s"),
        "status": (sig.get("outcome") or {}).get("status", "?"),
        "workflow": sig.get("workflow", "?"),
        "cost": doc_cost_usd(usage, pricing_model),
        "calls": sum(
            v.get("calls", 0)
            for v in usage.values()
            if isinstance(v, dict) and "calls" in v
        ),
        "reading_window_status": st.get("reading_window_status"),
        "restitution_acts_degraded": st.get("restitution_acts_degraded"),
        # The terminal classification lives at the signature's root and is
        # written ONLY for the non-argumentative case (#1909 slice 2) — its
        # absence is data, not a hole, and keys the honest render below.
        "classification": sig.get("document_classification"),
        "outcome": sig.get("outcome") or {},
    }


def median(values: List[int]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    return float(s[n // 2]) if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def provenance_block(run_head: str, model: str, command: str) -> str:
    return (
        "---\n"
        f"producer: scripts/dataset/render_campaign_reading_folder.py (#2841 reading folder)\n"
        f"campaign_run_git_head: {run_head}\n"
        f"model: {model}\n"
        f"pricing: recomputed from measured per-phase tokens, #3095 table (standard row of {model})\n"
        f"command: {command}\n"
        "---\n"
    )


# #3393 — the FB-18 anchors are the pipeline's grounding: they stay in the
# STATE (what an auditor resolves against the run's artifacts), and the
# READER surface prints prose — each anchor becomes a numbered note. The
# numbering happens INSIDE `pipeline_full_text`, the one producer the fiche
# prints and the judge reads (#3375 tranche 3): a caller that numbered on its
# own would leave the judge reading raw `[artifact:…]` while the reader read
# notes — the divergence that single producer exists to close.
_ARTIFACT_ANCHOR_RE = re.compile(r"\[artifact:([^\]\s]+)\]")


def anchors_to_notes(text: str, notes: Dict[str, str]) -> str:
    """One FB-18 anchor becomes one numbered note (#3393).

    ``notes`` is the fiche-wide registry, carried by the caller so every
    act numbers into ONE list: the same anchor keeps the same number
    wherever it appears, and the fiche's notes section (below) names what
    each number stands for — the anchor stays checkable, the prose stays
    readable.
    """

    def _sub(match: "re.Match[str]") -> str:
        anchor = match.group(1)
        if anchor not in notes:
            notes[anchor] = f"[{len(notes) + 1}]"
        return notes[anchor]

    return _ARTIFACT_ANCHOR_RE.sub(_sub, text)


def notes_section(notes: Dict[str, str]) -> str:
    """The fiche's notes block — one line per anchor, numbered, checkable."""
    if not notes:
        return ""
    ordered = sorted(notes.items(), key=lambda kv: int(kv[1][1:-1]))
    lines = ["### Notes du pipeline (ancres du run)", ""]
    lines += [
        f"- {mark} fait ancré dans l'état du run : `{anchor}`"
        for anchor, mark in ordered
    ]
    return "\n".join(lines)


def document_chars(state: Dict[str, Any]) -> int:
    """The document's length, read from the state — ONE measure (#3392).

    The fiche's ``chars`` fact and the reader paragraph both come from here,
    so the reader cannot be told two lengths for the same document.
    """
    st = state.get("state") or state
    return len(st.get("raw_text") or "")


def render_non_argumentative_reader_paragraph(state: Dict[str, Any], chars: int) -> str:
    """#3392 — the reader's paragraph for the valid no-analysis case.

    A correct CLASSIFICATION with an English batch log is not an explained
    refusal (GRILLE_JUGE_2841 §5): on the panel's one non-argumentative
    document the zero-shot named what the document was and why no argument
    could be analysed, and the render taught the reader less — the only
    ZEROSHOT_WINS of cycle 0.

    Everything here comes from what the extract and the corpus record put
    on the state: the metadata it recorded (through the SAME reader-label
    view the acts use, #3311), and the counts it measured. One clause per
    recorded element, absent fields omitted — an element the extract did
    not record is the gap the issue names, never something to invent.
    No LLM call (the issue's ask 2). The batch log keeps its own English
    line; this paragraph is the reader's, built beside it.

    ``chars`` is the length ``document_chars`` measured — passed in, never
    recomputed here (R1141).

    #3389's rule rides every recorded value (#3408 rework): a value goes
    between « » ONLY if the in-memory document carries it
    (``normalised_quote_in``) — « » is a verbatim claim, and the recorded
    event or participants of a header are often the record's own words
    about the document, not the document's. An uncarried value prints as
    what it is, a recorded description, with no quotes around it.
    """
    st = state.get("state") or state
    from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
        reader_metadata_view,
    )
    from argumentation_analysis.reporting.restitution.quote_fidelity import (
        normalised_quote_in,
    )

    metadata = reader_metadata_view(st.get("source_metadata") or {})
    text = st.get("raw_text") or ""
    subject = f"Ce document de {chars} caractères" if chars else "Ce document"
    parts = [
        f"{subject} n'a pas été lu comme une "
        "argumentation : l'extraction n'y a identifié aucun argument — "
        "aucune thèse à examiner, aucun raisonnement à suivre."
    ]
    if metadata:
        elements = [
            (
                f"{label} : « {value} »"
                if normalised_quote_in(text, value)
                else f"{label} : {value}"
            )
            for label, value in metadata.items()
        ]
        parts.append(
            "Le matériel enregistré le décrit ainsi — " + " ; ".join(elements) + "."
        )
    parts.append(
        "Les phases qui lisent des arguments, des sophismes ou des inférences "
        "ont donc été écartées : la classification est terminale, et ce n'est "
        "pas un échec."
    )
    return "\n\n".join(parts)


#: #3468 — a cut dump says what exists; it does not re-run the analysis.
#: Eight items per list is a page the reader finishes, not a wall.
_CUT_MATERIAL_CAP = 8


def _capped_list_block(label: str, clauses: List[str]) -> str:
    """One #3468 material block: a capped list under a count-honest header."""
    shown = clauses[:_CUT_MATERIAL_CAP]
    head = f"**{label} — {len(clauses)} enregistré(s)"
    if len(clauses) > len(shown):
        head += f", {len(shown)} listé(s)"
    head += " :**"
    return head + "\n" + "\n".join(shown)


def render_cut_analysis_material(
    st: Dict[str, Any], outcome: Optional[Dict[str, Any]] = None
) -> str:
    """#3468 — the cut run's dump: recorded material under a named cut.

    A wall-clock bound kills the pipeline mid-DAG and the state IS recovered
    (#1528) — but the acts are DAG-tail phases and never ran, so the state
    carries upstream material (extracts, fallacies, stakes) and no act
    string. Without this section ``pipeline_full_text`` printed four absence
    lines and nothing else: everything the run paid for was lost to the
    fiche AND the blind judge at the cut — both read this one producer.

    Everything here comes from the state's recorded fields — one clause per
    recorded element, absent fields omitted (#3392's rule), never a
    fabricated act (anti-#1019). An extract goes between « » only when the
    in-memory document carries it (``normalised_quote_in``, #3389's rule).
    The stakes read mirrors ``act1_framing``'s: ``description`` then
    ``stake_type``, a bare string read as itself.

    Returns "" when the state recorded no material — an early cut stays what
    it is, four named absences, nothing invented to fill it.
    """
    from argumentation_analysis.reporting.restitution.quote_fidelity import (
        normalised_quote_in,
    )

    text = st.get("raw_text") or ""
    blocks: List[str] = []

    arguments = st.get("identified_arguments") or {}
    if isinstance(arguments, dict):
        extracts = [
            v.strip() for v in arguments.values() if isinstance(v, str) and v.strip()
        ]
        if extracts:
            blocks.append(
                _capped_list_block(
                    "Extraits identifiés",
                    [
                        f"« {desc} »" if normalised_quote_in(text, desc) else desc
                        for desc in extracts
                    ],
                )
            )

    fallacies = st.get("identified_fallacies") or {}
    if isinstance(fallacies, dict):
        clauses: List[str] = []
        for entry in fallacies.values():
            if not isinstance(entry, dict):
                continue
            ftype = str(entry.get("type") or "").strip()
            why = str(entry.get("justification") or "").strip()
            if ftype and why:
                clauses.append(f"{ftype} — {why}")
            elif ftype:
                clauses.append(ftype)
        if clauses:
            blocks.append(_capped_list_block("Sophismes identifiés", clauses))

    stakes_obj = st.get("stakes_and_stakeholders") or {}
    stakes: List[str] = []
    if isinstance(stakes_obj, dict):
        for s in stakes_obj.get("stakes") or []:
            desc = ""
            if isinstance(s, dict):
                desc = str(s.get("description") or s.get("stake_type") or "")
            elif isinstance(s, str):
                desc = s
            desc = desc.strip()
            if desc:
                stakes.append(desc)
    if stakes:
        blocks.append(_capped_list_block("Enjeux enregistrés", stakes))

    strategic = st.get("strategic_read") or {}
    historical = st.get("historical_context") or {}
    reading = (
        str(strategic.get("reading") or "").strip()
        if isinstance(strategic, dict)
        else ""
    )
    situation = (
        str(historical.get("situation") or "").strip()
        if isinstance(historical, dict)
        else ""
    )
    if reading or situation:
        lines = []
        if reading:
            lines.append(f"- lecture stratégique enregistrée : {reading}")
        if situation:
            lines.append(f"- situation historique enregistrée : {situation}")
        blocks.append("**Lectures de contexte enregistrées :**\n" + "\n".join(lines))

    if not blocks:
        return ""

    if str((outcome or {}).get("status") or "").strip() == "partial":
        intro = (
            "**Analyse coupée par le budget de temps avant les actes.** Les "
            "actes sont les dernières phases du parcours : aucun n'a été "
            "produit. Ce qui suit est le matériel établi en amont, tel "
            "qu'enregistré dans l'état au moment de la coupe — une pièce "
            "par élément, rien d'inventé, listes bornées."
        )
    else:
        intro = (
            "**Aucun acte produit pour ce document.** Les actes sont les "
            "dernières phases du parcours : aucun n'a eu lieu. Ce qui suit "
            "est le matériel enregistré dans l'état — une pièce par "
            "élément, rien d'inventé, listes bornées."
        )
    return intro + "\n\n" + "\n\n".join(blocks)


def pipeline_full_text(
    st: Dict[str, Any],
    classification: Optional[str],
    opaque_id: str,
    outcome: Dict[str, Any],
    chars: Optional[int] = None,
) -> str:
    """The pipeline's own words for one document — ONE producer, two callers.

    The fiche prints this verbatim under ``## Le pipeline, en texte intégral``
    and the blind judge reads the very same string as an arm (#3375 tranche 3).
    A second copy built for the judge had already diverged: it dropped the
    terminal classification of a non-argumentative document (#3278), so the
    judge stared at an EMPTY text where the reader saw the classification
    sentence — the exact failure this single producer exists to close.

    #3393: the FB-18 anchors are numbered here, in the same string, so the
    judge reads prose with resolvable notes instead of raw ``[artifact:…]``
    markers the reader never sees.
    #3392: the non-argumentative branch prints the reader's French paragraph,
    built from the recorded material, instead of the batch runner's English
    line (which stays in the log). ``chars`` is the length the caller already
    measured; omitted, it is read from the state — the same measure.
    """
    notes: Dict[str, str] = {}
    body: List[str] = []
    if classification == "non_argumentative":
        # #3278 — the empty acts of a non-argumentative document are a
        # terminal classification, not an absence: the reader of the one
        # document with no analysis is the one who most needs to know why.
        # #3392 — the reader gets a French paragraph built from the recorded
        # material; the batch runner's English line stays in the LOG
        # (run_corpus_batch prints it there, untouched) and leaves the
        # reader's surface entirely — a hidden copy here would still be
        # text the judge reads.
        length = document_chars(st) if chars is None else chars
        body.append(
            "**Classification terminale : document non-argumentatif.** "
            "Aucun acte n'est produit pour ce document, et c'est le "
            "comportement attendu."
        )
        body.append("")
        body.append(render_non_argumentative_reader_paragraph(st, length))
        body.append("")
    else:
        acts = [
            ("Acte I — cadrage", st.get("act1_framing")),
            ("Acte II — récit", st.get("act2_narrative")),
            ("Acte III — conclusion", st.get("act3_conclusion")),
            ("Synthèse narrative", st.get("narrative_synthesis")),
        ]
        for heading, text in acts:
            body.append(f"### {heading}")
            body.append("")
            if isinstance(text, str) and text:
                body.append(anchors_to_notes(text, notes))
            else:
                body.append(
                    f"*(absent de l'état — {heading.lower()} non produit pour ce document)*"
                )
            body.append("")
        # #3468 — a wall-clock cut recovers the state but not the acts (they
        # are DAG-tail phases): when every act is absent yet the state carries
        # analysis material, that material is rendered honestly, or four
        # absence lines are all the fiche and the blind judge ever see.
        if not any(isinstance(text, str) and text for _, text in acts):
            cut_block = render_cut_analysis_material(st, outcome)
            if cut_block:
                body.append(cut_block)
                body.append("")
    question = st.get("interpretive_question")
    if isinstance(question, str) and question:
        body.append("### Question interprétative")
        body.append("")
        body.append(anchors_to_notes(question, notes))
        body.append("")
    notes_block = notes_section(notes)
    if notes_block:
        body.append(notes_block)
        body.append("")
    return "\n".join(body)


def render_fiche(
    facts: Dict[str, Any],
    state: Dict[str, Any],
    zeroshot: Optional[Dict[str, Any]],
    run_head: str,
    model: str,
    command: str,
) -> str:
    """One readable fiche: the acts in full, the zero-shot beside, the facts."""
    st = state.get("state") or state
    cost_txt = f"{facts['cost']:.4f} $" if facts["cost"] is not None else "non chiffré"
    zs_cost = (
        f"{zeroshot_cost_usd(zeroshot):.4f} $"
        if zeroshot and zeroshot_cost_usd(zeroshot) is not None
        else "non chiffré"
    )
    lines: List[str] = []
    lines.append(provenance_block(run_head, model, command))
    lines.append(
        f"# {facts['title']} — {facts['speaker']}"
        + (f" ({facts['year']})" if facts["year"] else "")
    )
    lines.append("")
    lines.append(
        f"*Document `{facts['opaque_id']}` — {WORKFLOW_LABELS_FR.get(facts['workflow'], facts['workflow'])}, statut `{STATUS_LABELS_FR.get(facts['status'], facts['status'])}`.*"
    )
    lines.append("")
    lines.append("## Faits mesurés (lus dans l'état de la campagne)")
    lines.append("")
    lines.append(
        f"- Longueur du document : **{facts['chars']} caractères** ; arguments extraits : **{facts['args']}** ; sophismes : **{facts['fallacies']}**"
    )
    lines.append(
        f"- Verdicts formels : FOL **{facts['fol']}** / logique propositionnelle **{facts['pl']}** / modale **{facts['modal']}** (les « talons » non traduits s'y comptent comme résultats)"
    )
    lines.append(
        f"- Durée : **{facts['wall_s']} s** ; appels LLM : **{facts['calls']}** ; coût recalculé : pipeline **{cost_txt}**, zero-shot **{zs_cost}**"
    )
    lines.append(
        f"- Fenêtre de lecture : `{json.dumps(facts['reading_window_status'], ensure_ascii=False) if facts['reading_window_status'] is not None else 'null'}` ; actes dégradés : `{json.dumps(facts['restitution_acts_degraded'], ensure_ascii=False) if facts['restitution_acts_degraded'] is not None else 'null'}`"
    )
    lines.append("")
    lines.append("## Le pipeline, en texte intégral")
    lines.append("")
    full_text = pipeline_full_text(
        st,
        facts.get("classification"),
        facts["opaque_id"],
        facts.get("outcome") or {},
        chars=facts["chars"],
    )
    if full_text:
        lines.append(full_text)
    lines.append("## La réponse zero-shot, intégrale")
    lines.append("")
    if zeroshot and zeroshot.get("answer"):
        lines.append(
            f"*Même modèle, entrée pleine, un seul appel sans outils ({zeroshot.get('elapsed_seconds')} s).*"
        )
        lines.append("")
        lines.append(zeroshot["answer"])
    else:
        lines.append("*(pas d'enregistrement zero-shot pour ce document)*")
    lines.append("")
    return "\n".join(lines)


def build_reading_order(all_ids: List[str]) -> List[str]:
    designated = [doc_id for doc_id, _ in DESIGNATED_ORDER if doc_id in all_ids]
    rest = sorted(doc_id for doc_id in all_ids if doc_id not in designated)
    return designated + rest


def resolve_run_pricing(
    signatures: List[Path], zeroshots: Dict[str, Path]
) -> Tuple[str, str]:
    """The run's pricing model and git head, from the first signature-ordered
    doc that has a zero-shot record.

    The model exists in exactly one place — the zero-shot records'
    provenance — and every pipeline figure below is priced with it. A
    provenance that names no model, or no zero-shot record at all, is a
    named exit: falling back silently to the module constant is the shape
    that priced a sonnet-tier campaign at the haiku row, exactly 20x its
    accountant's total (#3138).
    """
    for sig_path in signatures:
        sig = load_json(sig_path)
        doc_id = sig.get("opaque_id", sig_path.stem.replace("signature_", ""))
        zs_path = zeroshots.get(doc_id)
        if zs_path is None:
            continue
        provenance = load_json(zs_path).get("provenance") or {}
        model = provenance.get("model")
        if not model:
            raise SystemExit(
                f"the zero-shot record of {doc_id} carries no provenance"
                " model — the pipeline pricing row cannot be guessed;"
                f" refusing to fall back to {PRICING_MODEL_ID} (#3138)"
            )
        return model, provenance.get("git_head", "unavailable")
    raise SystemExit(
        "no zero-shot record found to carry the run's provenance — the"
        " pipeline pricing row cannot be guessed; refusing to fall back to"
        f" {PRICING_MODEL_ID} (#3138)"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="#2841 reading folder")
    parser.add_argument("--states-dir", type=Path, default=STATES_DIR)
    parser.add_argument("--signatures-dir", type=Path, default=SIGNATURES_DIR)
    parser.add_argument("--zeroshot-dir", type=Path, default=ZEROSHOT_DIR)
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="campaign report to copy in (optional)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    guard_output_path(args.out)

    signatures = sorted(args.signatures_dir.glob("signature_*.json"))
    states = {
        p.stem.replace("state_full_", ""): p
        for p in args.states_dir.glob("state_full_*.json")
    }
    zeroshots = {p.stem: p for p in args.zeroshot_dir.glob("*.json")}

    # Run-level provenance, resolved BEFORE the first fact is built: the
    # model prices every pipeline figure below, and resolving it after the
    # loop priced a sonnet-tier campaign at the haiku row (#3138).
    model, run_head = resolve_run_pricing(signatures, zeroshots)
    command = "PYTHONPATH=. python scripts/dataset/render_campaign_reading_folder.py"

    docs: List[Dict[str, Any]] = []
    missing_states: List[str] = []
    for sig_path in signatures:
        sig = load_json(sig_path)
        doc_id = sig.get("opaque_id", sig_path.stem.replace("signature_", ""))
        state_path = states.get(doc_id)
        if state_path is None:
            missing_states.append(doc_id)
            continue
        state = load_json(state_path)
        zeroshot = load_json(zeroshots[doc_id]) if doc_id in zeroshots else None
        docs.append(
            {
                "sig": sig,
                "sig_path": sig_path,
                "state_path": state_path,
                "zeroshot": zeroshot,
                "facts": doc_facts(sig, state, pricing_model=model),
            }
        )

    if missing_states:
        raise SystemExit(
            f"{len(missing_states)} signature(s) without a full state dump:"
            f" {', '.join(missing_states)} — the reading folder cannot render"
            " their acts; refusing to build a folder with holes"
        )

    reading_order = build_reading_order([d["facts"]["opaque_id"] for d in docs])
    by_id = {d["facts"]["opaque_id"]: d for d in docs}

    # 02_rendus — the fiches, numbered in reading order.
    renders_dir = args.out / "02_rendus"
    renders_dir.mkdir(parents=True, exist_ok=True)
    for index, doc_id in enumerate(reading_order, start=1):
        d = by_id[doc_id]
        f = d["facts"]
        name = f"{index:02d}_{doc_id}_{safe_name(f['title'])}.md"
        (renders_dir / name).write_text(
            render_fiche(
                f, load_json(d["state_path"]), d["zeroshot"], run_head, model, command
            ),
            encoding="utf-8",
        )

    # 01_tableau_corpus — every number read from an artifact above.
    args_counts = [d["facts"]["args"] for d in docs]
    med = median(args_counts)
    # The flood is data-driven, not a hand list: measured on this corpus the
    # normal rich run tops at 134 arguments for a median of 23, while the
    # flood family starts at 863 — 20x the median separates them with room.
    outliers = {d["facts"]["opaque_id"] for d in docs if d["facts"]["args"] > 20 * med}
    lines = [
        "# Le corpus, une ligne par document",
        "",
        f"{len(docs)} documents rendus. Médiane des arguments extraits : **{med:.0f}**.",
        "Les lignes ⚠ marquent les extractions débordantes (la « crue », mesurée en regard de la longueur du document).",
        "",
        "| # | id | titre | locuteur | caractères | arguments | sophismes | verdicts formels (FOL/PL/modal) | durée (s) | coût pipeline | statut | fiche |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for index, doc_id in enumerate(reading_order, start=1):
        f = by_id[doc_id]["facts"]
        flag = "⚠ " if doc_id in outliers else ""
        cost = f"{f['cost']:.4f} $" if f["cost"] is not None else "—"
        fiche = f"{index:02d}_{doc_id}_{safe_name(f['title'])}.md"
        lines.append(
            f"| {index} | `{doc_id}` | {f['title']} | {f['speaker']} | {f['chars']} | {flag}{f['args']} | {f['fallacies']} | {f['fol']}/{f['pl']}/{f['modal']} | {f['wall_s']} | {cost} | {f['status']} | [fiche](02_rendus/{fiche}) |"
        )
    (args.out / "01_tableau_corpus.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    # inondation_extraction — the flood, measured: args vs document length.
    flood = sorted(docs, key=lambda d: -d["facts"]["args"])
    lines = [
        "# Extraction vs longueur — la mesure de la « crue »",
        "",
        "Arguments extraits en regard de la longueur du document, pour les documents au-dessus de la médiane, puis la queue fine. Mesuré dans les états (`identified_arguments` / `len(raw_text)`), pas recopié.",
        "",
        "| id | caractères | arguments | arguments / 1000 caractères |",
        "|---|---|---|---|",
    ]
    for d in flood[:12]:
        f = d["facts"]
        rate = f"{1000.0 * f['args'] / f['chars']:.1f}" if f["chars"] else "—"
        lines.append(f"| `{f['opaque_id']}` | {f['chars']} | {f['args']} | {rate} |")
    lines += [
        "",
        f"Médiane du corpus : {med:.0f} arguments pour une longueur médiane de {median([d['facts']['chars'] for d in docs]):.0f} caractères.",
        "",
    ]
    (args.out / "inondation_extraction.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    # 00_LIRE_D_ABORD — the entry point, readable without knowing the pipeline.
    total_cost = sum(d["facts"]["cost"] or 0.0 for d in docs)
    total_zeroshot = sum(
        zeroshot_cost_usd(d["zeroshot"]) or 0.0 for d in docs if d["zeroshot"]
    )
    # The report priced every zero-shot call at the standard row; the #3095
    # table as written bills calls past 100k prompt tokens at the long tier
    # (never exercised against a real bill). 5 campaign calls cross it (the
    # flood family's full texts) — the two totals differ by that tier choice,
    # and the reader gets BOTH rather than a silently picked one.
    zeroshot_tokens = [
        (d["zeroshot"].get("usage") or {}) for d in docs if d["zeroshot"]
    ]
    zs_prompt = sum(u.get("prompt_tokens", 0) for u in zeroshot_tokens)
    zs_completion = sum(u.get("completion_tokens", 0) for u in zeroshot_tokens)
    zs_long_calls = sum(
        1 for u in zeroshot_tokens if u.get("prompt_tokens", 0) > 100_000
    )
    # The standard figure prices at the run's model row — the tier the
    # campaign report itself used (a hard-coded haiku row here was the
    # readme's own x20 on a sonnet run, #3138).
    from argumentation_analysis.services.model_prices import resolve_price_row

    std_row = resolve_price_row(model, 0)
    if std_row is not None:
        zs_standard = (
            zs_prompt / 1e6 * std_row.input_per_mtok
            + zs_completion / 1e6 * std_row.output_per_mtok
        )
        zs_standard_txt = f"**{zs_standard:.4f} $** au tarif standard (le chiffre du rapport de campagne)"
    else:
        zs_standard_txt = (
            "non chiffrable (rang de prix standard inconnu pour ce modèle)"
        )
    lines = [
        provenance_block(run_head, model, command),
        "# Campagne #2841 — lire d'abord ceci",
        "",
        "## Ce que c'est",
        "",
        f"Le corpus chiffré du dépôt ({len(docs)} segments de discours politiques historiques et contemporains) a été traité le 2026-10-21 par le pipeline complet (« workflow spectacular » : extraction d'arguments, détection de sophismes, analyse formelle FOL/propositionnelle/modale, puis restitution narrative en trois actes), modèle **{model}**, sans limite de longueur d'entrée. Chaque document a été traité aussi en **zero-shot** : le même modèle, le texte entier, un seul appel sans outils — pour comparer ce que la machinerie apporte au-dessus du modèle brut.",
        "",
        f"Coût du pipeline recalculé depuis les jetons mesurés : **{total_cost:.4f} $**. Coût zero-shot : {zs_standard_txt} ou **{total_zeroshot:.4f} $** en appliquant le palier long-prompt de la table de prix à ses {zs_long_calls} appels de plus de 100 k jetons d'entrée — palier jamais confronté à une facture réelle, l'écart entre les deux chiffres est la mesure de cette incertitude. Code du run : `{run_head}`.",
        "",
        "## Ce que la campagne établit — et n'établit pas",
        "",
        "Établit : le pipeline traite les {n} documents de bout en bout ({ok} statuts ok) ; le coût par document est reproductible à partir des jetons ; deux familles de défauts sont visibles dans le rendu (la « crue » d'extraction — des milliers d'arguments énumérés au lieu de hiérarchisés — et des verdicts formels non traduits de la forme « premier mot(X) »).".format(
            n=len(docs),
            ok=sum(1 for d in docs if d["facts"]["status"] == "ok"),
        ),
        "",
        "N'établit pas : la qualité interprétative des actes (aucun juge humain ne les a notés) ; l'effet d'un changement de modèle (le palier supérieur est précisément ce qui va être mesuré ensuite) ; la complétude des verdicts formels (les « talons » parsables s'y comptent comme résultats — voir 03_defauts_connus.md).",
        "",
        "## Ordre de lecture conseillé",
        "",
        "Les cinq premières fiches couvrent les situations contrastées du corpus ; les trois suivantes complètent les 8 documents désignés pour le réexamen au palier supérieur.",
        "",
    ]
    # The reading advice lists only the designated documents this corpus
    # actually contains (a partial corpus renders partial advice).
    designated_present = [
        (doc_id, reason) for doc_id, reason in DESIGNATED_ORDER if doc_id in by_id
    ]
    for rank, (doc_id, reason) in enumerate(designated_present[:5], start=1):
        index = reading_order.index(doc_id) + 1
        f = by_id[doc_id]["facts"]
        lines.append(
            f"{rank}. **fiche {index:02d} — `{doc_id}` ({f['title']})** : {reason}."
        )
    lines.append("")
    for rank, (doc_id, reason) in enumerate(designated_present[5:], start=6):
        index = reading_order.index(doc_id) + 1
        f = by_id[doc_id]["facts"]
        lines.append(
            f"{rank}. fiche {index:02d} — `{doc_id}` ({f['title']}) : {reason}."
        )
    lines += [
        "",
        "## Comment lire une fiche",
        "",
        "Chaque fiche porte d'abord cinq lignes de faits mesurés, puis les trois actes et la synthèse du pipeline **en texte intégral**, puis la réponse zero-shot intégrale à côté. Annexes : les signatures (comptes) et états complets (JSON) de chaque document, pour vérifier chaque chiffre.",
        "",
        "Défauts déjà connus et tracés : voir `03_defauts_connus.md` avant de « découvrir » un défaut — il est probablement déjà numéroté.",
        "",
    ]
    (args.out / "00_LIRE_D_ABORD.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    # 03_defauts_connus — so the reader does not rediscover them.
    lines = [
        "# Défauts connus avant lecture",
        "",
        "Ce que vous verrez dans les fiches et qui est déjà suivi. Un défaut numéroté n'est pas une découverte — inutile de le re-signaler ; en revanche, un défaut **hors** cette liste mérite une issue.",
        "",
    ]
    for number, description in KNOWN_DEFECTS:
        lines.append(f"- **{number}** — {description}.")
    (args.out / "03_defauts_connus.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    # 04_annexes — the machine artifacts of THIS campaign, for verification.
    # The states dir also holds older campaigns' dumps (90 files where the
    # campaign has 49): copy by the campaign's doc ids, never the whole dir.
    annexes = args.out / "04_annexes"
    campaign_ids = set(by_id)
    for sub, src_dir, pattern in (
        ("signatures", args.signatures_dir, "signature_*.json"),
        ("states", args.states_dir, "state_full_*.json"),
        ("zeroshot", args.zeroshot_dir, "*.json"),
    ):
        dst = annexes / sub
        dst.mkdir(parents=True, exist_ok=True)
        for src in src_dir.glob(pattern):
            stem = src.stem
            doc_id = stem.replace("signature_", "").replace("state_full_", "")
            if doc_id not in campaign_ids:
                continue
            target = dst / src.name
            # #3284 — re-rendering from this folder's own annexes meets
            # itself: copying a file onto itself raises SameFileError AFTER
            # every reading file is written, so the folder looked done while
            # the producer reported failure. The annex is already where it
            # belongs: nothing to copy.
            if target.exists() and src.samefile(target):
                continue
            shutil.copy2(src, target)

    if args.report and args.report.exists():
        report_target = args.out / args.report.name
        # Same trap as the annexes one step above (#3284): a --report that
        # already lives inside the output folder is in place already.
        if not (report_target.exists() and args.report.samefile(report_target)):
            shutil.copy2(args.report, report_target)

    print(f"reading folder: {args.out}")
    print(
        f"documents rendered: {len(docs)} (reading order: {len(DESIGNATED_ORDER)} designated first)"
    )
    print(
        f"recomputed campaign cost: {total_cost:.4f} $ pipeline + {total_zeroshot:.4f} $ zero-shot"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
