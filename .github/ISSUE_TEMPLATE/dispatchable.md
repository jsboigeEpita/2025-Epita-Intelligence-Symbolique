---
name: Dispatchable issue
about: "A defect or a task with a self-contained contract: a worker or a cloud agent can take it from the issue alone"
title: "<area>: <what was measured, in one sentence>"
labels: ""
assignees: ""
---

<!--
A dispatchable issue is taken from the issue alone: whoever picks it up has a
clone, this text, and nothing else (see AGENTS.md). Fill every section, then
delete these comments.

This surface is indexed by GitHub: opaque ids only (doc_A, corpus_001). No
author, title, speaker or date of a source.
-->

## What was measured

<!--
The observation, with its figures and where they were read: which field of
which artifact, which command. A table beats a paragraph.

If the measure lives on a seat (recorded states, a paid run), say so, and give
the synthetic inputs that reproduce the same behaviour on a keyless clone.
Never state more than was measured.
-->

## Mechanism

<!--
Where it happens: file, function, and the path from the code to the figures
above. One numbered item per mechanism.

If the cause is not established, write "cause not established" and make
finding it the first ask.
-->

1. …

## Files in scope

<!--
The files the change is expected to touch, and the readers of what it changes
(a field and whatever consumes it). Name what is OUT of scope when a neighbour
is tempting.
-->

- `path/to/file.py` — …

## Asks

<!--
Numbered, each one checkable. An ask says what must be true afterwards, not
how to write it.
-->

1. …

## Definition of Done

- [ ] Each ask is met, or the pull request says which one is not, and why.
- [ ] The witness below is red on `main` and green on the branch.
- [ ] Mutation control: with the fix undone or broken, the witness is red again.
- [ ] The tests that import the changed modules pass; passed and skipped counts are given.
- [ ] `black --check` is clean on the changed files; `mypy` too, if a file of the CI's strict list is touched.
- [ ] The privacy scan is clean on the commits and on the pull request body.

## Witness (free: no key, no network, no corpus)

<!--
The command that decides, runnable on a keyless clone and in CI. Say what it
shows before and after the change.

Positive control: the fact that proves the witness can see the defect — for
instance, it reproduces the measured figure on `main`.

If one step can only be done on a seat (a replay on recorded states, a paid
measure), name it here and leave it to the coordinator.
-->

```bash
python -m pytest tests/unit/<path>/test_<name>.py -v -m "not slow and not requires_api"
```

## Not

<!--
The false fixes this issue does not want, one line each, with the reason.
Typical ones: raising a bound that only moves the cut; removing or loosening
the check that reddens; a fix that is right for this one input only; undoing
the decision of an earlier issue.
-->

- Not …

## Where it can be done

- [ ] **Seat-free** — every step above runs on a keyless clone. Add the label `seat-free`.
- [ ] **Needs a seat** for: … (dataset passphrase, API key, recorded states, paid run). The rest is seat-free.

## Privacy

Opaque ids only in this issue, in the pull request and in the commits. No
document identifier in any tracked file, fixture or comment; tests use
synthetic texts. Rules: `CLAUDE.md`, "Dataset Privacy Discipline".

Refs #…
