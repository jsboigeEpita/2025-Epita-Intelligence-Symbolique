"""
Tests for the Argument Quality Evaluator (integrated from 2.3.5).

Tests validate:
- Module import without errors
- CapabilityRegistry registration
- Individual virtue detectors
- Full evaluation pipeline
- DLL failure raises RuntimeError (fail-loud, #1019)
"""

import pytest
from unittest.mock import patch

import argumentation_analysis.agents.core.quality.quality_evaluator as qmod


# In the test process, jpype may already be loaded (conftest.py), so
# importing spacy can trigger the WinError 182 DLL conflict.  The tests
# that exercise the real evaluator need a safe _load_deps that either
# succeeds (spacy available) or gracefully sets fallback state.
@pytest.fixture(autouse=True)
def _safe_load_deps(request):
    """Ensure _load_deps doesn't crash the test process with DLL errors.

    If spacy/textstat are already loaded, leave them in place.
    If not, mock _load_deps to set the fallback globals without
    triggering the DLL crash.

    Skipped for tests in TestDllFailureFailLoud — those tests need
    the real _load_deps (and mock it themselves per-test).
    """
    # Don't interfere with fail-loud tests that mock _load_deps themselves
    cls = request.node.getparent(pytest.Class)
    if cls is not None and cls.name == "TestDllFailureFailLoud":
        yield
        return

    if qmod._DEPS_AVAILABLE:
        # Already loaded (e.g. conftest loaded torch first) — use real deps
        yield
        return

    # spacy not yet loaded — mock _load_deps to avoid DLL crash
    saved = qmod._load_deps

    def _mock_load_deps():
        """Mark deps as "available" (per-detector heuristics still work)
        without actually importing spacy.

        _DEPS_AVAILABLE=True so the early gate in evaluate() passes.
        _nlp=None / _flesch_reading_ease=None so individual detectors
        use their built-in heuristics (word length, sentence counting, etc.)
        """
        qmod._nlp = None
        qmod._flesch_reading_ease = None
        qmod._DEPS_AVAILABLE = True
        qmod._DEPS_ATTEMPTED = True
        return True

    qmod._load_deps = _mock_load_deps
    try:
        yield
    finally:
        qmod._load_deps = saved


