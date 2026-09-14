"""Round-trip guard for the argumentation-schemes CoursIA notebook (#1961 Phase 5).

Every classification the notebook displays comes from
``docs/coursia_contrib/argumentation_schemes_examples.json`` — the single source
of truth shared by the notebook and this guard. This test replays each example
against the real engine (``classify_scheme``): positives must fire the expected
scheme, negatives must return ``None`` (the honest miss). It also pins the
structural claims the notebook teaches — 10 schemes, accented keyword pairs,
specific schemes ordered before ``modus_ponens`` — and that the committed
notebook ships with executed outputs.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import pytest

from argumentation_analysis.agents.core.debate.argumentation_schemes import (
    _SCHEME_KEYWORDS,
    _load_argumentation_schemes,
    classify_scheme,
    schemes_as_prompt_context,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_PATH = (
    REPO_ROOT / "docs" / "coursia_contrib" / "argumentation_schemes_examples.json"
)
NOTEBOOK_PATH = REPO_ROOT / "docs" / "coursia_contrib" / "argumentation_schemes.ipynb"

EXPECTED_KEYS = frozenset(
    {
        "modus_ponens",
        "expert_opinion",
        "analogy",
        "cause_effect",
        "consensus",
        "empirical_evidence",
        "economic_argument",
        "precautionary_principle",
        "moral_argument",
        "historical_precedent",
    }
)


def _load_examples() -> dict[str, Any]:
    with open(EXAMPLES_PATH, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def test_examples_file_is_well_formed() -> None:
    data = _load_examples()
    positives = data["positives"]
    negatives = data["negatives"]
    assert len(positives) == 10, "one example per scheme"
    assert len(negatives) >= 3, "negative controls are part of the teaching claim"
    table = _load_argumentation_schemes()
    for ex in positives:
        assert ex["expected_key"] in table, f"unknown key {ex['expected_key']}"
        assert ex["text"], "empty positive text"
    assert {ex["expected_key"] for ex in positives} == EXPECTED_KEYS


@pytest.mark.parametrize(
    "text,expected_key",
    [(ex["text"], ex["expected_key"]) for ex in _load_examples()["positives"]],
    ids=[ex["expected_key"] for ex in _load_examples()["positives"]],
)
def test_positive_example_round_trips(text: str, expected_key: str) -> None:
    scheme = classify_scheme(text)
    assert scheme is not None, f"expected {expected_key}, got None"
    assert scheme.key == expected_key


@pytest.mark.parametrize(
    "text",
    [ex["text"] for ex in _load_examples()["negatives"]],
    ids=[f"neg{i}" for i in range(len(_load_examples()["negatives"]))],
)
def test_negative_example_returns_none(text: str) -> None:
    assert classify_scheme(text) is None


def test_table_structure_matches_notebook_claims() -> None:
    table = _load_argumentation_schemes()
    assert set(table) == EXPECTED_KEYS
    for scheme in table.values():
        assert 0.0 < scheme.strength <= 1.0
        assert scheme.critical_questions, f"{scheme.key} teaches critical questions"


def test_specific_schemes_fire_before_modus_ponens() -> None:
    text = (
        "L'étude fournit une mesure directe ; par conséquent, si l'échantillon "
        "est représentatif, la conclusion vaut."
    )
    scheme = classify_scheme(text)
    assert scheme is not None
    assert scheme.key == "empirical_evidence"


def test_accented_keywords_are_required() -> None:
    text = _load_examples()["positives"][0]["text"]
    assert classify_scheme(_strip_accents(text)) is None


def test_prompt_context_lists_every_scheme() -> None:
    context = schemes_as_prompt_context()
    for scheme in _load_argumentation_schemes().values():
        assert scheme.label in context


def test_committed_notebook_carries_executed_outputs() -> None:
    with open(NOTEBOOK_PATH, encoding="utf-8") as fh:
        nb = json.load(fh)
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert code_cells, "notebook has code cells"
    for cell in code_cells:
        assert cell.get("outputs"), "every code cell ships an executed output"
        assert cell.get("execution_count") is not None


def test_keyword_table_covers_every_scheme() -> None:
    assert set(_SCHEME_KEYWORDS) == EXPECTED_KEYS
