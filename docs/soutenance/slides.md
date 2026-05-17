---
title: "Analyse Argumentative Multi-Agents"
subtitle: "Intelligence Symbolique — EPITA 2025"
author: "Equipe Projet IS"
date: "2025"
revealjs-url: "https://cdn.jsdelivr.net/npm/reveal.js@5"
theme: "white"
---

# Analyse Argumentative Multi-Agents

## Intelligence Symbolique — EPITA 2025

Equipe Projet IS | Mai 2025

---

## Le Probleme

- Comment analyser automatiquement la qualite d'un discours politique ?
- Peut-on detecter les sophismes de maniere systematique ?
- Comment formaliser un debat en logique mathematique ?
- Est-il possible de simuler un vote democratique sur des arguments ?

**Reponse** : Un systeme multi-agents combinant IA symbolique et connexionniste.

---

## Architecture Multi-Agents

```
Strategic  → Orchestrators (workflows complexes)
Tactical   → Coordinators (interactions agents)
Operational → Base agents (Sherlock, Watson, JTMS, FOL, Modal)
```

- **CapabilityRegistry** — Registre central Lego
- **AgentFactory** — Fabrication d'agents avec wiring SK
- **WorkflowDSL** — Workflows declaratifs en DAG
- **17 phases** dans le pipeline spectacular

---

## Le Tronc Commun

Fondation du professeur :

- **Agents SK** heritant de `BaseAgent(ChatCompletionAgent)`
- **Plugins** exposes via `@kernel_function`
- **Tweety Bridge** — Raisonneur formel Java/JPype
- **Communication** — Messagerie multi-canal hierarchique
- **Pydantic V2** — Validation et serialisation

---

## Integrations Etudiants

12 projets etudiens integres dans l'architecture `BaseAgent` :

| Projet | Composant integre |
|--------|------------------|
| 1.4.1 JTMS | Systeme de maintenance de verite |
| 2.3.2 Detection sophismes | Taxonomie 8 familles |
| 2.3.3 Contre-argumentation | 5 strategies rhetoriques |
| 2.3.5 Qualite argumentaire | 9 vertus d'evaluation |
| 2.3.6 LLM local | Adaptateur endpoints locaux |
| ... | ... |

---

## Pipeline Spectacular — 17 Phases

```
Extract → Quality → NL-to-Logic → Neural Detect → Hierarchical Fallacy
    ↓
PL → FOL → Modal → Dung → ASPIC → Counter-Args
    ↓
JTMS → Debate → ATMS → Governance → Formal Synthesis → Narrative Synthesis
```

17 phases | 0 echecs (sur golden fixture) | ~45s par document

---

## Phase 1-2 : Extraction & Qualite

**Extraction** : 8 arguments identifies (5 premisses, 3 conclusions)

**Qualite** : 4 dimensions par argument

| Argument | Clarte | Coherence | Pertinence | Global |
|----------|--------|-----------|------------|--------|
| arg_p1 | 0.92 | 0.88 | 0.95 | **0.90** |
| arg_c1 | 0.85 | 0.72 | 0.88 | **0.78** |

Score moyen : 0.84 | Range : 0.74 – 0.90

---

## Phase 3-4 : Detection de Sophismes

**Detection hybride** : neuronale + hierarchique

| Sophisme | Famille | Confiance |
|----------|---------|-----------|
| Ad hominem | Pertinence | 87% |
| Pente glissante | Causal | 82% |
| Homme de paille | Distorsion | 79% |
| Faux dilemme | Presomption | 75% |

**Taxonomie** : 8 familles, 30+ types de sophismes

---

## Phase 5-7 : Logique Formelle

**Trois systemes** pour le meme texte :

- **Propositionnelle** : P1 AND P2 → C1 (3/5 valides)
- **Premier ordre** : ∀x(Citizen(x) → HasRight(x, expression))
  - 16 predicats dans la signature
- **Modale S5** : □(HasRight(citizen, expression))
  - 5 formules analysees

---

## Phase 8 : Cadre de Dung

**Argumentation abstraite** — extensions semantiques :

```
arg_c1 ← ATTACKS ← arg_p3
arg_c1 ← ATTACKS ← arg_c2
```

| Semantique | Taille | Arguments acceptes |
|-------------|--------|--------------------|
| Grounded | 6 | p1, p2, p4, p5, c2, c3 |
| Preferred | 6-7 | + p3 (credule) |
| Stable | 6 | p1, p2, p4, p5, c2, c3 |

**Verdict** : arg_c1 rejete (grounded)

---

