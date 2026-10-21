"""#3093 — no code path downloads NLTK's cmudict at run time.

textstat's lazy CMUdict loader downloads the corpus on a missing resource
(``quiet=True``), which made ``DebatePlugin()`` — a constructor — a network
dependency: on CI run 39424301617 the fetch failed and the constructor raised
``LookupError`` from a corpus the test never touched. The repair:

* the code never fetches: ``text_scoring`` guards the English instrument with
  a plain ``nltk.data.find`` (no download) and degrades the English Flesch to
  ``None`` with its cause named — French and German (pyphen) are unaffected;
* the corpus is provisioned with the environment, declared in
  ``setup_project_env.ps1`` (step 2.2), idempotent;
* the CI-side provisioning (``.github/actions/setup-projet-is``) is volet A
  (PR #3115), merged under this branch's base — witnessed by
  ``tests/unit/test_setup_action_provisions_cmudict_3093.py``.

These tests read the repair, not the network: ``nltk.download`` is booby-
trapped so any run-time fetch fails loudly inside the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from argumentation_analysis.agents.core import text_scoring

REPO_ROOT = Path(__file__).resolve().parents[5]

FR_TEXT = "Une phrase suffisamment longue pour être mesurée en français."
EN_TEXT = "A reasonably long English sentence to be measured."


@pytest.fixture()
def corpus_absent(monkeypatch):
    """The corpus is not provisioned, and any download attempt explodes.

    ``_CMUDICT_PRESENT`` is forced False (the cache would otherwise read the
    seat's real corpus), ``nltk.data.find`` denies ``corpora/cmudict`` so
    textstat's own lazy loader takes its download branch on a provisioned
    seat too, and ``nltk.download`` raises: the guard must keep every code
    path away from that branch.
    """
    import nltk

    real_find = nltk.data.find

    def find_without_cmudict(resource_name, *args, **kwargs):
        if str(resource_name).endswith("cmudict"):
            raise LookupError(f"Resource '{resource_name}' not found. (fixture)")
        return real_find(resource_name, *args, **kwargs)

    monkeypatch.setattr(text_scoring, "_CMUDICT_PRESENT", False)
    monkeypatch.setattr(nltk.data, "find", find_without_cmudict)
    monkeypatch.setattr(
        nltk,
        "download",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("run-time nltk.download reached (#3093)")
        ),
    )
    monkeypatch.setattr(text_scoring, "_WARMED", False)
    monkeypatch.setattr(text_scoring, "_DEGRADED", {})
    yield


class TestNoRunTimeDownload:
    def test_warm_up_degrades_instead_of_downloading(self, corpus_absent):
        text_scoring.warm_up()  # must not raise — the incident's path

        assert text_scoring.degraded_reason("en") == "cmudict-missing"
        assert text_scoring._DEGRADED.get("en") == "cmudict-missing"

    def test_english_flesch_is_none_with_its_cause_named(self, corpus_absent):
        score, lang = text_scoring.flesch_reading_ease_for(EN_TEXT, lang="en")
        assert score is None
        assert lang == "en"
        assert text_scoring.degraded_reason("en") == "cmudict-missing"

    def test_french_and_german_are_unaffected(self, corpus_absent):
        fr_score, fr_lang = text_scoring.flesch_reading_ease_for(FR_TEXT, lang="fr")
        de_score, de_lang = text_scoring.flesch_reading_ease_for(
            "Dies ist ein hinreichend langer deutscher Satz.", lang="de"
        )
        assert fr_score is not None and fr_lang == "fr"
        assert de_score is not None and de_lang == "de"
        assert text_scoring.degraded_reason("fr") is None

    def test_the_incidents_constructor_never_touches_the_network(self, corpus_absent):
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebatePlugin,
        )

        plugin = DebatePlugin()  # CI run 39424301617 raised here

        assert plugin.analyzer is not None

    @pytest.mark.skipif(
        text_scoring.cmudict_available(),
        reason="corpus provisioned on this seat — the absent case is the repair",
    )
    def test_guard_runs_without_the_fixture_too(self):
        text_scoring.warm_up()
        assert text_scoring.flesch_reading_ease_for(EN_TEXT, lang="en") == (
            None,
            "en",
        )


class TestConsumersCarryTheDegrade:
    """Both production consumers of the English Flesch honor the None (#1019).

    Census (this repo, #3093): two production consumers read
    ``flesch_reading_ease_for`` — the debate scorer
    (``debate_scoring.ArgumentAnalyzer``) and the quality evaluator
    (``quality_evaluator.detect_clarte``). Each is witnessed here on the
    corpus-absent seat: the metric is honestly None / a named degrade, and
    the aggregate renormalizes over what was measured — never a silent
    heuristic substitute.
    """

    def test_debate_readability_is_none_and_persuasiveness_renormalizes(
        self, corpus_absent
    ):
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            ArgumentType,
            DebatePhase,
            EnhancedArgument,
        )
        from argumentation_analysis.agents.core.debate.debate_scoring import (
            ArgumentAnalyzer,
        )

        analyzer = ArgumentAnalyzer()
        assert analyzer._assess_readability(EN_TEXT, lang="en") is None

        arg = EnhancedArgument(
            agent_name="Alice",
            position="for",
            content=EN_TEXT,
            argument_type=ArgumentType.CLAIM,
            timestamp="2025-01-01T00:00:00",
            phase=DebatePhase.MAIN_ARGUMENTS,
        )
        metrics = analyzer.analyze_argument(arg, [], lang="en")
        assert metrics.readability_score is None  # not computed, not substituted
        # The weighted combo drops the 0.15 readability weight and
        # renormalizes over the 0.60 that was actually measured.
        expected = min(
            (
                metrics.logical_coherence * 0.25
                + metrics.evidence_quality * 0.25
                + metrics.fact_check_score * 0.10
            )
            / 0.60,
            1.0,
        )
        assert metrics.persuasiveness == pytest.approx(expected, abs=0.01)

    def test_quality_clarte_degrades_with_the_cause_named(self, corpus_absent):
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_clarte,
        )

        score, comment = detect_clarte(EN_TEXT, lang="en")
        assert score == 0.5  # neutral, not a measurement
        assert "indisponible" in comment and "cmudict-missing" in comment, comment
        assert "heuristique" not in comment, (
            comment + " — the language IS decided (en); presenting the word-length "
            "heuristic as a measurement is the silent substitute #1019 forbids"
        )

    def test_quality_clarte_keeps_the_heuristic_for_undecidable_language(
        self, corpus_absent
    ):
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_clarte,
        )

        # Counter-pendule: a text with no decidable language keeps the NAMED
        # heuristic even on a degraded seat — the instrument's absence must
        # not widen into "never measure anything".
        _score, comment = detect_clarte("zzqq xxvv. kkww jjff.", lang=None)
        assert "heuristique" in comment, comment


class TestProvisioningIsDeclared:
    def test_setup_script_provisions_the_corpus(self):
        """The provisioning step exists and downloads only when absent."""
        script = (REPO_ROOT / "setup_project_env.ps1").read_text(encoding="utf-8")
        assert "nltk.download('cmudict')" in script, (
            "the corpus must travel with the environment (#3093), not with "
            "a run-time fetch"
        )
        assert "nltk.data.find('corpora/cmudict')" in script, (
            "the step is idempotent: an already-provisioned corpus is not "
            "downloaded again"
        )
