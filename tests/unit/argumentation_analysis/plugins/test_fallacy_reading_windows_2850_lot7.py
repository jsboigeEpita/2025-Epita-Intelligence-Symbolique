"""#2850 lot 7 — the fallacy workflow's document windows reach the #1737 record.

The four census rows of ``fallacy_workflow_plugin.py`` (wide-net Phase-1
``[:WIDE_NET_WINDOW]``, two descent ``[:500]``, one-shot
``selected_text(..., WIDE_NET_WINDOW)``) bound the DOCUMENT on every real run
(the document-path construction hands the plugin the whole text), and nothing
said so: the slices are raw, the one-shot's ``selected_text`` call was
stateless. The fix records what they read — the slices stay exactly where
they are (prompts byte-identical), only the #1737 table gains the entries,
and the acts can quote them (lot 6's reading record).

Deliberate non-goal, pinned here: the PER-ARGUMENT instances stay stateless.
The reading record is document-scoped by construction — every line renders
"k of N chars" against the document — so a unit-relative read recorded there
would render as a false document bound.

Mutations that must redden this file (rendered in the PR): removing any of
the three ``_record_window`` calls / the ``state=`` kwarg, dropping the
invoke-layer wiring, or adding ``reading_state`` to the per-argument
construction. Synthetic opaque text only; no cassette surface moves.
"""

import ast
from pathlib import Path
from unittest.mock import AsyncMock, create_autospec

import pytest
from semantic_kernel.kernel import Kernel

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)
from argumentation_analysis.reporting.restitution.reading_record import (
    ReadingLine,
    ReadingRecord,
    format_reading_block,
)

_DOC_CHARS = 56_000  # doc_A shape, per the coordinator's R1100 measure
_PROSE = "une affirmation, une autre; voici une clause, encore une, et voici. "

# Minimal two-level taxonomy: one root, one child — enough for the wide-net
# index and one descent step.
_TAXONOMY = [
    {
        "PK": "10",
        "path": "2",
        "depth": "1",
        "text_fr": "Hors sujet",
        "text_en": "Irrelevance",
        "desc_fr": "Arguments sans rapport",
        "desc_en": "Unrelated arguments",
        "example_fr": "",
        "example_en": "",
        "nom_vulgarisé": "Hors sujet",
    },
    {
        "PK": "11",
        "path": "2.1",
        "depth": "2",
        "text_fr": "Ad Hominem",
        "text_en": "Ad Hominem",
        "desc_fr": "Attaque la personne",
        "desc_en": "Attacks the person",
        "example_fr": "",
        "example_en": "",
        "nom_vulgarisé": "Ad Hominem",
    },
]


class _RecordingState:
    """Mirrors ``UnifiedAnalysisState.record_reading_window`` verbatim
    (shared_state.py:261) — same entry shape, so the assertions read the
    real contract, not a convenient fake."""

    def __init__(self):
        self.reading_window_status = {}

    def record_reading_window(self, site, selection):
        self.reading_window_status[site] = {
            "status": getattr(selection, "status", str(selection)),
            "offset": getattr(selection, "offset", 0),
            "window": getattr(selection, "window", 0),
        }