## Phase 9 : ATMS — Branchement d'Hypotheses

**4 contextes de raisonnement** :

| Contexte | Statut | Hypotheses |
|----------|--------|------------|
| Liberte absolue | **CONTRADICTOIRE** | freedom_absolute |
| Liberte regulee | Consistent | regulation_compatible |
| Inductif historique | **CONTRADICTOIRE** | censorship_authoritarian |
| Deliberatif | Consistent | structured_deliberation |

2 contextes contradictoires revelent les tensions internes

---

## Phase 10 : JTMS — Cascades de Retraction

**Maintenance de verite** avec 10 croyances :

```
Cascade 1 : counter_reductio → arg_c1: IN → OUT
  Raison : Le contre-argument reductio expose le faux dilemme

Cascade 2 : counter_example → arg_p3: confiance 0.85 → 0.78
  Raison : L'exemple allemand affaiblit le lien causal
```

Methode AGM : contraction avec minimalite

---

## Phase 11 : Contre-Argumentation

**4 strategies** deployees :

| Strategie | Cible | Force |
|-----------|-------|-------|
| Reductio ad absurdum | arg_c1 | 88% |
| Contre-exemple | arg_p3 | 91% |
| Distinction | arg_c2 | 84% |
| Concession | arg_p4 | 79% |

Le contre-exemple allemand est le plus fort (91%)

---

## Phase 12 : Debat — Protocole Walton-Krabbe

**3 rounds** de debat structure :

| Round | Proponent | Opposant | Vainqueur |
|-------|-----------|----------|-----------|
| 1 | arg_c1 | reductio | **Opposant** |
| 2 | arg_p3 | contre-exemple | **Opposant** |
| 3 | arg_c2 | distinction | Nul |

Protocole : PPD (Persuasion Dialogue Protocol)
Point tournant : round 1 reductio

---

## Phase 13 : Gouvernance Democratique

**3 methodes de vote** unanimes :

| Methode | Gagnant | Consensus |
|---------|---------|-----------|
| Majorite | Liberte regulee | 67% |
| Borda | Liberte regulee | 78% |
| Condorcet | Liberte regulee | 72% |

**Verdict** : Tous les votants preferent la proposition "liberte regulee"

---

## Phase 14 : Synthese Narrative

**Integration des 16 phases** precedentes :

> "L'analyse spectaculaire de doc_A revele une structure argumentative a 8 arguments...
> La logique propositionnelle valide 3/5 formules mais trouve le lien causal non supporte...
> 4 sophismes detectes sur 3 familles...
> Le Dung rejette arg_c1 en semant grounded...
> Le JTMS demontre 2 cascades de retraction...
> La gouvernance vote unanimement pour la liberte regulee."

---

## 5 Scenarios Pedagogiques

| Scenario | Theme | Phases cibles |
|----------|-------|--------------|
| Politique | Loi logement | Extraction, sophismes, gouvernance |
| Scientifique | Climat | Logique formelle, Dung |
| Media | Liberte expression | Qualite, taxonomie |
| Fact-check | Retraites | ATMS, JTMS |
| Philosophie | Tramway | Contre-args, debat |

Tous originaux — aucun extrait du corpus chiffre

---

## Scenario : Politique

**"Loi sur le Logement Abordable"**

- 7 arguments extraits
- Ad hominem (87%) + pente glissante (82%)
- Appel a l'autorite (expert)
- Faux dilemme : "marche libre ou justice sociale"

**Enseignement** : Comment identifier les sophismes dans un debat politique reel

---

## Scenario : Science

**"Le changement climatique : mythe ou realite ?"**

- 6 arguments extraits
- Formalisation PL : Emissions → Rechauffement (valide)
- FOL : ∀x(CO2(x) → Temperature(x+Δ))
- Dung : contre-argument reductio sur l'inaction

**Enseignement** : Logique formelle appliquee a la desinformation

---

## Scenario : Media

**"La liberte d'expression a-t-elle des limites ?"**

- 5 arguments extraits
- Qualite : 0.72 a 0.88 (variance)
- 3 familles de sophismes
- Argument nuance (ni pour ni contre)

**Enseignement** : Evaluation de la qualite argumentaire dans un editorial

---

## Scenario : Fact-Checking

**"Les retraites seront-elles supprimees en 2027 ?"**

- 4 hypotheses ATMS
- JTMS : 2 cascades de retraction
- Modal S5 : "necessairement faux" pour la suppression
- Verdict : FAUX (reduction, pas suppression)

**Enseignement** : Maintenance de verite appliquee au fact-checking

