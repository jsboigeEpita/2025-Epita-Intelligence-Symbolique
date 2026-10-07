"""TextToKB SK Plugin — NL extraction to knowledge base with iterative descent.

Wraps NL argument/belief extraction as @kernel_function methods for LLM agents.
Supports PL, FOL, and Modal logic targets with Pydantic-validated output.
For long texts, splits into paragraphs and extracts in parallel via asyncio.gather.

Issue #474: Semantic plugin TextToKBPlugin (NL extraction with iterative descent).
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models for validated extraction output
# ---------------------------------------------------------------------------


class ExtractedPremise(BaseModel):
    text: str = Field(..., description="Original NL premise text")
    formal: Optional[str] = Field(None, description="Formal representation")
    sort: Optional[str] = Field(None, description="FOL sort/category")


class ExtractedArgument(BaseModel):
    id: str = Field(..., description="Unique argument identifier")
    text: str = Field(..., description="Full argument text")
    premises: List[ExtractedPremise] = Field(default_factory=list)
    conclusion: str = Field(..., description="Argument conclusion")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    # #2973 (Expected 2): the offset the heuristic producer extracted this
    # argument's first sentence FROM, in the source text — recorded at split
    # time, where the position is known exactly, so no search is needed.
    # None when the producer could not record it (the search in
    # ``add_argument`` remains the fallback for those).
    text_offset: Optional[int] = Field(
        None, description="Source-text offset of the argument's first sentence"
    )


class FOLSignature(BaseModel):
    predicates: List[str] = Field(default_factory=list)
    constants: List[str] = Field(default_factory=list)
    sorts: List[str] = Field(default_factory=list)


class KBExtractionResult(BaseModel):
    arguments: List[ExtractedArgument] = Field(default_factory=list)
    belief_candidates: List[str] = Field(
        default_factory=list,
        description="NL statements suitable for formal belief sets",
    )
    fol_signature: Optional[FOLSignature] = None
    target_logic: str = Field(
        "fol", description="Target logic type: propositional, fol, or modal"
    )
    source_length: int = Field(0, description="Character count of source text")
    chunk_count: int = Field(1, description="Number of chunks processed")


# ---------------------------------------------------------------------------
# Internal extraction helpers
# ---------------------------------------------------------------------------

_ARG_PATTERN = re.compile(
    r"(?:premièrement|deuxièmement|tout d'abord|en outre|par ailleurs|de plus|"
    r"en effet|or|donc|ainsi|par conséquent|c'est pourquoi|il s'ensuit|"
    r"firstly|secondly|moreover|furthermore|therefore|thus|hence|consequently|"
    r"because|since|so|accordingly)\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# The period of a common abbreviation is not a sentence end. This list is a
# convenience, not the guarantee: a missed abbreviation merges two sentences,
# it never drops text (the JOIN rule below is what guarantees no word is
# lost — #2982).
_ABBREVIATION_TAIL = re.compile(
    r"(?:\b(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr|vs|etc|al|cf|no|art|p|pp|M|Mme|Mlle)\.|"
    r"(?:e\.g|i\.e|etc)\.)$",
    re.IGNORECASE,
)

# A fragment this short is not a sentence of its own: it joins its neighbour.
# It is a JOIN threshold, never a drop threshold (#2982 — a piece of 20
# characters or fewer used to be discarded, losing the attribution words).
_MIN_SENTENCE_CHARS = 20


def _split_sentences_with_offsets(text: str) -> List[Tuple[str, int]]:
    """#2973 — the same split as ``_split_sentences``, positionally.

    Each surviving sentence carries the offset of its FIRST content
    character in ``text``. A sentence assembled by the join rule (short
    piece, or previous piece ending on an abbreviation) keeps the offset of
    the piece that opened it — the group starts where its first sentence
    starts. The sentence TEXTS are byte-identical to ``_split_sentences``
    (same pieces, same joins): only positions are added.
    """
    # Pieces between separators, with their absolute positions. The pattern
    # has no capture groups (lookbehind), so finditer spans partition the
    # text exactly the way .split() pieces do.
    pieces: List[Tuple[str, int]] = []
    last = 0
    for m in _SENTENCE_SPLIT.finditer(text):
        pieces.append((text[last : m.start()], last))
        last = m.end()
    pieces.append((text[last:], last))

    sentences: List[Tuple[str, int]] = []
    for piece, piece_at in pieces:
        stripped = piece.strip()
        if not stripped:
            continue
        content_at = piece_at + (len(piece) - len(piece.lstrip()))
        if sentences and (
            len(stripped) <= _MIN_SENTENCE_CHARS
            or _ABBREVIATION_TAIL.search(sentences[-1][0])
        ):
            sentences[-1] = (f"{sentences[-1][0]} {stripped}", sentences[-1][1])
        else:
            sentences.append((stripped, content_at))
    return sentences


def _split_sentences(text: str) -> List[str]:
    """Split into sentences WITHOUT losing text (#2982).

    Two traps, both measured on the 06/10 paid run:

    * a period after an abbreviation (``Mr.``) is not a sentence end, yet the
      splitter cut there;
    * a fragment of 20 characters or fewer was DISCARDED, which dropped the
      attribution words (``He knows that``) from the unit.

    A piece no real sentence end separates — because the previous piece ends
    on an abbreviation, or because the piece is too short to stand alone —
    joins its neighbour. Every character of ``text`` survives into some
    returned sentence, whitespace-normalised.
    """
    return [sentence for sentence, _ in _split_sentences_with_offsets(text)]


def _split_into_chunks(text: str, max_chars: int = 2000) -> List[Tuple[str, int]]:
    """Split text into paragraph-based chunks for parallel processing.

    #2973 — each chunk is an EXACT SUBSTRING of ``text`` (from its first
    paragraph's first content character to its last paragraph's last content
    character) and carries the source offset of that first character. A
    position measured inside the chunk translates to a source-text position
    by simple addition — no search, no ambiguity between duplicate
    occurrences. The extraction OUTPUT is unchanged: paragraphs are the same
    stripped strings, the greedy max_chars grouping follows the same
    arithmetic, and only the whitespace BETWEEN paragraphs of one chunk
    (previously normalised to ``\\n\\n``) now travels through as written.
    """
    # Paragraph spans on the original text. re.finditer over "\n\n+" yields
    # the same non-empty paragraph sequence text.split("\n\n") did (runs of
    # separators produced empty pieces that the old filter dropped).
    paragraphs: List[Tuple[str, int]] = []  # (stripped paragraph, content start)
    last = 0
    for m in re.finditer(r"\n\n+", text):
        para = text[last : m.start()]
        if para.strip():
            paragraphs.append((para.strip(), last + (len(para) - len(para.lstrip()))))
        last = m.end()
    para = text[last:]
    if para.strip():
        paragraphs.append((para.strip(), last + (len(para) - len(para.lstrip()))))
    if not paragraphs:
        return [(text, 0)]

    def _chunk_span(paras: List[Tuple[str, int]]) -> Tuple[str, int]:
        """Exact substring covering ``paras``: first content char to last."""
        start = paras[0][1]
        last_para, last_start = paras[-1]
        return text[start : last_start + len(last_para)], start

    chunks: List[Tuple[str, int]] = []
    current: List[Tuple[str, int]] = []
    current_len = 0  # joined length of ``current`` (same arithmetic as before)
    for para, pstart in paragraphs:
        add = len(para) + (2 if current else 0)
        if current_len + add > max_chars and current:
            chunks.append(_chunk_span(current))
            current = [(para, pstart)]
            current_len = len(para)
        else:
            current.append((para, pstart))
            current_len += add
    if current:
        chunks.append(_chunk_span(current))
    return chunks if chunks else [(text, 0)]


def _heuristic_extract_arguments(
    text: str, base_offset: int = 0
) -> List[ExtractedArgument]:
    """Extract arguments heuristically from text when LLM is unavailable.

    #2973 — ``base_offset`` is the source-text offset of ``text[0]`` (0 for a
    whole document, the chunk origin otherwise). Each argument records
    ``text_offset = base_offset + (offset of its first sentence)``: the TRUE
    position it was extracted from, known exactly at split time — not a
    ``find()`` first-occurrence guess that conflates duplicate sentences.
    """
    arguments: List[ExtractedArgument] = []
    sentences = _split_sentences_with_offsets(text)

    # Group consecutive sentences into argument-like units
    # triggered by argument markers
    current_group: List[str] = []
    group_start = 0  # offset (within ``text``) of the group's first sentence
    arg_idx = 0

    def _flush() -> None:
        nonlocal arg_idx
        arg_idx += 1
        arg_text = " ".join(current_group)
        premises = [ExtractedPremise(text=s) for s in current_group[:-1] if len(s) > 15]
        conclusion = current_group[-1] if current_group else arg_text
        arguments.append(
            ExtractedArgument(
                id=f"arg_{arg_idx}",
                text=arg_text,
                premises=premises,
                conclusion=conclusion,
                confidence=0.3,
                text_offset=base_offset + group_start,
            )
        )

    for sent, sent_at in sentences:
        is_marker = bool(_ARG_PATTERN.search(sent.split(",")[0]))
        if is_marker and current_group:
            _flush()
            current_group = [sent]
            group_start = sent_at
        else:
            if not current_group:
                group_start = sent_at
            current_group.append(sent)

    if current_group:
        _flush()

    return arguments


def _extract_fol_signature(arguments: List[ExtractedArgument]) -> FOLSignature:
    """Derive FOL signature from extracted arguments."""
    predicates: set = set()
    constants: set = set()
    sorts: set = set()

    for arg in arguments:
        for premise in arg.premises:
            if premise.sort:
                sorts.add(premise.sort)
            if premise.formal:
                # Extract predicate names: word followed by (
                preds = re.findall(r"(\w+)\s*\(", premise.formal)
                predicates.update(preds)
                # Extract constants: lowercase words not followed by (
                consts = re.findall(r"\b([a-z]\w*)\b", premise.text[:100])
                constants.update(consts[:3])  # Limit per premise

    return FOLSignature(
        predicates=sorted(predicates)[:20],
        constants=sorted(constants)[:20],
        sorts=sorted(sorts)[:10],
    )


async def _extract_chunk(
    chunk: str, target_logic: str, chunk_idx: int, base_offset: int = 0
) -> KBExtractionResult:
    """Extract KB from a single chunk (heuristic-only, LLM path available via SK).

    #2973 — ``base_offset`` is the chunk's origin in the source text, so the
    arguments carry true source-text offsets.
    """
    arguments = _heuristic_extract_arguments(chunk, base_offset)

    belief_candidates = [
        arg.conclusion for arg in arguments if len(arg.conclusion) > 10
    ]

    fol_sig = (
        _extract_fol_signature(arguments) if target_logic in ("fol", "all") else None
    )

    return KBExtractionResult(
        arguments=arguments,
        belief_candidates=belief_candidates,
        fol_signature=fol_sig,
        target_logic=target_logic,
        source_length=len(chunk),
        chunk_count=1,
    )


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------


class TextToKBPlugin:
    """Semantic Kernel plugin for NL → Knowledge Base extraction.

    Provides @kernel_function methods that extract arguments, beliefs,
    and FOL signatures from natural language text. Supports iterative
    descent for long texts via paragraph splitting + asyncio.gather.

    Usage:
        kernel.add_plugin(TextToKBPlugin(), plugin_name="text_to_kb")
    """

    @kernel_function(
        name="extract_kb",
        description=(
            "Extraire une base de connaissances structuree a partir d'un texte. "
            "Identifie arguments, premisses, conclusions, croyances candidates. "
            "Supporte PL, FOL, Modal via parametre target_logic. "
            "Entree: texte NL. Retourne JSON valide avec arguments, fol_signature."
        ),
    )
    async def extract_kb(self, text: str, target_logic: str = "fol") -> str:
        """Extract KB from NL text with iterative descent for long texts."""
        if not text or not text.strip():
            return json.dumps({"error": "Empty text provided"})

        target_logic = target_logic.lower().strip()
        if target_logic not in ("propositional", "fol", "modal", "all"):
            target_logic = "fol"

        chunks = _split_into_chunks(text)

        if len(chunks) == 1:
            result = await _extract_chunk(chunks[0][0], target_logic, 0, chunks[0][1])
        else:
            tasks = [
                _extract_chunk(chunk, target_logic, idx, origin)
                for idx, (chunk, origin) in enumerate(chunks)
            ]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Merge results
            all_args: List[ExtractedArgument] = []
            all_beliefs: List[str] = []
            fol_sig = FOLSignature()
            total_len = 0

            for idx, cr in enumerate(chunk_results):
                if isinstance(cr, Exception):
                    logger.warning("Chunk %d extraction failed: %s", idx, cr)
                    continue
                # Re-index arguments to avoid ID collisions across chunks
                for arg in cr.arguments:
                    arg.id = f"arg_{len(all_args) + 1}"
                    all_args.append(arg)
                all_beliefs.extend(cr.belief_candidates)
                total_len += cr.source_length
                if cr.fol_signature:
                    fol_sig.predicates.extend(cr.fol_signature.predicates)
                    fol_sig.constants.extend(cr.fol_signature.constants)
                    fol_sig.sorts.extend(cr.fol_signature.sorts)

            result = KBExtractionResult(
                arguments=all_args,
                belief_candidates=all_beliefs,
                fol_signature=fol_sig if fol_sig.predicates or fol_sig.sorts else None,
                target_logic=target_logic,
                source_length=total_len,
                chunk_count=len(chunks),
            )

        return result.model_dump_json()

    @kernel_function(
        name="extract_arguments_only",
        description=(
            "Extraire uniquement les arguments d'un texte (sans signature FOL). "
            "Entree: texte NL. Retourne JSON avec liste d'arguments structures."
        ),
    )
    async def extract_arguments_only(self, text: str) -> str:
        """Extract only arguments from text (lighter-weight extraction)."""
        if not text or not text.strip():
            return json.dumps({"error": "Empty text provided"})

        chunks = _split_into_chunks(text)

        if len(chunks) == 1:
            arguments = _heuristic_extract_arguments(chunks[0][0], chunks[0][1])
            return json.dumps(
                {
                    "arguments": [a.model_dump() for a in arguments],
                    "count": len(arguments),
                    "source_length": len(text),
                }
            )

        # Parallel extraction for multi-chunk
        async def _extract_args(chunk: str, origin: int) -> List[ExtractedArgument]:
            return _heuristic_extract_arguments(chunk, origin)

        results = await asyncio.gather(
            *[_extract_args(c, origin) for c, origin in chunks],
            return_exceptions=True,
        )

        all_args: List[ExtractedArgument] = []
        for r in results:
            if isinstance(r, Exception):
                continue
            for arg in r:
                arg.id = f"arg_{len(all_args) + 1}"
                all_args.append(arg)

        return json.dumps(
            {
                "arguments": [a.model_dump() for a in all_args],
                "count": len(all_args),
                "source_length": len(text),
                "chunk_count": len(chunks),
            }
        )

    @kernel_function(
        name="write_kb_to_state",
        description=(
            "Ecrire les resultats d'extraction KB dans l'etat d'analyse. "
            "Entree: JSON avec 'arguments', 'belief_candidates', 'target_logic'. "
            "Retourne JSON avec IDs assignes."
        ),
    )
    def write_kb_to_state(self, input: str, state: object = None) -> str:
        """Write extracted KB results into the analysis state."""
        if state is None:
            return json.dumps({"error": "No state provided"})

        try:
            params = json.loads(input) if isinstance(input, str) else input
        except (json.JSONDecodeError, TypeError):
            return json.dumps({"error": "Invalid JSON input"})

        arguments = params.get("arguments", [])
        belief_candidates = params.get("belief_candidates", [])
        target_logic = params.get("target_logic", "fol")

        arg_ids = []
        belief_ids = []

        # Write arguments to state
        add_arg = getattr(state, "add_argument", None)
        if callable(add_arg):
            for arg_data in arguments:
                if isinstance(arg_data, dict):
                    text = arg_data.get("text", "")
                    # #2973 — the producer-recorded source offset rides the
                    # payload; ``add_argument`` uses it directly (search is
                    # only the fallback).
                    offset = arg_data.get("text_offset")
                    if isinstance(offset, bool) or not isinstance(offset, int):
                        offset = None
                else:
                    text = str(arg_data)
                    offset = None
                if text:
                    arg_ids.append(add_arg(text, offset=offset))

        # Write belief candidates as belief sets
        add_bs = getattr(state, "add_belief_set", None)
        if callable(add_bs):
            for belief_text in belief_candidates:
                if isinstance(belief_text, str) and belief_text.strip():
                    belief_ids.append(add_bs(target_logic, belief_text))

        return json.dumps(
            {
                "arguments_written": len(arg_ids),
                "argument_ids": arg_ids,
                "beliefs_written": len(belief_ids),
                "belief_ids": belief_ids,
            }
        )
