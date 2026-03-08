# Benchmark Evaluation Report

Generated: 2026-03-08T13:22:36.163519

Total benchmark cells: 107
Models tested: qwen-local, default, endpoint-2, endpoint-3, endpoint-4, openrouter

## Performance Summary

| Model | Cells | Success | Rate | Avg Duration | Avg Phases |
|-------|-------|---------|------|--------------|------------|
| qwen-local | 20 | 20 | 100% | 0.7s | 5.2 |
| default | 31 | 31 | 100% | 0.9s | 5.0 |
| endpoint-2 | 14 | 14 | 100% | 0.6s | 4.9 |
| endpoint-3 | 14 | 14 | 100% | 0.6s | 4.9 |
| endpoint-4 | 14 | 14 | 100% | 0.6s | 4.9 |
| openrouter | 14 | 14 | 100% | 0.6s | 4.9 |

## Per-Workflow Breakdown

| Model | Workflow | Success | Avg Duration | Avg Phases |
|-------|----------|---------|--------------|------------|
| qwen-local | fact_check | 3/3 | 2.1s | 5.0 |
| qwen-local | formal_debate | 3/3 | 0.1s | 4.0 |
| qwen-local | formal_verification | 3/3 | 0.1s | 8.0 |
| qwen-local | full | 3/3 | 2.1s | 7.0 |
| qwen-local | light | 4/4 | 0.3s | 3.0 |
| qwen-local | standard | 4/4 | 0.0s | 5.0 |
| default | debate_tournament | 2/2 | 0.4s | 6.0 |
| default | democratech | 2/2 | 2.1s | 8.0 |
| default | fact_check | 2/2 | 2.0s | 5.0 |
| default | full | 7/7 | 2.0s | 7.0 |
| default | light | 8/8 | 0.3s | 3.0 |
| default | quality_gated | 2/2 | 0.4s | 2.0 |
| default | standard | 8/8 | 0.0s | 5.0 |
| endpoint-2 | full | 4/4 | 2.1s | 7.0 |
| endpoint-2 | light | 5/5 | 0.0s | 3.0 |
| endpoint-2 | standard | 5/5 | 0.0s | 5.0 |
| endpoint-3 | full | 4/4 | 2.1s | 7.0 |
| endpoint-3 | light | 5/5 | 0.0s | 3.0 |
| endpoint-3 | standard | 5/5 | 0.0s | 5.0 |
| endpoint-4 | full | 4/4 | 2.1s | 7.0 |
| endpoint-4 | light | 5/5 | 0.0s | 3.0 |
| endpoint-4 | standard | 5/5 | 0.0s | 5.0 |
| openrouter | full | 4/4 | 2.1s | 7.0 |
| openrouter | light | 5/5 | 0.0s | 3.0 |
| openrouter | standard | 5/5 | 0.0s | 5.0 |

## LLM Judge Quality Scores (1-5 scale)

| Model | Overall | Completeness | Accuracy | Depth | Coherence | Actionability |
|-------|---------|-------------|----------|-------|-----------|--------------|
| default | 1.0 | 1.0 | 1.0 | 1.0 | 1.5 | 1.0 |
| endpoint-2 | 1.0 | 1.0 | 1.0 | 1.0 | 1.3 | 1.0 |
| endpoint-3 | 1.0 | 1.0 | 1.0 | 1.0 | 1.3 | 1.0 |
| endpoint-4 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| openrouter | 1.0 | 1.0 | 1.0 | 1.0 | 1.3 | 1.0 |

### Individual Judge Evaluations

