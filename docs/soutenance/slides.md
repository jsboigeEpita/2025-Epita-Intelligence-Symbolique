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

## Performance

**Pipeline spectacular** (golden fixture doc_A) :

| Metrique | Valeur |
|----------|--------|
| Phases | 17/17 completees |
| Duree totale | ~45 secondes |
| Arguments extraits | 8 |
| Sophismes detectes | 4 |
| Formules formelles | 16 |
| Croyances JTMS | 10 |
| Methodes de vote | 3 |

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

## Tests & Qualite

**Strategie de test** :

- **2845+ tests** passes
- **Couverture** : 7 modules >80%
- **Tests de regression** : 75 tests golden (spectacular)
- **Markers** : 41 markers pytest (requires_api, slow, jpype, ...)
- **CI** : GitHub Actions (lint + automated-tests)

**Hardening en cours** (Epic A) :

- Property-based tests (hypothesis)
- LLM response caching (DiskCache)
- mypy strict mode
- Coverage audit

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
