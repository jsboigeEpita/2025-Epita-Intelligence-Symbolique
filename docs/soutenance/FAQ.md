# Soutenance FAQ — 30+ Anticipated Questions

Evidence-backed answers for examiner questions. Cross-linked to slide deck where applicable.

---

## Architecture

### Q1: Why a 3-tier agent hierarchy (Strategic/Tactical/Operational)?

The 3-tier model maps directly to the problem complexity: Strategic orchestrators manage end-to-end workflows (17-phase spectacular pipeline), Tactical coordinators handle inter-agent dialogues (Sherlock/Watson, Walton-Krabbe debates), and Operational agents perform single-domain tasks (fallacy detection, FOL reasoning, JTMS belief updates). This separation prevents coupling — adding a new operational agent (e.g., a Modal Logic agent) requires zero changes to strategic or tactical layers. Implemented in `argumentation_analysis/core/capability_registry.py` with `CapabilityRegistry` as the central lookup.

### Q2: Why Semantic Kernel rather than LangChain or raw OpenAI SDK?

Semantic Kernel provides native `ChatCompletionAgent` with `AgentGroupChat` for multi-turn agent conversations — critical for the Sherlock/Watson paradigm. LangChain's agent abstractions are single-agent focused. SK also provides `@kernel_function` plugin decorators that auto-expose agent methods to the orchestration layer, eliminating boilerplate. The `AgentFactory` (`agents/factory.py`) leverages this to wire agents with a single `create_*()` call. Trade-off: SK has fewer community plugins than LangChain, but our custom plugins (`FrenchFallacyPlugin`, `GovernancePlugin`, `QualityScoringPlugin`) fill the gap.

### Q3: Why Tweety/JPype for formal reasoning instead of pure Python?

Tweety is the most comprehensive argumentation reasoning library available — 12 ranking reasoners for Dung semantics, SAT-based solvers for FOL, and ATMS implementations. No pure-Python equivalent exists with this breadth. The JPype bridge (`argumentation_analysis/core/jvm_setup.py`) loads the JVM once and reuses it across all formal phases (PL, FOL, Modal, Dung, ASPIC, ATMS). Trade-off: JVM startup cost (~3s) and memory overhead (~30MB), plus Windows DLL load ordering requires importing torch/transformers before jpype (handled in `conftest.py`).

### Q4: Why DAG-based pipeline instead of simple sequential execution?

The spectacular pipeline has 17 phases, but not all depend on each other. Phase DAG analysis shows that phases at the same level (e.g., PL + FOL + Modal, or Dung + ASPIC) are independent and can run in parallel. PR #438 implemented `asyncio.gather()` per DAG level, reducing theoretical wall-clock from 80s to ~50s (-37%). Sequential execution would leave CPU idle during LLM API calls. The DAG is declared via `WorkflowDSL.add_phase(capability=..., depends_on=...)` in `orchestration/workflow_dsl.py`.

### Q5: How does the Lego architecture work?

`CapabilityRegistry` is a central dictionary mapping capability names to implementations (agents, plugins, services). `AgentFactory` creates agents with proper SK kernel wiring. `WorkflowDSL` declares phases declaratively. Any new component registers via `register_agent()` / `register_plugin()`, and the pipeline discovers it via `find_*_for_capability()`. This means adding a new fallacy detector requires only: (1) inherit `BaseAgent`, (2) register, (3) add to workflow — no orchestration code changes. See `argumentation_analysis/core/capability_registry.py`.

---

## Models & LLM

### Q6: Why gpt-5-mini as the primary model?

Cost-quality trade-off. gpt-5-mini provides sufficient reasoning for argument extraction, fallacy detection, and NL-to-logic translation at ~$0.05-0.15 per full analysis (17 phases). The 8-family fallacy taxonomy uses hybrid detection (neural + hierarchical rules), so model accuracy isn't the sole bottleneck. For formal phases (PL, FOL, Modal), the model generates candidate formulas that are validated by Tweety — incorrect formulas are rejected by the solver, not by the model. Config in `.env` via `OPENAI_CHAT_MODEL_ID`.

