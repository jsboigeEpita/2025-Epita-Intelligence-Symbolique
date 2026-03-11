# Skill: Integrate Component

**Version:** 1.0.0
**Usage:** `/integrate-component <project>`

---

## Objective

Take an analysis report (from `/analyze-student-project`) and execute the integration:
- Create the target sub-package
- Wrap/adapt student code according to the chosen patron (A/B/C)
- Register in CapabilityRegistry
- Write tests
- Verify non-regression

---

## Workflow

### Phase 1: Read Analysis Report

1. Read the analysis report from `docs/architecture/INTEGRATION_PLANS/<project>.md`
2. Extract: patron (A/B/C), target path, capabilities, requirements, features

### Phase 2: Create Target Structure

Based on the patron:

**Patron A (Deep):**
```
argumentation_analysis/agents/core/<component>/
  __init__.py
  <component>_agent.py     # Extends BaseAgent
  <component>_definitions.py  # Types, enums
  # Additional modules as needed
```

**Patron B (Adapter):**
```
argumentation_analysis/adapters/
  <component>_adapter.py   # Thin wrapper implementing core interface
```
Or:
```
argumentation_analysis/services/
  <component>_service.py   # Service wrapper
```

**Patron C (External):**
- No new Python files — update API endpoints if needed
- Configure CORS, add new routes in `api/`

### Phase 3: Adapt Code

1. **Import student code** — reference from original directory or copy key logic
2. **Wrap in core interfaces** — BaseAgent, LegoPlugin, AbstractAnalysisService
3. **Register in CapabilityRegistry** — add registration to an init module
4. **Remove sys.path hacks** if any
5. **Replace hardcoded models** — use ServiceDiscovery for LLM/embedding references

### Phase 4: Write Tests

Write at minimum 3 tests per component:
1. **Import test** — component can be imported without errors
2. **Registration test** — component registers correctly in CapabilityRegistry
3. **Capability test** — component provides declared capabilities

### Phase 5: Verify

1. Run `black --check` on new/modified files
2. Run `pytest tests/ --allow-dotenv --disable-jvm-session -q` — 0 regressions
3. Update the GitHub issue checklist

---

## Tools Used

- **Read**: Analysis reports, student code, core interfaces
- **Write**: New files (agents, adapters, services, tests)
- **Edit**: Modify existing files (registrations, imports)
- **Bash**: Run tests, black formatting
- **Grep/Glob**: Find files to update

---

## Notes

- Always read the target file before editing
- Follow existing code patterns (Pydantic V2, BaseAgent contract)
- Degradation gracieuse: adapters should not crash if dependencies are missing
- Run `/validate` after integration to confirm