---

## Scenario : Philosophie

**"Le probleme du tramway"**

- 5 arguments (utilitariste, deontologique, agentivite)
- 3 strategies de contre-argumentation
- Debat : utilitarisme vs deontologie
- Gouvernance : vote sur la decision morale

**Enseignement** : Ethique computationnelle et dilemmes moraux

---

## Sprint 4→5 Progression

**Convergence fix** : le pipeline passe de 5 tours (exit premature) a **12 tours complets** :

| Metrique | Sprint 4 | Sprint 5 | Delta |
|----------|----------|----------|-------|
| Tours total | 5 | **12** | +140% |
| Duree corpus A | 383s | 139s | **-64%** |
| Agents actifs | 3 | **5** | Formal + Quality |
| Croyances JTMS | 0 | **94** | bridge wire |
| Hook chain | 0/6 | **6/6** | Dung, Modal, ASPIC, AGM, PL/FOL, JTMS |
| ParserExceptions | 159 → 0 | **0** | maintenu |

**6 dimensions auparavant vides, maintenant peuplees** par post-phase hooks (Dung, Modal, ASPIC+, AGM, PL/FOL coordonne, JTMS sync).

---

## Comparaison 3-Voies — Detection de Sophismes

**Methode** : 3 approches de detection sur corpus reel (IDs opaques, 18 docs) :

| Dimension | 0-shot brut | 0-shot + taxonomie | Sub-workflow guide |
|-----------|-------------|--------------------|--------------------|
| Sophismes uniques | 12 | 18 | **23 types** |
| Couverture taxonomie | 4/8 familles | 6/8 familles | **8/8 familles** |
| Confiance moyenne | 0.65 | 0.74 | **0.82** |
| Leaf-level tagging | 35% | 58% | **80%+** |
| Faux positifs (estime) | ~20% | ~12% | **<8%** |

**Resultat** : le sub-workflow guide (Phase 1 wide-net → Phase 2 parallel deepening → Phase 3 parent harness) produit un spectre **2x plus large** que le 0-shot, avec une taxonomie complete et un leaf-tagging >=80%.

---

## Constitution KB — Profondeur par Argument

**Base de connaissances** peuplee par 6 post-phase hooks (corpus_dense_A) :

| Couche formelle | Champs peuple | Volume |
|-----------------|---------------|--------|
| Propositionnelle | `atomic_propositions` | signatures par argument |
| Premier ordre | `fol_shared_signature` | predicats partagees intra-corpus |
| Modale S5 | `modal_analysis_results` | formules par argument |
| Dung | `dung_frameworks` | extensions grounded/preferred/stable |
| ASPIC+ | `aspic_results` | arbres d'attaque structures |
| AGM | `belief_revision_results` | contractions avec minimalite |
| JTMS | `jtms_beliefs` | **94 croyances** + cascades retraction |

**Architecture 2-pass** : Pass 1 extrait signature/atoms du texte complet → Pass 2 genere formules exclusives par argument (convergence inter-arguments via `UnifiedAnalysisState`).

---

## Performance

**Pipeline spectacular** (corpus_dense_A, Sprint 5) :

| Metrique | Valeur |
|----------|--------|
| Phases | 17/17 completees |
| Tours | 12 (3 phases completes) |
| Duree totale | ~139 secondes |
| Croyances JTMS | **94** |
| Sophismes (18 docs) | 23 types, 8/8 familles |
| Extensions Dung | grounded + preferred + stable |
| Agents specialises | 5 actifs (PM, Extract, Formal, Quality, Informal) |
| Tests | 2845+ passes, 0 regression |

---

## Discourse Pattern Mining

**18 documents** analyses via spectacular workflow sur corpus reel (IDs opaques) :

| Metrique | Valeur | Description |
|----------|--------|-------------|
| Documents | 18 | extraits < 15K chars |
| Sophismes uniques | 23 types | spectre marginal 0.03–0.21 |
| Sophisme dominant | Illusion de regroupement | 21% des unites |
| Co-occurrences top | Lift 18.0 (6 paires) | perfect co-occurrence |
| Dung : args/attaques | 8.0 / 3.0 | densite 5.4% |
| JTMS : croyances | 38.0 | retraction 7.9% |
| Cross-coverage | Jtms_Retraction 100% | toutes fallacies → JTMS signal |

_Pipeline_ : Privacy → Batch → Aggregator → Report → Enrichment

---

## What We Discovered — Corpus Patterns

