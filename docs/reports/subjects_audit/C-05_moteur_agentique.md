# C-05: Audit Sujets — Section II-C Moteur Agentique et Agents Spécialistes

**Track**: C-05 #783 (Epic C #744)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
**Scope**: 7 sujets (moteur agentique + 6 agents spécialistes)

---

## Table préalable — Status des sujets

| Code | Sujet | Statut | Lien Epic A | Pipeline wiring |
|------|-------|--------|-------------|-----------------|
| 2.3.1 | Abstraction moteur agentique | À auditer | — | NONE (SK-only) |
| 2.3.2 | Détection sophismes et biais | 🟢 Traité | A-07 #753 | COMPLETE (3-tier hybrid) |
| 2.3.3 | Génération contre-arguments | 🟢 Traité | A-08 #754 | COMPLETE (5 stratégies + évaluateur) |
| 2.3.4 | Formalisation logique | À auditer | — | COMPLETE (PL+FOL+Modal + NL translator) |
| 2.3.5 | Évaluation qualité argumentative | 🟢 Traité | A-09 #755 | COMPLETE (9 vertus + LLM enrichment) |
| 2.3.6 | Intégration LLMs locaux légers | 🟢 Traité | A-10 #759 | PARTIAL (service existe, dormant) |
| 2.3.7 | Speech to Text fallacieux | 🟢 Traité | A-16 #777 | PARTIAL (router + state writer, invoke stub) |

**Bilan** : 5 traités (🟢), 2 à auditer (2.3.1, 2.3.4).

---

## Audit détaillé

### 🟢 2.3.2 Détection de sophismes et biais cognitifs

**Statut** : Intégré (SUIVI 90%, `2.3.2-detection-sophismes/`)
**Epic A** : A-07 #753 — 🟢 INTÉGRÉ fidèlement (PR #826)
**Pipeline wiring** : `InformalAnalysisAgent(BaseAgent)`, `FrenchFallacyAdapter` (3-tier hybrid), `TaxonomySophismDetector` (8 familles, 28 labels), capability `fallacy_detection`.

---

### 🟢 2.3.3 Génération de contre-arguments

**Statut** : Intégré (SUIVI 95%, `2.3.3-generation-contre-argument/`)
**Epic A** : A-08 #754 — 🟢 INTÉGRÉ fidèlement (PR #830)
**Pipeline wiring** : `CounterArgumentAgent(BaseAgent)`, 5 stratégies rhétoriques, évaluateur 5-critères, validation Tweety, plugin SK.

---

### 🟢 2.3.5 Évaluation de qualité argumentative

**Statut** : Intégré (SUIVI, `2.3.5_argument_quality/`)
**Epic A** : A-09 #755 — 🟢 INTÉGRÉ fidèlement (PR #832)
**Pipeline wiring** : 9 détecteurs de vertus, `QualityScoringPlugin` (3 `@kernel_function`), capability `argument_quality` + `virtue_detection` + `quality_scoring`, LLM enrichment.

---

### 🟢 2.3.6 Intégration LLMs locaux légers

**Statut** : Intégré partiel (SUIVI, `2.3.6_local_llm/`)
**Epic A** : A-10 #759 — 🟡 INTÉGRÉ partiellement (PR #833)
**Pipeline wiring** : `LocalLLMService` (OpenAI-compatible adapter), `local_llm_service` capability enregistrée. **Dormant** : pas de state writer ni de workflow phase. 2 fix-intents #834/#835 ouverts (R288).

---

### 🟢 2.3.7 Speech to Text et Analyse d'arguments fallacieux

**Statut** : Structurally integrated with dead invoke stub (SUIVI, `speech-to-text/`)
**Epic A** : A-16 #777 — 🟡 invoke stub mort (PR #849)
**Pipeline wiring** : Router FastAPI + state writer + 2 capabilities enregistrées + 2 consumers. **Invoke callable = stub mort** (`invoke_callables.py:2244-2251`) retourne `{status: ready}` sans appeler le service. 3 fix-intents (HIGH invoke, MEDIUM chaining, LOW Gradio).

---

### 2.3.1 Abstraction du moteur agentique

**Sujet** : Permettre utilisation de différents frameworks agentiques (Semantic Kernel, LangChain, AutoGen, CrewAI) via adaptateurs. Design pattern abstraction.
**Pipeline** : **AUCUN WIRING** :
- `BaseAgent(ChatCompletionAgent, ABC)` hérite directement de SK (`semantic_kernel.agents.chat_completion.ChatCompletionAgent`)
- `BaseLogicAgent(BaseAgent)` spécialise pour la logique formelle
- `AgentFactory` crée tous les agents via SK (`Kernel`, `ChatCompletionAgent`, `FunctionChoiceBehavior`)
- Aucun `framework_adapter`, aucun adapter LangChain/AutoGen/CrewAI
- Grep "langchain|autogen|crewai" : 0 hit dans le code source

Le système est **monolithiquement SK-bound**. Toute la couche agent (bases, factory, plugins, invoke callables) est couplée à Semantic Kernel.

