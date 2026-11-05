"""#3425 — an unlisted language is not a French document.

Cycle 1 measured it on the panel: the document in a third language came back
``fr`` from ``_detect_language``, and 13 spans its render translated were
degraded as ``unverified`` instead of ``translation``. The heuristic returns
the arg-max of three marker counts as soon as the best count reaches 3, so a
long text in a language it does not list wins by a few short words that
collide with FR markers (``de``, ``du``, ``se``, ``la``).

The repair is a COVERAGE floor plus a second answer:

* the winning list must cover at least ``LANGUAGE_COVERAGE_FLOOR`` of the
  probe's word tokens — measured 0.201 as the floor among the real languages
  of the panel, 0.016 on the mislabelled document;
* below it the answer is ``UNLISTED_LANGUAGE`` ("a probe long enough, which
  no list covers"), NOT ``UNKNOWN_LANGUAGE`` ("too little text to tell") —
  and only the first licenses ``translation`` in ``quote_fidelity``.

No fourth marker list: a fourth list would move the defect to the fifth
language, the floor is what makes the answer honest.

Born red on ``c6e25c2e1``: neither constant exists, and the synthetic
fourth-language text below is labelled ``fr``.
"""

import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from argumentation_analysis.agents.core import text_scoring
from argumentation_analysis.agents.core.text_scoring import (
    SUPPORTED_LANGUAGES,
    UNKNOWN_LANGUAGE,
    UNLISTED_LANGUAGE,
    detect_language,
)
from argumentation_analysis.orchestration.conversational_orchestrator import (
    LANGUAGE_COVERAGE_FLOOR,
    _LANGUAGE_PROBE_WINDOW,
    _detect_language,
)
from argumentation_analysis.reporting.restitution import quote_fidelity

# --- fixtures -------------------------------------------------------------

# Invented vocabulary chosen so that NO word collides with a DE/FR/EN marker:
# the text carries no real language at all.
_INVENTED = (
    "keld",
    "grast",
    "mondo",
    "thur",
    "varn",
    "osprev",
    "pral",
    "nev",
    "brakh",
    "telm",
    "sorv",
    "drenn",
    "quast",
    "morn",
    "veln",
    "harn",
    "stupf",
    "glarn",
)

#: The shape the panel measured on its third-language document: fr 7, de 6,
#: en 6 — three counts within one of each other, on a long probe.
_PLANTED = {
    # French markers: 7
    13: "de",
    113: "de",
    223: "la",
    327: "de",
    423: "se",
    489: "de",
    505: "de",
    # German markers: 6
    41: "der",
    151: "die",
    259: "der",
    359: "die",
    447: "der",
    499: "der",
    # English markers: 6
    79: "in",
    187: "as",
    293: "on",
    391: "in",
    471: "as",
    497: "on",
}


def _fourth_language_text(tokens: int = 600) -> str:
    """A ~3 200-character text in no listed language (#3425)."""
    words = []
    for i in range(tokens):
        words.append(_PLANTED.get(i) or _INVENTED[i % len(_INVENTED)])
    return " ".join(words)


FR_TEXT = (
    "Le peuple de cette nation est uni par des valeurs communes. "
    "Les citoyens ont le droit de s'exprimer librement. Dans cette "
    "république, nous célébrons la liberté et l'égalité. Il est "
    "essentiel que nous continuions à construire une société juste. "
) * 3
EN_TEXT = (
    "The people of this great nation are united by common values. We have "
    "the right to express ourselves freely. In this republic, we celebrate "
    "freedom and equality. It is essential that we continue to build a just "
    "society for all citizens of our country. "
) * 3
DE_TEXT = (
    "Der Staat ist die Grundlage der Ordnung und das Volk muss mit Vernunft "
    "handeln. Eine starke Wirtschaft ist der Schlüssel und die Politik wird "
    "durch klare Regeln bestimmt. Wir sind für den Fortschritt. "
) * 3

SHORT_FR = "Ceci est un texte français et clair."
FORTY_FR = "Le texte est court mais il est bien en français."


def _coverage(text: str) -> float:
    """The production share: the winning list's coverage of the probe.

    Delegates to the producer's own measure — a witness that recounted the
    markers itself would be measuring its own arithmetic, not the detector.
    """
    from argumentation_analysis.core.reading_window import selected_text
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        language_coverage,
    )

    sample = selected_text(text, _LANGUAGE_PROBE_WINDOW, "detect_language")
    return max(language_coverage(sample).values())


class TestTheUnknownLanguageIsNoLongerCalledFrench:
    def test_a_fourth_language_reads_as_unlisted(self):
        text = _fourth_language_text()
        assert len(text) >= 3000, "the witness must be the size the issue names"
        assert _detect_language(text) == UNLISTED_LANGUAGE

    def test_the_answer_travels_through_the_repository_probe(self):
        assert detect_language(_fourth_language_text()) == UNLISTED_LANGUAGE

    def test_the_floor_is_calibrated_between_the_measured_populations(self):
        """The constant sits between 0.016 (unlisted) and 0.201 (lowest real).

        A floor lowered under the mislabelled document would let it back in; a
        floor raised over 0.201 would eat a real language. Both ends are
        measured numbers, not chosen ones.
        """
        assert 0.016 < LANGUAGE_COVERAGE_FLOOR < 0.201
        assert _coverage(_fourth_language_text()) < LANGUAGE_COVERAGE_FLOOR

    def test_a_document_with_a_long_neutral_header_keeps_its_language(self):
        """The third measured population: #3389's twin-document geometry.

        A 2 000-character shared header no function word populates, then
        French/English prose — the shape that reproduces the R1141 regression
        (a language inherited across twins cut from one source). Its measured
        coverage is 0.068, so the floor must stay under it: a constant chosen
        to sit above would have turned a real witness into a false unlisted.
        """
        header = ("qwvk zrn mpxl btf gjd wzs " * 100)[:2000]
        french = (
            header
            + (
                "Le comité invite les participants à se rendre dans la salle "
                "commune avant midi. Le secrétariat rappelle que les documents "
                "préparatoires restent consultables au bureau de la délégation. "
                "Aucune décision ne sera prise sans quorum. La presidente de la "
                "séance précise que les échanges restent limités aux points "
                "inscrits pour l'ordre du jour de la session."
            )
            * 2
        )
        english = (
            header
            + (
                "The committee invites the participants to gather in the common "
                "room before noon. The secretariat recalls that the preparatory "
                "documents stay available at the office of the delegation. No "
                "decision will be taken without a quorum. The chairperson states "
                "that the exchanges remain limited to the items listed on the "
                "agenda of the session."
            )
            * 2
        )
        assert _coverage(french) < 0.08  # the measurement that moved the floor
        assert _coverage(french) > LANGUAGE_COVERAGE_FLOOR
        assert (_detect_language(french), _detect_language(english)) == ("fr", "en")


