# SCDA Spectacular Capstone Bundle

Full artefact bundle for Epic #530 (Spectacular Demonstrator for Conversational Analysis). Four politically-diverse corpora analyzed through the 8-agent SCDA pipeline, exported in multiple formats with balance analysis, cross-reference graphs, and re-prompt traces.

## Corpus Overview

| Corpus | Arguments | Fallacies | Counter-args | JTMS Beliefs | Duration |
|--------|-----------|-----------|-------------|-------------|----------|
| A | 20 | 13 | 4 | 3 | ~39 min |
| B | 17 | 17 | 7 | 13 | ~36 min |
| C | 10 | 14 | 1 | 6 | ~41 min |
| D | 16* | 17 | 4 | 5 | ~37 min |

**Total: 63 arguments, 44+ fallacies across 4 corpora.**

*\*Corpus D: 16 arguments extracted by the pipeline (confirmed in `deep_synthesis_report.md`). Bundle artefacts show 0 due to a now-fixed snapshot bug — see `corpus_d_caveat_investigation.md` for details.*

## Quick Start — What to Open First

| You want to see... | Open this file |
|--------------------|---------------|
| Executive summary + all 4 properties | `../EPIC_530_SCDA_SPECTACULAR_FINAL_REPORT.md` |
| Soutenance slide deck (15 slides) | `soutenance_slides.md` |
| Human-readable state dump | `corpus_A.md`, `corpus_B.md`, `corpus_C.md`, `corpus_D.md` |
| Interactive HTML presentation | `corpus_A.html` (collapsible sections + summary cards) |
| Conversation balance per corpus | `balance_corpus_A.md`, `balance_corpus_B.md`, `balance_corpus_C.md` |
| Interactive cross-ref graph explorer | `cross_ref_viz.html` (open in browser — D3.js, filter by edge type, corpus dropdown) |
| Static cross-reference graphs | `cross_ref_graph_corpus_A.mmd` (Mermaid), `*.dot` (Graphviz) |
| Re-prompt trace evidence | `reprompt_trace_corpus_A.json` |
| Machine-readable state | `corpus_A.json` |
| Spreadsheet analysis | `A/csv/args.csv`, `A/csv/fallacies.csv`, etc. |

## Artefact Inventory

### State Dumps (5 formats × 4 corpora)

| Format | Corpus A | Corpus B | Corpus C | Corpus D |
|--------|----------|----------|----------|----------|
| JSON | `corpus_A.json` | `corpus_B.json` | `corpus_C.json` | `corpus_D.json` |
| XML | `corpus_A.xml` | `corpus_B.xml` | `corpus_C.xml` | `corpus_D.xml` |
| Markdown | `corpus_A.md` | `corpus_B.md` | `corpus_C.md` | `corpus_D.md` |
| CSV tables | `A/csv/*.csv` | `B/csv/*.csv` | `C/csv/*.csv` | `D/csv/` |
| HTML | `corpus_A.html` | `corpus_B.html` | `corpus_C.html` | `corpus_D.html` |

### Balance Reports (Track Q)

- `balance_corpus_A.md` — Shannon entropy balance score, per-agent turn/char distribution, dominance alerts
- `balance_corpus_B.md`
- `balance_corpus_C.md`

### Cross-Reference Graphs (Track Q + R + S, 4 formats × 4 corpora)

- `cross_ref_viz.html` — **Interactive D3.js visualizer** (force-directed layout, edge-type filters, corpus dropdown, hover tooltips, zoom/pan)
- `cross_ref_graph_corpus_A.json` — Full graph data (nodes + edges + metadata)
- `cross_ref_graph_corpus_A.dot` — Graphviz DOT format
- `cross_ref_graph_corpus_A.mmd` — Mermaid diagram (renderable in GitHub)

### Re-Prompt Traces (corpora A/B/C)

- `reprompt_trace_corpus_A.json` — Per-turn fingerprint deltas, agent, outcome (ok/reran/gave_up)
- `reprompt_trace_corpus_B.json`
- `reprompt_trace_corpus_C.json`

### Soutenance Slide Deck

- `soutenance_slides.md` — Marp-compatible 15-slide presentation (exportable to PPTX/PDF)

## How Each Artefact Answers a Jury Question

| Jury Question | Artefact | Answer |
|---------------|----------|--------|
| "Is the conversation balanced?" | `balance_corpus_*.md` | Shannon entropy balance score, agent participation distribution |
| "Is the state rich and interconnected?" | `cross_ref_graph_corpus_*.json` | 7 edge types, density metrics showing cascade propagation |
| "Can you export in multiple formats?" | 20+ state dump files across 5 formats | JSON, XML, Markdown, CSV, HTML |
| "How do you handle LLM failures?" | `reprompt_trace_corpus_*.json` | Fingerprint-delta tracking, ok/reran/gave_up outcomes (12 events across 3 corpora) |
| "What fallacies are detected?" | `corpus_*.md` fallacy section | 44+ fallacies across 4 corpora, 6+ families |
| "How do formal methods connect?" | `cross_ref_viz.html` | Interactive explorer: argument→fallacy→JTMS→BR cascade, filter by edge type, switch corpus |
| "How do formal methods connect?" (static) | `cross_ref_graph_corpus_*.mmd` | Visual showing argument→fallacy→JTMS→BR cascade |
| "Does it generalize?" | Corpus D (4th corpus, 16 args) | Validated on N=4, distinct rhetorical profile, all ≥10 args |

## Privacy

All artefacts use opaque IDs only. No plaintext from the encrypted dataset is included. Corpus labels (A, B, C, D) are abstract — no author names, speech titles, or dates appear in git-tracked files.

## Reproduction

```bash
# Generate the full bundle from pipeline outputs
conda run -n projet-is-roo-new python scripts/analysis/generate_spectacular_bundle.py

# Run a single corpus (~30 min)
python examples/soutenance/run_corpus_d.py
```

---
*Generated by `scripts/analysis/generate_spectacular_bundle.py`*
