# Archeologie de l'Orchestration — Rapport Issue #209

> Date : 23 mars 2026 | Auteur : Claude Code | Epic #208

## Resume executif

L'analyse de 80+ commits sur `argumentation_analysis/orchestration/` revele que le systeme a traverse 3 architectures distinctes, et que l'infrastructure pour les 2 premieres (conversationnelle et hierarchique) **existe toujours dans le code** mais n'est pas cablee.

---

## 1. Trois architectures, une seule active

| Architecture | Periode | Status actuel | Fichier cle |
|-------------|---------|---------------|-------------|
| **Conversationnelle** (AgentGroupChat) | Juin 2025 - Mars 2026 | DORMANTE | `analysis_runner_v2.py`, `GroupChatTurnStrategy` |
| **Hierarchique** (Strategic→Tactical→Operational) | Mars 2026 | DORMANTE | `hierarchy_bridge.py`, `HierarchicalTurnStrategy` |
| **Pipeline sequentiel** (WorkflowDSL) | Mars 2026 - present | ACTIVE | `unified_pipeline.py`, `WorkflowTurnStrategy` |

---

## 2. Le systeme Sherlock-Watson (SEPARE)

Le systeme d'investigation Sherlock-Watson est une **architecture multi-agents complete et independante** :

### Agents et plugins specifiques

| Agent | Plugin | @kernel_function | Role |
|-------|--------|-----------------|------|
| SherlockEnqueteAgent | SherlockTools | 4 (case, hypothesis, solution, deduction) | Detective, investigation lead |
| WatsonLogicAssistant | WatsonTools | 4 (validate, query, step_by_step, inherited PL) | Logicien, validation formelle |
| MoriartyInterrogatorAgent | MoriartyTools + OracleTools | 4+7 | Oracle, gardien de donnees |

### Orchestration propre
- `CluedoOrchestrator` : 2 agents (Sherlock + Watson)
- `CluedoExtendedOrchestrator` : 3 agents (+ Moriarty Oracle)
- `CyclicSelectionStrategy` : tour de table Sherlock→Watson→Moriarty
- `OracleTerminationStrategy` : convergence sur solution (validation par oracle)

### Etat propre
- `EnqueteCluedoState` / `CluedoOracleState` (PAS `UnifiedAnalysisState`)
- `EnqueteStateManagerPlugin` : @kernel_function pour lire/ecrire l'etat d'enquete
- Plugin specifique au jeu, pas partage avec l'analyse rhetorique

### Pattern cle a retenir
Les agents Sherlock-Watson montrent le **pattern ideal** d'orchestration conversationnelle :
- Chaque agent a SES plugins specifiques (pas tout sur tout)
- Le StateManagerPlugin est le medium de communication
- Le `CyclicSelectionStrategy` gere le tour de parole
- Le `OracleTerminationStrategy` detecte la convergence
- `FunctionChoiceBehavior.Auto()` permet aux agents d'invoquer leurs outils

---

## 3. Associations agent<->plugins originelles

### Systeme d'investigation (Cluedo)
```
SherlockEnqueteAgent
  + SherlockTools (case_description, hypothesis, solution, deduction)
  + EnqueteStateManagerPlugin (lecture etat enquete)

WatsonLogicAssistant
  + WatsonTools (validate_formula, execute_query, step_by_step)
  + TweetyBridge (heritage de PropositionalLogicAgent)

MoriartyInterrogatorAgent
  + MoriartyTools (validate_suggestion, reveal_card, provide_clue, simulate_player)
  + OracleTools (permission, authorized_query, available_types, controlled_reveal)
```

### Systeme d'analyse rhetorique (original, pre-pipeline)
```
ProjectManagerAgent
  + StateManagerPlugin (add_task, get_state_snapshot, designate_next_agent)
  + project_management_plugin (PM-specific tools)

InformalAnalysisAgent
  + InformalAnalysisPlugin (analyse_sophismes, list_fallacy_families)
  + StateManagerPlugin (add_identified_fallacies)

PropositionalLogicAgent
  + PropositionalLogicPlugin (create_belief_set, execute_query, check_consistency)
  + StateManagerPlugin (add_belief_set, log_query)

ExtractAgent
  + ExtractPlugin (extract_arguments, extract_claims)
  + StateManagerPlugin (add_identified_argument)
```

