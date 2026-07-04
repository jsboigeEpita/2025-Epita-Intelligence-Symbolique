"""Conversational wiring — render the 3-act restitution from a conversational run.

CONV-D #1335 (périmètre 1+2). The pipeline path has wired restitution since R6
(``unified_pipeline.render_restitution`` → ``pipeline_adapter``); the
conversational path (``run_conversational_analysis``) produced the same
``UnifiedAnalysisState`` but never ran the act-generation phases, so the three
restitution act strings stayed empty and no report was assembled.

This module closes that gap. It is the single place where a completed
conversational state becomes the readable 3-act report. Design (anti-pendule,
file-disjoint lane mirroring ``pipeline_adapter.py``):

  - ``generate_and_render_for_conversational_state(state, input_text, *, llm_callable=None,
    output_path=None)`` — resolve ONE async LLM callable (reused for all 3 acts,
    vs. 3 kernels if we called the workflow invoke-callables), run the 3 act
    generators (``build_act1_framing`` / ``build_act2_narrative`` /
    ``build_act3_conclusion``), persist the narratives onto the state (the keys
    ``state.act1_framing`` / ``act2_narrative`` / ``act3_conclusion`` the renderer
    reads), then render via ``render_spectacular_restitution``.

  - Reuses the act plugin entry-points directly (clean ``(state, llm_callable)``
    contract), NOT the workflow ``_invoke_actN_*`` wrappers (which each spin a
    Kernel and expect an executor-style context dict). One LLM resolution for
    three acts = the cost shape of the pipeline path.

  - Fail-loud (#1019/#369): absent LLM → acts come back ``status="unavailable"``
    with empty narratives → the renderer names the acts "indisponible"
    honestly. The conversational run is never failed by reporting.

Privacy HARD: ``source_id`` stays opaque (derived opaquely by
``pipeline_adapter._derive_source_id``). The act plugins already truncate +
paraphrase corpus-derived fields; the renderer never writes to disk (privacy
boundary stays at the caller via ``output_path``).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .act1_framing_plugin import LlmCallable, build_act1_framing
from .act2_narrative_plugin import build_act2_narrative
from .act3_conclusion_plugin import build_act3_conclusion
from .pipeline_adapter import render_spectacular_restitution
from .renderer import RenderedReport

logger = logging.getLogger(__name__)


def _resolve_default_llm_callable() -> Optional[LlmCallable]:
    """Resolve an async LLM callable from a Kernel + default service.

    Mirrors the idiom in ``invoke_callables._invoke_actN_*`` (service_id=
    "default" activates the LLM path). Absent service → None (the act
    generators record ``status="unavailable"`` fail-loud).
    """
    try:
        from semantic_kernel import Kernel

        kernel = Kernel()
        try:
            from argumentation_analysis.core.llm_service import create_llm_service

            llm = create_llm_service(service_id="default")
            if not llm:
                return None
            kernel.add_service(llm)
        except Exception:  # noqa: BLE001 — LLM absence is a fail-loud case, not a crash
            return None
    except Exception:  # noqa: BLE001 — semantic_kernel import/unavailable
        return None

    async def _llm(prompt: str) -> str:
        settings = kernel.get_prompt_execution_settings_from_service_id("default")
        result = await kernel.invoke_prompt(
            function_name="conversational_restitution_conducted",
            plugin_name="restitution",
            prompt=prompt,
            settings=settings,
        )
        return str(result) if result else ""

    return _llm


async def generate_and_render_for_conversational_state(
    state: Any,
    input_text: str,
    *,
    llm_callable: Optional[LlmCallable] = None,
    output_path: Optional[str] = None,
) -> RenderedReport:
    """Generate the 3 acts on a completed conversational state + render the report.

    Runs the act generators (LLM-conducted), persists the narratives onto
    ``state.act1_framing`` / ``act2_narrative`` / ``act3_conclusion`` (the keys
    the renderer consumes), then assembles the readable 3-act report via
    ``render_spectacular_restitution``. The conversational path does not run the
    act phases (it runs Extraction/Formal/Synthesis macro-phases via
    AgentGroupChat), so this is where the acts are produced for that path.

    Args:
        state: a completed ``UnifiedAnalysisState`` from a conversational run.
        input_text: the source text (unused if acts need no re-derivation; kept
            for parity with the invoke-callable contract + future framing use).
        llm_callable: optional async LLM callable. If omitted, resolved from the
            default service. None/absent → fail-loud "indisponible" acts.
        output_path: if given, the rendered Markdown is written there (caller
            picks a gitignored path for real corpora).

    Returns:
        The rendered report (Markdown + gate-lisibilité verdict).
    """
    llm = llm_callable if llm_callable is not None else _resolve_default_llm_callable()

    # Acte I — framing. ``input_text`` kept in the contract for parity; the
    # plugin derives framing evidence from the state.
    try:
        act1 = await build_act1_framing(state, llm_callable=llm)
        _persist_act(state, "act1_framing", act1.narrative, act1.status)
    except Exception:  # noqa: BLE001 — one act failing must not abort the others
        logger.warning("Acte I framing failed (fail-loud, continuing): ", exc_info=True)

    # Acte II — dialectical narrative by movement. CONV-D #1335 périmètre 2:
    # the conversational state carries the CONV-C deliberation trace, which the
    # narrative can weave as "how the experts debated" material.
    try:
        act2 = await build_act2_narrative(state, llm_callable=llm)
        _persist_act(state, "act2_narrative", act2.narrative, act2.status)
    except Exception:  # noqa: BLE001
        logger.warning("Acte II narrative failed (fail-loud, continuing): ", exc_info=True)

    # Acte III — actionable conclusion (gated verdict + balanced appréciations).
    try:
        act3 = await build_act3_conclusion(state, llm_callable=llm)
        _persist_act(state, "act3_conclusion", act3.narrative, act3.status)
    except Exception:  # noqa: BLE001
        logger.warning("Acte III conclusion failed (fail-loud, continuing): ", exc_info=True)

    return render_spectacular_restitution(state, output_path=output_path)


def _persist_act(state: Any, key: str, narrative: str, status: str) -> None:
    """Write an act narrative onto the state if the state accepts the attribute.

    Skips silently when the state does not expose the attribute (defensive — the
    conversational state is a ``UnifiedAnalysisState`` which does, but the act
    generators are kept decoupled from the state class). Logs the act status so
    a fail-loud "unavailable" is traceable in the run log.
    """
    if not hasattr(state, key):
        logger.warning(
            "State has no '%s' attribute — act narrative dropped (status=%s)",
            key,
            status,
        )
        return
    if isinstance(state, dict):
        state[key] = narrative
    else:
        setattr(state, key, narrative)
    logger.info("Restitution %s persisted (%d chars, status=%s)", key, len(narrative), status)
