# Dataset Enrichment Workflow

How to add new extracts and regenerate the discourse pattern report.

## Adding a new extract

1. Place the plaintext **outside** the repo (e.g. `~/local-texts/foo.txt`).
2. Run:
   ```bash
   python scripts/dataset/tasks.py pattern-add \
       --source "speech_id_X" \
       --text ~/local-texts/foo.txt \
       --metadata "discourse_type=populist,era=2025,regime_type=democracy"
   ```
   The script encrypts the text and appends it to the canonical dataset,
   then prints the opaque ID assigned to the new extract.
3. Re-run the full analysis:
   ```bash
   python scripts/dataset/tasks.py pattern-rerun --skip-existing
   ```
   This runs the spectacular workflow on new documents (~7 min/doc).
4. Regenerate the public report:
   ```bash
   python scripts/dataset/tasks.py pattern-report
   ```
   Output: `docs/reports/discourse_patterns.md` + SVG charts.
5. Commit the report (**not** the plaintext, **not** `.analysis_kb/`).

## Metadata schema

| Field | Required | Values |
|-------|----------|--------|
| `discourse_type` | yes | `populist`, `technocratic`, `dictatorial`, `dialectic`, `other` |
| `era` | yes | Decade bucket, e.g. `2020-2025` |
| `regime_type` | no | `democracy`, `autocracy`, `mixed`, `historical` |
| `language` | no | Default `fr` |

## Privacy reminders

- Plaintext stays on local disk. **Never** tracked in git.
- Use opaque IDs in commits, PRs, and dashboards. **Never** source names.
- `.analysis_kb/` is gitignored — do not move state dumps out of it.
- For full policy, see `CLAUDE.md` → "Dataset Privacy Discipline".

## Rotating the passphrase

1. Generate a new key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. Update `TEXT_CONFIG_PASSPHRASE` in `.env`.
3. Re-encrypt the dataset with the new key (keep a backup of the old `.env` until confirmed).
4. Verify decryption round-trip before deleting the old key.

## Task reference

| Task | Script | Description |
|------|--------|-------------|
| `pattern-add` | `add_extract.py` | Encrypt + append extract to canonical dataset |
| `pattern-rerun` | `run_corpus_batch.py` | Run spectacular on new/selected documents |
| `pattern-report` | `build_pattern_report.py` | Generate markdown + SVG report from signatures |
