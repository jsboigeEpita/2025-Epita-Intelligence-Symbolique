# Integration Plan: Evaluation Qualite Argumentative (2.3.5)

## 1. Sujet (resume spec professeur)

**Objectif pedagogique** : Evaluer les qualites positives ("vertus") des arguments, en complement de la detection de sophismes (defauts).

**Fonctionnalites demandees** :
- **9 vertus argumentatives** : clarte, pertinence, suffisance des preuves, refutation constructive, structure logique, analogies pertinentes, consistance, source fiable, exhaustivite
- **4 modules** : preprocessing, detecteurs par vertu, agregation scores, reporting
- **Approches de detection** : heuristiques rule-based + NLP (spaCy, textstat)
- **Integration** : combiner avec l'agent de detection de sophismes pour une evaluation holistique

**Etudiants** : Cambou, Prunet, Raitiere-Delsupexhe, Schreiber

## 2. Travail Etudiant (analyse code)

### Structure (`2.3.5_argument_quality/src/`, ~450 LoC)

| Fichier | LoC | Description |
|---------|-----|-------------|
| `agent.py` | 235 | **Coeur** : 9 detecteurs de vertus + `evaluer_argument()` + 13 exemples |
| `arguments.py` | 47 | Classification type d'argument (7 types, regex) — non integre |
| `interface.py` | 112 | GUI PyQt5 — non integre |
| `server.py` | 49 | WebSocket mock — non integre |
| `ressources_argumentatives.json` | 45 | Ressources linguistiques (connecteurs, marqueurs, sources) |

### Qualite du code

- **Bien structure** pour un projet etudiant — 9 detecteurs independants, chacun retourne un score 0.0-1.0
- **Hard import** de spaCy et textstat (crash si absent)
- Auto-telechargement de `fr_core_news_sm` a l'import (pratique mauvaise)
- `arguments.py` fournit une classification de type d'argument (LOGICAL, CAUSAL, ANALOGICAL, etc.) via regex — fonctionnalite complementaire non integree

### Points forts a conserver

- 9 detecteurs de vertus : algorithmes heuristiques solides
- `ressources_argumentatives.json` : 28 connecteurs, 12 patterns de citation, 15 marqueurs de refutation, 21 connecteurs logiques, 14 patterns d'analogie, 30+ sources credibles
- 13 arguments d'exemple pour les tests

## 3. Etat Actuel dans le Tronc Commun

### Fichiers existants dans `argumentation_analysis/agents/core/quality/`

| Fichier | LoC | Statut |
|---------|-----|--------|
| `quality_evaluator.py` | 337 | Integration correcte des 9 vertus |
| `__init__.py` | 17 | Exporte `ArgumentQualityEvaluator`, `VERTUES`, `evaluer_argument` |
| `ressources_argumentatives.json` | ~45 | Copie des ressources linguistiques |

### Ce qui fonctionne

- **9 detecteurs identiques** au code etudiant, avec les memes seuils et logique
- **Degradation gracieuse** ajoutee : spaCy et textstat optionnels, fallback heuristiques
- **`_FALLBACK_RESOURCES`** inline si le JSON est absent (10 connecteurs vs 28 dans le fichier)
- **`ArgumentQualityEvaluator`** wrapper classe avec gestion d'erreur par detecteur
- **Enregistre dans CapabilityRegistry** via `register_with_capability_registry()`
- Tests passent (13 tests unitaires)

### Ecarts architecturaux

