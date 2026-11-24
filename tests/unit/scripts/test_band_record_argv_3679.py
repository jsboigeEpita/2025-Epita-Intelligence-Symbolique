"""A band record is dispatched with what the replay job runs (#3679 ask 4).

Recorder population must equal replayer population (#2323). The operator used
to assemble the record workflow's ``lane`` and ``extra_args`` by hand from the
band workflow; the 18/09 record left out the deselects that way. The recipe in
``scripts/cassettes/band_record_argv.py`` reads them from the replay job's own
pytest call. This holds the recipe to the files: fed with what it prints, the
record step selects exactly what the replay call selects, and the check the
record step runs on its own inputs refuses the 18/09 dispatch.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from scripts.cassettes import band_record_argv as recipe  # noqa: E402

BAND_YML = REPO / ".github" / "workflows" / "requires_api_band.yml"
RECORD_YML = REPO / ".github" / "workflows" / "record-llm-cassettes.yml"

RECIPE_CHECK = "scripts/cassettes/band_record_argv.py --check-env"
CHECK_EXIT = "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }"


def _band() -> str:
    return BAND_YML.read_text(encoding="utf-8")


def _record() -> str:
    return RECORD_YML.read_text(encoding="utf-8")


def _derived() -> recipe.Recipe:
    return recipe.derive(_band(), _record())


def _replay_marker_and_tokens():
    return recipe.replay_argv(_band())


def _record_step() -> dict:
    steps = yaml.safe_load(_record())["jobs"]["record"]["steps"]
    (step,) = [step for step in steps if step.get("id") == "record"]
    return step


# --- The recipe, held to the two files -------------------------------------


def test_the_recipe_selects_the_replay_population():
    derived = _derived()
    assert (
        derived.same_population
    ), f"record: {derived.record_selection}\nreplay: {derived.replay_selection}"


def test_the_lane_is_the_replay_marker():
    marker, _tokens = _replay_marker_and_tokens()
    assert marker == "requires_api and not llm_light"
    assert _derived().lane == marker


def test_every_directory_and_deselect_of_the_replay_call_is_carried():
    _marker, replay_tokens = _replay_marker_and_tokens()
    derived = _derived()
    carried = recipe.split_pwsh(derived.extra_args)

    replay_paths = []
    for token in replay_tokens:
        if token.startswith("-"):
            break
        replay_paths.append(token)
    # tests/unit/ is the one path the record step names itself.
    assert carried[: len(replay_paths) - 1] == replay_paths[1:]
    assert carried.count("--deselect") == replay_tokens.count("--deselect")
    assert replay_tokens.count("--deselect") >= 1


def test_each_side_adds_only_what_is_named():
    template = recipe.record_template_argv(_record())
    _marker, replay_tokens = _replay_marker_and_tokens()
    record_adds = recipe._flags(template, "--allow-dotenv") + recipe._pairs(
        template, "--deselect"
    )
    # The record step's own deselect: an env-shape mismatch of the record
    # lane (the service is wrapped in the cache there), not a population choice.
    assert record_adds == [
        ("--allow-dotenv", None),
        (
            "--deselect",
            "tests/unit/argumentation_analysis/test_llm_service.py::TestLLMService"
            "::test_create_llm_service_openai_authentic",
        ),
    ]
    assert recipe._pairs(replay_tokens, "-p") == [
        ("-p", "scripts.cassettes.replay_stats_plugin")
    ]


def test_the_cli_prints_two_lines_to_paste(capsys):
    assert recipe.main([]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("lane=")
    assert lines[1].startswith("extra_args=")
    assert len(lines[1]) > len("extra_args=")
    assert sum(line.startswith("OK: the record step") for line in lines) == 1


def _slowed_record_step() -> str:
    """The record step with a timeout of its own: the replay call untouched."""
    mutated = _record().replace("--timeout=900", "--timeout=600")
    assert mutated != _record(), "the mutation did not take"
    assert _record().count("--timeout=900") == 1, "the mutation is not local"
    return mutated


def test_the_cli_fails_loud_when_the_record_step_stops_following_the_replay_call(
    capsys, tmp_path
):
    """The control of the first test: the comparison can fail.

    The recipe follows the replay call by construction, so a change on that
    side alone cannot separate the two. What can is the part of the record
    step that no dispatch input fills.
    """
    path = tmp_path / "record.yml"
    path.write_text(_slowed_record_step(), encoding="utf-8")
    with pytest.raises(SystemExit) as exit_info:
        recipe.main(["--record-yml", str(path)])
    assert exit_info.value.code == 1
    assert "FAIL-LOUD" in capsys.readouterr().err


def test_an_option_the_recipe_does_not_know_is_refused_not_dropped():
    with pytest.raises(ValueError, match=r"the replay call carries '--ignore'"):
        recipe.record_inputs(
            "m", ["tests/unit/", "tests/x/", "--ignore", "tests/y", "-m", "m"]
        )


def test_a_root_other_than_the_one_the_record_step_names_is_refused():
    with pytest.raises(ValueError, match="must start with tests/unit/"):
        recipe.record_inputs("m", ["tests/integration/", "-m", "m"])


def test_the_quoting_the_splitter_does_not_model_is_refused():
    for line in (
        "pytest tests/ -k 'a b'",
        'pytest tests/ -k "a` b"',
        "pytest tests/ a\\b",
    ):
        with pytest.raises(ValueError, match="cannot tokenise"):
            recipe.split_pwsh(line)
    with pytest.raises(ValueError, match="unbalanced"):
        recipe.split_pwsh('pytest tests/ --deselect "a')


# --- The record step checks the inputs it received --------------------------


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _rejoin(tokens: list) -> str:
    """Tokens back to the spelling of the dispatch form: a deselect is quoted."""
    parts = []
    index = 0
    while index < len(tokens):
        if tokens[index] == "--deselect":
            parts += ["--deselect", f'"{tokens[index + 1]}"']
            index += 2
        else:
            parts.append(tokens[index])
            index += 1
    return " ".join(parts)


def _dispatch(monkeypatch, lane: str, extra_args: str) -> None:
    monkeypatch.setenv(recipe.LANE_ENV, lane)
    monkeypatch.setenv(recipe.EXTRA_ARGS_ENV, extra_args)


def _tokens() -> list:
    return recipe.split_pwsh(_derived().extra_args)


def test_the_check_accepts_the_recipe(monkeypatch, capsys):
    derived = _derived()
    _dispatch(monkeypatch, derived.lane, derived.extra_args)
    assert recipe.main(["--check-env"]) == 0
    out = capsys.readouterr().out
    assert "OK: this record selects what the replay call selects" in out
    assert "FAIL-LOUD" not in out


def test_the_check_reads_tokens_not_their_spelling(monkeypatch):
    """A lane with spaces around it, an argument list broken over lines."""
    derived = _derived()
    broken = derived.extra_args.replace(" --deselect ", "\n  --deselect  ")
    assert broken != derived.extra_args
    _dispatch(monkeypatch, f"  {derived.lane} \n", broken)
    assert recipe.main(["--check-env"]) == 0


def test_every_deselect_of_the_recipe_matters(monkeypatch):
    """The 18/09 dispatch, one deselect at a time: none may slip through."""
    derived = _derived()
    tokens = _tokens()
    positions = [index for index, token in enumerate(tokens) if token == "--deselect"]
    assert len(positions) == tokens.count("--deselect")
    let_through = []
    for position in positions:
        kept = tokens[:position] + tokens[position + 2 :]
        _dispatch(monkeypatch, derived.lane, _rejoin(kept))
        if recipe.main(["--check-env"]) == 0:
            let_through.append(tokens[position + 1])
    assert let_through == []


def test_every_directory_of_the_recipe_matters(monkeypatch):
    derived = _derived()
    tokens = _tokens()
    directories = []
    index = 0
    while tokens[index].startswith("tests/"):
        directories.append(tokens[index])
        index += 1
    assert len(directories) >= 1
    let_through = []
    for directory in directories:
        _dispatch(
            monkeypatch,
            derived.lane,
            _rejoin([token for token in tokens if token != directory]),
        )
        if recipe.main(["--check-env"]) == 0:
            let_through.append(directory)
    assert let_through == []


def test_a_deselect_left_out_stops_the_record_before_it_bills(monkeypatch, capsys):
    derived = _derived()
    tokens = _tokens()
    position = tokens.index("--deselect")
    _dispatch(
        monkeypatch, derived.lane, _rejoin(tokens[:position] + tokens[position + 2 :])
    )
    assert recipe.main(["--check-env"]) == 1
    out = capsys.readouterr().out
    assert out.startswith(
        "FAIL-LOUD: this record would not select the replay population"
    )
    assert "Nothing was billed" in out
    # The operator is handed what to dispatch again with.
    assert f"lane={derived.lane}" in out
    assert f"extra_args={derived.extra_args}" in out


def test_a_deselect_added_stops_the_record_too(monkeypatch):
    derived = _derived()
    added = _tokens() + ["--deselect", "tests/unit/test_never_in_the_band.py::test_x"]
    _dispatch(monkeypatch, derived.lane, _rejoin(added))
    assert recipe.main(["--check-env"]) == 1


def test_the_message_names_the_deselect_the_record_lacks(monkeypatch, capsys):
    """One deselect dropped in the middle: the two lists disagree from there."""
    derived = _derived()
    tokens = _tokens()
    position = tokens.index("--deselect")
    _dispatch(
        monkeypatch, derived.lane, _rejoin(tokens[:position] + tokens[position + 2 :])
    )
    assert recipe.main(["--check-env"]) == 1
    out = capsys.readouterr().out
    assert "first difference at token" in out
    assert f"replay '{tokens[position + 1]}'" in out


def test_an_option_the_record_step_loses_reads_as_the_side_that_carries_less(
    tmp_path, capsys
):
    """The two lists agree up to the record step's last token."""
    record = _record().replace(" --timeout-method=thread", "")
    assert record != _record() and _record().count("--timeout-method=thread") == 1
    path = _write(tmp_path, "record.yml", record)
    with pytest.raises(SystemExit) as exit_info:
        recipe.main(["--record-yml", str(path)])
    assert exit_info.value.code == 1
    assert "the replay side carries 1 token(s) more" in capsys.readouterr().err


