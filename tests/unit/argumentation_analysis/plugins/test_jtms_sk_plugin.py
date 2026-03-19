"""
Tests unitaires pour JTMSSemanticKernelPlugin.

Couvre les 5 kernel functions, les méthodes utilitaires,
la factory function et la gestion automatique de session/instance.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.plugins.semantic_kernel.jtms_plugin import (
    JTMSSemanticKernelPlugin,
    create_jtms_plugin,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_jtms_service():
    """Creates a mocked JTMSService with all async methods."""
    svc = MagicMock()
    svc.create_jtms_instance = AsyncMock(return_value="inst_abc123")
    svc.create_belief = AsyncMock(
        return_value={
            "belief_name": "rain",
            "value": True,
            "created": True,
        }
    )
    svc.add_justification = AsyncMock(
        return_value={
            "justification_id": "j_001",
            "in_beliefs": ["rain"],
            "out_beliefs": [],
            "conclusion": "wet_road",
        }
    )
    svc.explain_belief = AsyncMock(
        return_value={
            "belief_name": "rain",
            "current_status": True,
            "non_monotonic": False,
            "justifications": [{"id": "j_001"}],
            "implications_count": 1,
        }
    )
    svc.query_beliefs = AsyncMock(
        return_value={
            "beliefs": [{"name": "rain", "status": "valid"}],
            "total_beliefs": 3,
            "filtered_count": 1,
        }
    )
    svc.get_jtms_state = AsyncMock(
        return_value={
            "beliefs": [{"name": "rain"}, {"name": "wet_road"}],
            "justifications_graph": {
                "j_001": {"in": ["rain"], "out": [], "conclusion": "wet_road"}
            },
            "statistics": {
                "total_beliefs": 2,
                "valid_beliefs": 1,
                "invalid_beliefs": 0,
                "unknown_beliefs": 1,
                "total_justifications": 1,
                "non_monotonic_beliefs": 0,
            },
        }
    )
    return svc


@pytest.fixture
def mock_session_manager():
    """Creates a mocked JTMSSessionManager with all async methods."""
    mgr = MagicMock()
    mgr.create_session = AsyncMock(return_value="session_xyz789")
    mgr.add_jtms_instance_to_session = AsyncMock()
    mgr.get_session = AsyncMock(
        return_value={
            "session_id": "session_xyz789",
            "agent_id": "semantic_kernel",
            "session_name": "SK_Session_semantic_kernel",
            "created_at": "2026-01-01T00:00:00",
            "last_accessed": "2026-01-01T00:01:00",
            "checkpoint_count": 0,
        }
    )
    return mgr


@pytest.fixture
def plugin(mock_jtms_service, mock_session_manager):
    """Returns a fully-mocked plugin instance."""
    return JTMSSemanticKernelPlugin(
        jtms_service=mock_jtms_service,
        session_manager=mock_session_manager,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_result(json_str: str) -> dict:
    """Parse a JSON string returned by a kernel function."""
    assert isinstance(json_str, str)
    return json.loads(json_str)


# ===========================================================================
# 1. Construction & Factory
# ===========================================================================


class TestConstruction:

    def test_default_init(self):
        """Plugin can be constructed with default services."""
        with patch(
            "argumentation_analysis.plugins.semantic_kernel.jtms_plugin.JTMSService"
        ) as MockSvc, patch(
            "argumentation_analysis.plugins.semantic_kernel.jtms_plugin.JTMSSessionManager"
        ) as MockMgr:
            p = JTMSSemanticKernelPlugin()
            assert p.jtms_service is not None
            assert p.session_manager is not None

    def test_custom_services(self, mock_jtms_service, mock_session_manager):
        p = JTMSSemanticKernelPlugin(mock_jtms_service, mock_session_manager)
        assert p.jtms_service is mock_jtms_service
        assert p.session_manager is mock_session_manager

    def test_factory_function_default(self):
        with patch(
            "argumentation_analysis.plugins.semantic_kernel.jtms_plugin.JTMSService"
        ), patch(
            "argumentation_analysis.plugins.semantic_kernel.jtms_plugin.JTMSSessionManager"
        ):
            p = create_jtms_plugin()
            assert isinstance(p, JTMSSemanticKernelPlugin)

    def test_factory_function_custom(self, mock_jtms_service, mock_session_manager):
        p = create_jtms_plugin(mock_jtms_service, mock_session_manager)
        assert p.jtms_service is mock_jtms_service
        assert p.session_manager is mock_session_manager


# ===========================================================================
# 2. Configuration methods
# ===========================================================================


class TestConfiguration:

    def test_set_default_session(self, plugin):
        plugin.set_default_session("s_123")
        assert plugin.default_session_id == "s_123"

    def test_set_default_instance(self, plugin):
        plugin.set_default_instance("i_456")
        assert plugin.default_instance_id == "i_456"

    def test_configure_auto_creation(self, plugin):
        plugin.configure_auto_creation(auto_session=False, auto_instance=False)
        assert plugin.auto_create_session is False
        assert plugin.auto_create_instance is False


# ===========================================================================
# 3. get_plugin_status
# ===========================================================================


class TestGetPluginStatus:

    async def test_returns_correct_fields(self, plugin):
        status = await plugin.get_plugin_status()
        assert status["plugin_name"] == "JTMSSemanticKernelPlugin"
        assert status["functions_count"] == 5
        assert len(status["functions"]) == 5
        assert "create_belief" in status["functions"]
        assert "get_jtms_state" in status["functions"]
        assert status["jtms_service_active"] is True
        assert status["session_manager_active"] is True
        assert status["auto_create_session"] is True
        assert status["auto_create_instance"] is True
        assert status["default_session_id"] is None
        assert status["default_instance_id"] is None


# ===========================================================================
# 4. _ensure_session_and_instance
# ===========================================================================


class TestEnsureSessionAndInstance:

    async def test_auto_creates_session_and_instance(
        self, plugin, mock_session_manager, mock_jtms_service
    ):
        sid, iid = await plugin._ensure_session_and_instance()
        mock_session_manager.create_session.assert_awaited_once()
        mock_jtms_service.create_jtms_instance.assert_awaited_once()
        assert sid == "session_xyz789"
        assert iid == "inst_abc123"
        # Should store as defaults
        assert plugin.default_session_id == sid
        assert plugin.default_instance_id == iid

    async def test_uses_defaults_when_set(
        self, plugin, mock_session_manager, mock_jtms_service
    ):
        plugin.set_default_session("my_session")
        plugin.set_default_instance("my_instance")
        sid, iid = await plugin._ensure_session_and_instance()
        assert sid == "my_session"
        assert iid == "my_instance"
        mock_session_manager.create_session.assert_not_awaited()
        mock_jtms_service.create_jtms_instance.assert_not_awaited()

    async def test_uses_explicit_params(
        self, plugin, mock_session_manager, mock_jtms_service
    ):
        sid, iid = await plugin._ensure_session_and_instance(
            session_id="explicit_s", instance_id="explicit_i"
        )
        assert sid == "explicit_s"
        assert iid == "explicit_i"
        mock_session_manager.create_session.assert_not_awaited()
        mock_jtms_service.create_jtms_instance.assert_not_awaited()

    async def test_raises_when_auto_create_disabled_no_session(self, plugin):
        plugin.configure_auto_creation(auto_session=False, auto_instance=False)
        with pytest.raises(ValueError, match="session"):
            await plugin._ensure_session_and_instance()

    async def test_raises_when_auto_create_instance_disabled(
        self, plugin, mock_session_manager
    ):
        plugin.configure_auto_creation(auto_session=True, auto_instance=False)
        # session auto-creates fine, but instance should fail
        with pytest.raises(ValueError, match="instance"):
            await plugin._ensure_session_and_instance()


# ===========================================================================
# 5. create_belief
# ===========================================================================


class TestCreateBelief:

    async def test_success_true(self, plugin, mock_jtms_service):
        result = parse_result(
            await plugin.create_belief(belief_name="rain", initial_value="true")
        )
        assert result["operation"] == "create_belief"
        assert result["status"] == "success"
        assert result["belief"] == {
            "belief_name": "rain",
            "value": True,
            "created": True,
        }
        mock_jtms_service.create_belief.assert_awaited_once_with(
            instance_id="inst_abc123",
            belief_name="rain",
            initial_value=True,
        )

    async def test_success_false(self, plugin, mock_jtms_service):
        result = parse_result(
            await plugin.create_belief(belief_name="sun", initial_value="false")
        )
        assert result["status"] == "success"
        mock_jtms_service.create_belief.assert_awaited_once_with(
            instance_id="inst_abc123",
            belief_name="sun",
            initial_value=False,
        )

    async def test_success_unknown(self, plugin, mock_jtms_service):
        result = parse_result(
            await plugin.create_belief(belief_name="wind", initial_value="unknown")
        )
        assert result["status"] == "success"
        mock_jtms_service.create_belief.assert_awaited_once_with(
            instance_id="inst_abc123",
            belief_name="wind",
            initial_value=None,
        )

    async def test_invalid_initial_value(self, plugin):
        result = parse_result(
            await plugin.create_belief(belief_name="x", initial_value="maybe")
        )
        assert result["status"] == "error"
        assert (
            "invalide" in result["error"].lower()
            or "invalid" in result["error"].lower()
        )
        assert result["operation"] == "create_belief"

    async def test_service_error(self, plugin, mock_jtms_service):
        mock_jtms_service.create_belief.side_effect = RuntimeError("DB down")
        result = parse_result(await plugin.create_belief(belief_name="fail_belief"))
        assert result["status"] == "error"
        assert "DB down" in result["error"]

    async def test_returns_session_and_instance_ids(self, plugin):
        result = parse_result(await plugin.create_belief(belief_name="test"))
        assert "session_id" in result
        assert "instance_id" in result
        assert "agent_id" in result

    async def test_custom_agent_id(self, plugin):
        result = parse_result(
            await plugin.create_belief(belief_name="b", agent_id="sherlock")
        )
        assert result["agent_id"] == "sherlock"


# ===========================================================================
# 6. add_justification
# ===========================================================================


class TestAddJustification:

    async def test_success_with_comma_separated(self, plugin, mock_jtms_service):
        result = parse_result(
            await plugin.add_justification(
                in_beliefs="rain, wind",
                out_beliefs="sun",
                conclusion="bad_weather",
            )
        )
        assert result["operation"] == "add_justification"
        assert result["status"] == "success"
        assert "justification" in result
        assert "rule_description" in result
        mock_jtms_service.add_justification.assert_awaited_once_with(
            instance_id="inst_abc123",
            in_beliefs=["rain", "wind"],
            out_beliefs=["sun"],
            conclusion="bad_weather",
        )

    async def test_empty_in_and_out_beliefs(self, plugin, mock_jtms_service):
        result = parse_result(
            await plugin.add_justification(
                in_beliefs="",
                out_beliefs="",
                conclusion="axiom",
            )
        )
        assert result["status"] == "success"
        mock_jtms_service.add_justification.assert_awaited_once_with(
            instance_id="inst_abc123",
            in_beliefs=[],
            out_beliefs=[],
            conclusion="axiom",
        )

    async def test_empty_conclusion_error(self, plugin):
        result = parse_result(
            await plugin.add_justification(
                in_beliefs="a",
                out_beliefs="",
                conclusion="",
            )
        )
        assert result["status"] == "error"
        assert "vide" in result["error"].lower() or "empty" in result["error"].lower()

    async def test_whitespace_conclusion_error(self, plugin):
        result = parse_result(
            await plugin.add_justification(
                in_beliefs="a",
                out_beliefs="",
                conclusion="   ",
            )
        )
        assert result["status"] == "error"

    async def test_service_error(self, plugin, mock_jtms_service):
        mock_jtms_service.add_justification.side_effect = RuntimeError("conflict")
        result = parse_result(
            await plugin.add_justification(
                in_beliefs="a", out_beliefs="", conclusion="c"
            )
        )
        assert result["status"] == "error"
        assert "conflict" in result["error"]


# ===========================================================================
# 7. explain_belief
# ===========================================================================


class TestExplainBelief:

    async def test_success(self, plugin, mock_jtms_service):
        result = parse_result(await plugin.explain_belief(belief_name="rain"))
        assert result["operation"] == "explain_belief"
        assert result["status"] == "success"
        assert result["belief_name"] == "rain"
        assert result["current_status"] is True
        assert "natural_language_summary" in result
        assert "vraie" in result["natural_language_summary"]
        assert "1 justification" in result["natural_language_summary"]
        assert result["session_id"]
        assert result["instance_id"]

    async def test_non_monotonic_mention_in_summary(self, plugin, mock_jtms_service):
        mock_jtms_service.explain_belief.return_value = {
            "belief_name": "loop",
            "current_status": None,
            "non_monotonic": True,
            "justifications": [],
            "implications_count": 0,
        }
        result = parse_result(await plugin.explain_belief(belief_name="loop"))
        assert "non-monotone" in result["natural_language_summary"]

    async def test_false_belief_summary(self, plugin, mock_jtms_service):
        mock_jtms_service.explain_belief.return_value = {
            "belief_name": "x",
            "current_status": False,
            "non_monotonic": False,
            "justifications": [],
            "implications_count": 0,
        }
        result = parse_result(await plugin.explain_belief(belief_name="x"))
        assert "fausse" in result["natural_language_summary"]

    async def test_error_handling(self, plugin, mock_jtms_service):
        mock_jtms_service.explain_belief.side_effect = KeyError("not found")
        result = parse_result(await plugin.explain_belief(belief_name="ghost"))
        assert result["status"] == "error"
        assert result["operation"] == "explain_belief"
        assert result["belief_name"] == "ghost"


# ===========================================================================
# 8. query_beliefs
# ===========================================================================


class TestQueryBeliefs:

    @pytest.mark.parametrize(
        "filter_val,expected_param",
        [
            ("valid", "valid"),
            ("invalid", "invalid"),
            ("unknown", "unknown"),
            ("non_monotonic", "non_monotonic"),
            ("all", None),
        ],
    )
    async def test_all_filter_types(
        self, plugin, mock_jtms_service, filter_val, expected_param
    ):
        result = parse_result(await plugin.query_beliefs(filter_status=filter_val))
        assert result["operation"] == "query_beliefs"
        assert result["status"] == "success"
        assert "beliefs" in result
        assert "natural_language_summary" in result
        mock_jtms_service.query_beliefs.assert_awaited_with(
            instance_id="inst_abc123",
            filter_status=expected_param,
        )

    async def test_all_filter_summary_text(self, plugin):
        result = parse_result(await plugin.query_beliefs(filter_status="all"))
        assert "au total" in result["natural_language_summary"]

    async def test_specific_filter_summary_text(self, plugin):
        result = parse_result(await plugin.query_beliefs(filter_status="valid"))
        assert "statut" in result["natural_language_summary"]

    async def test_invalid_filter_error(self, plugin):
        result = parse_result(await plugin.query_beliefs(filter_status="bogus"))
        assert result["status"] == "error"
        assert (
            "invalide" in result["error"].lower()
            or "invalid" in result["error"].lower()
        )

    async def test_service_error(self, plugin, mock_jtms_service):
        mock_jtms_service.query_beliefs.side_effect = RuntimeError("timeout")
        result = parse_result(await plugin.query_beliefs())
        assert result["status"] == "error"
        assert "timeout" in result["error"]


# ===========================================================================
# 9. get_jtms_state
# ===========================================================================


class TestGetJtmsState:

    async def test_success_full(self, plugin, mock_jtms_service, mock_session_manager):
        result = parse_result(await plugin.get_jtms_state())
        assert result["operation"] == "get_jtms_state"
        assert result["status"] == "success"
        assert "beliefs" in result
        assert "justifications_graph" in result
        assert "statistics" in result
        assert "session_info" in result
        assert "natural_language_summary" in result
        # Session info enrichment
        si = result["session_info"]
        assert si["session_id"] == "session_xyz789"
        assert si["agent_id"] == "semantic_kernel"
        assert si["session_name"] == "SK_Session_semantic_kernel"
        assert "created_at" in si
        assert "last_accessed" in si
        assert si["checkpoint_count"] == 0

    async def test_exclude_graph(self, plugin, mock_jtms_service):
        result = parse_result(await plugin.get_jtms_state(include_graph="false"))
        assert "justifications_graph" not in result
        assert "statistics" in result

    async def test_exclude_statistics(self, plugin, mock_jtms_service):
        result = parse_result(await plugin.get_jtms_state(include_statistics="false"))
        assert "justifications_graph" in result
        assert "statistics" not in result

    async def test_exclude_both(self, plugin, mock_jtms_service):
        result = parse_result(
            await plugin.get_jtms_state(
                include_graph="false", include_statistics="false"
            )
        )
        assert "justifications_graph" not in result
        assert "statistics" not in result
        # Summary should still exist, using empty stats
        assert "natural_language_summary" in result

    async def test_non_monotonic_warning_in_summary(
        self, plugin, mock_jtms_service, mock_session_manager
    ):
        state = mock_jtms_service.get_jtms_state.return_value
        state["statistics"]["non_monotonic_beliefs"] = 2
        result = parse_result(await plugin.get_jtms_state())
        assert "non-monotone" in result["natural_language_summary"].lower()

    async def test_error_handling(self, plugin, mock_jtms_service):
        mock_jtms_service.get_jtms_state.side_effect = RuntimeError("corrupt state")
        result = parse_result(await plugin.get_jtms_state())
        assert result["status"] == "error"
        assert "corrupt state" in result["error"]
        assert result["operation"] == "get_jtms_state"

    async def test_session_manager_error(
        self, plugin, mock_jtms_service, mock_session_manager
    ):
        mock_session_manager.get_session.side_effect = KeyError("session gone")
        result = parse_result(await plugin.get_jtms_state())
        assert result["status"] == "error"
