# Pre-commit Hook Sketch — Cleanup Gate (issue #581 Phase 3)

## Purpose

Enforce Rule A from the CLAUDE.md Cleanup Gate addendum at commit time. The hook detects staged deletions of tracked documents and requires them to be justified in the commit message body.

## Behavior

1. **Trigger**: Any staged deletion of `.md`, `.py`, `.json`, `.yaml`, or `.toml` files.
2. **Extract commit body**: Read from `.git/COMMIT_EDITMSG` if available; otherwise fall back to the `GIT_COMMIT_MSG` environment variable.
3. **Parse**: Check whether the commit body contains a `## Files removed and why` or `Files removed` section.
4. **Verify**: For each deleted file, confirm its path (or basename) appears in that section.
5. **Block**: If any deletion is unjustified, print the missing files to stderr and exit 1.

## Pseudocode (Python)

```python
#!/usr/bin/env python3
"""Pre-commit hook: enforce cleanup gate Rule A — per-file justification."""
import os, re, subprocess, sys

TRACKED_EXTENSIONS = {".md", ".py", ".json", ".yaml", ".toml"}

# 1. Get staged deletions
diff_out = subprocess.check_output(["git", "diff", "--cached", "--name-only", "--diff-filter=D"]).decode()
deleted_files = [f.strip() for f in diff_out.splitlines() if f.strip()]

doc_deletions = [f for f in deleted_files if any(f.endswith(ext) for ext in TRACKED_EXTENSIONS)]
if not doc_deletions:
    sys.exit(0)  # no document deletions — nothing to check

# 2. Get commit message (from COMMIT_EDITMSG if pre-messaging, else env)
commit_msg_path = ".git/COMMIT_EDITMSG"
if os.path.exists(commit_msg_path):
    with open(commit_msg_path, encoding="utf-8") as fh:
        commit_msg = fh.read()
else:
    commit_msg = os.environ.get("GIT_COMMIT_MSG", "")

# 3. Check for justification section
has_section = bool(re.search(r"(##\s+Files?\s+removed|Files?\s+removed\s+and\s+why)", commit_msg, re.IGNORECASE))

# 4. Verify each file is mentioned in the section
justified = []
if has_section:
    section_match = re.search(r"((?:##\s+Files?\s+removed[\s\S]*?)(?:##\s|$))", commit_msg)
    if section_match:
        section_text = section_match.group(1)
        for f in doc_deletions:
            if f in section_text or os.path.basename(f) in section_text:
                justified.append(f)

unjustified = [f for f in doc_deletions if f not in justified]

if unjustified:
    print("CLEANUP GATE: The following document deletions lack justification in the commit body:", file=sys.stderr)
    for f in unjustified:
        print(f"  - {f}", file=sys.stderr)
    print("\nAdd a '## Files removed and why' section to your commit message, one entry per deleted file.", file=sys.stderr)
    print("To bypass: git commit --no-verify (acknowledge the risk).", file=sys.stderr)
    sys.exit(1)
```

## Edge Cases

| Case | Handling |
|------|----------|
| **File renames** (Git records as add+delete with similarity score) | Allowed without justification when `git diff --find-renames --diff-filter=R` shows similarity >= 90%. The file still exists, just relocated. |
| **Auto-generated files** | Already excluded by `.gitignore` — would not be tracked, so not staged for deletion. |
| **Test fixtures genuinely obsolete** | Must still be justified, but the justification can be minimal (e.g., "obsolete fixture"). The hook checks for presence of the file path in the section, not the quality of the reason. |
| **Partial commit** (some deleted files in this commit, some in a different one) | The hook checks the current commit only. If a file was deleted across multiple commits, each must carry its own justification. |

## Installation (Optional)

This hook is **OPTIONAL** — it lives in the repo as a reference for developers who want local enforcement:

```bash
# From repo root:
cp scripts/hooks/pre-commit-cleanup-gate.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

The Python version above would be placed at `scripts/hooks/pre-commit-cleanup-gate.py`.

## Limitations

- **Pre-commit hooks are local and bypassable** (`--no-verify`). This hook is a convenience layer, not a guarantee.
- **CI is the real enforcement**. The pre-commit hook alerts developers early; the actual gate must be a PR review requirement enforced in CI (proposed as separate work under issue #581).
- **No history check**. The hook does not run `git log --all -- <path>` (Rule B from the CLAUDE.md addendum). That check requires more computation and should be a CI step or a reviewer action, not a pre-commit gate.
- **Commit message format**. If a developer uses the interactive editor (`-m` without inline text), the hook reads `COMMIT_EDITMSG` only if it already exists — which may not be the case during `git commit` invocation. The hook provides a graceful fallback rather than crashing.
