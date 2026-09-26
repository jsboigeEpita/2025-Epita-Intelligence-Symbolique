"""#2675 — the French model the quality evaluator declares REQUIRED is required.

The module has always documented ``fr_core_news_sm`` as REQUIRED and a load
failure as a RuntimeError. The loader nevertheless caught the model's
``OSError`` apart from every other failure, logged a warning and went on with
``_nlp = None``: the detectors then tokenised by regex and returned DIFFERENT
scores, and no field of the result said so. That is how CI once computed
replay keys that existed nowhere (#2320 — the comment on the model pin in
``environment.yml``), and how the #2353 lexical arm rendered differently from
one seat to the next.

Pinned here, with the real ``spacy.load`` made to fail the way it does when the
model is not installed ([E050]):

1. the load raises RuntimeError naming the model, and records the cause for
   the later gates (#2320);
2. the detectors that tokenise do not score by regex on the way: the first
   unit records them UNAVAILABLE with the cause, and every later unit is
   refused — the #1907 outage state and the #1019 gate, as for any load
   failure;
3. control: with the model installed the same load succeeds and hands the
   detectors a real pipeline, so what reddens 1-2 is the missing model alone.
"""

import spacy
import pytest

from argumentation_analysis.agents.core.quality import quality_evaluator as qe

_E050 = (
    "[E050] Can't find model 'fr_core_news_sm'. It doesn't seem to be a "
    "Python package or a valid path to a data directory."
)

_TEXT = (
    "Il faut investir dans les transports publics, car ils réduisent la "
    "pollution. En effet, chaque bus remplace plusieurs voitures. Certains "
    "objectent que le coût est élevé ; pourtant, les économies de santé le "
    "compensent."
)

# The detectors that call the loader. pertinence, exhaustivite and
# redondance_faible read the model and fell back to regex tokenisation without
# it; clarte calls the loader for textstat.
_LOADER_DETECTORS = {"clarte", "pertinence", "exhaustivite", "redondance_faible"}


def _judged(result):
    """Status of each loader detector the unit was applicable to."""
    statuses = result["statuts_par_vertu"]
    return {
        v: statuses[v]
        for v in _LOADER_DETECTORS
        if statuses.get(v) not in (None, qe.VirtueStatus.NOT_APPLICABLE)
    }


@pytest.fixture
def cold_deps(monkeypatch):
    """The process state before any unit has loaded the dependencies."""
    monkeypatch.setattr(qe, "_DEPS_ATTEMPTED", False)
    monkeypatch.setattr(qe, "_DEPS_AVAILABLE", False)
    monkeypatch.setattr(qe, "_LAST_LOAD_ERROR", None)
    monkeypatch.setattr(qe, "_nlp", None)


@pytest.fixture
def model_missing(monkeypatch):
    def _load(name, *args, **kwargs):
        raise OSError(_E050)

    monkeypatch.setattr(spacy, "load", _load)


def test_a_missing_model_fails_the_load_and_names_it(cold_deps, model_missing):
    with pytest.raises(RuntimeError, match="fr_core_news_sm"):
        qe._load_deps()
    assert qe._DEPS_AVAILABLE is False
    assert qe._LAST_LOAD_ERROR.startswith("OSError: [E050]")


def test_the_detectors_do_not_score_by_regex_without_the_model(
    cold_deps, model_missing
):
    first = qe.ArgumentQualityEvaluator().evaluate(_TEXT)
    loader = _judged(first)
    assert "pertinence" in loader, loader
    assert set(loader.values()) == {qe.VirtueStatus.UNAVAILABLE}, loader
    for vertu in loader:
        assert "fr_core_news_sm" in first["rapport_detaille"][vertu]

    with pytest.raises(RuntimeError, match=r"First load failure: OSError: \[E050\]"):
        qe.ArgumentQualityEvaluator().evaluate(_TEXT)


def test_control_the_installed_model_loads_a_real_pipeline(cold_deps):
    assert qe._load_deps() is True
    assert qe._nlp is not None
    assert qe._nlp.lang == "fr"
    judged = _judged(qe.ArgumentQualityEvaluator().evaluate(_TEXT))
    assert "pertinence" in judged, judged
    assert set(judged.values()) == {qe.VirtueStatus.EVALUATED}, judged