### Q7: What about privacy — are corpus texts sent to OpenAI?

Yes, individual text extracts are sent to OpenAI for analysis. The corpus is encrypted at rest (`extract_sources.json.gz.enc` with AES-256, passphrase in `.env`). All downstream outputs use opaque IDs (`sha256[:8]`) — the public report (`docs/reports/discourse_patterns.md`) contains zero source names, zero raw text, zero author info. Privacy plumbing was a dedicated Epic C sub-task (#409, PR #425). See `argumentation_analysis/evaluation/opaque_id.py` and `sanitize_state.py`.

### Q8: Could you use local models instead?

Yes — `argumentation_analysis/services/local_llm_service.py` is an OpenAI-compatible adapter for local endpoints. Student project 2.3.6 built this adapter. Trade-off: local models (e.g., Mistral 7B via Ollama) achieve ~60-70% of gpt-5-mini's extraction accuracy on French political text. For formal phases, accuracy drops further because local models struggle with NL-to-FOL translation. The system supports fallback: local model for extraction, cloud model for formal reasoning.

### Q9: What's the cost per analysis?

~$0.05-0.15 per full spectacular analysis (17 phases, ~45s wall-clock). The LLM phases consume 68.3% of runtime (PR #422 profiling). Each phase makes 1-3 API calls. With the LLM caching layer (PR #432, DiskCache-backed), repeated analyses of the same text with same model settings hit cache, reducing cost to $0. The batch corpus run (18 documents) cost approximately $1-3 total.

### Q10: How do you handle LLM non-determinism?

Three mechanisms: (1) **LLM caching** (PR #432) normalizes inputs by serializing system prompt + user message + tool schemas into a cache key — identical requests return cached results. (2) **Formal validation** — Tweety solvers validate all logic outputs, rejecting syntactically incorrect formulas regardless of LLM variation. (3) **Pydantic V2 validation** — all agent outputs pass through typed models (`BaseModel`), catching malformed responses at the boundary.

---

## Pipeline & Phases

### Q11: Why this specific phase order?

The DAG respects data dependencies: extraction must precede fallacy detection (which needs argument boundaries), which must precede formalization (which needs identified fallacies as constraints). Within each level, phases are independent: PL/FOL/Modal can run in parallel because they formalize different aspects of the same arguments. Dung/ASPIC depend on formalization outputs. Counter-argumentation depends on fallacy detection. Governance depends on all prior analysis. See the pipeline diagram in slides ("Pipeline Spectacular — 17 Phases").

### Q12: What happens when a phase fails?

The pipeline catches exceptions per-phase and marks the result as `failed=True` with error details. Subsequent phases that depend on a failed phase receive empty inputs and produce empty outputs (graceful degradation). The narrative synthesis phase aggregates whatever succeeded — a document with 14/17 successful phases still produces a useful report. In practice, the failure rate on golden fixtures is 0/17. On real corpus (18 docs, PR #460), the JVM OOM issue caused some late-phase failures (JTMS/ATMS), but earlier phases always succeeded.

### Q13: How extensible is the pipeline?

Adding a phase requires: (1) create an agent inheriting `BaseAgent`, (2) implement a `@kernel_function` method, (3) register in `CapabilityRegistry`, (4) add to `WorkflowDSL` with `add_phase(capability="my_phase", depends_on=["extraction"])`. No changes to orchestration logic. The 12 student projects were integrated this way — each became an operational agent with zero orchestration refactoring. See CLAUDE.md "Lego Architecture" section.

### Q14: Why 17 phases specifically?

The phases correspond to distinct analytical capabilities: extraction (2), quality (1), detection (2), formalization (3), argumentation frameworks (2), counter-argumentation (1), debate (1), truth maintenance (2), governance (1), synthesis (2). Each phase produces a typed output that feeds into subsequent phases. Fewer phases would merge unrelated concerns (e.g., combining Dung + ASPIC loses the distinction between abstract and structured argumentation). More phases would over-fragment without analytical benefit.

---

## Formal Logic

### Q15: What's the FOL formula bottleneck mentioned in limitations?

Tweety's FOL reasoner currently handles one formula at a time — the NL-to-FOL translation produces multiple candidate formulas, but the solver evaluates them individually rather than as a combined theory. PR #439 (#434) added per-formula retry with regex-based predicate extraction, but the fundamental limitation remains: FOL reasoning is O(2^n) in the number of predicates. For a typical document with 8 arguments, the signature has ~16 predicates, which is manageable. For longer documents, we truncate to the top-5 formulas by confidence. See `argumentation_analysis/agents/logic/fol_logic_agent.py`.

### Q16: How do Dung semantics work in your system?

The system builds an abstract argumentation framework (attack graph) from identified arguments and counter-arguments. It then computes three semantics: **Grounded** (skeptical, unique), **Preferred** (credulous, maximal), and **Stable** (no attacked arguments survive). On golden fixtures: grounded accepts 6/8 arguments, preferred 6-7/8. The "rejection" of arg_c1 in grounded semantics signals that this argument cannot be defended against all attacks — a strong indicator of fallacious reasoning. Implemented via Tweety's `DungTheory` + `SimpleArgumentationFramework`. See slide "Phase 8: Cadre de Dung".

### Q17: What's the difference between JTMS and ATMS?

**JTMS** (Justification-based TMS) maintains beliefs with justifications — when a belief is retracted, all dependent beliefs cascade. This models "if we reject premise X, what else must change?" On golden fixture: 2 cascades from 10 beliefs, 7.9% retraction rate on corpus. **ATMS** (Assumption-based TMS) explores multiple assumption contexts simultaneously — each context is a set of assumptions, and the ATMS identifies which contexts are contradictory. On golden fixture: 2/4 contexts contradictory, revealing internal tensions. JTMS is linear; ATMS is exponential in assumptions (>10 = combinatorial explosion).

---

## Performance

### Q18: What's the wall-clock breakdown?

Profiling (PR #422) on golden fixture (doc_A): **total 80s** (pre-parallelism) → ~50s (post-#438 parallelism). Breakdown: LLM phases = 68.3% (API call latency), formal reasoning = 15% (Tweety solver), orchestration overhead = 16.7%. The bottleneck is LLM API latency, not CPU. Peak memory: 66.8 MB. L1 parallelism (PR #438) targets the 3 independent formalization phases (PL/FOL/Modal) which previously ran sequentially for 34s → now ~11s.

### Q19: What's the scalability ceiling?

Single-document analysis: ~50s. Batch processing: JVM memory accumulates across documents (JPype doesn't free Java heap between docs), causing OOM after 1-3 documents. The iterative strategy is `--skip-existing` with relaunch (PR #460 batch run). For true scalability, the JVM would need per-document isolation (future work, issue #451 checkpoint/resume). Current ceiling: ~18 documents per batch session with manual relaunches.

### Q20: Why does the JVM cause OOM?

JPype loads the JVM once per process and shares it across all analyses. Tweety's reasoners create Java objects (formulas, argumentation frameworks, belief sets) that accumulate in the Java heap. The default heap size is ~512MB, and after processing 2-3 documents with 17 phases each, the heap fills up with unreferenced but not-yet-garbage-collected objects. `System.gc()` helps but doesn't fully solve it. The proper fix is per-document JVM restart (#451) or subprocess isolation.

---

## Detection & Analysis

### Q21: How does the hybrid fallacy detection work?

Two layers: **Neural** — the LLM identifies fallacy candidates with confidence scores (0-1) based on prompt engineering. **Hierarchical** — a rule-based taxonomy (`argumentation_analysis/agents/informal/taxonomy_sophism_detector.py`) classifies detected fallacies into 8 families (Relevance, Causal, Distortion, Presumption, Ambiguity, Diversion, Fallacious Structure, Emotional). The `FrenchFallacyPlugin` adds French-specific NLP patterns. The combination reduces false positives: a neural-only detector might flag rhetorical questions as fallacies, but the hierarchical layer filters them unless they match a known fallacy pattern.

### Q22: What 8 fallacy families do you detect?

1. **Pertinence** (Relevance) — ad hominem, red herring
2. **Causal** (Causation) — slippery slope, post hoc
3. **Distorsion** (Distortion) — straw man, false equivalence
4. **Presomption** (Presumption) — false dilemma, begging the question
5. **Ambiguite** (Ambiguity) — equivocation, amphiboly
6. **Diversion** (Diversion) — appeal to authority, ad populum
7. **Structure fallacieuse** (Fallacious Structure) — invalid enthymeme, circular reasoning
8. **Emotionnel** (Emotional) — appeal to fear, pity

On real corpus (18 docs, PR #460): 23 unique fallacy types detected. Most frequent: "Illusion de regroupement" at 21% of units.

### Q23: What did the corpus pattern mining reveal?

Three key findings (see slide "What We Discovered" and report `docs/reports/discourse_patterns.md`): (1) "Illusion de regroupement" is the most frequent fallacy (21%) and acts as a hub, co-occurring with 5 other types. (2) 6 fallacy pairs show perfect co-occurrence (lift=18.0), forming tight clusters like {Acte de foi, Coup de pouce, Misogynie}. (3) JTMS retraction signal has 100% cross-coverage with informal fallacy detection — every detected fallacy triggers a formal JTMS signal. FOL and Dung show 0% cross-coverage (formulas are valid, attacks are sparse).

---

## Dataset & Privacy

### Q24: What corpus do you analyze?

An encrypted dataset of politically sensitive texts (historical speeches, contemporary political discourse). 9 sources, 37 extracts, ~274K characters total. The dataset is AES-256 encrypted (`extract_sources.json.gz.enc`) with passphrase in `.env`. Access requires `TEXT_CONFIG_PASSPHRASE` environment variable. See `argumentation_analysis/core/io_manager.py:load_extract_definitions()` for the decryption pipeline.

### Q25: Why encrypt the dataset?

The corpus contains politically sensitive content (historical dictator speeches, contemporary heads of state, domestic political debates). Plaintext must never leave the machine via git. The encryption layer ensures: (1) the dataset can be versioned in the repository, (2) analysis artifacts use opaque IDs only, (3) downstream reports pass privacy review. Privacy verification script at `scripts/security/verify_encrypted_dataset_completeness.py`.

### Q26: What are opaque IDs?

Each source gets `sha256(source_name)[:8]` as an opaque identifier. Extracts get `{opaque_id}_ext{index}`. The public report references only these IDs (e.g., `0c45b55d_ext1`, `96d4752a_ext2`). The reverse mapping exists only in the encrypted dataset. This prevents GitHub indexing of source names. Implemented in `argumentation_analysis/evaluation/opaque_id.py`. A privacy scan checks for FORBIDDEN strings (`raw_text`, `full_text`, `source_name`, `"text":`, `author`) in all committed outputs.

---

## Testing & Quality

### Q27: What's your test strategy?

2845+ tests across unit/integration/e2e. Pytest with 41 markers (requires_api, slow, jpype, belief_set, etc.). Tests auto-skip when API keys are unavailable (no false failures). CI: GitHub Actions with Black + Flake8 linting and automated test runs on Windows/Conda. Property-based tests via Hypothesis for ATMS/JTMS (#420). Coverage audit: 7 modules >80%, with `conflict_resolution.py` at 93%, `governance_agent.py` at 96%, `quality_evaluator.py` at 78%.

### Q28: How do you test formal reasoning without a real JVM?

You can't — JPype/Tweety requires a real JVM. Tests marked `@pytest.mark.jpype` or `@pytest.mark.tweety` expect a running JVM. The `conftest.py` handles JVM initialization and the critical DLL load ordering (torch/transformers before jpype on Windows to avoid `WinError 182`). CI provides Java 11 via Temurin. For pure logic tests, we use mock formulas and test the translation layer (NL → logic syntax) independently.

### Q29: What's the mypy situation?

PR #423 added `mypy` to `environment.yml` and ran strict mode on `argumentation_analysis/core/orchestration/`. Current coverage: type-checked modules include `unified_pipeline.py`, `workflow_dsl.py`, `workflow_executor.py`. Full repo strict mode is not yet achieved — estimated ~200 type:ignore comments would be needed for the student project code that wasn't written with type hints.

---

## Limitations & Future Work

### Q30: What are the main limitations?

1. **FOL bottleneck**: One formula at a time in Tweety, no combined theory reasoning (#434/#439)
2. **French NLP**: Models are English-primary, French fallacy detection relies on rule-based supplements
3. **JVM memory**: Cumulative heap growth limits batch size to 1-3 docs per process (#451 for fix)
4. **ATMS explosion**: >10 assumptions = combinatorial explosion (inherent to ATMS, not fixable)
5. **LLM cost**: $0.05-0.15 per analysis, prohibitive for real-time use
6. **Corpus size**: 37 extracts, not statistically representative
7. **No temporal analysis**: Can't compare discourse patterns across time periods (future work)

### Q31: What didn't ship?

From the original roadmap (#78): Mobile UI (React Native), public API, multi-user collaboration, real-time debate. From Epic D: FOL signature pre-declaration is partial (#439 — collision risk remains, followup #459). From Epic F (in progress): Docker reproducibility package, Gradio demo app, demo video. The hierarchical orchestration mode (Strategic → Tactical → Operational delegation) is declared but dormant — only pipeline and conversational modes are active.

### Q32: What's the long-term vision?

"Democratech" — iterative discourse analysis at scale: (1) grow the corpus with diverse discourse types, (2) enrich patterns via LLM-assisted narrative, (3) build a public API for real-time argumentation analysis, (4) mobile UI for citizen use, (5) multi-user collaborative debate. The architecture (Lego/CapabilityRegistry) is designed for this extensibility. See issue #78 for the full roadmap.

---

## Pedagogical

### Q33: How did you integrate 12 student projects?

Each student project became an operational agent or plugin: (1) inherit `BaseAgent(ChatCompletionAgent)`, (2) expose logic via `@kernel_function`, (3) register in `CapabilityRegistry`. The integration was tracked in Epic #317 consolidation — 6 PRs (#321-#326) cleaned up root-level overflow. Some projects required significant refactoring (e.g., governance simulation was a standalone script, converted to a plugin). Others were straightforward (JTMS was already well-structured). See CLAUDE.md "Known Overflow" table for the cleanup history.

### Q34: What are the 5 pedagogical scenarios?

Original texts (not from encrypted corpus), each targeting specific analytical capabilities: (1) **Politique** — "Loi Logement Abordable" → extraction, sophismes, gouvernance, (2) **Scientifique** — "Changement climatique" → logique formelle, Dung, (3) **Media** — "Liberte d'expression" → qualite, taxonomie, (4) **Fact-check** — "Retraites 2027" → ATMS, JTMS, Modal, (5) **Philosophie** — "Tramway" → contre-args, debat, gouvernance. Scenarios are Pydantic-validated fixtures in `examples/scenarios/`.

### Q35: How would you demo this live?

Three options: (1) **Jupyter notebook** (`examples/notebooks/spectacular_full_tour.ipynb`) — 20-cell guided tour, (2) **HTML report** — `argumentation_analysis/visualization/html_report.py` generates a standalone report with 10 sections + D3 visualizations, (3) **CLI** — `python argumentation_analysis/run_orchestration.py --mode pipeline --workflow spectacular`. All produce the same output. Pre-recorded video fallback available if live demo fails (issue #455).
