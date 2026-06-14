# Torch DLL WinError 182 — Repair Recipe

**Issue**: #1020 (subsystem 1 of #1019 — eliminate fallbacks)
**Scope**: Read-only investigation + recipe document. Zero code changes (lane po-2025).
**Target**: po-2025 applies the fix described here when implementing #1019 subsystem 1.

> **⚠️ UPDATE (FB-23 #1088, 2026-06-14)** — The recipe below assumes the
> quality-radar failure is caused by the WinError 182 DLL conflict. On
> `projet-is` (po-2023) this was **empirically refuted**: a fresh-process
> repro with jpype loaded *before* spaCy loaded `fr_core_news_sm` cleanly
> (no WinError 182). The **actual root cause was missing dependencies**:
> `textstat` was not declared in any env spec, and the `fr_core_news_sm`
> spaCy model was never downloaded by `setup_project_env.ps1`. The durable
> fix for #1088 therefore (a) declares `textstat` in `environment.yml` +
> `requirements.txt`, (b) adds a `python -m spacy download fr_core_news_sm`
> step to `setup_project_env.ps1`, and (c) rewords the evaluator's error
> message to point at the likely-actual cause (missing dep/model) first.
> The WinError 182 DLL-ordering fix below remains valid as defense-in-depth
> (and applies on environments where the conflict does manifest, e.g. some
> torch/jpype version combos) — but it is **not** the quality-radar's
> primary failure mode on this cluster. Verify the actual root cause with a
> fresh-process repro before applying the DLL recipe.


---

## 1. Root Cause

### The DLL conflict

On Windows, `torch` ships a native DLL `fbgemm.dll` that conflicts with DLLs loaded by JPype (the Java bridge). If **JPype loads before torch**, the DLL conflict causes:

```
OSError: [WinError 182] torch\lib\fbgemm.dll
```

The fix is simple in principle: **torch must load before JPype in every Python process**.

### Why quality_evaluator.py crashes

The import chain that triggers the crash:

```
quality_evaluator._load_deps()     (line 38)
  → import spacy                   (spacy loads thinc → torch)
    → import thinc                 (thinc depends on torch)
      → import torch               (fbgemm.dll fails because jpype already loaded)
```

When `_load_deps()` is called (line 38), it tries `import spacy`. spacy transitively imports `thinc`, which imports `torch`. If `jpype` has already been loaded in the process, `fbgemm.dll` fails with `WinError 182`. The except clause at line 52 catches this silently and sets `_DEPS_AVAILABLE = False`, causing all quality scoring to use regex heuristics instead.

### Why conftest.py's workaround doesn't protect production

The workaround in `tests/conftest.py` (lines 113-127) correctly imports torch before jpype:

```python
# tests/conftest.py:113-127
try:
    import torch          # torch FIRST
    import transformers
    import openai
    import semantic_kernel
except (ImportError, OSError, RuntimeError) as e:
    ...
import jpype              # jpype AFTER torch
```

**But this only applies during `pytest` runs.** Production entry points do NOT go through `tests/conftest.py`.

### The production guard and its gaps

`argumentation_analysis/core/dll_guard.py` provides the production guard:

```python
# dll_guard.py:42-44 — pre-loads torch before jpype
for mod_name in ("torch", "transformers"):
    try:
        __import__(mod_name)
    except (ImportError, OSError, RuntimeError):
        pass
```

**Only ONE production file imports dll_guard**: `jvm_setup.py` (line 4):

```python
# jvm_setup.py:4-5
import argumentation_analysis.core.dll_guard  # noqa: F401 — must precede jpype
import jpype
```

**Files that import jpype WITHOUT dll_guard protection**:

| File | Line | Import | Protected? |
|------|------|--------|:----------:|
| `jvm_setup.py` | 4-5 | `dll_guard` then `jpype` | ✅ |
| `api/main.py` | 98 | `import jpype` directly | ❌ |
| `api/main.py` | 113 | `import jpype` directly | ❌ |

**Files that trigger torch loading without dll_guard**:

| File | Line | Trigger | Protected? |
|------|------|---------|:----------:|
| `plugins/quality_scoring_plugin.py` | 16 | Top-level import of `ArgumentQualityEvaluator` | ❌ |
| `orchestration/invoke_callables.py` | 356 | Lazy import of quality evaluator | ❌ |

**dll_guard.py's own docstring is stale**: it claims `api/main.py` and `run_orchestration.py` are guarded, but neither file imports `dll_guard`.

---

## 2. Fix Recipe

### Fix A: Add dll_guard to all entry points (minimum fix)

Add `import argumentation_analysis.core.dll_guard` as the **first import** (after `__future__` and docstrings) in every production entry point:

**File: `api/main.py`**
```python
# At top of file, before any other imports:
import argumentation_analysis.core.dll_guard  # noqa: F401
```

**File: `argumentation_analysis/run_orchestration.py`**
```python
# At top of file, before any other imports:
import argumentation_analysis.core.dll_guard  # noqa: F401
```

**File: `argumentation_analysis/core/bootstrap.py`** (if not already present)
```python
# At top of file, before any other imports:
import argumentation_analysis.core.dll_guard  # noqa: F401
```

### Fix B: Add dll_guard to quality_evaluator.py (defense in depth)

This ensures that even if quality_evaluator is loaded via an unexpected code path, torch is pre-loaded before spacy:

**File: `argumentation_analysis/agents/core/quality/quality_evaluator.py`**
```python
# After existing imports (line 18), add:
import sys
if sys.platform == "win32":
    import argumentation_analysis.core.dll_guard  # noqa: F401
```

This is the critical fix: it ensures that when `_load_deps()` (line 38) tries `import spacy`, torch has already been loaded by dll_guard, so `fbgemm.dll` doesn't conflict.

### Fix C: Remove the heuristic fallback

Per user mandate (#1019), the regex fallback in `_load_deps()` (lines 52-60) must be replaced with an explicit failure:

**File: `argumentation_analysis/agents/core/quality/quality_evaluator.py`**

Replace lines 52-60:
```python
# BEFORE (fallback regex):
except (ImportError, OSError, RuntimeError):
    logger.warning(
        "spacy or textstat not available (import error or DLL failure). "
        "Quality evaluation will use fallback heuristics."
    )
    return False

# AFTER (fail explicit):
except (ImportError, OSError, RuntimeError) as e:
    raise RuntimeError(
        f"spacy/textstat failed to load: {e}. "
        f"Quality scoring requires spacy + textstat. "
        f"On Windows, ensure torch is loaded before jpype (dll_guard). "
        f"Install: pip install spacy textstat && python -m spacy download fr_core_news_sm"
    ) from e
```

This ensures that if the DLL fix (Fix B) doesn't work for some reason, the failure is **visible and actionable**, not silently masked by fake scores.

---

## 3. Files to Modify (for po-2025)

| File | Change | Lines | Priority |
|------|--------|-------|:--------:|
| `api/main.py` | Add `import dll_guard` at top | Before line 1 | P0 |
| `argumentation_analysis/run_orchestration.py` | Add `import dll_guard` at top | Before line 1 | P0 |
| `argumentation_analysis/core/bootstrap.py` | Verify/add `import dll_guard` | Check existing | P0 |
| `argumentation_analysis/agents/core/quality/quality_evaluator.py` | Add `import dll_guard` (Fix B) | After line 18 | P0 |
| `argumentation_analysis/agents/core/quality/quality_evaluator.py` | Replace fallback with explicit fail (Fix C) | Lines 52-60 | P1 |
| `argumentation_analysis/core/dll_guard.py` | Update docstring (stale entry point list) | Lines 17-19 | P2 |

---

## 4. Verification Procedure

After po-2025 applies the fixes, verify on Windows:

### Step 1: Verify dll_guard pre-loads torch

```python
# In a fresh Python process on Windows:
import argumentation_analysis.core.dll_guard
import torch
print("torch loaded:", torch.__version__)
# Should succeed without WinError 182
```

### Step 2: Verify spacy loads after dll_guard

```python
# In a fresh Python process on Windows:
import argumentation_analysis.core.dll_guard
import spacy
nlp = spacy.load("fr_core_news_sm")
doc = nlp("Ceci est un test.")
print("spacy loaded successfully, tokens:", [t.text for t in doc])
# Should succeed without WinError 182
```

### Step 3: Verify quality evaluator loads without degradation

```python
# In a fresh Python process on Windows:
from argumentation_analysis.agents.core.quality.quality_evaluator import ArgumentQualityEvaluator
evaluator = ArgumentQualityEvaluator()
result = evaluator.evaluate("This argument is logically coherent and well-supported.")
print("degraded:", result.get("degraded", False))
print("scores:", result)
# degraded should be False or absent (not True)
# scores should contain real spacy-based values, not regex heuristics
```

### Step 4: Verify explicit failure if spacy missing

```python
# Simulate: uninstall spacy, then try loading quality_evaluator
# Expected: RuntimeError with clear message (not silent fallback)
```

### Step 5: Run quality-related tests

```bash
conda run -n projet-is --no-capture-output pytest tests/unit/argumentation_analysis/ -v -k "quality"
# All quality tests should pass with real spacy, not degraded mode
```

---

## 5. Root Cause Summary

| Factor | Detail |
|--------|--------|
| **DLL** | `torch/lib/fbgemm.dll` conflicts with JPype-loaded DLLs |
| **Error** | `OSError: [WinError 182]` |
| **Platform** | Windows only (Linux/macOS unaffected) |
| **Trigger** | `import spacy` → thinc → torch after JPype has loaded |
| **Silent failure** | `_load_deps()` catches OSError → sets `_DEPS_AVAILABLE=False` → regex heuristics |
| **Gap** | `dll_guard` only imported in `jvm_setup.py`, not in other entry points |
| **Fix** | Import `dll_guard` before any torch/spacy/jpype usage in ALL entry points + quality_evaluator |

---

## 6. Cross-References

- **Issue #882**: Original torch DLL crash report
- **Issue #993**: Quality fallback introduced to mask the crash
- **Issue #1019**: Mandate to eliminate all fallbacks (parent issue)
- **Issue #1020**: This investigation (recipe for po-2025)
- **`argumentation_analysis/core/dll_guard.py`**: Production guard (only used in `jvm_setup.py`)
- **`tests/conftest.py:113-127`**: Test-only workaround (torch before jpype)
- **`argumentation_analysis/agents/core/quality/quality_evaluator.py:31-60`**: Lazy spacy load + crash fallback
- **`argumentation_analysis/plugins/quality_scoring_plugin.py:16`**: Top-level import of quality_evaluator (gap entry)
