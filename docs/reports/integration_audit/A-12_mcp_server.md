# Audit A-12: MCP Server

**Issue**: #35 | **SUIVI**: Score 90% | **Date audit**: 2026-05-31

## Status: 🟢 Integrated

## What was delivered (student source)

Student project delivered an MCP (Model Context Protocol) server that exposes the argumentation analysis platform's capabilities as tools consumable by LLM clients. The server mirrors the existing Web API functionality and adds V2 infrastructure tools for workflow management, conversation orchestration, and capability discovery.

Key features:
- V1 tools: mirror of existing web API endpoints (analysis, agents, etc.)
- V2 tools: workflow creation, conversation management, capability discovery, specialized analysis
- Transport: streamable-http protocol
- Containerized: Dockerfile for deployment

## What exists in argumentation_analysis/

### Server implementation

- **`services/mcp_server/main.py`** — `MCPService` class, the main server entry point. Handles tool registration, request routing, and response formatting.
- **`services/mcp_server/session_manager.py`** — Session management for stateful conversations across tool calls.
- **`services/mcp_server/server_config.py`** — Configuration management (ports, transports, timeouts).
- **`services/mcp_server/Dockerfile`** — Container build configuration.
- **`services/mcp_server/README.md`** — Usage documentation.

### Tool surface

**23 tools total** organized in two tiers:

**V1 (10 tools)** — Web API mirror:
- Direct HTTP passthrough to existing web API endpoints
- Covers analysis, extraction, and basic agent interaction

**V2 (13 tools)** — Infrastructure tools:
- `workflow` tools — create, configure, and execute analysis workflows
- `conversation` tools — manage multi-turn agent conversations
- `capability` tools — discover and query available capabilities
- `specialized` tools — invoke specific analysis modes (fallacy detection, quality scoring, etc.)

### Integration

The MCP server reuses the existing Web API services (ServiceManager, agents, plugins) rather than reimplementing analysis logic. This is a thin orchestration layer over the existing architecture.

## Preservation Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| V1 tool surface | **Preserved** | All web API endpoints mirrored |
| V2 tool surface | **Preserved** | Workflow, conversation, capability tools all present |
| Session management | **Preserved** | Stateful conversations across tool calls |
| Transport | **Preserved** | streamable-http as designed |
| Service reuse | **Correct** | Delegates to existing Web API services, no duplication |
| Dockerfile | **Preserved** | Minor issue (see below) |

## Gap Analysis

### Minor: Dockerfile references non-existent conda environment

The `Dockerfile` references conda environment `projet-is-v2` which does not match any documented environment in CLAUDE.md. The documented environments are `projet-is` and `projet-is-roo-new`.

**Impact**: Low. The Dockerfile is likely a template that needs updating per deployment. Does not affect local development or CI. Should be aligned with documented environments for consistency.

## Recommended Action

1. **Fix Dockerfile conda env** — Update the environment name in the Dockerfile to match one of the documented environments (`projet-is-roo-new` preferred, or `projet-is` for CI parity).
2. No other changes needed — the integration is complete and the architecture is clean (thin orchestration layer over existing services).

## Source Files

| File | Role |
|------|------|
| `argumentation_analysis/services/mcp_server/main.py` | MCPService (server entry point) |
| `argumentation_analysis/services/mcp_server/session_manager.py` | Session management |
| `argumentation_analysis/services/mcp_server/server_config.py` | Configuration |
| `argumentation_analysis/services/mcp_server/Dockerfile` | Container build |
| `argumentation_analysis/services/mcp_server/README.md` | Documentation |
