#!/usr/bin/env python3
"""#3375 — the v1 panel's blind judge: two arms, one grid, a traceable verdict.

The v1 bar (Epic #3374) is the final differential against the same-model
zero-shot, on a ten-document panel. This producer is the instrument of that
bar: it takes both arms' outputs, has each document judged by a model of
ANOTHER family, verifies every citation mechanically, and writes one
aggregated table.

What it refuses, and why (each refusal is a witness in
``tests/unit/scripts/test_judge_panel_3375.py``):

- a judge of the pipeline's own family — the grid's opening line
  (``docs/guides/GRILLE_JUGE_2841.md``) excludes the producer grading itself
  (``argumentation_analysis/evaluation/judge.py`` is exactly that, and is
  deliberately NOT used here);
- a citation that is not in the text it claims — an item whose quote cannot
  be found is DROPPED and COUNTED, never swallowed: that is what makes the
  judge falsifiable ("un item sans citation n'existe pas");
- a silent fallback when a cost cannot be priced (``#1019`` tri-state: an
  unpriced arm prints ``unpriced``, never 0.0000 $).

The judge sees the SOURCE DOCUMENT as a third prompt block: an M2 is a claim
the document contradicts, and without the document the single-pass reading
would be the oracle of its own correctness. The document is decrypted IN
MEMORY (``load_extract_definitions`` with the derived key) and never
persisted — no file, no log, no test output carries it (dataset privacy
rule 5). The WHOLE document rides in the prompt or that document fails
loudly: an excerpt would let the judge verify quotes against a slice the
campaign itself never read.

Blindness, stated honestly: the two texts are shown as ``Texte 1`` and
``Texte 2``, their side of the pairing drawn per document from a seed that
is recorded. The pipeline's rendered form stays recognisable — so this is
**blind to order, not to style**, and the table says so in those words.

Usage (PYTHONPATH is required, like the two arms):

    PYTHONPATH=. python scripts/dataset/judge_panel.py \\
        --judge-model claude-sonnet-5-5 \\
        --panel-file panel.txt --seed 3375 [--dry-run]

Output (gitignored — ``argumentation_analysis/evaluation/results/``):

    argumentation_analysis/evaluation/results/judge_panel_3375/
        <opaque_id>.json   raw answer + verified items + the draw
        TABLE.md           the aggregated verdict table
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from argumentation_analysis.evaluation.model_family import (  # noqa: E402
    assert_judge_differs,
    model_family,
)
from argumentation_analysis.reporting.restitution.quote_fidelity import (  # noqa: E402
    normalise_for_citation,
    normalised_quote_in,
)

from scripts.dataset.render_campaign_reading_folder import (  # noqa: E402
    SIGNATURES_DIR as _FICHE_SIGNATURES_DIR,
    STATES_DIR as _FICHE_STATES_DIR,
    ZEROSHOT_DIR as _FICHE_ZEROSHOT_DIR,
)

RESULTS_ROOT = REPO_ROOT / "argumentation_analysis" / "evaluation" / "results"
DEFAULT_OUT = RESULTS_ROOT / "judge_panel_3375"
# The judge reads the folders the fiche reads: the judged text is what the
# fiche prints (``pipeline_full_text``), so its inputs keep no copy of the
# path. A copy here pointed at ``.analysis_kb/``, which the campaign never
# writes, and the judge found no arm at all on the real cycle-0 run.
DEFAULT_STATES_DIR = _FICHE_STATES_DIR
DEFAULT_SIGNATURES_DIR = _FICHE_SIGNATURES_DIR
DEFAULT_ZEROSHOT_DIR = _FICHE_ZEROSHOT_DIR
GRID_PATH = REPO_ROOT / "docs" / "guides" / "GRILLE_JUGE_2841.md"

# The grid's five states (§3) — a verdict is an état, never a score.
STATES: Tuple[str, ...] = (
    "PIPELINE_SUPPLIES",
    "PIPELINE_SUPPLIES_WITH_GAP",
    "PARITY",
    "ZEROSHOT_WINS",
    "BOTH_ABSTAIN",
)

# The seven item codes (§2): five S, two M. Order is the grid's.
ITEM_CODES: Tuple[str, ...] = ("S1", "S2", "S3", "S4", "S5", "M1", "M2")

# Which side an item MUST quote, by the grid's own definition of the code.
#  - S* ("ce que l'analyse établit que le zero-shot n'établit pas") is a claim
#    about the analysis: its quote must come from the analysis text.
#  - M1 ("une observation qu'AUCUNE ligne du rendu ne porte") is an ABSENCE on
#    the analysis side: demanding an analysis quote would make every M1
#    unprovable, so only the zero-shot quote is required.
#  - M2 ("une affirmation du rendu que le document démentit") quotes all
#    three: the wrong claim, the correct reading, and the DOCUMENT line that
#    contradicts it — an M2 the source cannot be shown to contradict is an
#    opinion, not a contresens.
# A document_quote on ANY code is verified when present (a fabricated
# citation is a fabricated citation) and required only where stated.
REQUIRED_SIDES: Dict[str, Tuple[str, ...]] = {
    "S1": ("pipeline",),
    "S2": ("pipeline",),
    "S3": ("pipeline",),
    "S4": ("pipeline",),
    "S5": ("pipeline",),
    "M1": ("zeroshot",),
    "M2": ("pipeline", "zeroshot", "document"),
}

# §2's two M forms plus the coordinator's severity rule (R1139): severe = M2,
# or M1 on the document's central thesis; moderate = M1 elsewhere. Form is NOT
# an M (the grid says so): style notes are kept apart and never counted as a
# gap.
SEVERITY_SEVERE = "severe"
SEVERITY_MODERATE = "moderate"

# #3458 — the pipeline arm's health, read from each document's state dump.
# The three act keys the rule reads; all three live at the state's root, the
# same level the fiche renderer reads them at.
ACT_KEYS: Tuple[str, ...] = ("act1_framing", "act2_narrative", "act3_conclusion")
# Refuse the pass when this many documents carry a degraded pipeline arm.
# Calibration on the panel runs: c2 = 1 degraded document passes (judged,
# flagged), c3 = 9 refuses — the boundary is 2 of 10, a named constant so
# the refusal never hides behind a bare literal at the call site.
DEGRADED_ARM_REFUSAL_THRESHOLD = 2


class JudgeUnparsed(RuntimeError):
    """The judge's answer carried no readable JSON — counted, never guessed."""


# ---------------------------------------------------------------------------
# The draw — per document, from a recorded seed
# ---------------------------------------------------------------------------


def draw_order(opaque_id: str, seed: int) -> bool:
    """True when the PIPELINE takes position 1 for this document.

    Per document, never one draw for the panel: a single global order lets a
    position bias (readers over-credit the first text) masquerade as a
    pipeline effect across all ten documents.
    """
    rng = random.Random(f"{seed}:{opaque_id}")
    return rng.random() < 0.5


def positions(opaque_id: str, seed: int) -> Dict[str, int]:
    """``{"pipeline": 1|2, "zeroshot": 1|2}`` for this document."""
    pipeline_first = draw_order(opaque_id, seed)
    return {
        "pipeline": 1 if pipeline_first else 2,
        "zeroshot": 2 if pipeline_first else 1,
    }


# ---------------------------------------------------------------------------
# Citations — mechanical, normalised, falsifiable
# ---------------------------------------------------------------------------
#
# #3389 — ONE rule, one producer. The judge's ``document_quote`` and the
# render's « … » spans are located by the same implementation
# (``reporting/restitution/quote_fidelity``): case, whitespace and typographic
# apostrophes folded, ``[…]`` read as an elision gap. This file used to carry
# its own whitespace-only copy, so the two surfaces could disagree on what
# "the document says this" means.


def normalise(text: Any) -> str:
    """The comparison form of ``text`` — the shared citation rule (#3389)."""
    return normalise_for_citation(text)


def is_cited(text: str, quote: str) -> bool:
    """True when ``quote`` occurs in ``text`` under the shared citation rule.

    Kept as the judge's name for it: a judge that has to copy the words
    cannot invent one whole, and the length floor stays here because it is
    the JUDGE's rule — a word or two is a keyword, not a citation, and it
    occurs in every text. Grading the quality of a quote is the reader's job,
    not the verifier's.
    """
    return normalised_quote_in(text, quote)


