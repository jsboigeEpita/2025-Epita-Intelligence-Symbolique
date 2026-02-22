# Skill: Continue - Resume Work From Session History

**Version:** 1.0.0
**Usage:** `/continue`

---

## Objective

Bootstrap a new session by consulting persistent memory and project state, then autonomously identify and start working on the highest-priority next step. This skill ensures continuity across sessions — no context is lost, no work is duplicated.

---

## Workflow

### Phase 1: Load Context (READ-ONLY)

**Read these files in parallel:**

1. **Auto-memory**: `~/.claude/projects/d--2025-Epita-Intelligence-Symbolique/memory/MEMORY.md`
   - Current test health, environment, open issues, key patterns
2. **Session history**: `~/.claude/projects/d--2025-Epita-Intelligence-Symbolique/memory/session-history.md`
   - What was done in previous sessions, what was tried and failed
3. **Plan file** (if exists): Check `~/.claude/plans/` for any active plan related to this project
   - May contain a multi-phase plan with incomplete phases
4. **Project instructions**: `CLAUDE.md` at repo root
   - Architecture, conventions, test commands

**Method:**
```bash
# Read all context files in parallel using Read tool
# Then gather current state:
git log --oneline -5
git status --short
```

### Phase 2: Assess Current State

Run a quick test baseline to know exactly where we stand:

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/ --allow-dotenv --disable-jvm-session --ignore=tests/e2e --ignore=tests/performance -q 2>&1 | tail -5
```

Also check open GitHub issues:
```bash
gh issue list --state open --limit 10
```

### Phase 3: Identify Next Steps

Cross-reference:
- **Open GitHub issues** (prioritize by label/number)
- **Plan file phases** (find first incomplete phase)
- **MEMORY.md "GitHub Issues" section** (known open work)
- **Test results** (any new failures = highest priority)
- **Remaining skips/xfails** (reduction opportunities)

**Priority order:**
1. **Regressions**: Any new test failures since last session (fix immediately)
2. **In-progress issues**: GitHub issues marked "in progress" in MEMORY.md
3. **Plan phases**: Next incomplete phase from the plan file
4. **Open issues by number**: Lower issue numbers first (older = more important)
5. **Skip/xfail reduction**: Reduce test skips for better coverage
6. **Technical debt**: Stale imports, cosmetic cleanup, documentation

### Phase 4: Present Plan & Start Working

Output a concise summary to the user:

```markdown
# Session Resume - [DATE]

## Current State
- Tests: X passed, Y failed, Z skipped
- Last commit: [hash] [message]
- Branch: [branch]

## Open Work
1. [Issue/task with priority]
2. [Issue/task]
3. [Issue/task]

## Starting With
**[Description of chosen task]** — [Why this is highest priority]

---
Working on it now...
```

Then immediately begin working on the highest-priority task. Use TodoWrite to track progress.

### Phase 5: Ongoing Work

- Use the project's established patterns (from MEMORY.md "Key Patterns & Gotchas")
- Run tests after each fix to verify no regressions
- Mark todos as completed as you go
- If context is running low, invoke `/debrief` before ending

---

## Tools Used

- **Read**: Memory files, plan files, project docs
- **Bash**: Git status, test runs, GitHub CLI
- **Grep/Glob**: Code exploration as needed
- **TodoWrite**: Track progress on identified tasks
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
