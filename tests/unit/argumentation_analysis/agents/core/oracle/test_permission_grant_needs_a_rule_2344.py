"""#2344: a permission is granted to an agent the ACL knows, never to a stranger.

Measured on ``main`` ``dc463b0a5``: ``PermissionManager.add_permission`` on an
agent with no rule silently created one from the ``PermissionRule`` defaults:
no ``forbidden_fields``, a 50-query quota, the ``balanced`` policy. The three
default Cluedo rules all carry explicit protections, so a stranger entered the
whitelist through a side door, with weaker conditions than every agent in it.

An agent enters the ACL through ``add_permission_rule``, with conditions its
caller wrote. ``add_permission`` only widens a rule that already exists.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
from argumentation_analysis.agents.core.oracle.dataset_access_manager import (
    CluedoDatasetManager,
)
from argumentation_analysis.agents.core.oracle.error_handling import (
    OraclePermissionError,
)
from argumentation_analysis.agents.core.oracle.permissions import (
    PermissionManager,
    PermissionRule,
    QueryType,
)


@pytest.fixture
def manager() -> CluedoDatasetManager:
    return CluedoDatasetManager(
        CluedoDataset(moriarty_cards=["Colonel Moutarde", "Revolver", "Cuisine"])
    )


class TestAStrangerIsRefused:
    def test_granting_to_an_unknown_agent_raises(self):
        pm = PermissionManager()
        with pytest.raises(OraclePermissionError, match="add_permission_rule"):
            pm.add_permission("Intrus", QueryType.CARD_INQUIRY)

    def test_the_refused_agent_stays_outside_the_acl(self):
        pm = PermissionManager()
        with pytest.raises(OraclePermissionError):
            pm.add_permission("Intrus", QueryType.CARD_INQUIRY)
        assert pm.get_permission_rule("Intrus") is None
        assert pm.is_authorized("Intrus", QueryType.CARD_INQUIRY) is False

    async def test_the_dataset_manager_refuses_too(self, manager):
        with pytest.raises(OraclePermissionError):
            manager.add_permission("Intrus", QueryType.CARD_INQUIRY)
        assert manager.get_agent_permissions("Intrus") is None
        assert await manager.check_permission("Intrus", QueryType.CARD_INQUIRY) is False


class TestAKnownAgentKeepsItsConditions:
    def test_widening_a_default_rule_keeps_its_protections(self, manager):
        # Control: the capability stays for an agent the ACL knows.
        rule = manager.get_agent_permissions("SherlockEnqueteAgent")
        forbidden = list(rule.forbidden_fields)
        manager.add_permission("SherlockEnqueteAgent", QueryType.RAPID_TEST)
        assert QueryType.RAPID_TEST in rule.allowed_query_types
        assert rule.forbidden_fields == forbidden
        assert "solution_secrete" in rule.forbidden_fields

    def test_an_explicit_rule_admits_the_agent(self):
        pm = PermissionManager()
        pm.add_permission_rule(
            PermissionRule(
                agent_name="Lestrade",
                allowed_query_types=[QueryType.CLUE_REQUEST],
                conditions={"forbidden_fields": ["solution_secrete"]},
            )
        )
        pm.add_permission("Lestrade", QueryType.CARD_INQUIRY)
        assert pm.is_authorized("Lestrade", QueryType.CARD_INQUIRY) is True
