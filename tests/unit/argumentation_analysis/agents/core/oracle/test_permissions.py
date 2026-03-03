# tests/unit/argumentation_analysis/agents/core/oracle/test_permissions.py
"""Tests for Oracle permission system — ACL, quotas, audit logging."""

import pytest
from argumentation_analysis.agents.core.oracle.permissions import (
    PermissionDeniedError,
    InvalidQueryError,
    QueryType,
    RevealPolicy,
    PermissionRule,
    QueryResult,
    ValidationResult,
    OracleResponse,
    AccessLog,
    PermissionManager,
    CluedoIntegrityError,
    validate_cluedo_method_access,
    get_default_cluedo_permissions,
)


# ── Enums ──

class TestQueryType:
    def test_has_twelve_types(self):
        assert len(QueryType) == 12

    def test_card_inquiry(self):
        assert QueryType.CARD_INQUIRY.value == "card_inquiry"

    def test_admin_command(self):
        assert QueryType.ADMIN_COMMAND.value == "admin_command"


class TestRevealPolicy:
    def test_has_four_policies(self):
        assert len(RevealPolicy) == 4

    def test_values(self):
        expected = {"progressive", "cooperative", "competitive", "balanced"}
        assert {p.value for p in RevealPolicy} == expected


# ── PermissionRule ──

class TestPermissionRule:
    def test_defaults(self):
        rule = PermissionRule(
            agent_name="TestAgent",
            allowed_query_types=[QueryType.CARD_INQUIRY],
        )
        assert rule.agent_name == "TestAgent"
        assert rule.max_daily_queries == 50
        assert rule.forbidden_fields == []
        assert rule.reveal_policy == RevealPolicy.BALANCED.value

    def test_custom_conditions(self):
        rule = PermissionRule(
            agent_name="Agent",
            allowed_query_types=[],
            conditions={
                "max_daily_queries": 10,
                "forbidden_fields": ["secret"],
                "reveal_policy": RevealPolicy.PROGRESSIVE.value,
            },
        )
        assert rule.max_daily_queries == 10
        assert rule.forbidden_fields == ["secret"]
        assert rule.reveal_policy == RevealPolicy.PROGRESSIVE.value

    def test_post_init_fills_defaults(self):
        rule = PermissionRule(
            agent_name="Agent",
            allowed_query_types=[],
            conditions={"custom_key": True},
        )
        # Post-init should add defaults alongside custom keys
        assert "max_daily_queries" in rule.conditions
        assert "forbidden_fields" in rule.conditions
        assert "reveal_policy" in rule.conditions
        assert rule.conditions["custom_key"] is True


# ── QueryResult ──

class TestQueryResult:
    def test_success(self):
        r = QueryResult(success=True, data={"key": "val"}, message="OK")
        assert "SUCCESS" in str(r)

    def test_failure(self):
        r = QueryResult(success=False, message="Not found")
        assert "FAILED" in str(r)


# ── ValidationResult ──

class TestValidationResult:
    def test_can_refute(self):
        v = ValidationResult(can_refute=True, reason="Card match")
        assert "CAN_REFUTE" in str(v)
        assert "AUTHORIZED" in str(v)

    def test_cannot_refute(self):
        v = ValidationResult(can_refute=False)
        assert "CANNOT_REFUTE" in str(v)

    def test_denied(self):
        v = ValidationResult(can_refute=False, authorized=False, reason="No access")
        assert "DENIED" in str(v)


# ── OracleResponse ──

class TestOracleResponse:
    def test_authorized(self):
        r = OracleResponse(authorized=True, message="Access granted")
        assert r.success is True
        assert "AUTHORIZED" in str(r)

    def test_denied(self):
        r = OracleResponse(authorized=False, message="Denied")
        assert r.success is False
        assert "DENIED" in str(r)

    def test_all_fields(self):
        r = OracleResponse(
            authorized=True,
            data={"card": "Colonel Mustard"},
            message="Found",
            query_type=QueryType.CARD_INQUIRY,
            revealed_information=["Colonel Mustard"],
            agent_name="Sherlock",
            revelation_triggered=True,
            hint_content="Look in the library",
            error_code=None,
        )
        assert r.agent_name == "Sherlock"
        assert r.revelation_triggered is True
        assert r.hint_content == "Look in the library"
        assert r.error_code is None


# ── PermissionManager ──

