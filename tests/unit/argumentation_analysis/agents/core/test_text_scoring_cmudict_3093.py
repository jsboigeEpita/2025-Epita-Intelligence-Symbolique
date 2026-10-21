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
* the CI-side provisioning (caching the corpus in the gate runner) lives
  under ``.github/`` — named on the issue, not merged here.

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

    def test_ci_side_provisioning_is_named_not_merged(self):
        """The gate runner's cache belongs to .github/ — named, not edited.

        The repair deliberately ships without touching ``.github/``: that
        file family is not merged without the user. This witness pins the
        boundary so a future change there is a conscious one.
        """
        action_dir = REPO_ROOT / ".github" / "actions" / "setup-projet-is"
        if action_dir.exists():
            blob = "\n".join(
                p.read_text(encoding="utf-8", errors="replace")
                for p in action_dir.rglob("*")
                if p.is_file()
            )
            assert "cmudict" not in blob
