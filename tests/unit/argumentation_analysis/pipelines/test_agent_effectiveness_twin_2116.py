"""Direct guard on the surviving effectiveness twin (#2116 item 4, decision A3).

``reporting_pipeline._analyze_agent_effectiveness`` is the analysis kept alive
when its duplicated sibling ``analytics/effectiveness_analyzer.py`` was
withdrawn — and it had **zero direct tests** at that moment. This guard pins
the capability on the live function so the kept twin is not a blind spot:
empty / single / multi-corpus cases, the averaging path, and the advanced-only
branch, on synthetic opaque inputs.
"""

import pandas as pd
import pytest

from argumentation_analysis.pipelines.reporting_pipeline import (
    _analyze_agent_effectiveness,
)

BASE_AGENT_KEYS = {
    "contextual_fallacy_detector",
    "argument_coherence_evaluator",
    "semantic_argument_analyzer",
}
ADVANCED_AGENT_KEYS = {
    "enhanced_contextual_fallacy_analyzer",
    "enhanced_complex_fallacy_analyzer",
    "enhanced_fallacy_severity_evaluator",
    "enhanced_rhetorical_result_analyzer",
}


def _base_result(corpus: str, coherence: float, semantic: float, fallacies=None):
    return {
        "corpus_name": corpus,
        "analyses": {
            "contextual_fallacies": {
                "argument_results": [{"detected_fallacies": fallacies or []}]
            },
            "argument_coherence": {"coherence_score": coherence},
            "semantic_analysis": {"semantic_score": semantic},
        },
    }


def test_empty_inputs_yield_empty_effectiveness():
    assert _analyze_agent_effectiveness([], [], pd.DataFrame()) == {}


def test_single_corpus_base_result():
    base = [
        _base_result("corpus_A", coherence=0.5, semantic=0.25, fallacies=["f1", "f2"])
    ]
    effectiveness = _analyze_agent_effectiveness(base, [], pd.DataFrame())

    assert set(effectiveness) == {"corpus_A"}
    entry = effectiveness["corpus_A"]
    assert set(entry["base_agents"]) == BASE_AGENT_KEYS
    assert entry["base_agents"]["contextual_fallacy_detector"]["fallacy_count"] == 2
    assert entry["base_agents"]["contextual_fallacy_detector"]["effectiveness"] == 2.0
    assert (
        entry["base_agents"]["argument_coherence_evaluator"]["coherence_score"] == 0.5
    )
    assert entry["base_agents"]["semantic_argument_analyzer"]["semantic_score"] == 0.25
    assert entry["advanced_agents"] == {}
    assert entry["best_agent"] == "contextual_fallacy_detector"
    assert len(entry["recommendations"]) == 3


def test_multi_corpus_averages_scores_per_corpus():
    base = [
        _base_result("corpus_A", coherence=0.2, semantic=0.1),
        _base_result("corpus_A", coherence=0.6, semantic=0.3),
        _base_result("corpus_B", coherence=0.9, semantic=0.9),
    ]
    effectiveness = _analyze_agent_effectiveness(base, [], pd.DataFrame())

    assert set(effectiveness) == {"corpus_A", "corpus_B"}
    corpus_a = effectiveness["corpus_A"]["base_agents"]
    assert corpus_a["argument_coherence_evaluator"]["coherence_score"] == pytest.approx(
        0.4
    )
    assert corpus_a["semantic_argument_analyzer"]["semantic_score"] == pytest.approx(
        0.2
    )
    corpus_b = effectiveness["corpus_B"]["base_agents"]
    assert corpus_b["argument_coherence_evaluator"]["coherence_score"] == 0.9


def test_recommendations_are_order_invariant_2362():
    """The guidance attached to a corpus must not depend on its rank (#2362).

    A class-specific advice keyed on the position of the corpus in the run
    qualifies whichever corpus lands at that position — the name is gone but
    the claim about the corpus stays, and the rendered report carries it.
    Same two corpora, both orders: each one keeps its own recommendations.
    """
    corpus_a = _base_result("corpus_A", coherence=0.5, semantic=0.25)
    corpus_b = _base_result("corpus_B", coherence=0.9, semantic=0.9)

    forward = _analyze_agent_effectiveness([corpus_a, corpus_b], [], pd.DataFrame())
    backward = _analyze_agent_effectiveness([corpus_b, corpus_a], [], pd.DataFrame())

    assert (
        forward["corpus_A"]["recommendations"]
        == backward["corpus_A"]["recommendations"]
    )
    assert (
        forward["corpus_B"]["recommendations"]
        == backward["corpus_B"]["recommendations"]
    )


def test_advanced_only_corpus_exercises_advanced_branch():
    advanced = [
        {
            "corpus_name": "corpus_C",
            "analyses": {
                "contextual_fallacies": {"contextual_fallacies_count": 3},
                "complex_fallacies": {
                    "individual_fallacies_count": 1,
                    "basic_combinations": ["combo1"],
                    "advanced_combinations": [],
                    "fallacy_patterns": [],
                },
                "fallacy_severity": {"overall_severity": 0.7},
                "rhetorical_results": {"overall_analysis": {"rhetorical_quality": 0.8}},
            },
        }
    ]
    effectiveness = _analyze_agent_effectiveness([], advanced, pd.DataFrame())

    entry = effectiveness["corpus_C"]
    assert entry["base_agents"] == {}
    assert set(entry["advanced_agents"]) == ADVANCED_AGENT_KEYS
    assert (
        entry["advanced_agents"]["enhanced_contextual_fallacy_analyzer"][
            "fallacy_count"
        ]
        == 3
    )
    # 1 individual + 1 basic combination
    assert (
        entry["advanced_agents"]["enhanced_complex_fallacy_analyzer"]["fallacy_count"]
        == 2
    )
    # contextual analyzer effectiveness 3.0 dominates complex 2.0, severity 0.7, rhetoric 0.8
    assert entry["best_agent"] == "enhanced_contextual_fallacy_analyzer"
