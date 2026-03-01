# Integration Plan: Systeme JTMS (1.4.1)

## 1. Sujet (resume spec professeur)

**Objectif pedagogique** : Implementer un systeme de maintenance de verite (TMS) avec deux variantes : JTMS (Justification-based) et ATMS (Assumption-based).

**Fonctionnalites demandees** :
- JTMS : croyances, justifications (in/out lists), propagation, labeling (valid/invalid/unknown)
- ATMS : environnements, labels comme ensembles d'hypotheses, detection de contradictions
- Detection de cycles (SCC), revision non-monotone (postulats AGM)
- Integration TweetyProject pour la logique formelle
- Visualisation du reseau de croyances

**Etudiants** : julien.zebic, thomas.leguere

## 2. Travail Etudiant (analyse code)

### Structure (`1.4.1-JTMS/`, ~620 LoC)

| Fichier | LoC | Description |
|---------|-----|-------------|
| `jtms.py` | 184 | **JTMS** : Belief, Justification, JTMS — core |
| `atms.py` | 83 | **ATMS** : Node, ATMS — environnements et contradictions |
| `tests.py` | 185 | 6 tests JTMS + 6 tests ATMS |
| `main.py` | 17 | Demo interactive |
| `belifs_loader.py` | 17 | Chargeur JSON |
| `analyse_complete.py` | 135 | Script de test complet |

### Points forts
- **JTMS complet** : propagation recursive, detection SCC (networkx), visualisation (pyvis)
- **ATMS fonctionnel** : labels comme ensembles de frozensets, produit cartesien des environnements, detection de contradictions
- 12 tests unitaires couvrant les cas edge (circulaire, multi-step, out-list blocking)

### Limitations
- Hard imports pyvis/networkx (crash si absent)
- Typo `update_non_monotonic_befielfs()` dans le code etudiant
- Pas de SK, pas de service wrapper

## 3. Etat Actuel dans le Tronc Commun

### Fichiers existants dans `argumentation_analysis/services/jtms/`

| Fichier | LoC | Statut |
|---------|-----|--------|
| `jtms_core.py` | 263 | JTMS complete — version amelioree du code etudiant |
| `__init__.py` | 19 | Exporte Belief, Justification, JTMS |

### Ce qui fonctionne

- **Algorithme identique** au code etudiant avec ameliorations :
  - Type hints, docstrings
  - Logging au lieu de print
  - Dependances optionnelles (`_HAS_NETWORKX`, `_HAS_PYVIS`)
  - Typo corrige (`befielfs` → `beliefs`)
  - Emoji remplace par texte dans `explain_belief()`
- Utilise par `SherlockJTMSAgent` dans les pipelines existants
- Enregistre dans `CapabilityRegistry`
- Tests passent

### Ecarts

1. **ATMS non integre** — seulement le JTMS est dans le tronc commun
2. **Pas de `@kernel_function`** plugin (mais c'est un service, pas un plugin)
3. **ServiceDiscovery** pas effectivement enregistre

## 4. Plan de Consolidation

### 4.1 Classification : Service (deja fait — verification)

Le JTMS est un service de raisonnement non-monotone, deja bien integre et utilise par `SherlockJTMSAgent`.

### 4.2 Actions

1. **Verifier le cablage ServiceDiscovery** — s'assurer que le service est trouvable
2. **Integrer l'ATMS** (optionnel) : copier `atms.py` → `services/jtms/atms_core.py`
   - Meme pattern que jtms_core.py : ajouter type hints, docstrings, deps optionnelles
   - Exporter depuis `__init__.py`
3. **Verifier que `SherlockJTMSAgent`** utilise correctement le service

### 4.3 Ce qu'on garde

**Tel quel** : tout le code existant est correct.

## 5. Criteres d'Acceptation

- [ ] `jtms_core.py` fonctionne (deja le cas)
- [ ] Enregistre dans `CapabilityRegistry` (type SERVICE) — verifier
- [ ] `SherlockJTMSAgent` l'utilise correctement — verifier
- [ ] (Optionnel) ATMS integre comme `atms_core.py`
- [ ] Zero regression

## 6. Notes

### Effort estime : ~30min (verification) + ~1h si ATMS integre

Ce projet est le mieux integre de tous. Le seul gap significatif est l'absence de l'ATMS.
