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
| **Hiérarchique** | historique | ✅ intégré | `--mode hierarchical` (livré #890) | — |

---

## B. Orchestrateurs pré-Registry (axe cleanup — décision user R313)

| Morceau | Type | Statut | Note |
|---------|------|--------|------|
| RealLLMOrchestrator (125 LOC) | obsolète | ❌ retiré (#887) | Shim `NotImplementedError` — UnifiedPipeline le remplace |
| LogiqueComplexeOrchestrator (109 LOC) | obsolète | ❌ retiré (#887) | Stub mock hardcodé — FOL/Tweety via Registry |
| ConversationOrchestrator (1045 LOC) | historique | 🔄 recyclé | **Baseline sélectionnable** — modes déterministes sans LLM (demo/trace/enhanced/micro) |
| CluedoOrchestrator base (489 LOC) | historique | 🔄 recyclé | **Baseline sélectionnable** — comparaison 2-agent vs 3-agent (Extended) |

> **Décision user (R313)** : seuls les 2 littéralement vides (real_llm shim + logique_complexe stub) sont retirés.
> Les 2 non-vides (ConversationOrchestrator + CluedoOrchestrator base) sont **recyclés comme baselines comparables**.
> Voir PR #890 (réactivation hiérarchique) et PR #891 (harness comparaison 8 modes).

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

## F. NORTH-STAR — translateurs formels + comparaison multi-backends (R606, post-merge #1438/#1439)

> Mise à jour 2026-07-11 (po-2025, base `994baf93`). Les mécanismes NORTH-STAR
> ci-dessous sont **complets côté code et sélectionnables** via le pipeline. Le
> seul travail restant = le **run corpus réel multi-axes (ATT-3)**, gated sur
> décision user — marqué OUVERT, PAS coché (anti-pendule : ne pas déclarer fait
> ce qui ne l'est pas).

### F.1 Translateurs texte→structuré (5/5 formalismes)

Chaque formalisme a un handler `_invoke_*` qui traduit le texte d'entrée en
théorie structurée consommée par le gate `evaluated`. Tous registered et
sélectionnables via le `CapabilityRegistry`.

| Formalisme | Capability | Handler (`invoke_callables.py`) | Livré |
|-----------|-----------|---------------------------------|-------|
| Bipolar AF | `bipolar_argumentation` | `_invoke_bipolar` (l.3064) | #1422 (TR-1) |
| ABA | `aba_reasoning` | `_invoke_aba` (l.3111) | #1422 (TR-1) |
| ASPIC+ | `aspic_plus_reasoning` | `_invoke_aspic` (l.3217) | #1427 (TR-2) |
| SetAF | `setaf_reasoning` | `_invoke_setaf` (l.3620) | #1428 (TR-2) |
| Weighted AF | `weighted_argumentation` | `_invoke_weighted` (l.3670) | #1431 (TR-2) |

Pointeurs vérifiés `git grep` : `registry_setup.py:765,772,784,822,828`.

**Nuance honnête (code vs corpus, #1442)** : les 5 translateurs sont **codés ET
capables d'extraction génuine** — vérifié firsthand (probe scratchpad, 2026-07-12) :
SetAF extrait bien des attaques collectives (joint attack de 4 attaquants sur un
extrait de corpus_A + `{B,C}→A` sur texte synthétique), et weighted dérive des
poids **variés dérivés du texte** (0.95 « overwhelming evidence » vs 0.2 « weakly »,
pas un poids uniforme). Les validateurs `_validate_setaf_attacks` /
`_validate_weighted_attacks` et le wiring (handlers → translateurs → gate) sont
couverts par 75 tests DI JVM/LLM-free (`test_structured_arg_translator.py`).

Cependant, le **run ATT-3** (3 corpus politiques, jugé première main) a obtenu
`status=absent_no_translator, degraded=true` pour SetAF et weighted — alors que
bipolaire/ABA/ASPIC+ passaient `evaluated`. Le translateur étant non-déterministe
(appel LLM), cet écart est **honnêtement déclaratif, pas un bug du translateur** :
le LLM n'a pas proposé de structure canonique valide sur l'inventaire de ce run
précis. Un re-run peut flipper vers `evaluated` (le probe sur corpus_A retourne
non-vide). Anti-théâtre #1019 : on ne force JAMAIS un `evaluated` sur entrée
synthétique — le drapeau `degraded` reste le signal honnête quand l'extraction
LLM revient vide.

### F.2 Axes de comparaison multi-backends (3/3)

Chaque axe compare plusieurs backends sur le même input et surface les
désaccords **verbatim, jamais auto-réconciliés** (anti-théâtre #1019). Un
backend indisponible = `available=False` fail-loud, jamais omis.

| Axe | Comparateur | Backends | Livré |
|-----|-------------|----------|-------|
| FOL | `compare_fol_backends` (`fol_handler.py:963`) | EProver / Prover9 / Mace4 | pré-existant |
| Dung | `_compare_dung_backends` (`invoke_callables.py:6847`) | Tweety / student (`abs_arg_dung`) | #1432/#1434/#1436 (I5 #1430) |
| Sophism | `compare_sophism_backends` (`neuro_symbolic_arbitrator.py:526`, SYNC) | neural / neuro-symbolic (Walton CQ) | #1433/#1435 (I1 #1429) |

### F.3 Harness unifié + capability pipeline-sélectionnable

`compare_all_axes` (`invoke_callables.py:7186`) route les 3 axes depuis un
**seul point** : routeur + agrégateur de shape uniforme
`{available, agreement, disagreements, backends, timings_ms}`, **zéro
ré-implémentation** (chaque axe garde sa shape d'entrée native).

Exposé comme **capability pipeline-sélectionnable** `multi_axis_compare` via le
handler `_invoke_multi_axis_compare` (`invoke_callables.py:7333`), registered
`multi_axis_compare_service` (`registry_setup.py:470`). Dung dérivé de l'amont
**seulement si le caller opte pour l'axe** (selectable, not imposed) ; default
honest-absent `agreement=None` (jamais un accord fabriqué). Mirrors le wiring
`dung_mode=compare` de `_invoke_dung_extensions` (`invoke_callables.py:6478`,
I5 #1434).

### F.4 Reste ouvert (ATT-3)

Le **run corpus réel multi-axes** (data feeding terminal) n'est PAS fait —
gated sur feu vert user, exécution ai-01-local (artefacts nominatifs,
non-délégeable). Honnêtement laissé ouvert.

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
| 8 | **Mode hiérarchique** | 3e mode comparable | ~~L~~ ✅ livré (#890) | 392 tests, bridge B4 |

**Séquence recommandée** : tracks 1-3 (1 session) → tracks 4-6 (1-2 sessions) → track 8 (3 sessions, si GO confirmé).

---

## À valider par l'utilisateur

1. **Ordre de priorité** : les tracks 1-3 (effort S, valeur immédiate) sont-elles les premières à câbler ? → **ACTÉ R316** : tracks 1+3 en design (#894 merged), impl en cours.
2. **Critère obsolète** : décision user R313 — seuls les 2 vides sont retirés (#887 merged). Les 2 non-vides sont recyclés. **RÉSOLU.**
3. **Bias candidat** : en cas de doute, le morceau est classé « candidat » (règle user). Ajuster ? → **TOUJOURS EN VIGUEUR.**
