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


def load_document_texts(panel: Sequence[str]) -> Dict[str, str]:
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
    try:
        return document_texts_from_definitions(definitions, panel)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


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
        payload = {
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


def render_table(rows: Sequence[Dict[str, Any]], meta: Dict[str, Any]) -> str:
    """The aggregated verdict table: per document, then the totals.

    Every figure is a count of something the rows carry; nothing is scored.
    The grid's §4 forbids an aggregate score, and this table honours that:
    the last section names a distribution and a dominant nature, not a note.
    """
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
    lines.append("")

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
        if row.get("stop_reason") in TRUNCATION_STOP_REASONS:
            state_cell += " **(tronquée à la limite de sortie)**"
        elif row.get("state") == "UNPARSED" and row.get("reported_state"):
            state_cell += f" (état hors grille : `{row['reported_state']}`)"
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
    return "\n".join(lines)


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
    state = str(parsed.get("state") or "").strip()
    reported_state = state
    if state not in STATES:
        state = "UNPARSED"
    kept, dropped = validate_items(
        parsed.get("items") or [], pipeline_text, zeroshot_text, document_text
    )
    return {
        "opaque_id": doc_id,
        "positions": pos,
        "reported_identification": reported,
        "identification_ok": identification_ok,
        "state": state,
        # What the judge wrote in ``state``, kept when it is not one of the
        # grid's five: an UNPARSED row must say which word it refused.
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
    parser.add_argument("--judge-model", required=True, help="judge model id")
    parser.add_argument("--doc-ids", default=None, help="panel ids, comma separated")
    parser.add_argument("--panel-file", default=None, help="panel ids, one per line")
    parser.add_argument("--seed", type=int, default=3375, help="A/B draw seed")
    parser.add_argument("--states-dir", type=Path, default=DEFAULT_STATES_DIR)
    parser.add_argument("--signatures-dir", type=Path, default=DEFAULT_SIGNATURES_DIR)
    parser.add_argument("--zeroshot-dir", type=Path, default=DEFAULT_ZEROSHOT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the panel, prompt sizes and estimated cost — no call at all",
    )
    args = parser.parse_args(argv)

    from scripts.dataset.run_corpus_batch import parse_doc_ids

    panel = parse_doc_ids(args.doc_ids, args.panel_file)
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
        signature = load_json(sig_path) if sig_path.exists() else {}
        documents.append(
            {
                "opaque_id": doc_id,
                "pipeline_text": pipeline_text_from_state(
                    load_json(state_path), signature
                ),
                "zeroshot_text": zeroshot.get("answer") or "",
                "document_text": document_texts[doc_id],
                "zeroshot": zeroshot,
                "costs": arm_costs(signature, zeroshot, pipeline_model),
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
        print(f"seed: {args.seed}", flush=True)
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

    endpoint = resolve_judge_endpoint(args.judge_model)
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
        ),
    }
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
