# Integration Plan: Argumentation Dialogique (1.2.7)

## 1. Sujet (resume spec professeur)

**Objectif pedagogique** : Implementer un systeme d'argumentation dialogique multi-agents base sur la theorie de Walton-Krabbe, ou des agents debattent selon des protocoles formels.

**Fonctionnalites demandees** :
- **6 types de dialogue** : information_seeking, inquiry, persuasion, negotiation, deliberation, eristic
- **6+ actes de langage** (speech acts) : CLAIM, QUESTION, CHALLENGE, ARGUE, CONCEDE, RETRACT (+ SUPPORT, REFUTE, UNDERSTAND)
- **Protocoles formels** avec regles de transition (FSM), conditions de terminaison, validation de coups
- **Base de connaissances** par agent : propositions, arguments, verification de consistance
- **Schemas d'argumentation** : modus ponens, opinion d'expert, analogie, cause-effet, etc.
- **Integration TweetyProject** via jpype pour la validation formelle (argumentation de Dung)
- **Metriques d'evaluation** : coherence logique, qualite des preuves, pertinence, persuasion

**Contraintes techniques** : Python + JPype/TweetyProject, protocoles formels Walton-Krabbe

**Etudiants** : aurelien.daudin, khaled.mili, maxim.bocquillion

## 2. Travail Etudiant (analyse code)

### 2.1 Deux implementations distinctes

Le projet contient **deux implementations complementaires** dans le dossier `1_2_7_argumentation_dialogique/` :

#### A. Implementation structuree (`local_db_arg/src/`, ~800 LoC)

Code bien organise en modules :
- `core/models.py` : Enums Walton-Krabbe (DialogueType, SpeechAct), dataclasses (Proposition, Argument, DialogueMove)
- `core/knowledge_base.py` : KnowledgeBase avec propositions, arguments, regles
- `core/argumentation_engine.py` : **10 schemas d'argumentation** (modus_ponens, expert_opinion, analogy, cause_effect, consensus, empirical_evidence, economic_argument, precautionary_principle, moral_argument, historical_precedent), generation/evaluation/contre-arguments
- `protocols/base_protocol.py` : DialogueProtocol(ABC) avec `is_valid_move()`, `is_terminal_state()`, `get_allowed_responses()`
- `protocols/persuasion_protocol.py` : PersuasionProtocol avec table de transitions complete (FSM) et 3 conditions de terminaison
- `agents/dialogue_agent.py` : DialogueAgent avec strategies collaborative/skeptical, detection de boucle, commitment store

**Qualite** : Bonne structure, separation des responsabilites. Manque d'integration LLM (tout est rule-based). Pas de SK, pas de BaseAgent.

#### B. Monolithe enhanced (`enhanced_argumentation_main.py`, ~1500 LoC)

