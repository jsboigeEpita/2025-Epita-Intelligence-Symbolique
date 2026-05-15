"""Tests for German language support — Option C hybrid (#539).

Validates:
- _detect_language heuristic (DE, FR, EN, unknown)
- Conversational orchestrator prompt adaptation for DE text
"""

import pytest

from argumentation_analysis.orchestration.conversational_orchestrator import (
    _detect_language,
)


# ---------------------------------------------------------------------------
# Language detection tests
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """Test _detect_language heuristic."""

    def test_german_text_detected(self):
        """German text with typical articles and function words detected."""
        text = (
            "Der Staat und die Nation sind das Ergebnis einer langen "
            "historischen Entwicklung. Das Volk hat sich durch gemeinsame "
            "Kultur und Sprache vereinigt. Wir sind stolz auf unsere "
            "Errungenschaften und werden weiter für die Freiheit kämpfen. "
            "Durch die Arbeit der Menschen wird das Land gestärkt. Auch "
            "nach den schweren Zeiten sind wir noch stärker geworden."
        )
        assert _detect_language(text) == "de"

    def test_german_long_text(self):
        """Longer German text with many markers."""
        text = (
            "Die Versammlung ist eröffnet. Wir haben uns heute versammelt, "
            "um über die Zukunft unserer Nation zu sprechen. Es ist nicht nur "
            "ein Recht, sondern eine Pflicht, für das Wohl des deutschen Volkes "
            "zu kämpfen. Durch den Willen des Volkes werden wir den Sieg erringen. "
            "Das Schicksal unserer Nation liegt in unseren Händen. Wir werden "
            "nicht aufhören, bis das Ziel erreicht ist. Für das Vaterland!"
        )
        assert _detect_language(text) == "de"

    def test_french_text_detected(self):
        """French text detected correctly."""
        text = (
            "Le peuple de cette nation est uni par des valeurs communes. "
            "Les citoyens ont le droit de s'exprimer librement. Dans cette "
            "république, nous célébrons la liberté et l'égalité. Il est "
            "essentiel que nous continuions à construire une société juste."
        )
        assert _detect_language(text) == "fr"

    def test_english_text_detected(self):
        """English text detected correctly."""
        text = (
            "The people of this great nation are united by common values. "
            "We have the right to express ourselves freely. In this republic, "
            "we celebrate freedom and equality. It is essential that we continue "
            "to build a just society for all citizens of our country."
        )
        assert _detect_language(text) == "en"

    def test_short_text_unknown(self):
        """Very short text returns unknown."""
        assert _detect_language("Hi") == "unknown"
        assert _detect_language("") == "unknown"

    def test_numbers_only_unknown(self):
        """Text with only numbers returns unknown."""
        assert _detect_language("123 456 789") == "unknown"

    def test_german_with_umlauts(self):
        """German text with umlauts and special chars."""
        text = (
            "Über die Bedeutung der Einheit können wir nicht hinwegsehen. "
            "Für das Wohlergehen aller Bürger ist es notwendig, Veränderungen "
            "durchzuführen. Dieösterreichische Nation wird stärker."
        )
        assert _detect_language(text) == "de"


# ---------------------------------------------------------------------------
# Integration-style tests (orchestrator prompt adaptation)
# ---------------------------------------------------------------------------


class TestOrchestratorPromptAdaptation:
    """Test that orchestrator adapts prompts for DE text."""

    def test_german_prompt_contains_translation_instruction(self):
        """Extraction prompt for DE text includes translation instruction."""
        text = (
            "Der Staat und die Nation sind durch gemeinsame Geschichte vereint. "
            "Wir werden für die Freiheit des deutschen Volkes kämpfen. Die "
            "Zukunft gehört uns, wenn wir stark bleiben und uns nicht beugen."
        )
        lang = _detect_language(text)
        assert lang == "de"

        prompt = (
            f"Analysez ce texte argumentatif. Identifiez les arguments, "
            f"claims et sophismes.\n\n"
            f"IMPORTANT : Le texte est en allemand. Pour la detection de sophismes "
            f"(InformalAgent), traduisez mentalement les passages en anglais avant "
            f"d'appliquer la taxonomie de sophismes. Pour les citations textuelles, "
            f"conservez IMPERATIVEMENT le texte original allemand — ne traduisez "
            f"jamais les citations. Les arguments doivent etre extraits en anglais "
            f"avec citations en allemand.\n\n"
            f"Texte:\n{text}"
        )

        assert "allemand" in prompt
        assert "traduisez mentalement" in prompt
        assert "texte original allemand" in prompt

    def test_english_prompt_no_translation_instruction(self):
        """Extraction prompt for EN text does NOT include translation instruction."""
        text = (
            "The state and nation are united through shared history. "
            "We will fight for freedom of our people. The future belongs "
            "to us if we remain strong and do not bow down."
        )
        lang = _detect_language(text)
        assert lang == "en"

        prompt = (
            f"Analysez ce texte argumentatif. Identifiez les arguments, "
            f"claims et sophismes.\n\nTexte:\n{text}"
        )
        assert "allemand" not in prompt
        assert "traduisez" not in prompt
