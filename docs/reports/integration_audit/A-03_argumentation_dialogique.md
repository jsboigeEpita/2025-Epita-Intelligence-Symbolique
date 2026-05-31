# Audit A-03: 1.2.7 Argumentation Dialogique

**Issue**: #42 (CLOSED) | **SUIVI**: Score 90% (intégré) | **Date audit**: 2026-06-01
**Ré-audit R290**: DoD enrichi intent-fix (Epic A #742, Track A-03 #747)
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique

## Status: 🟢 Integrated — Pas de gap pipeline

Le projet étudiant `1_2_7_argumentation_dialogique` est **entièrement intégré** dans `argumentation_analysis/agents/core/debate/`. Les deux sous-projets (GPT-based debate + Walton-Krabbe protocols) ont été fusionnés et adaptés au système Lego.

## What exists in `1_2_7_argumentation_dialogique/`

### Structure du projet étudiant

| Répertoire/Fichier | Lignes | Contenu |
|---|---|---|
| `enhanced_argumentation_main.py` | ~1497 | Système de débat GPT avec 8 personnalités, 8 métriques, analyse de cohérence |
| `local_db_arg/` | — | Sous-projet Walton-Krabbe (protocoles, KB, agents) |
| `local_db_arg/main.py` | ~221 | CLI multi-mode (demo, rich-demo, config) |
| `local_db_arg/src/agents/dialogue_agent.py` | ~400 | Agent de dialogue avec commitment store |
| `local_db_arg/src/agents/multi_agent_system.py` | ~150 | Orchestrateur multi-agent |
| `local_db_arg/src/core/argumentation_engine.py` | ~200 | Moteur avec 5 schémas d'argumentation |
| `local_db_arg/src/core/knowledge_base.py` | ~70 | Base de connaissances propositionnelle |
| `local_db_arg/src/core/models.py` | ~87 | Data models (DialogueType, SpeechAct, Proposition, Argument, DialogueMove) |
| `local_db_arg/src/protocols/base_protocol.py` | ~33 | Protocole abstrait (transitions, terminaison) |
| `local_db_arg/src/protocols/inquiry_protocol.py` | ~80 | Protocole d'enquête |
| `local_db_arg/src/protocols/persuasion_protocol.py` | ~55 | Protocole de persuasion |
| `local_db_arg/src/interfaces/cli.py` | ~250 | Interface CLI interactive |
| `local_db_arg/src/interfaces/config.py` | ~70 | Chargement config YAML |
| `local_db_arg/config/rich_agents_demo.yaml` | ~340 | Config enrichie (agents climat, économie, politique) |
| `local_db_arg/tests/` | 3 fichiers | Tests stubs (placeholders vides) |
| `first_try/argumentation_main.py` | ~400 | Première version (itération initiale) |
| `baudelaire_debate.json` | ~1200 | Transcript de débat Baudelaire (données de test) |
| `slides/` | 6 images + HTML/CSS/JS | Présentation (diagrammes d'architecture, performances) |
| `Sujet.md` | ~1200 | Sujet détaillé avec fondements théoriques Walton-Krabbe |

## What exists in `argumentation_analysis/`

| Layer | File | Detail |
|---|---|---|
| Agent | `agents/core/debate/debate_agent.py` | `DebateAgent(BaseAgent)` — agent SK avec stratégies adaptatives, analyse d'adversaires, scoring 8 métriques. `EnhancedDebateModerator` (utilitaire, pas BaseAgent). |
| Plugin | `agents/core/debate/debate_agent.py` | `DebatePlugin` — expose les fonctions de débat via `@kernel_function` |
| Definitions | `agents/core/debate/debate_definitions.py` | `ArgumentType`, `DebatePhase`, `ArgumentMetrics`, `EnhancedArgument`, `DebateState`, `AGENT_PERSONALITIES` |
| Scoring | `agents/core/debate/debate_scoring.py` | `ArgumentAnalyzer` — 8 métriques (cohérence logique, qualité preuves, pertinence, appel émotionnel, lisibilité, fact-check, nouveauté, persuasivité) |
| Protocols | `agents/core/debate/protocols.py` | `DialogueType` (6 types Walton-Krabbe), `SpeechAct` (9 types), `DialogueProtocol` (ABC), `InquiryProtocol`, `PersuasionProtocol` |
| Knowledge base | `agents/core/debate/knowledge_base.py` | `KnowledgeBase` — base propositionnelle avec vérification consistance |
| Capability Registry | `orchestration/registry_setup.py:130-147` | `debate_agent` → capabilities `adversarial_debate` + `debate_scoring` |
| Invoke callable | `orchestration/invoke_callables.py` | `_invoke_debate_analysis` |
| State writer | `orchestration/state_writers.py` | Writer pour les résultats de débat |
| Workflow | `workflows/formal_debate.py` | `build_formal_debate_workflow` |
| Workflow | `orchestration/workflows.py:449` | `build_debate_governance_loop_workflow` (Loop 1) |
| Workflow | `workflows/debate_tournament.py` | `build_debate_tournament_workflow` |
| Collaborative | `orchestration/collaborative_debate.py` | `collaborative_debate_service` — débat multi-agent collaboratif avec 4 rôles |
| API route | `api/` | Routes REST pour débat |

**Tests**: 198 tests dans `tests/unit/argumentation_analysis/agents/core/debate/` (4 fichiers). Plus tests workflow et intégration.

## Preservation Assessment

### Enhanced Debate System (from `enhanced_argumentation_main.py`)

- ArgumentType / DebatePhase: ✅ → `debate_definitions.py`
- ArgumentMetrics (8 métriques): ✅ → `debate_scoring.py`
- EnhancedArgument: ✅ → `debate_definitions.py`
- EnhancedArgumentationAgent: ✅ → `DebateAgent(BaseAgent)` avec même logique adaptative
- EnhancedDebateModerator: ✅ → préservé comme utilitaire (pas BaseAgent)
- EnhancedArgumentationSystem: ✅ → remplacé par CapabilityRegistry + workflows
- VisualizationEngine: ✅ → conservé dans debate_agent (network + charts)
- 8 personnalités: ✅ → `AGENT_PERSONALITIES` dict dans `debate_definitions.py`
- GPT calls: ✅ → migré vers SK kernel (pas de raw OpenAI client)

### Walton-Krabbe Protocols (from `local_db_arg/`)

- DialogueType (6 types): ✅ → `protocols.py`
- SpeechAct (9 types): ✅ → `protocols.py`
- DialogueProtocol (ABC): ✅ → `protocols.py`
- InquiryProtocol: ✅ → `protocols.py`
- PersuasionProtocol: ✅ → `protocols.py`
- KnowledgeBase: ✅ → `knowledge_base.py`
- ArgumentationEngine (5 schémas): ✅ → intégré dans `debate_scoring.py`
- Proposition / Argument / DialogueMove: ✅ → `protocols.py` et `debate_definitions.py`
- DialogueAgent: ✅ → fusionné dans `DebateAgent`
- MultiAgentDialogueSystem: ✅ → remplacé par CapabilityRegistry orchestration
- CLI interface: ❌ Non intégrée (normal — le projet a sa propre CLI)
- Config YAML: ❌ Non intégrée (normal — le CapabilityRegistry gère la config)

### Ce qui n'a PAS été intégré (normal)

| Élément | Pourquoi |
|---------|----------|
| `local_db_arg/interfaces/cli.py` | CLI remplacée par `api/` routes + orchestration CLI |
| `local_db_arg/src/interfaces/config.py` | Config YAML remplacée par CapabilityRegistry |
| `local_db_arg/config/*.yaml` | Config remplacée par système de configuration unifié |
| `local_db_arg/tests/*.py` | Tests stubs vides (3 fichiers, 0 tests réels) |
| `first_try/argumentation_main.py` | Version initiale, supplantée par `enhanced_argumentation_main.py` |
| `baudelaire_debate.json` | Données de test étudiant (transcript de débat) |
| `slides/` | Présentation HTML/CSS/JS du projet |
| `Sujet.md` | Documentation pédagogique |

## Gap Analysis

**No gap.** L'intégration couvre :

1. **Agent**: `DebateAgent(BaseAgent)` avec SK kernel wiring
2. **Plugin**: `DebatePlugin` expose les fonctions via `@kernel_function`
3. **Protocoles**: Walton-Krabbe (inquiry, persuasion, + 4 autres) avec transitions formelles
4. **Scoring**: 8 métriques d'analyse d'argument (même logique que l'étudiant)
5. **CapabilityRegistry**: `debate_agent` enregistré avec `adversarial_debate` + `debate_scoring`
6. **Workflows**: 3 workflows (formal_debate, debate_governance_loop, debate_tournament) + collaborative debate
7. **Tests**: 198 tests (4 fichiers) couvrant agent, scoring, protocols, definitions
8. **API**: Routes REST pour l'interaction débat

Note : 4 des 6 types de dialogue sont enum-only (information_seeking, negotiation, deliberation, eristic) — ceci correspond au scope étudiant original qui n'implémentait que Inquiry et Persuasion.

Le projet **dépasse** le scope étudiant original : migration OpenAI → SK kernel, intégration CapabilityRegistry, workflows déclaratifs, collaborative debate, tournament.

## Fix-intents

**Aucun fix-intent ouvert.** L'intégration est complète, wirée, testée, et documentée.

## Recommended Action

**No work needed.** Issue #42 est correctement fermée. Le SUIVI est exact :
- Score: 90% ✅
- Integration: `DebateAgent(BaseAgent)` avec protocoles Walton-Krabbe ✅
- Issue: #42 → CLOSED ✅

Les 10% restants correspondent aux éléments non-intégrés par design (CLI étudiante, config YAML, slides, données de test).

## Source Files

- `argumentation_analysis/agents/core/debate/debate_agent.py`
- `argumentation_analysis/agents/core/debate/debate_definitions.py`
- `argumentation_analysis/agents/core/debate/debate_scoring.py`
- `argumentation_analysis/agents/core/debate/protocols.py`
- `argumentation_analysis/agents/core/debate/knowledge_base.py`
- `argumentation_analysis/workflows/formal_debate.py`

---

*Ré-audit R290 — Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track A-03 #747 — Epic A #742*