Application complete en un seul fichier :
- `EnhancedArgumentationAgent` : Agent de debat LLM-powered avec strategies adaptatives
- `EnhancedDebateModerator` : Orchestrateur phase-based (opening → main → rebuttals → closing)
- 8 archetypes de personnalite (Scholar, Pragmatist, Devil's Advocate, Idealist, Skeptic, Populist, Economist, Philosopher)
- `ArgumentAnalyzer` : Scoring 8 metriques (coherence logique, qualite preuves, pertinence, appel emotionnel, lisibilite, fact-check, nouveaute, persuasion)
- Simulation d'audience, graphes networkx, visualisation matplotlib

**Qualite** : Riche en fonctionnalites, mais monolithique. Utilise `OpenAI` SDK directement (gpt-3.5-turbo hardcode). Depend de matplotlib, networkx, textstat (deps lourdes).

### 2.2 Points forts a conserver

| Source | Fonctionnalite | Valeur |
|--------|---------------|--------|
| Structuree | 10 schemas d'argumentation | **Haute** — algorithmique formelle absente ailleurs |
| Structuree | Protocoles Walton-Krabbe (FSM) | **Haute** — formalisme propre |
| Structuree | DialogueAgent strategies (collab/skeptical) | **Moyenne** — logique de reponse rule-based |
| Structuree | KnowledgeBase avec consistance | **Moyenne** — utile pour les protocoles |
| Monolithe | 8 personnalites configurables | **Haute** — enrichit le debat |
| Monolithe | ArgumentAnalyzer (8 metriques) | **Haute** — scoring multi-dimensionnel |
| Monolithe | EnhancedDebateModerator (phases) | **Haute** — orchestration complete |
| Monolithe | Strategies adaptatives (opponent analysis) | **Moyenne** — interessant mais complexe |

### 2.3 A ne PAS conserver

- `OpenAI` client hardcode → remplacer par `kernel.invoke()`
- matplotlib/networkx/textstat deps → optionnelles ou supprimees
- CLI interactive, logging console brut
- Visualisations graphiques (hors scope)

## 3. Etat Actuel dans le Tronc Commun

### 3.1 Fichiers existants dans `argumentation_analysis/agents/core/debate/`

| Fichier | Contenu | Source | Conforme BaseAgent? |
|---------|---------|--------|-------------------|
| `debate_definitions.py` | ArgumentType, DebatePhase, ArgumentMetrics, EnhancedArgument, DebateState, 8 personnalites | Monolithe | N/A (data) |
| `debate_agent.py` | `EnhancedArgumentationAgent` + `EnhancedDebateModerator` | Monolithe | **NON** — classe standalone |
| `debate_scoring.py` | `ArgumentAnalyzer` (8 metriques) | Monolithe | N/A (utilitaire) |
| `protocols.py` | DialogueType, SpeechAct, Proposition, DialogueProtocol, Inquiry/PersuasionProtocol | Structuree | N/A (framework) |
| `knowledge_base.py` | KnowledgeBase (propositions, arguments, consistance) | Structuree | N/A (data store) |
| `__init__.py` | Exports combinant les deux systemes | — | — |

### 3.2 Ce qui fonctionne

- Les dataclasses/enums sont correctement extraites et utilisables
- `ArgumentAnalyzer` fonctionne de facon autonome (heuristiques text-based)
- Les protocoles (InquiryProtocol, PersuasionProtocol) sont complets avec FSM
- La KnowledgeBase fonctionne pour stocker/requeter propositions et arguments
- 41 tests passent pour le module debate (tests unitaires)

### 3.3 Ecarts architecturaux CRITIQUES

1. **`EnhancedArgumentationAgent` n'herite PAS de `BaseAgent`** — ne peut pas participer a `AgentGroupChat`
2. **LLM via raw OpenAI SDK** (`self._llm_client.chat.completions.create()`) au lieu de `kernel.invoke()`
3. **Pas de `@kernel_function` plugins** — aucune fonction SK registree
4. **Pas de wiring** dans `AgentFactory`, `bootstrap.py`, ni aucun orchestrateur
5. **`unified_pipeline.py` l.91** importe `DebateAgent` qui **n'existe pas** — la classe s'appelle `EnhancedArgumentationAgent`
6. **`ArgumentationEngine` (10 schemas) non integre** — reste uniquement dans le code etudiant

## 4. Plan de Consolidation

### 4.1 Classification : BaseAgent

`EnhancedArgumentationAgent` est un agent qui fait de l'analyse textuelle et genere des arguments via LLM → doit etre un `BaseAgent(ChatCompletionAgent)`.

### 4.2 Architecture cible

```
agents/core/debate/
├── debate_agent.py          # DebateAgent(BaseAgent) — RECRIRE
├── debate_definitions.py    # GARDER tel quel (dataclasses, enums, personalities)
├── debate_scoring.py        # GARDER tel quel (ArgumentAnalyzer)
├── debate_plugin.py         # CREER — DebatePlugin(@kernel_function)
├── protocols.py             # GARDER tel quel (Walton-Krabbe)
├── knowledge_base.py        # GARDER tel quel
├── argumentation_engine.py  # INTEGRER depuis etudiant (10 schemas)
└── __init__.py              # MODIFIER — exporter DebateAgent
```

### 4.3 Quoi garder du code actuel

**Tel quel** (algorithmes corrects, bien structures) :
- `debate_definitions.py` — enums, dataclasses, 8 personnalites
- `debate_scoring.py` — `ArgumentAnalyzer` avec 8 metriques
- `protocols.py` — DialogueProtocol, InquiryProtocol, PersuasionProtocol
- `knowledge_base.py` — KnowledgeBase

**A integrer depuis le code etudiant** :
- `1_2_7.../local_db_arg/src/core/argumentation_engine.py` → copier comme `argumentation_engine.py`
  - 10 schemas d'argumentation (pas present dans notre codebase)
  - Adapter les imports pour utiliser les types de `protocols.py` au lieu de `models.py`

### 4.4 Quoi reecrire

**`debate_agent.py`** — transformer `EnhancedArgumentationAgent` en `DebateAgent(BaseAgent)` :

```python
class DebateAgent(BaseAgent):
    """Agent de debat multi-personnalite avec strategies adaptatives."""

    def __init__(self, kernel, agent_name="DebateAgent",
                 personality="The Scholar", position="neutral", **kwargs):
        system_prompt = f"You are {agent_name}, personality: {personality}..."
        super().__init__(kernel=kernel, agent_name=agent_name,
                        system_prompt=system_prompt, **kwargs)
        self._personality = PrivateAttr(default=personality)
        self._position = PrivateAttr(default=position)
        self._analyzer = PrivateAttr(default_factory=ArgumentAnalyzer)
        self._memory = PrivateAttr(default_factory=list)
        self._opponent_analysis = PrivateAttr(default_factory=dict)

    def setup_agent_components(self, llm_service_id=None):
        """Enregistre le DebatePlugin dans le kernel."""
        plugin = DebatePlugin(analyzer=self._analyzer)
        self.kernel.add_plugin(plugin, "DebatePlugin")

    def get_agent_capabilities(self) -> dict:
        return {
            "generate_argument": "Generate debate arguments with adaptive strategy",
            "analyze_argument": "Score argument quality on 8 dimensions",
            "evaluate_debate": "Determine debate winner via multi-criteria scoring",
        }

    async def invoke_single(self, messages):
        # Extract topic from messages, use kernel.invoke() for LLM
        result = await self.kernel.invoke(
            plugin_name="DebatePlugin",
            function_name="generate_argument",
            arguments=KernelArguments(topic=topic, position=self._position, ...)
        )
        return [ChatMessageContent(role="assistant", content=str(result))]
```

**`debate_plugin.py`** (NOUVEAU) — plugin SK avec `@kernel_function` :

```python
class DebatePlugin:
    """Plugin SK pour la generation et l'analyse d'arguments de debat."""

    @kernel_function(name="generate_argument",
                     description="Generate a debate argument on a topic")
    async def generate_argument(self, topic: str, position: str,
                                personality: str, phase: str) -> str:
        """Genere un argument adapte au contexte du debat."""
        # Construit le prompt enrichi (strategies, phase, personnalite)
        # Le kernel resoudra l'appel LLM
        ...

    @kernel_function(name="analyze_argument",
                     description="Score argument quality on 8 dimensions")
    def analyze_argument(self, argument_text: str) -> str:
        """Analyse la qualite d'un argument via ArgumentAnalyzer."""
        # Delegue a ArgumentAnalyzer, retourne JSON
        ...

    @kernel_function(name="find_counter_arguments",
                     description="Find counter-arguments using argumentation schemes")
    def find_counter_arguments(self, proposition: str) -> str:
        """Trouve des contre-arguments via ArgumentationEngine."""
        # Delegue a ArgumentationEngine (10 schemas)
        ...
```

### 4.5 Quoi supprimer

- `EnhancedDebateModerator` : NE PAS convertir en BaseAgent — c'est un orchestrateur, pas un agent d'analyse. Le garder comme classe utilitaire dans `debate_agent.py` mais sans le wire comme agent.
- La logique `_call_llm` avec raw OpenAI SDK dans `EnhancedArgumentationAgent` → remplacee par `kernel.invoke()`

## 5. Cablage Architecture

### 5.1 AgentFactory

```python
# agents/factory.py
def create_debate_agent(self, personality="The Scholar", position="neutral", **kwargs):
    agent = DebateAgent(
        kernel=self.kernel, personality=personality, position=position, **kwargs
    )
    agent.setup_agent_components(self.llm_service_id)
    return agent
```

### 5.2 unified_pipeline.py

Corriger l'import casse (ligne ~91) :
```python
# AVANT (casse) :
from ...agents.core.debate.debate_agent import DebateAgent
# APRES :
from ...agents.core.debate.debate_agent import DebateAgent  # sera correct apres rewrite
```

### 5.3 CapabilityRegistry

Conserver le `register_with_capability_registry()` existant dans `__init__.py`, adapter pour enregistrer `DebateAgent` (type AGENT) au lieu de `EnhancedArgumentationAgent`.

### 5.4 Tests

- Adapter `tests/unit/argumentation_analysis/agents/core/test_debate.py` pour tester le nouveau `DebateAgent(BaseAgent)` wrapper
- Tester le `DebatePlugin` avec `@kernel_function`
- Verifier que `EnhancedDebateModerator` fonctionne toujours comme utilitaire
- Tester l'`ArgumentationEngine` integre (10 schemas)

## 6. Criteres d'Acceptation

- [ ] `DebateAgent` herite de `BaseAgent(ChatCompletionAgent, ABC)`
- [ ] `DebatePlugin` utilise `@kernel_function` pour generate_argument, analyze_argument, find_counter_arguments
- [ ] LLM appele via `kernel.invoke()` (pas de raw OpenAI SDK)
- [ ] `ArgumentationEngine` (10 schemas) integre depuis code etudiant
- [ ] `EnhancedDebateModerator` conserve comme classe utilitaire
- [ ] Enregistre dans `CapabilityRegistry` (type AGENT)
- [ ] Cable dans `AgentFactory.create_debate_agent()`
- [ ] Import `unified_pipeline.py` fonctionne sans erreur
- [ ] `ArgumentAnalyzer` (8 metriques) toujours fonctionnel
- [ ] Protocoles Walton-Krabbe (InquiryProtocol, PersuasionProtocol) preserves
- [ ] 8 personnalites configurables via constructeur
- [ ] Template fallback quand LLM indisponible
- [ ] Tests passent (unitaires + integration)
- [ ] Zero regression sur la suite existante (2631 passed baseline)

## 7. Notes

### Fusion des deux implementations

La consolidation doit **fusionner** les points forts des deux implementations etudiantes :
- Du **monolithe** : personnalites, scoring 8 metriques, strategies adaptatives, moderation par phases
- Du **code structure** : protocoles formels Walton-Krabbe, 10 schemas d'argumentation, knowledge base

Le `DebateAgent(BaseAgent)` final sera plus riche que chacune des implementations individuelles car il combinera les deux.

### EnhancedDebateModerator

Ce composant n'est PAS un BaseAgent — c'est un orchestrateur de debat. Il reste comme classe utilitaire pouvant etre utilisee par les orchestrateurs de plus haut niveau (`UnifiedPipeline`, `RealLLMOrchestrator`).

### textstat dependency

`debate_scoring.py` utilise `textstat.flesch_reading_ease()` avec un fallback heuristique si textstat n'est pas installe. Garder ce pattern (dep optionnelle).
