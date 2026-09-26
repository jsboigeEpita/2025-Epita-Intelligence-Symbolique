"""#2346: ``scripts/run_experiments.py`` → validation demo, a chain that could
not run.

Measured on ``main`` ``5e4cd3788`` before this fix:

- the runner launched ``demos/validation_complete_epita.py``, a path gone
  since #34;
- it passed ``--trace-log-path``, which the demo did not declare, and
  ``--agent-type full``, which the demo's ``choices`` refused;
- the demo ran no scenario without ``--integration-test`` or
  ``--dialogue-text``, then exited 0, because ``all([])`` is true;
- the demo printed no ``SCORE FINAL`` line, so the runner's regex had nothing
  to read;
- the runner used ``check_errors=True``, and the demo exits 1 whenever a
  scenario misses: a partial score became "Erreur" and its number was lost.

These tests hold the two ends of the chain together: every command the
runner builds parses with the demo's own parser, and the runner's regex reads
the score line the demo prints. Both modules are loaded from their files; no
LLM call, no subprocess.
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts" / "run_experiments.py"
DEMO = (
    REPO_ROOT
    / "examples"
    / "03_demos_overflow"
    / "validation"
    / "validation_complete_epita.py"
)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load(RUNNER, "run_experiments_2346")
demo = _load(DEMO, "validation_complete_epita_2346")


def _demo_args(command):
    return command[command.index(str(runner.VALIDATION_SCRIPT)) + 1 :]


def _results(*statuses):
    tests = [{"name": f"s{i}", "status": s} for i, s in enumerate(statuses)]
    return {"components": {"Analyse Informelle": {"tests": tests}}}


def test_the_runner_launches_the_demo_file():
    assert runner.VALIDATION_SCRIPT.resolve() == DEMO.resolve()
    assert runner.VALIDATION_SCRIPT.exists()


def test_every_experiment_parses_with_the_demo_parser(tmp_path):
    parser = demo.build_parser()
    seen = 0
    for agent in runner.AGENTS:
        for taxonomy_file in runner.TAXONOMIES:
            trace_dir = tmp_path / f"{agent}-{taxonomy_file}"
            command = runner.build_validation_command(agent, taxonomy_file, trace_dir)
            args = parser.parse_args(_demo_args(command))
            assert args.agent_type == agent
            assert Path(args.taxonomy).exists(), args.taxonomy
            assert Path(args.trace_dir) == trace_dir
            assert not args.integration_test
            seen += 1
    assert seen == len(runner.AGENTS) * len(runner.TAXONOMIES) >= 12


def test_the_integration_flag_reaches_the_demo(tmp_path):
    command = runner.build_validation_command(
        "simple", runner.TAXONOMIES[0], tmp_path, integration_test=True
    )
    assert demo.build_parser().parse_args(_demo_args(command)).integration_test


def test_the_runner_reads_the_score_line_the_demo_prints():
    results = _results("SUCCESS", "SUCCESS", "SUCCESS", "FAILED", "PARTIAL")
    line = demo.final_score_line(results)
    assert line == "SCORE FINAL: 3/4 (75.00%)"
    assert runner.extract_score(line) == 75.0
    assert runner.extract_score("noise before\n" + line + "\nnoise after") == 75.0


def test_a_run_without_a_scored_scenario_has_no_score_and_fails():
    for results in ({}, _results(), _results("PARTIAL")):
        assert runner.extract_score(demo.final_score_line(results)) is None
    assert not demo.validation_succeeded({})
    assert not demo.validation_succeeded(_results())
    assert not demo.validation_succeeded(_results("SUCCESS", "FAILED"))
    assert demo.validation_succeeded(_results("SUCCESS", "PARTIAL"))


def test_every_informal_config_is_an_agent_choice():
    from argumentation_analysis.agents.concrete_agents.informal_fallacy_agent import (
        INFORMAL_AGENT_CONFIGS,
    )

    choices = {a.dest: a.choices for a in demo.build_parser()._actions if a.choices}[
        "agent_type"
    ]
    assert set(choices) == set(INFORMAL_AGENT_CONFIGS)
    assert set(runner.AGENTS) <= set(choices)
