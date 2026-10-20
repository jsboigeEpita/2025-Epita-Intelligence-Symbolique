"""#2850 lot 6 — the four reconstruction states stop seeding a 200-char head.

Lot 5 reclassified the four ``UnifiedAnalysisState(input_text[:200])``
constructor seedings (``_invoke_narrative_synthesis``, Acts I/II/III invoke
functions) as **constructor ballast**: measured, no consumer reads the seeded
text's content — the only reflection is a length (Act II's ``source_length``)
and the state writers' anchor ``find``, which a 200-char fake corpus turns
into WRONG anchor claims (an offset into a corpus that is really the head of
a much longer document). The dispatch's arbitration: stop seeding it, rather
than disclose it.

Every witness is born red on the pre-fix tree: the captured reconstruction
state's ``raw_text`` is the 200-char head there, and the fix makes it the
empty string — the reconstruction never knew the document, and an empty
``raw_text`` says exactly that (unanchored units, ``source_length`` 0).
"""

from __future__ import annotations

import asyncio
from typing import Any, List
from unittest.mock import patch

INVOKE = "argumentation_analysis.orchestration.invoke_callables"

# Longer than the 200-char seed so the witness can tell head from empty.
LONG = (
    "Ce document synthetique depasse largement les deux cents caracteres "
    "attendus par le ballast constructeur, et chaque phrase ajoute une unite "
    "distincte que le lecteur pourrait croire ancree alors que le corpus de "
    "reconstruction n'en connait que la tete."
)


def _capturing_builder(captured: List[Any], result: Any = None):
    """A builder stand-in that records the state it was handed."""

    async def _build(state, *args: Any, **kwargs: Any):
        captured.append(state)
        return result

    return _build


def _act_result() -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(
        narrative="narrative",
        status="woven",
        gate_verdict=None,
        degraded={},
        interpretive_question="",
    )


class TestReconstructionStatesUnseeded:
    """Rows ``input_text[:200]#3-6`` — the seeding is removed, not disclosed."""

    def _assert_unseeded(self, captured: List[Any]) -> None:
        assert len(captured) == 1, "the builder must have been called once"
        raw = getattr(captured[0], "raw_text", "<missing>")
        assert raw == "", (
            "the reconstruction state must not carry a 200-char head: no "
            "consumer reads its content (lot 5, measured), the anchor find "
            f"turns it into wrong offset claims, and Act II's source_length "
            f"misdocuments the document as {len(raw)} chars — the "
            "reconstruction never knew the document, and an empty raw_text "
            "is the honest value"
        )

    def test_narrative_synthesis_reconstruction_is_unseeded(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_narrative_synthesis,
        )

        captured: List[Any] = []
        with patch(
            "argumentation_analysis.plugins.narrative_synthesis_plugin"
            ".build_narrative",
            side_effect=lambda state: captured.append(state) or "n",
        ):
            asyncio.run(_invoke_narrative_synthesis(LONG, {}))
        self._assert_unseeded(captured)

    def test_act2_reconstruction_is_unseeded(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_act2_narrative,
        )

        captured: List[Any] = []
        with patch(
            "argumentation_analysis.reporting.restitution.act2_narrative_plugin"
            ".build_act2_narrative",
            _capturing_builder(captured, _act_result()),
        ):
            asyncio.run(_invoke_act2_narrative(LONG, {}))
        self._assert_unseeded(captured)

    def test_act1_reconstruction_is_unseeded(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_act1_framing,
        )

        captured: List[Any] = []
        with patch(
            "argumentation_analysis.reporting.restitution.act1_framing_plugin"
            ".build_act1_framing",
            _capturing_builder(captured, _act_result()),
        ):
            asyncio.run(_invoke_act1_framing(LONG, {}))
        self._assert_unseeded(captured)

    def test_act3_reconstruction_is_unseeded(self) -> None:
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_act3_conclusion,
        )

        captured: List[Any] = []
        with patch(
            "argumentation_analysis.reporting.restitution.act3_conclusion_plugin"
            ".build_act3_conclusion",
            _capturing_builder(captured, _act_result()),
        ):
            asyncio.run(_invoke_act3_conclusion(LONG, {}))
        self._assert_unseeded(captured)

    def test_a_state_in_context_is_never_replaced(self) -> None:
        """Control: the reconstruction path is the only one unseeded — a
        state passed in the context keeps its real raw_text."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_act2_narrative,
        )

        real = UnifiedAnalysisState(LONG)
        captured: List[Any] = []
        with patch(
            "argumentation_analysis.reporting.restitution.act2_narrative_plugin"
            ".build_act2_narrative",
            _capturing_builder(captured, _act_result()),
        ):
            asyncio.run(_invoke_act2_narrative(LONG, {"_state_object": real}))
        assert captured[0] is real
        assert captured[0].raw_text == LONG
