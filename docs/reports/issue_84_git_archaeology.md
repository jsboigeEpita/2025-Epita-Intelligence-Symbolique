# Issue #84 — Git Archaeology: Taxonomy Fallacy Detection Rebuild

## Executive Summary

The taxonomy-guided fallacy detection plugin went through **6 architectural phases** across 9 commits (Jun 29 - Jul 30, 2025), evolving from a simple parallel exploration tool to a sophisticated master-slave iterative deepening system, before being regressed to a one-shot approach that lost the hierarchical navigation capability entirely.

**Key finding**: The iterative deepening approach at commit `d2fdd930` (Phase 4) represents the most feature-complete version, with master-slave kernel architecture, parallel branch exploration, and the "double-selection" pattern (parent-confirm + child-explore). This is the primary recovery target.

---

## Timeline of Evolution

| # | Commit | Date | Phase | Description |
|---|--------|------|-------|-------------|
| 1 | `f6cf8c41` | 2025-06-29 | Initial | `FallacyWorkflowPlugin` created with `parallel_exploration` via `TaxonomyDisplayPlugin` |
| 2 | `29ea84d0` | 2025-07-01 | Sequential | Two-step exploration + identification with manual tool loop |
| 3 | `d2fdd930` | 2025-07-12 | **Enriched** | Major rewrite: master-slave architecture, `TaxonomyNavigator`, `ExplorationPlugin`, parallel branch exploration with iterative deepening |
| 4 | `18f015e1` | 2025-07-09* | Two-Step | Simplified to sequential root-selection + depth exploration (removed parallelism) |
| 5 | `f1654f83` | 2025-07-12 | **One-Shot** | Gutted iterative approach; replaced with one-shot full-taxonomy prompt + `ResultParsingPlugin` |
| 6 | `7c613a71` | 2025-07-30 | Migration | Moved to `plugins/FallacyWorkflow/` directory structure with `manifest.json` |
| 7 | `df031b34` | 2026-02-25 | Consolidation | Moved to `argumentation_analysis/plugins/fallacy_workflow_plugin.py` (current location) |

*Note: Git dates suggest `18f015e1` was authored before `d2fdd930` but committed after; the enriched version is a response to the two-step version's limitations.

---

## Phase-by-Phase Architecture Analysis

### Phase 1: Initial Parallel Exploration (`f6cf8c41`)

**Files created:**
- `argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py`
- `argumentation_analysis/agents/prompts/TaxonomyDisplayPlugin/DisplayBranch/config.json`
- `argumentation_analysis/docs/architecture_fallacy_workflows.md`

**Architecture:**
- Simple plugin with one `@kernel_function`: `parallel_exploration`
- Used `asyncio.gather` to call a Semantic Kernel prompt function (`DisplayBranch`) for multiple taxonomy nodes in parallel
- Taxonomy loaded from a static `Taxonomy` utility class (JSON tree format)
- The `DisplayBranch` was a **semantic function** (SK prompt template) that used the LLM to extract/format a taxonomy sub-branch

**Key code pattern:**
```python
class FallacyWorkflowPlugin:
    def __init__(self, kernel: Kernel):
        self.kernel = kernel
        self.taxonomy = Taxonomy()

    @kernel_function(name="parallel_exploration")
    async def parallel_exploration(self, nodes: List[str], depth: int = 1) -> str:
        display_function = self.kernel.plugins["TaxonomyDisplayPlugin"]["DisplayBranch"]
        tasks = [self.kernel.invoke(display_function, args) for node_id in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return json.dumps(aggregated_results)
```

**Taxonomy data:** Simple JSON tree (`fallacy_taxonomy.json`) with nested `children` arrays.

---

### Phase 2: Sequential Two-Step (`29ea84d0`)

**Architecture change:** Split into exploration + identification phases.

**New files:**
- `argumentation_analysis/agents/plugins/exploration_plugin.py` — `ExplorationPlugin` with `explore_branch` kernel function
- `argumentation_analysis/agents/plugins/identification_plugin.py` — `IdentificationPlugin` with Pydantic `IdentifiedFallacy` model

