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
import shutil
import subprocess
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
RECIPE_LINE = "conda run -n projet-is --no-capture-output python " + RECIPE_CHECK
# The three answers of the check (#3679 item 40c): 0 a verified band record,
# 1 a dispatch that would not select the band, 3 another lane.
NOT_BAND_RECORD = 3
GUARD = (
    f"if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne {NOT_BAND_RECORD}) "
    "{ exit $LASTEXITCODE }"
)
# The step says the word only once it has seen the passphrase gone: a record
# that kept it stops before billing, and says nothing to the export step.
SURVIVED_LINE = (
    'if (Test-Path Env:TEXT_CONFIG_PASSPHRASE) { Write-Host "FAIL-LOUD: the dataset '
    'passphrase survived the record step — nothing was billed."; exit 1 }'
)
# What the step does with a verified band record: it runs it without the
# dataset passphrase, and tells the export step.
WITHHOLD_BLOCK = [
    "if ($LASTEXITCODE -eq 0) {",
    "if (Test-Path Env:TEXT_CONFIG_PASSPHRASE) { Remove-Item Env:TEXT_CONFIG_PASSPHRASE }",
    SURVIVED_LINE,
    # ``$env:`` — a bare ``$GITHUB_OUTPUT`` names a PowerShell variable that
    # does not exist, and the word goes nowhere (the shell witness below
    # caught exactly that line).
    'echo "dataset_passphrase=withheld" >> $env:GITHUB_OUTPUT',
    "}",
]
EXPORT_STEP = "Export cassettes + blocking privacy audit"


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
    """The general harvest selects another population by design.

    It has its own exit code (#3679 item 40c): the step reads 0 as « a
    verified band record — run it without the dataset passphrase », and the
    general harvest reads the corpus.
    """
    _dispatch(monkeypatch, "not slow and not requires_api", "")
    assert recipe.main(["--check-env"]) == NOT_BAND_RECORD
    assert "not a band record" in capsys.readouterr().out


def test_the_check_tells_its_three_outcomes_apart(monkeypatch):
    derived = _derived()
    tokens = _tokens()
    position = tokens.index("--deselect")
    outcomes = {
        "a verified band record": (derived.lane, derived.extra_args),
        "a dispatch that would not select the band": (
            derived.lane,
            _rejoin(tokens[:position] + tokens[position + 2 :]),
        ),
        "another lane": ("not slow and not requires_api", ""),
    }
    codes = {}
    for name, (lane, extra_args) in outcomes.items():
        _dispatch(monkeypatch, lane, extra_args)
        codes[name] = recipe.main(["--check-env"])
    assert codes == {
        "a verified band record": 0,
        "a dispatch that would not select the band": 1,
        "another lane": NOT_BAND_RECORD,
    }
    assert recipe.NOT_BAND_RECORD_EXIT == NOT_BAND_RECORD


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
    # Anything unexpected stops it too; only another lane is let through
    # (#3679 item 40c).
    assert lines[check + 1] == GUARD


# --- A band record runs without the dataset passphrase (#3679 item 40c) ------
#
# The band population never decrypts the corpus (0 call to the dataset loader
# in a local replay of the exact record population), so a band record has no
# use for the passphrase — and without it, no prompt of the run can carry
# corpus prose. The export's historical-year rule is reported, not blocking,
# for such a run only (scripts/cassettes/export.py). These hold the step to
# that: it removes the passphrase exactly for a verified band record, and it
# says so to the export step.


def _executable_lines() -> list:
    return [
        line.strip()
        for line in _record_step()["run"].splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _from_the_check_to_the_end_of_the_block() -> list:
    lines = _executable_lines()
    (check,) = [
        index for index, line in enumerate(lines) if line.endswith(RECIPE_CHECK)
    ]
    block = [lines[check]]
    for line in lines[check + 1 :]:
        block.append(line)
        if line == "}":
            return block
    raise AssertionError("no closing brace after the check")


def test_a_verified_band_record_loses_the_dataset_passphrase_before_it_bills():
    """The lines between the check and the billable command, exactly."""
    assert _from_the_check_to_the_end_of_the_block() == [
        RECIPE_LINE,
        GUARD,
        *WITHHOLD_BLOCK,
    ]


def test_nothing_else_runs_between_the_withholding_and_the_billable_command():
    lines = _executable_lines()
    (billable,) = [index for index, line in enumerate(lines) if "pytest " in line]
    block = _from_the_check_to_the_end_of_the_block()
    assert lines[billable - len(block) : billable] == block


def test_the_export_step_reads_what_the_record_step_reported():
    steps = yaml.safe_load(_record())["jobs"]["record"]["steps"]
    (step,) = [step for step in steps if step.get("name") == EXPORT_STEP]
    assert step["env"]["RECORD_DATASET_PASSPHRASE"] == (
        "${{ steps.record.outputs.dataset_passphrase || 'given' }}"
    )


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh is not installed")
@pytest.mark.parametrize(
    ("answer", "exit_code", "passphrase", "reported", "removal", "present"),
    [
        (0, 0, "absent", True, "works", True),  # a verified band record
        # no secret on the dispatch: nothing to remove, the record is without it
        (0, 0, "absent", True, "works", False),
        # the removal does not take: stop before billing, say nothing
        (0, 1, "present", False, "ineffective", True),
        (
            1,
            1,
            "present",
            False,
            "works",
            True,
        ),  # a dispatch that would not select the band
        (NOT_BAND_RECORD, 0, "present", False, "works", True),  # another lane
        (
            2,
            2,
            "present",
            False,
            "works",
            True,
        ),  # anything unexpected stops before billing
    ],
)
def test_the_step_s_shell_withholds_exactly_for_a_verified_band_record(
    tmp_path, answer, exit_code, passphrase, reported, removal, present
):
    """The lines of the workflow, run by the shell that will run them.

    The recipe check stands in as a function that sets the exit code. The
    script reports whether the passphrase survived the block — from a
    ``finally``, since the block's own ``exit`` would skip a later line.
    """
    from scripts.cassettes import export as cassette_export

    output = tmp_path / "github_output.txt"
    script = tmp_path / "step.ps1"
    script.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'stop'",
                # GitHub runs a pwsh step with this preference: a non-terminating
                # error (a missing Env: entry) would fail the step.
                f"function conda {{ $global:LASTEXITCODE = {answer} }}",
                # The secret, when the dispatch has one, before the step.
                *(["$env:TEXT_CONFIG_PASSPHRASE = 'not-a-key'"] if present else []),
                # A removal that does nothing: the word must not follow it.
                *(["function Remove-Item { }"] if removal == "ineffective" else []),
                f"$env:GITHUB_OUTPUT = '{output}'",
                "try {",
                *_from_the_check_to_the_end_of_the_block(),
                "} finally {",
                "if (Test-Path Env:TEXT_CONFIG_PASSPHRASE) { "
                "Write-Output 'PASSPHRASE=present' } else { "
                "Write-Output 'PASSPHRASE=absent' }",
                "}",
                "exit 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    run = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-File", str(script)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == exit_code, run.stdout + run.stderr
    assert f"PASSPHRASE={passphrase}" in run.stdout, run.stdout + run.stderr
    assert output.exists() is reported
    assert ("FAIL-LOUD" in run.stdout) is (removal == "ineffective")
    if reported:
        assert (
            output.read_text(encoding="utf-8").strip() == "dataset_passphrase=withheld"
        )
        assert cassette_export.WITHHELD == "withheld"
