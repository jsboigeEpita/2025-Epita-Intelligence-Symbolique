"""The two dispatch inputs of a BAND record, read from the replay job (#3679).

A band record must cover exactly the population the replay-band job replays:
same marker, same directories, same ``--deselect`` list (#2323). Until now the
operator assembled ``lane`` and ``extra_args`` by hand from
``requires_api_band.yml``. The 18/09 record (run 35326898374) left out the
deselects that way and recorded five tests the band never replays; the 15/11
record (run 43684055967) pasted them whole. This reads the replay job's own
pytest call and prints both values, then rebuilds the record step's command
from them and holds it against that call::

    python scripts/cassettes/band_record_argv.py

The operator copies the two lines into the dispatch form. A test
(``tests/unit/scripts/test_band_record_argv_3679.py``) runs the same
comparison on every push, so the two cannot drift apart quietly.

The record step then runs the comparison on what it really received::

    python scripts/cassettes/band_record_argv.py --check-env

with the two inputs in ``RECORD_LANE`` and ``RECORD_EXTRA_ARGS``. A dispatch
that would not select the replay population stops there, before anything is
billed. A run on another lane (the general harvest) is not a band record and
is let through.

The check answers in three ways, and the step reads each (#3679 item 40c):

- ``0`` — a verified band record: it selects what the replay call selects.
  The step then runs it WITHOUT the dataset passphrase. The band population
  never decrypts the corpus, and without the passphrase no prompt of the run
  can carry corpus prose — by construction, which is what lets the export
  report its historical-year hints instead of refusing them
  (``scripts/cassettes/privacy.py``).
- ``1`` — the dispatch would not select the replay population: the step
  stops, nothing is billed.
- ``NOT_BAND_RECORD_EXIT`` — another lane (the general harvest): the step
  goes on as before, WITH the passphrase, since its unit tests read the
  dataset. A code of its own, so that the step cannot mistake that lane for a
  verified band record.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[2]
BAND_YML = ROOT / ".github" / "workflows" / "requires_api_band.yml"
RECORD_YML = ROOT / ".github" / "workflows" / "record-llm-cassettes.yml"

# Where the record step passes its two inputs to ``--check-env``. An ``env:``
# entry carries any text as is; a command-line argument would go through the
# quoting of the shell.
LANE_ENV = "RECORD_LANE"
EXTRA_ARGS_ENV = "RECORD_EXTRA_ARGS"

# The check's third answer, "not a band record" (module docstring). 0 and 1
# are taken: 0 a verified band record, 1 a refusal (and a crash of the
# interpreter); argparse stops on 2 before the comparison.
NOT_BAND_RECORD_EXIT = 3

PYTEST_CALL = "--no-capture-output pytest "
MARKER_ASSIGN = '$marker = "'
LANE_INPUT = "${{ inputs.lane }}"
EXTRA_ARGS_INPUT = "${{ inputs.extra_args }}"
# The same two inputs as single tokens. ``${{ inputs.extra_args }}`` stands
# unquoted in the file, so its own spaces would cut it into three tokens.
_LANE_TOKEN = "@@inputs.lane@@"
_EXTRA_ARGS_TOKEN = "@@inputs.extra_args@@"

# The one directory the record step names itself, ahead of ``extra_args``.
RECORD_ROOT = "tests/unit/"

# Options of the replay call that the record step provides under its own
# spelling, or that only a replay needs: option -> number of arguments that
# follow it. Anything else is refused, never dropped — a new option on the
# replay side changes the population, and the recorder has to follow it here
# and in the record step.
REPLAY_OPTIONS_NOT_CARRIED = {
    "-m": 1,  # the marker: it becomes the ``lane`` input
    "-p": 1,  # the replay stats plugin: an observer of the replay only
    "-v": 0,  # --timeout=900 and --junitxml=… come in the inline form
    "--timeout": 0,
    "--timeout-method": 0,
    "--junitxml": 0,
}

# (option, target): a flag has no target.
Removal = Tuple[str, Optional[str]]


def split_pwsh(line: str) -> List[str]:
    """Tokens of a PowerShell command line, double quotes removed.

    Models the quoting the two workflow files use — double quotes around a
    value with no space inside — and refuses anything else (a single quote, a
    backtick, a backslash) instead of splitting it wrongly.
    """
    for forbidden in ("'", "`", "\\"):
        if forbidden in line:
            raise ValueError(
                f"cannot tokenise {forbidden!r} in the pytest call: {line[:80]}…"
            )
    tokens: List[str] = []
    current: List[str] = []
    quoted = False
    for char in line:
        if char == '"':
            quoted = not quoted
        elif char.isspace() and not quoted:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)
    if quoted:
        raise ValueError(f"unbalanced double quote in the pytest call: {line[:80]}…")
    if current:
        tokens.append("".join(current))
    return tokens


def _pytest_step(job: dict) -> dict:
    steps = [step for step in job["steps"] if PYTEST_CALL in step.get("run", "")]
    if len(steps) != 1:
        raise ValueError(f"expected one pytest call in the job, found {len(steps)}")
    return steps[0]


def marker_of(run_text: str) -> str:
    """The marker the step assigns right before its pytest call."""
    marker: Optional[str] = None
    for line in run_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(MARKER_ASSIGN):
            marker = stripped[len(MARKER_ASSIGN) :].split('"', 1)[0]
        elif PYTEST_CALL in line:
            break
    if marker is None:
        raise ValueError(f'no {MARKER_ASSIGN}…" assignment before the pytest call')
    return marker


def pytest_tokens(run_text: str) -> List[str]:
    """Everything the step passes to pytest, token by token.

    The two dispatch inputs come out as one token each, whatever the quoting
    around them in the file.
    """
    (line,) = [line for line in run_text.splitlines() if PYTEST_CALL in line]
    line = line.replace(LANE_INPUT, _LANE_TOKEN).replace(
        EXTRA_ARGS_INPUT, _EXTRA_ARGS_TOKEN
    )
    tokens = split_pwsh(line)
    return tokens[tokens.index("pytest") + 1 :]


def replay_argv(band_yml_text: str) -> Tuple[str, List[str]]:
    """Marker and pytest argv of the replay-band job, read from its own call."""
    run_text = _pytest_step(yaml.safe_load(band_yml_text)["jobs"]["replay-band"])["run"]
    return marker_of(run_text), pytest_tokens(run_text)


def record_inputs(marker: str, argv: Sequence[str]) -> Tuple[str, str]:
    """``lane`` and ``extra_args``: what makes the record step run ``argv``."""
    paths: List[str] = []
    index = 0
    while index < len(argv) and not argv[index].startswith("-"):
        paths.append(argv[index])
        index += 1
    if not paths or paths[0] != RECORD_ROOT:
        raise ValueError(
            f"the replay call must start with {RECORD_ROOT} (the record step names "
            f"it itself); it starts with {paths[:1]}"
        )
    carried = list(paths[1:])
    while index < len(argv):
        option = argv[index]
        if option == "--deselect":
            if index + 1 >= len(argv):
                raise ValueError("--deselect with no target at the end of the call")
            carried += [option, f'"{argv[index + 1]}"']
            index += 2
            continue
        name = option.split("=", 1)[0]
        if name not in REPLAY_OPTIONS_NOT_CARRIED:
            raise ValueError(
                f"the replay call carries {option!r}: the record recipe does not "
                "carry it. Add it here and to the record step, or remove it from "
                "the replay call."
            )
        index += 1 + REPLAY_OPTIONS_NOT_CARRIED[name]
    return marker, " ".join(carried)


def record_template_argv(record_yml_text: str) -> List[str]:
    """The record step's pytest argv as the file spells it, inputs in place."""
    steps = yaml.safe_load(record_yml_text)["jobs"]["record"]["steps"]
    (step,) = [step for step in steps if step.get("id") == "record"]
    return pytest_tokens(step["run"])