**Key pattern — Manual tool loop:**
```python
async def run_workflow(self, argument_text: str) -> str:
    # STEP 1: EXPLORATION — separate kernel with ExplorationPlugin
    exploration_kernel = Kernel()
    exploration_kernel.add_plugin(ExplorationPlugin(), "exploration")

    for _ in range(3):  # 3-turn exploration loop
        response = await service.get_chat_message_contents(history, settings, kernel)
        tool_calls = [item for item in response.items if isinstance(item, FunctionCallContent)]
        if not tool_calls: break
        # Manually invoke each tool call and feed results back
        for tool_call in tool_calls:
            result = await kernel.invoke(function, **arguments)
            history.add_message(FunctionResultContent(id=tool_call.id, result=str(result)))

    # STEP 2: IDENTIFICATION — separate kernel with IdentificationPlugin
    id_kernel = Kernel()
    id_kernel.add_plugin(IdentificationPlugin(), "identifier")
    # FunctionChoiceBehavior.Required forces the LLM to call identify_fallacies
```

**Important concepts:**
- **Separate kernels per phase** — different plugins available at each step
- **Manual tool invocation** (`auto_invoke=False`) — the workflow controls what happens with LLM responses
- **Pydantic-validated output** — `IdentifiedFallacy(fallacy_type, explanation, problematic_quote)`

---

### Phase 3: Enriched Master-Slave with Iterative Deepening (`d2fdd930`)

This is the **most architecturally complete version** and the primary recovery target.

**New/modified files:**
- `argumentation_analysis/agents/utils/taxonomy_navigator.py` — Created (replaces `taxonomy_utils.py`)
- `argumentation_analysis/agents/plugins/exploration_plugin.py` — Rewritten with `explore_branch` + `conclude_no_fallacy`
- `argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py` — Major rewrite

**Taxonomy data migration:** From JSON tree to **CSV flat table** with columns: `PK`, `path`, `depth`, `text_fr`, `text_en`, `desc_fr`, `desc_en`, `example_fr`, `example_en`, `Simple_name_en`, `ex_en`

**Architecture — Master-Slave Kernel Pattern:**

```
+-------------------+       +-------------------+
|   Master Kernel   |       |   Slave Kernel    |
|   (orchestrates)  | ----> |   (constrained)   |
+-------------------+       +-------------------+
| - FallacyWorkflow |       | - ExplorationPlugin|
|   Plugin          |       |   (explore_branch) |
| - llm_service     |       |   (conclude_no_    |
|                   |       |    fallacy)        |
+-------------------+       +-------------------+
```

**Key algorithm — Parallel Branch Exploration with Iterative Deepening:**

```python
async def run_guided_analysis(self, argument_text: str) -> str:
    slave_kernel, slave_exec_settings = self._create_slave_kernel()

    # PHASE 1: Present root categories WITH their children to the LLM
    # The LLM calls explore_branch for EACH plausible root category
    # -> Multiple initial candidates selected in parallel

    # PHASE 2: Explore each candidate branch IN PARALLEL
    exploration_tasks = [
        self._explore_single_branch(argument_text, pk, slave_kernel, ...)
        for pk in candidate_branch_pks
    ]
    branch_results = await asyncio.gather(*exploration_tasks)

    # PHASE 3: Reconcile results (take first non-null)
    final_node = next((res for res in branch_results if res), None)
```

**The "Double-Selection" Pattern in `_explore_single_branch`:**

At each depth level, the LLM is presented with options that include BOTH:
1. **The current parent node** (marked "PARENT - Confirm this") — selecting this means "this level is specific enough"
2. **All child nodes** (marked "CHILD - Explore this") — selecting one means "go deeper"

```python
async def _explore_single_branch(self, argument_text, start_node_pk, ...):
    for i in range(5):  # Max 5 depth levels per branch
        children = self.taxonomy_navigator.get_children(candidate_nodes[0])
        if not children:
            return self.taxonomy_navigator.get_node(candidate_nodes[0])  # Leaf = answer

        options_to_present = []
        # Option 1: CONFIRM the parent
        options_to_present.append({
            "id": current_pk,
            "description": "PARENT (Confirm this): ..."
        })
        # Options 2..N: EXPLORE a child
        for child in children:
            options_to_present.append({
                "id": child["PK"],
                "description": "CHILD (Explore this): ...",
                "example": child["example_fr"]
            })

        # LLM chooses via explore_branch function call
        # If it picks parent -> branch confirmed, return None (dead end for this branch)
        # If it picks child -> iterate deeper
```

