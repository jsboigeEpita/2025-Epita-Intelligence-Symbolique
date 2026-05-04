# Archived: 2026-03-24 - Removed from agents.py and factory.py (#216)
# Reason: 3 broken agent archetypes — never called from production code,
#   explicitly marked "Known broken" in test_agent_family.py (line 62)
# Original patterns:
#   - MethodicalAuditorAgent: 2-step (guiding plugin → filtered parallel)
#   - ParallelExplorerAgent: exhaustive taxonomy exploration
#   - ResearchAssistantAgent: unimplemented placeholder
# Superseded by: FrenchFallacyPlugin (3-tier: regex → CamemBERT → LLM)
# Also removed from: AgentType enum, factory.py agent_map

# --- MethodicalAuditorAgent (85 lines) ---
# Two-step analysis:
#   1. GuidingPlugin suggests relevant fallacy categories
#   2. ParallelWorkflowManager explores only suggested categories
# Dependencies: ParallelWorkflowManager, TaxonomyLoader, GuidingPlugin

# --- ParallelExplorerAgent (41 lines) ---
# Explores all taxonomy branches in parallel via ParallelWorkflowManager
# Dependencies: ParallelWorkflowManager, TaxonomyLoader

# --- ResearchAssistantAgent (25 lines) ---
# Placeholder for interactive planner-based analysis
# Never implemented — returns stub response
