# Corpus Batch Runner

Process the encrypted corpus through the analysis pipeline and produce
per-document sanitized signatures.

## Quick Start

```bash
# Full batch (from repo root, conda activated)
python scripts/dataset/run_corpus_batch.py --workflow spectacular

# Limit to N documents
python scripts/dataset/run_corpus_batch.py --max-docs 5

# Skip already-processed documents
python scripts/dataset/run_corpus_batch.py --skip-existing

# Skip very long documents (> 15K chars)
python scripts/dataset/run_corpus_batch.py --max-chars 15000
```

## Resume Mode

Long batches can be interrupted (session close, timeout, crash).  Use
`--resume` to pick up from per-document checkpoints instead of restarting
each document from scratch.

```bash
# Resume an interrupted batch
python scripts/dataset/run_corpus_batch.py --resume

# Resume + skip existing signatures
python scripts/dataset/run_corpus_batch.py --resume --skip-existing
```

### How It Works

After each DAG level in the workflow, a checkpoint file is written
atomically to `.analysis_kb/checkpoints/<doc_id>.checkpoint.json`.  The
checkpoint captures:

- Completed phase names and their serialized outputs
- State snapshot at that point
- Workflow name and timestamp

On resume, the runner loads checkpoints for each document and passes
completed phases to the executor, which skips them and continues from
the first incomplete phase.

When a document completes successfully, its checkpoint is removed.

### Output Layout

All outputs are gitignored under `.analysis_kb/`:

```
.analysis_kb/
├── checkpoints/     <doc_id>.checkpoint.json   (intermediate, auto-cleaned)
├── state_dumps/     state_full_<doc_id>.json   (full analysis state)
└── signatures/      signature_<doc_id>.json    (privacy-safe summary)
```

## Flags

| Flag              | Description                                    |
|-------------------|------------------------------------------------|
| `--workflow`      | Workflow name: `spectacular` (default), `standard`, `light` |
| `--output-dir`    | Directory for signatures (default: `.analysis_kb/signatures`) |
| `--max-docs`      | Process at most N documents (0 = all)          |
| `--max-chars`     | Skip documents longer than N characters (0 = no limit) |
| `--skip-existing` | Skip documents with existing signatures        |
| `--resume`        | Resume from per-document checkpoints           |