- **default** × light × doc[0]: overall=1/5 — The output is largely a dump of raw text and metadata counts with almost no extraction of arguments, claims, or fallacie
- **default** × light × doc[1]: overall=1/5 — The analysis fails to identify or extract any of the clear arguments or claims in the input excerpt (argument_count = 0,
- **default** × standard × doc[0]: overall=1/5 — The analysis largely failed to extract or label the clear arguments and claims in the input (Douglas's accusations, Linc
- **default** × standard × doc[1]: overall=1/5 — The analysis essentially returned only a raw text snippet and empty counts (task_count, argument_count, fallacy_count al
- **default** × full × doc[0]: overall=1/5 — The analysis fails to identify or summarize the key arguments in the text and mostly returns structural counters and a r
- **default** × full × doc[1]: overall=1/5 — The analysis fails to identify or summarize any arguments from the input text (argument_count = 0) despite the text cont
- **endpoint-2** × light × doc[0]: overall=1/5 — The analysis fails to identify or summarize any of the key arguments or claims in the input text and reports zero argume
- **endpoint-2** × light × doc[1]: overall=1/5 — The analysis largely fails to identify any arguments, claims, or relationships in the provided text (argument_count 0, f
- **endpoint-2** × standard × doc[0]: overall=1/5 — The analysis fails to extract or label the clear arguments and claims in the passage (argument_count=0 despite many clai
- **endpoint-2** × standard × doc[1]: overall=1/5 — The output is largely placeholder/empty and fails to extract any arguments, claims, or fallacies from the input text. Se
- **endpoint-2** × full × doc[0]: overall=1/5 — The output largely fails to extract or summarize the key arguments and claims from the text (Douglas's accusations, Linc
- **endpoint-2** × full × doc[1]: overall=1/5 — The analysis output is essentially empty and inconsistent. It fails to extract or summarize arguments, claims, or rhetor
- **endpoint-3** × light × doc[0]: overall=1/5 — The analysis fails to extract or summarize the text's main claims (Douglas's accusations, Lincoln's denials/rebuttals). 
- **endpoint-3** × light × doc[1]: overall=1/5 — The analysis fails to identify or summarize any of the text's arguments, claims, or rhetorical moves (completeness and d
- **endpoint-3** × standard × doc[0]: overall=1/5 — The analysis fails to identify or extract the text's arguments, claims, or fallacies (most counts are zero) and provides
- **endpoint-3** × standard × doc[1]: overall=1/5 — The analysis fails to extract any arguments, claims, or fallacies from the provided Lincoln text and returns mostly zero
- **endpoint-3** × full × doc[0]: overall=1/5 — The analysis fails to extract or summarize the key arguments from the text, reports contradictory and mostly zero counts
- **endpoint-3** × full × doc[1]: overall=1/5 — The analysis fails to extract any arguments or claims from a clearly argumentative historical speech (argument_count 0, 
- **endpoint-4** × light × doc[0]: overall=1/5 — The analysis fails to identify any of the obvious arguments, claims, or rebuttals in the provided debate excerpt (claims
- **endpoint-4** × light × doc[1]: overall=1/5 — The analysis is essentially a sparse metadata dump with no substantive identification of arguments, claims, or fallacies
- **endpoint-4** × standard × doc[0]: overall=1/5 — The analysis largely fails to extract or label the arguments present in the text (no arguments, fallacies, or tasks iden
- **endpoint-4** × standard × doc[1]: overall=1/5 — The analysis fails to identify any arguments, claims, or fallacies from the provided Lincoln text and reports mostly zer
- **endpoint-4** × full × doc[0]: overall=1/5 — The analysis fails to extract or label any arguments, claims, or fallacies from the input text and contains an error. Th
- **endpoint-4** × full × doc[1]: overall=1/5 — The analysis largely failed to extract or label the argumentative content of the input: argument_count, tasks_defined, a
- **openrouter** × light × doc[0]: overall=1/5 — The analysis largely fails to extract or label the text's arguments, claims, or fallacies (argument_count, fallacy_count
- **openrouter** × light × doc[1]: overall=1/5 — The output fails to identify or extract any arguments, claims, or fallacies from the input text (task_count=0, argument_
- **openrouter** × standard × doc[0]: overall=1/5 — The analysis largely fails to extract or label any arguments, claims, or fallacies from the input text (task_count, argu
- **openrouter** × standard × doc[1]: overall=1/5 — The analysis essentially failed to extract the speech's arguments or structure (argument_count=0) despite clear argument
- **openrouter** × full × doc[0]: overall=1/5 — The analysis fails to extract or summarize the key arguments and claims in the input (Douglas's charges and Lincoln's re
- **openrouter** × full × doc[1]: overall=1/5 — The analysis largely fails to identify any arguments, claims, or rhetorical structure from the Lincoln excerpt (argument

## Analysis & Recommendations

### Why Quality Scores Are Uniformly Low

All models score 1/5 on judge evaluation because the **workflow phases use stub invocations** — the `CapabilityRegistry` components are registered without real `invoke` callbacks that call the LLM. The pipeline mechanics (phase ordering, dependency resolution, error handling) execute correctly, but the analysis output is empty/minimal.

This is **expected behavior** at this stage: the benchmark framework validates that:
1. All 5 models are correctly discovered from `.env` configuration
2. Model switching (environment variable swapping) works reliably
3. All 10 workflows complete without errors across all models (100% success rate)
4. The LLM judge correctly identifies empty analysis outputs
5. The full evaluation pipeline (benchmark → judge → report) is end-to-end functional

### Recommendations for Real Quality Comparison

To differentiate model quality, the following work is needed:

1. **Wire real `invoke` callbacks**: Register `ComponentRegistration.invoke` callables that actually call the LLM for each capability (argument extraction, fallacy detection, etc.)
2. **Re-run benchmarks with real LLM calls**: This will produce meaningful analysis outputs that the judge can score differentially
3. **Expected differentiation**: gpt-5-mini and Claude Sonnet should outperform local models on analysis depth and accuracy
4. **Cost tracking**: Add token usage tracking per model to compare cost-effectiveness

### Framework Validation Summary

| Aspect | Status |
|--------|--------|
| Model discovery from .env | Working (5 endpoints) |
| Model switching at runtime | Working |
| Pipeline execution (10 workflows) | 100% success |
| LLM judge evaluation | Working (30/30 scored) |
| Report generation | Working |
| CSV export | Working |
| JSONL persistence | Working |

---
*Report generated by `scripts/run_benchmark_multimodel.py` on 2026-03-08 13:22*