### Associations post-integration (#35, non cablee dans GroupChat)
```
DebateAgent
  + DebatePlugin (analyze_quality, analyze_structure, suggest_strategy)

CounterArgumentAgent
  + CounterArgumentPlugin (parse_argument, identify_vulnerabilities, suggest_strategy)

QualityAgent (via QualityScoringPlugin)
  + QualityScoringPlugin (evaluate_quality, get_score, list_virtues)

GovernanceAgent (via GovernancePlugin)
  + GovernancePlugin (detect_conflicts, resolve_conflict, consensus_metrics, social_choice_vote, condorcet_winner)
```

---

## 4. Flux d'alimentation de KB (patterns retrouves)

### Pattern 1 : Extraction → State (original)
```
PM ordonne "identifier les arguments"
  → ExtractAgent invoke extract_arguments(@kernel_function)
  → ExtractAgent appelle StateManager.add_identified_argument(description)
  → State enrichi : identified_arguments["arg_1"] = "La regulation est necessaire..."
```

### Pattern 2 : Detection sophismes → State (original)
```
PM ordonne "detecter les sophismes"
  → InformalAgent invoke analyse_sophismes(@kernel_function)
  → InformalAgent appelle StateManager.add_identified_fallacies([{type, justification, target_arg_id}])
  → State enrichi : identified_fallacies["f_1"] = {type: "ad_hominem", target: "arg_3"}
```

### Pattern 3 : Formalisation → Requete → Interpretation (original)
```
PM ordonne "formaliser en logique propositionnelle"
  → PropositionalLogicAgent invoke text_to_belief_set()
    → TweetyBridge.parse_pl(formulas)
    → StateManager.add_belief_set(logic_type="pl", content={formulas, model})
  → PM ordonne "verifier la consistance"
  → PropositionalLogicAgent invoke execute_query()
    → TweetyBridge.query_pl(belief_set_id, query)
    → StateManager.log_query(belief_set_id, query, result)
  → PropositionalLogicAgent invoke interpret_results()
    → LLM genere interpretation en langage naturel
```

### Pattern 4 : Tour de table avec designation (original)
```
PM lit l'etat via StateManager.get_current_state_snapshot()
PM decide qui parler via StateManager.designate_next_agent("InformalAgent")
InformalAgent est selectionne par CyclicSelectionStrategy.next()
InformalAgent parle, enrichit l'etat
PM reprend la main, lit le nouvel etat, decide de la suite
```

### Pattern 5 : Enrichissement croise JTMS (concu mais pas cable)
```
Fallacies detectees → JTMS undermines les croyances basees sur des sophismes
Quality scores → JTMS pondere la force des justifications
Counter-arguments → JTMS ajoute des defeating conditions
Debat → JTMS met a jour les croyances selon le resultat
```
Ce pattern est documente dans `jtms_communication_hub.py` (54 KB) et `jtms_agent_base.py` (25 KB) mais n'est pas cable dans le pipeline actuel.

---

## 5. System prompts du PM orchestrateur

### Original (pre-pipeline)
Le PM avait un system prompt de 38 lignes en francais lui demandant de :
- Lire l'etat partage a chaque tour
- Decider quel agent interroger ensuite
- Formuler des questions precises pour chaque specialiste
- Synthetiser les resultats quand tous les aspects sont couverts
- Utiliser `designate_next_agent()` pour controler le tour de parole

### Actuel (pipeline sequentiel)
Le PM n'existe plus en tant qu'orchestrateur actif. Les phases sont ordonnees par le WorkflowDSL, pas par un agent.

---

## 6. FunctionChoiceBehavior — timeline

