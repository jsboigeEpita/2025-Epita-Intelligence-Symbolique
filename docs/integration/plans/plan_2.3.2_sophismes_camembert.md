# Integration Plan: Detection de Sophismes et Biais Cognitifs (2.3.2)

## 1. Sujet (resume spec professeur)

**Objectif pedagogique** : Detecter automatiquement les sophismes et biais cognitifs dans des textes francais via un pipeline hybride (rules + NLP + ML).

**Fonctionnalites demandees** :
- **Taxonomie** : 6+ types de sophismes (ad_hominem, strawman, false_dilemma, slippery_slope, appeal_to_authority, circular_reasoning) + 4 biais cognitifs
- **Pipeline 4 etapes** : pattern matching symbolique → analyse NLP (spaCy/CamemBERT) → classification ML (BERT fine-tune) → validation TweetyProject (Dung)
- **Evaluation** : precision, recall, F1, matrice de confusion
- **Integration TweetyProject** : validation formelle des detections via argumentation de Dung

**Etudiant** : arthur.hamard

## 2. Travail Etudiant (analyse code)

### Structure (`2.3.2-detection-sophismes/`, ~1100 LoC + data)

| Fichier | LoC | Description |
|---------|-----|-------------|
| `fallacy_pipeline.py` | 323 | **Pipeline principal** : 5 modules sequentiels |
| `train_camembert.py` | 172 | Fine-tuning CamemBERT-large (40 epochs) |
| `benchmark_model.py` | 118 | Evaluation modele fine-tune |
| `benchmark_gpt.py` | 131 | Benchmark GPT-4 vs modele |
| `classify_with_chatgpt.py` | 113 | Wrapper API OpenAI |
| `symbolic_rules.py` | 189 | Patterns spaCy pour 5 familles de sophismes |
| `argument_mining_rules.py` | 63 | Patterns spaCy pour extraction claims/premises |
| `run_cli.py` | 21 | Point d'entree CLI |

**13 classes de sophismes** : ad hominem, ad populum, appel a l'emotion, fallacy of credibility, fallacy of extension, fallacy of logic, faulty generalization, fausse causalite, faux dilemme, intentional, raisonnement circulaire, sophisme de pertinence, equivoque

**Donnees** : Datasets Parquet (train/val/test + augmented) avec poids de classes pour gerer le desequilibre.

### Architecture du pipeline etudiant

1. **Argument Mining** : spaCy `fr_core_news_lg` + Matcher → extraction claims/premises
2. **Classification neurale** : CamemBERT-large fine-tune → 13 classes, softmax
3. **Pattern matching symbolique** : spaCy Matcher, 5 familles (ad hominem, pente glissante, generalisation hative, appel tradition, argument autorite)
4. **Ensemble & Verification** : fusion neural+symbolique, symbolique prioritaire si confiance=1.0
5. **Generation d'explications** : templates en francais

### Points forts

- **Pipeline complet 5 etapes** bien orchestre
- **13 classes de sophismes** avec dataset annote
- **Regles symboliques** precises en francais (patterns spaCy)
- **Fine-tuning CamemBERT-large** avec gestion du desequilibre

### Limitations

- Le modele fine-tune (`./fine_tuned_camembert/`) n'est PAS dans le repo (trop volumineux)
- Hard import du modele a l'import du module (crash si absent)
- Depend de `fr_core_news_lg` (modele spaCy large, ~500Mo)
- Pipeline non async, pas de SK

## 3. Etat Actuel dans le Tronc Commun

### Fichier existant

`argumentation_analysis/adapters/french_fallacy_adapter.py` (631 LoC)

### Ce qui fonctionne

L'adaptateur implemente un **systeme hybride 3 tiers** :
- **Tier 3 (Symbolique)** : `SymbolicFallacyDetector` — copie des regles spaCy du code etudiant, degradation gracieuse (`fr_core_news_lg` → `fr_core_news_sm`)
- **Tier 2 (NLI Zero-Shot)** : `NLIFallacyDetector` — utilise `mDeBERTa-v3-base-xnli` pour classification zero-shot (PAS le CamemBERT fine-tune)
- **Tier 1 (LLM)** : `LLMFallacyDetector` — **placeholder vide** (retourne `[]`)
- **Fusion** : priorite symbolique (confiance=1.0)

### Ecarts CRITIQUES

1. **Import casse** : `unified_pipeline.py:165` importe `from ...adapters.camembert_fallacy import ...` mais le fichier s'appelle `french_fallacy_adapter.py`
2. **Pas de CamemBERT** : l'adaptateur remplace le CamemBERT fine-tune par NLI zero-shot (mDeBERTa) — approche differente
3. **LLM tier stub** : `LLMFallacyDetector.detect_async()` retourne toujours `[]`
4. **N'est PAS un Plugin SK** — classe standalone, pas de `@kernel_function`
5. **Pas de wiring** dans `InformalAnalysisAgent` ni aucun agent
6. **Regles symboliques incompletes** : manque `ARGUMENT_D_AUTORITE_GENERAL` (3 patterns)
7. **Pas d'heritage `AbstractFallacyDetector`** visible dans les imports des agents

## 4. Plan de Consolidation

