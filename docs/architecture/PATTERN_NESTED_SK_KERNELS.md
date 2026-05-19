# Pattern: Nested SK Kernels (Master/Slave)

## Problem

Some Semantic Kernel plugins need to call the LLM internally — iterative deepening over a taxonomy, multi-round voting, sub-workflow orchestration. Naively invoking `llm_service.get_chat_message_contents()` from inside a `@kernel_function` works but has two failure modes:

1. **Tool pollution** — if the plugin registers its own tools on the parent (master) kernel, the LLM in the nested call sees every tool the agent owns. The model may call `add_identified_argument` mid-taxonomy-exploration, producing spurious state mutations.
2. **Concurrency hazards** — the master kernel's `ChatHistory` and plugin registry are mutable. Multiple concurrent nested invocations sharing the master kernel race on shared state.

Baseline: `FallacyWorkflowPlugin` (PR #471) solved this internally; `IterativeDeepeningOrchestrator` (PR #471) extracts the reusable core.

## Solution: Master/Slave Kernel Architecture

The plugin holds references to the **master kernel** (the agent's kernel with full plugin set) and the **LLM service**. For each nested LLM call, it creates a **fresh slave kernel** with a narrow, constrained plugin surface.

### Invariant

```
slave_kernel = Kernel()              # fresh, never shared between calls
slave_kernel.add_service(llm_service) # same HTTP client, isolated registry
slave_kernel.add_plugin(narrow_plugin) # only the tools the sub-workflow needs
```

### Data Flow

```
Orchestration Layer
  │
  ├── master_kernel (full plugin set + shared state)
  │     │
  │     └── registers FallacyWorkflowPlugin via factory
  │              │
  │              ├── holds: master_kernel ref, llm_service ref
  │              │
  │              ├── _create_slave_kernel()
  │              │     └── fresh Kernel() + ExplorationPlugin only
  │              │           └── FunctionChoiceBehavior.Auto(auto_invoke=False)
  │              │                 └── plugin intercepts tool calls manually
  │              │
  │              └── _create_one_shot_kernel()
  │                    └── fresh Kernel() + no plugins
  │                          └── FunctionChoiceBehavior.NoneInvoke()
  │                                └── structured JSON output only
  │
  └── asyncio.gather(*tasks)  # each task owns its ChatHistory
        └── slave_kernel shared safely (read-only plugin, isolated history)
```

## Implementation: FallacyWorkflowPlugin (`fallacy_workflow_plugin.py`)

### Constructor — Master References Injected

`fallacy_workflow_plugin.py:67-102`

```python
def __init__(self, master_kernel, llm_service, ...):
    self.master_kernel = master_kernel  # held for extension, not used directly
    self.llm_service = llm_service      # shared HTTP client
    self.exploration_plugin = ExplorationPlugin(...)
```

The factory (`agents/factory.py:221-230`) special-cases this plugin:

```python
if plugin_name == "fallacy_workflow":
    instances.append(plugin_cls(master_kernel=kernel, llm_service=llm_service))
```

### Slave Kernel Factory

`fallacy_workflow_plugin.py:104-117`

1. Create fresh `Kernel()` — isolated plugin registry, no parent state
2. Add the shared `llm_service` — HTTP client is stateless, safe to share
3. Add only `ExplorationPlugin` — narrow tool surface (taxonomy navigation)
4. Set `FunctionChoiceBehavior.Auto(auto_invoke=False)` — plugin intercepts tool calls

### One-Shot Kernel Factory

`fallacy_workflow_plugin.py:119-126`

1. Fresh `Kernel()` with `llm_service` only
2. `FunctionChoiceBehavior.NoneInvoke()` — no tools, LLM must emit structured text
3. Used for free-form prompts (candidate generation, one-shot classification)

### Tool Call Execution

`fallacy_workflow_plugin.py:341-397`

Because `auto_invoke=False`, the plugin manually processes `FunctionCallContent` items:

1. Extract tool call name + arguments from LLM response
2. Call `getattr(self.exploration_plugin, short_name)(**arguments)` directly
3. Feed `FunctionResultContent` back into `ChatHistory`
4. Return parsed navigation result

This gives the plugin full observability over navigation decisions (logging, fingerprinting, timeout enforcement).

### Parallel Branch Exploration

`fallacy_workflow_plugin.py:737-856`

```python
slave_kernel, slave_settings = self._create_slave_kernel()
exploration_tasks = [
    self._explore_single_branch(slave_kernel, slave_settings, branch, ...)
    for branch in candidate_branches
]
results = await asyncio.gather(*exploration_tasks, return_exceptions=True)
```

Single slave kernel backs N parallel tasks. Safe because:
- Each task owns its `ChatHistory` (no shared mutable state)
- `ExplorationPlugin` methods are **read-only** over `TaxonomyNavigator`
- Per-task timeout via `asyncio.wait_for(..., timeout=30.0)`

## Generalized Abstraction: IterativeDeepeningOrchestrator

`orchestration/iterative_deepening.py`

### TaxonomyLike Protocol

```python
class TaxonomyLike(Protocol):
    def get_root_nodes(self) -> List[Dict]: ...
    def get_children(self, pk: str) -> List[Dict]: ...
    def get_node(self, pk: str) -> Optional[Dict]: ...
```

Any tree structure implementing these three methods can be traversed by the orchestrator.

### LeafConfirmer Protocol

```python
class LeafConfirmer(Protocol):
    async def confirm_leaf(self, node, context, slave_kernel, slave_settings, timeout): ...
```

Strategy interface decoupling the leaf-confirmation policy from the traversal engine. The `FallacyWorkflowPlugin` hardcodes this; the generalized version lets callers inject custom behavior.

### Constrained Kernel Factory

`iterative_deepening.py:99-109`

```python
def _create_constrained_kernel(self, plugin, plugin_name):
    kernel = Kernel()
    kernel.add_service(self.llm_service)
    kernel.add_plugin(plugin, plugin_name)
    settings = OpenAIPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=False)
    )
    return kernel, settings
```

Same pattern as `_create_slave_kernel`, but the plugin is **parameterized** — callers choose which narrow plugin surface to expose (Tweety query tools, Dung semantics tools, FOL signature tools).

## Factory Wiring

`agents/factory.py:102-105, 221-230, 291-298`

The plugin registry marks `fallacy_workflow` as a "complex plugin" requiring constructor args. The factory special-cases it to inject `master_kernel` and `llm_service`:

```
Plugin registry entry:
  "fallacy_workflow": ("argumentation_analysis.plugins.fallacy_workflow_plugin", "FallacyWorkflowPlugin")

get_plugin_instances (line 221):
  if plugin_name == "fallacy_workflow" and kernel is not None and llm_service is not None:
      instances.append(plugin_cls(master_kernel=kernel, llm_service=llm_service))

load_plugins_for_agent (line 291):
  same branch — passes caller's kernel as master_kernel
```

Other complex plugins follow the same pattern: `jtms` (needs `JTMSService`), `exploration` (needs `TaxonomyNavigator`, loaded by `FallacyWorkflowPlugin` internally).

## Shared vs Isolated

| Aspect | Shared | Isolated per slave call |
|--------|--------|------------------------|
| `OpenAIChatCompletion` (HTTP client) | Yes — stateless, async-safe | — |
| `ExplorationPlugin` instance | Yes — read-only methods | — |
| `TaxonomyNavigator` | Yes — immutable tree reads | — |
| `Kernel` object | — | Fresh `Kernel()` per factory call |
| Plugin registry on kernel | — | Slave: only `Exploration`; one-shot: none |
| `OpenAIPromptExecutionSettings` | — | New per factory call |
| `ChatHistory` | — | Fresh per LLM round / per branch task |

## Concurrency Invariants

1. **Slave kernel never shared between concurrent calls** — each `_create_slave_kernel()` returns a fresh instance
2. **Slave settings disable non-scoped tools** — `ExplorationPlugin` only, or none for one-shot
3. **`llm_service` shared OK** — `OpenAIChatCompletion` is HTTP-based and async-safe
4. **`asyncio.gather` on plugin invocations = kernel isolation by construction** — each task owns its `ChatHistory`

## When to Use This Pattern

- A `@kernel_function` needs to run multi-turn LLM conversations internally (iterative refinement, guided navigation, voting rounds)
- The nested LLM calls must not see or use the parent agent's full tool surface
- Multiple sub-tasks must run in parallel with isolated conversation histories

## Anti-patterns to Avoid

1. **Reusing the master kernel for nested calls** — the LLM sees every registered tool, may invoke `add_identified_argument` or `add_identified_fallacy` mid-sub-workflow
2. **Sharing `ChatHistory` between parallel tasks** — messages from one branch leak into another's context window
3. **Skipping `auto_invoke=False`** — without it, SK auto-executes tool calls, bypassing the plugin's observability and timeout enforcement
4. **Creating slave kernels at `__init__` time** — stale kernels accumulate if the plugin is long-lived; create them per-call instead

## Cross-References

- **Related pattern:** `docs/architecture/PATTERN_2PASS_SHARED_STATE.md` — shared state across 2-pass pipelines
- **Plugin implementation:** `argumentation_analysis/plugins/fallacy_workflow_plugin.py`
- **Generalized orchestrator:** `argumentation_analysis/orchestration/iterative_deepening.py`
- **Factory wiring:** `argumentation_analysis/agents/factory.py:221-230, 291-298`
- **Origin issue:** #578 (architectural note), #471 (implementation PRs)
