"""
Robustness tests for unified pipeline workflows against adversarial inputs.

Tests all available workflows against malformed, edge-case, and adversarial
inputs to ensure no unhandled exceptions, no hangs, and graceful degradation.

Categories tested:
1. Empty/whitespace inputs
2. Very short inputs
3. Very long inputs (100K+ chars)
4. Non-French / non-Latin inputs (Chinese, Arabic, emoji-only)
5. Code injection attempts (Python, HTML, SQL)
6. Special characters (null bytes, control chars, mixed encodings)
7. Repetitive inputs (same word x1000)
8. Mixed content (code + natural language + URLs)

Each test verifies:
- No unhandled exceptions (workflow completes or fails gracefully)
- result["summary"] is always present with correct structure
- No hang (asyncio.wait_for with 30s timeout)
"""

import asyncio
import pytest

from argumentation_analysis.orchestration.unified_pipeline import (
    run_unified_analysis,
    setup_registry,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(scope="module")
def shared_registry():
    """Create a single registry for the entire module (no optional deps)."""
    return setup_registry(include_optional=False)


# ============================================================
# Adversarial input definitions
# ============================================================

BASE_WORKFLOWS = ["light", "standard", "full"]

# 1. Empty and whitespace inputs
EMPTY_WHITESPACE_INPUTS = [
    pytest.param("", id="empty_string"),
    pytest.param(" ", id="single_space"),
    pytest.param("   ", id="multiple_spaces"),
    pytest.param("\n\n\n", id="newlines_only"),
    pytest.param("\t", id="tab_only"),
    pytest.param("\t\n \t\n", id="mixed_whitespace"),
    pytest.param("\r\n\r\n", id="crlf_whitespace"),
]

# 2. Very short inputs
VERY_SHORT_INPUTS = [
    pytest.param("a", id="single_char"),
    pytest.param("Oui.", id="single_word_fr"),
    pytest.param("Non.", id="single_word_non"),
    pytest.param("42", id="number_only"),
    pytest.param(".", id="dot_only"),
    pytest.param("?!", id="punctuation_only"),
]

# 3. Very long inputs
VERY_LONG_INPUTS = [
    pytest.param("Lorem ipsum dolor sit amet. " * 10000, id="100k_chars_lorem"),
    pytest.param("A" * 100000, id="100k_single_char"),
    pytest.param(("Ceci est un argument. " * 5000), id="100k_french_repeated"),
]

# 4. Non-French / non-Latin inputs
NON_FRENCH_INPUTS = [
    pytest.param(
        "\u8fd9\u662f\u4e00\u4e2a\u8bba\u70b9\u3002\u6211\u4eec\u5e94\u8be5\u8003\u8651\u6240\u6709\u56e0\u7d20\u3002",
        id="chinese_text",
    ),
    pytest.param(
        "\u0647\u0630\u0627 \u0627\u0631\u063a\u0645\u0646\u062a. \u064a\u062c\u0628 \u0623\u0646 \u0646\u0646\u0638\u0631 \u0641\u064a \u062c\u0645\u064a\u0639 \u0627\u0644\u0639\u0648\u0627\u0645\u0644.",
        id="arabic_text",
    ),
    pytest.param(
        "\ud83d\ude80\ud83d\udd25\ud83d\udca1\ud83c\udf0d\ud83d\udcca\ud83e\udd14\ud83d\udca3\u2728\ud83c\udfaf\ud83d\udcaf",
        id="emoji_only",
    ),
    pytest.param(
        "\u3053\u308c\u306f\u8b70\u8ad6\u3067\u3059\u3002\u3059\u3079\u3066\u306e\u5074\u9762\u3092\u8003\u616e\u3059\u308b\u5fc5\u8981\u304c\u3042\u308a\u307e\u3059\u3002",
        id="japanese_text",
    ),
    pytest.param(
        "\u042d\u0442\u043e \u0430\u0440\u0433\u0443\u043c\u0435\u043d\u0442. \u041c\u044b \u0434\u043e\u043b\u0436\u043d\u044b \u0440\u0430\u0441\u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c \u0432\u0441\u0435 \u0444\u0430\u043a\u0442\u043e\u0440\u044b.",
        id="russian_text",
    ),
    pytest.param(
        "\ud55c\uad6d\uc5b4 \ud14d\uc2a4\ud2b8\uc785\ub2c8\ub2e4. \ubaa8\ub4e0 \uc694\uc18c\ub97c \uace0\ub824\ud574\uc57c \ud569\ub2c8\ub2e4.",
        id="korean_text",
    ),
]

# 5. Code injection attempts
CODE_INJECTION_INPUTS = [
    pytest.param(
        'import os; os.system("rm -rf /")',
        id="python_injection",
    ),
    pytest.param(
        "__import__('subprocess').call(['ls', '-la'])",
        id="python_dunder_import",
    ),
    pytest.param(
        '<script>alert("XSS")</script><img src=x onerror=alert(1)>',
        id="html_xss_injection",
    ),
    pytest.param(
        "'; DROP TABLE users; --",
        id="sql_injection",
    ),
    pytest.param(
        '{"__class__": {"__reduce__": ["os.system", ["echo pwned"]]}}',
        id="json_deserialization_attack",
    ),
    pytest.param(
        "${7*7}{{7*7}}#{7*7}<%= 7*7 %>",
        id="template_injection",
    ),
    pytest.param(
        "eval(compile('print(1)','<string>','exec'))",
        id="python_eval_injection",
    ),
]

# 6. Special characters
SPECIAL_CHAR_INPUTS = [
    pytest.param(
        "Text with \x00 null byte inside.",
        id="null_byte_embedded",
    ),
    pytest.param(
        "\x00\x01\x02\x03\x04\x05\x06\x07",
        id="control_chars_only",
    ),
    pytest.param(
        "Normal text \x0b\x0c\x0e\x0f more text",
        id="mixed_control_chars",
    ),
    pytest.param(
        "caf\xc3\xa9 na\xc3\xafve r\xc3\xa9sum\xc3\xa9",
        id="utf8_encoded_bytes_as_str",
    ),
    pytest.param(
        "\ufffd\ufffd\ufffd replacement chars \ufffd\ufffd",
        id="unicode_replacement_chars",
    ),
    pytest.param(
        "text\u200b\u200b\u200bwith\u200bzero\u200bwidth\u200bspaces",
        id="zero_width_spaces",
    ),
    pytest.param(
        "\u202e\u0052\u0069\u0067\u0068\u0074\u002d\u0074\u006f\u002d\u006c\u0065\u0066\u0074\u0020\u006f\u0076\u0065\u0072\u0072\u0069\u0064\u0065",
        id="rtl_override_bidi",
    ),
    pytest.param(
        "a\u0300\u0301\u0302\u0303\u0304\u0305\u0306\u0307\u0308\u0309\u030a\u030b\u030c\u030d\u030e\u030f",
        id="combining_diacriticals_zalgo",
    ),
]

# 7. Repetitive inputs
REPETITIVE_INPUTS = [
    pytest.param(
        "argument " * 1000,
        id="same_word_1000x",
    ),
    pytest.param(
        "oui non " * 500,
        id="alternating_words_1000",
    ),
    pytest.param(
        "!@#$%^&*() " * 200,
        id="repeated_symbols",
    ),
    pytest.param(
        "Ceci est un sophisme. " * 500,
        id="repeated_sentence_fr",
    ),
]

# 8. Mixed content
MIXED_CONTENT_INPUTS = [
    pytest.param(
        "Check https://example.com/api?q=test&limit=10 for details. "
        "def foo(): return 42\n"
        "L'argument est valide car <b>logiquement coherent</b>.",
        id="url_code_french_html",
    ),
    pytest.param(
        "SELECT * FROM args WHERE id=1;\n"
        "This is a valid philosophical argument about ethics.\n"
        "```python\nprint('hello world')\n```\n"
        "Visit http://localhost:8080/api/v1/analyze",
        id="sql_english_code_url",
    ),
    pytest.param(
        "{ \"key\": \"value\", \"nested\": { \"arr\": [1,2,3] } }\n"
        "The above JSON represents the argument structure.\n"
        "\u8fd9\u662f\u4e2d\u6587\u3002 This is English. C'est du francais.",
        id="json_multilingual",
    ),
    pytest.param(
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==\n"
        "file:///etc/passwd\n"
        "\\\\server\\share\\path\n"
        "Argument: donc il faut conclure que...",
        id="data_uri_file_path_unc",
    ),
]

# Combine all adversarial inputs for a mega-parametrize
ALL_ADVERSARIAL_INPUTS = (
    EMPTY_WHITESPACE_INPUTS
    + VERY_SHORT_INPUTS
    + VERY_LONG_INPUTS
    + NON_FRENCH_INPUTS
    + CODE_INJECTION_INPUTS
    + SPECIAL_CHAR_INPUTS
    + REPETITIVE_INPUTS
    + MIXED_CONTENT_INPUTS
)


# ============================================================
# Helper: validate result structure
# ============================================================


def assert_valid_result(result, workflow_name):
    """Assert that a workflow result has the expected structure."""
    assert result is not None, f"Result is None for workflow '{workflow_name}'"
    assert "summary" in result, (
        f"Missing 'summary' key in result for workflow '{workflow_name}'"
    )
    summary = result["summary"]
    assert "completed" in summary, "Missing 'completed' in summary"
    assert "failed" in summary, "Missing 'failed' in summary"
    assert "skipped" in summary, "Missing 'skipped' in summary"
    assert "total" in summary, "Missing 'total' in summary"
    assert isinstance(summary["completed"], int)
    assert isinstance(summary["failed"], int)
    assert isinstance(summary["skipped"], int)
    assert isinstance(summary["total"], int)
    assert summary["total"] == (
        summary["completed"] + summary["failed"] + summary["skipped"]
    ), (
        f"Total mismatch: {summary['total']} != "
        f"{summary['completed']} + {summary['failed']} + {summary['skipped']}"
    )
    assert "phases" in result, "Missing 'phases' key in result"
    assert "workflow_name" in result, "Missing 'workflow_name' key in result"


# ============================================================
# Test classes by adversarial input category
# ============================================================


@pytest.mark.robustness
class TestEmptyWhitespaceInputs:
    """Test workflows with empty and whitespace-only inputs."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_input", EMPTY_WHITESPACE_INPUTS)
    @pytest.mark.parametrize("workflow_name", BASE_WORKFLOWS)
    async def test_empty_whitespace(self, text_input, workflow_name, shared_registry):
        """Workflow handles empty/whitespace input without crash or hang."""
        result = await asyncio.wait_for(
            run_unified_analysis(
                text_input,
                workflow_name=workflow_name,
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, workflow_name)


@pytest.mark.robustness
class TestVeryShortInputs:
    """Test workflows with very short inputs (1-4 chars)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_input", VERY_SHORT_INPUTS)
    @pytest.mark.parametrize("workflow_name", BASE_WORKFLOWS)
    async def test_very_short(self, text_input, workflow_name, shared_registry):
        """Workflow handles very short input without crash or hang."""
        result = await asyncio.wait_for(
            run_unified_analysis(
                text_input,
                workflow_name=workflow_name,
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, workflow_name)


@pytest.mark.robustness
class TestVeryLongInputs:
    """Test workflows with very long inputs (100K+ chars)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_input", VERY_LONG_INPUTS)
    @pytest.mark.parametrize("workflow_name", BASE_WORKFLOWS)
    async def test_very_long(self, text_input, workflow_name, shared_registry):
        """Workflow handles very long input without crash or hang."""
        result = await asyncio.wait_for(
            run_unified_analysis(
                text_input,
                workflow_name=workflow_name,
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, workflow_name)


@pytest.mark.robustness
class TestNonFrenchInputs:
    """Test workflows with non-French and non-Latin text."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_input", NON_FRENCH_INPUTS)
    @pytest.mark.parametrize("workflow_name", BASE_WORKFLOWS)
    async def test_non_french(self, text_input, workflow_name, shared_registry):
        """Workflow handles non-French/non-Latin input without crash or hang."""
        result = await asyncio.wait_for(
            run_unified_analysis(
                text_input,
                workflow_name=workflow_name,
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, workflow_name)


@pytest.mark.robustness
class TestCodeInjectionInputs:
    """Test workflows with code injection attempts."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_input", CODE_INJECTION_INPUTS)
    @pytest.mark.parametrize("workflow_name", BASE_WORKFLOWS)
    async def test_code_injection(self, text_input, workflow_name, shared_registry):
        """Workflow handles code injection input without crash, hang, or execution."""
        result = await asyncio.wait_for(
            run_unified_analysis(
                text_input,
                workflow_name=workflow_name,
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, workflow_name)


@pytest.mark.robustness
class TestSpecialCharInputs:
    """Test workflows with special characters (null bytes, control chars, etc.)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_input", SPECIAL_CHAR_INPUTS)
    @pytest.mark.parametrize("workflow_name", BASE_WORKFLOWS)
    async def test_special_chars(self, text_input, workflow_name, shared_registry):
        """Workflow handles special characters without crash or hang."""
        result = await asyncio.wait_for(
            run_unified_analysis(
                text_input,
                workflow_name=workflow_name,
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, workflow_name)


@pytest.mark.robustness
class TestRepetitiveInputs:
    """Test workflows with highly repetitive inputs."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_input", REPETITIVE_INPUTS)
    @pytest.mark.parametrize("workflow_name", BASE_WORKFLOWS)
    async def test_repetitive(self, text_input, workflow_name, shared_registry):
        """Workflow handles repetitive input without crash or hang."""
        result = await asyncio.wait_for(
            run_unified_analysis(
                text_input,
                workflow_name=workflow_name,
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, workflow_name)


@pytest.mark.robustness
class TestMixedContentInputs:
    """Test workflows with mixed content (code + language + URLs)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_input", MIXED_CONTENT_INPUTS)
    @pytest.mark.parametrize("workflow_name", BASE_WORKFLOWS)
    async def test_mixed_content(self, text_input, workflow_name, shared_registry):
        """Workflow handles mixed content without crash or hang."""
        result = await asyncio.wait_for(
            run_unified_analysis(
                text_input,
                workflow_name=workflow_name,
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, workflow_name)


# ============================================================
# Cross-workflow robustness: all inputs x all available workflows
# ============================================================


# Extended workflow list - includes all catalog workflows that may be available
EXTENDED_WORKFLOWS = [
    "light",
    "standard",
    "full",
    "quality_gated",
    "debate_governance",
    "jtms_dung",
    "neural_symbolic",
    "hierarchical_fallacy",
    "democratech",
    "debate_tournament",
    "fact_check",
    "formal_debate",
    "formal_verification",
]


@pytest.mark.robustness
class TestAllWorkflowsEmptyInput:
    """Test all available workflows with empty input."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("workflow_name", EXTENDED_WORKFLOWS)
    async def test_empty_string_all_workflows(self, workflow_name, shared_registry):
        """Every available workflow handles empty string gracefully."""
        try:
            result = await asyncio.wait_for(
                run_unified_analysis(
                    "",
                    workflow_name=workflow_name,
                    registry=shared_registry,
                    create_state=True,
                ),
                timeout=30.0,
            )
            assert_valid_result(result, workflow_name)
        except ValueError as e:
            # Acceptable: workflow may not be in catalog
            assert "Unknown workflow" in str(e)


@pytest.mark.robustness
class TestAllWorkflowsAdversarialSample:
    """Test all available workflows with a representative adversarial sample."""

    REPRESENTATIVE_INPUTS = [
        pytest.param("", id="empty"),
        pytest.param("a", id="minimal"),
        pytest.param("A" * 50000, id="long_50k"),
        pytest.param(
            "\ud83d\ude80\ud83d\udd25\ud83d\udca1",
            id="emoji",
        ),
        pytest.param(
            '<script>alert("XSS")</script>',
            id="xss",
        ),
        pytest.param(
            "Text with \x00 null",
            id="null_byte",
        ),
        pytest.param(
            "mot " * 500,
            id="repetitive",
        ),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text_input", REPRESENTATIVE_INPUTS)
    @pytest.mark.parametrize("workflow_name", EXTENDED_WORKFLOWS)
    async def test_adversarial_all_workflows(
        self, text_input, workflow_name, shared_registry
    ):
        """Each workflow handles a representative adversarial input."""
        try:
            result = await asyncio.wait_for(
                run_unified_analysis(
                    text_input,
                    workflow_name=workflow_name,
                    registry=shared_registry,
                    create_state=True,
                ),
                timeout=30.0,
            )
            assert_valid_result(result, workflow_name)
        except ValueError as e:
            # Acceptable: workflow may not be in catalog
            assert "Unknown workflow" in str(e)


# ============================================================
# State integrity under adversarial inputs
# ============================================================


@pytest.mark.robustness
class TestStateIntegrityAdversarial:
    """Verify UnifiedAnalysisState remains consistent after adversarial inputs."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "text_input",
        [
            pytest.param("", id="empty"),
            pytest.param("\x00\x01\x02", id="control_chars"),
            pytest.param("A" * 100000, id="100k_chars"),
            pytest.param(
                "\ud83d\ude80" * 1000,
                id="1k_emoji",
            ),
            pytest.param(
                "'; DROP TABLE users; --",
                id="sql_injection",
            ),
        ],
    )
    async def test_state_snapshot_valid(self, text_input, shared_registry):
        """State snapshot is valid dict after adversarial input on light workflow."""
        result = await asyncio.wait_for(
            run_unified_analysis(
                text_input,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")
        # State should be present and snapshot should be a dict
        if "unified_state" in result:
            assert result["unified_state"] is not None
        if "state_snapshot" in result:
            assert result["state_snapshot"] is None or isinstance(
                result["state_snapshot"], dict
            )

    @pytest.mark.asyncio
    async def test_state_not_corrupted_by_null_bytes(self, shared_registry):
        """State remains usable after processing null-byte input."""
        text = "Valid start.\x00Hidden\x00text.\x00End."
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")
        state = result.get("unified_state")
        if state is not None:
            # State should still be queryable
            snapshot = state.get_state_snapshot(summarize=True)
            assert isinstance(snapshot, dict)

    @pytest.mark.asyncio
    async def test_state_not_corrupted_by_massive_input(self, shared_registry):
        """State remains usable after processing massive input."""
        text = "Ceci est un long argument. " * 10000
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")
        state = result.get("unified_state")
        if state is not None:
            snapshot = state.get_state_snapshot(summarize=True)
            assert isinstance(snapshot, dict)


# ============================================================
# Boundary and edge-case specific tests
# ============================================================


@pytest.mark.robustness
class TestBoundaryEdgeCases:
    """Edge cases that don't fit neatly into the parametrized categories."""

    @pytest.mark.asyncio
    async def test_none_like_strings(self, shared_registry):
        """Strings that look like None/null values are handled."""
        for text in ["None", "null", "undefined", "NaN", "false", "0"]:
            result = await asyncio.wait_for(
                run_unified_analysis(
                    text,
                    workflow_name="light",
                    registry=shared_registry,
                    create_state=True,
                ),
                timeout=30.0,
            )
            assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_only_newlines_between_sentences(self, shared_registry):
        """Text with only newlines as separators (no periods)."""
        text = "Premier argument\nDeuxieme argument\nTroisieme argument"
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_extremely_long_single_word(self, shared_registry):
        """A single word with 50K characters."""
        text = "supercalifragilistic" * 2500  # ~50K chars, no spaces
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_all_punctuation(self, shared_registry):
        """Input consisting entirely of punctuation."""
        text = "!@#$%^&*()_+-=[]{}|;':\",./<>?" * 50
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_backslash_heavy_input(self, shared_registry):
        """Input with many backslashes (path-like, escape-like)."""
        text = "C:\\Users\\admin\\Documents\\secret.txt\n\\n\\t\\r\\0\\\\"
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_deeply_nested_brackets(self, shared_registry):
        """Input with deeply nested brackets/parens."""
        depth = 200
        text = "(" * depth + "argument" + ")" * depth
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_format_string_attack(self, shared_registry):
        """Input containing Python format string placeholders."""
        text = "This has {0} and {key} and %s and %d and %(name)s placeholders."
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_regex_bomb_input(self, shared_registry):
        """Input that could cause regex catastrophic backtracking."""
        # Classic ReDoS pattern: many 'a's followed by something that won't match
        text = "a" * 100 + "!"
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_unicode_surrogates_safe(self, shared_registry):
        """Input with high Unicode codepoints (beyond BMP)."""
        # Mathematical symbols, musical symbols, etc.
        text = "\U0001D49E \U0001D4B6 \U0001D4C1 \U0001F3B5 \U0001F3B6 This is an argument."
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="light",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_mixed_line_endings(self, shared_registry):
        """Input with mixed line endings (LF, CR, CRLF)."""
        text = "Line one.\nLine two.\rLine three.\r\nLine four."
        result = await asyncio.wait_for(
            run_unified_analysis(
                text,
                workflow_name="standard",
                registry=shared_registry,
                create_state=True,
            ),
            timeout=30.0,
        )
        assert_valid_result(result, "standard")


# ============================================================
# Concurrent execution robustness
# ============================================================


@pytest.mark.robustness
class TestConcurrentAdversarialExecution:
    """Test that multiple adversarial inputs can be processed concurrently."""

    @pytest.mark.asyncio
    async def test_concurrent_mixed_inputs(self, shared_registry):
        """Multiple adversarial inputs run concurrently without interference."""
        inputs = [
            "",
            "a",
            "Normal argument text about philosophy.",
            "\x00\x01\x02",
            "A" * 10000,
            "\ud83d\ude80\ud83d\udd25\ud83d\udca1",
            '<script>alert("XSS")</script>',
            "mot " * 200,
        ]
        tasks = [
            asyncio.wait_for(
                run_unified_analysis(
                    text,
                    workflow_name="light",
                    registry=shared_registry,
                    create_state=True,
                ),
                timeout=30.0,
            )
            for text in inputs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Timeout or other error - should not happen but don't crash test
                pytest.fail(
                    f"Concurrent task {i} raised {type(result).__name__}: {result}"
                )
            else:
                assert_valid_result(result, "light")

    @pytest.mark.asyncio
    async def test_concurrent_different_workflows(self, shared_registry):
        """Different workflows process the same adversarial input concurrently."""
        text = '<script>alert(1)</script> Cet argument est un sophisme \x00 ad hominem.'
        tasks = [
            asyncio.wait_for(
                run_unified_analysis(
                    text,
                    workflow_name=wf,
                    registry=shared_registry,
                    create_state=True,
                ),
                timeout=30.0,
            )
            for wf in BASE_WORKFLOWS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(
                    f"Workflow {BASE_WORKFLOWS[i]} raised "
                    f"{type(result).__name__}: {result}"
                )
            else:
                assert_valid_result(result, BASE_WORKFLOWS[i])
