---
description: Resume work from session history — reads memory, assesses state, picks next task, starts working
allowed-tools: Read, Edit, Write, Grep, Glob, Bash, Task, TodoWrite
---

# /continue - Resume Work From Session History

Resume work on this project by consulting persistent memory, assessing current test/git state, and autonomously starting the highest-priority next task.

## What This Command Does

1. **Load Context**: Read MEMORY.md, session-history.md, active plan files, and CLAUDE.md
2. **Assess State**: Run test suite baseline, check git status, list open GitHub issues
3. **Identify Next Steps**: Cross-reference open issues, plan phases, test results, and known technical debt
4. **Present & Start**: Show a concise session resume, then immediately begin working on the highest-priority task

## Priority Order

1. Regressions (new test failures since last session)
2. In-progress GitHub issues
3. Incomplete plan phases
4. Open issues by number
5. Skip/xfail reduction
6. Technical debt cleanup

## When to Use

- Start of a new session (fresh context)
- After a `/compact` when context was compressed
- When you want to pick up where the last session left off

## Complement

Use `/debrief` at the end of the session to capture lessons and update memory.
