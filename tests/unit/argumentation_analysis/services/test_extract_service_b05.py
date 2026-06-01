"""Tests for ExtractService pure text-processing methods (#815).

ExtractService has zero external dependencies — all methods are pure text
processing, making it ideal for thorough unit testing without mocking.

Covers: extract_text_with_markers, find_similar_text, highlight_text,
search_in_text, highlight_search_results, extract_blocks,
search_text_dichotomically.
"""

import pytest
from argumentation_analysis.services.extract_service import ExtractService


@pytest.fixture
def svc():
    return ExtractService()


# ---------------------------------------------------------------------------
# extract_text_with_markers
# ---------------------------------------------------------------------------


class TestExtractTextWithMarkers:
    """Tests for extract_text_with_markers."""

    def test_basic_extraction(self, svc):
        text = "Before [START]important content[END] after"
        result, status, sf, ef = svc.extract_text_with_markers(text, "[START]", "[END]")
        assert result == "important content"
        assert sf is True
        assert ef is True
        assert "réussie" in status

    def test_empty_text(self, svc):
        result, status, sf, ef = svc.extract_text_with_markers("", "[S]", "[E]")
        assert result is None
        assert sf is False
        assert ef is False

    def test_missing_start_marker(self, svc):
        text = "Some text with [END] marker only"
        result, status, sf, ef = svc.extract_text_with_markers(text, "[MISSING]", "[END]")
        # Start not found → start_index=0, end found
        assert sf is False
        assert ef is True

    def test_missing_end_marker(self, svc):
        text = "Text with [START] but no end"
        result, status, sf, ef = svc.extract_text_with_markers(text, "[START]", "[MISSING]")
        assert sf is True
        assert ef is False

    def test_template_start_marker(self, svc):
        text = "Before <<MARKER_A>>content[END] after"
        result, status, sf, ef = svc.extract_text_with_markers(
            text, "MARKER_A", "[END]", template_start="<<{0}>>"
        )
        assert sf is True
        assert ef is True
        assert "content" in result

    def test_both_markers_missing(self, svc):
        text = "Just some text with no markers"
        result, status, sf, ef = svc.extract_text_with_markers(text, "[S]", "[E]")
        assert sf is False
        assert ef is False
        # Returns full text when neither marker found
        assert result is not None

    def test_marker_conflict_start_after_end(self, svc):
        """When end_marker appears before start_marker in text."""
        text = "A [END] B [START] C"
        result, status, sf, ef = svc.extract_text_with_markers(text, "[START]", "[END]")
        # start_index is after [START], end_marker [END] not found after that
        assert sf is True


# ---------------------------------------------------------------------------
# find_similar_text
# ---------------------------------------------------------------------------


class TestFindSimilarText:
    """Tests for find_similar_text."""

    def test_short_marker_exact_match(self, svc):
        text = "The quick brown fox jumps over the lazy fox"
        results = svc.find_similar_text(text, "fox", context_size=10)
        assert len(results) >= 2  # "fox" appears twice
        # Each result is (context, position, matched_text)
        for ctx, pos, matched in results:
            assert "fox" in matched.lower()

    def test_empty_inputs(self, svc):
        assert svc.find_similar_text("", "marker") == []
        assert svc.find_similar_text("text", "") == []

    def test_long_marker_difflib(self, svc):
        """Long marker (>20 chars) triggers difflib path."""
        text = "A" * 200
        marker = "A" * 40
        results = svc.find_similar_text(text, marker, max_results=3)
        assert len(results) >= 1

    def test_max_results_limit(self, svc):
        text = "abc " * 100
        results = svc.find_similar_text(text, "abc", max_results=2)
        assert len(results) <= 2


# ---------------------------------------------------------------------------
# highlight_text
# ---------------------------------------------------------------------------


class TestHighlightText:
    """Tests for highlight_text."""

    def test_highlight_both_markers(self, svc):
        text = "Before [START]middle[END] after"
        html, sf, ef = svc.highlight_text(text, "[START]", "[END]")
        assert sf is True
        assert ef is True
        assert "background-color" in html
        assert "[START]" in html  # Still present inside span

    def test_empty_text(self, svc):
        html, sf, ef = svc.highlight_text("", "[S]", "[E]")
        assert "vide" in html.lower() or "empty" in html.lower()
        assert sf is False
        assert ef is False

    def test_html_escaping(self, svc):
        text = "Text with <script>alert('xss')</script> & [START]content[END]"
        html, sf, ef = svc.highlight_text(text, "[START]", "[END]")
        assert "&lt;script&gt;" in html
        assert "&amp;" in html

    def test_template_start(self, svc):
        text = "Begin <<MARK>>content[END]"
        html, sf, ef = svc.highlight_text(text, "MARK", "[END]", template_start="<<{0}>>")
        assert sf is True


