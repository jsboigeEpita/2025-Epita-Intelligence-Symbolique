# -*- coding: utf-8 -*-
"""
Unit tests for FallacyWorkflowPlugin — hierarchical taxonomy-guided fallacy detection.

Tests cover:
- Construction with/without taxonomy
- Slave kernel creation (constrained tools)
- One-shot fallback mode
- Iterative deepening with double-selection
- Parallel branch exploration
- Error handling and fallbacks
- ExplorationPlugin functions
- IdentifiedFallacy model
"""

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.plugins.fallacy_workflow_plugin import (
    FallacyWorkflowPlugin,
)
from argumentation_analysis.plugins.exploration_plugin import ExplorationPlugin
from argumentation_analysis.plugins.identification_models import (
    IdentifiedFallacy,
    FallacyAnalysisResult,
)
from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator

# ---------------------------------------------------------------------------
# Sample taxonomy data for testing
# ---------------------------------------------------------------------------

SAMPLE_TAXONOMY = [
    {
        "PK": "0",
        "path": "0",
        "depth": "0",
        "text_fr": "Argument fallacieux",
        "text_en": "Fallacy",
        "desc_fr": "Votre discours vise à tromper",
        "desc_en": "Your argument depends on unjustified claims",
        "example_fr": "Tout ce qui rare est cher.",
        "example_en": "Everything rare is expensive.",
        "nom_vulgarisé": "Argument fallacieux",
    },
    {
        "PK": "1",
        "path": "1",
        "depth": "1",
        "text_fr": "Insuffisance",
        "text_en": "Insufficiency",
        "desc_fr": "Les arguments ne suffisent pas",
        "desc_en": "Arguments fail to provide adequate support",
        "example_fr": "",
        "example_en": "",
        "nom_vulgarisé": "Insuffisance",
    },
    {
        "PK": "2",
        "path": "1.1",
        "depth": "2",
        "text_fr": "Argument bâclé",
        "text_en": "Sloppy argument",
        "desc_fr": "Basé sur des impressions ou anecdotes",
        "desc_en": "Based on anecdotes without solid evidence",
        "example_fr": "Hier j'ai marché dans une crotte",
        "example_en": "Yesterday I stepped in dog poo",
        "nom_vulgarisé": "Argument bâclé",
    },
    {
        "PK": "3",
        "path": "1.1.1",
        "depth": "3",
        "text_fr": "Argument vide",
        "text_en": "Hollow argument",
        "desc_fr": "Affirmations sans poids argumentatif",
        "desc_en": "Assertions without argumentative weight",
        "example_fr": "L'avenir est incertain",
        "example_en": "Our future is uncertain",
        "nom_vulgarisé": "Argument vide",
    },
    {
        "PK": "4",
        "path": "1.1.2",
        "depth": "3",
        "text_fr": "Généralisation hâtive",
        "text_en": "Hasty generalization",
        "desc_fr": "Conclusion générale à partir d'un cas isolé",
        "desc_en": "General conclusion from limited cases",
        "example_fr": "Tous les politiciens sont corrompus",
        "example_en": "All politicians are corrupt",
        "nom_vulgarisé": "Généralisation hâtive",
    },
    {
        "PK": "10",
        "path": "2",
        "depth": "1",
        "text_fr": "Hors sujet",
        "text_en": "Irrelevance",
        "desc_fr": "Arguments sans rapport avec la conclusion",
        "desc_en": "Arguments unrelated to the conclusion",
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
        "desc_fr": "Attaque la personne plutôt que l'argument",
        "desc_en": "Attacks the person rather than the argument",
        "example_fr": "Tu es stupide donc tu as tort",
        "example_en": "You are stupid so you are wrong",
        "nom_vulgarisé": "Ad Hominem",
    },
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_kernel():
    kernel = MagicMock()
    kernel.add_service = MagicMock()
    kernel.add_plugin = MagicMock()
    kernel.plugins = MagicMock()
    return kernel


@pytest.fixture
def mock_llm_service():
    service = AsyncMock()
    service.get_chat_message_content = AsyncMock()
    service.get_chat_message_contents = AsyncMock()
    return service


@pytest.fixture
def taxonomy_nav():
    return TaxonomyNavigator(taxonomy_data=SAMPLE_TAXONOMY)


@pytest.fixture
def plugin(mock_kernel, mock_llm_service):
    """Plugin with sample taxonomy data (no file needed)."""
    return FallacyWorkflowPlugin(
        master_kernel=mock_kernel,
        llm_service=mock_llm_service,
        taxonomy_data=SAMPLE_TAXONOMY,
    )


@pytest.fixture
def empty_plugin(mock_kernel, mock_llm_service):
    """Plugin with no taxonomy data."""
    return FallacyWorkflowPlugin(
        master_kernel=mock_kernel,
        llm_service=mock_llm_service,
    )


# ---------------------------------------------------------------------------
# 1. Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_basic_construction(self, mock_kernel, mock_llm_service):
        plugin = FallacyWorkflowPlugin(
            master_kernel=mock_kernel,
            llm_service=mock_llm_service,
        )
        assert plugin.master_kernel is mock_kernel
        assert plugin.llm_service is mock_llm_service
        assert plugin.language == "fr"
        assert plugin.taxonomy_navigator is not None
        assert plugin.exploration_plugin is not None

    def test_construction_with_taxonomy_data(self, plugin):
        roots = plugin.taxonomy_navigator.get_root_nodes()
        assert len(roots) == 2  # Insuffisance + Hors sujet
        assert roots[0]["PK"] == "1"
        assert roots[1]["PK"] == "10"

    def test_construction_with_taxonomy_file(
        self, mock_kernel, mock_llm_service, tmp_path
    ):
        csv_file = tmp_path / "taxonomy.csv"
        csv_file.write_text(
            "PK,path,depth,name\n1,root,1,Root Fallacy\n",
            encoding="utf-8",
        )
        plugin = FallacyWorkflowPlugin(
            master_kernel=mock_kernel,
            llm_service=mock_llm_service,
            taxonomy_file_path=str(csv_file),
        )
        roots = plugin.taxonomy_navigator.get_root_nodes()
        assert len(roots) == 1
        assert roots[0]["name"] == "Root Fallacy"

    def test_construction_with_custom_logger(self, mock_kernel, mock_llm_service):
        custom_logger = logging.getLogger("test.custom")
        plugin = FallacyWorkflowPlugin(
            master_kernel=mock_kernel,
            llm_service=mock_llm_service,
            logger=custom_logger,
        )
        assert plugin.logger is custom_logger

    def test_construction_without_taxonomy_has_empty_navigator(self, empty_plugin):
        roots = empty_plugin.taxonomy_navigator.get_root_nodes()
        assert roots == []

    def test_exploration_plugin_shares_navigator(self, plugin):
        assert plugin.exploration_plugin.taxonomy_navigator is plugin.taxonomy_navigator


# ---------------------------------------------------------------------------
# 2. Bad taxonomy path
# ---------------------------------------------------------------------------


class TestBadTaxonomyPath:
    def test_file_not_found_logged(self, mock_kernel, mock_llm_service, caplog):
        with caplog.at_level(logging.ERROR):
            plugin = FallacyWorkflowPlugin(
                master_kernel=mock_kernel,
                llm_service=mock_llm_service,
                taxonomy_file_path="/nonexistent/path/taxonomy.csv",
            )
        assert plugin.taxonomy_navigator is not None
        assert any("not found" in r.message.lower() for r in caplog.records)

    def test_plugin_works_after_bad_path(self, mock_kernel, mock_llm_service):
        plugin = FallacyWorkflowPlugin(
            master_kernel=mock_kernel,
            llm_service=mock_llm_service,
            taxonomy_file_path="/nonexistent/taxonomy.csv",
        )
        assert plugin.taxonomy_navigator.get_root_nodes() == []


# ---------------------------------------------------------------------------
# 3. Kernel creation
# ---------------------------------------------------------------------------


class TestKernelCreation:
    def test_one_shot_kernel_returns_tuple(self, plugin):
        result = plugin._create_one_shot_kernel()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_slave_kernel_returns_tuple(self, plugin):
        result = plugin._create_slave_kernel()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch(
        "argumentation_analysis.plugins.fallacy_workflow_plugin.Kernel",
        return_value=MagicMock(),
    )
    def test_slave_kernel_has_exploration_plugin(self, mock_kernel_cls, plugin):
        kernel, settings = plugin._create_slave_kernel()
        mock_kernel_cls.return_value.add_plugin.assert_called_once()
        call_args = mock_kernel_cls.return_value.add_plugin.call_args
        assert call_args[0][0] is plugin.exploration_plugin
        assert call_args[0][1] == "Exploration"

    @patch(
        "argumentation_analysis.plugins.fallacy_workflow_plugin.Kernel",
        return_value=MagicMock(),
    )
    def test_one_shot_settings_has_none_invoke(self, mock_kernel_cls, plugin):
        from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings

        _kernel, settings = plugin._create_one_shot_kernel()
        assert isinstance(settings, OpenAIPromptExecutionSettings)
        assert settings.function_choice_behavior is not None
        assert settings.function_choice_behavior.maximum_auto_invoke_attempts == 0

    @patch(
        "argumentation_analysis.plugins.fallacy_workflow_plugin.Kernel",
        return_value=MagicMock(),
    )
    def test_slave_settings_has_auto_no_invoke(self, mock_kernel_cls, plugin):
        from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings

        _kernel, settings = plugin._create_slave_kernel()
        assert isinstance(settings, OpenAIPromptExecutionSettings)
        # Auto with auto_invoke=False means the workflow controls execution
        assert settings.function_choice_behavior is not None


# ---------------------------------------------------------------------------
# 4. Root presentation
# ---------------------------------------------------------------------------


class TestRootPresentation:
    def test_includes_root_categories(self, plugin):
        presentation = plugin._build_root_presentation()
        assert "Insuffisance" in presentation
        assert "Hors sujet" in presentation

    def test_includes_children_of_roots(self, plugin):
        presentation = plugin._build_root_presentation()
        # Children of Insuffisance
        assert "Argument bâclé" in presentation
        # Children of Hors sujet
        assert "Ad Hominem" in presentation

    def test_includes_ids(self, plugin):
        presentation = plugin._build_root_presentation()
        assert "ID: 1" in presentation
        assert "ID: 10" in presentation

    def test_empty_taxonomy_returns_empty(self, empty_plugin):
        presentation = empty_plugin._build_root_presentation()
        assert presentation == ""


# ---------------------------------------------------------------------------
# 5. ExplorationPlugin unit tests
# ---------------------------------------------------------------------------


class TestExplorationPlugin:
    def test_explore_branch_returns_node_info(self, taxonomy_nav):
        plugin = ExplorationPlugin(taxonomy_nav)
        result = json.loads(plugin.explore_branch(node_pk="1"))
        assert result["node"]["pk"] == "1"
        assert result["node"]["name"] == "Insuffisance"
        assert result["children_count"] == 1  # Argument bâclé

    def test_explore_branch_shows_children(self, taxonomy_nav):
        plugin = ExplorationPlugin(taxonomy_nav)
        result = json.loads(plugin.explore_branch(node_pk="2"))
        assert result["children_count"] == 2  # Argument vide + Généralisation hâtive
        child_pks = [c["pk"] for c in result["children"]]
        assert "3" in child_pks
        assert "4" in child_pks

    def test_explore_branch_leaf_node(self, taxonomy_nav):
        plugin = ExplorationPlugin(taxonomy_nav)
        result = json.loads(plugin.explore_branch(node_pk="3"))
        assert result["node"]["is_leaf"] is True
        assert result["children_count"] == 0

    def test_explore_branch_unknown_node(self, taxonomy_nav):
        plugin = ExplorationPlugin(taxonomy_nav)
        result = json.loads(plugin.explore_branch(node_pk="999"))
        assert "error" in result

    def test_confirm_fallacy(self, taxonomy_nav):
        plugin = ExplorationPlugin(taxonomy_nav)
        result = json.loads(
            plugin.confirm_fallacy(
                node_pk="11",
                confidence="high",
                justification="Text attacks the person",
            )
        )
        assert result["confirmed"] is True
        assert result["pk"] == "11"
        assert result["confidence"] == 0.9
        assert "attacks" in result["justification"]

    def test_confirm_fallacy_medium_confidence(self, taxonomy_nav):
        plugin = ExplorationPlugin(taxonomy_nav)
        result = json.loads(plugin.confirm_fallacy(node_pk="3", confidence="medium"))
        assert result["confidence"] == 0.7

    def test_confirm_fallacy_unknown_node(self, taxonomy_nav):
        plugin = ExplorationPlugin(taxonomy_nav)
        result = json.loads(plugin.confirm_fallacy(node_pk="999"))
        assert "error" in result

    def test_conclude_no_fallacy(self, taxonomy_nav):
        plugin = ExplorationPlugin(taxonomy_nav)
        result = json.loads(plugin.conclude_no_fallacy(reason="No match found"))
        assert result["confirmed"] is False
        assert "No match" in result["reason"]


# ---------------------------------------------------------------------------
# 6. IdentifiedFallacy model
# ---------------------------------------------------------------------------


class TestIdentifiedFallacyModel:
    def test_basic_creation(self):
        f = IdentifiedFallacy(
            fallacy_type="Ad Hominem",
            taxonomy_pk="11",
            explanation="Attacks the person",
        )
        assert f.fallacy_type == "Ad Hominem"
        assert f.confidence == 0.0
        assert f.navigation_trace == []

    def test_with_all_fields(self):
        f = IdentifiedFallacy(
            fallacy_type="Argument vide",
            taxonomy_pk="3",
            taxonomy_path="1.1.1",
            explanation="Empty claims",
            problematic_quote="L'avenir est incertain",
            confidence=0.85,
            navigation_trace=["1", "2", "3"],
        )
        assert f.taxonomy_path == "1.1.1"
        assert f.confidence == 0.85
        assert len(f.navigation_trace) == 3

    def test_confidence_clamped(self):
        with pytest.raises(Exception):
            IdentifiedFallacy(
                fallacy_type="test",
                taxonomy_pk="1",
                explanation="test",
                confidence=1.5,
            )

    def test_analysis_result(self):
        result = FallacyAnalysisResult(
            fallacies=[
                IdentifiedFallacy(
                    fallacy_type="Ad Hominem",
                    taxonomy_pk="11",
                    explanation="test",
                )
            ],
            exploration_method="iterative_deepening",
            branches_explored=2,
            total_iterations=5,
        )
        assert len(result.fallacies) == 1
        assert result.exploration_method == "iterative_deepening"


# ---------------------------------------------------------------------------
# 7. One-shot fallback mode
# ---------------------------------------------------------------------------


class TestOneShotMode:
    async def test_one_shot_with_json_response(self, plugin, mock_llm_service):
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: json.dumps(
            {
                "fallacy_name": "Ad Hominem",
                "taxonomy_pk": "11",
                "explanation": "Attacks the person",
                "confidence": 0.8,
            }
        )
        mock_llm_service.get_chat_message_content.return_value = mock_response

        result = await plugin._run_one_shot("You are stupid so you are wrong")
        parsed = json.loads(result)
        assert parsed["fallacies"][0]["fallacy_type"] == "Ad Hominem"
        assert parsed["exploration_method"] == "one_shot"

    async def test_one_shot_with_plain_text(self, plugin, mock_llm_service):
        mock_response = MagicMock()
        mock_response.__str__ = lambda self: "Ad Hominem"
        mock_llm_service.get_chat_message_content.return_value = mock_response

        result = await plugin._run_one_shot("You are wrong")
        parsed = json.loads(result)
        assert "Ad Hominem" in parsed["fallacies"][0]["fallacy_type"]
        assert (
            parsed["fallacies"][0]["confidence"] == 0.3
        )  # Low confidence for plain text

    async def test_one_shot_on_llm_error(self, plugin, mock_llm_service):
        mock_llm_service.get_chat_message_content.side_effect = RuntimeError(
            "API error"
        )
        result = await plugin._run_one_shot("test")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_use_one_shot_flag(self, plugin, mock_llm_service):
        mock_response = MagicMock()
        mock_response.__str__ = (
            lambda self: '{"fallacy_name": "Test", "taxonomy_pk": "1", "explanation": "test", "confidence": 0.5}'
        )
        mock_llm_service.get_chat_message_content.return_value = mock_response

        result = await plugin.run_guided_analysis(
            argument_text="test", use_one_shot=True
        )
        parsed = json.loads(result)
        assert parsed["exploration_method"] == "one_shot"
        # Should NOT have called get_chat_message_contents (iterative mode)
        mock_llm_service.get_chat_message_contents.assert_not_called()


# ---------------------------------------------------------------------------
# 8. Iterative deepening — full flow
# ---------------------------------------------------------------------------


class TestIterativeDeepening:
    def _make_response_with_tool_calls(self, tool_calls):
        """Create a mock LLM response containing function call items."""
        from semantic_kernel.contents import FunctionCallContent

        items = []
        for tc in tool_calls:
            fcc = MagicMock(spec=FunctionCallContent)
            fcc.name = tc["name"]
            fcc.arguments = tc.get("arguments", {})
            fcc.id = tc.get("id", "call_1")
            # Make isinstance check work
            type(fcc).__instancecheck__ = lambda cls, inst: True
            items.append(fcc)

        msg = MagicMock()
        msg.items = items
        return [msg]

    async def test_falls_back_to_one_shot_on_empty_taxonomy(
        self, empty_plugin, mock_llm_service
    ):
        """With no taxonomy, iterative deepening should fall back to one-shot."""
        # Root selection will fail → fallback
        mock_llm_service.get_chat_message_contents.return_value = []

        mock_response = MagicMock()
        mock_response.__str__ = (
            lambda self: '{"fallacy_name": "Unknown", "taxonomy_pk": "", "explanation": "fallback", "confidence": 0.3}'
        )
        mock_llm_service.get_chat_message_content.return_value = mock_response

        result = await empty_plugin.run_guided_analysis(argument_text="Some text")
        parsed = json.loads(result)
        assert parsed["exploration_method"] == "one_shot"

    async def test_falls_back_when_llm_returns_no_tool_calls(
        self, plugin, mock_llm_service
    ):
        """If LLM doesn't call any tools during root selection, fall back."""
        msg = MagicMock()
        msg.items = []  # No function calls
        mock_llm_service.get_chat_message_contents.return_value = [msg]

        mock_response = MagicMock()
        mock_response.__str__ = (
            lambda self: '{"fallacy_name": "Fallback", "taxonomy_pk": "", "explanation": "no tools", "confidence": 0.3}'
        )
        mock_llm_service.get_chat_message_content.return_value = mock_response

        result = await plugin.run_guided_analysis(argument_text="text")
        parsed = json.loads(result)
        assert parsed["exploration_method"] == "one_shot"

    async def test_falls_back_on_root_selection_error(self, plugin, mock_llm_service):
        """If root selection LLM call fails, fall back to one-shot."""
        mock_llm_service.get_chat_message_contents.side_effect = RuntimeError("fail")

        mock_response = MagicMock()
        mock_response.__str__ = (
            lambda self: '{"fallacy_name": "Fallback", "taxonomy_pk": "", "explanation": "error", "confidence": 0.2}'
        )
        mock_llm_service.get_chat_message_content.return_value = mock_response

        result = await plugin.run_guided_analysis(argument_text="text")
        parsed = json.loads(result)
        assert parsed["exploration_method"] == "one_shot"


# ---------------------------------------------------------------------------
# 9. Trace logging
# ---------------------------------------------------------------------------


class TestTraceLogging:
    async def test_trace_log_file_created(self, plugin, mock_llm_service, tmp_path):
        # Use one-shot mode for simpler mock setup
        mock_response = MagicMock()
        mock_response.__str__ = (
            lambda self: '{"fallacy_name": "Test", "taxonomy_pk": "1", "explanation": "t", "confidence": 0.5}'
        )
        mock_llm_service.get_chat_message_content.return_value = mock_response

        log_file = tmp_path / "trace.log"
        await plugin.run_guided_analysis(
            argument_text="Look over there!",
            trace_log_path=str(log_file),
            use_one_shot=True,
        )
        assert log_file.exists()

    async def test_handlers_cleaned_up(self, plugin, mock_llm_service, tmp_path):
        mock_response = MagicMock()
        mock_response.__str__ = (
            lambda self: '{"fallacy_name": "T", "taxonomy_pk": "", "explanation": "", "confidence": 0.5}'
        )
        mock_llm_service.get_chat_message_content.return_value = mock_response

        log_file = tmp_path / "trace.log"
        handler_count_before = len(plugin.logger.handlers)

        await plugin.run_guided_analysis(
            argument_text="text",
            trace_log_path=str(log_file),
            use_one_shot=True,
        )

        assert len(plugin.logger.handlers) == handler_count_before


# ---------------------------------------------------------------------------
# 10. Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    async def test_general_error_returns_json(self, plugin, mock_llm_service):
        mock_llm_service.get_chat_message_contents.side_effect = RuntimeError("fail")
        mock_llm_service.get_chat_message_content.side_effect = RuntimeError("fail too")

        result = await plugin.run_guided_analysis(argument_text="text")
        parsed = json.loads(result)
        assert "error" in parsed


# ---------------------------------------------------------------------------
# 11. Defensive FileHandler — no 'None' file creation
# ---------------------------------------------------------------------------


class TestFileHandlerDefensiveGuard:
    """Verify that FileHandler is NOT created for invalid trace_log_path values."""

    async def test_none_path_no_file_created(self, plugin, mock_llm_service):
        """Passing None (default) must not create a file."""
        mock_llm_service.get_chat_message_contents.side_effect = RuntimeError("stop")
        mock_llm_service.get_chat_message_content.side_effect = RuntimeError("stop")
        handler_count_before = len(plugin.logger.handlers)

        await plugin.run_guided_analysis(argument_text="text", trace_log_path=None)

        assert len(plugin.logger.handlers) == handler_count_before

    async def test_string_none_no_file_created(
        self, plugin, mock_llm_service, tmp_path
    ):
        """Passing 'None' (string) must not create a file named 'None'."""
        mock_llm_service.get_chat_message_contents.side_effect = RuntimeError("stop")
        mock_llm_service.get_chat_message_content.side_effect = RuntimeError("stop")

        await plugin.run_guided_analysis(argument_text="text", trace_log_path="None")

        none_file = tmp_path / "None"
        # Also check CWD isn't polluted
        import os

        assert not os.path.exists("None"), "File named 'None' should not be created"

    async def test_empty_string_no_file_created(self, plugin, mock_llm_service):
        """Passing '' (empty string) must not create a file."""
        mock_llm_service.get_chat_message_contents.side_effect = RuntimeError("stop")
        mock_llm_service.get_chat_message_content.side_effect = RuntimeError("stop")
        handler_count_before = len(plugin.logger.handlers)

        await plugin.run_guided_analysis(argument_text="text", trace_log_path="")

        assert len(plugin.logger.handlers) == handler_count_before

    async def test_null_string_no_file_created(self, plugin, mock_llm_service):
        """Passing 'null' (string) must not create a file."""
        mock_llm_service.get_chat_message_contents.side_effect = RuntimeError("stop")
        mock_llm_service.get_chat_message_content.side_effect = RuntimeError("stop")
        handler_count_before = len(plugin.logger.handlers)

        await plugin.run_guided_analysis(argument_text="text", trace_log_path="null")

        assert len(plugin.logger.handlers) == handler_count_before

    async def test_valid_path_creates_handler(self, plugin, mock_llm_service, tmp_path):
        """Passing a valid path SHOULD create a log file."""
        mock_llm_service.get_chat_message_contents.side_effect = RuntimeError("stop")
        mock_llm_service.get_chat_message_content.side_effect = RuntimeError("stop")
        log_file = str(tmp_path / "trace.log")

        await plugin.run_guided_analysis(argument_text="text", trace_log_path=log_file)

        # Handler is removed in finally, but the file should exist
        import os

        assert os.path.exists(log_file), "Log file should be created for valid path"