def fill_record_template(
    template_argv: Sequence[str], lane: str, extra_args: str
) -> List[str]:
    """The record step's pytest argv once the dispatch form is filled in."""
    if (
        template_argv.count(_LANE_TOKEN) != 1
        or template_argv.count(_EXTRA_ARGS_TOKEN) != 1
    ):
        raise ValueError(
            "the record step must use "
            f"{LANE_INPUT} and {EXTRA_ARGS_INPUT} exactly once each"
        )
    tokens: List[str] = []
    for token in template_argv:
        if token == _LANE_TOKEN:
            tokens.append(lane)
        elif token == _EXTRA_ARGS_TOKEN:
            tokens.extend(split_pwsh(extra_args))
        else:
            tokens.append(token)
    return tokens


def _flags(tokens: Sequence[str], flag: str) -> List[Removal]:
    return [(token, None) for token in tokens if token == flag]


def _pairs(tokens: Sequence[str], option: str) -> List[Removal]:
    """Every ``(option, target)`` of a token list, in order."""
    pairs: List[Removal] = []
    for position, token in enumerate(tokens):
        if token == option:
            if position + 1 >= len(tokens):
                raise ValueError(f"{option} with no target at the end of the call")
            pairs.append((token, tokens[position + 1]))
    return pairs


