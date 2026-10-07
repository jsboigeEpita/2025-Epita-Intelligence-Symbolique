"""#2973 (Expected 2) — the kb_heuristic producer records the offset it
extracted from, at split time; the search is only the fallback.

The defect (paid run 06/10, doc_A): the heuristic producer splits the text,
strips each sentence, then hands the state a unit text it can no longer
place. ``locate_unit_offset`` searches the source for it — a first-occurrence
guess that (a) returns None on a unit whose text occurs twice (the exact and
flexible steps both refuse non-unique matches), and (b) could never return
the TRUE second position even when allowed to guess.

The fix moves the knowledge to where it exists: the splitter knows the
position of every piece it emits. Offsets are recorded at split time and
ride the payload (``text_offset``) through the writers into
``add_argument(offset=...)``, which uses a stated, in-range offset directly
(basis ``"producer-recorded"``) and searches only when the producer could
not state one. Chunks are exact substrings carrying their origin, so an
intra-chunk position translates to a source position by addition — never a
search.

Born red against the search-only code (witnesses 1-8); positive controls
(9-10) pin the unchanged extraction output.
"""

import json
from unittest.mock import MagicMock, call

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_text_to_kb_to_state,
)
from argumentation_analysis.plugins.text_to_kb_plugin import (
    TextToKBPlugin,
    _heuristic_extract_arguments,
    _split_into_chunks,
    _split_sentences,
)

# Crafted so the heuristic emits TWO IDENTICAL units ("En effet, ..." twice,
# each closed by a "Donc, ..." marker) at distinct true positions: the
# search-only code cannot anchor either one.
_PART = "En effet, the repeated claim is stated right here."
_DUP_TEXT = (
    f"Opening context before anything else at all. {_PART} "
    f"Donc, a distinct middle unit follows the first. {_PART} "
    f"Donc, a distinct closing unit ends the run."
)


class TestProducerSplitRecordsOffsets:
    """The producer records true offsets at split time (#2973 item 2)."""

    def test_duplicate_units_get_distinct_true_offsets(self):
        """Two identical unit texts carry their TRUE, distinct positions.

        Red on the search-only code: ``text_offset`` did not exist, and the
        search cannot anchor a duplicate at all.
        """
        args = _heuristic_extract_arguments(_DUP_TEXT)
        duplicates = [a for a in args if a.text == _PART]
        assert len(duplicates) == 2
        first, second = duplicates
        # Each offset is the TRUE position of that occurrence — the second
        # unit points at the second occurrence, not the first (what a
        # first-occurrence search returns) and not None (what the
        # non-unique-aware search returns).
        assert first.text_offset == _DUP_TEXT.find(_PART)
        assert second.text_offset == _DUP_TEXT.rfind(_PART)
        assert first.text_offset != second.text_offset
        for a in duplicates:
            assert a.text_offset is not None
            assert _DUP_TEXT[a.text_offset : a.text_offset + len(_PART)] == _PART

    def test_offset_points_at_first_content_character(self):
        """The offset is the first CONTENT character, leading whitespace skipped."""
        text = f"   {_PART}"
        args = _heuristic_extract_arguments(text)
        assert len(args) == 1
        assert args[0].text_offset == len(text) - len(text.lstrip())
        assert text[args[0].text_offset : args[0].text_offset + len(_PART)] == _PART

    def test_base_offset_translates_chunk_positions(self):
        """A chunk extracted at its origin reports SOURCE offsets (addition)."""
        args = _heuristic_extract_arguments(_PART, base_offset=100)
        assert len(args) == 1
        # Intra-chunk position 0 + origin 100 = source position 100 — the
        # translation is the addition, never a search into the source.
        assert args[0].text_offset == 100


class TestSentenceOffsetsPositional:
    """``_split_sentences_with_offsets`` adds positions, changes no text."""

    def test_each_sentence_is_verbatim_at_its_offset(self):
        # Imported here (not at module level): the symbol is NEW in #2973,
        # and a module-level ImportError would turn the whole file into a
        # collection ERROR that masks the other witnesses' néo-rouge.
        from argumentation_analysis.plugins.text_to_kb_plugin import (
            _split_sentences_with_offsets,
        )

        text = "  Abc def. Short piece. Tail sentence long enough to stand alone."
        sentences = _split_sentences_with_offsets(text)
        # Same texts as the #2982 splitter, positionally.
        assert [s for s, _ in sentences] == _split_sentences(text)
        # "Short piece." (<= 20 chars) joins its opener (#2982) and the
        # joined sentence KEEPS the opener's offset: the group starts where
        # its first sentence starts.
        joined, tail = sentences
        assert joined[0] == "Abc def. Short piece."
        assert text[joined[1] : joined[1] + len("Abc def.")] == "Abc def."
        for sentence, offset in sentences:
            assert text[offset : offset + len(sentence)] == sentence


