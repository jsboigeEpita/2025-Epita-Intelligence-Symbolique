# -*- coding: utf-8 -*-
"""#1906 guard: the metadata a corpus run hands to the model must be earned.

Two defects, both of which became reader-facing when #1913 wired
``source_metadata`` through the batch runner. ``act1_framing_plugin`` renders
every key of ``state.source_metadata`` verbatim, so what this merge produces is
a contract with the model, not an internal detail.

- **Precedence was inverted.** The merge was ``classified.setdefault(k, v)``,
  but ``classify_metadata`` *always* writes its four keys, defaulting to
  ``"unknown"``. The sentinel is a value, so ``setdefault`` protected it and
  discarded the explicit value from the corpus definition. Only keys the
  inference never writes (e.g. ``speaker``) survived — which is why the defect
  went unnoticed: some fields did work.
- **``regime_type`` was asserted, not inferred.** It was assigned ``"democracy"``
  unconditionally, so no input could change it, contradicting the function's own
  docstring ("the fields default to unknown"). A grep for code consumers returns
  zero, and that grep under-counts: the consumer is the prompt.

Lives in ``tests/scripts/`` and not beside the runner's other tests in
``tests/integration/triage/`` for one measured reason: the CI argv
(``ci.yml``) names only ``orchestration|services|workers|api`` under
``tests/integration/``. A guard the harness does not name is not a guard — the
first version of these tests ran nowhere. ``tests/scripts/`` is named, and
already hosts ``test_corpus_batch_coverage_1903.py`` for this same script.
Widening the gate is #1867's subject, not this PR's.

Synthetic opaque identifiers only — no encrypted dataset, no LLM call.
"""

import importlib.util
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "dataset" / "run_corpus_batch.py"
)


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_corpus_batch_under_test_1906", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _merge(src_name: str, date_iso: str, src_meta: dict) -> dict:
    """Call the production merge — never a copy of it.

    A first version of this helper reproduced the merge inline, because the
    logic lived inside ``main()`` and was unreachable. The control exposed it:
    with the production change reverted, four of six tests still passed, since
    they exercised the copy. ``main()`` now delegates to
    ``merge_source_metadata`` so these assertions have something real to fail
    against.
    """
    runner = _load_runner()
    return runner.merge_source_metadata(
        runner.merge_source_metadata(
            runner.classify_metadata(src_name, date_iso),
            runner.parse_legacy_label(src_name),
        ),
        src_meta,
    )


class TestMetadataPrecedence:
    def test_explicit_field_wins_over_failed_inference(self):
        merged = _merge(
            "Some Document", "", {"era": "era_A", "discourse_type": "plaidoyer"}
        )
        assert merged["era"] == "era_A"
        assert merged["discourse_type"] == "plaidoyer"

    def test_key_the_inference_never_writes_still_passes_through(self):
        """Control: the one shape that already worked must keep working."""
        merged = _merge("Some Document", "", {"speaker": "Speaker_A"})
        assert merged["speaker"] == "Speaker_A"

    def test_inference_still_wins_when_nothing_explicit_is_supplied(self):
        """Discriminator — without it, a merge that ignored ``src_meta``
        entirely would pass the test above by accident."""
        merged = _merge("Discours du President", "2024-06-15", {})
        assert merged["discourse_type"] == "political"
        assert merged["era"] == "2024"

    def test_explicit_unknown_does_not_erase_a_real_inference(self):
        """Anti-pendulum: precedence is for *values*, not for the sentinel.

        A definition carrying an explicit ``"unknown"`` must not overwrite a
        field the label inference actually resolved — otherwise the fix would
        invert the defect instead of removing it.
        """
        merged = _merge(
            "Discours du President", "2024-06-15", {"discourse_type": "unknown"}
        )
        assert merged["discourse_type"] == "political"


