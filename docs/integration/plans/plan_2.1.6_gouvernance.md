# Integration Plan: Gouvernance Multi-Agents (2.1.6)

## 1. Sujet (resume spec professeur)

**Objectif pedagogique** : Implementer un systeme de gouvernance multi-agents avec mecanismes de vote, consensus, et resolution de conflits.

**Fonctionnalites demandees** :
- **Theorie du choix social** : pluralite, Borda, Condorcet
- **Theorie des jeux cooperatifs** : valeurs de Shapley
- **Agents BDI** (Belief-Desire-Intention) avec revision de croyances
- **Protocoles FIPA-ACL** : performatifs VOTE, DELEGATE, FORM_COALITION
- **Algorithmes de consensus** : tolerance byzantine, Raft, vote quadratique
- **Integration TweetyProject** : validation via argumentation de Dung
- **Resolution de conflits** : mediation collaborative, competitive, compromis

**Etudiant** : arthur.guelennoc (niveau avance)

## 2. Travail Etudiant (analyse code)

### Structure (`2.1.6_multiagent_governance_prototype/`, ~1300 LoC + scenarios)

| Fichier | LoC | Description |
|---------|-----|-------------|
| `agents/base_agent.py` | 244 | Agent + BDIAgent + ReactiveAgent (personnalites, Q-learning) |
| `agents/agent_factory.py` | 44 | Factory statique (base/bdi/reactive) |
| `governance/methods.py` | 133 | **7 methodes de vote** |
| `governance/simulation.py` | 269 | Simulation, manipulation, Shapley values |
| `governance/conflict_resolution.py` | 74 | Detection + 3 strategies de mediation |
| `metrics/metrics.py` | 131 | Consensus, fairness (Gini), efficiency, stability |
| `cli.py` | 225 | CLI Click avec 6 commandes |
| `runner.py` | 44 | Batch runner avec export CSV |
| `reporting/visualize.py` | 187 | Visualisations matplotlib/seaborn |
| `scenarios/*.json` | 14 fichiers | Scenarios predefinies (budget, coalition, byzantine, etc.) |

### Points forts

- **7 methodes de vote** completes : majority, plurality, borda_count, condorcet, quadratic_voting, byzantine_consensus, raft_consensus
- **Agents avec personnalites** : stubborn/flexible/strategic/random avec adaptation (Q-learning epsilon-greedy)
- **BDI et Reactive** : sous-classes avec beliefs/desires/intentions et rules
- **Simulation riche** : coalitions, gossip distribue, manipulation (strategic, bribery, noise), analyse de manipulabilite (7 scenarios)
- **Metriques completes** : consensus, Gini fairness, efficiency, satisfaction, stability, per-agent
- **14 scenarios JSON** pour tester des configurations variees

### Limitations

- Pas de SK, pas de BaseAgent du tronc commun
- Pas d'appel LLM (tout algorithmique)
- Imports absolus (`from governance import ...`) cassent hors du dossier etudiant
- `Agent.decide()` crash si `context=None` avec coalition

## 3. Etat Actuel dans le Tronc Commun

### Fichiers existants dans `argumentation_analysis/agents/core/governance/`

| Fichier | LoC | Statut |
|---------|-----|--------|
| `governance_methods.py` | 121 | 7 methodes de vote — fidele au code etudiant |
| `governance_agent.py` | 271 | Agent + BDI + Reactive + Factory — bugs corriges |
| `simulation.py` | 258 | Simulation + manipulation + Shapley — adapte |
| `conflict_resolution.py` | 62 | Detection + 3 mediations — simplifie |
| `metrics.py` | 130 | 7 metriques — adapte pour serialisation |
| `__init__.py` | 31 | Exports combines |

### Ce qui fonctionne

- **Tout le code algorithmique est fonctionnel** et teste (41 tests passent)
- Imports relatifs corrects
- Bug `context=None` corrige dans `Agent.decide()`
- `gini()` et `summarize_results()` adaptes pour serialisation Python (float casting)
- `CapabilityRegistry` enregistrement fonctionnel

### Ecarts architecturaux

1. **N'est PAS un Plugin SK** — classes standalone, pas de `@kernel_function`
2. **`Agent` locale (governance) ≠ `BaseAgent` du tronc commun** — homonymie confuse
3. **Pas de wiring** dans aucun orchestrateur ou agent existant
4. **`unified_pipeline.py` l.111** importe `GovernanceAgent` qui **n'existe pas** — la classe s'appelle `Agent`
5. **14 scenarios JSON** non copies (tests creent des scenarios programmatiquement)
6. **CLI/visualisations** non integrees (correct pour un usage library)

## 4. Plan de Consolidation

### 4.1 Classification : Plugin SK

La gouvernance est un ensemble d'**algorithmes de decision collective** — pas un agent qui fait de l'analyse textuelle. C'est un plugin SK reutilisable par tout agent orchestrateur.

### 4.2 Architecture cible

