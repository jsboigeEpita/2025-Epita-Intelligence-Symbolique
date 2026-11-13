# Panel cycle runbook

How to run one cycle of the v1 panel bar (Epic #3374, `CLAUDE.md` § "When v1 Is
Done"), read it, and turn it into the next batch of work. Written for whoever
holds the coordinator role: paid runs and merges stay with the coordinator.

A **cycle** is: the whole panel through the pipeline once, each judge family
over it several times, a consensus per family, then the free instruments that
say *where* the pipeline lost each item the judges raised. The instruments
live in [`scripts/panel/`](../../scripts/panel/); the judge and the two arms
live in [`scripts/dataset/`](../../scripts/dataset/).

## 1. What stays on the seat

Nothing below is in git, and nothing below may enter it (`CLAUDE.md` § "Dataset
Privacy Discipline"). All of it sits under
`argumentation_analysis/evaluation/results/`, which is gitignored:

| Path under `results/` | What | Made by |
|---|---|---|
| `panel_v1/panel.txt` | the panel: one document id per line | the coordinator, once (#3375); kept on the coordinator seat |
| `panel_v1/zeroshot/` | the zero-shot arm: one answer per panel document | `scripts/dataset/run_zeroshot_arm.py --panel-file <panel>`, then a frozen copy |
| `panel_cycles/<tag>/` | one cycle: `states/`, `signatures/`, `logs/`, `status.jsonl`, `pipeline.json`, `cycle.json`, `trace.jsonl` | `scripts/panel/run_cycle.py` |
| `judge_panel_3375_<tag>_<judge>_p<i>/` | one judge pass: a row per document, `META.json`, `TABLE.md` | `scripts/dataset/judge_panel.py` |
| `judge_panel_3375_<tag>_<judge>_cons<k>/` | the consensus of `k` passes, `STABILITY.md` against the previous cycle | `judge_panel.py --consensus` |

The panel's composition is passed **by path** to every script. No tracked file
lists the panel's ids, and a test keeps it so
(`tests/unit/scripts/test_panel_cycle_3374.py`, `TestPrivacy`).

The zero-shot arm is frozen on purpose: the same answers are judged against
every cycle, so what moves between two cycles is the pipeline. Produce it
again only when the pipeline's model changes, and say so in the cycle's
report.

On a seat that has neither file, the panel comes from the coordinator (private
RooSync channel, never an issue or a PR) and the zero-shot arm is produced
with the command above.

## 2. When to launch

A cycle is worth paying when merged fixes have not been measured on the panel
yet. Write the criterion and the expected cost in the dispatch before
launching. Orders of magnitude from the last cycles, for ten documents: about
11 $ on the OpenRouter key (pipeline and six passes of an OpenRouter judge),
about 2 $ for six passes of an Anthropic judge through Message Batches, under
1 $ for the classification of §5. The real spend is read after the run, never
assumed (§4).

Before paying, in this order:

1. `git status` is clean and `HEAD` is the commit to measure. **Do not check
   out, pull or switch branch in this clone while the pipeline runs**: the
   documents would not all run the same code, and the runner stops the cycle
   when it sees `HEAD` move. Do not run a cycle from a `git worktree` either:
   the JVM side of the pipeline reads untracked files of the main clone.
2. Run from the seat's environment (`docs/guides/DEV_ENV_SEATS.md`). The
   runner launches every command with the interpreter that launched it.
3. `python scripts/panel/openrouter_credit.py` — the key must have more left
   than the cycle costs. `--min-credit` makes the runner refuse otherwise.
4. Print the plan and read it: every command, in order, with the paid ones
   marked.

```bash
R=argumentation_analysis/evaluation/results
python scripts/panel/run_cycle.py --tag <cycle> \
    --panel-file $R/panel_v1/panel.txt --zeroshot-dir $R/panel_v1/zeroshot \
    --judge g=gemini-4-argon,env.OPENROUTER_CHAT_MODEL_ID=google/gemini-4-argon \
    --judge s=claude-sonnet-5-5,batch \
    --passes 6 --partial-consensus 3 --compare-with-tag <previous cycle> \
    --min-credit 12 --plan
```

A judge is `NAME=MODEL`: the name enters the directory names, so keep the same
letter from one cycle to the next or `--compare-with-tag` finds nothing. The
judge must be of another family than the pipeline's model (the judge script
refuses otherwise). `batch` routes an Anthropic judge through Message Batches
at half price. `env.KEY=VALUE` is set for that judge's commands only: an
OpenRouter judge needs the model id of its route there.

## 3. Launch

The same command without `--plan`. It is long: start it in the background and
read `status.jsonl` when it ends — one observer, no polling loop on top.

What the runner does, and where it stops (each stop was paid for once):

| Step | Stops the cycle when |
|---|---|
| reads the panel, the zero-shot arm and the credit | a panel document has no zero-shot answer; the credit left is not above `--min-credit` |
| pipeline on the panel | its exit code is not 0 — no paid judge on a failed batch |
| reads `HEAD` again | it moved during the pipeline |
| harvest into `panel_cycles/<tag>/` | a panel document has no state or signature written during this run (an older file belongs to an earlier cycle) |
| per judge: dry-run | the dry-run fails: the route does not resolve, or an arm is degraded beyond the judge's threshold |
| per judge: passes | a synchronous judge's first pass did not judge the whole panel — the other passes are not paid |
| per judge: consensus | a pass is incomplete — no consensus of fewer passes than planned |
| free tracer on the full consensus of the families that completed | — |

Exit code 0: the cycle ran whole. 1: it stopped before any judge. 2: a judge
family did not complete.

**Resuming.** `--stage judges` re-runs the judges on a harvested cycle and
skips every pass whose stored rows already cover the panel: nothing is paid
twice. `--stage consensus` rebuilds the consensus and the trace and pays
nothing, whatever it finds. An Anthropic batch that was submitted but not
retrieved is resumed by hand with `judge_panel.py --batch-id` (its results
live 29 days), then `--stage consensus`. `--stage pipeline` runs the pipeline
and the harvest alone.

A resume never rewrites what the pipeline did. The pipeline stage writes
`pipeline.json` once — the commit, the tree and the dirty flag its states were
produced at, its exit code, `HEAD` after the run, the harvest — and a resumed
invocation only reads it. `--stage judges` refuses a pipeline recorded as
failed, for the three reasons the full run stops on (exit code, `HEAD` moved,
incomplete harvest): resuming is not a way round them. A cycle harvested
without the runner has no record; the runner says so (`pipeline_unrecorded` in
`status.jsonl`) and the commit of its states is then whatever the operator
wrote down, not something the cycle can prove.

## 4. Read the cycle

- `panel_cycles/<tag>/pipeline.json` — the commit the states were produced
  at. This is the commit a cycle's verdict is about.
- `panel_cycles/<tag>/cycle.json` — the last invocation: its command and its
  own `HEAD`, the exit code of every step, the credit before and after and
  `openrouter_spent`, and the pipeline record again under `pipeline`. After a
  resume the two commits differ, and the one that counts is the pipeline's.
  An unread credit is reported as unread, not as zero.
- `judge_panel_3375_<tag>_<judge>_cons<k>/TABLE.md` — the verdict table of one
  family. `STABILITY.md` beside it compares the items kept with the previous
  cycle's.
- An Anthropic judge's cost is in its pass tables (`judge_cost` per row); it
  is not on the OpenRouter key.

The cycle's report (the coordinator's `DONE`) carries the verdict table per
family and the count for condition 2 of the exhaustion rule: two consecutive
cycles without the pipeline-versus-zero-shot verdict progressing.

Read the renders too. A table is a report about the output; the mandate is the
output (`docs/guides/RENDER_REPRODUCIBILITY.md`).

## 5. From the verdict to defect classes

All of this is free except the last two commands, and all of it reads the
recorded cycle: no pipeline run.

**Where each item was lost.** The runner already wrote it:

```bash
python scripts/panel/trace_items.py --states-dir $R/panel_cycles/<tag>/states \
    --consensus-dir $R/judge_panel_3375_<tag>_g_cons6 $R/judge_panel_3375_<tag>_s_cons6 \
    --out $R/panel_cycles/<tag>/trace.jsonl
```

For an observation the judge says the analysis misses (M1), the stage is the
first hop that fails: the quote is not found in the document (`unlocated`);
no reading names the passage and no unit covers it (`not_named_no_unit`); the
first reading names it but no unit covers it (`named_no_unit`); a unit covers
it but the per-argument pass did not examine it (`unit_not_examined`); it was
examined and nothing was retained (`examined_no_finding`); a finding exists
and no act renders it (`found_not_rendered`); an act carries the passage and
the judge still raised it (`rendered_judge_disagrees`). For a claim the
document contradicts (M2), the stage names the acts that carry it.

**Would a change to the selection examine more of them?** Check out the
change, then:

```bash
python scripts/panel/replay_selection.py --states-dir $R/panel_cycles/<tag>/states \
    --passages-from $R/judge_panel_3375_<tag>_g_p[1-6] --min-chars 6016 \
    [--budget 45 60] [--moves-dir <draws>/d1 <draws>/d2 <draws>/d3]
```

`today` is what the checked-out code would select on the recorded states; the
other columns force a budget or replace the first reading's moves.
`--min-chars 6016` keeps the documents longer than one extraction call
(`WHOLE_TEXT_CALL_CAPACITY` in `core/reading_window.py`): the only ones where
a budget rations.

**Does the recorded first reading name them?**

```bash
python scripts/panel/first_reading_draws.py calibrate \
    --states-dir $R/panel_cycles/<tag>/states \
    --passages-from $R/judge_panel_3375_<tag>_g_p[1-6] --min-chars 6016
```

Three rules decide whether one of these counts means anything. Each has cost a
paid cycle or a wrong conclusion; the incidents are in
[`MEASUREMENT_DISCIPLINE.md`](MEASUREMENT_DISCIPLINE.md).

1. **Fidelity.** A replay is a measure only where it reproduces the recorded
   selection: same unit ids, same population size. Each line says which
   population did (`production`, `merged_only` for a state recorded before
   #3518), `no_record`, or `unfaithful`. On an `unfaithful` document nothing
   is a measure, and `replay_selection.py` exits 2.
2. **The random control.** "X of Y passages examined" is read against the same
   passages redrawn elsewhere in the text (`random`). A selection that covers
   most of a text examines most passages by chance. Each passage is redrawn
   **on its side of the record**: the passages a cycle's own judge raises are
   the ones that cycle missed, so drawn anywhere some would land where the
   run did examine, and a real gain would read as chance. Measured on cycle
   6 at budget 45, on the 33 passages with an unexamined unit: 12 examined,
   against 12.3 drawn anywhere and 7.7 drawn where the run had not examined.
   The reading's control (`first_reading_draws.py`) redraws the anchors and
   is not matched this way. Either way, confirm a change on the passages of
   the next cycle.
3. **Three draws.** A step with a model call upstream is read on three draws
   or more: minimum, mean, spread. One draw that passes a bar shows the bar
   can be passed once.

**Paid, optional.** A stronger model sorts the traced items into defect
classes (under 1 $; `--dry-run` first prints the estimate):

```bash
python scripts/panel/classify_items.py --states-dir $R/panel_cycles/<tag>/states \
    --trace $R/panel_cycles/<tag>/trace.jsonl \
    --out $R/panel_cycles/<tag>/classes.json --dry-run
```

and the first reading is redrawn live on the checked-out code (one call per
document and per draw; the draws feed `replay_selection.py --moves-dir`):

```bash
python scripts/panel/first_reading_draws.py paid --draws 3 \
    --states-dir $R/panel_cycles/<tag>/states \
    --passages-from $R/judge_panel_3375_<tag>_g_p[1-6] --min-chars 6016 \
    --out-dir $R/panel_cycles/<tag>/first_reading_draws
```

The tracer's stage is the measure; the model's class is a reading of it.
`RENDERED_UNSEEN` and `JUDGE_WRONG` are not pipeline defects and open no
issue.

## 6. From classes to the next batch

One issue per class, never one per item, with the class's count and stage in
the body and opaque ids only. Sort by severity; a worker takes several per
cycle. An issue whose whole contract runs on a keyless clone gets the label
`seat-free` ([`AGENTS.md`](../../AGENTS.md)) and follows
`.github/ISSUE_TEMPLATE/dispatchable.md`; any other issue names the seat it
needs.

A fix is measured free before it is measured paid: replay the recorded states
through the fix (§5) and state the control. The next cycle is launched when
the criterion of §2 holds again.

## 7. Privacy

- Every instrument refuses to write where git would track the file.
- stdout carries counts and the ids the script was given; quotes go to the
  gitignored outputs only.
- On GitHub (commits, PR and issue text): opaque ids, counts, classes. Scan
  before pushing: `python scripts/security/scan_indexed_surfaces.py --commits <range>`.
- Private RooSync dashboards and messages may name documents.
