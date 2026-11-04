"""Historian persona — the situation before the analysis (#3377, Epic #3374).

The pipeline may not use what the model knows. On an undated document the
render says the date "is only a deduction from the content" and that a place
"remains to be verified elsewhere"; the same-model zero-shot of #2841 dates and
situates it in its title line. That is M1: global context, where the zero-shot
wins. This persona closes it without blurring the line the renderer keeps — the
historian's output is labelled **model knowledge**, in the state and in the
render, and never reads as the text's own content.

What it writes (``state.historical_context``): a one-sentence situation, then
items — date, place, actors, and what was at stake then — each with a
confidence and a ``supports`` hint naming which element of the document the
claim explains. No quotation: a quote would make the claim look textual, which
is the failure mode this module exists to prevent.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from argumentation_analysis.agents.core.context import (
    MODEL_KNOWLEDGE_BASIS,
    stamp_basis,
)
from argumentation_analysis.core.reading_window import (
    LLM_EXTRACTION_WINDOW,
    selected_text,
)

logger = logging.getLogger("Historian")

#: Cap on the items the state carries. A situation, not an encyclopaedia: the
#: read is an orientation for the acts, and an unbounded list would crowd the
#: Act I prompt without adding a stake.
MAX_ITEMS = 8

#: How many extracted stakes the historian's prompt restates to the model —
#: a bound on the prompt, not on the era it may situate. Named so the reader
#: can check it against the rendered prompt instead of a hidden truncation.
_PROMPT_MAX_STAKES = 6

HISTORIAN_PROMPT = """You are a historian. Situate the document below before anyone
analyses its reasoning: what period, what place, which actors, and what was at
stake THEN (not what the document argues).

Hard rules:
- You are stating what you know, as a historian. This is MODEL KNOWLEDGE, not
  the document's content; the report will label it as such.
- Never quote the document. Say what you know, and, for each item, name the
  element of the document it explains (its "supports" field) in your own words.
- State a confidence between 0 and 1 per item. A date you infer from style is
  not a date you know: say 0.3, not 0.9.
- If you do not know, return an empty list. An invented situation is worse than
  no situation: it would be rendered as knowledge.

Answer in French, with ONLY this JSON, no fences, no commentary:
{{"situation": "one sentence situating the document",
  "items": [{{"claim": "...", "confidence": 0.0,
             "supports": "which element of the document this explains"}}]}}

Source metadata given by the pipeline: speaker={speaker}, venue={venue},
topic={topic}, era={era}, language={language}.

Enjeux already extracted from the text (read them, do not restate them as
history):
{stakes_block}