**Slave Kernel Configuration:**
```python
def _create_slave_kernel(self):
    slave_kernel = Kernel()
    slave_kernel.add_service(self.llm_service)
    slave_kernel.add_plugin(self.exploration_plugin, "Exploration")
    slave_exec_settings = OpenAIPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=False)
    )
    return slave_kernel, slave_exec_settings
```

**Critical design decisions:**
- `auto_invoke=False` — the plugin controls tool execution, not the SK auto-invoke
- System message: "Your ONLY purpose is to classify text by navigating a taxonomy. You MUST call one function."
- The slave LLM is highly constrained: it can ONLY call `explore_branch` or `conclude_no_fallacy`
- Phase 1 prompt includes sub-categories of each root (not just root names) for better initial selection

---

### Phase 4: Simplified Two-Step Sequential (`18f015e1`)

**Change:** Removed parallel branch exploration, kept the iterative deepening but made it purely sequential.

**Algorithm:**
```
Step 1: Present ONLY root categories -> LLM picks ONE
Step 2: Loop (max 10 iterations):
  - Present current node's children + parent-confirm option
  - LLM picks next node or confirms current
  - If leaf reached, conclude
  - If LLM calls conclude_fallacy/conclude_no_fallacy, finish
  - If LLM re-selects parent, finish
```

**Added:** `conclude_fallacy(fallacy_name)` function call support alongside `conclude_no_fallacy`.

**Removed:** Parallel exploration of multiple branches. Only one path is followed.

---

### Phase 5: One-Shot Regression (`f1654f83`)

**All iterative navigation removed.** The entire taxonomy is dumped into a single prompt.

**New file:** `result_parsing_plugin.py` — trivial plugin with `parse_and_return_fallacy(fallacy_name) -> fallacy_name`

**Architecture:**
```python
# Dump full taxonomy as JSON into prompt
full_taxonomy_json = self.taxonomy_navigator.get_taxonomy_as_json()
prompt = f"Analyze: {text}\n\nTAXONOMY:\n{full_taxonomy_json}\n\nIdentify the fallacy."

# Force LLM to call parse_and_return_fallacy
settings = FunctionChoiceBehavior.Required(function_name="parse_and_return_fallacy")

response = await llm_service.get_chat_message_content(history, settings, kernel)
```

**What was lost:**
- Iterative deepening through taxonomy tree
- Parallel branch exploration
- Double-selection (parent-confirm vs child-explore) pattern
- Constrained slave LLM with limited tool access
- Progressive narrowing of the search space
- Examples shown in context at each depth level

---

### Phase 6: Current State (post-consolidation)

**File:** `argumentation_analysis/plugins/fallacy_workflow_plugin.py`

The current version is a further simplification of the one-shot approach:
- `FunctionChoiceBehavior.NoneInvoke()` — LLM responds in plain text, no function calls at all
- No `ResultParsingPlugin` — result is `str(response).strip()`
- Added `trace_log_path` parameter for file-based logging
- The `TaxonomyNavigator` is still instantiated but only used for `get_taxonomy_as_json()`

---

## Supporting Components (Still Exist)

### `TaxonomyNavigator` (`argumentation_analysis/agents/utils/taxonomy_navigator.py`)

Still present and functional. Provides:
- `get_root_nodes()` — nodes at depth 1
- `get_children(node_id)` — direct children by path prefix matching
- `get_parent(node_id)` — parent by path truncation
- `is_leaf(node_id)` — check for leaf nodes
- `get_branch_as_str(node_id)` — formatted branch display
- `get_taxonomy_preview(depth, language, details)` — tree preview up to depth N
- `get_taxonomy_as_json()` — full dump (used by current one-shot)

**Data format:** Flat CSV with `PK`, `path` (dot-separated like "1.2.3"), `depth`, multilingual fields.

### `ExplorationPlugin` (DELETED)

Was at `argumentation_analysis/agents/plugins/exploration_plugin.py`. Last version provided:
- `explore_branch(node_pk)` — returns JSON of node + children
- `conclude_no_fallacy(reason)` — signals "no fallacy found"

### `IdentificationPlugin` (DELETED)

Was at `argumentation_analysis/agents/plugins/identification_plugin.py`. Provided:
- `identify_fallacies(fallacies: List[IdentifiedFallacy])` — Pydantic-validated structured output
- `IdentifiedFallacy(fallacy_type, explanation, problematic_quote)` — data model

### `ResultParsingPlugin` (DELETED)

Was at `argumentation_analysis/agents/plugins/result_parsing_plugin.py`. Trivial:
- `parse_and_return_fallacy(fallacy_name) -> fallacy_name` — pass-through for forced function calls

