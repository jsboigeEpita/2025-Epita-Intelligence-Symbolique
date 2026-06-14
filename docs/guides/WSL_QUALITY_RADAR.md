# WSL Execution Path for the Quality Radar

**Track**: FB-24 #1090 — Epic #947 (Final Boss), quality-radar gate
**Parallel to**: FB-23 #1088 (po-2023, Windows-native fix attempt)
**Date**: 2026-06-14
**Lane**: po-2025 (heavy run / env plumbing)

---

## TL;DR

The quality radar (9-virtue `ArgumentQualityEvaluator`) crashes on **Windows-native**
with spaCy/torch `WinError 182` (`fbgemm.dll` DLL load fault, issue #882). Under **WSL2
(Ubuntu)** the same import chain loads cleanly and the quality dimension produces **real
non-trivial values**. This document stands up the WSL env and documents the reproducible
invocation so the A/B/C quality re-measurement (and #1088) can use it.

**This is the answer to #1088's native-vs-WSL question**: WSL works; the DLL conflict is
Windows-only.

---

## Proven result (FB-24)

| Check | Result |
|-------|--------|
| spaCy + torch load (torch-before-spacy, conftest order) | ✅ `spacy 3.8.14 \| torch 2.6.0 \| platform=linux` |
| spaCy + torch load (spacy-before-torch, the Windows-fatal order) | ✅ loads — import order is irrelevant under Linux |
| `WinError 182` | **ABSENT** (no Windows DLL conflict under WSL) |
| `fr_core_news_sm` model load | ✅ 3.8.0 |
| Quality dimension on corpus_C | ✅ note_finale 2.0/9, Flesch 46.34 (real textstat), 3/9 non-zero virtues |
| Quality dimension on corpus_A | ✅ Flesch 40.12, 3/9 non-zero virtues |

Per-virtue scores are genuinely computed (Flesch reading-ease, connector counts, phrase
counts via spaCy/doc) — **not** the zero-filled degraded output that `WinError 182` forced
on Windows. Captured proof is gitignored (privacy HARD: aggregate-only, no raw corpus text).

---

## Reproducible setup (WSL2 Ubuntu)

> The project has no pre-existing WSL setup guide. These steps were executed fresh on a
> barebones Ubuntu WSL2 (system `python3.12`, no conda/deps/java). 910 GB disk, pypi reachable.

```bash
# 1. Miniconda (user-space, no sudo)
cd ~
wget "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" -O /tmp/mc.sh
bash /tmp/mc.sh -b -f -p ~/miniconda3
~/miniconda3/bin/conda init bash
source ~/miniconda3/etc/profile.d/conda.sh

# 2. Accept ToS (conda >= 26 requires it before using default channels)
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# 3. Env (python 3.10, matches environment.yml)
conda create -y -n quality-wsl python=3.10
conda activate quality-wsl

# 4. Project deps. NOTE: requirements.txt is INCOMPLETE vs environment.yml — it omits
#    textstat and pybreaker (both required by the quality path). Install both files:
cd /mnt/d/dev/2025-Epita-Intelligence-Symbolique
pip install -r argumentation_analysis/requirements.txt
pip install textstat pybreaker ag2 pytest-dotenv mcp blis tiktoken tenacity  # env.yml pip-section gap

# 5. French spaCy model
python -m spacy download fr_core_news_sm
```

### Run the quality dimension

```bash
cd /mnt/d/dev/2025-Epita-Intelligence-Symbolique
conda activate quality-wsl
# Uses the encrypted dataset in-memory (TEXT_CONFIG_PASSPHRASE from .env).
# Aggregate-only output; raw corpus text never printed.
python -c "
import os, sys
from pathlib import Path
sys.path.insert(0, '.')
for line in open('.env'):
    if '=' in line and not line.strip().startswith('#'):
        k,_,v = line.partition('='); os.environ.setdefault(k.strip(), v.strip())
from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions
from argumentation_analysis.agents.core.quality.quality_evaluator import ArgumentQualityEvaluator
key = derive_encryption_key(os.environ['TEXT_CONFIG_PASSPHRASE'])
defs = load_extract_definitions(Path('argumentation_analysis/data/extract_sources.json.gz.enc'), key)
text = defs[2].get('full_text', '')[:4000]   # corpus_C (opaque); truncate to excerpt
r = ArgumentQualityEvaluator().evaluate(text)
print('note_finale', r['note_finale'], '| note_moyenne', round(r['note_moyenne'],3))
for v,n in r['scores_par_vertu'].items(): print(f'  {v:<24} {n}')
"
```

For a full A/B/C quality re-measurement, loop over `CORPUS_SRC_IDX = {"A": 11, "B": 3, "C": 2}`
and feed the full (or 60K-truncated) text instead of the 4000-char excerpt.

---

## Findings

### 1. `requirements.txt` is missing deps the quality path needs (relevant to #1088)

- **`textstat`** — imported by `quality_evaluator.py:59` (`from textstat import
  flesch_reading_ease`) but **absent from `requirements.txt`** and `argumentation_analysis/requirements.txt`.
  It IS in `environment.yml`'s transitive deps (conda pulls it via spacy on some resolvers,
  but not reliably). A fresh Windows-native env would hit `ModuleNotFoundError: textstat`
  even after the DLL fix.
- **`pybreaker`** — in `environment.yml` pip section (line 82), missing from
  `requirements.txt`. Pulled by `core/utils/network_utils.py:24`.

→ Implication for po-2023 / #1088: the Windows-native quality fix must ALSO ensure `textstat`
  is installed, or the radar will fail on `import` regardless of the DLL repair. Tracked as
  a tech-debt follow-up (file-disjoint from this PR — I do not edit `requirements.txt` here).

### 2. The `dll_guard` is a no-op under WSL

`argumentation_analysis/core/dll_guard.py` early-returns when `sys.platform != "win32"`.
Under WSL (`platform=linux`) it does nothing — the torch-before-jpype ordering that
`conftest.py:113-127` enforces on Windows is unnecessary here. The radar loads regardless
of import order.

### 3. JDK/JPype for the FULL harness is NOT yet stood up (DoD item 1, partial)

The **quality dimension** does not need the JVM — it uses spaCy + textstat only, and is fully
runnable as proven above. The **full spectacular harness** (formal-logic phases PL/FOL via
JPype/Tweety) needs a JDK. Under this WSL2, `sudo apt-get install -j headless` is
password-gated, so the JVM is not yet available. Two options to complete DoD item 1:

- **`sudo apt-get install -y default-jdk`** (needs the WSL user's sudo password), then
  `export JAVA_HOME=/usr/lib/jvm/default-java`, or
- **Portable JDK** (user-space, no sudo): download a Temurin Linux tarball to `~/jdk` and
  set `JAVA_HOME` (mirrors the Windows `portable_jdk/` pattern).

The formal phases are already proven working on Windows-native (FB-22 #1087, PR #1089), so
the WSL JDK is only needed if the A/B/C quality re-measurement wants to run the **full**
pipeline (not just the quality category) under WSL for environmental consistency.

---

## Anti-pendule / anti-theater

- **No heuristic quality fallback** was added to "produce a number" (#1019). The values
  above are real spaCy/textstat output. If the env isn't ready, `ArgumentQualityEvaluator.evaluate`
  **raises** (`quality_evaluator.py:349-355`, fail-loud), it does not return zeros.
- This is the **WSL path only**. It does not duplicate po-2023's Windows-native fix attempt
  (#1088); the two are file-disjoint (this touches WSL setup/docs only, not the quality
  module internals, `conftest.py`, or `KNOWN_ISSUES.md`).
- FB-20's quality note (#1087 / #1088) is NOT edited here — only one of po-2023/po-2025
  touches it, per dispatch coordination. po-2023 owns it.

---

## Privacy HARD

- Opaque corpus IDs only (`corpus_A/B/C`, source indices). No source names, no
  `raw_text`/`full_text` printed or committed.
- Proof runs write to gitignored paths (`argumentation_analysis/evaluation/results/`,
  `.cache/`). This document is aggregate-only.
- The encrypted dataset is consumed **in-memory** via `load_extract_definitions` (CLAUDE.md
  dataset rule 5).
