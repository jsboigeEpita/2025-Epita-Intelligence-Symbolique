Show the current integration status of all 12 student projects.

For each project, check:
1. Whether an analysis report exists in `docs/architecture/INTEGRATION_PLANS/`
2. Whether the target integration directory exists in `argumentation_analysis/`
3. Whether tests exist for the integrated component
4. Whether the component is registered in CapabilityRegistry

Display a summary table:

| # | Project | Analysis | Integrated | Tests | Registered | Status |
|---|---------|----------|-----------|-------|-----------|--------|

Projects to check:
1. 1.4.1-JTMS → services/jtms/
2. 1_2_7_argumentation_dialogique → agents/core/debate/
3. 2.1.6_multiagent_governance_prototype → agents/core/governance/
4. 2.3.2-detection-sophismes → adapters/camembert_fallacy.py
5. 2.3.3-generation-contre-argument → agents/core/counter_argument/
6. 2.3.5_argument_quality → agents/core/quality/
7. 2.3.6_local_llm → services/local_llm_service.py
8. 3.1.5_Interface_Mobile → (external, API only)
9. abs_arg_dung → adapters/dung_framework.py
10. Arg_Semantic_Index → services/semantic_index_service.py
11. CaseAI → (external, webhooks)
12. speech-to-text → services/speech_transcription.py

Also check GitHub issue #35 status using `gh issue view 35`.
