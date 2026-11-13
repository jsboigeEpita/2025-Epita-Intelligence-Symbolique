# Measurement discipline

What decides before a figure is trusted, a paid run is launched, a guard is believed, or a pull
request is merged — distilled from the coordinator seat's local method notes, so that a worker or
a cloud agent can apply it without that seat's memory. Each rule comes with the incident that
founded it (figures as measured on this repository at the time) and its instrument. Documents are
named `doc_A`, `doc_B` (dataset privacy, `CLAUDE.md`).

**Before quoting a figure, name its population, its instrument, and what the instrument would have
printed if the claim were false.** If that is "the same thing", it is not a measurement.

## 1. Before measuring — can this instrument answer the question?

### 1.1 A zero counts only after the same instrument has returned a positive

Run the probe on a population known to be non-empty before reading its zero, and check that the
code that decides actually executed on the path measured.

- **Measured.** `grep -cE "^FAILED "` on a CI log returned 0: every line carries a prefix, so the
  anchor could not match. A guard "admitting 0 of 66" had never run: the run's log held no line
  from its module (#1668).
- **Instrument.** Prefer what prints its own census: the pytest summary line (no summary line
  means the suite did not run, #1799), `scanned N commit message(s)` from the privacy scanner, the
  consumer's logger name in the run's log.

### 1.2 "Not visible from my tree" is not "does not exist"

Run artifacts are gitignored (`argumentation_analysis/evaluation/results/`, `.tmp/`): they live on
the seat that produced them. Symmetrically, a cited artifact is evidence only if its reader can
open it.

- **Measured (#2045).** A measure cited a state file that a local `find` did not return; it existed
  on the other seat, and the two disagreeing measures read two different objects.
- **Instrument.** Ask for a transportable meta without document text (keys, counts, statuses, text
  reduced to `<text N chars>`) and open it. Until then, write "not visible from here".

### 1.3 A census built on one literal measures that literal

A grep for a name finds the name, not its class; and "no reader", "zero importer", "dormant" are
the verdicts nobody re-tests. Before retiring anything, look for the reader that takes the key as
a variable, the lazy import inside a function, the caller under `scripts/`, the `__main__` entry.

- **Measured.** A privacy census of 8 tracked files for one identifier missed a second identifier
  of the same class on 3 other files. 3 of 4 sampled "zero importer" verdicts were false. A sidecar
  retired as "no consumer" had a generic reader taking the leaf name as a parameter (#2952, #2956).
- **Instrument.** `git grep` is the authority on what the tree holds (ripgrep honours ignore files
  and skipped a tracked file in that census). Search by pattern, then by producer; quote a count
  with its root directory. Real data without a consumer is a wiring defect to open, not dead code.
  Capability counts: [`CAPABILITY_CENSUS_GUARDS.md`](../architecture/CAPABILITY_CENSUS_GUARDS.md).

### 1.4 A field and its reader (the #1019 family)

A value reaches the reader only if a producer writes it, under the name the reader reads, on the
lane the run takes. Forms measured so far:

- read and never written (a phantom key reads as a fabricated 0), or written and never read;
- the test fixture is the field's only producer;
- a fallback fires after an honest "absent" (#1629; the fix was a subtraction);
- true at each site, false once summed (#1698: count distinct fingerprints, not occurrences);
- a success message read as an error by 4 of 5 callers (#2639, repaired at the producer); a new
  status value meeting a consumer that tests `!= "ok"` instead of enumerating failures.

**Instrument.** For one field: its producers, its readers, and its value in a state serialized by
a real run — never in a fixture.

### 1.5 An overlap count is read against random spans

"X of Y passages are covered" says nothing without the count expected from spans drawn at random,
in the same number and with the same lengths.

- **Measured (#3511, #3516).** 4 of 39 observed against 5.6 expected at random: chance level.
  Another probe gave 26 against 14 at random: a real signal, half of which was density.
- **Instrument.** Draw random spans (same count, same lengths; 2000 draws were used), report
  observed next to expected, and state the bar as a ratio over that control. Two corollaries: a
  bound the model does not fill does not bind (measure the fill rate before raising a cap); and
  measure with production's own locator — a bar calibrated on a probe's lenient locator (98 %)
  failed on production's (83 %, #3517).

### 1.6 Also measured

- **Count a loss hop by hop.** "12 phases lost" was 8: four reached the conclusion through an
  indirect channel (#1605, #1626). At each hop ask "is there a direct reader?" and "is there
  another channel?"; find the indirect channel from the writer, not by grepping the field's name.
- **A synthetic witness shows the mechanism; recorded states show the magnitude.** A synthetic
  passage put 6 of 6 lexical virtue detectors at their maximum, where the median fraction on real
  arguments was 0.283; three synthetic texts were posted as decisive while the same measure
  existed on 170 real arguments (#1907). Report a synthetic test as "the code path works".
- **Search the tracker, not only the code.** #1659 re-opened #1635, written seven rounds earlier
  by the same seat: `gh issue list --state all --search "<symbol or key> in:body"` first.

## 2. Before a paid run

Everything that can be learnt without paying is learnt first. Paid spends stay with the
coordinator (`CLAUDE.md`, the panel bar); a worker proposes a run with its count and expected cost.

### 2.1 Replay for free on recorded states first, and prove the replay

Before paying to see whether a change does anything, run the changed function on the states the
last paid cycle recorded. The replay is trusted only with its positive control: **at the base
commit, it reproduces the figure the recorded states carry.**

- **Measured.** #3492, #3495: 0 of 3 measured anchors reached the new pass's prompt — found for
  free instead of by a 1.5 $ probe. #3481: a deterministic check replayed on the recorded panel
  states fired on 2 of 10 documents, once wrongly.
- **Instrument.** Load base and head as two modules, each from a snapshot
  (`git show <sha>:<path> > .tmp/base.py`, then `importlib`); run both on every recorded state and
  print `base == recorded` per state. A deterministic check passes when it fires on the known true
  case and on no other recorded document. Never take the base from the shared checkout: during a
  union the checkout is the union, base equals head, two identical zeros come out (#3250, #3252).

### 2.2 "In the prompt" is not "in the render"

A prompt fix does not rewrite a recorded state: the text a model wrote is stored verbatim in the
state, and the renderer copies it. A render belongs to the commit of the run that produced it.

- **Measured (#3259, #3283).** A render produced before a fix was judged against the fixed code.
- **Instrument.** Read `git_head` in the render's provenance header. Re-render from the recorded
  state first: it costs no model call, and the recomputed invariants (cost identical to four
  decimals, annexes unchanged) prove the re-render faithful. Only a new paid run shows what the
  prompt change does. Convention: [`RENDER_REPRODUCIBILITY.md`](RENDER_REPRODUCIBILITY.md).

### 2.3 One draw of an LLM stage measures one draw

A bar on a stage that calls a model is read on **at least three draws**: minimum, mean, and
dispersion per document, saying which of them the bar is set on.

- **Measured (#3511).** The same call drew 26, 11, 20, 14 and 19 of 39. A change accepted on one
  draw at 26/39 gave 11/39 in the next production run (chance: 11.6). Three more draws cost
  0.086 $. Most of the variance sat on one document; another, `doc_B`, stayed at 0 of 11 on every
  draw — re-drawing is not its repair.
- **Instrument.** N ≥ 3 identical calls, one row per document, the random control of 1.5 beside
  it. A "near the named passage" criterion is at chance from a window of about 1000 characters:
  exact span overlap is the criterion that carries signal.

### 2.4 Seams doubled in tests fail on the first real run

Every seam a test replaces (transport, paths, route, model answer) is untested by that test.

- **Measured.** A judge runner with about 70 green witnesses failed three ways on its first real
  run (#3401 default directories, #3402 an endpoint answering 404 with exit 0, #3404 a token cap):
  1.37 $ lost. A transport double more tolerant than the real consumer let a judge score stub
  output (#3450); since #3458 and #3462 the judge refuses a degraded arm (exit 3).
- **Instrument.** `--dry-run` with no path or route override, reading where it returns (#3478: it
  returned before the route seam). One real call on the longest panel document, then 1–2
  documents, before the whole panel. A failed or truncated call exits non-zero and keeps the raw
  answer with its stop reason. In tests, keep the callee real and fake only the completion.
- **"One or N paid runs" means one.** A request for "a corpus analysis to present" meant one
  document; 49 were dispatched (#2841). The run count is written in the dispatch.

## 3. Before trusting a guard or a green run

### 3.1 The control of a guard is a mutation, never a grep

A test proves something only if a degenerate substitute makes it fail.

- **Measured (#1588, found while auditing #1585).** `assert isinstance(result, dict)` as the only
  assertion; a terminal `or`; `in ("a", "b")` accepting both branches.
- **Instrument.** Replace the function under test by `{}`, `None` or a `MagicMock()`, or revert
  the fix, and watch the test go red. Tighten the assertion on the named property; do not delete
  the test.
- **Then mutate the input.** A conclusion gate died under three code mutations and removed nothing
  from the real prose of three corpora: its vocabulary and the model's were disjoint (#1605,
  #1609). On a recorded state, degrade the input to the absurd and check that the output changes.

### 3.2 A targeted green run is not its neighbours

- **Measured.** #2776: two CI reds after green targeted runs (the neighbour set was 34 files, 435
  tests, 5 minutes). #2937 against the README-citation guard (#2669). #3193 against the
  unbounded-prompt census (#2908): 1 failure in 19,198.
- **Instrument.** `git diff --name-only origin/main...HEAD`, then `git grep -l` the touched module
  and directory names across `tests/`, and run that whole set in one pytest call. A new test file
  ⇒ the guards that scan `tests/`. A `.md` touched under `argumentation_analysis/`, or a symbol
  retired ⇒ the README-reading guards. A new prompt line carrying document text ⇒
  `test_unbounded_prompt_census_2908.py`. Most population guards sit at the root of
  `tests/unit/argumentation_analysis/`; a review brief names the ones that apply.

### 3.3 The local union run

The local replay of the gate — one branch, or several PRs merged together — runs in the lock
environment, without the user-site, on 4 workers, with the gate's marker filter, **in the main
clone and never in a linked git worktree**: a worktree has no JDK, no Tweety jars and no `.env`,
so JVM tests and key-gated tests skip there in silence.

```bash
PYTHONNOUSERSITE=1 conda run -n projet-is-lock --no-capture-output python -m pytest \
  <the paths of the pytest line in ci.yml> -m "not slow and not requires_api" -n 4 -q
```

- **Measured.** Without the marker filter, a green `3530 passed` had made 3,057 real model calls
  through the seat's `.env`; and the filter is not an egress guard either: three new unmarked
  tests made 86 real calls under it (#2989). A dev environment had drifted 52 package versions
  from the lock and lacked 2 packages: false reds (#3304). `-n auto` started 24 workers holding
  about 37 GB on a shared machine.
- **Instrument.** Read the `LLM egress (#1787)` line before the pass count; under `-n` it was
  blind until #3120, so if it reports that its control did not run, replay the touched files in
  one process. Reconcile the test count with the previous union: `tests/unit` alone is about 1,400
  tests short of the gate. `env -u KEY` protects nothing (the conftest reloads `.env`). Do not add
  `LLM_CACHE_MODE=replay`: the gate does not set it. Environments per seat:
  [`DEV_ENV_SEATS.md`](DEV_ENV_SEATS.md).

### 3.4 Also measured

- **Ask which branch the green suite took.** 40 green tests all ran the "JVM unavailable" branch
  under `--disable-jvm-session`; the repaired branch had 2 (#1776, #1773). Read `-rs`: "1 passed,
  1 skipped" proves nothing about the skipped half.
- **A test the harness never names is not a guard.** Three guards lived in directories the gate
  did not run (#1778, #1776, #1782); one had been red on `main` since #723. The perimeter is
  the pytest line of `.github/workflows/ci.yml`; widening it is a user decision (#1867).
- **Run a new guard first on the diff that introduces it.** A PR added a guard refusing a degraded
  value shape at export and committed three cassettes carrying that shape (#1792).
- **A historical witness names a commit sha.** A born-red witness reading `origin/main:<file>`
  passed on the PR and on the union replay, then reddened `main` after the squash: the moving ref
  now held the fix (#2859). Use `git show <sha>:<path>`.
- **A fix reaches only what it constructs.** A transport-level fix was reported "repaired"; one
  construction path used that transport, 18 other sites built a bare client (#2387, #2391).
- **Shell forms that fabricate a result.** A scan chained by `&&` after `grep -c` is skipped
  exactly when the count is 0, because `grep -c` then exits 1 (#3276): run each scan alone. A wait
  loop testing a field that is empty while waiting exits at once and announces completion (#2058):
  wait on an enumerated status. `gh pr diff N` can return nothing with exit 0 on a server error
  (#1481): check its line count. `"checks": []` is an absent CI, not a green one (#2162).

## 4. Before merging

### 4.1 A sequence of green PRs ships an untested union

- **Measured.** #2556 and #2467 were each green; `main` was red after both (repaired in #2565).
  Again with #2714, #2717 and #2721: 1 failed of 16,190.
- **Instrument.** In a batch, look for a PR whose test walks a population and another PR that adds
  a member to it. Replay those population guards on the merged union in gate mode (`CI=true`,
  3.3). A clean `git merge-tree` speaks of text, not of tests.

### 4.2 Authorship is read from local provenance

The whole fleet pushes under one GitHub identity: the `author` field is constant, and the commit
email follows whichever `gh` account was active. "Was this branch written on this seat?" is
answered by the local reflogs, with a positive control on each surface.

- **Measured (#2354).** A branch written here in a linked worktree returned 0 on the main reflog:
  a false "not mine", the direction that licenses a merge.
- **Instrument.** Commands and decision table: `.claude/commands/coordinate.md`, section
  « Contrôle d'autorat ».

### 4.3 Also measured

- **A stacked branch does not follow its base.** "#1947 and #1948 contain my commit" was false:
  they descended from an earlier state of the base, and merging them after the base's squash would
  have undone the repair. Check with `git merge-base --is-ancestor <sha> origin/<branch>`.
  Retarget the child before deleting the base (deleting it closes the child), then close and
  reopen the child: a retarget triggers no CI run.
- **A sliced issue is re-read whole before it closes.** Six slice PRs merged; 1 of 8 acceptance
  criteria held (#1914). Closing keywords ignore negation: "does NOT close #2130" closed it
  (#3026). Read `gh pr view N --json closingIssuesReferences` before every merge.
- **A review state cannot fire across one identity.** GitHub refuses "request changes" on one's
  own pull request, and every worker PR is the coordinator's own (#1792). Objections live in the
  PR comments: read all of them.
- **A squash takes the branch's commit message.** A PR's title and body had been scrubbed; the
  squash built the commit on `main` from the branch's original message (#1503). Merge with an
  explicit `--subject` and `--body-file`, then scan what landed:
  `python scripts/security/scan_indexed_surfaces.py --commits <previous main>..origin/main`.
- **An artifact newer than its producer's last success was harvested by hand.** 211 cassettes were
  committed while the job that produces them had last succeeded a month earlier (#2323, #2321).
  Date the producing job's last success against the artifact's commit.

## Related pages

[`RENDER_REPRODUCIBILITY.md`](RENDER_REPRODUCIBILITY.md) (a render is cited with the command that
reproduces it; the final judge is the text, read) ·
[`CAPABILITY_CENSUS_GUARDS.md`](../architecture/CAPABILITY_CENSUS_GUARDS.md) ·
[`DEV_ENV_SEATS.md`](DEV_ENV_SEATS.md) · `CLAUDE.md` (STOP&REPAIR, the panel bar, dataset privacy)
· `.claude/commands/coordinate.md` and `worker-round.md` (the round protocols).