def _without(tokens: Sequence[str], removals: Sequence[Removal]) -> List[str]:
    """``tokens`` minus one occurrence of each option (and its target, if any)."""
    kept = list(tokens)
    for option, target in removals:
        width = 2 if target is not None else 1
        for position in range(len(kept) - width + 1):
            if kept[position] == option and (
                target is None or kept[position + 1] == target
            ):
                del kept[position : position + width]
                break
        else:
            raise ValueError(
                f"{' '.join(str(part) for part in (option, target) if part)} "
                "is no longer in the call"
            )
    return kept


def _selection(tokens: Sequence[str], removals: Sequence[Removal]) -> List[str]:
    """What decides which tests run, and how pytest reports them.

    The junit file is an output, the marker is compared on its own: each is
    taken out with the named differences.
    """
    outputs = [(token, None) for token in tokens if token.startswith("--junitxml=")]
    return _without(tokens, list(removals) + outputs)


@dataclass(frozen=True)
class Recipe:
    """The two dispatch inputs, and what each side selects once they are used."""

    lane: str
    extra_args: str
    marker: str
    record_selection: List[str]
    replay_selection: List[str]

    @property
    def same_population(self) -> bool:
        return (
            self.lane == self.marker and self.record_selection == self.replay_selection
        )


def _selections(
    record_yml_text: str, band_yml_text: str, lane: str, extra_args: str
) -> Tuple[str, List[str], List[str]]:
    """Marker of the replay call, and what each side selects under the inputs."""
    marker, replay_tokens = replay_argv(band_yml_text)
    template = record_template_argv(record_yml_text)
    record_tokens = fill_record_template(template, lane, extra_args)
    # The record step's own additions, read from the file: the dotenv flag and
    # the deselect it carries itself (an env-shape mismatch of the record lane).
    record_adds = _flags(template, "--allow-dotenv") + _pairs(template, "--deselect")
    # The replay-only observer plugin.
    replay_adds = _pairs(replay_tokens, "-p")
    if _pairs(replay_tokens, "-m") != [("-m", "$marker")]:
        raise ValueError('the replay call must pass the assigned marker: -m "$marker"')
    # The marker is compared on its own (``lane`` against ``marker``), so it
    # leaves each selection under that side's own spelling.
    return (
        marker,
        _selection(record_tokens, record_adds + _pairs(record_tokens, "-m")),
        _selection(replay_tokens, replay_adds + _pairs(replay_tokens, "-m")),
    )


def derive(band_yml_text: str, record_yml_text: str) -> Recipe:
    """Read both workflow files and derive the band record recipe from them."""
    marker, replay_tokens = replay_argv(band_yml_text)
    lane, extra_args = record_inputs(marker, replay_tokens)
    marker, record_selection, replay_selection = _selections(
        record_yml_text, band_yml_text, lane, extra_args
    )
    return Recipe(lane, extra_args, marker, record_selection, replay_selection)


