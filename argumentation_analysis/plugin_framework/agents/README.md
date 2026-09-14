# Agent Loading Mechanism — withdrawn

The manifest-based agent discovery that used to live here (`agent_loader.py` +
`agent_manifest.json`) was withdrawn (#2099):

- `AgentLoader` had **zero production callers** (tests only);
- its documentation described scanning `src/agents` — a prefix dead since the
  #34/#321 consolidation;
- the single real manifest (`simple_analyst/agent_manifest.json`) pointed at an
  `agent.py` that never existed on disk.

What remains in this subtree: `__init__.py` (empty) and `personalities/` — an
empty reserved slot whose disposition is tracked by #2102 §6.

Agents actually used in production are not discovered: they are built by
`argumentation_analysis/agents/factory.py` and registered in the
`CapabilityRegistry` (see `orchestration/registry_setup.py`).