class TestARealLanguageKeepsItsLabel:
    @pytest.mark.parametrize(
        "text,expected", [(FR_TEXT, "fr"), (EN_TEXT, "en"), (DE_TEXT, "de")]
    )
    def test_the_three_listed_languages_are_untouched(self, text, expected):
        assert _detect_language(text) == expected
        assert _coverage(text) >= LANGUAGE_COVERAGE_FLOOR

    def test_a_short_french_text_stays_as_today(self):
        """The floor must not eat short texts: 7–10 word tokens, measured.

        Their coverage is 0.4+ precisely because a short sentence is dense in
        function words — the reason a SHARE, not a count, is the right gate.
        """
        assert len(SHORT_FR) < 40 and len(FORTY_FR) < 50
        assert _detect_language(SHORT_FR) == "fr"
        assert _detect_language(FORTY_FR) == "fr"
        assert _coverage(SHORT_FR) > LANGUAGE_COVERAGE_FLOOR
        assert _coverage(FORTY_FR) > LANGUAGE_COVERAGE_FLOOR

    def test_the_two_no_language_answers_are_different_facts(self):
        assert _detect_language("Hi") == UNKNOWN_LANGUAGE
        assert _detect_language("") == UNKNOWN_LANGUAGE
        assert _detect_language("123 456 789") == UNKNOWN_LANGUAGE
        assert UNKNOWN_LANGUAGE != UNLISTED_LANGUAGE
        assert UNLISTED_LANGUAGE not in SUPPORTED_LANGUAGES


class TestTheConsumersReadTheNewAnswer:
    def test_an_unlisted_document_licenses_translation(self):
        document = _fourth_language_text()
        span = "Une phrase française absente du document d'origine."
        assert quote_fidelity.document_language(document) == UNLISTED_LANGUAGE
        assert (
            quote_fidelity.classify_span(span, document) == quote_fidelity.TRANSLATION
        )

    def test_an_unknown_document_licenses_nothing(self):
        """Anti-#1019: too thin a probe is not a proven translation."""
        assert quote_fidelity.document_language("Hi") == UNKNOWN_LANGUAGE
        assert (
            quote_fidelity.classify_span("Une phrase.", "Hi")
            == quote_fidelity.UNVERIFIED
        )

    def test_no_language_bound_instrument_runs_on_an_unlisted_document(self):
        document = _fourth_language_text()
        lang = detect_language(document)
        assert lang not in SUPPORTED_LANGUAGES
        score, used = text_scoring.flesch_reading_ease_for(document, lang=lang)
        assert score is None and used == UNLISTED_LANGUAGE

    async def test_the_extraction_prompt_gets_no_language_clause(self):
        """No clause at all — a false "in French" is worse than silence."""
        import argumentation_analysis.orchestration.invoke_callables as mod

        async def _system_for(text):
            capture = {}

            async def _create(*args, **kwargs):
                capture["messages"] = kwargs.get("messages", [])
                msg = SimpleNamespace(
                    content='{"arguments": [], "claims": [], "summary": "ok"}'
                )
                return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

            client = SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=_create))
            )
            with patch.object(
                mod, "_get_openai_client", return_value=(client, "model-x")
            ):
                await mod._invoke_fact_extraction(text, {})
            return next(
                (m["content"] for m in capture["messages"] if m["role"] == "system"),
                "",
            )

        unlisted = await _system_for(_fourth_language_text())
        french = await _system_for(FR_TEXT)
        # No false statement about the language in the unlisted case...
        assert "The source text is in" not in unlisted
        assert "original language" not in unlisted
        # ...while a real French document keeps its clause (the control: the
        # silence is caused by the answer, not by the clause disappearing).
        assert "The source text is in French." in french

    def test_debate_scoring_degrades_to_its_union(self):
        from argumentation_analysis.agents.core.debate.debate_scoring import (
            ArgumentAnalyzer,
        )

        scorer = ArgumentAnalyzer()
        unlisted = scorer._assess_evidence_quality(
            _fourth_language_text(), lang=UNLISTED_LANGUAGE
        )
        union = scorer._assess_evidence_quality(
            _fourth_language_text(), lang="xx-not-a-language"
        )
        assert unlisted == union


class TestTheProbeWindowIsTheSameMeaning:
    def test_the_probe_window_is_not_the_extraction_window(self):
        """#2915's rule holds: the detector's window is its own meaning."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _LANGUAGE_PROBE_WINDOW,
        )

        assert _LANGUAGE_PROBE_WINDOW == 3000
