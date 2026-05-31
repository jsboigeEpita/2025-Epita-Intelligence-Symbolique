# Audit C-05: Section II-C Moteur Agentique et Agents Spécialistes (7 sujets)

**Issue**: #783 (C-05) | **Epic**: #744 | **Date audit**: 2026-05-31

## Préambule — Table de correspondance

| Code sujet | Statut | Lien Epic A si traité |
|------------|--------|-----------------------|
| 2.3.1 Abstraction moteur agentique | 🟡 Code exists, no subject doc | — |
| 2.3.2 Détection sophismes | 🟢 Treated | #753 (A-07) |
| 2.3.3 Contre-arguments | 🟢 Treated | #754 (A-08) |
| 2.3.4 Formalisation logique | 🟡 Code exists, no subject doc | — |
| 2.3.5 Évaluation qualité | 🟢 Treated | #755 (A-09) |
| 2.3.6 LLMs locaux | 🟢 Treated | #759 (A-10) |
| 2.3.7 [Custom] Speech to Text | 🟢 Treated | #777 (A-16) |

## Résultats détaillés

### 🟢 TREATED (5)

**2.3.2 Détection sophismes** — Student project (arthur.hamard, score 90%). Code: `InformalAnalysisAgent(BaseAgent)`, `TaxonomySophismDetector` (8 families, 28 labels), `FrenchFallacyAdapter` (3-tier), `plugins/french_fallacy_plugin.py`. Cross-ref → Epic A #753 (A-07).

**2.3.3 Contre-arguments** — Student project (leo.sambrook, score 95%). Code: `CounterArgumentAgent(BaseAgent)`, 5 rhetorical strategies, 5-criteria evaluator. Cross-ref → Epic A #754 (A-08).

**2.3.5 Évaluation qualité** — Student project (4 students, score 90%). Code: `ArgumentQualityEvaluator` (9 virtues), `plugins/quality_scoring_plugin.py` (3 SK functions). Cross-ref → Epic A #755 (A-09).

**2.3.6 LLMs locaux** — Student project (5 students, score 80%). Code: `services/local_llm_service.py` (multi-backend vLLM/Ollama/llama-cpp). Cross-ref → Epic A #759 (A-10).

**2.3.7 [Custom] Speech to Text** — Student project (4 students, score 75%). Code: `services/speech_transcription_service.py` (2-tier: Whisper API + Gradio). Cross-ref → Epic A #777 (A-16). Note: filed as "[Custom]", not "2.3.7" in SUIVI.

### 🟡 CODE EXISTS, NO SUBJECT DOC (2)

**2.3.1 Abstraction du moteur agentique** — Professor's trunk infrastructure, never a student subject. Extensive code:
- `agents/core/abc/agent_bases.py` (668 LOC) — `BaseAgent(ChatCompletionAgent)` + `BaseLogicAgent`
- `agents/factory.py` (492 LOC) — `AgentFactory` with `AGENT_SPECIALITY_MAP`
- `core/capability_registry.py` (586 LOC) — `CapabilityRegistry` + `ServiceDiscovery`
- `orchestration/registry_setup.py`, `workflow_dsl.py` — auto-registration + declarative DAG
- **Assessment**: HIGH value, very mature (~1750 LOC core). The angle mort is purely documentary — the architecture everything depends on has never been written up as a subject. An Epic A issue here would be a documentation/architecture-spec task.

**2.3.4 Formalisation logique (NL→logique formelle)** — Professor's trunk infrastructure. Substantial code:
- `services/nl_to_logic.py` (836 LOC) — `NLToLogicTranslator`: LLM translation + Tweety validation + retry loop
- `plugins/nl_to_logic_plugin.py` — `NLToLogicPlugin` (SK functions `translate_to_pl`, FOL)
- `agents/core/logic/` — full stack: `fol_logic_agent.py` (1215 LOC), `propositional_logic_agent.py` (993), `modal_logic_agent.py` (920), `logic_factory.py`, `tweety_bridge.py`
- **Assessment**: HIGH value, the most code-heavy (~4000+ LOC). The angle mort is again documentary. Cross-refs: issues #173, #285.

## Synthèse C-05

- **5/7 🟢 Treated** (student projects with documentation)
- **2/7 🟡 Code exists, no subject doc** — professor trunk infrastructure never scoped as student subjects
- **0/7 🔴 Angle mort** — no technical gaps

**Recommendation**: The 2 angles morts (2.3.1, 2.3.4) are documentation gaps, not code gaps. Suggest two new Epic A documentation issues.

## Fichiers sources
- `argumentation_analysis/agents/core/abc/agent_bases.py`, `agents/factory.py`, `core/capability_registry.py`
- `argumentation_analysis/services/nl_to_logic.py`, `plugins/nl_to_logic_plugin.py`
- `argumentation_analysis/agents/core/logic/logic_factory.py`