def validate_items(
    raw_items: Sequence[Any],
    pipeline_text: str,
    zeroshot_text: str,
    document_text: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split the judge's items into kept and DROPPED, with a reason each.

    Dropped items are returned, never filtered away: the table prints their
    count and their reasons, which is the whole point of a falsifiable judge.
    """
    kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    for index, raw in enumerate(raw_items or []):
        if not isinstance(raw, dict):
            dropped.append({"index": index, "code": None, "reason": "not_an_object"})
            continue
        code = str(raw.get("code") or "").strip().upper()
        if code not in ITEM_CODES:
            dropped.append({"index": index, "code": code, "reason": "unknown_code"})
            continue
        # The judge quotes by ROLE ("analysis" / "reading"), never by arm:
        # the position each role occupies is the draw's business, recorded
        # separately, and the mapping to the arms stays in the runner. The
        # document is a third side — the source itself, quoted by its own
        # field, verified against the decrypted-in-memory text.
        sides = {
            "pipeline": raw.get("analysis_quote") or "",
            "zeroshot": raw.get("reading_quote") or "",
            "document": raw.get("document_quote") or "",
        }
        texts = {
            "pipeline": pipeline_text,
            "zeroshot": zeroshot_text,
            "document": document_text,
        }
        reason = None
        for side, quote in sides.items():
            if quote and not is_cited(texts[side], quote):
                # A FABRICATED quote drops the item even when that side was
                # not required: an invented citation is an invented citation.
                reason = f"quote_not_in_{side}_text"
                break
        if reason is None:
            for side in REQUIRED_SIDES[code]:
                if not normalise(sides[side]):
                    reason = f"missing_{side}_quote"
                    break
        if reason is not None:
            dropped.append({"index": index, "code": code, "reason": reason})
            continue
        kept.append(
            {
                "code": code,
                "severity": severity_of(code, bool(raw.get("on_central_thesis"))),
                "on_central_thesis": bool(raw.get("on_central_thesis")),
                "pipeline_quote": normalise(sides["pipeline"]),
                "zeroshot_quote": normalise(sides["zeroshot"]),
                "document_quote": normalise(sides["document"]),
                "note": str(raw.get("note") or "").strip(),
            }
        )
    return kept, dropped


def severity_of(code: str, on_central_thesis: bool = False) -> Optional[str]:
    """The coordinator's rule, applied by the runner — not chosen by the judge.

    The judge answers FACTS (which code, and whether an M1 bears on the
    document's central thesis); the severity mapping lives here so that one
    rule produces every row of the table.
    """
    if code == "M2":
        return SEVERITY_SEVERE
    if code == "M1":
        return SEVERITY_SEVERE if on_central_thesis else SEVERITY_MODERATE
    return None  # S* is a supply, not a defect: severity does not apply.


# #3417 — the grid's §3 names S1/S2/S3 as what makes the pipeline SUPPLY
# something; S4 (declared partial coverage) and S5 (a discriminating virtue
# note) are kept and counted as items, but they do not by themselves make a
# document a supply.
CORE_SURPLUS_CODES: Tuple[str, ...] = ("S1", "S2", "S3")

DERIVED_STATE_RULE = (
    "au moins un S1/S2/S3 vérifié et aucun item sévère ⇒ `PIPELINE_SUPPLIES` ; "
    "au moins un S1/S2/S3 et au moins un item sévère (M2, ou M1 sur la thèse "
    "centrale) ⇒ `PIPELINE_SUPPLIES_WITH_GAP` ; aucun S1/S2/S3 et au moins un "
    "item sévère ⇒ `ZEROSHOT_WINS` ; sinon `PARITY`, ou `BOTH_ABSTAIN` quand le "
    "juge l'a dit et qu'aucun item n'a été retenu"
)


def derive_state(kept: Sequence[Dict[str, Any]], reported_state: str) -> str:
    """The document's state, derived from its VERIFIED items (#3417).

    Cycle 1 measured why the judge's own label cannot decide the table: on
    one document the judge kept the same single item (an M1 on the central
    thesis) in both cycles and wrote ``PARITY`` the first time and
    ``ZEROSHOT_WINS`` the second. Exhaustion condition 2 compares states
    across cycles, so the state has to be a function of the items: identical
    items give the identical state, whatever the label says.

    The rule is the grid's §3 read on the item codes, with the coordinator's
    severity rule (``severity_of``) standing in for the grid's « manque
    matériel » and « lecture trompeuse »: an M2 is a misleading reading, an
    M1 on the central thesis is a material miss. A moderate M1 (an
    observation off the thesis) is counted as an item and makes no gap.

    ``reported_state`` is consulted for ONE distinction the items cannot
    carry: an empty item list is ``BOTH_ABSTAIN`` when the judge said both
    texts abstain, ``PARITY`` otherwise. The grid's « D » clause (the axis
    that judges read a minority of the text) has no item code, so it cannot
    be verified here: a gap claimed through it alone does not count.
    """
    codes = [str(item.get("code") or "") for item in kept]
    core = any(code in CORE_SURPLUS_CODES for code in codes)
    severe = any(item.get("severity") == SEVERITY_SEVERE for item in kept)
    if core:
        return "PIPELINE_SUPPLIES_WITH_GAP" if severe else "PIPELINE_SUPPLIES"
    if severe:
        return "ZEROSHOT_WINS"
    if not kept and reported_state == "BOTH_ABSTAIN":
        return "BOTH_ABSTAIN"
    return "PARITY"


# ---------------------------------------------------------------------------
# The judge's answer
# ---------------------------------------------------------------------------


def parse_judge_answer(answer: str) -> Dict[str, Any]:
    """Extract the JSON object from a judge answer, or raise ``JudgeUnparsed``.

    The judge is asked for bare JSON; models wrap it in prose anyway. The
    first ``{`` to the matching ``}`` is taken by brace counting, not by a
    regex — a nested object (the items) would defeat the lazy form.
    """
    text = answer or ""
    start = text.find("{")
    while start != -1:
        depth = 0
        for pos in range(start, len(text)):
            char = text[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : pos + 1]
                    try:
                        parsed = json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    if isinstance(parsed, dict):
                        return parsed
                    break
        start = text.find("{", start + 1)
    raise JudgeUnparsed(
        "the judge's answer carries no readable JSON object — counted as "
        "unparsed, never guessed into a verdict"
    )


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------

_PROMPT_HEADER = """Tu es le lecteur-juge de la campagne d'analyse argumentative.

Un document source, et deux textes portent sur lui :
- l'un est une **analyse multi-méthodes** (actes de cadrage, récit, conclusion,
  synthèse ; verdicts formels ; graphe d'argumentation ; détection de
  sophismes ; notes de qualité) ;
- l'autre est une **lecture en un seul passage** du même document.

Tu ne sais pas dans quel ordre ils sont présentés. Identifie-les toi-même.
Le document source est là : c'est lui qui fait foi quand un texte affirme
quelque chose qu'il dément.

## Ce que tu rends

Un objet JSON, et rien d'autre :

{
  "identification": "1" ou "2",
  "state": "PIPELINE_SUPPLIES" | "PIPELINE_SUPPLIES_WITH_GAP" | "PARITY" | "ZEROSHOT_WINS" | "BOTH_ABSTAIN",
  "items": [
    {
      "code": "S1".."S5" | "M1" | "M2",
      "analysis_quote": "extrait EXACT de l'analyse multi-méthodes",
      "reading_quote": "extrait EXACT de la lecture en un seul passage",
      "document_quote": "extrait EXACT du document source",
      "on_central_thesis": true | false,
      "note": "une phrase"
    }
  ],
  "style_notes": ["différence de forme, jamais comptée comme un manque"],
  "conclusion": "une phrase qui nomme la nature dominante du surplus"
}

## Codes

