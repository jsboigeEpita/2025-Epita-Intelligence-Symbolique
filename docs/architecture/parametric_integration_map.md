# Parametric Integration Map — R311

**Date**: 2026-06-02
**Author**: Claude Code @ myia-po-2023
**Base**: `e6c7003b` (main, post-R311)
**North-star user** : intégration paramétrique maximale — chaque morceau non-obsolète devient un **paramètre sélectionnable** d'un système unifié.

---

## Cap

Le projet contient **80 capabilities, 22 workflows, 49 routes API** (vérifié R310). La majorité est câblée mais **pas encore exposée comme paramètres sélectionnables** au niveau CLI/API. Ce document classe chaque morceau et identifie les prochaines tracks d'intégration pour rendre le système véritablement paramétrique.

**Conclusion** : 8 morceaux candidats prioritaires identifiés (effort S à L). Les 4 premiers (fallacy-tier, vote-method, hidden workflows, shield-preset) sont réalisables en **2 sessions** et transforment le système d'un ensemble de chemins figés en un sélecteur paramétrique. Le mode hiérarchique (L) et les latéraux non-wired (abs_arg_dung, CaseAI) sont des tracks ultérieures.

---

## Taxonomie

- **Latéral** : logique distincte d'un projet étudiant, plugin, spécialiste, catalogue
- **Historique** : ancien orchestrateur, mode dormant, implémentation précoce
- **Obsolète** : vide/superseded sans rien à recycler

---

## A. Modes d'orchestration (axe `--mode`)

| Morceau | Type | Statut | Axe-paramètre | Effort |
|---------|------|--------|---------------|--------|
| Pipeline (`WorkflowExecutor`) | — | ✅ intégré | `--mode pipeline` | — |
| Conversational | — | ✅ intégré | `--mode conversational` | — |
| Cluedo (3-agent) | — | ✅ intégré | mode dédié | — |
| Sherlock Modern | latéral | ✅ intégré | `--mode sherlock_modern` | — |
| **Hiérarchique** | historique | 🔄 candidat | `--mode hierarchical` (ABSENT du CLI) | **L** |

---

## B. Orchestrateurs pré-Registry (axe cleanup)

| Morceau | Type | Statut | Note |
|---------|------|--------|------|
| RealLLMOrchestrator (125 LOC) | historique | ❌ obsolète | ARCHIVE — UnifiedPipeline le remplace |
| ConversationOrchestrator (1045 LOC) | historique | ❌ obsolète | ARCHIVE — 8-agent SK le remplace |
| CluedoOrchestrator base (489 LOC) | historique | ❌ obsolète | ARCHIVE — ExtendedOrchestrator le remplace |
| LogiqueComplexeOrchestrator (109 LOC) | obsolète | ❌ obsolète | REMOVE — stub mock |

---

## C. Workflows cachés (22 en catalogue, 6 seulement exposés au CLI)

| Morceau | Type | Statut | Axe-paramètre | Effort |
|---------|------|--------|---------------|--------|
| `iterative` / `quality_gated` / `jtms_dung` / `neural_symbolic` / `nl_to_logic` / `hierarchical_fallacy` | latéral | 🔄 candidat | exposer via `--list-workflows` + CLI help | **S** |
| `spectacular` (29 phases) / `comprehensive` | latéral | 🔄 candidat | axe benchmark | S |
| `formal_extended` / `formal_verification` / `formal_debate` / `belief_dynamics` / `argument_strength` | latéral | 🔄 candidat | axe profondeur chaîne formelle | S |
| **`democratech`** (`consensus_threshold`) | latéral | 🔄 candidat | param builder existe, PAS exposé CLI/API | **M** |
| **`debate_tournament`** (`max_rounds`) | latéral | 🔄 candidat | param builder existe, PAS exposé | **S** |
| `fact_check` | latéral | 🔄 candidat | — | S |

---

## D. Capabilities câblées mais non-sélectionnable