**Insight 1** : `Illusion de regroupement` est le sophisme le plus frequent (21%)
→ Co-occurre avec 5 autres types (Populisme, Pseudorationalisme, Souffle court, Faisceau de preuves, Mauvaise etiquetage) — hub central du reseau

**Insight 2** : 6 paires de sophismes ont un **lift de 18** (perfect co-occurrence)
→ Acte de foi + Coup de pouce + Misogynie forment un triplet joint
→ Haptique + Lancer de soulier = paire specifique

**Insight 3** : JTMS retraction = 100% cross-coverage avec les detections informelles
→ Chaque detection de sophisme declenche un signal formel JTMS
→ FOL et Dung restent a 0% (formules valides, pas d'attaques Dung)

_Rapport complet_ : `docs/reports/discourse_patterns.md`
_Visualisations_ : `docs/reports/discourse_patterns/*.svg`

---

## DeepSynthesis vs LLM 0-Shot

**Comparaison qualitative** : pipeline vs appel direct gpt-5-mini (corpus_dense_A) :

| Dimension | Pipeline SCDA | LLM 0-shot |
|-----------|---------------|------------|
| Axiomes FOL solver-grounded | **Oui** | Non |
| Revision AGM des croyances | **Oui** | Non |
| Paralleles intertextuels | **Template** | Non |
| Citations nommees | 1 | **12** |
| Sophismes nommes | 0 | **4** |
| Volume (mots) | 210 | **527** |

**Verdict** : le pipeline produit des **insights qualitatifs inaccessibles au 0-shot** (solver-grounded, AGM, cross-text), mais le 0-shot reste superieur en extraction brute. Root cause : instruction tuning agents (en cours, #595).

---

## Tests & Qualite

**Strategie de test** :

- **2845+ tests** passes, 0 regression
- **Couverture** : 7 modules >80%
- **Sprint 5** : 50+ nouveaux tests (convergence, idempotency, JPype warmup)
- **CI** : GitHub Actions (lint mypy strict + automated-tests)
- **Markers** : 50+ markers pytest (requires_api, slow, jpype, ...)

**Hardening realise** (Sprint 4-5) :

- mypy strict mode sur orchestration core
- ID-based tracking (arg_id, target_arg_id, resolved_arg_id)
- Post-phase hooks avec 38 tests de verification
- JPype warmup synchrone (elimine 20% timeouts)

---

## Limitations

**Honetesse sur les points faibles** :

- **Tweety FOL** : Les constantes doivent etre pre-definies (pas de decouverte dynamique)
- **Cout LLM** : ~$0.05-0.15 par analyse complete
- **Biais de detection** : Les modeles neuronaux sont entraines sur l'anglais
- **JTMS** : Les cascades de retraction peuvent etre incompletes sur des texts tres longs
- **Langue** : Support optimal en anglais, partiel en francais
- **ATMS** : Explosion combinatoire sur >10 hypotheses

---

## Travaux Futurs — Roadmap Democratech

**Vision long terme** :

1. **Discourse Pattern Mining** — Signatures quantitatives sur corpus
2. **Enrichissement iteratif** — Cycle vertueux dataset → analyse → rapport
3. **Mobile UI** — Interface React Native pour grand public
4. **API publique** — Analyse argumentaire en temps reel
5. **Collaboration** — Multi-utilisateurs avec debat en direct

**Issue #78** : Roadmap complete post-integration

---

## Conclusion

- **17 phases** d'analyse couvrant extraction → synthese
- **Multi-agents** : Sherlock, Watson, JTMS, Dung, ATMS, governance
- **Formel + connexionniste** : Meilleur des deux mondes
- **Pedagogique** : 5 scenarios, notebook Jupyter, slide deck
- **Open source** : Architecture extensible Lego

**Merci ! Questions ?**

---

## Architecture Lego — Vue d'ensemble

```
┌─────────────────────────────────────┐
│        CapabilityRegistry           │
│  (agents, plugins, services)        │
├─────────────────────────────────────┤
│  AgentFactory → BaseAgent (SK)      │
│  ├── Sherlock, Watson, Moriarty     │
│  ├── FOL, Modal, Propositional      │
│  ├── Counter-Argument, Debate       │
│  └── Quality, Fallacy, Governance   │
├─────────────────────────────────────┤
│  WorkflowDSL → UnifiedPipeline      │
│  ├── light (5 phases)               │
│  ├── standard (10 phases)           │
│  └── spectacular (17 phases)        │
├─────────────────────────────────────┤
│  Tweety Bridge (Java/JPype)         │
│  └── 12 ranking reasoners           │
└─────────────────────────────────────┘
```
