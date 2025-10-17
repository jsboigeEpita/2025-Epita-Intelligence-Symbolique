# Authentic gpt-5-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixtures pour les agents utilisés dans les tests.

Ce module fournit des fixtures réutilisables pour les tests d'agents
et leurs adaptateurs.
"""

import pytest
import os
import sys


# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
# sys.path.append(os.path.abspath('../..'))
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

# Import des modules à tester
from argumentation_analysis.agents.core.informal.informal_agent import (
    InformalAnalysisAgent as InformalAgent,
)
from argumentation_analysis.agents.core.informal.informal_definitions import (
    FallacyDefinition,
    FallacyCategory,
)
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import (
    ComplexFallacyAnalyzer,
)
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import (
    EnhancedContextualFallacyAnalyzer as ContextualFallacyAnalyzer,
)
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import (
    FallacySeverityEvaluator,
)
from argumentation_analysis.agents.tools.analysis.fallacy_detector import (
    FallacyDetector,
)
from argumentation_analysis.agents.tools.analysis.rhetorical_analyzer import (
    RhetoricalAnalyzer,
)
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import (
    ExtractAgentAdapter,
)
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import (
    InformalAgentAdapter,
)
from argumentation_analysis.orchestration.message_middleware import MessageMiddleware


@pytest.fixture
def mock_middleware():
    """Fixture fournissant un middleware mocké."""
    middleware = MagicMock(spec=MessageMiddleware)
    middleware.send_message.return_value = True
    middleware.receive_message.return_value = None
    middleware.get_pending_messages.return_value = []
    return middleware


@pytest.fixture
def real_middleware():
    """Fixture fournissant un middleware réel."""
    middleware = MessageMiddleware()
    middleware.initialize_protocols()
    yield middleware
    middleware.shutdown()


@pytest.fixture
def fallacy_definitions():
    """Fixture fournissant des définitions de sophismes."""
    return [
        FallacyDefinition(
            name="ad_hominem",
            category=FallacyCategory.RELEVANCE,
            description="Attaque la personne plutôt que l'argument",
            examples=["Il est stupide, donc son argument est invalide"],
            detection_patterns=["stupide", "idiot", "incompétent"],
        ),
        FallacyDefinition(
            name="faux_dilemme",
            category=FallacyCategory.STRUCTURE,
            description="Présente seulement deux options alors qu'il en existe d'autres",
            examples=["Soit vous êtes avec nous, soit vous êtes contre nous"],
            detection_patterns=["soit...soit", "ou bien...ou bien", "deux options"],
        ),
        FallacyDefinition(
            name="pente_glissante",
            category=FallacyCategory.CAUSALITE,
            description="Suggère qu'une action mènera inévitablement à une chaîne d'événements indésirables",
            examples=["Si nous autorisons cela, bientôt tout sera permis"],
            detection_patterns=["bientôt", "mènera à", "conduira à", "inévitablement"],
        ),
    ]


@pytest.fixture
def fallacy_detector(fallacy_definitions):
    """Fixture fournissant un détecteur de sophismes."""
    return FallacyDetector(fallacy_definitions=fallacy_definitions)


@pytest.fixture
def rhetorical_analyzer():
    """Fixture fournissant un analyseur rhétorique."""
    return RhetoricalAnalyzer()


@pytest.fixture
def complex_fallacy_analyzer():
    """Fixture fournissant un analyseur de sophismes complexes."""
    return ComplexFallacyAnalyzer()


@pytest.fixture
def contextual_fallacy_analyzer():
    """Fixture fournissant un analyseur contextuel de sophismes."""
    return ContextualFallacyAnalyzer()


@pytest.fixture
def fallacy_severity_evaluator():
    """Fixture fournissant un évaluateur de sévérité des sophismes."""
    return FallacySeverityEvaluator()


@pytest.fixture
def informal_agent(fallacy_detector, rhetorical_analyzer):
    """Fixture fournissant un agent informel avec des outils de base."""
    return InformalAgent(
        agent_id="informal_agent_test",
        tools={
            "fallacy_detector": fallacy_detector,
            "rhetorical_analyzer": rhetorical_analyzer,
        },
    )


@pytest.fixture
def enhanced_informal_agent(
    complex_fallacy_analyzer, contextual_fallacy_analyzer, fallacy_severity_evaluator
):
    """Fixture fournissant un agent informel avec des outils améliorés."""
    return InformalAgent(
        agent_id="enhanced_informal_agent_test",
        tools={
            "complex_analyzer": complex_fallacy_analyzer,
            "contextual_analyzer": contextual_fallacy_analyzer,
            "severity_evaluator": fallacy_severity_evaluator,
        },
    )


@pytest.fixture
def extract_agent_adapter(mock_middleware):
    """Fixture fournissant un adaptateur d'agent d'extraction avec un middleware mocké."""
    return ExtractAgentAdapter(
        agent_id="extract_agent_test", middleware=mock_middleware
    )


@pytest.fixture
def real_extract_agent_adapter(real_middleware):
    """Fixture fournissant un adaptateur d'agent d'extraction avec un middleware réel."""
    return ExtractAgentAdapter(
        agent_id="extract_agent_test", middleware=real_middleware
    )


@pytest.fixture
def informal_agent_adapter(mock_middleware):
    """Fixture fournissant un adaptateur d'agent informel avec un middleware mocké."""
    return InformalAgentAdapter(
        agent_id="informal_agent_adapter_test", middleware=mock_middleware
    )


