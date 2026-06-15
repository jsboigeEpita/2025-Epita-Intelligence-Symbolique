# FB-19 Design — Taxonomy Deep-Descent: Agent-Guided Exploration Beyond Depth 2-3

> ## ⚠️ SUPERSEDED by FB-30 (#1107, 2026-06-15) — mechanical beam REMOVED
>
> The **agent-guided beam descent** described below (§2) was implemented as the
> mechanical per-level `_beam_descent` (`fallacy_workflow_plugin.py`, #1044) —
> a Python loop that showed the LLM only immediate children, kept top-k, and
> descended one level per iteration under a hard `MAX_DEPTH_PER_BRANCH = 8` cap.
> That made the 12 leaf nodes at taxonomy depth 9-10 **structurally
> unreachable** and re-determinised a navigation that was originally (summer
> 2025, commit `d2fdd930`) a free LLM-driven `explore_branch(any_pk)` walk with
> **no cap**.
>
> **FB-30 restores the agentic design BY SUBTRACTION** (anti-pendule: one
> scheme, not two):
> - `MAX_DEPTH_PER_BRANCH` removed — taxonomy leaves are the only cap.
> - `_beam_descent` + its Phase 3b call **deleted**.
> - Runaway protection (#708) preserved by a generous per-branch LLM-**call**
>   budget (`MAX_NAVIGATION_LLM_CALLS = 18`), NOT a depth cap.
> - The navigation prompt shows a **multi-level cluster**
>   (`_render_subtree_cluster`) so the LLM can jump levels via
>   `explore_branch(any_pk)` — exactly the original design.
> - FB-27 (#1101) case-(c) intermediate-confirm + D6/D7 directives preserved.
>
> The design rationale in §1 (why deep nodes were MISSED) and §5 (expected
> impact) remain valid; only the **mechanism** (§2 beam) is superseded. Tests:
> `tests/unit/argumentation_analysis/test_fb30_agentic_navigation.py`.

---

**Issue**: #1040 (Epic #947 follow-up — root cause of MISSED D3/D6/D7)
**Author**: po-2023 worker (design)
**Date**: 2026-06-11
**Status**: SUPERSEDED (beam mechanism) — see banner above. Problem analysis (§1) and impact (§5) still valid.

---

## 1. Problem Statement

The fallacy taxonomy (`taxonomy_full.csv`, ~1 550 nodes, max depth 10) **already covers** the yardstick dimensions that the pipeline MISSED:

| Dimension | Taxonomy Node | PK | Depth |
|-----------|--------------|----|-------|
| D1 Jargon | "Preuve par le jargon prestigieux" | 193 | 6 |
| D3 Populism | "Populisme" | 1211 | 8 |
| D6 Circular | "Argument circulaire" | 699 | 5+ |
| D6 Circular | "Pétition de principe" | 183/698 | 4+ |
| D8 Permission | "Escalade d'engagement" | 433 | 5+ |
| D8 Permission | "Gish gallop" | 475/772/1331 | varies |
| (bonus) | "Sophisme de la motte castrale" | 364/875 | — |

But the detection pipeline **cannot reach them**:

1. `french_fallacy_adapter.py:70` loads **taxonomy_medium** (depth 1+2 = 28 labels)
2. `french_fallacy_adapter.py:579-581` drills to **depth 2-3 only** in stage 2 of hierarchical NLI
3. Discriminating nodes at depth 5-8 are **structurally out of reach**

The exploration primitive `_internal_explore_hierarchy` (`informal_definitions.py:195`) exists but is not driven — it provides level-by-level navigation (max 15 children per step) that an agent could use iteratively, but the DAG pipeline never invokes it.

---

## 2. Design — Agent-Guided Beam Descent

### 2.1 Core Idea

Instead of expanding the flat classification to depth 8 (combinatorial explosion: 1 550 nodes → dilution), an **LLM agent guides a beam search** through the taxonomy tree, selecting the most promising branches at each level based on the text content.

### 2.2 Algorithm

```
Input: text, taxonomy_full.csv, beam_width=3, max_depth=8, min_confidence=0.3

1. ROOT SELECTION: Classify text against 7 depth-1 families (existing stage 1)
   → Keep top beam_width families by confidence

2. For each selected family (beam candidates):
   LEVEL 2: _internal_explore_hierarchy(parent_pk=family_pk)
     → Present children to LLM with text context
     → LLM selects top beam_width children per candidate
   LEVEL 3: _internal_explore_hierarchy(parent_pk=selected_pk)
     → Same selection
   ...
   LEVEL K: Continue until:
     a) LLM confidence < min_confidence for all branches → prune
     b) Node has no children (leaf) → emit as result
     c) K > max_depth → emit best match at current depth
     d) Total LLM calls > budget → emit all accumulated results

3. RESULT AGGREGATION:
   - All leaf/deepest nodes collected across beam paths
   - Confidence = product of per-level selections
   - Merge with existing tier results (symbolic + flat NLI)
   - Higher confidence wins (existing ensemble merge logic)
```

### 2.3 Budget Control

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `beam_width` | 3 | At each level, explore top 3 branches per path |
| `max_depth` | 8 | Covers the deepest yardstick nodes (Populisme depth 8) |
| `max_llm_calls` | 15 | Circuit breaker: 7 families × 2 levels ≈ 14 calls max |
| `min_confidence` | 0.3 | Prune branches where the LLM is not confident |
| `max_children_per_node` | 15 | Inherited from `_internal_explore_hierarchy` |

**Worst case**: 7 families × beam_width=3 × 8 levels × 1 LLM call = 168 calls → **unacceptable**. Budget guard limits to 15 total calls, which means:
- Root selection: 1 call (7 families)
- Level 2: beam_width calls (3 branches)
- Level 3-8: beam_width calls each, but total budget = 15 → ~4-5 levels of descent per path

This is the **key trade-off**: with budget=15, the beam reaches depth 4-5 on the most promising path. To reach depth 8 (Populisme), the budget would need ~25 calls. The design allows tuning this parameter.

### 2.4 Integration Point

The beam descent replaces **stage 2** of the current `_nli_hierarchical_classify`:

**Current** (depth 2-3):
```python
# Stage 2: collect depth-2 children + depth-3 grandchildren, flat classify
children = get_children(family_pk, max_depth=3)  # flat
results = nli_classify(text, children)  # single call
```

**Proposed** (agent-guided beam):
```python
# Stage 2: iterative beam descent from family_pk
beam = BeamDescent(taxonomy=taxonomy_full, beam_width=3, max_calls=15)
results = beam.descend(text, root_pk=family_pk, agent=llm_agent)
# Returns: list of (node_pk, confidence, depth) tuples
```

The beam descent is **additive**: results merge with existing symbolic + flat NLI results. If the beam finds nothing new, the existing results stand (no regression).

### 2.5 Relationship to FB-18 PM Agentique

The beam descent is the **instrument** that the PM agentique (FB-18 Mode B) would naturally use:

- **Without PM** (DAG mode): beam descent is automated — the LLM selects branches based on text-content similarity at each level. The "guidance" is NLI confidence.
- **With PM** (agentique mode): the PM makes the branch selections, using its broader context (it has seen the Dung framework, the quality scores, the JTMS beliefs). The PM's "intuition" is informed by cross-artifact reasoning, not just text-content similarity.

Both modes produce the same type of output (taxonomy node + confidence). The difference is the selection criterion.

---

## 3. Anti-Pendule Guards

| Concern | Guard |
|---------|-------|
| Expanding flat to depth 8 | Beam search limits exploration to top-k branches, not full expansion |
| Hardcoding yardstick PKs | Descent is text-guided, not target-guided. No corpus_X-specific tuning. |
| Combinatorial explosion | Budget guard (max 15 LLM calls). Circuit breaker inherited from #708. |
| Dilution (too many nodes) | beam_width=3 means at most 3 candidates per level, not 15. |
| Regression on existing detection | Additive merge: existing results stand if beam finds nothing new. |
| Budget overrun | `max_llm_calls` hard cap. Fail-graceful: emit whatever was found so far. |

---

## 4. Value-Gates

| Gate | Criterion | Pass Condition |
|------|-----------|---------------|
| VG-D1 | Deep node reached | On synthetic text with known deep fallacy, descent reaches ≥1 node at depth ≥5 |
| VG-D2 | No regression | Existing detection (depth 2-3) results are unchanged when beam is active |
| VG-D3 | Budget respected | Total LLM calls ≤ `max_llm_calls` parameter |
| VG-D4 | Additive merge | If beam finds nothing new, output is identical to pre-beam output |

---

## 5. Expected Impact

| Dimension | Current (#1027) | Expected with beam descent | Rationale |
|-----------|-----------------|---------------------------|-----------|
| D3 Populist | MISSED | **PARTIAL** | Beam can reach Populisme PK 1211 (depth 8) if budget allows |
| D6 Circular | MISSED | **PARTIAL** | Beam reaches Argument circulaire PK 699 (depth 5) within budget |
| D7 Drive-Relief | MISSED | **PARTIAL/MISSED** | Emotional appeal nodes exist but are less clearly mapped in taxonomy |

**Honest assessment**: D3 and D6 are likely improvable with budget=15. D7 (drive-relief / emotional appeal) is less clearly represented in the taxonomy — the beam may not find a matching node even at depth 8. This is a taxonomy gap, not a pipeline gap.

**Combined with FB-18 Mode A** (deep synthesis):
- D1/D5/D8 improve via transversal synthesis (MATCH)
- D3/D6 improve via beam descent (PARTIAL)
- D7 remains uncertain (taxonomy gap)
- Aggregate: score_A from -1 to +4 → EDGES (potentially DECIDES if D7 moves to PARTIAL)

---

## 6. Privacy Compliance

- Opaque IDs only (PK numbers are taxonomy-internal, not identifying)
- No source names, authors, URLs, dates
- No `raw_text`, `full_text`, `full_text_segment`
- grep-clean (verified before commit)

---

## 7. Cross-References

| Artifact | Issue/PR | Role |
|----------|----------|------|
| FB-18 deep synthesis spec | #1039 | Complementary — PM uses beam descent as instrument |
| Phase 4 verdict rubric | #1037 / PR #1038 | Closure criteria |
| corpus_X yardstick | #952 / #958 | D1-D10 definitions |
| corpus_X benchmark | #1027 | Current scoring (MATCH 2, PARTIAL 5, MISSED 3) |
| Taxonomy CSV | `argumentation_analysis/data/taxonomy_full.csv` | ~1 550 nodes, depth 10 |
| Exploration primitive | `informal_definitions.py:195` | `_internal_explore_hierarchy` |
| Depth 2-3 drill | `french_fallacy_adapter.py:579` | Current stage 2 (to be extended) |
| LLM Budget Guard | #1029 / #1030 | Circuit breaker for budget enforcement |