- **S1** formel : un verdict FOL / propositionnel / modal qui discrimine.
- **S2** structurel : une exclusion ou acceptation Dung (présent dans une
  sémantique, absent d'une autre).
- **S3** convergence : au moins trois méthodes indépendantes NOMMÉES qui
  s'accordent. Si la convergence porte sur la revendication la moins étayée,
  dis-le : c'est une fragilité, pas un surplus.
- **S4** honnêteté : le rendu **déclare** une couverture partielle.
- **S5** qualité : une note de vertu qui discrimine. Sous le seuil faible,
  l'axe n'est pas concluable — ne le compte pas comme un acquis.
- **M1** : une observation sur le document qu'AUCUNE ligne de l'analyse ne
  porte. Mets `on_central_thesis` à true si elle porte sur la thèse centrale.
- **M2** : une affirmation de l'analyse que le document démentit, et que la
  lecture en un seul passage lit correctement. Cite dans `document_quote` la
  ligne du document qui démentit — sans elle, l'item n'existe pas.

## Règles de citation — non négociables

Chaque citation doit être **recopiée mot pour mot** du texte qu'elle cite —
l'analyse, la lecture, ou le document. Une citation introuvable fait tomber
l'item : c'est la vérification mécanique qui rend ce jugement falsifiable.
Aucun item sans citation n'existe. Si tu n'as pas la citation exacte,
n'émets pas l'item.

Une différence de **forme** (l'un écrit mieux) n'est pas un M : mets-la dans
`style_notes`.

## Les cinq états

- `PIPELINE_SUPPLIES` : au moins un S1/S2/S3 vérifié, et aucun M2.
- `PIPELINE_SUPPLIES_WITH_GAP` : au moins un S1/S2/S3, et soit un M2, soit un
  manque matériel de lecture côté analyse.
- `PARITY` : aucun S1/S2/S3 ; l'analyse n'ajoute que du détail procédural.
- `ZEROSHOT_WINS` : la lecture en un seul passage est utilisable et l'analyse
  n'en produit aucune, ou en produit une trompeuse.
- `BOTH_ABSTAIN` : l'entrée n'est pas analysable et les deux le disent.
"""


def build_judge_prompt(text_1: str, text_2: str, document: str) -> str:
    """The judge's prompt: the grid, the two texts positionally, the source.

    No arm name appears in it: the roles are the judge's to establish, and
    the mapping back to the arms is the runner's, recorded in the table. The
    document rides WHOLE — the caller refuses to build this prompt on an
    excerpt (#3375 tranche 3), and a prompt too large for the judge fails
    that document loudly at call time, never by silent truncation here.
    """
    return (
        _PROMPT_HEADER
        + "\n## Texte 1\n\n<<<\n"
        + (text_1 or "")
        + "\n>>>\n\n## Texte 2\n\n<<<\n"
        + (text_2 or "")
        + "\n>>>\n\n## Document\n\n<<<\n"
        + (document or "")
        + "\n>>>\n"
    )


# ---------------------------------------------------------------------------
# The arms' texts
# ---------------------------------------------------------------------------


def pipeline_text_from_state(state: Dict[str, Any], signature: Dict[str, Any]) -> str:
    """The pipeline's judged text IS the fiche's full-text section — verbatim.

    One producer, two callers (#3375 tranche 3): ``pipeline_full_text`` in the
    reading-folder renderer builds it, the fiche prints it and the judge reads
    it. The classification and outcome live at the SIGNATURE's root (#1909
    slice 2) — that is why the signature rides along, and a document the
    campaign classified non-argumentative shows the judge its terminal
    classification instead of an empty string.
    """
    from scripts.dataset.render_campaign_reading_folder import pipeline_full_text

    st = state.get("state") or state
    return pipeline_full_text(
        st,
        signature.get("document_classification"),
        str(signature.get("opaque_id") or ""),
        signature.get("outcome") or {},
    )


def arm_health(state: Dict[str, Any]) -> Dict[str, Any]:
    """The pipeline arm's health for ONE document, read from its state dump.

    Degraded = an empty act key AND a non-empty ``restitution_acts_degraded``
    — never either half alone (#3458):

    - a document with no acts BY DESIGN carries neither (empty acts, no
      report): it is not degraded, it is a document the campaign never meant
      to render in three acts;
    - the c2 panel run carries the report on documents whose acts RENDERED
      (the report records per-act retry events, not only hard gaps): the
      report alone must not flag them.

    The conjunctive rule is what separates "the render broke mid-way" (a
    break the judge would grade as the pipeline's own doing) from both
    honest shapes above. The state is unwrapped the way
    ``pipeline_text_from_state`` unwraps it.
    """
    st = state.get("state") or state
    empty_acts = [key for key in ACT_KEYS if not str(st.get(key) or "").strip()]
    reported = bool(st.get("restitution_acts_degraded"))
    return {
        "pipeline_degraded": bool(empty_acts) and reported,
        "empty_acts": empty_acts,
        "acts_degraded_reported": reported,
    }


def document_texts_from_definitions(
    definitions: Sequence[Dict[str, Any]], panel: Sequence[str]
) -> Dict[str, str]:
    """Map each panel id to its WHOLE text, from in-memory definitions.

    ``max_chars=0`` on purpose: the judge sees the source entire or the
    document fails loudly — an excerpt would let a quote be verified against
    a slice the campaign itself never read. A panel id the corpus does not
    carry raises ``ValueError`` (via ``expand_corpus``), naming the id.
    """
    from scripts.dataset.run_corpus_batch import expand_corpus

    docs, _omitted, _skipped = expand_corpus(list(definitions), 0, list(panel))
    return {doc["opaque_id"]: doc["full_text"] for doc in docs}


def _passphrase_or_exit() -> str:
    """The dataset passphrase from the checkout ``.env``, or a loud stop.

    No key, no document — and no fallback to judging without the source:
    a judge that has not read the document cannot rule on what it
    contradicts (#3375).
    """
    from dotenv import load_dotenv

    from scripts.dataset.run_corpus_batch import REPO_ROOT

    load_dotenv(REPO_ROOT / ".env")
    passphrase = os.environ.get("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        raise SystemExit(
            "TEXT_CONFIG_PASSPHRASE is not set — the judge cannot see the "
            "document, and a judge that has not read the source cannot rule "
            "on what it contradicts (#3375)"
        )
    return passphrase


def load_document_records(panel: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """Decrypt the corpus for the panel — in memory only, never persisted.

    Dataset privacy rule 5: the definitions are consumed through
    ``load_extract_definitions`` with the derived key and stay in this
    process. No file, no log, no test output carries them; the only things
    that leave are the prompt (to the judge) and short verified quotes (to
    the gitignored results tree).
    """
    from argumentation_analysis.core.io_manager import load_extract_definitions
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key

    from scripts.dataset.run_corpus_batch import ENCRYPTED_PATH

    passphrase = _passphrase_or_exit()
    key = derive_encryption_key(passphrase)
    if not key:
        raise SystemExit("failed to derive the dataset key from the passphrase")
    definitions = load_extract_definitions(
        config_file=ENCRYPTED_PATH,
        b64_derived_key=key.decode("utf-8"),
        raise_on_decrypt_error=True,
    )
    from scripts.dataset.run_corpus_batch import expand_corpus

    try:
        docs, _, _ = expand_corpus(list(definitions), 0, list(panel))
        return {doc["opaque_id"]: doc for doc in docs}
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def load_document_texts(panel: Sequence[str]) -> Dict[str, str]:
    """The judge's original text-only view of in-memory panel records."""
    return {key: doc["full_text"] for key, doc in load_document_records(panel).items()}


def load_json(path: Path) -> Dict[str, Any]:
    payload: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def resolve_run_pricing(signatures_dir: Path, zeroshot_dir: Path) -> Tuple[str, str]:
    """The pipeline's model and the run head, resolved BEFORE any judgement.

    Delegated to the reading-folder producer: one resolver, two callers. A
    second copy here is how the pipeline's model and the table's model drift
    (the failure #3138 priced a Sonnet-tier campaign at the Haiku row).
    """
    from scripts.dataset.render_campaign_reading_folder import resolve_run_pricing as _r

    signatures = sorted(signatures_dir.glob("signature_*.json"))
    zeroshots = {p.stem: p for p in zeroshot_dir.glob("*.json")}
    return _r(signatures, zeroshots)


def arm_costs(
    signature: Dict[str, Any],
    zeroshot: Dict[str, Any],
    pricing_model: str,
) -> Dict[str, Optional[float]]:
    """Both arms' costs, through the campaign's own two helpers."""
    from scripts.dataset.render_campaign_reading_folder import (
        doc_cost_usd,
        zeroshot_cost_usd,
    )

    return {
        "pipeline": doc_cost_usd(
            signature.get("llm_usage") or {}, pricing_model=pricing_model
        ),
        "zeroshot": zeroshot_cost_usd(zeroshot) if zeroshot else None,
    }


# ---------------------------------------------------------------------------
# Cost of the judging pass, printed BEFORE any call
# ---------------------------------------------------------------------------

# Rough chars-per-token for the estimate. It is an ESTIMATE and the table
# says so; the real figure comes from the provider's usage block afterwards.
CHARS_PER_TOKEN_ESTIMATE = 4
# The judge's answer quotes three sides per item (analysis, reading, document)
# and the long documents carry many items. At 4096 the cycle-0 pass (R1141)
# lost 7 of 10 answers; 16384 bounds the cost, it does not ask for length.
JUDGE_MAX_TOKENS = 16384


# The two wires' names for "the answer was cut at max_tokens".
TRUNCATION_STOP_REASONS = ("max_tokens", "length")


def estimate_judge_cost(
    judge_model: str, prompt_chars: Sequence[int]
) -> Optional[float]:
    """USD estimate for the whole pass, or ``None`` when the model is unpriced.

    One ``price_tokens`` call PER DOCUMENT, summed: a single call on the
    concatenated prompts would bill every document at the whole panel's size
    — the aggregate-vs-per-call confusion #3138 already cost the campaign
    (21.94 $ instead of 8.17 $).
    """
    from argumentation_analysis.services.model_prices import price_tokens

    total = 0.0
    for chars in prompt_chars:
        per_doc = price_tokens(
            judge_model, chars // CHARS_PER_TOKEN_ESTIMATE, JUDGE_MAX_TOKENS
        )
        if per_doc is None:
            return None
        total += per_doc
    return round(total, 4)


# ---------------------------------------------------------------------------
# Endpoints and the one call
# ---------------------------------------------------------------------------


def resolve_judge_endpoint(judge_model: str) -> Dict[str, Any]:
    """The judge's route: the canonical resolver first (#2352), else named env.

    The pipeline arm must measure the route production uses; a judge is not
    production, but it still never guesses — an unconfigured route exits with
    the variables to set, and the table records the host it reached.
    """
    from urllib.parse import urlparse

    from argumentation_analysis.core.llm_service import resolve_chat_endpoint

    want = model_family(judge_model)
    api_key, base_url, model_id = resolve_chat_endpoint()
    if model_family(model_id) == want:
        route = "canonical"
    elif want == "anthropic":
        key, named_base_url, key_source = anthropic_route_pair()
        if not key:
            raise SystemExit(
                f"the judge {judge_model!r} is an Anthropic model and the "
                f"canonical route resolves to {model_id!r}: set "
                f"ANTHROPIC_API_KEY (and optionally ANTHROPIC_BASE_URL) so the "
                f"judge has its own route — never fall back to the pipeline's"
            )
        api_key = key
        # The SDK's convention: ANTHROPIC_BASE_URL names the host WITHOUT the
        # ``/v1`` segment (``https://api.anthropic.com``), and the client adds
        # ``/v1/messages``. ``anthropic_messages_url`` accepts both forms.
        base_url = named_base_url
        route = f"named-anthropic ({key_source})"
    else:
        raise SystemExit(
            f"the judge {judge_model!r} is a {want} model but the canonical "
            f"route resolves to {model_id!r}: no named route exists for "
            f"{want} — configure the route or pick another judge"
        )
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model_id": judge_model,
        "family": want,
        "host": urlparse(base_url).hostname or "",
        "route": route,
    }


ANTHROPIC_DEFAULT_BASE_URL = "https://api.anthropic.com"


def anthropic_route_pair(dotenv_path: Optional[Path] = None) -> Tuple[str, str, str]:
    """The judge's key AND base URL, both from ONE source: ``(key, url, source)``.

    R1143: the repository's ``.env`` carries ``ANTHROPIC_API_KEY`` and no
    ``ANTHROPIC_BASE_URL``, while the agent harness running the script exports
    ``ANTHROPIC_BASE_URL`` for its own local proxy. Taken separately, the key
    came from the file and the URL from the harness: all ten cycle-1 judging
    calls went to ``127.0.0.1:3002`` with the vendor key and answered 401.
    A route is a pair, so the URL now follows the key. When the key is the
    file's (the process carries none, or the same one), the URL is the file's,
    or the vendor's default. When the process carries its own key, the URL is
    the process's. Nothing is guessed: a missing key still returns ``""``.
    """
    from dotenv import dotenv_values

    from scripts.dataset.run_corpus_batch import REPO_ROOT

    path = Path(dotenv_path) if dotenv_path is not None else REPO_ROOT / ".env"
    file_values = dotenv_values(path) if path.is_file() else {}
    file_key = (file_values.get("ANTHROPIC_API_KEY") or "").strip()
    process_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if file_key and process_key in ("", file_key):
        base = (file_values.get("ANTHROPIC_BASE_URL") or "").strip()
        return file_key, base or ANTHROPIC_DEFAULT_BASE_URL, ".env"
    base = (os.environ.get("ANTHROPIC_BASE_URL") or "").strip()
    return process_key, base or ANTHROPIC_DEFAULT_BASE_URL, "process"


def anthropic_messages_url(base_url: str) -> str:
    """``<base>/v1/messages`` whether or not ``base_url`` already ends in ``/v1``.

    The variable the SDK reads (``ANTHROPIC_BASE_URL``) carries no ``/v1``; an
    agent harness exports it that way. Appending ``/messages`` to it alone
    posted every judging call to ``<host>/messages`` and got 404 on the whole
    cycle-0 panel (R1141), so the segment is added here when it is missing.
    """
    base = (base_url or "").strip().rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    return f"{base}/messages"


async def call_judge(
    endpoint: Dict[str, Any], prompt: str, timeout: int = 600
) -> Dict[str, Any]:
    """One judging call. Two wires, because the judge is another family.

    Anthropic's native ``/messages`` and the OpenAI-compatible
    ``/chat/completions`` return their text and their token counts under
    different names; both are normalised here so the table has one shape.
    """
    import httpx

    if endpoint["family"] == "anthropic":
        payload: Dict[str, Any] = {
            "model": endpoint["model_id"],
            "max_tokens": JUDGE_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": endpoint["api_key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = anthropic_messages_url(endpoint["base_url"])
    else:
        payload = {
            "model": endpoint["model_id"],
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": JUDGE_MAX_TOKENS,
        }
        headers = {"Authorization": f"Bearer {endpoint['api_key']}"}
        url = f"{endpoint['base_url'].rstrip('/')}/chat/completions"
    # #3423 — the sampling temperature rides on the endpoint. ``None`` leaves
    # the provider's default, which is what every pass before #3423 ran on.
    if endpoint.get("temperature") is not None:
        payload["temperature"] = endpoint["temperature"]

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        return {
            "status_code": response.status_code,
            "error_body_head": response.text[:500],
        }
    body = response.json()
    if endpoint["family"] == "anthropic":
        blocks = body.get("content") or []
        answer = "".join(
            part.get("text", "") for part in blocks if part.get("type") == "text"
        )
        usage = body.get("usage") or {}
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        stop_reason = body.get("stop_reason")
    else:
        choice = (body.get("choices") or [{}])[0]
        answer = choice.get("message", {}).get("content", "")
        usage = body.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        stop_reason = choice.get("finish_reason")
    return {
        "status_code": 200,
        "answer": answer,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "usage": usage,
        # The model the provider says answered. A route through a proxy can
        # serve another model under the requested name; the family claim of
        # the table rests on this field, not on the id the request carried.
        "answered_model": body.get("model"),
        "stop_reason": stop_reason,
    }


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------


def _money(value: Optional[float]) -> str:
    return "unpriced" if value is None else f"{value:.4f} $"


def render_table(
    rows: Sequence[Dict[str, Any]],
    meta: Dict[str, Any],
    recorded_header: Optional[str] = None,
) -> str:
    """The aggregated verdict table: per document, then the totals.

    Every figure is a count of something the rows carry; nothing is scored.
    The grid's §4 forbids an aggregate score, and this table honours that:
    the last section names a distribution and a dominant nature, not a note.

    ``recorded_header`` (#3417 re-render) is the header block a pass wrote
    before its meta was stored beside its rows: it is kept verbatim, so a
    re-rendered table still names the judge, route and command of the pass.
    """
    lines: List[str] = []
    if recorded_header is not None:
        lines.extend(recorded_header.rstrip("\n").split("\n"))
        if "judge_temperature" not in meta:
            lines.append(f"- Température du juge : {_temperature_label(meta)}")
    else:
        lines.extend(_header_lines(rows, meta))
    _append_state_rule(lines, meta)
    _append_body(lines, rows, meta)
    return "\n".join(lines)


def _append_state_rule(lines: List[str], meta: Dict[str, Any]) -> None:
    lines.append(
        "- État : **dérivé des items vérifiés** (#3417), jamais recopié de "
        f"l'étiquette du juge — {DERIVED_STATE_RULE}. L'étiquette du juge est "
        "imprimée à côté quand elle diffère."
    )
    if meta.get("rerendered_from"):
        lines.append(
            f"- **Re-rendu sans appel du juge** depuis les lignes de "
            f"`{meta['rerendered_from']}` : seuls l'état dérivé et cette table "
            "sont recalculés, les items et les coûts sont ceux du passage."
        )
    if meta.get("consensus_of"):
        sources = meta["consensus_of"]
        need = meta.get("consensus_need", len(sources) // 2 + 1)
        lines.append(
            f"- **Consensus de {len(sources)} passages** sur les mêmes entrées "
            f"({', '.join(f'`{name}`' for name in sources)}), sans appel du juge "
            "(#3423) : chaque passage répond, sur SES items vérifiés, aux deux "
            "questions de la règle — un surplus S1/S2/S3 ? un item sévère ? — "
            "et l'état est la réponse de la majorité. Un document est "
            "**fragile** quand, sur l'une des deux questions, la minorité "
            "atteint un tiers des passages (à 3 passages : toute dissidence) : "
            "un changement d'état sur un document fragile ne mesure pas le "
            f"pipeline. Les items listés sont ceux qu'au moins {need} passages "
            "gardent (même code, citation contenue) ; les items tombés à la "
            "vérification sont comptés dans chaque passage."
        )
    lines.append("")


def _header_lines(rows: Sequence[Dict[str, Any]], meta: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    lines.append("# Table de verdicts — juge à l'aveugle (#3375)")
    lines.append("")
    lines.append(f"- Juge : `{meta['judge_model']}` (famille `{meta['judge_family']}`)")
    if meta.get("judge_host"):
        lines.append(
            f"- Route du juge : `{meta.get('judge_route')}` → hôte "
            f"`{meta['judge_host']}`"
        )
    answered = sorted(
        {row["answered_model"] for row in rows if row.get("answered_model")}
    )
    if answered:
        lines.append(
            "- Modèle(s) ayant répondu, selon le fournisseur : "
            + ", ".join(f"`{model}`" for model in answered)
        )
    lines.append(
        f"- Pipeline : `{meta['pipeline_model']}` (famille "
        f"`{meta['pipeline_family']}`) — la différence de famille est vérifiée"
    )
    lines.append(f"- Graine du tirage A/B : `{meta['seed']}` (par document)")
    lines.append(f"- Température du juge : {_temperature_label(meta)}")
    lines.append(
        "- Le juge a lu le **document source** (bloc `Document`, texte "
        "entier) : un M2 est vérifié contre lui, `document_quote` à l'appui"
    )
    lines.append(
        "- Cécité : **aveugle à l'ordre, pas au style** — les deux textes sont "
        "présentés comme `Texte 1` / `Texte 2`, sans nom d'arm ; la forme du "
        "rendu du pipeline reste reconnaissable, et l'identification du juge "
        "est enregistrée ci-dessous."
    )
    lines.append(f"- Commande : `{meta['command']}`")
    return lines


def _temperature_label(meta: Dict[str, Any]) -> str:
    """How the judge sampled (#3423): a pass at the provider's default
    temperature moves more between two passes than the pipeline moved
    between two cycles, so the table says which one it was."""
    if "judge_temperature" not in meta:
        return "non enregistrée (passage antérieur à #3423 : défaut du fournisseur)"
    value = meta["judge_temperature"]
    if value is None:
        return "défaut du fournisseur (non fixée)"
    return f"`{value}`"


def parse_temperature(text: str) -> Optional[float]:
    """``--judge-temperature``: a number, or ``provider`` for the default."""
    if text.strip().lower() == "provider":
        return None
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"temperature must be a number or 'provider', got {text!r}"
        )
    if value < 0:
        raise argparse.ArgumentTypeError(f"temperature must be >= 0, got {value}")
    return value


def _temperature_arg(value: Optional[float]) -> str:
    return "provider" if value is None else f"{value:g}"


def _append_body(
    lines: List[str], rows: Sequence[Dict[str, Any]], meta: Dict[str, Any]
) -> None:
    lines.append("## Par document")
    lines.append("")
    lines.append(
        "| doc | verdict | ID juge | S | M | sévère | modéré | items tombés | "
        "coût pipeline | coût zero-shot |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        counts = _count_codes(row.get("kept") or [])
        severity = _count_severities(row.get("kept") or [])
        ident = "ok" if row.get("identification_ok") else "**inversée**"
        state_cell = f"`{row.get('state')}`"
        if _label_differs(row):
            state_cell += f" (juge : `{row['reported_state']}`)"
        votes = (row.get("consensus") or {}).get("votes")
        if votes:
            parsed = votes.get("parsed", 0)
            state_cell += (
                f" · votes : surplus {votes.get('core', 0)}/{parsed}, "
                f"sévère {votes.get('severe', 0)}/{parsed}"
            )
            if row["consensus"].get("fragile"):
                state_cell += " **fragile**"
        if row.get("stop_reason") in TRUNCATION_STOP_REASONS:
            state_cell += " **(tronquée à la limite de sortie)**"
        elif row.get("state") == "UNPARSED" and row.get("reported_state"):
            state_cell += f" (état hors grille : `{row['reported_state']}`)"
        if row.get("pipeline_degraded"):
            # #3458 — the arm's health, on the row itself: a state read
            # without this flag would mistake a broken render for the
            # pipeline's own doing.
            state_cell += " **(bras pipeline dégradé)**"
        if row.get("zeroshot_truncated"):
            # #3460 — the baseline's own truncation, on the row itself: a
            # verdict read without this flag counts a cut baseline as a
            # plain pipeline win.
            state_cell += " **(zero-shot tronqué)**"
        if row.get("status_code") not in (200, None):
            # A document whose call failed (a prompt over the judge's context
            # answers 400, a network fault 0) is UNPARSED — and the reader
            # must see WHY, not wonder (#3375 tranche 3: loud, never silent).
            state_cell += f" **(HTTP {row['status_code']})**"
        lines.append(
            f"| `{row['opaque_id']}` | {state_cell} | {ident} | "
            f"{counts['S']} | {counts['M']} | {severity['severe']} | "
            f"{severity['moderate']} | {len(row.get('dropped') or [])} | "
            f"{_money(row['costs'].get('pipeline'))} | "
            f"{_money(row['costs'].get('zeroshot'))} |"
        )
    lines.append("")

    lines.append("## Répartition des états (le chiffre qui décide)")
    lines.append("")
    distribution = _state_distribution(rows)
    for state in STATES:
        if distribution.get(state):
            lines.append(f"- `{state}` : **{distribution[state]}**")
    if distribution.get("UNPARSED"):
        failed = sum(1 for row in rows if row.get("status_code") not in (200, None))
        truncated = sum(
            1
            for row in rows
            if row.get("state") == "UNPARSED"
            and row.get("stop_reason") in TRUNCATION_STOP_REASONS
        )
        unreadable = distribution["UNPARSED"] - failed - truncated
        detail = []
        if failed:
            detail.append(f"{failed} appel(s) échoué(s), sans réponse du juge")
        if truncated:
            detail.append(
                f"{truncated} réponse(s) tronquée(s) à la limite de sortie "
                f"({JUDGE_MAX_TOKENS} tokens)"
            )
        if unreadable:
            detail.append(f"{unreadable} réponse(s) illisible(s)")
        lines.append(
            f"- `UNPARSED` : **{distribution['UNPARSED']}** — "
            + " ; ".join(detail)
            + ", comptés comme tels et jamais convertis en verdict"
        )
    fragile = [
        row["opaque_id"] for row in rows if (row.get("consensus") or {}).get("fragile")
    ]
    if fragile:
        lines.append(
            f"- **fragiles** (minorité d'au moins un tiers des passages sur une "
            f"question décisive) : **{len(fragile)}** document(s) — "
            + ", ".join(f"`{doc_id}`" for doc_id in fragile)
            + " ; leur état est celui de la majorité, et un changement d'état "
            "sur eux ne compte pas pour la condition 2"
        )
    degraded = [row["opaque_id"] for row in rows if row.get("pipeline_degraded")]
    if degraded:
        lines.append(
            f"- **bras pipeline dégradé** : **{len(degraded)}** document(s) — "
            + ", ".join(f"`{doc_id}`" for doc_id in degraded)
            + " ; comptés dans la répartition ci-dessus, mais jamais lus "
            "comme une victoire ou une défaite du pipeline sans ce drapeau "
            "(#3458 : un acte vide ET un signalement de dégradation)"
        )
    zs_truncated = [row["opaque_id"] for row in rows if row.get("zeroshot_truncated")]
    if zs_truncated:
        lines.append(
            f"- **zero-shot tronqué** : **{len(zs_truncated)}** document(s) — "
            + ", ".join(f"`{doc_id}`" for doc_id in zs_truncated)
            + " ; comptés dans la répartition ci-dessus, mais jamais comptés "
            "comme une victoire simple du pipeline : la baseline a été "
            "coupée à sa limite de sortie avant sa conclusion (#3460)"
        )
    differing = [row["opaque_id"] for row in rows if _label_differs(row)]
    if differing:
        lines.append(
            f"- étiquette du juge ≠ état dérivé : **{len(differing)}** "
            "document(s) — "
            + ", ".join(f"`{doc_id}`" for doc_id in differing)
            + " ; la répartition ci-dessus compte l'état dérivé"
        )
    lines.append("")

    lines.append("## Items par classe et par sévérité")
    lines.append("")
    for code in ITEM_CODES:
        total = sum(
            1
            for row in rows
            for item in (row.get("kept") or [])
            if item["code"] == code
        )
        lines.append(f"- **{code}** : {total}")
    lines.append("")

    lines.append("## Items tombés à la vérification mécanique")
    lines.append("")
    total_dropped = sum(len(row.get("dropped") or []) for row in rows)
    lines.append(
        f"**{total_dropped}** item(s) tombés — une citation introuvable n'est "
        "pas un détail de forme : elle retire l'item, et elle est comptée ici."
    )
    lines.append("")
    for row in rows:
        for drop in row.get("dropped") or []:
            lines.append(
                f"- `{row['opaque_id']}` — code `{drop.get('code')}` : "
                f"`{drop.get('reason')}`"
            )
    lines.append("")

    lines.append("## Coût par arm, et coût par état")
    lines.append("")
    pipeline_total = sum(
        row["costs"].get("pipeline") or 0
        for row in rows
        if row["costs"].get("pipeline")
    )
    zeroshot_total = sum(
        row["costs"].get("zeroshot") or 0
        for row in rows
        if row["costs"].get("zeroshot")
    )
    judge_total = sum(row.get("judge_cost") or 0 for row in rows)
    lines.append(f"- pipeline : **{pipeline_total:.4f} $**")
    lines.append(f"- zero-shot : **{zeroshot_total:.4f} $**")
    lines.append(f"- juge (mesuré, tokens rapportés) : **{judge_total:.4f} $**")
    lines.append("")
    for state in STATES:
        in_state = [
            row["costs"].get("pipeline")
            for row in rows
            if row.get("state") == state and row["costs"].get("pipeline") is not None
        ]
        if in_state:
            mean = sum(in_state) / len(in_state)
            lines.append(
                f"- coût pipeline moyen, `{state}` : **{mean:.4f} $** "
                f"({len(in_state)} document(s)) — un surplus qui ne se trouve "
                "que sur les documents chers est une corrélation avec la "
                "longueur, pas un surplus"
            )
    lines.append("")

    lines.append("## Conclusion")
    lines.append("")
    lines.append(meta.get("conclusion") or _dominant_nature(rows))
    lines.append("")


def _label_differs(row: Dict[str, Any]) -> bool:
    """True when the judge's in-grid label is not the derived state (#3417)."""
    reported = row.get("reported_state")
    return reported in STATES and reported != row.get("state")


def _count_codes(items: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "S": sum(1 for item in items if item["code"].startswith("S")),
        "M": sum(1 for item in items if item["code"].startswith("M")),
    }


def _count_severities(items: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "severe": sum(1 for item in items if item.get("severity") == SEVERITY_SEVERE),
        "moderate": sum(
            1 for item in items if item.get("severity") == SEVERITY_MODERATE
        ),
    }


def _state_distribution(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    distribution: Dict[str, int] = {}
    for row in rows:
        state = row.get("state") or "UNPARSED"
        distribution[state] = distribution.get(state, 0) + 1
    return distribution


def _dominant_nature(rows: Sequence[Dict[str, Any]]) -> str:
    """The grid's §4 phrase: name the dominant surplus nature, say nothing else."""
    totals: Dict[str, int] = {}
    for row in rows:
        for item in row.get("kept") or []:
            totals[item["code"]] = totals.get(item["code"], 0) + 1
    surplus = {code: n for code, n in totals.items() if code.startswith("S")}
    if not surplus:
        return (
            "Aucun item de surplus n'a survécu à la vérification : la table ne "
            "nomme pas de nature dominante."
        )
    code = max(surplus, key=lambda key: surplus[key])
    return (
        f"Nature dominante du surplus : **{code}** ({surplus[code]} item(s) "
        "vérifié(s)). La table ne dit rien de la qualité interprétative absolue "
        "des actes, ni de l'exactitude historique des lectures (§1)."
    )


# ---------------------------------------------------------------------------
# #3417 — re-render a pass from its stored rows, and compare two passes
# ---------------------------------------------------------------------------

META_FILENAME = "META.json"
_NON_ROW_FILES = frozenset({META_FILENAME})


def load_rows(
    out_dir: Path, panel: Optional[Sequence[str]] = None
) -> List[Dict[str, Any]]:
    """The rows a pass wrote, in panel order when a panel is given."""
    if panel is not None:
        missing = [doc for doc in panel if not (out_dir / f"{doc}.json").exists()]
        if missing:
            raise SystemExit(
                f"{len(missing)} panel row(s) absent from {out_dir}: "
                f"{', '.join(missing)} — a re-render covers the panel or nothing"
            )
        paths = [out_dir / f"{doc}.json" for doc in panel]
    else:
        paths = sorted(
            path for path in out_dir.glob("*.json") if path.name not in _NON_ROW_FILES
        )
    return [load_json(path) for path in paths]


def rederive_row_state(row: Dict[str, Any]) -> str:
    """The derived state of a stored row — the same rule as a live pass.

    A row whose answer never parsed (failed call, truncated answer) or whose
    label left the grid stays ``UNPARSED``: there is nothing to derive from.
    """
    reported = row.get("reported_state")
    consensus = row.get("consensus") or {}
    if consensus.get("votes"):
        # #3423 — a consensus row is decided by its passes' votes, not by
        # the recurring items it lists.
        return state_from_votes(consensus["votes"])
    if reported in STATES:
        return derive_state(row.get("kept") or [], str(reported))
    return "UNPARSED"


def rerender(
    out_dir: Path, panel: Optional[Sequence[str]] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """Re-derive every row's state and rewrite the table — no judge call.

    The rows are rewritten with the derived ``state`` (the judge's label is
    already kept as ``reported_state``, so nothing is lost), and the table the
    pass first wrote is preserved once as ``TABLE.before-rerender.md`` before
    the new one replaces it.
    """
    rows = load_rows(out_dir, panel)
    for row in rows:
        row["state"] = rederive_row_state(row)
        (out_dir / f"{row['opaque_id']}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    table_path = out_dir / "TABLE.md"
    preserved = out_dir / "TABLE.before-rerender.md"
    recorded_header: Optional[str] = None
    meta_path = out_dir / META_FILENAME
    if meta_path.exists():
        meta = load_json(meta_path)
    else:
        # A pass from before #3417 stored no meta: its own header, verbatim.
        if not table_path.exists():
            raise SystemExit(
                f"{out_dir} carries neither {META_FILENAME} nor TABLE.md — the "
                "re-render cannot say which judge produced these rows"
            )
        recorded_header = table_path.read_text(encoding="utf-8").split(
            "\n## Par document", 1
        )[0]
        meta = {}
    meta["rerendered_from"] = out_dir.name
    if table_path.exists() and not preserved.exists():
        preserved.write_text(table_path.read_text(encoding="utf-8"), encoding="utf-8")
    table = render_table(rows, meta, recorded_header=recorded_header)
    table_path.write_text(table, encoding="utf-8")
    return rows, table


def _item_anchor(item: Dict[str, Any]) -> str:
    """The quote that identifies an item: the side its code must quote."""
    side = "zeroshot" if item.get("code") == "M1" else "pipeline"
    return normalise(item.get(f"{side}_quote") or "")


def _same_item(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Same code, and one pass's anchor quote contains the other's.

    Containment, not equality: two passes over the same texts often cut the
    same passage a few words wider or narrower, and that is the same item.
    """
    if a.get("code") != b.get("code"):
        return False
    qa, qb = _item_anchor(a), _item_anchor(b)
    return bool(qa and qb) and (qa in qb or qb in qa)


def compare_passes(
    rows_a: Sequence[Dict[str, Any]], rows_b: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Per document: how many items both passes kept, and both states."""
    by_id = {row["opaque_id"]: row for row in rows_b}
    report: List[Dict[str, Any]] = []
    for row in rows_a:
        other = by_id.get(row["opaque_id"])
        if other is None:
            continue
        items_a = list(row.get("kept") or [])
        remaining = list(other.get("kept") or [])
        stable: List[str] = []
        for item in items_a:
            for index, candidate in enumerate(remaining):
                if _same_item(item, candidate):
                    stable.append(str(item.get("code")))
                    del remaining[index]
                    break
        report.append(
            {
                "opaque_id": row["opaque_id"],
                "items_a": len(items_a),
                "items_b": len(other.get("kept") or []),
                "stable": len(stable),
                "stable_codes": stable,
                "state_a": rederive_row_state(row),
                "state_b": rederive_row_state(other),
                "label_a": row.get("reported_state"),
                "label_b": other.get("reported_state"),
                "consensus": bool(row.get("consensus") and other.get("consensus")),
                "fragile_a": bool((row.get("consensus") or {}).get("fragile")),
                "fragile_b": bool((other.get("consensus") or {}).get("fragile")),
            }
        )
    return report


def render_stability(report: Sequence[Dict[str, Any]], name_a: str, name_b: str) -> str:
    """The variance of the instrument, as counts — what a cycle delta can mean."""
    lines = [
        "# Stabilité du juge entre deux passages (#3417)",
        "",
        f"- Passage A : `{name_a}` · passage B : `{name_b}`",
        "- Un item est **stable** quand l'autre passage garde un item de même "
        "code dont la citation d'ancrage contient la sienne ou y est contenue "
        "(citation de l'analyse pour S* et M2, de la lecture pour M1).",
        "",
        "| doc | items A | items B | stables | état dérivé A | état dérivé B | "
        "étiquette A | étiquette B |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for entry in report:
        lines.append(
            f"| `{entry['opaque_id']}` | {entry['items_a']} | {entry['items_b']} | "
            f"{entry['stable']} | `{entry['state_a']}` | `{entry['state_b']}` | "
            f"`{entry['label_a']}` | `{entry['label_b']}` |"
        )
    total_a = sum(entry["items_a"] for entry in report)
    total_b = sum(entry["items_b"] for entry in report)
    total_stable = sum(entry["stable"] for entry in report)
    same_state = sum(1 for entry in report if entry["state_a"] == entry["state_b"])
    same_label = sum(1 for entry in report if entry["label_a"] == entry["label_b"])
    lines += [
        "",
        f"- items : **{total_stable}** stables sur {total_a} (A) et {total_b} (B)",
        f"- état dérivé identique : **{same_state}** document(s) sur {len(report)}",
        f"- étiquette du juge identique : **{same_label}** document(s) sur "
        f"{len(report)}",
    ]
    if report and all(entry.get("consensus") for entry in report):
        decided = [
            entry
            for entry in report
            if not entry.get("fragile_a") and not entry.get("fragile_b")
        ]
        contradicted = [e for e in decided if e["state_a"] != e["state_b"]]
        lines.append(
            f"- tranchés (non fragiles) des deux côtés : **{len(decided)}** "
            f"document(s), dont **{len(contradicted)}** d'états différents"
            + (
                " — " + ", ".join(f"`{e['opaque_id']}`" for e in contradicted)
                if contradicted
                else ""
            )
        )
    lines += [
        "",
        "Un écart entre deux cycles qui ne dépasse pas cet écart entre deux "
        "passages du même cycle ne mesure pas le pipeline.",
        "",
    ]
    return "\n".join(lines)


def _write_stability(
    out_dir: Path,
    rows: Sequence[Dict[str, Any]],
    other_dir: Path,
    panel: Optional[Sequence[str]],
) -> None:
    report = compare_passes(rows, load_rows(other_dir, panel))
    (out_dir / "STABILITY.md").write_text(
        render_stability(report, out_dir.name, other_dir.name), encoding="utf-8"
    )
    print(f"stability written: {out_dir / 'STABILITY.md'}", flush=True)


# ---------------------------------------------------------------------------
# #3423 — the consensus of N passes over the same inputs
# ---------------------------------------------------------------------------
#
# Two passes of claude-sonnet-5-5 over identical inputs agreed on the derived
# state on 4 of 10 documents and kept 13 common items out of 28 and 24. The
# model refuses a fixed temperature, so each cycle is judged N times.
#
# What is aggregated was measured on six passes over the cycle-1 inputs, over
# the ten ways of splitting them into two independent triples:
#  - a consensus on ITEM IDENTITY (same code, contained quote) agreed with
#    itself on 5.4 documents of 10 — worse than one pass (5.9 over the 15
#    pairs): the same observation is quoted with a different span from one
#    pass to the next, so on one document all three passes kept a severe M1
#    and the item consensus kept none;
#  - a majority over each pass's two DECIDING QUESTIONS (« a verified S1/S2/S3
#    surplus? », « a verified severe item? ») agreed on 7 of 10 in every split;
#    restricted to documents where both questions are unanimous in both
#    triples, the two triples contradicted each other on 0 documents in 8
#    splits and 1 in 2. Six passes leave three documents split exactly 3/3 on
#    one question: those the judge itself does not decide.
# So each pass answers the two questions from ITS OWN verified items, the
# state is the majority answer, and a document is FRAGILE when, on either
# question, the minority reaches a third of the passes (at three passes: any
# dissent — the unanimity measured above; at six: two dissents or more, which
# on the cycle-1 inputs names exactly the three documents split 3/3). Labels
# are never averaged; items recurring across passes are still listed (with
# their support), as what the reader can check.


def _parsed(row: Dict[str, Any]) -> bool:
    return row.get("reported_state") in STATES and row.get("state") != "UNPARSED"


def pass_answers(row: Dict[str, Any]) -> Dict[str, bool]:
    """One pass's answers to the two questions the state rule asks (#3417)."""
    kept = row.get("kept") or []
    return {
        "core": any(item.get("code") in CORE_SURPLUS_CODES for item in kept),
        "severe": any(item.get("severity") == SEVERITY_SEVERE for item in kept),
        "abstain": not kept and row.get("reported_state") == "BOTH_ABSTAIN",
    }


def state_from_votes(votes: Dict[str, int]) -> str:
    """The consensus state: the majority answer of the passes that parsed."""
    parsed = votes.get("parsed", 0)
    if parsed < votes.get("need", 1):
        return "UNPARSED"  # fewer passes read it than the majority needs

    def majority(key: str) -> bool:
        return votes.get(key, 0) * 2 > parsed

    if majority("core"):
        return (
            "PIPELINE_SUPPLIES_WITH_GAP" if majority("severe") else "PIPELINE_SUPPLIES"
        )
    if majority("severe"):
        return "ZEROSHOT_WINS"
    return "BOTH_ABSTAIN" if majority("abstain") else "PARITY"


def votes_are_fragile(votes: Dict[str, int]) -> bool:
    """True when, on a deciding question, the minority reaches a third of the
    parsed passes — any dissent at three passes, two or more at six."""
    parsed = votes.get("parsed", 0)
    for key in ("core", "severe"):
        yes = votes.get(key, 0)
        if parsed and min(yes, parsed - yes) * 3 >= parsed:
            return True
    return False


def consensus_row(
    rows: Sequence[Dict[str, Any]], sources: Sequence[str]
) -> Dict[str, Any]:
    """One document's consensus over the rows of N passes.

    The state is the majority of the passes' answers to the two deciding
    questions (``pass_answers``), and the row is ``fragile`` when the minority
    on either reaches a third of the passes. Items that at least
    ``N // 2 + 1`` passes keep
    (``_same_item``) are listed with their support, the others as
    ``minority`` — listed, never deciding. A document that fewer than a
    majority of passes could read stays ``UNPARSED``.
    """
    n = len(rows)
    need = n // 2 + 1
    first = rows[0]
    parsed = [row for row in rows if _parsed(row)]
    answers = [pass_answers(row) for row in parsed]
    votes = {
        key: sum(1 for answer in answers if answer[key])
        for key in ("core", "severe", "abstain")
    }
    votes.update({"parsed": len(parsed), "need": need})
    clusters: List[List[Tuple[int, Dict[str, Any]]]] = []
    for index, row in enumerate(parsed):
        for item in row.get("kept") or []:
            for cluster in clusters:
                if index not in {i for i, _ in cluster} and _same_item(
                    cluster[0][1], item
                ):
                    cluster.append((index, item))
                    break
            else:
                clusters.append([(index, item)])
    kept: List[Dict[str, Any]] = []
    minority: List[Dict[str, Any]] = []
    for cluster in clusters:
        item = dict(cluster[0][1])
        central_votes = sum(
            1 for _, member in cluster if member.get("on_central_thesis")
        )
        item["on_central_thesis"] = central_votes >= need
        item["severity"] = severity_of(item["code"], item["on_central_thesis"])
        item["support"] = len(cluster)
        (kept if len(cluster) >= need else minority).append(item)
    labels = [row["reported_state"] for row in parsed]
    reported = Counter(labels).most_common(1)[0][0] if labels else ""
    state = state_from_votes(votes)
    judge_costs = [row.get("judge_cost") for row in rows]
    return {
        "opaque_id": first["opaque_id"],
        "positions": first.get("positions"),
        "identification_ok": first.get("identification_ok"),
        "state": state,
        "reported_state": reported,
        "kept": kept,
        "minority": minority,
        # Mechanical drops belong to each pass; they are counted there.
        "dropped": [],
        "costs": first.get("costs") or {},
        # #3458 — the arm's health crosses into the consensus with the row:
        # a degraded document is never read as a pipeline loss/win without
        # its flag, whichever pass produced the rows.
        "pipeline_degraded": bool(first.get("pipeline_degraded")),
        "pipeline_empty_acts": list(first.get("pipeline_empty_acts") or []),
        # #3460 — the baseline's truncation crosses with it: a cut baseline
        # is never counted as a plain pipeline win, whichever pass produced
        # the rows.
        "zeroshot_truncated": bool(first.get("zeroshot_truncated")),
        "judge_cost": (
            round(sum(judge_costs), 6)
            if all(cost is not None for cost in judge_costs)
            else None
        ),
        "consensus": {
            "passes": n,
            "need": need,
            "parsed": len(parsed),
            "sources": list(sources),
            "votes": votes,
            "fragile": state != "UNPARSED" and votes_are_fragile(votes),
            "pass_states": [str(row.get("state")) for row in rows],
            "dropped_per_pass": [len(row.get("dropped") or []) for row in rows],
        },
    }


def build_consensus(
    pass_dirs: Sequence[Path], out_dir: Path, panel: Optional[Sequence[str]] = None
) -> Tuple[List[Dict[str, Any]], str]:
    """Write the consensus rows and table of ``pass_dirs`` into ``out_dir``."""
    if len(pass_dirs) < 2:
        raise SystemExit("a consensus needs at least two passes (three advised)")
    resolved_out = out_dir.resolve()
    if any(path.resolve() == resolved_out for path in pass_dirs):
        raise SystemExit(
            f"{out_dir} is one of the passes: the consensus goes elsewhere"
        )
    first_rows = load_rows(pass_dirs[0], panel)
    ids = [row["opaque_id"] for row in first_rows]
    passes = [first_rows] + [load_rows(path, ids) for path in pass_dirs[1:]]
    sources = [path.name for path in pass_dirs]
    rows = [
        consensus_row([rows_of[i] for rows_of in passes], sources)
        for i in range(len(ids))
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        (out_dir / f"{row['opaque_id']}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    meta_path = pass_dirs[0] / META_FILENAME
    recorded_header: Optional[str] = None
    if meta_path.exists():
        meta = load_json(meta_path)
    else:
        table_path = pass_dirs[0] / "TABLE.md"
        if not table_path.exists():
            raise SystemExit(
                f"{pass_dirs[0]} carries neither {META_FILENAME} nor TABLE.md — "
                "the consensus cannot say which judge produced these rows"
            )
        recorded_header = table_path.read_text(encoding="utf-8").split(
            "\n## Par document", 1
        )[0]
        meta = {}
    meta["consensus_of"] = sources
    meta["consensus_need"] = len(pass_dirs) // 2 + 1
    (out_dir / META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    table = render_table(rows, meta, recorded_header=recorded_header)
    (out_dir / "TABLE.md").write_text(table, encoding="utf-8")
    return rows, table


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


def _judge_one(
    doc_id: str,
    pipeline_text: str,
    zeroshot_text: str,
    document_text: str,
    seed: int,
    answer: str,
) -> Dict[str, Any]:
    """Pure: one document's answer → its verified row (no I/O, no network)."""
    pos = positions(doc_id, seed)
    try:
        parsed = parse_judge_answer(answer)
    except JudgeUnparsed as exc:
        return {
            "opaque_id": doc_id,
            "positions": pos,
            "state": "UNPARSED",
            "identification_ok": None,
            "kept": [],
            "dropped": [{"index": None, "code": None, "reason": str(exc)}],
            "style_notes": [],
            "conclusion": "",
        }
    reported = str(parsed.get("identification") or "").strip()
    # The judge names a POSITION as "the analysis"; compare it with the draw.
    identification_ok = reported in ("1", "2") and int(reported) == pos["pipeline"]
    reported_state = str(parsed.get("state") or "").strip()
    kept, dropped = validate_items(
        parsed.get("items") or [], pipeline_text, zeroshot_text, document_text
    )
    # #3417 — the state is derived from the verified items, never copied from
    # the judge's label. A label outside the grid still makes the row
    # UNPARSED: an answer that broke the format is not read further.
    state = (
        derive_state(kept, reported_state) if reported_state in STATES else "UNPARSED"
    )
    return {
        "opaque_id": doc_id,
        "positions": pos,
        "reported_identification": reported,
        "identification_ok": identification_ok,
        "state": state,
        # What the judge wrote in ``state``: printed beside the derived state
        # when the two differ (#3417), and the refused word on an UNPARSED row.
        "reported_state": reported_state,
        "kept": kept,
        "dropped": dropped,
        "style_notes": [str(note) for note in (parsed.get("style_notes") or [])],
        "conclusion": str(parsed.get("conclusion") or "").strip(),
    }


async def run(
    argv: Optional[List[str]] = None,
    judge_call: Callable[..., Any] = call_judge,
    document_loader: Optional[Callable[[Sequence[str]], Dict[str, str]]] = None,
) -> int:
    parser = argparse.ArgumentParser(description="#3375 blind judge — v1 panel")
    parser.add_argument(
        "--judge-model", default=None, help="judge model id (required for a pass)"
    )
    parser.add_argument("--doc-ids", default=None, help="panel ids, comma separated")
    parser.add_argument("--panel-file", default=None, help="panel ids, one per line")
    parser.add_argument("--seed", type=int, default=3375, help="A/B draw seed")
    parser.add_argument("--states-dir", type=Path, default=DEFAULT_STATES_DIR)
    parser.add_argument("--signatures-dir", type=Path, default=DEFAULT_SIGNATURES_DIR)
    parser.add_argument("--zeroshot-dir", type=Path, default=DEFAULT_ZEROSHOT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--judge-temperature",
        type=parse_temperature,
        default=None,
        help="#3423: the judge's sampling temperature, recorded in META.json "
        "and the table. Default 'provider' (none sent): claude-sonnet-5-5 "
        "answers 400 « `temperature` is deprecated for this model » (measured "
        "2026-11-05), so a fixed temperature only exists for judges that "
        "accept one; --consensus is the remedy that works on every judge",
    )
    parser.add_argument(
        "--consensus",
        type=Path,
        nargs="+",
        default=None,
        help="#3423: two or more out-dirs of passes over the same inputs; "
        "writes their consensus rows and table into --out-dir — no judge call",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the panel, prompt sizes and estimated cost — no call at all",
    )
    parser.add_argument(
        "--allow-degraded-arm",
        action="store_true",
        help="#3458/#3460: judge a panel whose arm is systemically broken "
        "at or beyond the refusal threshold anyway — a degraded pipeline "
        "arm or a zero-shot baseline cut at its token cap. The override's "
        "use is PRINTED, and every flagged document stays flagged in its "
        "record and the table",
    )
    parser.add_argument(
        "--rerender",
        action="store_true",
        help="#3417: re-derive the states of the rows in --out-dir and rewrite "
        "its table — no judge call, no document read",
    )
    parser.add_argument(
        "--compare-with",
        type=Path,
        default=None,
        help="#3417, with --rerender or --consensus: a second pass's (or "
        "consensus's) out-dir; writes STABILITY.md in --out-dir (items both "
        "kept, per document)",
    )
    args = parser.parse_args(argv)

    from scripts.dataset.run_corpus_batch import parse_doc_ids

    panel = parse_doc_ids(args.doc_ids, args.panel_file)
    if args.rerender and args.consensus:
        parser.error("--rerender and --consensus are two different reads: pick one")
    if args.rerender or args.consensus:
        if args.rerender:
            rows, _table = rerender(args.out_dir, panel)
            print(f"table re-rendered: {args.out_dir / 'TABLE.md'}", flush=True)
        else:
            rows, _table = build_consensus(args.consensus, args.out_dir, panel)
            print(f"consensus written: {args.out_dir / 'TABLE.md'}", flush=True)
        if args.compare_with is not None:
            _write_stability(args.out_dir, rows, args.compare_with, panel)
        return 0
    if args.compare_with is not None:
        parser.error(
            "--compare-with reads stored rows: it goes with --rerender or --consensus"
        )
    if not args.judge_model:
        parser.error("--judge-model is required for a judging pass")
    if panel is None:
        raise SystemExit(
            "no panel given: pass --doc-ids or --panel-file. The v1 bar is a "
            "ten-document panel (#3374), never 'whatever the directory holds'"
        )

    pipeline_model, run_head = resolve_run_pricing(
        args.signatures_dir, args.zeroshot_dir
    )
    judge_family, pipeline_family = assert_judge_differs(
        args.judge_model, pipeline_model
    )

    # The source document, decrypted in memory for the whole panel — the
    # judge rules on what the DOCUMENT contradicts, so it reads the document.
    # Resolved at call time (never a default-arg binding) so a test can
    # replace the loader without touching the encrypted corpus.
    loader = document_loader or load_document_texts
    document_texts = loader(panel)
    absent = [doc_id for doc_id in panel if doc_id not in document_texts]
    if absent:
        raise SystemExit(
            f"{len(absent)} panel document(s) the corpus does not carry: "
            f"{', '.join(absent)} — the judge cannot rule on a document it "
            "cannot read (#3375)"
        )

    documents: List[Dict[str, Any]] = []
    missing: List[str] = []
    for doc_id in panel:
        state_path = args.states_dir / f"state_full_{doc_id}.json"
        sig_path = args.signatures_dir / f"signature_{doc_id}.json"
        zs_path = args.zeroshot_dir / f"{doc_id}.json"
        if not state_path.exists():
            missing.append(f"{doc_id} (no state dump)")
            continue
        zeroshot = load_json(zs_path) if zs_path.exists() else None
        if not zeroshot or not zeroshot.get("answer"):
            missing.append(f"{doc_id} (no zero-shot answer)")
            continue
        # #3460 — the arm's OWN finish_reason is read, never assumed: panel B
        # carried 2 of 10 answers cut at the cap, and a baseline judged as
        # whole biases every verdict toward the pipeline.
        zeroshot_truncated = (
            str(zeroshot.get("finish_reason") or "") in TRUNCATION_STOP_REASONS
        )
        signature = load_json(sig_path) if sig_path.exists() else {}
        state = load_json(state_path)
        documents.append(
            {
                "opaque_id": doc_id,
                "pipeline_text": pipeline_text_from_state(state, signature),
                "zeroshot_text": zeroshot.get("answer") or "",
                "document_text": document_texts[doc_id],
                "zeroshot": zeroshot,
                "costs": arm_costs(signature, zeroshot, pipeline_model),
                # #3458 — the judge reads the arm's health itself, per
                # document, from the same state dump the fiche reads.
                "health": arm_health(state),
                # #3460 — the baseline's own truncation, read from the arm's
                # record (never re-derived from the text: the judge does not
                # truncate or rewrite the arm's response, it flags it).
                "zeroshot_truncated": zeroshot_truncated,
            }
        )
    if missing:
        raise SystemExit(
            f"{len(missing)} panel document(s) without an arm output: "
            f"{', '.join(missing)} — the table cannot be built on a subset "
            "reported as the panel (#3375)"
        )

    prompts = {
        doc["opaque_id"]: build_judge_prompt(
            *(
                (doc["pipeline_text"], doc["zeroshot_text"])
                if positions(doc["opaque_id"], args.seed)["pipeline"] == 1
                else (doc["zeroshot_text"], doc["pipeline_text"])
            ),
            doc["document_text"],
        )
        for doc in documents
    }
    estimate = estimate_judge_cost(
        args.judge_model, [len(prompt) for prompt in prompts.values()]
    )

    if args.dry_run:
        print(f"judge: {args.judge_model} ({judge_family})", flush=True)
        print(
            f"pipeline model: {pipeline_model} ({pipeline_family}) — families differ",
            flush=True,
        )
        # #3478 — the dry-run resolves the judge's route exactly as the paid
        # pass will: configuration only, no network call. A dry-run that
        # certifies a run which cannot start is the seam #3402 already paid
        # for once — an unresolvable route raises the same SystemExit the
        # paid pass would hit, before any call is made, so the exit code
        # says what the paid pass would have said.
        dry_endpoint = resolve_judge_endpoint(args.judge_model)
        print(
            f"judge route: family={dry_endpoint['family']} "
            f"host={dry_endpoint['host']} route={dry_endpoint['route']}",
            flush=True,
        )
        print(f"seed: {args.seed}", flush=True)
        print(
            f"judge temperature: {_temperature_arg(args.judge_temperature)}",
            flush=True,
        )
        print(f"candidate documents: {len(documents)}", flush=True)
        for doc in documents:
            doc_id = doc["opaque_id"]
            pos = positions(doc_id, args.seed)
            print(
                f"  {doc_id}  pipeline={len(doc['pipeline_text'])}c  "
                f"zeroshot={len(doc['zeroshot_text'])}c  "
                f"document={len(doc['document_text'])}c  "
                f"prompt={len(prompts[doc_id])}c  "
                f"pipeline_is_texte_{pos['pipeline']}",
                flush=True,
            )
        unpriced = estimate is None
        print(
            f"estimated judge cost: "
            f"{'unpriced (the model is not in the price table)' if unpriced else f'{estimate:.4f} $'}",
            flush=True,
        )
        print("dry-run: no call made", flush=True)
        return 0

    # #3458 — the arm's health gate: a systemically broken pipeline arm is
    # refused BEFORE the first paid call. The judge would grade a broken
    # render as the pipeline's own doing, and no consensus of judges repairs
    # that — the only honest move is to refuse and name the documents.
    degraded_ids = [
        doc["opaque_id"] for doc in documents if doc["health"]["pipeline_degraded"]
    ]
    if len(degraded_ids) >= DEGRADED_ARM_REFUSAL_THRESHOLD:
        if args.allow_degraded_arm:
            print(
                f"--allow-degraded-arm: judging {len(degraded_ids)} degraded "
                f"document(s) at or beyond the refusal threshold "
                f"({DEGRADED_ARM_REFUSAL_THRESHOLD}) anyway — every one stays "
                "flagged in its record and the table (#3458)",
                flush=True,
            )
        else:
            print(
                f"REFUSED: {len(degraded_ids)}/{len(documents)} document(s) "
                "carry a degraded pipeline arm (an empty act AND a non-empty "
                "restitution_acts_degraded): "
                + ", ".join(f"`{doc_id}`" for doc_id in degraded_ids)
                + f" — at or beyond DEGRADED_ARM_REFUSAL_THRESHOLD="
                f"{DEGRADED_ARM_REFUSAL_THRESHOLD}. The judge would grade a "
                "broken render, not the pipeline; refusing before the first "
                "paid call (#3458). Pass --allow-degraded-arm to judge anyway.",
                flush=True,
            )
            return 3

    # #3460 — the same mechanism for the baseline arm: a systemically
    # truncated zero-shot is refused before the first paid call. Judging a
    # baseline that was never finished measures the cap, not the model —
    # and the bias always goes toward the pipeline.
    truncated_ids = [doc["opaque_id"] for doc in documents if doc["zeroshot_truncated"]]
    if len(truncated_ids) >= DEGRADED_ARM_REFUSAL_THRESHOLD:
        if args.allow_degraded_arm:
            print(
                f"--allow-degraded-arm: judging {len(truncated_ids)} "
                "document(s) whose zero-shot baseline was cut at its token "
                f"cap, at or beyond the refusal threshold "
                f"({DEGRADED_ARM_REFUSAL_THRESHOLD}) anyway — every one "
                "stays flagged in its record and the table (#3460)",
                flush=True,
            )
        else:
            print(
                f"REFUSED: {len(truncated_ids)}/{len(documents)} document(s) "
                "carry a zero-shot baseline cut at its token cap "
                "(finish_reason length/max_tokens): "
                + ", ".join(f"`{doc_id}`" for doc_id in truncated_ids)
                + f" — at or beyond DEGRADED_ARM_REFUSAL_THRESHOLD="
                f"{DEGRADED_ARM_REFUSAL_THRESHOLD}. The judge would grade a "
                "baseline that was not finished, and the bias would always "
                "go toward the pipeline; refusing before the first paid "
                "call (#3460). Pass --allow-degraded-arm to judge anyway.",
                flush=True,
            )
            return 3

    endpoint = {
        **resolve_judge_endpoint(args.judge_model),
        "temperature": args.judge_temperature,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for doc in documents:
        doc_id = doc["opaque_id"]
        t0 = time.time()
        try:
            record = await judge_call(endpoint, prompts[doc_id], args.timeout)
        except Exception as exc:  # network-level: named, never silent
            record = {"status_code": 0, "error_body_head": repr(exc)}
        elapsed = round(time.time() - t0, 1)
        row = _judge_one(
            doc_id,
            doc["pipeline_text"],
            doc["zeroshot_text"],
            doc["document_text"],
            args.seed,
            record.get("answer") or "",
        )
        row["costs"] = doc["costs"]
        # #3458 — the arm's health rides in the record: a degraded doc's
        # state is never read as a pipeline loss/win without this flag.
        row["pipeline_degraded"] = doc["health"]["pipeline_degraded"]
        row["pipeline_empty_acts"] = doc["health"]["empty_acts"]
        row["zeroshot_truncated"] = doc["zeroshot_truncated"]
        row["elapsed_seconds"] = elapsed
        row["status_code"] = record.get("status_code")
        row["error_body_head"] = record.get("error_body_head")
        row["answered_model"] = record.get("answered_model")
        row["stop_reason"] = record.get("stop_reason")
        row["prompt_tokens"] = record.get("prompt_tokens")
        row["completion_tokens"] = record.get("completion_tokens")
        # The raw answer, as the module docstring promises: an UNPARSED row
        # with no answer kept cannot be diagnosed, only paid for again.
        # The output folder is gitignored (results/), like every judgement.
        row["answer"] = record.get("answer")
        from argumentation_analysis.services.model_prices import price_tokens

        observed = price_tokens(
            args.judge_model,
            record.get("prompt_tokens", 0) or 0,
            record.get("completion_tokens", 0) or 0,
        )
        row["judge_cost"] = round(observed, 6) if observed is not None else None
        rows.append(row)
        (args.out_dir / f"{doc_id}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(
            f"[{doc_id}] {row['state']} — kept {len(row['kept'])}, "
            f"dropped {len(row['dropped'])} in {elapsed}s",
            flush=True,
        )

    meta = {
        "judge_model": args.judge_model,
        "judge_family": judge_family,
        "pipeline_model": pipeline_model,
        "pipeline_family": pipeline_family,
        "seed": args.seed,
        "judge_temperature": args.judge_temperature,
        "run_head": run_head,
        "judge_host": endpoint.get("host"),
        "judge_route": endpoint.get("route"),
        # Replayable as typed (#2353): the panel selectors ride in the
        # command, so the recorded line re-runs the same ten documents.
        "command": (
            "PYTHONPATH=. python scripts/dataset/judge_panel.py "
            f"--judge-model {args.judge_model}"
            + (f" --doc-ids {args.doc_ids}" if args.doc_ids else "")
            + (f" --panel-file {args.panel_file}" if args.panel_file else "")
            + f" --seed {args.seed}"
            + f" --judge-temperature {_temperature_arg(args.judge_temperature)}"
            + (" --allow-degraded-arm" if args.allow_degraded_arm else "")
        ),
    }
    # #3417 — the meta rides beside the rows, so a re-render names this pass's
    # judge, route and command without reading them back out of a table.
    (args.out_dir / META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    table = render_table(rows, meta)
    (args.out_dir / "TABLE.md").write_text(table, encoding="utf-8")
    print(f"table written: {args.out_dir / 'TABLE.md'}", flush=True)
    failed = [row["opaque_id"] for row in rows if row.get("status_code") != 200]
    truncated = [
        row["opaque_id"]
        for row in rows
        if row.get("status_code") == 200
        and row.get("state") == "UNPARSED"
        and row.get("stop_reason") in TRUNCATION_STOP_REASONS
    ]
    if failed or truncated:
        # The table is kept (it names each failure), but a pass that did not
        # judge the whole panel is not a measurement of the panel: the exit
        # code says so, so no caller reads a 10/10 HTTP failure as a run.
        if failed:
            print(
                f"{len(failed)}/{len(rows)} judging call(s) failed: "
                f"{', '.join(failed)}",
                flush=True,
            )
        if truncated:
            print(
                f"{len(truncated)}/{len(rows)} answer(s) cut at "
                f"{JUDGE_MAX_TOKENS} output tokens: {', '.join(truncated)}",
                flush=True,
            )
        print("the panel was NOT judged in full", flush=True)
        return 2
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    return asyncio.run(run(argv))


if __name__ == "__main__":
    raise SystemExit(main())
