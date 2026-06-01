# Audit A-17: Projet Custom -- CaseAI / Moriarty Cluedo

**Issue**: #778 (A-17) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthese en 1 phrase

Le projet etudiant `CaseAI/` (etienne.senigout, pierre.braud, SUIVI 50%, projet Custom) est un **cas hybride** -- le frontend Phaser.js (17 fichiers, jeu Cluedo medieval avec cartes/plateau/personnages) est **completement standalone** sans aucun pont API vers le backend, tandis que le backend `MoriartyInterrogatorAgent` + `CluedoDataset` (634 LOC) + le workflow 3 agents Sherlock-Watson-Moriarty + `PermissionManager` + `CluedoOracleState` (1708 LOC) + `PhaseDExtensions` sont **pleinement integres** dans le pipeline unifie via le mode orchestration `cluedo` selectionne par `unified_pipeline.py`.

**Verdict**: :yellow_circle: **INTEGRE partiellement (backend complet, frontend orphelin)** -- le backend est lun des plus profondement cables du systeme (mode orchestration dedie), mais le frontend Phaser.js na aucune connexion API. Le repertoire racine `CaseAI/` est sanctuarise (reference pedagogique conservee).

---

## 1. Cadrage R281c -- 4 etapes

### 1.1 Localiser la version consolidee

**Cas particulier** : le projet est un **Custom** (pas un sujet numerote standard). Le frontend est dans `CaseAI/`, le backend a ete integre dans `argumentation_analysis/`.

| Fichier consolide | LOC approx | Role | Origine |
| --- | --- | --- | --- |
| `agents/core/oracle/oracle_base_agent.py` | ~200 | `OracleBaseAgent(ChatCompletionAgent)` -- base abstraite agents Oracle | Nouveau (professeur) |
| `agents/core/oracle/moriarty_interrogator_agent.py` | ~300 | `MoriartyInterrogatorAgent(OracleBaseAgent)` -- agent Moriarty avec sldoisement strategique | Etudiant + enrichissement |
| `agents/core/oracle/cluedo_dataset.py` | ~634 | `CluedoDataset` -- 20 suspects/armes/lieux, distributions cartes, resolution automatique | Etudiant + enrichissement |
| `core/cluedo_oracle_state.py` | ~1708 | `CluedoOracleState` -- etat complet du jeu (hypotheses, revelations, phases, permissions) | Nouveau (professeur) |
| `agents/core/oracle/permission_manager.py` | ~250 | `PermissionManager` -- ACL pour revelations, queries, phases | Nouveau |
| `agents/core/oracle/hypo_tracker.py` | ~150 | `HypoTracker` -- tracking hypotheses et deductions | Nouveau |
| `agents/core/oracle/phase_d_extensions.py` | ~200 | `PhaseDExtensions` -- extensions narratif Phase D | Nouveau |
| `pipelines/orchestration/cluedo_orchestrator.py` | ~400 | `CluedoOrchestrator` -- orchestration 3 agents (Sherlock-Watson-Moriarty) | Nouveau |
| `orchestration/unified_pipeline.py` | ~10 | Selection mode `cluedo` -> `CluedoOrchestrator` | Nouveau |

**Frontend** (reste dans `CaseAI/`) :
- `game.js` -- Phaser.js Cluedo game (medieval theme)
- `index.html` -- Page HTML principale
- `back.js` -- Slack bot backend
- `smithy_map.js` -- Configuration carte/plateau
- 13 autres fichiers (assets, config, themes)

### 1.2 Preservation fonctionnelle

