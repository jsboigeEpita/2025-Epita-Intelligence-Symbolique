"""#2346 — two HTML reports print dataset and verifier strings without escaping.

``generate_verification_report`` (``utils/dev_tools/verification_utils.py``,
reached by ``scripts/orchestration/run_verify_extracts.py``) and the corpus-info
HTML formatter of ``scripts/utils/unified_utilities.py`` interpolated source
names, extract names, statuses and messages straight into the page. A ``<`` or
``&`` in any of them broke or rewrote it, and a quote in the status closed the
row's ``class`` attribute. The two sibling reports of
``utils/extract_repair/`` were repaired in #2594; these are the rest of the
class.

Synthetic values only: no dataset content.
"""

import importlib.util
from pathlib import Path

from argumentation_analysis.utils.dev_tools.verification_utils import (
    generate_verification_report,
)

REPO = Path(__file__).resolve().parents[3]

HOSTILE = '<img src=x onerror="alert(1)">'


def _unified_utilities():
    # ``scripts/`` is not a package: load the module from its path.
    path = REPO / "scripts" / "utils" / "unified_utilities.py"
    spec = importlib.util.spec_from_file_location("unified_utilities_2346", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verification_page(tmp_path, **result):
    out = tmp_path / "verification.html"
    generate_verification_report([result], str(out))
    return out.read_text(encoding="utf-8")


def test_the_verification_report_escapes_names_and_message(tmp_path):
    page = _verification_page(
        tmp_path,
        source_name=HOSTILE,
        extract_name="A & B",
        status="invalid",
        message="marker '<' not found",
        start_found=False,
        end_found=False,
    )
    assert HOSTILE not in page
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in page
    assert "A &amp; B" in page
    assert "marker &#x27;&lt;&#x27; not found" in page


def test_the_verification_report_status_cannot_close_its_attribute(tmp_path):
    page = _verification_page(
        tmp_path, source_name="s", extract_name="e", status='x" onclick="y'
    )
    assert 'class="x" onclick="y"' not in page
    assert 'class="x&quot; onclick=&quot;y"' in page


def test_a_source_that_failed_to_load_names_its_url_intact(tmp_path):
    # The verifier's own message for an unloadable source quotes its URL, and
    # a query string carries ``&``.
    page = _verification_page(
        tmp_path,
        source_name="s",
        extract_name="e",
        status="error",
        message="Impossible de charger le texte source: https://h/p?a=1&b=2",
    )
    assert "https://h/p?a=1&amp;b=2" in page
    assert "a=1&b=2" not in page


def test_a_plain_report_is_unchanged(tmp_path):
    # Counter-pendulum: markup the report writes itself stays markup.
    page = _verification_page(
        tmp_path,
        source_name="Source 1",
        extract_name="Extract 1",
        status="valid",
        message="ok",
        extracted_length=42,
    )
    assert '<tr class="valid"><td>Source 1</td><td>Extract 1</td>' in page
    assert "<strong>Longueur de l'extrait:</strong> 42 caractères" in page


def test_the_corpus_info_page_escapes_source_fields():
    uu = _unified_utilities()
    info = uu.CorpusInfo(
        total_sources=1,
        total_extracts=2,
        total_content_length=10,
        file_size_bytes=20,
        last_modified="<now>",
        encryption_status="encrypted",
        sources_summary=[
            {
                "index": 0,
                "name": HOSTILE,
                "type": "a&b",
                "extract_count": 2,
                "content_length": 1234,
            }
        ],
    )
    page = uu.UnifiedUtilityFormatter._format_corpus_info_html(info)
    assert HOSTILE not in page
    assert "<td>&lt;img src=x onerror=&quot;alert(1)&quot;&gt;</td>" in page
    assert "<td>a&amp;b</td>" in page
    assert "<now>" not in page
    assert "<td>1,234 caractères</td>" in page