def test_another_lane_is_not_a_band_record(monkeypatch, capsys):
    """The general harvest selects another population by design."""
    _dispatch(monkeypatch, "not slow and not requires_api", "")
    assert recipe.main(["--check-env"]) == 0
    assert "not a band record" in capsys.readouterr().out


def test_the_check_sees_a_record_step_that_stopped_following_the_replay_call(
    monkeypatch, capsys
):
    derived = _derived()
    _dispatch(monkeypatch, derived.lane, derived.extra_args)
    code, message = recipe.check_env(_band(), _slowed_record_step(), os.environ)
    assert code == 1
    assert "FAIL-LOUD" in message
    assert "'--timeout=600'" in message and "'--timeout=900'" in message


def test_a_recipe_that_cannot_be_read_fails_closed(monkeypatch, tmp_path, capsys):
    derived = _derived()
    _dispatch(monkeypatch, derived.lane, derived.extra_args)
    # A new option on the replay side: the recipe refuses it rather than guess.
    unknown = _band().replace("--deselect", "--ignore")
    assert unknown != _band()
    path = _write(tmp_path, "band.yml", unknown)
    assert recipe.main(["--band-yml", str(path), "--check-env"]) == 1
    assert "FAIL-LOUD: the recipe cannot be read" in capsys.readouterr().out


# --- The record step runs that check ----------------------------------------


def test_the_record_step_passes_its_two_inputs_to_the_check():
    env = _record_step()["env"]
    assert env[recipe.LANE_ENV] == "${{ inputs.lane }}"
    assert env[recipe.EXTRA_ARGS_ENV] == "${{ inputs.extra_args }}"


def test_the_record_step_runs_the_check_before_its_billable_command():
    lines = [line.strip() for line in _record_step()["run"].splitlines()]
    (check,) = [
        index for index, line in enumerate(lines) if line.endswith(RECIPE_CHECK)
    ]
    (billable,) = [
        index
        for index, line in enumerate(lines)
        if "pytest " in line and not line.startswith("#")
    ]
    assert check < billable, "the check must run before anything is billed"
    assert lines[check].startswith("conda run -n projet-is --no-capture-output python ")
    # A refused dispatch stops the step: its failure is the run's failure.
    assert lines[check + 1] == CHECK_EXIT