class TestQualityImport:
    """Test that the quality module can be imported."""

    def test_import_module(self):
        """Quality module imports without errors."""
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
            VERTUES,
            evaluer_argument,
        )

        assert ArgumentQualityEvaluator is not None
        assert len(VERTUES) == 9
        assert callable(evaluer_argument)

    def test_import_detectors(self):
        """Individual detectors are importable."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            DETECTORS,
        )

        assert len(DETECTORS) == 9
        for name in [
            "clarte",
            "pertinence",
            "presence_sources",
            "refutation_constructive",
            "structure_logique",
            "analogie_pertinente",
            "fiabilite_sources",
            "exhaustivite",
            "redondance_faible",
        ]:
            assert name in DETECTORS


class TestQualityRegistration:
    """Test CapabilityRegistry registration."""

    def test_register_quality_evaluator(self):
        """Quality evaluator registers correctly in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            "quality_evaluator",
            ArgumentQualityEvaluator,
            capabilities=["argument_quality", "virtue_scoring"],
        )

        agents = registry.find_agents_for_capability("argument_quality")
        assert len(agents) == 1
        assert agents[0].name == "quality_evaluator"

    def test_provides_declared_capabilities(self):
        """Quality evaluator provides the capabilities it declares."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            "quality_evaluator",
            ArgumentQualityEvaluator,
            capabilities=["argument_quality", "virtue_scoring"],
        )

        all_caps = registry.get_all_capabilities()
        assert "argument_quality" in all_caps
        assert "virtue_scoring" in all_caps


class TestVirtueDetectors:
    """Test individual virtue detectors."""

    def test_detect_presence_sources_found(self):
        """Source detector finds citations."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_presence_sources,
        )

        text = (
            "Selon Dupont (2019), les résultats montrent que d'après Martin (2020) ..."
        )
        score, comment = detect_presence_sources(text)
        assert score >= 0.5
        assert "source" in comment.lower()

    def test_detect_presence_sources_none(self):
        """Source detector handles text without citations."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_presence_sources,
        )

        text = "Les choses vont mal et tout est compliqué."
        score, comment = detect_presence_sources(text)
        assert score == 0.0

    def test_detect_refutation_markers(self):
        """Refutation detector finds constructive opposition markers."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_refutation_constructive,
        )

        text = "Certains pensent que les renouvelables sont coûteuses, cependant les prix baissent."
        score, comment = detect_refutation_constructive(text)
        assert score == 1.0

    def test_detect_analogie(self):
        """Analogy detector finds comparison patterns."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_analogie_pertinente,
        )

        text = "La transition est comparable à la révolution industrielle, tout comme le numérique transforme."
        score, comment = detect_analogie_pertinente(text)
        assert score == 1.0

    def test_detect_fiabilite_sources(self):
        """Source credibility detector finds known sources."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_fiabilite_sources,
        )

        text = "Selon l'OMS, les campagnes de vaccination sont essentielles."
        score, comment = detect_fiabilite_sources(text)
        assert score == 1.0

    def test_detect_structure_logique(self):
        """Structure detector finds logical connectors."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_structure_logique,
        )

        text = "Les abeilles sont essentielles car elles pollinisent. Donc la production dépend d'elles."
        score, comment = detect_structure_logique(text)
        assert score == 1.0

    def test_detect_redondance_faible(self):
        """Redundancy detector evaluates word uniqueness ratio."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_redondance_faible,
        )

        # High diversity text
        text = "Les énergies renouvelables transforment notre avenir économique et environnemental."
        score, _ = detect_redondance_faible(text)
        assert score >= 0.5

    def test_detect_redondance_faible_redundant(self):
        """Redundancy detector catches highly redundant text."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_redondance_faible,
        )

        # Very redundant text
        text = "bon bon bon bon bon bon bon bon bon bon bon bon"
        score, _ = detect_redondance_faible(text)
        assert score <= 0.5


class TestFullEvaluation:
    """Test the full evaluation pipeline."""

    def test_evaluate_high_quality(self):
        """High-quality text gets a high score."""
        from argumentation_analysis.agents.core.quality import evaluer_argument

        text = (
            "Selon un rapport de l'Agence Internationale de l'Énergie (2023), "
            "les énergies renouvelables sont cruciales pour lutter contre le "
            "changement climatique, car elles réduisent les émissions de CO2. "
            "Par exemple, remplacer les centrales à charbon par des parcs solaires "
            "permettrait de diminuer drastiquement la pollution, tout comme remplacer "
            "une vieille chaudière par une pompe à chaleur moderne. "
            "Certains affirment que les renouvelables sont peu fiables, cependant, "
            "des avancées dans le stockage d'énergie réfutent cette idée. "
            "En effet, les batteries lithium-ion et les réseaux intelligents "
            "compensent les variations. De plus, l'ensemble des données montre "
            "une tendance globale à la baisse des coûts. "
            "Ainsi, la transition énergétique est non seulement possible, mais nécessaire."
        )
        result = evaluer_argument(text)

        assert "note_finale" in result
        assert "note_moyenne" in result
        assert "scores_par_vertu" in result
        assert "rapport_detaille" in result
        assert len(result["scores_par_vertu"]) == 9
        # High quality text should score well
        assert result["note_moyenne"] > 0.5

    def test_evaluate_low_quality(self):
        """Low-quality text gets a low score."""
        from argumentation_analysis.agents.core.quality import evaluer_argument

        text = "Manger des légumes est bon. C'est pourquoi les voitures polluent."
        result = evaluer_argument(text)

        assert result["note_finale"] < 5.0
        assert result["note_moyenne"] < 0.6

    def test_evaluate_returns_all_virtues(self):
        """Evaluation always returns all 9 virtues."""
        from argumentation_analysis.agents.core.quality import (
            evaluer_argument,
            VERTUES,
        )

        result = evaluer_argument("Un texte quelconque.")
        for vertu in VERTUES:
            assert vertu in result["scores_par_vertu"]
            assert vertu in result["rapport_detaille"]

    def test_evaluator_class_api(self):
        """ArgumentQualityEvaluator class has correct API."""
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
        )

        evaluator = ArgumentQualityEvaluator()
        result = evaluator.evaluate("Selon l'OMS, la santé est un droit fondamental.")
        assert isinstance(result, dict)
        assert "note_finale" in result


class TestDllFailureFailLoud:
    """Test that DLL failures raise RuntimeError, not silent fallback (#1019).

    Previously (#993), the evaluator silently fell back to regex heuristics
    and set a ``degraded`` flag.  The #1019 mandate requires fail-loud:
    if spacy/textstat cannot load, raise RuntimeError so the root cause
    (DLL load order) must be fixed instead of masked.
    """

    def test_dll_failure_raises_runtime_error(self):
        """When spacy import raises OSError (WinError 182), RuntimeError is raised.

        _load_deps() raises RuntimeError directly when spacy/textstat cannot
        be imported (e.g. torch DLL conflict on Windows).
        """
        import argumentation_analysis.agents.core.quality.quality_evaluator as qmod

        # Reset global state to force re-import attempt
        qmod._DEPS_ATTEMPTED = False
        qmod._DEPS_AVAILABLE = False
        qmod._nlp = None
        qmod._flesch_reading_ease = None

        # Patch both spacy AND textstat to simulate full DLL failure
        with patch.dict("sys.modules", {"spacy": None, "textstat": None}):
            # Force re-evaluation
            qmod._DEPS_ATTEMPTED = False
            qmod._DEPS_AVAILABLE = False

            with pytest.raises(RuntimeError, match="spacy"):
                qmod._load_deps()

        # Reset for other tests
        qmod._DEPS_ATTEMPTED = False
        qmod._DEPS_AVAILABLE = False

    def test_evaluate_raises_runtime_error_when_deps_unavailable(self):
        """evaluate() raises RuntimeError early when deps are unavailable (NanoClaw #1026).

        Previously, evaluate() caught RuntimeError per-detector → score 0.0,
        functionally identical to the silent fallback #1019 forbids. Now it
        raises before entering the detector loop.
        """
        import argumentation_analysis.agents.core.quality.quality_evaluator as qmod
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
        )

        saved_attempted = qmod._DEPS_ATTEMPTED
        saved_available = qmod._DEPS_AVAILABLE

        try:
            # Simulate: deps were attempted and failed
            qmod._DEPS_ATTEMPTED = True
            qmod._DEPS_AVAILABLE = False

            evaluator = ArgumentQualityEvaluator()
            with pytest.raises(RuntimeError, match="spacy/textstat"):
                evaluator.evaluate("Un texte quelconque.")
        finally:
            qmod._DEPS_ATTEMPTED = saved_attempted
            qmod._DEPS_AVAILABLE = saved_available

    def test_evaluer_argument_raises_runtime_error_when_deps_unavailable(self):
        """evaluer_argument() propagates RuntimeError from evaluate()."""
        import argumentation_analysis.agents.core.quality.quality_evaluator as qmod
        from argumentation_analysis.agents.core.quality import evaluer_argument

        saved_attempted = qmod._DEPS_ATTEMPTED
        saved_available = qmod._DEPS_AVAILABLE

        try:
            qmod._DEPS_ATTEMPTED = True
            qmod._DEPS_AVAILABLE = False

            with pytest.raises(RuntimeError, match="spacy/textstat"):
                evaluer_argument("Un texte quelconque.")
        finally:
            qmod._DEPS_ATTEMPTED = saved_attempted
            qmod._DEPS_AVAILABLE = saved_available

    def test_no_degraded_flag_in_normal_result(self):
        """Normal evaluation result does not contain degraded flag (#1019)."""
        from argumentation_analysis.agents.core.quality import evaluer_argument

        result = evaluer_argument("Selon l'OMS, la santé est fondamentale.")
        assert "degraded" not in result
        assert "degraded_reason" not in result