### 4.1 Classification : Plugin SK (pour InformalAgent)

La detection de sophismes est un complement au `InformalAnalysisAgent` existant qui utilise deja `TaxonomySophismDetector` (8 familles). Le CamemBERT/NLI ajoute une detection neurale en francais.

### 4.2 Architecture cible

```
adapters/
├── french_fallacy_adapter.py     # GARDER + CORRIGER — renommer ou creer alias
└── camembert_fallacy.py          # CREER — alias d'import pour unified_pipeline

plugins/
└── french_fallacy_plugin.py      # CREER — FrenchFallacyPlugin(@kernel_function)
```

### 4.3 Ce qu'on garde

**Tel quel** (bien adapte) :
- `SymbolicFallacyDetector` — regles spaCy fonctionnelles, degradation gracieuse
- `NLIFallacyDetector` — alternative viable au CamemBERT (pas besoin de modele pre-entraine)
- Dataclasses `FallacyDetection`, `FallacyAnalysisResult`
- Fusion tier par priorite symbolique

### 4.4 Ce qu'on corrige

1. **Import alias** : creer `adapters/camembert_fallacy.py` qui re-exporte depuis `french_fallacy_adapter.py`
2. **Regles symboliques** : ajouter les 3 patterns `ARGUMENT_D_AUTORITE_GENERAL` manquants
3. **LLM tier** : implementer via `ServiceDiscovery` au lieu de stub vide

### 4.5 Ce qu'on cree

**`plugins/french_fallacy_plugin.py`** — Plugin SK :

```python
class FrenchFallacyPlugin:
    """Plugin SK pour la detection de sophismes en francais (3 tiers)."""

    def __init__(self):
        self._adapter = FrenchFallacyAdapter()

    @kernel_function(name="detect_fallacies_french",
                     description="Detect fallacies in French text using hybrid 3-tier system")
    async def detect_fallacies(self, text: str) -> str:
        """Detecte les sophismes (symbolique + NLI + LLM)."""
        result = await self._adapter.analyze(text)
        return json.dumps(result.to_dict(), ensure_ascii=False)

    @kernel_function(name="get_fallacy_explanation",
                     description="Get explanation for detected fallacies")
    def get_explanation(self, fallacy_type: str) -> str:
        """Retourne une explication detaillee d'un type de sophisme."""
        ...
```

### 4.6 Decision CamemBERT vs NLI

Le modele CamemBERT fine-tune n'est pas dans le repo (trop volumineux). L'adaptateur NLI zero-shot (mDeBERTa) est une **alternative valable** qui :
- Ne necessite pas de modele pre-entraine specifique
- Supporte les 13 classes sans fine-tuning
- Se telecharge automatiquement (~600Mo)

**Decision** : garder NLI comme detection principale. Si le modele CamemBERT fine-tune devient disponible, il peut etre ajoute comme tier additionnel.

## 5. Cablage Architecture

### 5.1 InformalAnalysisAgent

Le plugin s'integre dans `InformalAnalysisAgent.setup_agent_components()` :

```python
# Dans InformalAnalysisAgent.setup_agent_components()
try:
    from argumentation_analysis.plugins.french_fallacy_plugin import FrenchFallacyPlugin
    fallacy_plugin = FrenchFallacyPlugin()
    self.kernel.add_plugin(fallacy_plugin, "FrenchFallacy")
except ImportError:
    pass  # Plugin optionnel
```

### 5.2 unified_pipeline.py

Corriger l'import (ligne ~165) via l'alias `camembert_fallacy.py`.

### 5.3 CapabilityRegistry

```python
registry.register_plugin(
    name="FrenchFallacyPlugin",
    plugin_class=FrenchFallacyPlugin,
    capabilities=["french_fallacy_detection", "sophism_detection_neural"],
)
```

## 6. Criteres d'Acceptation

- [ ] `FrenchFallacyPlugin` cree avec `@kernel_function` decorateurs
- [ ] Import `unified_pipeline.py` corrige (alias `camembert_fallacy.py`)
- [ ] Regles symboliques completees (3 patterns autorite manquants)
- [ ] LLM tier implemente via ServiceDiscovery (ou desactive proprement)
- [ ] Enregistrable dans InformalAnalysisAgent comme plugin additionnel
- [ ] Enregistre dans CapabilityRegistry (type PLUGIN)
- [ ] Degradation gracieuse preservee (spaCy, mDeBERTa optionnels)
- [ ] Tests passent
- [ ] Zero regression

## 7. Notes

### Donnees d'entrainement

Les datasets Parquet (13 classes, francais) dans `2.3.2-detection-sophismes/data/` sont une ressource precieuse pour un fine-tuning futur. Ils ne sont pas copies dans le tronc commun mais restent accessibles dans le dossier etudiant.

### Relation avec InformalAnalysisAgent

L'agent informel existant utilise `TaxonomySophismDetector` (8 familles de sophismes, detection par mots-cles). Le plugin FrenchFallacy ajoute :
- Detection neurale (NLI) sur 13 classes plus fines
- Pattern matching symbolique (spaCy Matcher)
- Fusion multi-tier

Les deux systemes sont **complementaires**, pas concurrents.
