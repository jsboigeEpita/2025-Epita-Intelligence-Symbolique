# Agent Loading Mechanism

This document outlines the architecture for discovering and loading agents within the system, a core component of our modular and extensible design.

## Agent Discovery via Manifest

The system employs a manifest-based discovery mechanism, architecturally identical to the [Plugin Loading mechanism](../core/plugins/README.md). This consistency is a deliberate design choice to reduce cognitive load and promote a unified development experience.

### The `AgentLoader`

The central component for this process is the `AgentLoader` class, located in `agent_loader.py`. Its primary responsibilities are:

1.  **Discovery:** The `discover_agents()` method scans the `src/agents` directory hierarchy for subdirectories containing an `agent_manifest.json` file. This file acts as a declaration card, signaling the presence of a valid agent.
2.  **Loading:** The `load_agent()` method reads and parses the `agent_manifest.json` file to retrieve the agent's metadata.

### The `agent_manifest.json` File

Every agent must have an `agent_manifest.json` at its root. This file provides essential metadata that the `AgentLoader` uses to understand and load the agent.

**Example Manifest:**

```json
{
  "manifest_version": "1.0",
  "agent_name": "SimpleAnalyst",
  "version": "0.1.0",
  "author": "Roo Orchestrator",
  "description": "A simple agent for basic analysis tasks.",
  "entry_point": "agent.py"
}
```

By adhering to this manifest-driven approach, we ensure that agents are self-describing, and the system can dynamically discover and integrate them without requiring hard-coded registration. This mirrors the plugin architecture, reinforcing our commitment to a consistent and maintainable codebase.