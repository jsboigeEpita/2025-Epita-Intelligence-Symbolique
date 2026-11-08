"""Synthetic reader-header guards (#3487)."""

from scripts.dataset.run_corpus_batch import expand_corpus, strip_reader_header
from scripts.dataset.judge_panel import document_texts_from_definitions
from scripts.dataset import run_zeroshot_arm


def test_header_stripped_and_counted_across_consumers(monkeypatch):
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-3487")
    header = "Title: synthetic\r\nURL Source: https://example.invalid\r\nPublished Time: 2001\r\nMarkdown Content:\r\n"
    body = "\nTexte synthétique.\n"
    definitions = [
        {"source_name": "synthetic", "extracts": [{"extract_text": header + body}]}
    ]
    docs, _, _ = expand_corpus(definitions)
    doc = docs[0]
    assert doc["full_text"] == body
    assert doc["reader_header_stripped"] == len(header)
    assert (
        document_texts_from_definitions(definitions, [doc["opaque_id"]])[
            doc["opaque_id"]
        ]
        == body
    )
    assert run_zeroshot_arm.expand_corpus(definitions)[0][0]["full_text"] == body


def test_single_line_header_stripped(monkeypatch):
    # The shape the only analysed header actually carries (#3490 review):
    # all four fields on ONE line, separated by spaces, body right after
    # the marker's single following space.
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-3487")
    header = (
        "Title: synthetic URL Source: https://example.invalid "
        "Published Time: 2001 Markdown Content: "
    )
    body = "Texte synthétique."
    definitions = [
        {"source_name": "synthetic", "extracts": [{"extract_text": header + body}]}
    ]
    docs, _, _ = expand_corpus(definitions)
    doc = docs[0]
    assert doc["full_text"] == body
    assert doc["reader_header_stripped"] == len(header)
    assert (
        document_texts_from_definitions(definitions, [doc["opaque_id"]])[
            doc["opaque_id"]
        ]
        == body
    )
    assert run_zeroshot_arm.expand_corpus(definitions)[0][0]["full_text"] == body


def test_plain_and_late_markers_are_unchanged():
    for text in (
        "Texte ordinaire.\n",
        "Title: synthetic\n" + "x" * 1600 + "\nMarkdown Content:\nbody",
        "Introduction\nTitle: cited\nMarkdown Content:\nbody",
        # Single-line shape without the offset-0 prefix fields: a mid-body
        # mention of the marker is not a reader header.
        "Introduction cites Markdown Content: body",
    ):
        assert strip_reader_header(text) == (text, 0)


def test_length_cap_applies_after_header_removal(monkeypatch):
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-3487")
    definitions = [
        {
            "source_name": "synthetic",
            "extracts": [{"extract_text": "Title: synthetic\nMarkdown Content:\nbody"}],
        }
    ]
    docs, _, skipped = expand_corpus(definitions, max_chars=4)
    assert skipped == 0
    assert docs[0]["full_text"] == "body"
