"""#3522 — the whole-document status has a reader.

``persona_reading`` records ``whole_document`` when the document fits one
call. The reading record prints a status through ``_STATUS_PHRASES_FR``, and a
status the table does not carry falls back to its raw token: the block would
have read « historien — situation du document » : whole_document — the
code-written-English-token class #3225/#3244 closed, on five of the ten panel
documents and two sites each.

Before this status existed, every status the recorded panel states carry had
its phrase (20 states, cycles 5 and 6: no raw token on any line). The last
witness keeps it so for the next status: a status with no phrase fails here,
not in a render.

Synthetic and free: no LLM, no network, no corpus.
"""

from __future__ import annotations

from argumentation_analysis.core import reading_window
from argumentation_analysis.core.reading_window import (
    STATUS_WHOLE_DOCUMENT,
    persona_reading,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.reading_record import (
    _STATUS_PHRASES_FR,
    ReadingLine,
    build_reading_record,
    format_reading_block,
    format_reading_line,
)

_PROSE = "une phrase de contexte, avec des virgules; et une autre clause. "


def _text(chars: int) -> str:
    return (_PROSE * (chars // len(_PROSE) + 1))[:chars]


class TestWholeDocumentLine:
    def test_the_line_says_whole_in_the_readers_words(self) -> None:
        line = ReadingLine(
            site="historian",
            status=STATUS_WHOLE_DOCUMENT,
            window=2_201,
            windows=1,
            chars_read=2_201,
        )

        rendered = format_reading_line(line, 2_201)

        assert rendered.startswith(
            "« historien — situation du document » : document lu en entier "
            "(2201 caractères)"
        ), rendered
        assert STATUS_WHOLE_DOCUMENT not in rendered

    def test_a_persona_read_reaches_the_block_without_its_token(self) -> None:
        """The real seam, end to end: the read, the state's recorder, the
        record, the block the acts graft."""
        text = _text(2_201)
        moves = [
            {"kind": "claim", "reading": "m", "quote": "", "offset": 300},
            {"kind": "claim", "reading": "m", "quote": "", "offset": 1_500},
        ]
        state = UnifiedAnalysisState(text)
        for site in ("historian", "strategist"):
            _, selection, extra = persona_reading(text, moves)
            state.record_reading_window(site, selection, extra)

        block = format_reading_block(build_reading_record(state))

        assert STATUS_WHOLE_DOCUMENT not in block, block
        assert block.count("document lu en entier (2201 caractères)") == 2, block


class TestEveryRecordedStatusHasAPhrase:
    def test_no_reading_status_can_reach_the_reader_raw(self) -> None:
        statuses = {
            value
            for name, value in vars(reading_window).items()
            if name.startswith("STATUS_") and isinstance(value, str)
        }
        # The census itself must see the vocabulary, or the check below
        # passes on an empty set.
        assert STATUS_WHOLE_DOCUMENT in statuses and len(statuses) >= 7

        # Never recorded as such: the descent translates both to ``selected``
        # before it records its site (``fallacy_workflow_plugin``, the
        # ``base_status`` of the descent record) and keeps the fallback as a
        # count in the entry's extras.
        internal = {
            reading_window.STATUS_CENTRED_ON_QUOTE,
            reading_window.STATUS_HEAD_FALLBACK,
        }
        # ``selected`` is the status every counted branch of
        # ``format_reading_line`` renders; it needs no phrase.
        rendered_by_counts = {reading_window.STATUS_SELECTED}

        missing = sorted(
            status
            for status in statuses - internal - rendered_by_counts
            if status not in _STATUS_PHRASES_FR
        )

        assert missing == [], f"statuses a reader would see raw: {missing}"
