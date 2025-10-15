#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum


class OrchestrationMode(Enum):
    """Modes d'orchestration disponibles."""

    PIPELINE = "pipeline"
    REAL = "real"
    CONVERSATION = "conversation"
    HIERARCHICAL_FULL = "hierarchical_full"
    STRATEGIC_ONLY = "strategic_only"
    TACTICAL_COORDINATION = "tactical_coordination"
    OPERATIONAL_DIRECT = "operational_direct"
    CLUEDO_INVESTIGATION = "cluedo_investigation"
    LOGIC_COMPLEX = "logic_complex"
    ADAPTIVE_HYBRID = "adaptive_hybrid"
    AUTO_SELECT = "auto_select"


class AnalysisType(Enum):
    """Types d'analyse supportés."""

    COMPREHENSIVE = "comprehensive"
    RHETORICAL = "rhetorical"
    LOGICAL = "logical"
    INVESTIGATIVE = "investigative"
    FALLACY_FOCUSED = "fallacy_focused"
    ARGUMENT_STRUCTURE = "argument_structure"
    DEBATE_ANALYSIS = "debate_analysis"
    CUSTOM = "custom"
