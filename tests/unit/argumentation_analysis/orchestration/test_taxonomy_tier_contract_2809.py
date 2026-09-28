"""The taxonomy tier carries the detector's PK, name and family (#2809).

``_invoke_taxonomy_only_fallacy`` used to read ``key``, which the detector never
writes, so ``taxonomy_pk`` held the popular name, or "" for the rows that have
none (most of them). These tests run the real detector on the tracked taxonomy
and compare the invoker with what the detector returned.
"""

import pytest

POPULAR = "Voici une attaque de l’estime de soi, clairement."


@pytest.fixture(scope="module")
def detector():
    from argumentation_analysis.agents.core.informal.taxonomy_sophism_detector import (
        get_global_detector,
    )

    return get_global_detector()


@pytest.fixture(scope="module")
def unnamed_text(detector):
    """A text that matches a row with no popular name through its keywords."""
    df = detector._get_taxonomy_df()
    unnamed = df[df["nom_vulgarisé"].fillna("").astype(str).str.strip() == ""]
    for _, row in unnamed.iterrows():
        words = [w for w in str(row["text_fr"]).lower().split() if len(w) > 4][:5]
        if len(words) >= 3:
            return "Le discours dit " + " et ".join(words) + "."
    pytest.fail("no taxonomy row without a popular name has three keywords")


async def _both(detector, text):
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_taxonomy_only_fallacy,
    )

    detected = detector.detect_sophisms_from_taxonomy(text)
    result = await _invoke_taxonomy_only_fallacy(text, {})
    return detected, result["fallacies"]


async def test_popular_name_row_keeps_its_pk(detector):
    detected, fallacies = await _both(detector, POPULAR)
    assert detected, "the detector must match its own popular name"
    assert [f["taxonomy_pk"] for f in fallacies] == [
        s["taxonomy_key"] for s in detected
    ]
    assert fallacies[0]["fallacy_type"] == detected[0]["nom_vulgarise"]
    assert fallacies[0]["family"] == detected[0]["famille"]


async def test_unnamed_row_is_named_and_keeps_its_pk(detector, unnamed_text):
    detected, fallacies = await _both(detector, unnamed_text)
    unnamed = [i for i, s in enumerate(detected) if not s["nom_vulgarise"]]
    assert unnamed, "the probe must reach a row without a popular name"
    for i in unnamed:
        assert fallacies[i]["taxonomy_pk"] == detected[i]["taxonomy_key"]
        assert fallacies[i]["fallacy_type"] == detected[i]["description"]
        assert fallacies[i]["fallacy_type"]


async def test_api_resolves_the_taxonomy_row(detector, unnamed_text):
    from api.fallacy_detection import _described, _taxonomy_rows

    for text in (POPULAR, unnamed_text):
        _, fallacies = await _both(detector, text)
        for fallacy in fallacies:
            described = _described(fallacy)
            row = _taxonomy_rows()[str(fallacy["taxonomy_pk"])]
            assert described.taxonomy_pk == str(fallacy["taxonomy_pk"])
            assert described.name != "unknown"
            assert described.family == (row["Famille"] or None)
            assert described.example == (row["example_fr"] or None)
