"""Né-rouge guard for #2097 — the analyzer must build its AnalysisService for real.

Measured on the pristine tree (base ``14fbe867``): ``_init_components`` called
``AnalysisService()`` with no argument while the constructor requires the
``llm_service`` positional (``analysis_service.py:82``) — the TypeError was
swallowed by the surrounding try/except and the analyzer silently reported
``analysis_service=None`` ("mode dégradé") on every seat, healthy or not.

The sibling suite ``test_argumentation_analyzer.py`` exercises degraded mode
behind an autouse fixture that forces the constructor to fail — it observes the
failure, not its absence. This guard observes the healthy path: under pytest
``create_llm_service`` returns a ``MockChatCompletion`` (llm_service.py:234),
so the real chain must construct.
"""

from argumentation_analysis.core.argumentation_analyzer import ArgumentationAnalyzer


def test_analyzer_builds_its_analysis_service_2097():
    analyzer = ArgumentationAnalyzer()
    assert analyzer.analysis_service is not None, (
        "ArgumentationAnalyzer degraded silently: AnalysisService was not "
        "constructed — the naked ctor call raised TypeError, swallowed by "
        "_init_components' except (#2097)"
    )


def test_analyzer_builds_its_pipeline_2097():
    """The swallowed TypeError also reset the pipeline to None — both must stand."""
    analyzer = ArgumentationAnalyzer()
    assert analyzer.pipeline is not None, (
        "the pipeline was constructed then discarded by the same except clause "
        "that swallowed the AnalysisService TypeError (#2097)"
    )


def test_analyzer_reaches_the_service_on_analyze_2097():
    """The chain must work end-to-end, not just construct.

    The real service exposes ``async analyze_text(AnalysisRequest)`` — the
    old facade call ``(text, dict)`` raised TypeError at first use (#2097):
    the failure moved from boot to first call, the exact pattern #1864
    forbids. ``enable_logic_analysis=False`` keeps the informal-only pipeline
    off the JVM; under pytest the LLM is a MockChatCompletion and the service
    answers (healthy or fallback), so the facade must carry its result.
    """
    analyzer = ArgumentationAnalyzer(config={"enable_logic_analysis": False})
    result = analyzer.analyze_text("Ce texte avance une thèse et une raison.")
    assert "service" in result["analysis"], (
        "the constructed AnalysisService was never reached: the facade call "
        "signature still mismatches the service contract (#2097)"
    )