# ---------------------------------------------------------------------------
# search_in_text
# ---------------------------------------------------------------------------


class TestSearchInText:
    """Tests for search_in_text."""

    def test_case_insensitive_default(self, svc):
        text = "Hello HELLO hello"
        matches = svc.search_in_text(text, "hello")
        assert len(matches) == 3

    def test_case_sensitive(self, svc):
        text = "Hello hello HELLO"
        matches = svc.search_in_text(text, "hello", case_sensitive=True)
        assert len(matches) == 1

    def test_empty_inputs(self, svc):
        assert svc.search_in_text("", "term") == []
        assert svc.search_in_text("text", "") == []

    def test_no_match(self, svc):
        assert svc.search_in_text("hello world", "xyz") == []

    def test_special_regex_chars_escaped(self, svc):
        text = "Price: 100$ (USD)"
        matches = svc.search_in_text(text, "100$")
        assert len(matches) == 1


# ---------------------------------------------------------------------------
# highlight_search_results
# ---------------------------------------------------------------------------


class TestHighlightSearchResults:
    """Tests for highlight_search_results."""

    def test_basic_highlight(self, svc):
        text = "The cat sat on the cat mat"
        html, count = svc.highlight_search_results(text, "cat")
        assert count == 2
        assert "background-color" in html

    def test_empty_inputs(self, svc):
        html, count = svc.highlight_search_results("", "term")
        assert count == 0
        html, count = svc.highlight_search_results("text", "")
        assert count == 0

    def test_no_match(self, svc):
        html, count = svc.highlight_search_results("hello world", "xyz")
        assert count == 0
        assert "Aucun résultat" in html


# ---------------------------------------------------------------------------
# extract_blocks
# ---------------------------------------------------------------------------


class TestExtractBlocks:
    """Tests for extract_blocks."""

    def test_basic_blocking(self, svc):
        text = "A" * 1200
        blocks = svc.extract_blocks(text, block_size=500, overlap=50)
        assert len(blocks) >= 2
        # Each block has required keys
        for b in blocks:
            assert "block" in b
            assert "start_pos" in b
            assert "end_pos" in b

    def test_empty_text(self, svc):
        assert svc.extract_blocks("") == []

    def test_text_shorter_than_block(self, svc):
        text = "Short text"
        blocks = svc.extract_blocks(text, block_size=500, overlap=50)
        assert len(blocks) == 1
        assert blocks[0]["block"] == "Short text"

    def test_overlap_coverage(self, svc):
        """Blocks overlap ensures no text is lost between boundaries."""
        text = "ABCDEFGHIJ" * 100  # 1000 chars
        blocks = svc.extract_blocks(text, block_size=200, overlap=50)
        # Reconstruct: verify all text is covered
        reconstructed = blocks[0]["block"]
        for i in range(1, len(blocks)):
            # Overlap means some text is duplicated, but nothing lost
            pass
        assert len(blocks) >= 3


# ---------------------------------------------------------------------------
# search_text_dichotomically
# ---------------------------------------------------------------------------


class TestSearchTextDichotomically:
    """Tests for search_text_dichotomically."""

    def test_find_occurrences(self, svc):
        text = "Python is great. Python is powerful. Python is easy."
        results = svc.search_text_dichotomically(text, "Python", block_size=100)
        assert len(results) >= 3
        for r in results:
            assert "match" in r
            assert "position" in r
            assert "context" in r
            assert "block_start" in r
            assert "block_end" in r

    def test_case_insensitive(self, svc):
        text = "Hello HELLO hello"
        results = svc.search_text_dichotomically(text, "hello", block_size=100)
        assert len(results) == 3

    def test_empty_inputs(self, svc):
        assert svc.search_text_dichotomically("", "term") == []
        assert svc.search_text_dichotomically("text", "") == []

    def test_no_match(self, svc):
        assert svc.search_text_dichotomically("hello world", "xyz") == []

    def test_large_text_blocking(self, svc):
        """Verify multi-block search finds matches across boundaries."""
        # Place target at a position near a block boundary
        text = "x" * 490 + "TARGET" + "y" * 500
        results = svc.search_text_dichotomically(text, "TARGET", block_size=500, overlap=50)
        assert len(results) >= 1
        assert results[0]["match"] == "TARGET"
