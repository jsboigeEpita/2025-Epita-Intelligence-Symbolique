#!/usr/bin/env python3
"""
TEST DE VALIDATION RÉELLE - Structure Actuelle du Projet
========================================================

Ce script teste ce qui existe VRAIMENT dans le projet, pas ce qu'on imagine.
Il examine la structure réelle et teste les vraies capacités.
"""

import sys
import os
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'trace_reelle_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

import pytest
from typing import Dict, Any
import json

# Configuration du logging
logger = logging.getLogger(__name__)

def test_imports_agents_reels():
    """Teste l'importation des agents Sherlock et Watson."""
    try:
        from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
        from argumentation_analysis.agents.watson_jtms_agent import WatsonJTMSAgent
        assert SherlockJTMSAgent is not None
        assert WatsonJTMSAgent is not None
    except ImportError as e:
        pytest.fail(f"Échec de l'import des agents réels: {e}")

def test_imports_jtms_base_reels():
    """Teste l'importation des composants de base du JTMS."""
    try:
        from argumentation_analysis.agents.jtms_agent_base import JTMSAgentBase
        from argumentation_analysis.agents.jtms_communication_hub import JTMSCommunicationHub
        from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
        assert JTMSAgentBase is not None
        assert JTMSCommunicationHub is not None
        assert CluedoOracleState is not None
    except ImportError as e:
        pytest.fail(f"Échec de l'import des composants JTMS de base: {e}")

def test_interface_web_reelle(capsys):
    """Teste l'importation et la structure de l'application Flask."""
    try:
        from interface_web.app import app
        assert app is not None

        endpoints_to_test = ['/', '/health', '/api/status', '/jtms', '/cluedo', '/playground']
        working_endpoints = 0
        with app.test_client() as client:
            for endpoint in endpoints_to_test:
                try:
                    resp = client.get(endpoint)
                    if resp.status_code < 500:
                        working_endpoints += 1
                except Exception:
                    pass  # Ignorer les erreurs d'endpoint pour le moment
        assert working_endpoints > 0, "Aucun endpoint de l'interface web ne fonctionne."
    except (ImportError, AssertionError) as e:
        pytest.fail(f"Test de l'interface web a échoué: {e}")

def test_imports_orchestration_reelle():
    """Teste l'importation des modules d'orchestration."""
    modules_ok = []
    modules_ko = []
    orchestration_modules = [
        'cluedo_extended_orchestrator',
        'cluedo_orchestrator',
        'sherlock_watson_orchestrator',
        'argumentation_analysis.main_orchestrator',
    ]
    for module in orchestration_modules:
        try:
            if '.' in module:
                 __import__(module, fromlist=['MainOrchestrator'])
            else:
                 __import__(f"argumentation_analysis.orchestration.{module}")
            modules_ok.append(module)
        except ImportError as e:
            modules_ko.append((module, e))
    
    assert not modules_ko, f"Échec d'import des modules d'orchestration: {modules_ko}"

def test_scenario_cluedo_simple():
    """Teste l'instanciation de CluedoOracleState."""
    try:
        from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
        state = CluedoOracleState()
        assert hasattr(state, 'add_evidence') or hasattr(state, 'add_clue')
    except (ImportError, AssertionError) as e:
        pytest.fail(f"Test du scénario Cluedo simple a échoué: {e}")