---

## Comparison: Iterative Deepening vs One-Shot

| Aspect | Iterative Deepening (d2fdd930) | Current One-Shot |
|--------|-------------------------------|------------------|
| **Taxonomy handling** | Progressive narrowing, 3-5 nodes shown per step | Full taxonomy dumped (~100+ entries) |
| **LLM cognitive load** | Low per step (5-10 options) | High (entire taxonomy at once) |
| **Accuracy potential** | High — examples shown in context | Lower — LLM must scan everything |
| **Token usage** | Multiple short calls | Single large call |
| **Latency** | Higher (multiple round-trips) | Lower (single call) |
| **Navigation trace** | Full path through taxonomy logged | No navigation trace |
| **Robustness** | Handles LLM confusion via branch backtracking | Single point of failure |
| **Parallel exploration** | Yes — multiple branches simultaneously | N/A |
| **Structured output** | Via `IdentifiedFallacy` Pydantic model | Plain text string |

---

## Recommended Rebuild Strategy

### Goal
Restore the iterative deepening approach with the following improvements based on lessons learned across all phases.

### Architecture Proposal

```
FallacyWorkflowPlugin (rebuilt)
├── __init__(master_kernel, llm_service, taxonomy_file_path)
├── _create_slave_kernel() -> (Kernel, Settings)
│   └── Loads ExplorationPlugin with explore_branch + conclude_fallacy + conclude_no_fallacy
├── run_guided_analysis(argument_text) -> AnalysisResult
│   ├── Phase 1: Root category selection (show roots + their children descriptions)
│   ├── Phase 2: Iterative deepening (max_depth=5, double-selection pattern)
│   ├── Phase 3: Result structuring (Pydantic IdentifiedFallacy model)
│   └── Fallback: one-shot if iterative fails after max retries
└── _explore_branch(text, start_pk, slave_kernel, settings) -> Optional[dict]

ExplorationPlugin (rebuilt)
├── explore_branch(node_pk) -> JSON branch info
├── conclude_fallacy(fallacy_name, confidence, explanation) -> structured result
└── conclude_no_fallacy(reason) -> confirmation

IdentifiedFallacy (Pydantic model)
├── fallacy_type: str
├── taxonomy_path: str  # NEW: full path through taxonomy
├── explanation: str
├── problematic_quote: str
├── confidence: float  # NEW
└── navigation_trace: List[str]  # NEW: nodes visited during deepening
```

### Key Design Decisions

1. **Keep `auto_invoke=False`** — The workflow must control tool execution, not SK's auto-invoke. This is critical for the iterative loop to work.

2. **Restore the double-selection pattern** — Present parent (confirm) + children (explore deeper) at each step. This was the core innovation of `d2fdd930`.

3. **Sequential first, parallel optional** — Start with the simpler sequential approach from `18f015e1`, add parallel branch exploration as an option. The parallel version in `d2fdd930` was more complex but also more thorough.