| Fonctionnalite etudiante | Preservee ? | Ou | Notes |
| --- | --- | --- | --- |
| Moriarty agent (strategic lying) | :white_check_mark: Superieur | `moriarty_interrogator_agent.py` | Enrichi avec sldoisement strategique |
| Cluedo dataset (20 elements x3) | :white_check_mark: Identique | `cluedo_dataset.py` | 634 LOC, 20 suspects/armes/lieux |
| Card distribution logic | :white_check_mark: Identique | `cluedo_dataset.py` | Distribution aleatoire + verification |
| Automatic resolution | :white_check_mark: Identique | `cluedo_dataset.py` | Verifie solution vs hypotheses |
| Phaser.js Cluedo game | :x: Orphelin | `CaseAI/game.js` | Aucun pont API |
| Medieval theme (assets) | :x: Orphelin | `CaseAI/assets/` | Cartes, sprites, UI |
| Slack bot (back.js) | :x: Orphelin | `CaseAI/back.js` | Backend Slack standalone |
| Sherlock-Watson-Moriarty workflow | :white_check_mark: Superieur | `cluedo_orchestrator.py` | 3 agents, tours structure, phases |
| Permission/ACL system | :white_check_mark: Superieur | `permission_manager.py` | Revelations, queries, phases |
| Phase D narrative extensions | :white_check_mark: Superieur | `phase_d_extensions.py` | Extensions narratifs |
| Oracle state management | :white_check_mark: Superieur | `cluedo_oracle_state.py` | 1708 LOC, etat complet |
| Mode orchestration dedie | :white_check_mark: Superieur | `unified_pipeline.py` | `mode="cluedo"` -> CluedoOrchestrator |
| Hypothesis tracking | :white_check_mark: Superieur | `hypo_tracker.py` | Tracking deductions |
| API bridge frontend-backend | :x: Non implante | -- | Zero connexion entre Phaser et pipeline |

**Score de preservation**: 9/14 fonctionnalites preservees ou superieures (64%). Les 5 perdues sont toutes cote frontend (Phaser.js + Slack bot). Le backend est le plus profondement cable du systeme.

### 1.3 Dilutions / Regressions

#### Dilution 1: Frontend Phaser.js completement orphelin (zero API bridge)

**Localisation**: `CaseAI/` -- 17 fichiers Phaser.js formant un jeu Cluedo complet (medieval theme, cartes, plateau, personnages) mais sans aucune connexion HTTP/WebSocket vers le backend pipeline.
**Impact**: HIGH -- le jeu frontend est jouable en standalone mais ne beneficie daucune intelligence du pipeline (pas danalyse argumentaire, pas dagent Moriarty, pas de resolution automatique).
**Assessment**: Le frontend est un projet jeu video complet, pas une UI danalyse. Labsence de pont API est un gap architectural, pas un bug. Connecter les deux necessiterait une API REST/WebSocket significative.
**Fix-intent**: `fix(a-17): add API bridge between Phaser.js Cluedo frontend and Moriarty pipeline`

#### Dilution 2: Slack bot (back.js) non integre

**Localisation**: `CaseAI/back.js` -- backend Slack bot pour interagir avec le jeu via Slack.
**Impact**: LOW -- le Slack bot etait un canal dinteraction alternatif, pas une fonctionnalite coeur.
**Assessment**: Le pipeline offre des canaux superieurs (API REST, MCP, CLI). Le Slack bot est obsolete.

#### Pas dautre dilution majeure

Le backend est exceptionnellement bien integre -- cest le **seul projet etudiant** qui a un **mode orchestration dedie** dans `unified_pipeline.py`. Le CluedoOrchestrator gere un workflow 3 agents complet avec phases, permissions, et tracking.

### 1.4 Statut du repertoire racine `CaseAI/`

**Verdict**: :green_circle: **Sanctuarise -- reference pedagogique conservee** (mandate R300)

- **0 import live Python** -- aucun `from CaseAI` dans le codebase consolide
- **Frontend Phaser.js** completement standalone
- **Slack bot** completement standalone
- **SUIVI** : 50% -- "Custom" (accurate -- backend integre, frontend orphelin)
- **Pas de sujet spec numerote** -- projet Custom

---

## 2. Matrice des capabilities

| Capability | Module consolide | Statut |
| --- | --- | --- |
| Moriarty agent (strategic lying) | `agents/core/oracle/moriarty_interrogator_agent.py` | :white_check_mark: Superieur |
| Cluedo dataset (20x3) | `agents/core/oracle/cluedo_dataset.py` | :white_check_mark: Identique |
| Card distribution + resolution | `agents/core/oracle/cluedo_dataset.py` | :white_check_mark: Identique |
| 3-agent workflow (S-W-M) | `pipelines/orchestration/cluedo_orchestrator.py` | :white_check_mark: Superieur |
| Permission/ACL system | `agents/core/oracle/permission_manager.py` | :white_check_mark: Superieur |
| Oracle state (1708 LOC) | `core/cluedo_oracle_state.py` | :white_check_mark: Superieur |
| Mode orchestration dedie | `orchestration/unified_pipeline.py` | :white_check_mark: Superieur |
| Phase D extensions | `agents/core/oracle/phase_d_extensions.py` | :white_check_mark: Superieur |
| Hypothesis tracking | `agents/core/oracle/hypo_tracker.py` | :white_check_mark: Superieur |
| Phaser.js Cluedo game | `CaseAI/game.js` | :x: Orphelin |
| API bridge frontend-backend | AUCUN | :x: Non implante |