1. **N'est PAS un Plugin SK** — classe standalone, pas de `@kernel_function`
2. **Pas de wiring** dans aucun agent existant (SynthesisAgent pourrait l'utiliser)
3. **`arguments.py`** (classification de type d'argument) non integre

## 4. Plan de Consolidation

### 4.1 Classification : Plugin SK

La qualite argumentative est un **scoring algorithmique pur** (pas d'appel LLM, pas d'analyse textuelle de haut niveau). C'est un plugin reutilisable par n'importe quel agent, pas un agent autonome.

### 4.2 Architecture cible

```
agents/core/quality/
├── quality_evaluator.py          # GARDER tel quel (logique metier)
├── ressources_argumentatives.json # GARDER
├── __init__.py                   # MODIFIER — ajouter export plugin
└── quality_plugin.py             # CREER — QualityScoringPlugin(@kernel_function)
```

### 4.3 Ce qu'on garde

**Tel quel** (code correct, bien adapte) :
- `quality_evaluator.py` — `ArgumentQualityEvaluator` avec 9 detecteurs
- `ressources_argumentatives.json` — ressources linguistiques
- `register_with_capability_registry()` dans `__init__.py`

### 4.4 Ce qu'on cree

**`quality_plugin.py`** — Plugin SK reutilisable :

```python
class QualityScoringPlugin:
    """Plugin SK pour l'evaluation de qualite argumentative (9 vertus)."""

    def __init__(self):
        self._evaluator = ArgumentQualityEvaluator()

    @kernel_function(name="evaluate_argument_quality",
                     description="Evaluate argument quality on 9 virtue dimensions")
    def evaluate_quality(self, text: str) -> str:
        """Evalue la qualite d'un argument (9 vertus, score 0-1 chacune)."""
        result = self._evaluator.evaluate(text)
        return json.dumps(result, ensure_ascii=False)

    @kernel_function(name="get_quality_summary",
                     description="Get a human-readable quality assessment summary")
    def get_quality_summary(self, text: str) -> str:
        """Resume la qualite en langage naturel."""
        result = self._evaluator.evaluate(text)
        # Genere un resume textuel des forces et faiblesses
        ...
```

### 4.5 Quoi ne pas integrer

- `arguments.py` (classification de type) — fonctionnalite interessante mais hors scope du plan actuel. Peut etre ajoutee plus tard comme extension du plugin.
- `interface.py` (PyQt5 GUI) — frontend desktop, hors scope
- `server.py` (WebSocket mock) — non fonctionnel

## 5. Cablage Architecture

### 5.1 Usage dans SynthesisAgent

Le `SynthesisAgent` peut enregistrer le plugin dans son kernel pour enrichir ses syntheses :

```python
# Dans SynthesisAgent.setup_agent_components()
quality_plugin = QualityScoringPlugin()
self.kernel.add_plugin(quality_plugin, "QualityScoring")
```

### 5.2 CapabilityRegistry

Conserver l'enregistrement existant, ajouter le plugin :

```python
registry.register_plugin(
    name="QualityScoringPlugin",
    plugin_class=QualityScoringPlugin,
    capabilities=["argument_quality_evaluation"],
)
```

### 5.3 Tests

- Tests existants suffisants pour la logique metier
- Ajouter 2-3 tests pour le plugin SK (`@kernel_function` invocation)

## 6. Criteres d'Acceptation

- [ ] `QualityScoringPlugin` cree avec `@kernel_function` decorateurs
- [ ] Delegue a `ArgumentQualityEvaluator` existant (pas de duplication)
- [ ] Enregistrable dans n'importe quel kernel via `kernel.add_plugin()`
- [ ] Enregistre dans `CapabilityRegistry` (type PLUGIN)
- [ ] `SynthesisAgent` peut l'utiliser pour enrichir ses analyses
- [ ] Degradation gracieuse preservee (spaCy/textstat optionnels)
- [ ] Tests passent (unitaires existants + plugin SK)
- [ ] Zero regression

## 7. Notes

### Effort estime : ~1h

Ce projet est le plus simple a consolider car :
1. L'integration actuelle est deja correcte et bien faite
2. Il manque uniquement le wrapper `@kernel_function`
3. La logique metier ne change pas

### Integration future de `arguments.py`

La classification de type d'argument (LOGICAL, CAUSAL, ANALOGICAL, etc.) par regex pourrait devenir une seconde `@kernel_function` du plugin :
```python
@kernel_function(name="classify_argument_type", ...)
def classify_type(self, text: str) -> str: ...
```
Mais ceci est optionnel et hors scope du plan actuel.
