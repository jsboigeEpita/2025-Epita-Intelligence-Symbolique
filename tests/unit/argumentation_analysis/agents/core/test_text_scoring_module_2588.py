"""#2588 — the text_scoring module: per-language measuring instruments."""

from argumentation_analysis.agents.core import text_scoring

FR_MID = (
    "La vaccination est un outil essentiel de santé publique, car les études "
    "montrent qu'elle réduit la propagation des maladies et protège les plus "
    "fragiles, même si certains doutes persistent dans la population."
)


class TestDetectLanguage:
    def test_delegates_to_the_orchestrator_heuristic(self):
        assert (
            text_scoring.detect_language("Ceci est un texte français et clair.") == "fr"
        )
        assert (
            text_scoring.detect_language(
                "Dies ist ein deutscher Text mit klaren Worten."
            )
            == "de"
        )
        assert (
            text_scoring.detect_language("This is an English text with clear words.")
            == "en"
        )
        assert text_scoring.detect_language("zzqq xxvv kkww jjff.") == "unknown"


class TestFleschPerLanguage:
    def test_returns_score_and_language(self):
        score, lang = text_scoring.flesch_reading_ease_for(FR_MID)
        assert lang == "fr"
        assert score is not None

    def test_explicit_language_overrides_detection(self):
        score, lang = text_scoring.flesch_reading_ease_for(FR_MID, lang="en")
        assert lang == "en"

    def test_unknown_language_returns_none(self):
        score, lang = text_scoring.flesch_reading_ease_for("zzqq xxvv kkww jjff.")
        assert score is None
        assert lang == "unknown"

    def test_french_and_english_rules_disagree_on_french_text(self):
        fr_score, _ = text_scoring.flesch_reading_ease_for(FR_MID, lang="fr")
        en_score, _ = text_scoring.flesch_reading_ease_for(FR_MID, lang="en")
        assert fr_score != en_score


class TestInstanceIsolation:
    def test_default_textstat_instance_stays_english(self):
        # The dedicated per-language instances must not flip the process-wide
        # default: a shared ``set_lang`` would silently re-language every other
        # textstat caller (quality_evaluator warms the default instance).
        from textstat import flesch_reading_ease as default_flesch

        before = default_flesch(FR_MID)
        text_scoring.flesch_reading_ease_for(FR_MID, lang="fr")
        text_scoring.flesch_reading_ease_for("Dies ist ein deutscher Satz.", lang="de")
        assert default_flesch(FR_MID) == before


class TestWarmUp:
    def test_warm_up_is_idempotent(self):
        text_scoring.warm_up()
        text_scoring.warm_up()
        score, lang = text_scoring.flesch_reading_ease_for(FR_MID)
        assert lang == "fr"
        assert score is not None