Document excerpt:
{excerpt}
"""


@dataclass
class HistoricalItem:
    """One item of model knowledge about the situation."""

    claim: str
    confidence: float = 0.0
    supports: str = ""
    basis: str = MODEL_KNOWLEDGE_BASIS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "confidence": self.confidence,
            "supports": self.supports,
            "basis": self.basis,
        }


@dataclass
class HistoricalContext:
    """The historian's read, ready for the state.

    ``status`` is discriminated on purpose (#3096's lesson): an LLM failure must
    never read as "completed, empty". The invoke turns a non-``ok`` status into
    a degraded phase carrying the reason.
    """

    situation: str = ""
    items: List[HistoricalItem] = field(default_factory=list)
    status: str = "no_llm"
    error: str = ""

    def to_state(self) -> Dict[str, Any]:
        return {
            "situation": self.situation,
            "items": [item.to_dict() for item in self.items],
            "status": self.status,
            "basis": MODEL_KNOWLEDGE_BASIS,
        }


def _clamp_confidence(value: Any) -> float:
    """Clamp a model-reported confidence into [0, 1]; unreadable → 0.0.

    Unreadable is 0.0 and not a default: an unmeasured confidence must read as
    unmeasured, the same rule #3029 applies to an absent detection score.
    """
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _stakes_block(state: Any) -> str:
    stakes = getattr(state, "stakes_and_stakeholders", {}) or {}
    descriptions = []
    for stake in (stakes.get("stakes") or [])[:_PROMPT_MAX_STAKES]:
        if isinstance(stake, dict):
            description = stake.get("description") or ""
            if description:
                descriptions.append(f"- {description}")
    return "\n".join(descriptions) if descriptions else "  (aucun enjeu extrait)"


def build_historian_prompt(state: Any, excerpt: str) -> str:
    """Render the historian's prompt from the gathered evidence."""
    metadata = getattr(state, "source_metadata", {}) or {}
    return HISTORIAN_PROMPT.format(
        speaker=metadata.get("speaker", "unknown"),
        venue=metadata.get("venue", "unknown"),
        topic=metadata.get("topic", "unknown"),
        era=metadata.get("era", metadata.get("date_or_year", "unknown")),
        language=metadata.get("language", "unknown"),
        stakes_block=_stakes_block(state),
        excerpt=excerpt,
    )


async def build_historical_context(
    state: Any,
    llm_callable: Optional[Callable[[str], Awaitable[str]]] = None,
) -> HistoricalContext:
    """Build ``state.historical_context`` — the situation, labelled as model knowledge.

    The excerpt is read through the #1737 selector (``selected_text``), so the
    window this persona reads is the one the pipeline decides everywhere else,
    and it is recorded on the state when the state can record it.

    ``llm_callable`` is injected: the invoke layer owns the client, the runaway
    guard and the provider route; this module owns the persona. No LLM → status
    ``no_llm`` and an empty read (never a fabricated one).
    """
    raw_text = getattr(state, "raw_text", "") or ""
    recorder = state if hasattr(state, "record_reading_window") else None
    excerpt = selected_text(raw_text, LLM_EXTRACTION_WINDOW, "historian", recorder)

    result = HistoricalContext()
    if llm_callable is None:
        logger.debug("Historian: no LLM callable; returning an empty read.")
        return result

    prompt = build_historian_prompt(state, excerpt)
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
        result.situation = str(parsed.get("situation", "") or "").strip()
        raw_items = parsed.get("items") or []
        items = []
        for raw in raw_items[:MAX_ITEMS]:
            if not isinstance(raw, dict):
                continue
            claim = str(raw.get("claim", "") or "").strip()
            if not claim:
                continue
            items.append(
                HistoricalItem(
                    claim=claim,
                    confidence=_clamp_confidence(raw.get("confidence")),
                    supports=str(raw.get("supports", "") or "").strip(),
                )
            )
        # ``stamp_basis`` runs over the dicts so the label is written here, not
        # by the model: the round-trip is deliberate, an item can never escape
        # this module without a basis.
        stamped = stamp_basis([item.to_dict() for item in items])
        result.items = [
            HistoricalItem(
                claim=entry["claim"],
                confidence=entry["confidence"],
                supports=entry["supports"],
                basis=entry["basis"],
            )
            for entry in stamped
        ]
        result.status = "ok"
        logger.info(
            "Historian: %d item(s), situation=%s",
            len(result.items),
            bool(result.situation),
        )
    except json.JSONDecodeError as e:
        result.status = "parse_error"
        result.error = f"{type(e).__name__}: {e}"
        logger.warning("Historian parse error: %s", e)
    except Exception as e:  # pragma: no cover - provider failures
        result.status = "llm_error"
        result.error = f"{type(e).__name__}: {e}"
        logger.warning("Historian LLM error: %s", e)
    return result


async def extract_historical_context(**kwargs: Any) -> Dict[str, Any]:
    """State-shaped wrapper: the dict the invoke returns and the writer persists."""
    return (await build_historical_context(**kwargs)).to_state()


def context_note(state: Any) -> str:
    """The labelled block a downstream reader prepends to its own prompt.

    ONE producer for the wording (#3377): the NL→KB translator and any later
    consumer must say the same thing about the same read, or two readers will
    disagree about what "model knowledge" covers. Empty string when there is
    nothing to say — a consumer that appended an empty header would advertise a
    provenance it does not have.
    """
    context = getattr(state, "historical_context", {}) or {}
    if not isinstance(context, dict):
        return ""
    situation = str(context.get("situation") or "").strip()
    items = [
        item
        for item in (context.get("items") or [])
        if isinstance(item, dict) and str(item.get("claim") or "").strip()
    ]
    if not situation and not items:
        return ""

    lines = [
        "SITUATION HISTORIQUE — SAVOIR DU MODÈLE, jamais le contenu du texte :",
        "  Utilise-la pour résoudre les références (époque, acteurs, "
        "institutions), jamais pour ajouter une prémisse au texte.",
    ]
    if situation:
        lines.append(f"  Situation : {situation}")
    for item in items:
        try:
            confidence = float(item.get("confidence"))
        except (TypeError, ValueError):
            confidence = 0.0
        lines.append(f"  - {item['claim']} (confiance {confidence:.2f})")
    return "\n".join(lines)