**Valeur potentielle** : LOW — l'abstraction multi-frameworks est un cas d'usage **académique** (comparaison, portabilité). En pratique :
- Le système est productif sur SK avec 50+ invoke callables, 17+ agents, 30+ plugins
- Migrer vers un autre framework nécessiterait réécrire l'architecture entière
- LangChain/AutoGen n'apportent pas de capabilities manquantes ( SK a le tool-calling, AgentGroupChat, kernel functions)

**Classification** : ⚫ **Abandonné légitimement** — le système a fait un choix d'architecture (SK) et l'a exploité à fond. L'abstraction multi-frameworks serait une réécriture complète pour un gain pédagogique (comparaison) plutôt qu'un gain pipeline.

---

### 2.3.4 Agent de formalisation logique

**Sujet** : Traduction langue naturelle → logiques formelles (propositionnelle, FOL, modale), vérification de validité.
**Pipeline** : **COMPLÈTEMENT COUVERT** :
- **Agents logiques** : `PropositionalLogicAgent`, `FOLLogicAgent` (1216 LOC), `ModalLogicAgent` (921 LOC), `WatsonLogicAssistant`
- **NL→Formal translator** : `NLToLogicTranslator` (837 LOC) avec translate-validate-retry loop, LLM + Tweety validation + heuristic fallback
- **TweetyBridge** : pont JVM vers TweetyProject (parsing, validation, raisonnement)
- **PL/FOL/Modal belief sets** : `PropositionalBeliefSet`, `FirstOrderBeliefSet`, `ModalBeliefSet`
- **Logic factory** : `LogicAgentFactory` (création par type, extensible)
- **SK Plugins** : `NLToLogicPlugin` (4 `@kernel_function` : translate_to_pl/fol + batch), `LogicAgentPlugin` (8 `@kernel_function` : parse/execute/check PL/FOL/Modal + validate)
- **Capabilities enregistrées** : `propositional_logic_service`, `fol_reasoning_service`, `modal_logic_service`, `nl_to_logic_service`, `sat_handler`
- **Invoke callables** : `_invoke_propositional_logic`, `_invoke_fol_reasoning`, `_invoke_modal_logic`, `_invoke_nl_to_logic`, `_invoke_sat`, `_invoke_external_fol_solver` (EProver/Prover9), `_invoke_external_modal_solver` (SPASS)

Pipeline complet : texte NL → traduction LLM → validation Tweety (retry) → belief set → query → interprétation NL.

**Valeur potentielle** : NONE — la formalisation logique est l'une des couches les plus denses du système.
**Classification** : 🔵 **Doublon cross-section** — 2.3.4 est entièrement couvert par l'existant (probable "traité implicite" : la formalisation logique existait dans le tronc commun avant la formalisation des sujets étudiants).

---

## Récapitulatif

| Code | Sujet | Classification | Pipeline wiring | Valeur potentielle |
|------|-------|----------------|-----------------|-------------------|
| 2.3.2 | Détection sophismes | 🟢 Traité (A-07) | COMPLETE | — |
| 2.3.3 | Contre-arguments | 🟢 Traité (A-08) | COMPLETE | — |
| 2.3.5 | Évaluation qualité | 🟢 Traité (A-09) | COMPLETE | — |
| 2.3.6 | LLMs locaux | 🟢 Traité (A-10, partiel) | PARTIAL (dormant) | — |
| 2.3.7 | Speech to Text | 🟢 Traité (A-16, partiel) | PARTIAL (stub mort) | — |
| 2.3.1 | Abstraction moteur | ⚫ Abandonné | NONE (SK-only) | LOW |
| 2.3.4 | Formalisation logique | 🔵 Doublon | COMPLETE (PL+FOL+Modal+NL) | NONE |

### Décompte

| Classification | Count | Sujets |
|----------------|-------|--------|
| 🟢 Traité | 5 | 2.3.2, 2.3.3, 2.3.5, 2.3.6, 2.3.7 |
| 🔵 Doublon cross-section | 1 | 2.3.4 (formalisation logique) |
| ⚫ Abandonné | 1 | 2.3.1 (abstraction moteur) |
| 🟠 Angle mort utile | 0 | — |

**Bilan** : C-05 est le packet le plus saturé — 5/7 sujets déjà traités par Epic A, les 2 restants sont soit doublon (2.3.4 couvert par l'existant) soit abandon légitime (2.3.1 incompatible avec l'architecture SK-bound). **Aucun angle mort utile** identifié : aucune enhancement proposal.

---

## Issues enhancement proposées

Aucune. Les 5 sujets déjà traités par Epic A ont déjà leurs fix-intents R288 respectifs (ouverts par audits A-07→A-10, A-16). Les 2 sujets non-traités ne génèrent pas d'enhancement :
- 2.3.1 (abstraction multi-frameworks) : réécriture complète pour gain pédagogique = hors scope
- 2.3.4 (formalisation logique) : déjà intégralement couvert par le tronc commun

### À valider par l'utilisateur

- RAS — audit read-only. Aucune décision en suspens. C-05 confirme la saturation du volet "agents spécialistes" : 5/7 déjà traités, 2/2 non-traités sont soit doublon soit abandon.
