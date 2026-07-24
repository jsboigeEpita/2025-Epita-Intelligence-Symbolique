# S6-B — Encrypted-extracts port: design + fables-tier scaffold

**Track**: S6-B (issue #1506) · **Epic**: CoursIA strate-6 ICT.
**Status**: **DESIGN PHASE**. Port réel **DIFFÉRÉ** — en attente d'acceptation
de S6-A1 ([PR #1516](https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/pull/1516)).
**Scaffold**: [`scripts/coursia_s6b/validate_fables_tier.py`](../../scripts/coursia_s6b/validate_fables_tier.py).
**CoursIA gate**: preparation for [seed `#7289`](https://github.com/jsboige/CoursIA/issues/7289)
morphogenèse corpus (jambe `#7742`).

## Why a design phase

The issue body states explicitly:

> **Phase design/scaffolding d'abord** (valider sur fables), port réel
> APRÈS acceptation du grounding.

The "grounding" = S6-A1 (PR #1516) just opened this round; until the
grounding is accepted (admin-merge coord), no real port. We therefore deliver
**only** the design doc + the fables-tier scaffold that validates the
existing encryption pipeline end-to-end on a weak-load public-domain tier.

## What "port" means here

Per the issue body:

> Port du système d'extracts chiffrés (jina/tika + chiffrement/compression,
> cf. `argumentation_analysis/data/extract_sources.json.gz.enc` +
> `io_manager.load_extract_definitions`) pour accès public partiel.

That is: take the existing extract-corpora pipeline (already supports
encrypted JSON+gzip at rest, decrypted in-memory, with the full-text
fetched on-demand by `text_retriever`) and **expose a partial-access mode**
suitable for CoursIA's public side. Two non-trivial design axes:

1. **Tier routing** — which extracts become public (fables/mythes,
   public-domain, weak-load) vs which stay encrypted (figures
   universellement condamnées — Anschluss-1938, Mandchourie) vs which
   are excluded entirely (figures contemporaines, même chiffrées).
2. **Schema exposure** — the encrypted blob stores opaque `source_name`
   + `path` + `host_parts`; the public-facing layer must consume that
   shape **without leaking source content**.

## Anti-pendule invariants (design + scaffold)

- **No re-implementation.** The encryption pipeline already exists
  (`argumentation_analysis.core.io_manager` +
  `argumentation_analysis.core.utils.crypto_utils` + Fernet PBKDF2HMAC
  with SHA256, 480 000 iterations). S6-B uses it as a black box.
- **No public exposure of fakes.** The fables-tier scaffold writes a
  small encrypted blob under `argumentation_analysis/data/fables_tier.json.gz.enc`,
  never plaintext on disk. `--cleanup-blob` removes it after validation.
- **Opaque IDs only on GitHub-indexed surfaces.** No real author / title /
  date reaches the script, the doc, or any commit message. The fakes
  carry `fable_tier_corpus_{a,b,c}` only.
- **Privacy HARD** — the fables tier's plaintext content is **stripped
  before save** (so the encrypted blob carries opaque-id metadata only).
  `load_extract_definitions` is faithful: what you saved is what you get
  back. Stripping at source is the right place (the `embed_full_text`
  flag covers `full_text` only, not `text`).

## Fables-tier scaffold — what it proves firsthand

The script validates the existing IO + crypto chain end-to-end on a tiny,
self-contained, public-domain tier:

| Step | Function | Purpose |
|------|----------|---------|
| 1a | `_strip_text_fields` | Strip `text` / `full_text` in memory (privacy HARD) |
| 1b | `save_extract_definitions` | Encrypt + gzip + write blob to disk |
| 2 | `load_extract_definitions` | Read blob, decrypt, gunzip, validate schema |
| 3 | invariant checks | (a) schema — list of dicts with required keys, (b) opaque-ids — `source_name` starts with `fable_tier_`, (c) no plaintext leak — `text` / `full_text` absent from loaded extracts |

Firsthand run output (anti-#1019: actually executed, not asserted):

```
Round-trip OK: {"n_sources": 3, "n_extracts_total": 3, "ids": ["fable_tier_corpus_a",
"fable_tier_corpus_b", "fable_tier_corpus_c"], "blob_path":
"argumentation_analysis\\data\\fables_tier.json.gz.enc",
"blob_name": "fables_tier.json.gz.enc", "tier": "fables_public_domain_weak_load"}
```

Two integration bugs caught by this firsthand run (would have shipped
silently otherwise):

1. **Validator gate mismatch** — `load_extract_definitions` requires
   `source_name`, `source_type`, `schema`, `host_parts`, `path`, and a
   list `extracts`. The original fakes had `id` + `extracts` only;
   the loader returned `fallback_definitions=[]` and we read
   `n_sources=0`. **Fix**: pad fakes with all required keys. The
   scaffold now genuinely round-trips.
2. **Plaintext field drift** — the `embed_full_text` flag covers
   `full_text` only; `text` survives the save/load round-trip. **Fix**:
   strip `text` / `full_text` from the in-memory payload **before**
   `save_extract_definitions`. Encrypted blob now carries opaque-id
   metadata only.

Both fixes are minimal, anti-pendule (no workarounds, no bypass), and
preserved as in-script invariants.

## What the real port will do (next, **after S6-A1 acceptance**)

When S6-A1 (PR #1516) lands, the design doc upgrades into a port PR:

1. **Tier classifier** — read each entry's metadata (`source_type`,
   `era`, public-domain flags), route to one of three buckets:
   `public_fables` / `encrypted_historical` / `excluded_contemporary`.
2. **Public-facing loader** — thin shim over `load_extract_definitions`
   that filters to `public_fables` only and strips any `host_parts`
   that would surface real-URL traces.
3. **Schema doc** — opaque-id schema for the public side
   (`fable_*`, `myth_*`, `legend_*`) — no real names on this surface.
4. **Verification gate** — re-run `validate_fables_tier.py` after each
   shape change; mypy --strict on every script; a privacy HARD grep
   `text|full_text` must return 0 hits in any committed artifact.

## What the real port will NOT do (anti-pendule guard rails)

- ❌ **No figures contemporaines**, même chiffrées (per spec).
- ❌ **No push upstream** to `jsboige/CoursIA` from this workspace
  (proposal-only discipline).
- ❌ **No new re-implementation** of the encryption pipeline (anti-#1019
  + reuse). The existing crypto is the contract.
- ❌ **No broadened scope.** S6-B is the **encrypted-extracts port**,
  not the *whole* public corpus. Other tracks (TPM, Dung, governance)
  stay on their own lanes.

## Reproduce

```bash
# Dry-run (contract, no disk write):
conda run -n projet-is-roo-new --no-capture-output python \
    scripts/coursia_s6b/validate_fables_tier.py --dry-run

# Round-trip on the canonical encrypted-dataset location (writes a
# fables_tier.json.gz.enc under argumentation_analysis/data/):
conda run -n projet-is-roo-new --no-capture-output python \
    scripts/coursia_s6b/validate_fables_tier.py

# Round-trip + cleanup (recommended after local validation):
conda run -n projet-is-roo-new --no-capture-output python \
    scripts/coursia_s6b/validate_fables_tier.py --cleanup-blob
```

## Relation to sibling tracks

- **S6-A1 #1516 (po-2025)** — TPM belief-state, Phase-A candidate #2
  (this round: just delivered).
- **S6-A2 #1509 (po-2023, MERGED)** — Dung labelling trajectory,
  Phase-A candidate #1.
- **S6-B (this design + scaffold)** — encrypted-extracts port, gated
  on S6-A1 acceptance.

## Links

- **CoursIA seed**: [`jsboige/CoursIA#7289`](https://github.com/jsboige/CoursIA/issues/7289)
- **CoursIA morphogenèse corpus**: [`jsboige/CoursIA#7742`](https://github.com/jsboige/CoursIA/issues/7742)
- **Falsifiability contract**: [`jsboige/CoursIA#7291`](https://github.com/jsboige/CoursIA/issues/7291)
- **S6-A1 PR (gating this port)**: [#1516](https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/pull/1516)
- **S6-A2 PR (MERGED)**: [#1509](https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/pull/1509)
- **Existing IO module**: [`../../argumentation_analysis/core/io_manager.py`](../../argumentation_analysis/core/io_manager.py)
- **Existing crypto module**: [`../../argumentation_analysis/core/utils/crypto_utils.py`](../../argumentation_analysis/core/utils/crypto_utils.py)

— Track S6-B · worker myia-po-2025 · #1506