# Skill: Analyze Student Project

**Version:** 1.0.0
**Usage:** `/analyze-student-project <directory>`

---

## Objective

Read a student project directory, cross-reference with subject documentation and soutenance transcripts, and produce a structured integration report.

---

## Workflow

### Phase 1: Discovery

1. **Read the project directory** — list all files, identify entry points, key classes, and dependencies
2. **Measure scope** — count LoC, files, identify tech stack (Python, Java, TypeScript, etc.)
3. **Identify features** — catalog what the project does (agents, services, UI, models)

### Phase 2: Cross-Reference

1. **Read the subject doc** from `docs/projets/sujets/` matching the project
2. **Read soutenance transcripts** from `G:\Mon Drive\MyIA\Formation\Epita\2025\Soutenances\` if available
3. **Compare** deliverables vs. subject requirements

### Phase 3: Core Overlap Analysis

1. **Search the core** (`argumentation_analysis/`) for overlapping functionality
2. **Identify** which capabilities already exist vs. what's new
3. **Check imports** — does the project already import from the core? Does it duplicate core code?

### Phase 4: Integration Assessment

1. **Determine integration patron**:
   - **A: Deep** — Python code → refactor into `agents/core/` or `services/`
   - **B: Adapter** — heavy deps (Java, models) → thin wrapper in `adapters/`
   - **C: External** — non-Python (TypeScript, HTML) → stays in place, consumes API
2. **Identify capabilities** to register in CapabilityRegistry
3. **Estimate effort** (hours) and risk (LOW/MED/HIGH)

### Phase 5: Report

Output a structured report:

```markdown
## Analysis Report: [Project Name]

### Overview
- Directory: `xxx/`
- LoC: N | Files: N | Stack: [...]
- Subject: [link]
- Soutenance quality: [Excellent/Bon/Correct/Insuffisant]

### Features Catalogued
1. [Feature] — [description]
...

### Core Overlap
- [Existing capability]: [overlap description]
...

### Integration Plan
- **Patron**: [A/B/C]
- **Target**: `argumentation_analysis/[path]`
- **Capabilities**: [list to register]
- **Requires**: [dependencies]
- **Effort**: [Xh]
- **Risk**: [LOW/MED/HIGH]

### Issues / Risks
- [list]
```

---

## Tools Used

- **Read**: Project files, subject docs, transcripts
- **Grep**: Search for imports, patterns, overlaps with core
- **Glob**: Find files by pattern
- **Bash**: `wc -l`, `find`, directory listing (read-only)

---

## Notes

- This skill is READ-ONLY — it does not modify any files
- Run this before `/integrate-component` to generate the analysis report
- Output can be saved to `docs/architecture/INTEGRATION_PLANS/[project].md`
