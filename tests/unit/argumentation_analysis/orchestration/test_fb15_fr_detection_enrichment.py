"""Value-gate tests for FB-15 #1032 — FR analytical detection enrichment.

Verifies that the three enriched FR registers (D3/D6/D7) are detectable
on synthetic French exemplars via the detection pipeline.

Privacy HARD: All exemplars are synthetic — no corpus content, no raw_text.
Anti-pendule: Tests use genuine FR rhetorical patterns, NOT corpus-specific phrases.
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# D3 — Ad-populum élitiste / populiste register
# ---------------------------------------------------------------------------


class TestD3ElitistAdPopulum:
    """Verify elitist ad-populum markers are in the detection vocabulary."""

    def test_elitist_markers_in_contextual_detector(self):
        """Elitist ad-populum markers are registered in contextual fallacy detector."""
        from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
            ContextualFallacyDetector,
        )

        detector = ContextualFallacyDetector()
        fallacies = detector._define_contextual_fallacies()
        pop_markers = fallacies["appel_inapproprié_popularité"]["markers"]

        # D3 elitist keywords must be present
        elitist_keywords = ["éclairé", "compétent", "ceux qui savent", "personnes averties"]
        for kw in elitist_keywords:
            assert kw in pop_markers, (
                f"Elitist keyword '{kw}' missing from popularité markers. "
                f"D3 enrichment not applied."
            )

    def test_elitist_markers_in_yaml_family(self):
        """Elitist ad-populum keywords are in the authority_popularity YAML family."""
        import yaml
        from pathlib import Path

        yaml_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "argumentation_analysis"
            / "plugin_framework"
            / "core"
            / "plugins"
            / "standard"
            / "taxonomy_explorer"
            / "data"
            / "fallacy_families.yaml"
        )

        with open(yaml_path, encoding="utf-8") as f:
            families = yaml.safe_load(f)

        auth_pop = [f for f in families if f["family"] == "authority_popularity"][0]
        keywords = [kw.lower() for kw in auth_pop["keywords"]]
        patterns = [p.lower() for p in auth_pop["patterns"]]

        # D3 elitist keywords
        assert any("élite" in kw or "éclairé" in kw for kw in keywords), (
            "Elitist keywords missing from authority_popularity family keywords"
        )
        assert any("élitiste" in p for p in patterns), (
            "Elitist pattern missing from authority_popularity family patterns"
        )

    def test_elitist_synthetic_exemplar_detected_by_contextual(self):
        """Synthetic elitist ad-populum text triggers contextual detection."""
        from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
            ContextualFallacyDetector,
        )

        detector = ContextualFallacyDetector()

        # Synthetic exemplar — elitist register (NOT from corpus)
        text = (
            "Seules les personnes éclairées comprennent que cette réforme "
            "est nécessaire. Ceux qui s'y opposent ne sont pas compétents "
            "pour en juger."
        )
        context = "Débat sur une réforme politique"

        result = detector.detect_contextual_fallacies(text, context)

        # Should detect popularité fallacy with elitist markers
        detected_types = [f["fallacy_type"] for f in result.get("detected_fallacies", [])]
        assert any("popularité" in t for t in detected_types), (
            f"Expected 'popularité' in detected types, got {detected_types}. "
            f"D3 elitist ad-populum not detected on synthetic exemplar."
        )


# ---------------------------------------------------------------------------
# D6 — Circular reasoning / critical-theory disqualification
# ---------------------------------------------------------------------------


class TestD6CircularDisqualification:
    """Verify critical-theory circular reasoning markers are registered."""

    def test_circular_markers_in_contextual_detector(self):
        """Circular disqualification markers are in contextual fallacy detector."""
        from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
            ContextualFallacyDetector,
        )

        detector = ContextualFallacyDetector()
        fallacies = detector._define_contextual_fallacies()

        assert "disqualification_circulaire" in fallacies, (
            "disqualification_circulaire entry missing from contextual fallacies. "
            "D6 enrichment not applied."
        )

        circ_markers = fallacies["disqualification_circulaire"]["markers"]
        required = ["aveuglé", "sous l'emprise", "refuse de voir"]
        for kw in required:
            assert kw in circ_markers, (
                f"Circular marker '{kw}' missing. D6 enrichment incomplete."
            )

    def test_circular_markers_in_yaml_family(self):
        """Circular reasoning patterns are in false_dilemma_simplification YAML."""
        import yaml
        from pathlib import Path

        yaml_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "argumentation_analysis"
            / "plugin_framework"
            / "core"
            / "plugins"
            / "standard"
            / "taxonomy_explorer"
            / "data"
            / "fallacy_families.yaml"
        )

        with open(yaml_path, encoding="utf-8") as f:
            families = yaml.safe_load(f)

        fds = [f for f in families if f["family"] == "false_dilemma_simplification"][0]
        patterns = [p.lower() for p in fds["patterns"]]
        keywords = [kw.lower() for kw in fds["keywords"]]

        assert any("circularité" in p or "circulaire" in p for p in patterns), (
            "Circular reasoning pattern missing from false_dilemma_simplification"
        )
        assert any("aveuglé" in kw or "emprise" in kw for kw in keywords), (
            "Critical-theory keywords missing from false_dilemma_simplification"
        )

    def test_circular_synthetic_exemplar_detected(self):
        """Synthetic circular disqualification text triggers contextual detection."""
        from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
            ContextualFallacyDetector,
        )

        detector = ContextualFallacyDetector()

        # Synthetic exemplar — critical-theory circularity (NOT from corpus)
        text = (
            "Ceux qui refusent de voir l'évidence sont aveuglés par le système. "
            "Si vous n'êtes pas d'accord, c'est précisément la preuve que vous "
            "êtes sous l'emprise de l'idéologie dominante."
        )
        context = "Débat idéologique"

        result = detector.detect_contextual_fallacies(text, context)

        detected_types = [f["fallacy_type"] for f in result.get("detected_fallacies", [])]
        assert any("circulaire" in t or "disqualification" in t for t in detected_types), (
            f"Expected 'circulaire' or 'disqualification' in detected types, "
            f"got {detected_types}. D6 circular disqualification not detected."
        )


# ---------------------------------------------------------------------------
# D7 — Affective drive→relief emotional appeal
# ---------------------------------------------------------------------------


class TestD7DriveReliefEmotion:
    """Verify drive→relief emotional appeal markers are registered."""

    def test_drive_relief_markers_in_contextual_detector(self):
        """Drive→relief emotional markers are in contextual fallacy detector."""
        from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
            ContextualFallacyDetector,
        )

        detector = ContextualFallacyDetector()
        fallacies = detector._define_contextual_fallacies()
        emo_markers = fallacies["appel_inapproprié_émotion"]["markers"]

        # D7 drive→relief keywords
        drive_relief_keywords = ["crise", "urgence", "soulagement", "salut", "réassurance"]
        for kw in drive_relief_keywords:
            assert kw in emo_markers, (
                f"Drive→relief keyword '{kw}' missing from emotion markers. "
                f"D7 enrichment not applied."
            )

    def test_drive_relief_patterns_in_yaml(self):
        """Drive→relief patterns are in emotional_appeals YAML family."""
        import yaml
        from pathlib import Path

        yaml_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "argumentation_analysis"
            / "plugin_framework"
            / "core"
            / "plugins"
            / "standard"
            / "taxonomy_explorer"
            / "data"
            / "fallacy_families.yaml"
        )

        with open(yaml_path, encoding="utf-8") as f:
            families = yaml.safe_load(f)

        emo = [f for f in families if f["family"] == "emotional_appeals"][0]
        patterns = [p.lower() for p in emo["patterns"]]
        keywords = [kw.lower() for kw in emo["keywords"]]

        assert any("drive" in p or "tension" in p for p in patterns), (
            "Drive→relief pattern missing from emotional_appeals"
        )
        assert any("soulagement" in kw or "crise" in kw for kw in keywords), (
            "Drive→relief keywords missing from emotional_appeals"
        )

    def test_drive_relief_synthetic_exemplar_detected(self):
        """Synthetic drive→relief text triggers contextual detection."""
        from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import (
            ContextualFallacyDetector,
        )

        detector = ContextualFallacyDetector()

        # Synthetic exemplar — drive→relief pattern (NOT from corpus)
        text = (
            "La crise menace notre avenir, l'angoisse grandit chaque jour. "
            "Mais il y a un salut : notre solution apporte le soulagement "
            "immédiat et la réassurance dont vous avez besoin."
        )
        context = "Message politique"

        result = detector.detect_contextual_fallacies(text, context)

        detected_types = [f["fallacy_type"] for f in result.get("detected_fallacies", [])]
        assert any("émotion" in t for t in detected_types), (
            f"Expected 'émotion' in detected types, got {detected_types}. "
            f"D7 drive→relief emotional appeal not detected."
        )


# ---------------------------------------------------------------------------
# LLM prompt enrichment verification
# ---------------------------------------------------------------------------


class TestLLMPromptEnrichment:
    """Verify the LLM system prompt includes D3/D6/D7 sub-categories."""

    def test_prompt_includes_elitist_ad_populum(self):
        """LLM system prompt mentions elitist ad-populum variant."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        prompt = LLMFallacyDetector.SYSTEM_PROMPT.lower()
        assert "éclairé" in prompt or "elitiste" in prompt or "competent" in prompt, (
            "LLM prompt missing elitist ad-populum variant (D3)."
        )

    def test_prompt_includes_circular_disqualification(self):
        """LLM system prompt mentions critical-theory circular variant."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        prompt = LLMFallacyDetector.SYSTEM_PROMPT.lower()
        assert "theorie-critique" in prompt or "disqualifiant" in prompt or "emprise" in prompt, (
            "LLM prompt missing critical-theory circular variant (D6)."
        )

    def test_prompt_includes_drive_relief(self):
        """LLM system prompt mentions drive→relief emotional variant."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        prompt = LLMFallacyDetector.SYSTEM_PROMPT.lower()
        assert "drive" in prompt or "soulagement" in prompt or "tension" in prompt, (
            "LLM prompt missing drive→relief emotional variant (D7)."
        )
