# AGENTS.md

For a coding agent that works from a fresh clone and has no *seat* — a seat
being one of the project's machines, with its `.env`, its conda environment and
its local artifacts. That is the position of a cloud agent (OpenAI, Anthropic),
and of anyone else who has the repository and nothing more.

[`CLAUDE.md`](CLAUDE.md) is the reference: architecture, environment, testing,
privacy, and the outcome the project steers at ("The Cap"). Read it first. This
file only says what changes when a clone is all you have.

## What you do not have

| You lack | So |
| --- | --- |
| The dataset passphrase (`TEXT_CONFIG_PASSPHRASE`). The corpus is tracked encrypted, as `argumentation_analysis/data/extract_sources.json.gz.enc`. | You cannot read a corpus document. Tests marked `requires_dataset_passphrase` skip. Work on synthetic texts; do not try to obtain, rebuild or stand in for the corpus. |
| API keys (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`). | No pipeline run, no judge, no paid run of any kind. |
| The roosync dashboards and messages (`CLAUDE.md`, "RooSync Cluster Topology"). | Your channel is the issue and the pull request. |
| The seats' local artifacts: recorded panel states, judge outputs, `.tmp/`, `argumentation_analysis/evaluation/results/`. All are gitignored. | Absent from your clone is not absent. An artifact an issue cites exists on the seat that produced it; the issue should give you synthetic inputs that reproduce the behaviour, and when it does not, ask there. |
| Merge rights and a budget. | Merges and paid spends stay with the coordinator (`CLAUDE.md`, "When v1 Is Done"). Open the pull request and stop. |

## What you can take

Issues labelled `seat-free`: every step of their contract runs on a keyless
clone. Their shape is [`.github/ISSUE_TEMPLATE/dispatchable.md`](.github/ISSUE_TEMPLATE/dispatchable.md).

An issue without the label may need a seat for one step (a replay on recorded
states, a paid measure). Do the keyless part, and name in the pull request the
step you left to the coordinator.

The seats take issues in the order of the open issue labelled `queue`
(`gh issue list --label queue --state open --json number,title`). Among the
`seat-free` issues, prefer one it lists, neither struck through there nor
claimed in the issue's comments, and read the issue's latest "State on <date>"
comment before its body, which that comment may supersede.

## Running things without keys

**Environment.** CI builds its environment from `conda-lock.yml`, which targets
`win-64` only, and runs on `windows-latest`. On another platform you solve
`environment.yml`, and what you run is then not what the gate runs
(`CLAUDE.md`, "Gate versions"). CI on your pull request decides, not your local
run.

**Tests.** Target what you touched, with the gate's own marker filter
(`.github/workflows/ci.yml`, job `automated-tests`):

```bash
python -m pytest tests/unit/<path>/test_<file>.py -v -m "not slow and not requires_api"
```

Keep the filter on every run. The automatic skip of `requires_api` tests fires
only when none of `OPENAI_API_KEY`, `GITHUB_TOKEN` and `OPENROUTER_API_KEY` is
set (`conftest.py`), so a sandbox that exports `GITHUB_TOKEN` would run them.
The gate names its directories one by one; `pytest tests/` whole is not a gate
(the workflow's comments record a full run killed at the six-hour job limit).

**Java.** The logic tests need the Tweety classpath and a JDK.
`scripts/ci/provision_tweety.py` assembles them and `scripts/ci/verify_tweety.py`
checks them — the two steps CI runs. Without a usable classpath the suite
reports skips, not errors (the workflow records a run at 15,010 skipped and 0
passed). `--disable-jvm-session` (`tests/conftest.py`) mocks `jpype` for the
whole process: right for a change that needs no Java, and no proof for one that
does, since the JVM tests are then skipped rather than failed
(`docs/guides/java_integration_handbook.md`, §2.2).

**Read the counts, not the colour.** `-rs` prints why each test was skipped. A
green run with your test among the skipped has not tested your change.

**Format, lint, types.**

```bash
black --check --diff <files you changed>
flake8 <files you changed>
```

CI runs both over `argumentation_analysis/ tests/ api/ project_core/` as
informational steps. The blocking step of `lint-and-format` is `mypy` in strict
mode over the core orchestration files it lists: if you touch one of them, run
the command of the step "Type check (mypy strict — core orchestration)" as
written in `.github/workflows/ci.yml`.

**Privacy scan.** Standard library only, no project environment needed; CI runs
the first form before it builds the environment:

```bash
python scripts/security/scan_indexed_surfaces.py --commits origin/main..HEAD
python scripts/security/scan_indexed_surfaces.py --text-file <your PR body>
```

## What CI tells you about your pull request

A pull request against `main` gets `lint-and-format` and `automated-tests`
(`.github/workflows/ci.yml`), and `replay-band`
(`.github/workflows/requires_api_band.yml`), which replays the `requires_api`
tests against committed cassettes without a live call. The other two jobs of
that workflow, `requires-api` and `report-main`, show as skipped: the paid band
runs on schedule or manual dispatch only.

In `automated-tests`, pytest runs only when the repository's `OPENAI_API_KEY`
secret reaches the run. When it does not — the workflow names forks and
external contributions — the step "Run automated tests" is skipped, a step
"Notify tests skipped" runs in its place, and the job can still end green: a
green that measured nothing. Say in the pull request which of the two you got;
the "TEST EXECUTION SUMMARY" block of the job log tells you.

## Where code goes

- New code inside `argumentation_analysis/`, tests under `tests/`. No new
  module at the repository root (`CLAUDE.md`, "Repository Structure").
- A new capability goes on the surface `setup_registry()` populates, and gets a
  consumer (`docs/architecture/CAPABILITY_CENSUS_GUARDS.md`).
- A test that would reach an LLM carries `@pytest.mark.requires_api`, so the
  gate's filter deselects it. Why this matters is measured in
  `tests/unit/test_gate_deselects_egress_leakers_1872.py`.
- A change to `environment.yml` needs `conda-lock.yml` regenerated in the same
  pull request with conda-lock 4.0.4 (`CLAUDE.md`;
  `tests/unit/test_conda_lock_matches_environment_1803.py` guards the pair). If
  you cannot produce the `win-64` lock, leave dependencies alone and describe
  the need in the issue.

## What a pull request carries

- **Title**: a conventional commit that states what is now true, with the issue
  number — `fix(reading): a quote the citation rule accepts has an offset (#3517)`.
- **Body**: `Closes #N`, what was measured before and after, and the command
  that reproduces it.
- **A free witness**: a test that is red before the change and green after, on
  synthetic inputs — no LLM, no network, no corpus.
- **A mutation control**: undo or break the fix and show the witness goes red
  again. A grep that finds the new line is not a control.
- **The neighbours**: run the tests that import what you changed, not only the
  new file, and give the passed and skipped counts.
- **Deletions** follow the Cleanup Gate (`CLAUDE.md`): a `## Files removed and
  why` section with each file's role and a one-sentence reason, the origin
  check `git log --all -- <path>`, and a table above five files.
- **No workaround**: a guard that blocks you is repaired or reported, never
  weakened, skipped or ignored (`CLAUDE.md`, "STOP&REPAIR").

## Privacy, on every surface GitHub indexes

Commit messages, pull request and issue titles, bodies and comments, and every
tracked file:

- opaque ids only (`doc_A`, `corpus_001`, `src0_ext0`) — no author, title,
  speaker or date of a source;
- no document identifier in any tracked file, fixtures, comments and detector
  pattern lists included;
- never plaintext corpus content, never a decrypted snapshot; analysis outputs
  go under gitignored paths.

The full rules are in `CLAUDE.md`, "Dataset Privacy Discipline".

## When the issue is not enough

Ask in the issue. Do not guess a missing measurement, do not widen the scope,
and do not replace a seat-bound step with an approximation: name the step and
leave it to the coordinator.
