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
from typing import Dict, List, Optional

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


def _split_into_chunks(text: str, max_chars: int = 2000) -> List[str]:
    """Split text into paragraph-based chunks for parallel processing."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: List[str] = []
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks if chunks else [text]


def _heuristic_extract_arguments(text: str) -> List[ExtractedArgument]:
    """Extract arguments heuristically from text when LLM is unavailable."""
    arguments: List[ExtractedArgument] = []
    sentences = _SENTENCE_SPLIT.split(text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    # Group consecutive sentences into argument-like units
    # triggered by argument markers
    current_group: List[str] = []
    arg_idx = 0

    for sent in sentences:
        is_marker = bool(_ARG_PATTERN.search(sent.split(",")[0]))
        if is_marker and current_group:
            arg_idx += 1
            arg_text = " ".join(current_group)
            premises = [
                ExtractedPremise(text=s)
                for s in current_group[:-1]
                if len(s) > 15
            ]
            conclusion = current_group[-1] if current_group else arg_text
            arguments.append(
                ExtractedArgument(
                    id=f"arg_{arg_idx}",
                    text=arg_text,
                    premises=premises,
                    conclusion=conclusion,
                    confidence=0.3,
                )
            )
            current_group = [sent]
        else:
            current_group.append(sent)

    if current_group:
        arg_idx += 1
        arg_text = " ".join(current_group)
        premises = [
            ExtractedPremise(text=s) for s in current_group[:-1] if len(s) > 15
        ]
        conclusion = current_group[-1] if current_group else arg_text
        arguments.append(
            ExtractedArgument(
                id=f"arg_{arg_idx}",
                text=arg_text,
                premises=premises,
                conclusion=conclusion,
                confidence=0.3,
            )
        )

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
    chunk: str, target_logic: str, chunk_idx: int
) -> KBExtractionResult:
    """Extract KB from a single chunk (heuristic-only, LLM path available via SK)."""
    arguments = _heuristic_extract_arguments(chunk)

    belief_candidates = [
        arg.conclusion for arg in arguments if len(arg.conclusion) > 10
    ]

    fol_sig = _extract_fol_signature(arguments) if target_logic in ("fol", "all") else None

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
            result = await _extract_chunk(chunks[0], target_logic, 0)
        else:
            tasks = [
                _extract_chunk(chunk, target_logic, idx)
                for idx, chunk in enumerate(chunks)
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
            arguments = _heuristic_extract_arguments(chunks[0])
            return json.dumps(
                {
                    "arguments": [a.model_dump() for a in arguments],
                    "count": len(arguments),
                    "source_length": len(text),
                }
            )

        # Parallel extraction for multi-chunk
        async def _extract_args(chunk: str) -> List[ExtractedArgument]:
            return _heuristic_extract_arguments(chunk)

        results = await asyncio.gather(
            *[_extract_args(c) for c in chunks], return_exceptions=True
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
                text = arg_data.get("text", "") if isinstance(arg_data, dict) else str(arg_data)
                if text:
                    arg_ids.append(add_arg(text))

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