def _squash(text: str) -> str:
    return " ".join(text.split())


def gap(
    band_yml_text: str, record_yml_text: str, lane: str, extra_args: str
) -> Optional[str]:
    """Why a record dispatched with ``lane`` and ``extra_args`` would not select
    the replay population. ``None`` when it does."""
    marker, record_selection, replay_selection = _selections(
        record_yml_text, band_yml_text, lane, extra_args
    )
    if _squash(lane) != _squash(marker):
        return f"the record lane is {lane!r}, the replay call selects {marker!r}"
    if record_selection != replay_selection:
        return _first_gap(record_selection, replay_selection)
    return None


def check_env(
    band_yml_text: str, record_yml_text: str, env: Mapping[str, str]
) -> Tuple[int, str]:
    """The record step's own check: exit code and line(s) to print.

    Reads the two inputs the step received and compares what its command would
    select with what the replay call selects. The code is the step's branch:
    ``0`` a verified band record, ``1`` a refusal,
    ``NOT_BAND_RECORD_EXIT`` another lane (module docstring).
    """
    recipe = derive(band_yml_text, record_yml_text)
    lane = env.get(LANE_ENV, "")
    if _squash(lane) != _squash(recipe.marker):
        return (
            NOT_BAND_RECORD_EXIT,
            f"not a band record: lane {lane!r} is not the replay marker "
            f"{recipe.marker!r} — nothing to compare",
        )
    found = gap(band_yml_text, record_yml_text, lane, env.get(EXTRA_ARGS_ENV, ""))
    if found is None:
        return (
            0,
            "OK: this record selects what the replay call selects "
            f"({len(recipe.replay_selection)} tokens)",
        )
    return (
        1,
        "\n".join(
            [
                "FAIL-LOUD: this record would not select the replay population "
                f"— {found}",
                "Nothing was billed. Dispatch again with:",
                f"lane={recipe.lane}",
                f"extra_args={recipe.extra_args}",
            ]
        ),
    )


def _first_gap(left: Sequence[str], right: Sequence[str]) -> str:
    for position, (one, other) in enumerate(zip(left, right)):
        if one != other:
            return f"first difference at token {position}: record {one!r}, replay {other!r}"
    longer = "record" if len(left) > len(right) else "replay"
    return f"the {longer} side carries {abs(len(left) - len(right))} token(s) more"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the lane and extra_args of a band record, read from "
        "the replay-band job's own pytest call."
    )
    parser.add_argument("--band-yml", type=Path, default=BAND_YML)
    parser.add_argument("--record-yml", type=Path, default=RECORD_YML)
    parser.add_argument(
        "--check-env",
        action="store_true",
        help=f"compare {LANE_ENV} and {EXTRA_ARGS_ENV} — the inputs the record "
        "step received — with the replay call. The record step runs this "
        "itself, before its billable command",
    )
    args = parser.parse_args(argv)
    band_yml_text = args.band_yml.read_text(encoding="utf-8")
    record_yml_text = args.record_yml.read_text(encoding="utf-8")
    if args.check_env:
        try:
            code, message = check_env(band_yml_text, record_yml_text, os.environ)
        except ValueError as error:
            code, message = 1, f"FAIL-LOUD: the recipe cannot be read — {error}"
        print(message)
        return code
    recipe = derive(band_yml_text, record_yml_text)
    print(f"lane={recipe.lane}")
    print(f"extra_args={recipe.extra_args}")
    if not recipe.same_population:
        parser.exit(
            1,
            "FAIL-LOUD: the record step fed with the two lines above does not "
            "select what the replay call selects "
            f"({gap(band_yml_text, record_yml_text, recipe.lane, recipe.extra_args)}).\n",
        )
    print(
        "OK: the record step fed with these two lines selects what the replay "
        f"call selects ({len(recipe.replay_selection)} tokens)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
