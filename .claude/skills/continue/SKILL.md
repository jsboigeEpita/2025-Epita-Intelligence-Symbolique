# Skill: Continue - Resume Work From Session History

**Version:** 2.0.0
**Usage:** `/continue`

---

## Objective

Bootstrap a new session by consulting persistent memory, GitHub issues, and project state, then autonomously identify and start working on the highest-priority next step. This skill ensures continuity across sessions — no context is lost, no work is duplicated.

---

## Workflow

### Phase 1: Load Context (READ-ONLY, parallel)

**Read these files in parallel:**

1. **Auto-memory**: `~/.claude/projects/d--2025-Epita-Intelligence-Symbolique/memory/MEMORY.md`
   - Current test health, environment, open issues, key patterns
2. **Session history**: `~/.claude/projects/d--2025-Epita-Intelligence-Symbolique/memory/session-history.md`
   - What was done in previous sessions, what was tried and failed
3. **Project instructions**: `CLAUDE.md` at repo root
   - Architecture, conventions, test commands

**Simultaneously gather git state:**
```bash
git log --oneline -10
git status --short
```

### Phase 2: Assess Current State (parallel)

Run these in parallel:

**2a. Test baseline:**
```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/ --allow-dotenv --disable-jvm-session --ignore=tests/e2e --ignore=tests/performance -q 2>&1 | tail -5
```

**2b. GitHub issues (full view):**
```bash
gh issue list --state open --limit 30 --json number,title,labels,body
```

**2c. Recently closed issues (for context):**
```bash
gh issue list --state closed --limit 10 --json number,title,closedAt --jq '.[] | "#\(.number) \(.title) (closed \(.closedAt | split("T")[0]))"'
```

### Phase 3: Identify Next Steps — Issue-Driven Priority

**The project uses GitHub issues as the primary work tracker.** Issues follow a dependency chain that MUST be respected:

#### Dependency Chain (Critical Path)
```
#32 (Audit core features)
  → #33 (Major cleanup: docs/, code hygiene)
    → #34 (Consolidate core into argumentation_analysis/)
      → #35 (Student project integration)
```

**An issue's prerequisites (listed in its body) must be closed before starting it.**

#### Priority Algorithm

1. **Regressions**: Any new test failures since last session → fix immediately
2. **Critical path issues**: Find the FIRST open issue in the dependency chain whose prerequisites are all closed. That's the current focus.
3. **Parallel-track issues**: Issues NOT in the critical path (e.g., Tweety improvements #21/#24-#27/#31, test skip reduction #28/#30) can be worked on alongside critical path work.
4. **Sub-tasks within an issue**: Read the issue body to find unchecked `- [ ]` items. Work on them in order.
5. **New regressions or skip increases**: If test count drops or skips increase vs MEMORY.md baseline, investigate.

#### How to Read an Issue

Each issue body contains:
- **Prerequisites**: Other issues that must be closed first (look for `#XX` references in "Prerequisites" section)
- **Checklist items**: `- [ ]` tasks to complete
- **Deliverables**: What artifact or change signals completion
- **Related issues**: Context and parallel work

**Before starting an issue**, verify:
1. All prerequisite issues are closed (`gh issue view <number> --json state`)
2. The issue hasn't been partially completed in a previous session (check MEMORY.md)
3. You understand the full scope by reading the issue body

### Phase 4: Present Plan & Start Working

Output a concise summary to the user:

```markdown
## Session Resume - [DATE]

### Current State
- Tests: X passed, Y failed, Z skipped (vs MEMORY.md baseline: A/B/C)
- Last commit: [hash] [message]
- Branch: [branch]
- Git status: clean / N modified files

### Issue Roadmap
| # | Issue | Status | Blocked by |
|---|-------|--------|------------|
| 32 | Audit core features | open/closed | — |
| 33 | Major cleanup | open/closed | #32 |
| 34 | Consolidate core | open/closed | #33 |
| 35 | Student integration | open/closed | #34 |

Parallel: #28 (JVM skips), #30 (misc skips), #31 (Tweety stack)

### Starting With
**#XX: [Issue title]** — [Which sub-task / checklist item]
[Why this is the right next step]

---
Working on it now...
```

Then immediately begin working. Use TodoWrite to track sub-tasks from the issue checklist.

### Phase 5: Ongoing Work

- Read the issue body as your detailed spec — it contains checklists, context, and acceptance criteria
- Use the project's established patterns (from MEMORY.md "Key Patterns & Gotchas")
- Run tests after each significant change to verify no regressions
- Mark todos as completed as you go
- When a checklist item is done, update the issue:
  ```bash
  # Comment progress on the issue
  gh issue comment <number> --body "Completed: [description]. Commit: [hash]"
  ```
- When ALL checklist items are done, close the issue:
  ```bash
  gh issue close <number> --comment "All tasks completed. Summary: [brief]"
  ```
- If context is running low, invoke `/debrief` before ending

### Phase 6: Session End Protocol

Before ending (or when context gets low):
1. Comment on the current issue with progress so far
2. Update MEMORY.md with session findings
3. If possible, invoke `/debrief` for full knowledge capture

---

## Issue Lifecycle

```
Open → In Progress (you're working on it)
     → Blocked (prerequisites not met — skip to parallel track)
     → Closed (all checklist items done, deliverable produced)
```

When closing an issue, always:
1. Verify the deliverable exists (report, code change, etc.)
2. Run tests to confirm no regressions
3. Reference the closing commit(s)

---

## Tools Used

- **Read**: Memory files, project docs, issue bodies
- **Bash**: Git status, test runs, GitHub CLI (`gh issue`)
- **Grep/Glob**: Code exploration as needed
- **TodoWrite**: Track progress on issue sub-tasks
- **Task**: Subagents for parallel investigation

---

## Invocation

```bash
/continue
```

---

## Notes

- **Duration**: Runs for the entire session (this is a "start working" skill, not a quick check)
- **Frequency**: Start of each new session
- **Prerequisite**: MEMORY.md must exist with current state
- **Complement**: Use `/debrief` at the end of the session to close the loop
- **Issue-first**: Always prefer working on a GitHub issue over ad-hoc tasks. If you discover work that doesn't have an issue, create one first.