@pytest.fixture
def real_informal_agent_adapter(real_middleware):
    """Fixture fournissant un adaptateur d'agent informel avec un middleware réel."""
    return InformalAgentAdapter(
        agent_id="informal_agent_adapter_test", middleware=real_middleware
    )


@pytest.fixture
def mock_extract_agent_adapter():
    """Fixture fournissant un adaptateur d'agent d'extraction entièrement mocké."""
    adapter = MagicMock(spec=ExtractAgentAdapter)
    adapter.agent_id = "mock_extract_agent"
    adapter.extract_text_from_file.return_value = """
    Le réchauffement climatique est un mythe car il a neigé cet hiver.
    Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
    Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
    """
    adapter.send_task_result.return_value = True
    return adapter


@pytest.fixture
def mock_informal_agent_adapter():
    """Fixture fournissant un adaptateur d'agent informel entièrement mocké."""
    adapter = MagicMock(spec=InformalAgentAdapter)
    adapter.agent_id = "mock_informal_agent_adapter"
    adapter.analyze_text.return_value = {
        "fallacies": [
            {
                "type": "généralisation_hâtive",
                "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver",
                "confidence": 0.92,
            },
            {
                "type": "faux_dilemme",
                "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans",
                "confidence": 0.85,
            },
            {
                "type": "ad_hominem",
                "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées",
                "confidence": 0.88,
            },
        ],
        "analysis_metadata": {
            "timestamp": "2025-05-21T23:30:00",
            "agent_id": "informal_agent",
            "version": "1.0",
        },
    }
    adapter.send_task_result.return_value = True
    return adapter


@pytest.fixture
def mock_informal_agent():
    """Fixture fournissant un agent informel entièrement mocké."""
    agent = MagicMock(spec=InformalAgent)
    agent.agent_id = "mock_informal_agent"
    agent.analyze_text.return_value = {
        "fallacies": [
            {
                "type": "généralisation_hâtive",
                "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver",
                "confidence": 0.92,
            },
            {
                "type": "faux_dilemme",
                "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans",
                "confidence": 0.85,
            },
            {
                "type": "ad_hominem",
                "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées",
                "confidence": 0.88,
            },
        ],
        "analysis_metadata": {
            "timestamp": "2025-05-21T23:30:00",
            "agent_id": "informal_agent",
            "version": "1.0",
        },
    }
    agent.perform_enhanced_analysis.return_value = {
        "fallacies": [
            {
                "type": "généralisation_hâtive",
                "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver",
                "confidence": 0.92,
            },
            {
                "type": "faux_dilemme",
                "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans",
                "confidence": 0.85,
            },
            {
                "type": "ad_hominem",
                "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées",
                "confidence": 0.88,
            },
        ],
        "context_analysis": {
            "généralisation_hâtive": {
                "context_relevance": 0.7,
                "cultural_factors": ["climat", "science"],
            },
            "faux_dilemme": {
                "context_relevance": 0.8,
                "cultural_factors": ["environnement", "politique"],
            },
            "ad_hominem": {
                "context_relevance": 0.9,
                "cultural_factors": ["science", "financement"],
            },
        },
        "severity_evaluation": [
            {"type": "généralisation_hâtive", "severity": 0.7, "impact": "medium"},
            {"type": "faux_dilemme", "severity": 0.8, "impact": "high"},
            {"type": "ad_hominem", "severity": 0.9, "impact": "high"},
        ],
        "metadata": {
            "timestamp": "2025-05-21T23:30:00",
            "agent_id": "informal_agent",
            "version": "1.0",
        },
    }
    return agent
