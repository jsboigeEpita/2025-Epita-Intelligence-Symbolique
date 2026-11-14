"""#3511 + #3565 (R1167 dispatch) — the first reading's prompt carries the
three measured disciplines, in general terms.

The free replays behind each (recorded panel artifacts, no paid call):

* **Chain** (#3511 taxonomy): 8 of 35 judge passages were never named by any
  recorded reading, 7 of them in ONE document's mid-band; the named classes
  were thin (distinction 4, peroration 2) — the lever is how the reading
  walks the document, not how much it may name (the inventory bound, the
  #3511 rework, already binds that side).
* **End-first + bare stretch** (#3511 oracle): moves := the judge's own
  passages are carried 35/35 (c6) and 39/39 (c8) at every rule — the
  selector seats whatever is named, so the ask is a reading that NAMES the
  late and the unquoted stretches.
* **Placement** (#3565 geometry): every recorded reading placed 4–7 moves
  INSIDE the target region but 80–1039 characters BESIDE the passages —
  quotes that name a place without quoting it.

Anti-overfitting (dispatch, HARD): no band, share or constant tuned on the
35 passages — the witness pins that the disciplines stay in general terms.

Synthetic documents only: markers and filler, no corpus content.
"""

from argumentation_analysis.agents.core.reading.first_reading import (
    build_first_reading_prompt,
)


def _synth_document(parts: int = 4, part_len: int = 5300) -> str:
    filler = "la phrase continue sans rien affirmer de neuf par ici. " * 400
    chunks = []
    for i in range(parts):
        marker = f"marqueur-numero-{i:02d}"
        chunk = f"{marker} {filler}"
        chunks.append(chunk[:part_len].ljust(part_len))
    return "".join(chunks)


def _flat(prompt: str) -> str:
    """The prompt with its line-wrapping collapsed — the disciplines are
    asserted as WORDS, not as a wrapped layout."""
    return " ".join(prompt.split())


class TestTheThreeDisciplines:
    def test_step3_reads_the_document_as_one_chain(self):
        flat = _flat(build_first_reading_prompt(_synth_document()))
        assert "one CHAIN" in flat
        assert "link the thesis hangs from" in flat

    def test_step3_rewalks_the_document_from_the_end(self):
        flat = _flat(build_first_reading_prompt(_synth_document()))
        assert "FROM THE END" in flat

    def test_step3_revisits_the_stretch_no_quote_touches(self):
        flat = _flat(build_first_reading_prompt(_synth_document()))
        assert "none of your quotes touches" in flat

    def test_the_anchor_rule_demands_the_sentence_the_argument_lives_in(self):
        flat = _flat(build_first_reading_prompt(_synth_document()))
        assert "LIVES IN" in flat
        assert "quoted from that stretch itself" in flat


class TestGeneralTermsOnly:
    def test_no_tuned_number_survives_in_the_disciplines(self):
        """Anti-overfitting (dispatch): the disciplines name no band, share
        or count tuned on the passages — no percentage, no fixed fraction of
        the document, no character count."""
        prompt = build_first_reading_prompt(_synth_document())
        for banned in ("%", "per cent", "percent", "last tenth", "final tenth"):
            assert banned not in prompt, banned

    def test_the_answer_schema_is_unchanged(self):
        """The three disciplines touch the ASK, never the answer format: the
        JSON block keeps its slots and closed vocabularies verbatim."""
        prompt = build_first_reading_prompt(_synth_document())
        assert '"thesis": {"reading"' in prompt
        assert '"moves": [{"kind"' in prompt
        assert '"pillars": [{"kind"' in prompt

    def test_the_earlier_asks_stay(self):
        """Non-regression: the #3511 rework's own question is untouched —
        every argument, exhaustively, one verbatim anchor of 8 to 40
        words."""
        prompt = build_first_reading_prompt(_synth_document())
        assert "EVERY argument" in prompt
        assert "exhaustively" in prompt
        assert "8 to 40 words" in prompt
        assert "BY ITS KIND" not in prompt

    def test_the_prompt_is_deterministic(self):
        doc = _synth_document()
        assert build_first_reading_prompt(doc) == build_first_reading_prompt(doc)