4. **Add one-shot fallback** — If iterative deepening fails (LLM doesn't cooperate, max iterations reached), fall back to the current one-shot approach. This makes the system more robust.

5. **Structured output via conclude_fallacy** — Rather than the plain text return of the one-shot approach, use a `conclude_fallacy` function call that forces structured output (name, confidence, explanation).

6. **Integrate with CapabilityRegistry** — Register as a capability provider for "fallacy_detection" so it can be discovered by the unified pipeline.

7. **Preserve `TaxonomyNavigator`** — It already has everything needed. No changes required.

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `argumentation_analysis/plugins/fallacy_workflow_plugin.py` | **REWRITE** | Restore iterative deepening with one-shot fallback |
| `argumentation_analysis/plugins/exploration_plugin.py` | **CREATE** | Restore `explore_branch`, `conclude_fallacy`, `conclude_no_fallacy` |
| `argumentation_analysis/plugins/identification_models.py` | **CREATE** | Pydantic `IdentifiedFallacy` model with new fields |
| `tests/unit/argumentation_analysis/plugins/test_fallacy_workflow_plugin.py` | **UPDATE** | Add tests for iterative deepening, double-selection, fallback |
| `tests/integration/test_fallacy_iterative_deepening.py` | **CREATE** | Integration test with mocked LLM responses |

### Migration Path

1. Create `ExplorationPlugin` and `IdentifiedFallacy` model (no existing code changes)
2. Rewrite `FallacyWorkflowPlugin` with both modes (iterative + one-shot fallback)
3. Update `InformalFallacyAgent` to pass taxonomy path when loading the plugin
4. Add unit tests for the new iterative logic
5. Integration test with real or mocked LLM
6. Register in `CapabilityRegistry` via `setup_registry()`

---

## Appendix: Recovered Key Code Snippets

### A. ExplorationPlugin (`d2fdd930`)

```python
class ExplorationPlugin:
    def __init__(self, taxonomy_navigator: TaxonomyNavigator):
        self.taxonomy_navigator = taxonomy_navigator

    @kernel_function(name="explore_branch")
    def explore_branch(self, node_pk: str) -> str:
        node = self.taxonomy_navigator.get_node(node_pk)
        children = self.taxonomy_navigator.get_children(node_pk)
        branch_info = {
            "id": node.get("PK"),
            "name": node.get("nom_vulgarise"),
            "description": node.get("description_courte"),
            "children": [{"id": c.get("PK"), "name": c.get("nom_vulgarise"), ...} for c in children]
        }
        return json.dumps(branch_info)

    @kernel_function(name="conclude_no_fallacy")
    def conclude_no_fallacy(self, reason: str) -> str:
        return f"Conclusion enregistrée : {reason}"
```

### B. Double-Selection Options Format (`d2fdd930`)

```python
options_to_present = []
# Parent node as "confirm" option
options_to_present.append({
    "id": current_pk,
    "name": current_node_data[f"text_{self.language}"],
    "description": f"PARENT (Confirm this): {current_node_data[f'desc_{self.language}']}"
})
# Children as "explore" options
for child in children:
    options_to_present.append({
        "id": child["PK"],
        "name": child[f"text_{self.language}"],
        "description": f"CHILD (Explore this): {child[f'desc_{self.language}']}",
        "example": child[f'example_{self.language}']
    })
```

### C. Slave Kernel Creation (`d2fdd930`)

```python
def _create_slave_kernel(self):
    slave_kernel = Kernel()
    slave_kernel.add_service(self.llm_service)
    slave_kernel.add_plugin(self.exploration_plugin, "Exploration")
    slave_exec_settings = OpenAIPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(auto_invoke=False)
    )
    return slave_kernel, slave_exec_settings
```

### D. IdentificationPlugin + Pydantic Model (`29ea84d0`)

```python
class IdentifiedFallacy(BaseModel):
    fallacy_type: str = Field(..., description="Le type de sophisme")
    explanation: str = Field(..., description="L'explication")
    problematic_quote: str = Field(..., description="La citation exacte")

class IdentificationPlugin:
    @kernel_function(name="identify_fallacies")
    def identify_fallacies(self, fallacies: List[IdentifiedFallacy]) -> List[IdentifiedFallacy]:
        return fallacies  # Pydantic validates structure
```

### E. Original Architecture Doc (`f6cf8c41`)

The original design document (`architecture_fallacy_workflows.md`) described:
- **`FallacyIdentificationPlugin`**: Atomic functions (`explore_branch`, `identify_fallacies`)
- **`FallacyWorkflowPlugin`**: Orchestration functions (`parallel_exploration`, `sequential_exploration`)
- **`DisplayBranch`**: Semantic function (SK prompt template) for LLM-formatted branch display
- Separation of concerns: atomic operations vs. orchestration workflows

---

## Appendix: Taxonomy Data Formats

### Original JSON Tree (`fce0e453`)
```json
{
  "id": "fallacy_root",
  "name": "Taxonomie des Sophismes",
  "children": [
    {
      "id": "relevance",
      "name": "Sophismes de Pertinence",
      "children": [
        { "id": "ad_hominem", "children": [...] }
      ]
    }
  ]
}
```

### CSV Flat Table (introduced in `d2fdd930`)
Columns: `PK`, `path`, `depth`, `text_fr`, `text_en`, `desc_fr`, `desc_en`, `example_fr`, `example_en`, `Simple_name_en`, `ex_en`, `nom_vulgarise`, `description_courte`

The CSV format with `path` (dot-separated, e.g., "1.2.3") and `depth` is what `TaxonomyNavigator` uses. Parent-child relationships are computed from path prefixes, not stored explicitly.

---

*Report generated 2026-03-08 by git archaeology on commits `f6cf8c41` through `df031b34`.*