---

## 3. Cartographie des connections

``text
CaseAI/                                    argumentation_analysis/
+-- game.js (Phaser.js Cluedo) -------- :warning: ORPHELIN (zero API bridge)
+-- back.js (Slack bot) ---------------- :warning: ORPHELIN
+-- smithy_map.js (map config) --------- :warning: ORPHELIN
+-- assets/ (medieval theme) ----------- :warning: ORPHELIN
+-- index.html ------------------------- :warning: ORPHELIN

                                           BACKEND (pleinement integre):
                                           +-- agents/core/oracle/
                                           |   +-- oracle_base_agent.py (OracleBaseAgent ABC)
                                           |   +-- moriarty_interrogator_agent.py (Moriarty agent)
                                           |   +-- cluedo_dataset.py (634 LOC, 20x3 elements)
                                           |   +-- permission_manager.py (ACL system)
                                           |   +-- hypo_tracker.py (hypothesis tracking)
                                           |   +-- phase_d_extensions.py (narrative extensions)
                                           +-- core/cluedo_oracle_state.py (1708 LOC state)
                                           +-- pipelines/orchestration/cluedo_orchestrator.py
                                           |   (3-agent S-W-M workflow)
                                           +-- orchestration/unified_pipeline.py
                                               (mode="cluedo" -> CluedoOrchestrator)

                                           Utilisateurs:
                                           +-- examples/ (Cluedo demo scripts)
                                           +-- tests/ (oracle test suite)
``

---

## 4. Fix-intents

| # | Issue proposee | Priorite | Action |
| --- | --- | --- | --- |
| F1 | `fix(a-17): add API bridge between Phaser.js Cluedo frontend and Moriarty pipeline` | **LOW** | Creer endpoints REST/WebSocket pour connecter le jeu Phaser au pipeline |
| F2 | `fix(a-17): document CaseAI/ as standalone frontend reference` | **LOW** | Ajouter README expliquant le gap architectural frontend/backend |

---

## 5. Conclusion

Le projet CaseAI/Moriarty est un **cas hybride unique** -- le backend est le **plus profondement integre** de tous les audits :yellow_circle: avec un mode orchestration dedie (`mode="cluedo"`), un workflow 3 agents, 1708 LOC detat, des permissions ACL, et des extensions narratifs. Le frontend Phaser.js (17 fichiers, jeu medieval complet) est **completement orphelin** -- aucun pont API.

**Contraste** : A-14 (dual-serveur fragmente), A-15 (backend cable bugs critiques), A-17 (backend excellent, frontend orphelin). Le backend de A-17 est le plus impressionnant des audits interface.

**SUIVI 50%** est accurate -- le backend est integre mais le frontend ne lest pas.

**Cas dusage soutenance** : excellent pour la partie backend -- le workflow Sherlock-Watson-Moriarty est une demonstration forte du systeme multi-agents. Le jeu Phaser.js peut etre montre independamment comme UX alternative, mais sans connection au pipeline.

**Le repertoire `CaseAI/` est sanctuarise** (mandate R300) -- conserve comme reference pedagogique + frontend standalone.

---

## 6. Fichiers sources

- `argumentation_analysis/agents/core/oracle/moriarty_interrogator_agent.py` -- Moriarty agent
- `argumentation_analysis/agents/core/oracle/cluedo_dataset.py` -- Cluedo dataset (634 LOC)
- `argumentation_analysis/core/cluedo_oracle_state.py` -- Oracle state (1708 LOC)
- `argumentation_analysis/agents/core/oracle/permission_manager.py` -- Permission/ACL system
- `argumentation_analysis/agents/core/oracle/hypo_tracker.py` -- Hypothesis tracking
- `argumentation_analysis/agents/core/oracle/phase_d_extensions.py` -- Phase D extensions
- `argumentation_analysis/pipelines/orchestration/cluedo_orchestrator.py` -- 3-agent orchestrator
- `argumentation_analysis/orchestration/unified_pipeline.py` -- Mode selection
- `CaseAI/game.js` -- Phaser.js Cluedo game (orphelin)
- `CaseAI/back.js` -- Slack bot (orphelin)

## A valider par lutilisateur

RAS -- verdict clair (backend excellent, frontend orphelin). SUIVI 50% accurate.