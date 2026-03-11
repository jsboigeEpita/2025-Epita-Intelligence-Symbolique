# Skill: Dataset Manager

**Version:** 1.0.0
**Usage:** `/dataset-manager [restore|catalog|enrich|encrypt]`

---

## Objective

Manage the encrypted dataset used for testing and demonstrations:
- Restore encrypted files to local cleartext
- Catalog available sources
- Add new test sources for student project integration
- Re-encrypt and commit updates

---

## Actions

### `restore` — Decrypt and Restore

1. Check `TEXT_CONFIG_PASSPHRASE` is set in environment
2. Decrypt `tests/extract_sources_with_full_text.enc` using Fernet
3. Decompress gzip
4. Save to local (gitignored) location
5. Report: file size, number of sources, format

### `catalog` — Catalog Sources

1. Load decrypted data (or decrypt if needed)
2. List all sources with metadata: name, type, language, word count
3. Identify coverage gaps for student project integration needs
4. Output structured catalog

### `enrich` — Add New Sources

1. Accept a source description (text, metadata)
2. Append to the dataset
3. Validate format consistency
4. Report: new source count, total size

### `encrypt` — Re-encrypt and Stage

1. Compress with gzip
2. Encrypt with Fernet using `TEXT_CONFIG_PASSPHRASE`
3. Write to `.enc` file
4. Verify: decrypt and compare with source
5. **CRITICAL**: Never commit cleartext files

---

## Security Rules

- **NEVER** index decrypted files on GitHub
- **ALWAYS** verify `.gitignore` covers cleartext files before operations
- **ALWAYS** use the `TEXT_CONFIG_PASSPHRASE` env var (never hardcode)
- Decrypted files go to `argumentation_analysis/data/` (gitignored)

---

## Tools Used

- **Read**: Encrypted files, dataset content
- **Write**: New encrypted files
- **Bash**: Decrypt/encrypt operations, file operations

---

## Related Files

- `argumentation_analysis/agents/tools/encryption/` — encryption scripts
- `tests/extract_sources_with_full_text.enc` — main encrypted dataset (1.4 MB)
- `tests/extract_sources_backup.enc` — backup (2.8 KB)
- `.gitignore` — must exclude `*.json.gz` and decrypted files
