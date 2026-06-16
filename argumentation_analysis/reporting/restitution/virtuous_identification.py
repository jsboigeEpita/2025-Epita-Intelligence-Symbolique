"""R5 volet-1 — identify *virtuous-text* candidates in the corpus (spec §5.1).

Epic #1134 (Restitution), Track R5 (#1139). The restitution engine and report
must run on **virtuous texts** (the positive case), not only on fallacy-laden
prose. On a virtuous text the report's headline is the *virtue* (formal
robustness, intellectual honesty, well-held schemes), not the absence of
fallacies.

This module answers the **identification** half of R5: *which corpus entries are
virtuous-text candidates?* The owner's standing question — *« le dataset en
contient, peut-être pas assez »* — is answered here, honestly.

Spec §5.1 is unambiguous about what "virtuous" means::

    a corpus input is flagged "virtuous" [...] a low (or zero) localized-fallacy
    count **combined with** a non-trivial formal/quality axis [...]. The flag is
    **derived, never asserted**: a text is virtuous iff the pipeline's own output
    says so. If the dataset lacks enough virtuous inputs, R5 reports that gap
    (fail-loud), it does not synthesize one.

The true virtuous flag therefore **requires a pipeline run** (fallacy descent +
formal/quality axes). This module does NOT run the pipeline — it is a cheap,
deterministic **candidate generator** that narrows the corpus to the entries
worth confirming. The output is explicitly a *candidate* list with the honest
caveat that confirmation is pending (fail-loud on the gap, #1019/#369). It never
asserts a text is virtuous on lexical evidence alone.

Privacy HARD (CLAUDE.md dataset-privacy): the module works on **already-decrypted
in-memory definitions** passed by the caller; it never touches disk, never prints
a ``source_name``/path, and emits only **opaque IDs** (``src_N_ext_M``). No
``raw_text`` / ``full_text`` / ``extract_text`` value ever leaves through this
module's outputs — only *lengths* and *signal counts*.

File-disjoint from the act generators (R2/R3/R4) and the renderer (R6): no edits
to ``workflows.py`` / ``invoke_callables.py`` / ``state_writers.py`` / plugins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

# --- schema ---------------------------------------------------------------

# The dataset carries prose under two coexisting schemas:
#   schema A (early sources): extract_name / extract_text / markers
#   schema B (later sources): full_text / metadata / num_extract
# ``extract_text`` is the primary prose field for schema A — do NOT assume
# ``full_text`` (FB-39 lesson: verify the field name, do not assume).
_TEXT_FIELDS: Sequence[str] = (
    "extract_text",
    "full_text",
    "text",
    "content",
    "raw_text",
)

# Cheap lexical fallacy-signal indicators (FR + EN, rule-based, no LLM).
# Counts, never verdicts: a high count ⇒ the text is likely fallacy-laden
# (not a virtuous candidate); a low count on a substantive text ⇒ a candidate
# worth confirming by the pipeline. NB: these patterns are LEXICAL — a text can
# be structurally fallacious (non sequitur, equivocation, circularity) with zero
# lexical hit, and conversely a long text in an unmatched language/register can
# score zero for the wrong reason. The screen's PRECISION is unknown without a
# pipeline run; it is a recall-oriented candidate generator, not a classifier.
_LEXICAL_SIGNALS: Sequence[tuple[str, str]] = (
    (r"\btous\b|\btoutes\b|\bjamais\b|\bpersonne ne\b|\bchacun\b", "generalisation"),
    (r"\bexperts?\b|\bscientifiques?\b|\bautorit", "appel_autorite_lex"),
    (r"\bpeur\b|\bmenace\b|\bdanger\b|\bcatastrophe", "peur_alarmisme"),
    (r"\bsi\b.{0,40}\balors\b|\bglissement\b", "pente_glissante"),
    (r"\bdevons\b|\bil faut\b|\bforc", "faux_debat_imperatif"),
    (r"\bcomme tout le monde\b|\btout le monde sait\b", "ad_populum_lex"),
)
# compiled lazily so the module imports with zero side effects
_COMPILED: Optional[List[tuple[Any, str]]] = None


def _compiled_signals() -> List[tuple[Any, str]]:
    global _COMPILED
    if _COMPILED is None:
        import re

        _COMPILED = [(re.compile(p, re.IGNORECASE), n) for p, n in _LEXICAL_SIGNALS]
    return _COMPILED


def _extract_prose(extract: Mapping[str, Any]) -> Optional[str]:
    """Return the prose held by an extract, whichever field carries it.

    Returns ``None`` when no text-bearing field has a non-blank value (the
    extract is metadata-only). Never prints the value — callers only see the
    opaque metrics derived downstream.
    """
    for k in _TEXT_FIELDS:
        v = extract.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return None


def _lexical_signal_count(text: str) -> Dict[str, int]:
    """Count cheap lexical fallacy signals by type. Empty dict if none."""
    low = text.lower()
    out: Dict[str, int] = {}
    for rx, name in _compiled_signals():
        n = len(rx.findall(low))
        if n:
            out[name] = n
    return out


# --- candidate model ------------------------------------------------------


@dataclass
class ExtractProfile:
    """Opaque profile of one extract — metrics only, never content."""

    opaque_id: str
    char_count: int
    has_text: bool
    signal_total: int
    signal_by_type: Dict[str, int] = field(default_factory=dict)

    @property
    def signal_density(self) -> float:
        """Lexical signals per 1000 chars (0.0 when no text)."""
        if self.char_count <= 0:
            return 0.0
        return round(self.signal_total / (self.char_count / 1000.0), 3)

    @property
    def in_sweet_spot(self) -> bool:
        """Substantive enough to mount an argument, small enough for one pipeline
        analysis (not a book). Bounds are module defaults — see ``identify``."""
        return _MIN_CANDIDATE_CHARS <= self.char_count <= _MAX_CANDIDATE_CHARS

    @property
    def low_signal(self) -> bool:
        return self.signal_density <= _MAX_CANDIDATE_DENSITY


# tunable candidate-screen defaults (documented, overridable via ``identify``)
_MIN_CANDIDATE_CHARS = 2000  # ~300-400 words: enough for premise+conclusion+schemes
_MAX_CANDIDATE_CHARS = 50000  # pipeline-feasible single analysis; larger = book
_MAX_CANDIDATE_DENSITY = 0.2  # lexical signals / 1000 chars


@dataclass
class VirtuousCandidate:
    """An extract that passes the cheap candidate screen — NOT confirmed virtuous."""

    opaque_id: str
    char_count: int
    signal_total: int
    signal_density: float

    def as_row(self) -> Dict[str, Any]:
        return {
            "opaque_id": self.opaque_id,
            "chars": self.char_count,
            "signal_total": self.signal_total,
            "signal_density": self.signal_density,
        }


@dataclass
class VirtuousInventory:
    """Opaque inventory of the corpus + the virtuous-candidate narrowing.

    ``candidates`` is a CANDIDATE list (cheap lexical screen). The DERIVED
    virtuous flag (spec §5.1) requires a pipeline run; ``rarity`` reports the
    honest gap when the candidate pool is thin.
    """

    total_sources: int
    total_extracts: int
    text_extracts: int
    metadata_only_extracts: int
    candidates: List[VirtuousCandidate] = field(default_factory=list)
    excluded_too_short: int = 0
    excluded_too_long: int = 0
    excluded_high_signal: int = 0
    size_brackets: Dict[str, int] = field(default_factory=dict)

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def rarity(self) -> str:
        """Honest rarity signal (fail-loud on a thin pool, never fabricates).

        * ``THIN``  — ≤ 2 candidates: the corpus barely supports a virtuous
          track; flag the gap, do not pad it.
        * ``SCARCE`` — 3–5 candidates: usable but document the scarcity.
        * ``ADEQUATE`` — ≥ 6 candidates.
        """
        n = self.candidate_count
        if n <= 2:
            return "THIN"
        if n <= 5:
            return "SCARCE"
        return "ADEQUATE"


def _opaque_id(source_index: int, extract_index: int) -> str:
    return f"src_{source_index}_ext_{extract_index}"


def _bracket(chars: int) -> str:
    if chars <= 0:
        return "no_text"
    if chars < 2000:
        return "tiny(<2k)"
    if chars < 50000:
        return "sweet(2k-50k)"
    if chars < 200000:
        return "large(50k-200k)"
    return "book(>200k)"


def identify(
    definitions: Sequence[Mapping[str, Any]],
    *,
    min_chars: int = _MIN_CANDIDATE_CHARS,
    max_chars: int = _MAX_CANDIDATE_CHARS,
    max_density: float = _MAX_CANDIDATE_DENSITY,
) -> VirtuousInventory:
    """Narrow a decrypted corpus to virtuous-text candidates (cheap screen).

    Args:
        definitions: the **decrypted in-memory** extract definitions (as returned
            by ``load_extract_definitions`` with the derived key). The module
            never decrypts itself.
        min_chars / max_chars: the sweet-spot bounds for a candidate (substantive
            but pipeline-feasible as one analysis).
        max_density: max lexical-signal density (per 1000 chars) for a candidate.

    Returns:
        A :class:`VirtuousInventory` with opaque profiles and the candidate list.
        Nothing in the result reveals corpus content or source identity.

    The candidates are **unconfirmed** — the spec §5.1 virtuous flag is derived
    from pipeline output (fallacy_count + non-trivial formal/quality axis). This
    function only narrows; confirmation is a separate, gated step.
    """
    inv = VirtuousInventory(
        total_sources=len(definitions),
        total_extracts=0,
        text_extracts=0,
        metadata_only_extracts=0,
    )
    candidates: List[VirtuousCandidate] = []

    for si, src in enumerate(definitions):
        extracts = src.get("extracts", []) or []
        inv.total_extracts += len(extracts)
        for ei, ex in enumerate(extracts):
            oid = _opaque_id(si, ei)
            prose = _extract_prose(ex)
            if prose is None:
                inv.metadata_only_extracts += 1
                inv.size_brackets["no_text"] = inv.size_brackets.get("no_text", 0) + 1
                continue
            inv.text_extracts += 1
            n = len(prose)
            sig = _lexical_signal_count(prose)
            total = sum(sig.values())
            density = round(total / (n / 1000.0), 3) if n else 0.0
            b = _bracket(n)
            inv.size_brackets[b] = inv.size_brackets.get(b, 0) + 1

            if n < min_chars:
                inv.excluded_too_short += 1
                continue
            if n > max_chars:
                inv.excluded_too_long += 1
                continue
            if density > max_density:
                inv.excluded_high_signal += 1
                continue
            candidates.append(
                VirtuousCandidate(
                    opaque_id=oid,
                    char_count=n,
                    signal_total=total,
                    signal_density=density,
                )
            )

    # stable order: lowest density first, then longest (more to analyse)
    candidates.sort(key=lambda c: (c.signal_density, -c.char_count))
    inv.candidates = candidates
    return inv


def render_inventory_report(inv: VirtuousInventory) -> str:
    """Render the opaque inventory as Markdown (for a gitignored artifact).

    Emits opaque IDs and metrics only. Includes the honest rarity signal and the
    mandatory caveat that candidates are unconfirmed (the DERIVED flag needs a
    pipeline run, spec §5.1).
    """
    lines: List[str] = []
    lines.append("# R5 volet-1 — virtuous-text candidate inventory (opaque)")
    lines.append("")
    lines.append("> Privacy HARD: opaque IDs only. No source name, no corpus text.")
    lines.append(
        "> This is a CANDIDATE list (cheap lexical screen). The virtuous flag is "
        "DERIVED from pipeline output (spec §5.1) — unconfirmed here."
    )
    lines.append("")
    lines.append("## Corpus composition")
    lines.append("")
    lines.append(f"- sources: **{inv.total_sources}**")
    lines.append(f"- extracts (total): **{inv.total_extracts}**")
    lines.append(
        f"- extracts with text: **{inv.text_extracts}** "
        f"(metadata-only: {inv.metadata_only_extracts})"
    )
    lines.append("- size brackets:")
    for b in sorted(inv.size_brackets):
        lines.append(f"  - `{b}`: {inv.size_brackets[b]}")
    lines.append("")
    lines.append("## Candidate screen (sweet spot + low lexical signal)")
    lines.append("")
    lines.append(
        f"bounds: `{_MIN_CANDIDATE_CHARS}`–`{_MAX_CANDIDATE_CHARS}` chars, "
        f"density ≤ `{_MAX_CANDIDATE_DENSITY}`/1k chars."
    )
    lines.append("")
    lines.append(
        f"excluded — too short (<{_MIN_CANDIDATE_CHARS}): {inv.excluded_too_short} · "
        f"too long (>{_MAX_CANDIDATE_CHARS}): {inv.excluded_too_long} · "
        f"high signal: {inv.excluded_high_signal}"
    )
    lines.append("")
    lines.append(
        f"**Rarity signal: {inv.rarity}** ({inv.candidate_count} candidate(s))"
    )
    lines.append("")
    if inv.candidates:
        lines.append("| opaque_id | chars | signal_total | density/1k |")
        lines.append("|---|---|---|---|")
        for c in inv.candidates:
            lines.append(
                f"| {c.opaque_id} | {c.char_count} | {c.signal_total} | {c.signal_density} |"
            )
    else:
        lines.append(
            "_(no candidate at this screen — corpus may lack virtuous inputs)_"
        )
    lines.append("")
    lines.append("## Caveat (load-bearing)")
    lines.append("")
    lines.append(
        "The lexical screen is a **recall-oriented candidate generator**. Its "
        "PRECISION is unknown: a long text scoring `density 0.0` often reflects a "
        "language/register mismatch, not virtue; a structurally fallacious text "
        "(non sequitur, circularity) can score zero lexically. **Do not assert a "
        "candidate is virtuous without a pipeline run** confirming `fallacy_count` "
        "≈ 0 AND a non-trivial formal/quality axis (spec §5.1). The next step is "
        "a (budget-gated) pipeline run on the top candidates to derive the flag."
    )
    lines.append("")
    return "\n".join(lines)