def _long_doc(chars: int) -> str:
    text = _PROSE * (chars // len(_PROSE) + 1)
    return text[:chars]


def _plugin(state, llm=None):
    return FallacyWorkflowPlugin(
        master_kernel=create_autospec(Kernel, instance=True),
        llm_service=llm or AsyncMock(),
        taxonomy_data=_TAXONOMY,
        reading_state=state,
    )


class TestWidenetHeadRecorded:
    async def test_widenet_head_is_recorded_selected(self):
        """The Phase-1 prompt reads the first 8000 chars of a 56k document —
        the record must say (0, 8000, selected), the slice untouched."""
        state = _RecordingState()
        plugin = _plugin(state)
        plugin.llm_service.get_chat_message_content = AsyncMock(return_value="[]")
        candidates = await plugin._wide_net_candidates(_long_doc(_DOC_CHARS))
        assert candidates == []
        assert state.reading_window_status["fallacy_widenet"] == {
            "status": "selected",
            "offset": 0,
            "window": 8000,
        }

    async def test_widenet_short_text_reads_whole(self):
        """A text shorter than the window is read whole. The record takes
        its window from the mirrored slice (#2908 rework, form (b)): a
        short text records (selected, 0, len) — the whole text, read —
        which the reading record's truncated_lines correctly excludes
        (window == source_chars bounds nothing)."""
        state = _RecordingState()
        plugin = _plugin(state)
        plugin.llm_service.get_chat_message_content = AsyncMock(return_value="[]")
        short = "court, très court."
        await plugin._wide_net_candidates(short)
        assert state.reading_window_status["fallacy_widenet"] == {
            "status": "selected",
            "offset": 0,
            "window": len(short),
        }


class TestDescentWindowRecorded:
    async def test_descent_window_recorded_before_any_llm_call(self):
        """Both descent prompts (leaf L-confirm and navigation) carry the same
        [:500] head; one site says it, recorded at method entry — the stub
        answers plain text (no function call), the branch exhausts, and the
        record is already there."""
        state = _RecordingState()
        plugin = _plugin(state)
        plugin.llm_service.get_chat_message_content = AsyncMock(
            return_value="pas d'appel d'outil — branche épuisée"
        )
        slave_kernel, slave_settings = plugin._create_slave_kernel()
        await plugin._explore_single_branch(
            _long_doc(_DOC_CHARS),
            "10",
            slave_kernel,
            slave_settings,
        )
        assert state.reading_window_status["fallacy_descent"] == {
            "status": "selected",
            "offset": 0,
            "window": 500,
        }


class TestOneShotRecorded:
    async def test_one_shot_selection_is_recorded(self):
        """The #2908-bounded one-shot selection was computed but never
        recorded (stateless call); the document path now threads the state —
        same selection, entry in the table."""
        state = _RecordingState()
        plugin = _plugin(state)
        plugin.llm_service.get_chat_message_content = AsyncMock(
            return_value=(
                '{"fallacy_name": "Ad Hominem", "taxonomy_pk": "11", '
                '"explanation": "synthetic", "confidence": 0.5}'
            )
        )
        await plugin._run_one_shot(_long_doc(_DOC_CHARS))
        entry = state.reading_window_status["fallacy_one_shot"]
        assert entry["window"] == 8000
        assert entry["offset"] == 0
        assert entry["status"] == "selected"


class TestStatelessConstructions:
    async def test_stateless_construction_records_nothing(self):
        """Control / anti-mutation: the per-argument instances (and every
        pre-existing test construction) pass no state and must record
        nothing — a unit-relative read does not belong in a
        document-scoped record."""
        state = _RecordingState()
        # Constructed exactly like the per-arg sites: no reading_state kwarg.
        plugin = FallacyWorkflowPlugin(
            master_kernel=create_autospec(Kernel, instance=True),
            llm_service=AsyncMock(),
            taxonomy_data=_TAXONOMY,
        )
        plugin.llm_service.get_chat_message_content = AsyncMock(return_value="[]")
        await plugin._wide_net_candidates(_long_doc(_DOC_CHARS))
        await plugin._run_one_shot(_long_doc(_DOC_CHARS))
        # The calls must not crash (no recorder to write to) and the default
        # construction stays stateless — a recording made unconditional has
        # nowhere to land and reddens here.
        assert getattr(plugin, "_reading_state", None) is None
        assert state.reading_window_status == {}


class TestInvokeWiring:
    async def test_document_path_threads_the_state(self, monkeypatch):
        """The wide-net document construction hands the plugin the shared
        state from the workflow context (#1737 wiring point)."""
        import argumentation_analysis.orchestration.invoke_callables as ic

        captured = {}

        class _FakePlugin:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            async def run_guided_analysis(self, argument_text, **kwargs):
                return '{"fallacies": [], "exploration_method": "stub"}'

        monkeypatch.setattr(
            "argumentation_analysis.plugins.fallacy_workflow_plugin."
            "FallacyWorkflowPlugin",
            _FakePlugin,
        )
        monkeypatch.setattr(
            "argumentation_analysis.core.llm_service.create_llm_service",
            lambda **kwargs: AsyncMock(),
        )

        async def _fake_per_arg(input_text, context):
            return {"fallacies": []}

        monkeypatch.setattr(
            ic, "_invoke_hierarchical_fallacy_per_argument", _fake_per_arg
        )

        marker = UnifiedAnalysisState(_long_doc(200))
        result = await ic._invoke_hierarchical_fallacy(
            _long_doc(200), {"_state_object": marker, "fallacy_tier": "llm"}
        )
        assert captured.get("reading_state") is marker, (
            "the document-path construction did not thread the shared state — "
            "the wide-net/descent/one-shot windows stay unrecorded (#2850 lot 7)"
        )
        assert result["fallacies"] == []

    def test_three_constructions_two_wired_one_stateless(self):
        """AST pin on the three invoke-layer constructions: the two document
        paths (wide-net, camembert) pass reading_state from the context; the
        per-argument construction deliberately does not."""
        import argumentation_analysis.orchestration.invoke_callables as _ic

        tree = ast.parse(
            Path(_ic.__file__).read_text(encoding="utf-8-sig"),
            filename="invoke_callables.py",
        )
        constructions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "FallacyWorkflowPlugin"
        ]
        assert len(constructions) == 3, (
            f"expected 3 plugin constructions, found {len(constructions)} — "
            "this pin must be re-measured when a construction appears"
        )

        def _passes_reading_state(call_node):
            return any(
                kw.arg == "reading_state"
                and isinstance(kw.value, ast.Call)
                and isinstance(kw.value.func, ast.Name)
                and kw.value.func.id == "reading_state_from_context"
                for kw in call_node.keywords
            )

        wired = sum(1 for c in constructions if _passes_reading_state(c))
        assert wired == 2, (
            f"expected exactly 2 document-path constructions wired with "
            f"reading_state_from_context, found {wired} — the per-argument "
            "construction must stay stateless (document-scoped record)"
        )


class TestActsCanQuoteThem:
    def test_fallacy_sites_render_in_french(self):
        """The three new sites render under their French labels with the
        k-of-N phrasing — a label-less site would render its raw name."""
        record = ReadingRecord(
            lines=[
                ReadingLine(
                    site="fallacy_widenet", status="selected", offset=0, window=8000
                ),
                ReadingLine(
                    site="fallacy_descent", status="selected", offset=0, window=500
                ),
                ReadingLine(
                    site="fallacy_one_shot", status="selected", offset=0, window=8000
                ),
            ],
            source_chars=_DOC_CHARS,
        )
        block = format_reading_block(record)
        assert "détection de sophismes — large filet" in block
        assert "détection de sophismes — descente" in block
        assert "détection de sophismes — repli en un appel" in block
        assert f"8000 des {_DOC_CHARS}" in block
        assert f"500 des {_DOC_CHARS}" in block
