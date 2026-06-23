"""The dimensional appendix — provenance, folded, never the report body (spec §6).

The restitution report's *body* is the 3-act narrative. The dimensional data
that used to be the whole report (phase tables, per-fallacy entries, formal
solver outputs — the "très difficile à lire" artifact) is relegated here, behind
a collapsed ``<details>`` block, for traceability only. It is no longer what the
reader meets first.

Privacy HARD: the appendix summarises *counts and verdicts* by default. The full
state JSON is opt-in (``include_full_state_json=True``) and is meant only for
emission under a gitignored path (the renderer never writes to disk — the caller
chooses the path). ``raw_text`` and any ``*snippet*`` key are stripped defensively
regardless, so a careless caller cannot leak the corpus through the appendix.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional

# Keys that carry corpus plaintext (directly or via derived fields). Stripped
# defensively from any state dict before it is rendered into the appendix, even
# when the caller asked for the full JSON. CLAUDE.md dataset-privacy rule.
_LEAK_KEYS = (
    "raw_text",
    "full_text",
    "raw_text_segment",
    "raw_text_snippet",
    "full_text_segment",
    "text",
    "content",  # last two: only stripped when
    # explicitly nested under a fallacy/argument that echoes corpus text; see
    # _strip below which only removes top-level + these echo fields by name.
)


def _strip_leak_keys(state: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``state`` with leak-capable top-level keys removed."""
    out: Dict[str, Any] = {}
    for k, v in state.items():
        if k in _LEAK_KEYS:
            continue
        out[k] = v
    return out


def _safe_len(value: Any) -> int:
    """Length of a collection-ish value, 0-safe."""
    try:
        return len(value)
    except TypeError:
        return 0


def _provenance_counts(state: Mapping[str, Any]) -> Dict[str, Any]:
    """Honest provenance summary: counts + verdict flags, no corpus content.

    Mirrors the spec §2 block→state-key table at the *aggregate* level. Each
    entry reports a non-triviality signal (how many arguments, fallacies, etc.
    the pipeline actually produced) so a reader can gauge what backs the
    narrative without reading the raw state.
    """
    counts: Dict[str, Any] = {}

    def _g(key: str, default: Any = None) -> Any:
        return state.get(key, default)

    counts["arguments_extraits"] = _safe_len(_g("identified_arguments", {}))
    counts["sophismes_localises"] = _safe_len(_g("identified_fallacies", {}))
    counts["contre_arguments"] = _safe_len(_g("counter_arguments", []))
    counts["scores_qualite"] = _safe_len(_g("argument_quality_scores", {}))

    # formal axes — report presence + a coarse status, not the raw belief sets
    fol = _g("fol_analysis_results")
    counts["axe_fol"] = (
        {
            "consistent": bool(fol.get("consistent")),
            "formules": _safe_len(fol.get("formulas")),
        }
        if isinstance(fol, Mapping)
        else "indisponible"
    )
    counts["axe_pl"] = (
        "disponible" if _g("propositional_analysis_results") else "indisponible"
    )
    counts["axe_modale"] = (
        "disponible" if _g("modal_analysis_results") else "indisponible"
    )
    counts["axe_dung"] = "disponible" if _g("dung_frameworks") else "indisponible"
    counts["axe_aspic"] = "disponible" if _g("aspic_results") else "indisponible"

    # Structured-argumentation honesty (FP-17 #1236). ASPIC+/ABA/SETAF/weighted/
    # bipolar have no text→structured translator wired (translation-gap FP-4
    # #1201), so an empty extension list is NOT "evaluated, empty" — it is
    # "never genuinely fed structured input". Surface that per-capability status
    # explicitly so the bare ``axe_aspic = disponible`` above is not misread as
    # a real structured-arg analysis of the source (#1019: no silent []).
    sa_status = _g("structured_arg_status")
    if isinstance(sa_status, Mapping) and sa_status:
        parts = []
        for cap, info in sa_status.items():
            st = info.get("status", "?") if isinstance(info, Mapping) else "?"
            label = (
                "absent (aucun traducteur structuré)"
                if st == "absent_no_translator"
                else str(st)
            )
            parts.append(f"{cap}={label}")
        counts["arg_structuree"] = "; ".join(parts)
    else:
        counts["arg_structuree"] = "indisponible"

    counts["synthese_narrative"] = (
        "présente" if _g("narrative_synthesis") else "absente"
    )
    counts["synthese_formelle"] = (
        "présente" if _g("formal_synthesis_reports") else "absente"
    )
    return counts


def render_appendix(
    state: Optional[Mapping[str, Any]],
    *,
    include_full_state_json: bool = False,
) -> str:
    """Render the dimensional appendix as a folded Markdown ``<details>`` block.

    Args:
        state: the (serialisable) shared-state mapping, or ``None`` to emit an
            honest "annexe indisponible" note.
        include_full_state_json: opt-in. When True, the leak-scrubbed state JSON
            is included (folded) for traceability. Meant for emission under a
            gitignored path only. Default False (counts-only provenance).

    Returns:
        A Markdown string beginning with ``<details>``. Empty string when
        ``state`` is None *and* the caller opts out — but by default a missing
        state still yields an honest note, not silence.
    """
    if state is None:
        return (
            "\n<details>\n<summary>Annexe — provenance dimensionnelle</summary>\n\n"
            "Annexe indisponible (shared-state non fourni au renderer). "
            "La narration ci-dessus se suffit à elle-même ; cette annexe n'aurait "
            "contenu que des agrégats de traçabilité.\n\n"
            "</details>\n"
        )

    counts = _provenance_counts(state)
    lines = [
        "\n<details>",
        "<summary>Annexe — provenance dimensionnelle ( repliée par défaut)</summary>",
        "",
        "Agrégats de traçabilité uniquement — pas de contenu de corpus.",
        "",
        "| Dimension | Valeur |",
        "|---|---|",
    ]
    for label, value in counts.items():
        lines.append(f"| {label} | {value} |")
    lines.append("")

    if include_full_state_json:
        scrubbed = _strip_leak_keys(state)
        lines.append("JSON shared-state (clés à fuite potentielles retirées, replié) :")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(scrubbed, indent=2, ensure_ascii=False, default=str))
        lines.append("```")
        lines.append("")

    lines.append("</details>")
    return "\n".join(lines) + "\n"