```
agents/core/governance/
├── governance_methods.py     # GARDER tel quel
├── governance_agent.py       # GARDER tel quel (renommer Agent → GovernanceParticipant?)
├── simulation.py             # GARDER tel quel
├── conflict_resolution.py    # GARDER tel quel
├── metrics.py                # GARDER tel quel
├── governance_plugin.py      # CREER — GovernancePlugin(@kernel_function)
└── __init__.py               # MODIFIER — exporter le plugin + renommer si necessaire
```

### 4.3 Ce qu'on garde

**Tel quel** (tout le code est correct et bien adapte) :
- `governance_methods.py` — 7 methodes de vote
- `governance_agent.py` — Agent/BDI/Reactive/Factory (avec bug fixes)
- `simulation.py` — simulation, manipulation, Shapley
- `conflict_resolution.py` — detection + mediation
- `metrics.py` — 7 metriques

### 4.4 Ce qu'on cree

**`governance_plugin.py`** — Plugin SK :

```python
class GovernancePlugin:
    """Plugin SK pour la gouvernance multi-agents (vote, consensus, conflits)."""

    @kernel_function(name="run_vote",
                     description="Run a voting process using a specified method")
    def run_vote(self, agents_json: str, options_json: str,
                 method: str = "condorcet") -> str:
        """Execute un vote avec la methode specifiee."""
        agents = json.loads(agents_json)
        options = json.loads(options_json)
        # Cree des Agent() temporaires, execute la methode
        ...

    @kernel_function(name="detect_conflicts",
                     description="Detect conflicts between agent positions")
    def detect_conflicts(self, positions_json: str) -> str:
        """Detecte les conflits entre positions d'agents."""
        ...

    @kernel_function(name="compute_consensus_metrics",
                     description="Compute consensus, fairness, and stability metrics")
    def compute_metrics(self, results_json: str) -> str:
        """Calcule les metriques de gouvernance."""
        ...

    @kernel_function(name="simulate_governance",
                     description="Run a full governance simulation")
    def simulate(self, scenario_json: str, method: str = "condorcet") -> str:
        """Execute une simulation de gouvernance complete."""
        ...
```

### 4.5 Renommage `Agent` → `GovernanceParticipant`

La classe `Agent` dans `governance_agent.py` cree une confusion avec le concept d'agent SK (`BaseAgent`). Options :
- **Option A** : renommer `Agent` → `GovernanceParticipant` (plus clair)
- **Option B** : garder `Agent` mais toujours qualifier (`governance.Agent` vs `BaseAgent`)

**Decision** : Option B (moins de changements, les tests referent a `Agent`). Le `__init__.py` exporte deja comme `Agent` et les tests l'utilisent.

## 5. Cablage Architecture

### 5.1 unified_pipeline.py

Corriger l'import casse (ligne ~111) :
```python
# AVANT (casse) :
from ...agents.core.governance.governance_agent import GovernanceAgent
# APRES :
from ...agents.core.governance.governance_agent import Agent as GovernanceAgent
```
Ou mieux, exporter un alias depuis `__init__.py`.

### 5.2 Usage par orchestrateurs

Le plugin peut etre utilise par `RealLLMOrchestrator` ou `UnifiedPipeline` pour prendre des decisions collectives entre agents :

```python
gov_plugin = GovernancePlugin()
kernel.add_plugin(gov_plugin, "Governance")
# Lors d'un desaccord entre agents, invoquer le vote
result = await kernel.invoke("Governance", "run_vote",
    agents_json=..., options_json=..., method="condorcet")
```

### 5.3 CapabilityRegistry

```python
registry.register_plugin(
    name="GovernancePlugin",
    plugin_class=GovernancePlugin,
    capabilities=["multi_agent_voting", "consensus", "conflict_resolution"],
)
```

## 6. Criteres d'Acceptation

- [ ] `GovernancePlugin` cree avec `@kernel_function` decorateurs
- [ ] Delegue aux modules existants (pas de duplication)
- [ ] Import `unified_pipeline.py` corrige (`GovernanceAgent` alias)
- [ ] Enregistrable dans n'importe quel kernel
- [ ] Enregistre dans `CapabilityRegistry` (type PLUGIN)
- [ ] 7 methodes de vote accessibles via le plugin
- [ ] Metriques (consensus, fairness, efficiency) accessibles
- [ ] Tests existants preserves + tests plugin
- [ ] Zero regression

## 7. Notes

### Effort estime : ~1.5h

Le code algorithmique est complet et bien teste. Le travail consiste essentiellement a creer le wrapper `@kernel_function` et corriger l'import dans `unified_pipeline.py`.

### Scenarios JSON

Les 14 scenarios JSON du code etudiant sont des **ressources de test precieuses**. Ils peuvent etre copies dans `tests/fixtures/governance/` pour enrichir les tests d'integration du plugin. Hors scope du plan actuel.

### Relation avec le systeme Lego

Le `GovernancePlugin` s'integre naturellement dans le systeme Lego : les agents enregistres dans `CapabilityRegistry` peuvent etre utilises comme "votants" dans un processus de gouvernance, et le plugin peut etre invoque par n'importe quel orchestrateur.
