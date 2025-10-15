"""Test d'intégration rapide des composants JTMS."""
import pytest


def test_import_sherlock_jtms_agent():
    """Vérifie que SherlockJTMSAgent peut être importé."""
    try:
        from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent

        assert SherlockJTMSAgent is not None
    except ImportError as e:
        pytest.fail(f"Impossible d'importer SherlockJTMSAgent: {e}")


def test_import_watson_jtms_agent():
    """Vérifie que WatsonJTMSAgent peut être importé."""
    try:
        from argumentation_analysis.agents.watson_jtms_agent import WatsonJTMSAgent

        assert WatsonJTMSAgent is not None
    except ImportError as e:
        pytest.fail(f"Impossible d'importer WatsonJTMSAgent: {e}")


def test_import_jtms_communication_hub():
    """Vérifie que JTMSCommunicationHub peut être importé."""
    try:
        from argumentation_analysis.agents.jtms_communication_hub import (
            JTMSCommunicationHub,
        )

        assert JTMSCommunicationHub is not None
    except ImportError as e:
        pytest.fail(f"Impossible d'importer JTMSCommunicationHub: {e}")


def test_import_jtms_agent_base():
    """Vérifie que JTMSAgentBase peut être importé."""
    try:
        from argumentation_analysis.agents.jtms_agent_base import JTMSAgentBase

        assert JTMSAgentBase is not None
    except ImportError as e:
        pytest.fail(f"Impossible d'importer JTMSAgentBase: {e}")