| Commit | Action | Impact |
|--------|--------|--------|
| `0ed1ea80` (WO-05) | Introduit `FunctionChoiceBehavior.Auto(max_attempts=5)` | Agents invoquent automatiquement les plugins |
| `5b717ee7` | Enhanced PM runner l'utilise (lignes 170-175) | Pattern fonctionnel |
| `d2fef7b4` | Runners "obsoletes" supprimes | Pattern perdu dans la migration |
| `7be4f5fc` (#35) | Pipeline sequentiel prend le relais | Plus besoin de FunctionChoiceBehavior |
| Present | Import dans factory.py mais JAMAIS cable | Agents muets (texte only, pas de tool_calls) |

---

## 7. Infrastructure JTMS oubliee

Deux fichiers massifs dans `agents/` n'ont jamais ete cables dans le pipeline :

### `jtms_agent_base.py` (25 KB)
- `ExtendedBelief` : wraps JTMS Belief avec metadata (agent_source, confidence, timestamps)
- `JTMSAgentMixin` : mixin pour ajouter JTMS a n'importe quel agent
- Permet a un agent de maintenir ses propres croyances avec justifications tracees

### `jtms_communication_hub.py` (54 KB)
- Hub central de messagerie pour coordonner l'etat JTMS entre agents
- Broadcasting de croyances, detection de contradictions, propagation de justifications
- Concu pour le multi-agent mais jamais active

---

## 8. Recommandations pour la restauration

### Ce qu'il faut reprendre du systeme originel
1. **Pattern agent↔plugins specifiques** : chaque agent a SES outils, pas tous les outils
2. **StateManagerPlugin comme medium** : les agents lisent et ecrivent via @kernel_function
3. **FunctionChoiceBehavior.Auto()** : les agents invoquent les outils automatiquement
4. **PM comme orchestrateur actif** : il lit l'etat, decide qui parler, et dirige l'analyse
5. **CyclicSelectionStrategy** : gestion du tour de parole (adaptable au-dela de Cluedo)

### Ce qu'il faut ajouter par rapport a l'originel
1. **Convergence detection** : le ConversationalPipeline le supporte deja (config.convergence_fn)
2. **Integration des 12 projets etudiants** : Debate, Counter, Quality, Governance, FOL, Modal, etc.
3. **JTMS comme tissu connectif** : croyances enrichies par les contributions de chaque agent
4. **NL→logic comme bridge** : permet aux agents formels de recevoir des formules, pas du texte brut

### Ce qu'il ne faut PAS faire
1. Donner tous les plugins a tous les agents (surcharge cognitive, actions incoherentes)
2. Supprimer le pipeline sequentiel (il reste utile pour les benchmarks rapides)
3. Fusionner Sherlock-Watson avec l'analyse rhetorique (architectures differentes, objectifs differents)

---

## 9. Fichiers cles par role

### Orchestration conversationnelle (a reactiver)
- `orchestration/conversational_executor.py` — ConversationalPipeline + GroupChatTurnStrategy
- `orchestration/turn_protocol.py` — TurnResult, ConversationConfig
- `orchestration/hierarchical/hierarchy_bridge.py` — HierarchicalTurnStrategy

### Reference (patterns a reproduire)
- `orchestration/analysis_runner_v2.py` — AgentGroupChat + FunctionChoiceBehavior
- `orchestration/cluedo_extended_orchestrator.py` — CyclicSelectionStrategy + OracleTerminationStrategy
- `orchestration/plugins/enquete_state_manager_plugin.py` — plugins d'etat par domaine

### Infrastructure JTMS (a cabler)
- `agents/jtms_agent_base.py` — ExtendedBelief + JTMSAgentMixin
- `agents/jtms_communication_hub.py` — hub de messagerie inter-agents

### Code mort (a archiver)
- `agents/agents.py`, `agents/base_agent.py`, `agents/agent_factory.py` — legacy
- `agents/core/orchestration_service.py` — service registry obsolete
- `orchestration/real_llm_orchestrator.py` — deprecated
- `services/web_api/` — ancienne API Flask

---

## 10. Commits cles pour reference

| Commit | Date | Evenement |
|--------|------|-----------|
| `0ed1ea80` | 29/06/2025 | WO-05 : AgentGroupChat + FunctionChoiceBehavior.Auto() |
| `d2fef7b4` | 12/07/2025 | Suppression runners "obsoletes" |
| `7be4f5fc` | 27/02/2026 | Lego Foundation : CapabilityRegistry + WorkflowDSL |
| `f5b87e7a` | 03/03/2026 | Invocation reelle + State Writers |
| `33fc7c80` | 04/03/2026 | ConversationalPipeline + 3 TurnStrategies |
| `b8d77104` | 04/03/2026 | Hierarchical Bridge |
| `6e89de40` | 22/03/2026 | Cross-component enrichment (Epic #176) |
| `9806c96b` | 22/03/2026 | NL-to-logic + QBF + AI Shield + CamemBERT + chunking |
