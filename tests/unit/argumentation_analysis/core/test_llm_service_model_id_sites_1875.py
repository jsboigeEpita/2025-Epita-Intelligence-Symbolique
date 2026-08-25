# -*- coding: utf-8 -*-
"""Guards for #1875: no call site freezes ``model_id="gpt-5-mini"``.

The env reader already exists in ``create_llm_service`` (llm_service.py:133:
``os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")``). The defect was call
sites passing the literal, short-circuiting that reader (#1019: a field and
its reader). The fix is subtraction: omit ``model_id`` at each call site so
the environment decides.

Two guards:

1. ``test_no_frozen_model_id_literal_at_call_sites`` — AST-scans every file
   whose call sites were fixed. Re-introducing ``model_id="gpt-5-mini"`` at
   any of them reddens. Each file must still contain at least one
   ``create_llm_service`` call (positive control): a renamed or emptied file
   must not pass by vacuity.
2. ``test_mcp_server_service_id_reflects_env_sentinel`` — with
   ``OPENAI_CHAT_MODEL_ID`` set to a sentinel (not the default), the factory
   call using the exact ``service_id`` of the mcp_server site reflects the
   sentinel. Testing the default would not discriminate: the fallback IS the
   string that was removed.
"""

import ast
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]

#: Files whose live call sites dropped the frozen literal (#1875: 6 sites in
#: the ticket's table + 2 brothers found by the completeness grep —
#: project_core showcase and the validation_point3 demo).
FIXED_SITE_FILES = [
    "argumentation_analysis/services/mcp_server/main.py",
    "argumentation_analysis/ui/extract_editor/extract_marker_editor.py",
    "argumentation_analysis/utils/dev_tools/repair_utils.py",
    "argumentation_analysis/utils/run_verify_extracts_with_llm.py",
    "project_core/rhetorical_analysis_from_scripts/educational_showcase_system.py",
    "scripts/apps/demos/validation_point3_demo_epita_dynamique.py",
]

#: Out of scope by design (ticket #1875): archives and overflow demos are
#: not live code.
EXPECTED_MIN_CALLS_PER_FILE = {
    "argumentation_analysis/services/mcp_server/main.py": 2,
    "argumentation_analysis/ui/extract_editor/extract_marker_editor.py": 2,
    "argumentation_analysis/utils/dev_tools/repair_utils.py": 1,
    "argumentation_analysis/utils/run_verify_extracts_with_llm.py": 1,
    "project_core/rhetorical_analysis_from_scripts/educational_showcase_system.py": 1,
    "scripts/apps/demos/validation_point3_demo_epita_dynamique.py": 1,
}


def _create_llm_service_calls(tree: ast.AST):
    """Yield every ``create_llm_service(...)`` call node in an AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            is_bare_name = (
                isinstance(func, ast.Name) and func.id == "create_llm_service"
            )
            is_attribute = (
                isinstance(func, ast.Attribute) and func.attr == "create_llm_service"
            )
            if is_bare_name or is_attribute:
                yield node


class TestNoFrozenModelIdLiteral:
    def test_no_frozen_model_id_literal_at_call_sites(self):
        for rel_path in FIXED_SITE_FILES:
            source_path = REPO_ROOT / rel_path
            assert (
                source_path.exists()
            ), f"#1875 guard: file disappeared — update the guard list: {rel_path}"
            tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))

            calls = list(_create_llm_service_calls(tree))
            minimum = EXPECTED_MIN_CALLS_PER_FILE[rel_path]
            assert len(calls) >= minimum, (
                f"#1875 guard: expected >= {minimum} create_llm_service call(s) "
                f"in {rel_path}, found {len(calls)} — the file was emptied or "
                f"renamed; the guard list must track it"
            )

            for call in calls:
                for keyword in call.keywords:
                    if keyword.arg == "model_id":
                        value = keyword.value
                        is_frozen = (
                            isinstance(value, ast.Constant)
                            and isinstance(value.value, str)
                            and value.value == "gpt-5-mini"
                        )
                        assert not is_frozen, (
                            f'#1875: {rel_path} freezes model_id="gpt-5-mini" '
                            f"at a call site — the env reader "
                            f"OPENAI_CHAT_MODEL_ID is short-circuited (#1019). "
                            f"Omit model_id and let the environment decide."
                        )


class TestEnvSentinelThroughFactory:
    def test_mcp_server_service_id_reflects_env_sentinel(self):
        """The mcp_server site's factory call reflects OPENAI_CHAT_MODEL_ID.

        Uses the exact ``service_id`` of the (now literal-free) mcp_server
        call sites. The sentinel differs from the default so the test
        discriminates: a re-frozen literal or a broken env reader both fail.
        """
        from argumentation_analysis.core.llm_service import create_llm_service

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "sk-test-sentinel-1875",
                "OPENAI_CHAT_MODEL_ID": "sentinel-model-1875",
            },
        ):
            # The OpenRouter toggle (llm_service.py:159) re-resolves the
            # model from OPENROUTER_CHAT_MODEL_ID when routed; pop it so the
            # OPENAI_CHAT_MODEL_ID path is the one under test, whatever the
            # host machine's .env routes through.
            for openrouter_var in (
                "OPENROUTER_BASE_URL",
                "OPENROUTER_API_KEY",
                "OPENROUTER_CHAT_MODEL_ID",
            ):
                os.environ.pop(openrouter_var, None)
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            with patch("argumentation_analysis.core.llm_service.AsyncOpenAI"):
                with patch(
                    "argumentation_analysis.core.llm_service.OpenAIChatCompletion"
                ) as mock_oai:
                    mock_oai.return_value = MagicMock()
                    create_llm_service("logic_service", force_authentic=True)

        call_kwargs = mock_oai.call_args
        assert call_kwargs[1]["ai_model_id"] == "sentinel-model-1875"
