"""Round-trip guard for the knowledge-base CoursIA notebook (#1961 Phase 5).

Every query the notebook displays comes from
``docs/coursia_contrib/knowledge_base_examples.json`` — the single source of
truth shared by the notebook and this guard. This test rebuilds each knowledge
base from the JSON and replays every query against the real ``KnowledgeBase``:
support/attack counts, consistency verdicts, entailment-as-membership. It also
pins the behaviors the notebook teaches — transitive population (a premise is
carried by its argument), the lexical negation convention (attacking P means
concluding "¬" + P) — and that the committed notebook ships with executed
outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from argumentation_analysis.agents.core.debate.knowledge_base import KnowledgeBase
from argumentation_analysis.agents.core.debate.protocols import (
    FormalArgument,
    Proposition,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_PATH = REPO_ROOT / "docs" / "coursia_contrib" / "knowledge_base_examples.json"
NOTEBOOK_PATH = REPO_ROOT / "docs" / "coursia_contrib" / "knowledge_base.ipynb"


def _load_examples() -> dict[str, Any]:
    with open(EXAMPLES_PATH, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def _build(spec: dict[str, Any]) -> KnowledgeBase:
    # The KnowledgeBase constructor carries no return annotation in the source
    # module (CI strict scope covers core orchestration only) — targeted ignore.
    kb = KnowledgeBase()  # type: ignore[no-untyped-call]
    for arg_spec in spec["arguments"]:
        kb.add_argument(
            FormalArgument(
                premises=[Proposition(content=p) for p in arg_spec["premises"]],
                conclusion=Proposition(content=arg_spec["conclusion"]),
                scheme=arg_spec["scheme"] or None,
            )
        )
    return kb


@pytest.fixture(scope="module")
def built_kbs() -> dict[str, KnowledgeBase]:
    return {spec["name"]: _build(spec) for spec in _load_examples()["kbs"]}


@pytest.mark.parametrize(
    "kb_name,query",
    [
        (spec["name"], query)
        for spec in _load_examples()["kbs"]
        for query in spec["queries"]
    ],
    ids=[
        f"{spec['name']}-{query['kind']}-{i}"
        for spec in _load_examples()["kbs"]
        for i, query in enumerate(spec["queries"])
    ],
)
def test_query_round_trips(
    kb_name: str, query: dict[str, Any], built_kbs: dict[str, KnowledgeBase]
) -> None:
    kb = built_kbs[kb_name]
    if query["kind"] == "supporting":
        got: Any = len(kb.find_supporting_arguments(Proposition(content=query["prop"])))
    elif query["kind"] == "attacking":
        got = len(kb.find_attacking_arguments(Proposition(content=query["prop"])))
    elif query["kind"] == "entails":
        got = kb.entails(Proposition(content=query["prop"]))
    elif query["kind"] == "consistent":
        got = kb.is_consistent()
    else:
        pytest.fail(f"unknown query kind {query['kind']}")
    assert got == query["expected"]


def test_add_argument_registers_premises_transitively(
    built_kbs: dict[str, KnowledgeBase],
) -> None:
    kb = built_kbs["deux_camps"]
    premise = Proposition(content="Le télétravail isole les collaborateurs")
    assert kb.entails(premise), "the argument carries its premise"


def test_negation_convention_is_lexical() -> None:
    kb = KnowledgeBase()  # type: ignore[no-untyped-call]
    kb.add_argument(
        FormalArgument(
            premises=[Proposition(content="les pauses restaurent la concentration")],
            conclusion=Proposition(content="¬Le télétravail réduit la concentration"),
        )
    )
    attacks = kb.find_attacking_arguments(
        Proposition(content="Le télétravail réduit la concentration")
    )
    assert len(attacks) == 1
    assert attacks[0].conclusion.content.startswith("¬")
    assert not kb.entails(Proposition(content="Le télétravail réduit la concentration"))
    assert (
        kb.is_consistent()
    ), "an attack alone leaves the KB consistent — inconsistency requires cohabitation"


def test_committed_notebook_carries_executed_outputs() -> None:
    with open(NOTEBOOK_PATH, encoding="utf-8") as fh:
        nb = json.load(fh)
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert code_cells, "notebook has code cells"
    for cell in code_cells:
        assert cell.get("outputs"), "every code cell ships an executed output"
        assert cell.get("execution_count") is not None