class TestPermissionManager:
    @pytest.fixture
    def pm(self):
        return PermissionManager()

    @pytest.fixture
    def rule_sherlock(self):
        return PermissionRule(
            agent_name="Sherlock",
            allowed_query_types=[
                QueryType.CARD_INQUIRY,
                QueryType.SUGGESTION_VALIDATION,
            ],
            conditions={"max_daily_queries": 5},
        )

    def test_add_rule(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        assert pm.get_permission_rule("Sherlock") is rule_sherlock

    def test_is_authorized_allowed(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        assert pm.is_authorized("Sherlock", QueryType.CARD_INQUIRY) is True

    def test_is_authorized_not_allowed(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        assert pm.is_authorized("Sherlock", QueryType.ADMIN_COMMAND) is False

    def test_is_authorized_unknown_agent(self, pm):
        assert pm.is_authorized("Unknown", QueryType.CARD_INQUIRY) is False

    def test_quota_enforcement(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        # Fill quota
        for i in range(5):
            pm.log_access("Sherlock", QueryType.CARD_INQUIRY, success=True)
        # Now should be denied
        assert pm.is_authorized("Sherlock", QueryType.CARD_INQUIRY) is False

    def test_add_permission_new_agent(self, pm):
        pm.add_permission(agent_name="NewAgent", query_type=QueryType.CLUE_REQUEST)
        assert pm.is_authorized("NewAgent", QueryType.CLUE_REQUEST) is True

    def test_add_permission_existing_agent(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        pm.add_permission("Sherlock", QueryType.CLUE_REQUEST)
        assert pm.is_authorized("Sherlock", QueryType.CLUE_REQUEST) is True

    def test_add_permission_idempotent(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        original_len = len(rule_sherlock.allowed_query_types)
        pm.add_permission("Sherlock", QueryType.CARD_INQUIRY)  # already there
        assert len(rule_sherlock.allowed_query_types) == original_len

    def test_log_access(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        pm.log_access("Sherlock", QueryType.CARD_INQUIRY, success=True, details="test")
        logs = pm.get_access_log("Sherlock")
        assert len(logs) == 1
        assert logs[0].agent_name == "Sherlock"
        assert logs[0].result is True

    def test_log_access_failed_no_count(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        pm.log_access("Sherlock", QueryType.CARD_INQUIRY, success=False)
        stats = pm.get_query_stats("Sherlock")
        assert stats["daily_queries_used"] == 0

    def test_get_access_log_all(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        pm.log_access("Sherlock", QueryType.CARD_INQUIRY, success=True)
        pm.log_access("Sherlock", QueryType.CARD_INQUIRY, success=False)
        all_logs = pm.get_access_log()
        assert len(all_logs) == 2

    def test_reset_daily_counts(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        for i in range(5):
            pm.log_access("Sherlock", QueryType.CARD_INQUIRY, success=True)
        assert pm.is_authorized("Sherlock", QueryType.CARD_INQUIRY) is False
        pm.reset_daily_counts()
        assert pm.is_authorized("Sherlock", QueryType.CARD_INQUIRY) is True

    def test_get_query_stats(self, pm, rule_sherlock):
        pm.add_permission_rule(rule_sherlock)
        pm.log_access("Sherlock", QueryType.CARD_INQUIRY, success=True)
        pm.log_access("Sherlock", QueryType.CARD_INQUIRY, success=False)
        stats = pm.get_query_stats("Sherlock")
        assert stats["agent_name"] == "Sherlock"
        assert stats["daily_queries_used"] == 1  # only successful
        assert stats["daily_queries_limit"] == 5
        assert stats["total_queries"] == 2
        assert stats["success_rate"] == 0.5

    def test_get_query_stats_unknown(self, pm):
        assert pm.get_query_stats("Unknown") == {}

    def test_get_permission_rule_none(self, pm):
        assert pm.get_permission_rule("Nonexistent") is None


# ── Cluedo Integrity ──

class TestCluedoIntegrity:
    def test_forbidden_method(self):
        with pytest.raises(CluedoIntegrityError, match="INTÉGRITÉ CLUEDO"):
            validate_cluedo_method_access("get_solution", "BadAgent")

    def test_forbidden_get_cards(self):
        with pytest.raises(CluedoIntegrityError):
            validate_cluedo_method_access("get_autres_joueurs_cards", "Agent")

    def test_forbidden_direct_access(self):
        with pytest.raises(CluedoIntegrityError):
            validate_cluedo_method_access("direct_card_access", "Agent")

    def test_allowed_method(self):
        # Should not raise
        validate_cluedo_method_access("safe_method", "Agent")


class TestDefaultCluedoPermissions:
    def test_has_three_agents(self):
        perms = get_default_cluedo_permissions()
        assert "SherlockEnqueteAgent" in perms
        assert "WatsonLogicAssistant" in perms
        assert "MoriartyInterrogator" in perms

    def test_sherlock_permissions(self):
        perms = get_default_cluedo_permissions()
        sherlock = perms["SherlockEnqueteAgent"]
        assert QueryType.CARD_INQUIRY in sherlock.allowed_query_types
        assert QueryType.SUGGESTION_VALIDATION in sherlock.allowed_query_types
        assert sherlock.conditions["integrity_enforced"] is True

    def test_watson_permissions(self):
        perms = get_default_cluedo_permissions()
        watson = perms["WatsonLogicAssistant"]
        assert QueryType.LOGICAL_VALIDATION in watson.allowed_query_types
        assert QueryType.CONSTRAINT_CHECK in watson.allowed_query_types

    def test_moriarty_permissions(self):
        perms = get_default_cluedo_permissions()
        moriarty = perms["MoriartyInterrogator"]
        assert QueryType.PROGRESSIVE_HINT in moriarty.allowed_query_types
        assert moriarty.conditions.get("can_reveal_own_cards") is True

    def test_all_have_forbidden_methods(self):
        perms = get_default_cluedo_permissions()
        for name, rule in perms.items():
            assert "get_solution" in rule.conditions.get("forbidden_methods", [])
            assert "get_autres_joueurs_cards" in rule.conditions.get(
                "forbidden_methods", []
            )


# ── Exceptions ──

class TestExceptions:
    def test_permission_denied_error(self):
        with pytest.raises(PermissionDeniedError):
            raise PermissionDeniedError("Access denied")

    def test_invalid_query_error(self):
        with pytest.raises(InvalidQueryError):
            raise InvalidQueryError("Bad query")

    def test_cluedo_integrity_error(self):
        with pytest.raises(CluedoIntegrityError):
            raise CluedoIntegrityError("Violation")
