"""#3095 — the run path's own per-MTok price table.

The usage line used to sum only the provider-reported ``usage.cost``: on a
BYOK route every call reports 0, so a 0.415 $ pass printed "cost: $0.0000";
on a provider that reports no cost field, nothing was priced. A run must be
able to price its own tokens.

Every row cites the page it was read from and the day it was read
(``PRICES_READ_ON``). Tiered models get one row per tier, selected by the
largest threshold the prompt STRICTLY exceeds — Haiku 5.5's >100k
long-prompt tier is its own row, never an average of the two, and exactly
100 000 prompt tokens still bills at the standard row (R1102 rework).

Deliberately out of scope (#3095 item 4): cache and batch modifiers. No run
path applies them today; a run that starts using one must model it here
before its line can claim a price. A row whose published price leaves a
measured gap against a real bill says so in its ``source`` — the table is
never tuned to fit one run (R1102 rework).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

# The day the figures below were read from their sources. Every row carries
# it; the usage line prints it so a reader knows how old the price is.
PRICES_READ_ON = "2026-10-20"

_ANTHROPIC = "Anthropic API pricing page (published per-MTok rates)"


@dataclass(frozen=True)
class PriceRow:
    """One priced model (or one of its prompt-size tiers)."""

    model_id: str
    input_per_mtok: float
    output_per_mtok: float
    source: str
    read_on: str = PRICES_READ_ON
    # 0 is the standard tier; a larger value selects the row only once the
    # call's prompt reaches it (whole request billed at that tier).
    prompt_threshold_tokens: int = 0


PRICE_TABLE: List[PriceRow] = [
    PriceRow(
        model_id="gpt-5.6-luna",
        input_per_mtok=0.20,
        output_per_mtok=1.20,
        source=(
            "OpenAI published rates — developers.openai.com/api/docs/models/"
            "gpt-5.6-luna and openai.com/index/advancing-the-price-performance-"
            "frontier-with-gpt-5-6/ (post 2026-07-30 cut). NOT verified against a "
            "bill: R1101 billed 0.415 $ where this row prices 0.383 $ (−7.7 %); "
            "cache writes (1.25× input) and the >272k long-context rates are "
            "out of scope (#3095 item 4), so the gap is kept, not tuned away."
        ),
    ),
    PriceRow(
        model_id="claude-haiku-5-5",
        input_per_mtok=0.10,
        output_per_mtok=0.50,
        source=_ANTHROPIC,
    ),
    PriceRow(
        model_id="claude-haiku-5-5",
        input_per_mtok=0.50,
        output_per_mtok=2.50,
        source=f"{_ANTHROPIC} — long-prompt tier (>100k prompt tokens)",
        prompt_threshold_tokens=100_000,
    ),
    PriceRow(
        model_id="claude-sonnet-5-5",
        input_per_mtok=2.00,
        output_per_mtok=10.00,
        source=_ANTHROPIC,
    ),
    PriceRow(
        model_id="claude-opus-5-5",
        input_per_mtok=4.00,
        output_per_mtok=20.00,
        source=_ANTHROPIC,
    ),
    PriceRow(
        model_id="claude-fable-5-1",
        input_per_mtok=10.00,
        output_per_mtok=50.00,
        source=_ANTHROPIC,
    ),
]


def bare_model_id(model_id: str) -> str:
    """The table's key for a routed id (``openai/gpt-5.6-luna`` → ``gpt-5.6-luna``).

    Only an exact catalogue match prices: a dated or versioned variant the
    table does not carry stays unknown rather than borrowing a neighbour's
    price (#3095 item 3)."""
    return (model_id or "").strip().lower().rsplit("/", 1)[-1]


def resolve_price_row(model_id: str, prompt_tokens: int) -> Optional[PriceRow]:
    """The row that prices this call, or ``None`` for an unknown model."""
    bare = bare_model_id(model_id)
    if not bare:
        return None
    rows = [row for row in PRICE_TABLE if row.model_id == bare]
    if not rows:
        return None
    prompt = max(0, prompt_tokens)
    # The standard row (threshold 0) always applies; a tiered row applies only
    # when the prompt STRICTLY exceeds its threshold — exactly 100 000 prompt
    # tokens bills at the standard row, 100 001 at the long one (R1102 rework).
    reached = [
        r
        for r in rows
        if r.prompt_threshold_tokens == 0 or r.prompt_threshold_tokens < prompt
    ]
    if not reached:  # defensive: a table with no standard tier prices nothing
        return None
    return max(reached, key=lambda r: r.prompt_threshold_tokens)


def price_tokens(
    model_id: str, prompt_tokens: int, completion_tokens: int
) -> Optional[float]:
    """USD for one call from its measured tokens, or ``None`` if unpriced.

    ``None`` is "not priced", never 0 (#1019 tri-state): the caller prints the
    model id instead of a fabricated zero."""
    row = resolve_price_row(model_id, prompt_tokens)
    if row is None:
        return None
    return (
        prompt_tokens / 1_000_000 * row.input_per_mtok
        + completion_tokens / 1_000_000 * row.output_per_mtok
    )
