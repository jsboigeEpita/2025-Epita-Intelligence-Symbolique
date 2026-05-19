# SCDA Spectacular Demo Bundle

This directory contains the full artefact bundle for Epic #530 (Spectacular Demonstrator for Conversational Analysis). Each corpus (A, B, C) is analyzed through the SCDA pipeline and exported in multiple formats with balance analysis and cross-reference graphs.

## Quick Start — What to Open First

| You want to see... | Open this file |
|--------------------|---------------|
| Executive summary + all 4 properties | `../EPIC_530_SCDA_SPECTACULAR_FINAL_REPORT.md` |
| Human-readable state dump | `corpus_A.md`, `corpus_B.md`, `corpus_C.md` |
| Conversation balance per corpus | `balance_corpus_A.md`, `balance_corpus_B.md`, `balance_corpus_C.md` |
| Cross-reference graph visualization | `cross_ref_graph_corpus_A.mmd` (Mermaid), `*.dot` (Graphviz) |
| Re-prompt trace evidence | `reprompt_trace_corpus_A.json` |
| Machine-readable state | `corpus_A.json` |
| HTML presentation | `corpus_A.html` |
| Spreadsheet analysis | `corpus_A/csv/*.csv` |

## Artefact Inventory

### State Dumps (6 formats × 3 corpora)

| Format | Corpus A | Corpus B | Corpus C |
|--------|----------|----------|----------|
| JSON | `corpus_A.json` | `corpus_B.json` | `corpus_C.json` |
| XML | `corpus_A.xml` | `corpus_B.xml` | `corpus_C.xml` |
| Markdown | `corpus_A.md` | `corpus_B.md` | `corpus_C.md` |
| CSV bundle | `corpus_A/csv/` | `corpus_B/csv/` | `corpus_C/csv/` |
| HTML | `corpus_A.html` | `corpus_B.html` | `corpus_C.html` |

### Balance Reports (Track Q)

- `balance_corpus_A.md` — Shannon entropy balance score, per-agent turn/char distribution, dominance alerts
- `balance_corpus_B.md`
- `balance_corpus_C.md`

### Cross-Reference Graphs (Track Q, 3 formats × 3 corpora)

- `cross_ref_graph_corpus_A.json` — Full graph data (nodes + edges + metadata)
- `cross_ref_graph_corpus_A.dot` — Graphviz DOT format
- `cross_ref_graph_corpus_A.mmd` — Mermaid diagram (renderable in GitHub)

### Re-Prompt Traces (Track P)

- `reprompt_trace_corpus_A.json` — Per-turn fingerprint deltas, agent, outcome (ok/reran/gave_up)
- `reprompt_trace_corpus_B.json`
- `reprompt_trace_corpus_C.json`

## How Each Artefact Answers a Jury Question

| Jury Question | Artefact | Answer |
|---------------|----------|--------|
| "Is the conversation balanced?" | `balance_corpus_*.md` | Shannon entropy balance score ~0.98-0.99 across all corpora |
| "Is the state rich and interconnected?" | `cross_ref_graph_corpus_*.json` | 7 edge types, density metrics showing cascade propagation |
| "Can you export in multiple formats?" | 18 state dump files across 6 formats | JSON, XML, Markdown, CSV, HTML, Rich CLI |
| "How do you handle LLM failures?" | `reprompt_trace_corpus_*.json` | Fingerprint-delta tracking, ok/reran/gave_up outcomes |
| "What fallacies are detected?" | `corpus_*.md` fallacy section | 44 total fallacies across 3 corpora, 6 families |
| "How do formal methods connect?" | `cross_ref_graph_corpus_*.mmd` | Visual showing argument→fallacy→JTMS→BR cascade |

## Privacy

All artefacts use opaque IDs only. No plaintext from the encrypted dataset is included. Corpus labels (A, B, C) are abstract — no author names, speech titles, or dates appear in git-tracked files.

## Reproduction

```bash
# Run SCDA on corpus A (gpt-5-mini, ~20 min)
conda run -n projet-is-roo-new python examples/soutenance/run_corpus_a.py

# Export all formats
conda run -n projet-is-roo-new python scripts/analysis/export_scda_state.py --format all --output docs/reports/spectacular/
```