class TestChunkOrigins:
    """Chunks are exact substrings carrying their source origin."""

    def test_chunks_are_exact_substrings_at_ascending_origins(self):
        text = (
            "First paragraph body here.\n\n\n\nSecond paragraph body follows now."
            "\n\nThird paragraph closes the document properly."
        )
        chunks = _split_into_chunks(text, max_chars=30)
        assert len(chunks) >= 2
        previous_end = 0
        for chunk, origin in chunks:
            # Exact substring: an intra-chunk position + origin IS the
            # source position — no normalisation, no search.
            assert text[origin : origin + len(chunk)] == chunk
            assert origin >= previous_end
            previous_end = origin + len(chunk)
        # The second chunk starts at the TRUE position of its first
        # paragraph — separators ("\n\n\n\n") are skipped, content is not.
        origins = [origin for _, origin in chunks]
        assert origins[1] == text.index("Second paragraph")

    def test_short_text_single_chunk(self):
        chunks = _split_into_chunks("No paragraph breaks at all in this text.")
        assert len(chunks) == 1


class TestAddArgumentStatedOffset:
    """``add_argument`` uses a stated offset directly; search is fallback."""

    def test_stated_offset_used_directly_over_search(self):
        state = UnifiedAnalysisState("Some raw text with Alpha Unit inside it.")
        state.add_argument("Alpha Unit inside", producer="kb_heuristic", offset=5)
        entry = state.argument_provenance["arg_1"]
        # The producer stated 5 — the search would have said 21 (exact match
        # position). The stated, in-range offset WINS.
        assert entry["offset"] == 5
        assert entry["offset_basis"] == "producer-recorded"

    def test_invalid_or_absent_stated_offset_falls_back_to_search(self):
        raw = "Some raw text with Alpha Unit inside it."
        expected = raw.find("Alpha Unit inside")
        for stated in (10**6, None, True):  # out of range / absent / bool junk
            state = UnifiedAnalysisState(raw)
            state.add_argument(
                "Alpha Unit inside", producer="kb_heuristic", offset=stated
            )
            entry = state.argument_provenance["arg_1"]
            assert entry["offset"] == expected
            assert entry["offset_basis"] != "producer-recorded"


class TestWriterThreadsStatedOffset:
    """Both writers thread the stated offset into ``add_argument``."""

    def test_end_to_end_duplicate_units_both_anchored(self):
        """Flagship: the paid-run defect end-to-end, on a REAL state.

        Producer → payload → orchestration writer → provenance: BOTH
        duplicate units land with true, distinct, producer-recorded offsets.
        Red on the search-only writer: the duplicates search to None.
        """
        state = UnifiedAnalysisState(_DUP_TEXT)
        args = _heuristic_extract_arguments(_DUP_TEXT)
        payload = {"arguments": [a.model_dump() for a in args], "belief_candidates": []}
        _write_text_to_kb_to_state(payload, state, {})
        provenance = state.argument_provenance
        assert len(provenance) == 5
        duplicate_offsets = sorted(
            e["offset"]
            for e in provenance.values()
            if e["producer"] == "kb_heuristic"
            and e["offset"] in (_DUP_TEXT.find(_PART), _DUP_TEXT.rfind(_PART))
        )
        assert duplicate_offsets == [
            _DUP_TEXT.find(_PART),
            _DUP_TEXT.rfind(_PART),
        ]
        # Every unit is anchored — no None left for the census to count.
        assert all(e["offset"] is not None for e in provenance.values())
        assert all(
            e["offset_basis"] == "producer-recorded" for e in provenance.values()
        )

    def test_plugin_writer_passes_stated_offset(self):
        plugin = TextToKBPlugin()
        state = MagicMock()
        state.add_argument.return_value = "arg_1"
        payload = {
            "arguments": [
                {"text": "unit a", "text_offset": 7},
                {"text": "unit b", "text_offset": True},  # bool junk -> None
                {"text": "unit c"},  # absent -> None
            ],
            "belief_candidates": [],
            "target_logic": "fol",
        }
        plugin.write_kb_to_state(json.dumps(payload), state=state)
        assert state.add_argument.call_args_list == [
            call("unit a", offset=7),
            call("unit b", offset=None),
            call("unit c", offset=None),
        ]


class TestPositiveControls:
    """The extraction OUTPUT itself is unchanged — only positions were added."""

    def test_extraction_texts_unchanged(self):
        args = _heuristic_extract_arguments(_DUP_TEXT)
        assert [a.text for a in args] == [
            "Opening context before anything else at all.",
            _PART,
            "Donc, a distinct middle unit follows the first.",
            _PART,
            "Donc, a distinct closing unit ends the run.",
        ]

    def test_empty_text_still_no_arguments(self):
        assert _heuristic_extract_arguments("") == []
        assert len(_split_into_chunks("")) == 1
