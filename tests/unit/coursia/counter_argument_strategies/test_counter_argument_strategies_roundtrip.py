"""Round-trip guard for the counter-argument strategies CoursIA notebook (#1961 Phase 5).

Every verdict the notebook displays comes from
``docs/coursia_contrib/counter_argument_strategies_examples.json`` — the single
source of truth shared by the notebook and this guard. This test replays each
example against the real ``RhetoricalStrategies`` engine: suggestion verdicts
(content heuristics then type table), best-strategy-per-counter-type, and
generated texts that must contain their expected fragment. It also pins the
honesty claim the notebook teaches — the statistical template returns an
explicit placeholder instead of fabricated numbers — and that the committed
notebook ships with executed outputs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from argumentation_analysis.agents.core.counter_argument.definitions import (
    Argument,
    CounterArgumentType,
    RhetoricalStrategy,
)
from argumentation_analysis.agents.core.counter_argument.strategies import (
    RhetoricalStrategies,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_PATH = (
    REPO_ROOT / "docs" / "coursia_contrib" / "counter_argument_strategies_examples.json"
)
NOTEBOOK_PATH = (
    REPO_ROOT / "docs" / "coursia_contrib" / "counter_argument_strategies.ipynb"
)


def _load_examples() -> dict[str, Any]:
    with open(EXAMPLES_PATH, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def _make_arg(spec: dict[str, Any]) -> Argument:
    return Argument(
        content=spec["content"],
        premises=list(spec["premises"]),
        conclusion=spec["conclusion"],
        argument_type=spec["argument_type"],
        confidence=0.7,
    )


@pytest.fixture(scope="module")
def engine() -> RhetoricalStrategies:
    # The RhetoricalStrategies constructor carries no return annotation in the
    # source module (CI strict scope covers core orchestration only).
    return RhetoricalStrategies()  # type: ignore[no-untyped-call]


@pytest.fixture(scope="module")
def variants() -> dict[str, Argument]:
    return {k: _make_arg(v) for k, v in _load_examples()["argument_variants"].items()}


@pytest.mark.parametrize(
    "argument_type,content,expected",
    [
        (ex["argument_type"], ex["content"], ex["expected"])
        for ex in _load_examples()["suggest"]
    ],
)
def test_suggest_round_trips(
    engine: RhetoricalStrategies, argument_type: str, content: str, expected: str
) -> None:
    got = engine.suggest_strategy(argument_type, content)
    assert got == RhetoricalStrategy[expected]


@pytest.mark.parametrize(
    "counter_type,expected",
    [(ex["counter_type"], ex["expected"]) for ex in _load_examples()["best_by_type"]],
)
def test_best_strategy_round_trips(
    engine: RhetoricalStrategies,
    variants: dict[str, Argument],
    counter_type: str,
    expected: str,
) -> None:
    got = engine.get_best_strategy(variants["base"], CounterArgumentType[counter_type])
    assert got == RhetoricalStrategy[expected]


@pytest.mark.parametrize(
    "strategy,counter_type,variant,fragment",
    [
        (ex["strategy"], ex["counter_type"], ex["variant"], ex["expected_fragment"])
        for ex in _load_examples()["apply"]
    ],
)
def test_apply_round_trips(
    engine: RhetoricalStrategies,
    variants: dict[str, Argument],
    strategy: str,
    counter_type: str,
    variant: str,
    fragment: str,
) -> None:
    text = engine.apply_strategy(
        RhetoricalStrategy[strategy],
        variants[variant],
        CounterArgumentType[counter_type],
    )
    assert fragment in text


def test_five_strategies_with_distinct_prompts(engine: RhetoricalStrategies) -> None:
    assert len(engine.strategies) == 5
    prompts = {engine.get_strategy_prompt(s) for s in RhetoricalStrategy}
    assert len(prompts) == 5 and all(prompts)


def test_statistical_template_refuses_fabricated_numbers(
    engine: RhetoricalStrategies, variants: dict[str, Argument]
) -> None:
    text = engine.apply_strategy(
        RhetoricalStrategy.STATISTICAL_EVIDENCE,
        variants["base"],
        CounterArgumentType.DIRECT_REFUTATION,
    )
    assert "[template/placeholder]" in text


def test_committed_notebook_carries_executed_outputs() -> None:
    with open(NOTEBOOK_PATH, encoding="utf-8") as fh:
        nb = json.load(fh)
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert code_cells, "notebook has code cells"
    for cell in code_cells:
        assert cell.get("outputs"), "every code cell ships an executed output"
        assert cell.get("execution_count") is not None