| Morceau | Type | Statut | Axe-paramètre latent | Effort |
|---------|------|--------|---------------------|--------|
| **Tiers sophisme** (neural / hierarchical / per-argument) | latéral (2.3.2) | 🔄 candidat | `--fallacy-tier {neural,hierarchical,per-argument}` | **S** |
| **7 méthodes de vote** (gouvernance) | latéral (2.1.6) | 🔄 candidat | `--vote-method {majority,borda,condorcet,...}` | **M** |
| **Solveurs formels** (EProver/Prover9/SPASS/Clingo) | latéral | 🔄 candidat | `--fol-solver` / `--modal-solver` | **M** |
| **AI Shield presets** (basic/advanced/output_only/strict) | latéral (#841) | 🔄 candidat | `--shield-preset` | **S** |
| **17 handlers Tweety** (ranking/bipolar/ABA/ASPIC/...) | latéral (Track A) | 🔄 candidat | `--formal-extension` sélecteur | **M** |
| **5 stratégies contre-argument** | latéral (2.3.3) | 🔄 candidat | `--counter-strategy` | **S** |
| Local LLM | latéral (2.3.6) | ✅ intégré | env-driven (endpoint-gated) | — |

---

## E. Latéraux non-wired

| Morceau | Type | Statut | Axe-paramètre | Effort |
|---------|------|--------|---------------|--------|
| **`abs_arg_dung/`** (lib Dung standalone) | latéral | 🔄 candidat | Own CLI/agent, 1 ref only dans tronc commun | **M** |
| **`CaseAI/`** (Slack bot frontend) | latéral | 🔄 candidat | 0 ref dans tronc commun — channel frontend isolé | **M** |
| `1_2_7_argumentation_dialogique/` | latéral | ✅ intégré | absorbé dans `debate/` agent | — |
| `speech-to-text/` | latéral | ✅ intégré | capability `speech_transcription` | — |
| `Arg_Semantic_Index/` | latéral | ✅ intégré | capability `semantic_indexing` | — |
| `3.1.5_Interface_Mobile/` | latéral | 🔄 candidat | mobile router existe, frontend pas paramétrisé | **S** |

---

## Prochaines tracks d'intégration (ordonnées par effort/valeur)

| # | Track | Axe | Effort | Valeur |
|---|-------|-----|:------:|--------|
| 1 | **Fallacy-tier selector** (`--fallacy-tier`) | Sélection profondeur détection | S | Transforme 3 chemins figés en paramètre |
| 2 | **Hidden workflows** (18/24 non exposés) | `--list-workflows` + help | S | Débloque l'accès aux 18 workflows cachés |
| 3 | **AI Shield preset** (`--shield-preset`) | Sélection niveau protection | S | 4 presets en metadata, aucun param |
| 4 | **Vote-method selector** (`--vote-method`) | Sélection méthode démocratique | M | 7 votes enterrés dans une capability |
| 5 | **Formal-solver selector** (`--fol-solver`) | Choix solveur externe | M | 4 solveurs, fallback hardcodé |
| 6 | **Democratech params** (consensus_threshold) | Paramètres workflow flagship | M | Builder existe, pas CLI |
| 7 | **abs_arg_dung + CaseAI** wiring | 2 latéraux isolés | M chacun | Élargit la surface |
| 8 | **Mode hiérarchique** | 3e mode comparable | L | 302 tests, 5 casses (scoping R311) |

**Séquence recommandée** : tracks 1-3 (1 session) → tracks 4-6 (1-2 sessions) → track 8 (3 sessions, si GO confirmé).

---

## À valider par l'utilisateur

1. **Ordre de priorité** : les tracks 1-3 (effort S, valeur immédiate) sont-elles les premières à câbler ?
2. **Critère obsolète** : `RealLLMOrchestrator`, `ConversationOrchestrator`, `CluedoOrchestrator` base, `LogiqueComplexeOrchestrator` sont classés obsolètes (B-09 #875). Confirmez-vous l'archivage/suppression ?
3. **Bias candidat** : en cas de doute, le morceau est classé « candidat » (règle user). Ajuster ?
