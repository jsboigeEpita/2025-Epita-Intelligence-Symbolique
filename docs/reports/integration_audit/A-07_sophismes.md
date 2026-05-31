# Audit A-07: Detection de Sophismes

**Issue**: N/A | **SUIVI**: Score 90% | **Date audit**: 2026-05-31

## Status: 🟢 Integrated

## What was delivered (student source)

Student project `2.3.2-detection-sophismes` delivered a French-language fallacy detection system with a 3-tier hybrid approach (symbolic rules, NLI zero-shot, LLM zero-shot), a hierarchical taxonomy of fallacies, and fine-tuned CamemBERT classification. Adapted from student's `local_db_arg/src/` codebase.

## What exists in `argumentation_analysis/`

| File | Description |
|------|-------------|
| `agents/core/informal/informal_agent.py` | `InformalAnalysisAgent(BaseAgent)` -- main agent for informal logic analysis |
| `agents/core/informal/taxonomy_sophism_detector.py` | `TaxonomySophismDetector` with 400+ node taxonomy, hierarchical descent |
| `agents/core/informal/informal_definitions.py` | `InformalAnalysisPlugin` with taxonomy loading from CSV |
| `adapters/french_fallacy_adapter.py` | `FrenchFallacyAdapter(AbstractFallacyDetector)` -- multi-tier detection facade |
| `plugins/french_fallacy_plugin.py` | `FrenchFallacyPlugin` with 3 `@kernel_function` methods |
| Data: `taxonomy_medium.csv` | 29 rows: 7 families + 1 root + 21 sub-families = 28 unique labels |

### FrenchFallacyAdapter Tier Hierarchy

| Tier | Name | Status | Description |
|------|------|--------|-------------|
| Tier 3 | Symbolic | Active | spaCy Matcher patterns, always available |
| Tier 2 | NLI zero-shot | Deprecated | mDeBERTa, shadowed by self-hosted LLM |
| Tier 2.5 | CamemBERT | Deprecated (#297) | Fine-tuned model never deployed |
| Tier 1.5 | Self-hosted LLM | Active (#297) | vLLM/text-generation-webui endpoint |
| Tier 1 | Remote LLM | Active | OpenAI via ServiceDiscovery |

## Preservation Assessment

- **7 fallacy families + 1 root = 28 unique labels** preserved in `taxonomy_medium.csv`. SUIVI incorrectly states "8 families" -- the taxonomy has 7 families plus a root node, yielding 28 labels (7 families + 1 root + 21 sub-families).
- **3-tier hybrid expanded to 5 tiers** with graceful fallback: symbolic, NLI, CamemBERT, self-hosted LLM, remote LLM. Each tier degrades gracefully if dependencies are missing.
- **Hierarchical NLI descent** added beyond the student's flat classification -- the `TaxonomySophismDetector` explores the taxonomy tree top-down rather than flat classification.
- **French-language NLP heuristics** preserved for symbolic tier (no LLM required).
- **Plugin integration** complete with 3 `@kernel_function` methods for Semantic Kernel.

## Gap Analysis

1. **CamemBERT tier (2.5) is deprecated** (#297) -- the fine-tuned model was never deployed. Code exists but is disabled by default (`enable_camembert=False`). Not a preservation gap since the student model itself was never production-ready.
2. **NLI tier (2) is deprecated** -- shadowed by self-hosted LLM, which provides better accuracy. Code retained for backward compatibility.
3. **SUIVI documentation mismatch** -- SUIVI says "8 families" but the taxonomy has 7 families + 1 root. The `taxonomy_medium.csv` contains 29 rows with 28 unique labels.

## Recommended Action

Update SUIVI and `CLAUDE.md` to state "7 families + 1 root = 28 labels" instead of "8 families". The deprecated CamemBERT and NLI tiers are correctly retained for backward compatibility. The self-hosted LLM tier (#297) is the appropriate replacement.

## Source Files

- `argumentation_analysis/agents/core/informal/informal_agent.py`
- `argumentation_analysis/agents/core/informal/taxonomy_sophism_detector.py`
- `argumentation_analysis/agents/core/informal/informal_definitions.py`
- `argumentation_analysis/adapters/french_fallacy_adapter.py`
- `argumentation_analysis/plugins/french_fallacy_plugin.py`