class TestNoAssertedRegime:
    def test_regime_type_is_not_asserted_for_an_arbitrary_source(self):
        """It is not an inference — no input could change it — and the corpus
        is not uniformly democratic. Since #1913 the value reaches the model as
        source metadata, so asserting it is a factual claim the pipeline has no
        basis for."""
        meta = _load_runner().classify_metadata("Some Document")
        assert meta["regime_type"] == "unknown"

    def test_an_explicit_regime_from_the_corpus_definition_wins(self):
        """Removing the constant must not remove the ability to state it."""
        merged = _merge("Some Document", "", {"regime_type": "regime_A"})
        assert merged["regime_type"] == "regime_A"


class TestLegacyLabelParsing:
    """#1906 scope item 2: a single parser/normalizer for legacy source labels.

    Most corpus definitions carry speaker/title/year information in the label
    string and no structured metadata dict — without a parser, the model was
    handed ``unknown`` for fields the label states explicitly, and Act I
    reported an absent speaker that Act III then inferred from the text (the
    inter-act contradiction this issue exists to close). The parser may only
    claim what the label structurally states: genuinely absent fields stay
    omitted, never invented.
    """

    def test_speaker_title_year_dash_shape(self):
        parsed = _load_runner().parse_legacy_label("Speaker_A - Title_X 1940")
        assert parsed["speaker"] == "Speaker_A"
        assert parsed["title"] == "Title_X"
        assert parsed["date_or_year"] == "1940"
        assert parsed["era"] == "1940"

    def test_three_segment_dash_shape_keeps_work_and_piece(self):
        parsed = _load_runner().parse_legacy_label("Speaker_A - Work_X - Piece_Y 1994")
        assert parsed["speaker"] == "Speaker_A"
        assert parsed["title"] == "Work_X - Piece_Y"
        assert parsed["date_or_year"] == "1994"

    def test_inverted_work_author_shape_resolves_the_author(self):
        """A single-word first segment followed by a person-shaped second
        segment is ``Oeuvre - Auteur``, not ``Auteur - Oeuvre``."""
        parsed = _load_runner().parse_legacy_label("Oeuvre_X - Author_First Last")
        assert parsed["speaker"] == "Author_First Last"

    def test_french_genre_keyword_yields_speaker_and_date(self):
        parsed = _load_runner().parse_legacy_label("Speaker_A Discours 12/03/1938")
        assert parsed["speaker"] == "Speaker_A"
        assert parsed["genre"] == "discours"
        assert parsed["date_or_year"] == "12/03/1938"
        assert parsed["era"] == "1938"

    def test_hyphenated_pair_and_parenthetical_venue(self):
        parsed = _load_runner().parse_legacy_label(
            "Speaker_A-Speaker_B Genreword_X 1 (Venue_Y)"
        )
        assert parsed["speaker"] == "Speaker_A-Speaker_B"
        assert parsed["venue"] == "Venue_Y"

    def test_genre_keyword_at_start_leaves_speaker_absent(self):
        parsed = _load_runner().parse_legacy_label("Discours du President")
        assert "speaker" not in parsed
        assert parsed["genre"] == "discours"

    def test_nothing_inferable_is_stated(self):
        """Anti-theater control: a label with no structure yields no claims —
        an omitted key, never a guessed value."""
        parsed = _load_runner().parse_legacy_label("corpus_X")
        assert parsed == {}

    def test_file_format_parenthetical_is_not_a_venue(self):
        """A ``(PDF)`` tag describes the artifact's format, not the arena —
        claiming it as venue hands the model a false fact."""
        parsed = _load_runner().parse_legacy_label("Speaker_A Discours (PDF)")
        assert "venue" not in parsed
        assert parsed["speaker"] == "Speaker_A"

    def test_wiring_parsed_label_reaches_the_merged_metadata(self):
        """The parser must be in the production merge chain — a parser nobody
        calls would green every unit test above and change nothing."""
        merged = _merge("Speaker_A - Title_X 1940", "", {})
        assert merged["speaker"] == "Speaker_A"
        assert merged["era"] == "1940"

    def test_wiring_explicit_definition_still_wins_over_parsed_label(self):
        """Anti-pendulum: adding a parser must not dethrone the explicit
        corpus definition — precedence order is heuristics < label < explicit."""
        merged = _merge("Speaker_A - Title_X 1940", "", {"speaker": "Explicit_Speaker"})
        assert merged["speaker"] == "Explicit_Speaker"
