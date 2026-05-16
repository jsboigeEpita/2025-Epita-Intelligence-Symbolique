# CLAUDE.md Addendum Proposal — Cleanup Gate (issue #581 Phase 3)

## Motivation

Session 101 exposed a systemic risk: "cleanup" PRs silently deleted load-bearing files that had been mistaken for drafts. Eight scripts were lost, the pipeline broke, and the "Consolider != Archiver" rule was born in CLAUDE.md. That rule alone proved insufficient. Two documented regressions followed:

- **Commit `a62ef234` (PR #130)**: deleted `DESIGN_PARALLEL_WORKFLOW.md` — a core design doc that described a critical workflow architecture. Created as a `feat(` commit, not a draft.
- **Commit `48f514c5` (PR #442)**: deleted `architecture_fallacy_workflows.md` — another architecture-level design doc removed during a "cleanup" sweep.

These deletions share a common pattern: the files were real artifacts (`feat(` origin), not temporary drafts, but were removed without justification. The existing "Consolider != Archiver" guidance does not specify a concrete gate at PR review time. The pattern is repeatable: any future agent or developer performing a "cleanup" sweep can make the same mistake — deleting files that look like scaffolding but are actually design records.

### Regression pattern summary

| Aspect | Observed behavior | Root cause |
|--------|------------------|------------|
| What happened | Design docs deleted as "cleanup" | No gate distinguishing design vs draft |
| Who was affected | Pipeline broke (Session 101, #130, #442) | 3 design docs lost total |
| Why it was missed | Files had no `.draft` suffix or `ARCHIVED` tag | No `git log` origin check before deletion |
| What this prevents | Future agents applying same heuristic | Structured justification forces intent review |

## Proposed Addition to CLAUDE.md

Insert the following block verbatim into CLAUDE.md **after** the "Consolider != Archiver" section and **before** the "Fixing Prompts and Rules" section.

```markdown
## Cleanup Gate — PR Deletion Policy

Cleanup PRs that delete tracked files MUST pass the following gates. These rules apply prospectively to all PRs opened after their adoption.

### Rule A — Per-file justification

Deletion of `.py`, `.md`, `.json`, `.yaml`, or `.toml` files in a cleanup PR MUST be accompanied by a per-file justification in the PR body. The PR body must contain a section titled `## Files removed and why` listing each deleted file with:
- Its **role** (design / archive / draft / test / config / other)
- A **1-sentence reason** for removal

Without this section, reviewers MUST request changes.

### Rule B — Origin check before deletion

Before deleting any file not referenced in the last N months (suggested N=3), run:

```bash
git log --all -- <path>
```

to verify its origin. If the most recent commit touching the file was a `feat(` commit — meaning it was created as a feature artifact, not a draft — treat it as HIGH suspicion and require an explicit justification in the PR body. This catches the regression pattern where design docs (which are `feat(` artifacts) are mistaken for temporary drafts.

### Rule C — Bulk deletion table

Cleanup PRs with more than 5 file deletions MUST include a markdown table in the PR body:

| File | Type | Last useful date | Reason for deletion |

Bulk deletions submitted without this table are NOT to be merged. The table forces deliberate review of each removal rather than blind sweeping.

### Backwards compatibility

These rules apply prospectively only. Existing files that were previously deleted without justification remain deleted. The goal is to prevent future regressions, not to retroactively restore files.

### Reviewer checklist

When reviewing a cleanup PR, verify each rule before approving:
- [ ] **Rule A**: Is there a `## Files removed and why` section? Does each `.md`/`.py`/`.json`/`.yaml`/`.toml` deletion have a role + reason?
- [ ] **Rule B**: Were files older than 3 months checked with `git log --all -- <path>`? Was any `feat(` origin flagged?
- [ ] **Rule C**: If >5 deletions, is the bulk table present and complete?

### Expected impact

- **Review time**: Expect +2-3 minutes per cleanup PR with document deletions. This is intentional — the gate trades a few minutes of review effort for assurance that no design artifact is lost.
- **Commit message hygiene**: Developers should add the justification section early in the commit body rather than at the end. A template:

```
fix(repo): remove outdated config files

## Files removed and why
- config/old_scheduler.yaml: config — replaced by config/new_scheduler.yaml in commit xyz
- docs/draft_notes.md: draft — never finalized, superseded by docs/decisions.md

Updated CI to reflect new config paths.
```

- **Agent compliance**: Agents performing cleanup sweeps should run the pre-commit hook locally first, or draft the PR body section before staging deletions. The justification should be written before the files are removed, not retroactively.
```

## Installation Note

This file (`docs/proposals/CLAUDE_MD_CLEANUP_GATE_ADDENDUM.md`) is the standalone proposal. The coordinator (Opus) will review and merge the verbatim block above into CLAUDE.md after approval. This file should remain as the audit trail of the proposal.
