# Integration Plan: Abstract Argumentation Dung (abs_arg_dung)

## 1. Sujet (resume spec)

**Pas de spec dediee** — ce projet est reference dans les specs unifiees (DEMOCRATECH, Speech-to-Text) comme composant de l'ecosysteme.

**Fonctionnalite** : Wrapper JPype autour du framework d'argumentation de Dung (TweetyProject), fournissant 7 semantiques : grounded, preferred, stable, complete, admissible, ideal, semi-stable.

## 2. Travail Etudiant (analyse code)

### Structure (`abs_arg_dung/`, ~1000 LoC)

| Fichier | LoC | Description |
|---------|-----|-------------|
| `agent.py` | 444 | **`DungAgent`** — wrapper Tweety/JPype, 7 semantiques, analyse, visualisation |
| `enhanced_agent.py` | 131 | `EnhancedDungAgent(DungAgent)` — corrections pour cas edge (cycles, self-attack) |
| `io_utils.py` | 140 | `FrameworkIO` — export/import JSON, TGF, DOT |
| `cli.py` | 253 | CLI argparse avec 6 sous-commandes |
| `config.py` | — | Configuration |
| `benchmark.py` | — | Benchmarks |
| `framework_generator.py` | — | Generateur de frameworks aleatoires |
| `test_agent.py` | — | Tests DungAgent |
| `test_enhanced.py` | — | Tests EnhancedDungAgent |
| `libs/` | — | **Copie complete des 22 JARs Tweety 1.28** (doublon) |

### Points forts
- **7 semantiques completes** avec cache lazy
- `EnhancedDungAgent` pour gestion des cas edge (cycles parfaits, self-attack)
- Analyse structurelle (cycles, attaques, statut credule/sceptique)
- I/O multi-format (JSON, TGF, DOT)
- Bonne couverture de tests

### Limitations
- Hard imports jpype, networkx, matplotlib
- Copie locale des JARs (doublon de `libs/tweety/`)
- Code utilise directement dans les tests du tronc commun (pas d'adaptateur)

## 3. Etat Actuel dans le Tronc Commun

### Integration minimale

- `abs_arg_dung/__init__.py` (7 lignes) — docstring seulement
- Le code est **utilise tel quel** depuis le dossier etudiant par certains tests
- Pas de service wrapper dans `argumentation_analysis/services/`
- Le `TweetyBridge` existant dans `argumentation_analysis/agents/core/logic/` fournit deja certaines fonctionnalites Dung

## 4. Plan de Consolidation

### 4.1 Classification : Service (verification/cablage)

Le `DungAgent` est un service d'argumentation formelle. Il ne fait pas d'analyse textuelle, donc pas un BaseAgent du tronc commun.

### 4.2 Actions

1. **Ne PAS copier** `DungAgent` dans `services/` — le code est deja fonctionnel a sa place
2. **Verifier les imports** : s'assurer que les tests referençant `abs_arg_dung` fonctionnent correctement
3. **CapabilityRegistry** : enregistrer `DungAgent` comme service avec capabilities
4. **Supprimer `libs/` doublon** si les JARs centraux (`libs/tweety/`) sont suffisants
5. **Relation avec TweetyBridge** : documenter la difference — `TweetyBridge` est interne aux agents logiques, `DungAgent` est un service standalone plus complet

### 4.3 Decision pragmatique

Le `DungAgent` fonctionne, est teste, et est deja accessible. L'effort de consolidation se limite a :
- S'assurer que l'enregistrement CapabilityRegistry est correct
- Documenter la relation avec `TweetyBridge`
- Verifier que les tests passent sans `sys.path` hacks

## 5. Criteres d'Acceptation

- [ ] `abs_arg_dung` importable sans `sys.path` hacks
- [ ] Enregistre dans `CapabilityRegistry` (type SERVICE)
- [ ] JARs dupliques identifies (mais ne pas supprimer sans verification)
- [ ] Relation avec `TweetyBridge` documentee
- [ ] Tests existants passent
- [ ] Zero regression

## 6. Notes

### Effort estime : ~30min

Verification et cablage uniquement — le code est fonctionnel.
