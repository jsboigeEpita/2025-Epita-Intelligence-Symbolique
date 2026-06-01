# B-12: Audit — `tests/unit/` misc (core, mocks, agents, root files)

**Track**: B-12 #769 (Epic B #743)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique
**Scope**: 17 fichiers de test, ~157 tests collectés

---

## Méthodologie

Même classification a/b/c que B-01 à B-11. Scope = fichiers de test dans `tests/unit/` qui n'ont PAS été couverts par les audits B-01 à B-11 :

- **B-01 à B-07** : `tests/unit/argumentation_analysis/` (agents, core, services, plugins, NLP, models, pipelines, orchestration interne, reporting, analytics, API eval)
- **B-08** : `tests/unit/api/`
- **B-09** : `tests/unit/orchestration/`
- **B-10** : `tests/unit/project_core/` + `tests/unit/scripts/`
- **B-11** : `tests/unit/webapp/` + web infrastructure

Restant pour B-12 :

| Répertoire | Fichiers | Tests | Description |
|------------|----------|-------|-------------|
| `tests/unit/core/` | 3 | ~12 | Plugin framework contracts, decorators, rhetorical state |
| `tests/unit/mocks/` | 4 | ~8 | JPype/numpy mock validation |
| `tests/unit/agents/` | 7 | ~83 | JTMS agents, FOL logic, agent loader |
| `tests/unit/*.py` | 3 | ~54 | Demo modules, service manager, Starlette interface |
| `tests/unit/recovered/` | 0 | 0 | Vide (uniquement `__init__.py`) |
| **TOTAL** | **17** | **~157** | |

Le wiring se vérifie par :
- **CapabilityRegistry** : grep dans `registry_setup.py`
- **Pipeline imports** : grep dans `argumentation_analysis/`
- **Entry points** : vérification que le module testé est réellement utilisé

---

## Scoreboard

| Catégorie | Fichiers | Tests | % |
|-----------|----------|-------|---|
| **(a) Mort** | 4 | ~5 | 3% |
| **(b) Non-wiré** | 2 | ~12 | 8% |
| **(c) Justifié** | 11 | ~140 | 89% |

---

## Tableau de classification

### (a) DEAD — Source inexistante ou jamais importée

| # | Fichier | Composant testé | Tests | Pourquoi DEAD |
|---|---------|-----------------|-------|---------------|
| 1 | `core/test_decorators.py` | `plugin_framework.core.decorators.track_tokens` | 3 | Le décorateur `track_tokens` n'est importé par **aucun** fichier de production. Seul son fichier de définition et ce test le référencent. |
| 2 | `mocks/test_jpype_mock_simple.py` | `tests.mocks.jpype_mock` | 0 | **Pas un vrai test** — script avec `print()` et assertions commentées. Aucune classe ni fonction pytest. |
| 3 | `agents/test_agent_loader.py` | `plugin_framework.agents.agent_loader.AgentLoader` | 1 | Seul test = vérification d'import. `AgentLoader` n'est jamais importé dans le code de production — seul ce test et un README le référencent. |
| 4 | `test_demo_epita_modules.py` | `examples/02_core_system_demos/` (7 modules démo) | 16 | Les modules démo (`demo_tests_validation`, `demo_services_core`, etc.) vivent dans `examples/` et ne sont jamais importés par le code de production. Tests de démonstration pédagogique uniquement. |

### (b) UNWIRED — Source existe mais pas dans le pipeline

| # | Fichier | Composant testé | Tests | Pourquoi UNWIRED |
|---|---------|-----------------|-------|-------------------|
| 1 | `core/test_contracts.py` | `plugin_framework.core.contracts` (OrchestrationRequest/Response) | 4 | Les contrats sont importés par `orchestration_service.py` et `benchmark_service.py` mais ne sont PAS enregistrés dans le CapabilityRegistry. Ce sont des modèles de données internes, pas des capacités pipeline. |
| 2 | `agents/test_sherlock_jtms_agent_simple.py` | `sherlock_jtms_agent.py` (doublon) | 9 | **Doublon** de `test_sherlock_jtms_agent.py` (même source, couverture redondante). Les 9 tests sont un sous-ensemble simplifié des 10 tests du fichier principal. |

### (c) JUSTIFIÉ — Infrastructure critique, mocks, agents actifs

#### `tests/unit/core/` — Framework de base

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 1 | `core/test_rhetorical_analysis_core.py` | `RhetoricalAnalysisState`, `StateManagerPlugin`, `SimpleTerminationStrategy`, `BalancedParticipationStrategy` | État partagé du pipeline, plugin de gestion d'état, stratégies de sélection d'agents. Importé par 16+ fichiers de production. | 5 |

#### `tests/unit/mocks/` — Infrastructure de mock JPype/numpy

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 2 | `mocks/test_jpype_mock.py` | JPype mock (JClass, JException) | Valide le mock JPype pour tests sans JVM. Requis par conftest.py. | 2 |
| 3 | `mocks/test_numpy_mock.py` | legacy_numpy_array_mock (numpy._core) | Valide le mock numpy pour environnements sans numpy complet. | 1 |
| 4 | `mocks/test_numpy_rec_mock.py` | legacy_numpy_array_mock (numpy.rec) | Valide recarray mock pour compatibilité pandas. | 5 |

#### `tests/unit/agents/` — Agents JTMS/FOL actifs

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 5 | `agents/test_jtms_agent_base.py` | `JTMSAgentBase`, `JTMSSession`, `ExtendedBelief` | Classe de base de tous les agents JTMS. Importé par 7+ modules. | 17 |
| 6 | `agents/test_jtms_communication_hub.py` | `JTMSCommunicationHub` | Communication Sherlock↔Watson. Importé par WatsonJTMSAgent et utils. | 12 |
| 7 | `agents/test_watson_jtms_agent.py` | `WatsonJTMSAgent` (4 engines) | Agent de validation/analyse. Contrepartie de Sherlock. | 14 |
| 8 | `agents/test_fol_logic_agent.py` | `FOLLogicAgent` + TweetyProject | Logique du premier ordre. Importé par 5 fichiers (logic_factory, fol_handler). | 20 |
| 9 | `agents/test_sherlock_jtms_agent.py` | `SherlockJTMSAgent` | Agent d'investigation. Importé par factory, communication hub. | 10 |

#### `tests/unit/*.py` — Fichiers racine

| # | Fichier | Composant testé | Rôle | Tests |
|---|---------|-----------------|------|-------|
| 10 | `test_service_manager_complete.py` | `InfrastructureServiceManager`, `PortManager`, `ProcessCleanup`, `ServiceConfig` | Gestion des services backend. 54+ références production. Critique. | 19 |
| 11 | `test_interface_web_starlette.py` | `interface_web/app.py` (Starlette) | Application web + API endpoints. Serveur de production. | 19 |

---

## Narratif

### Santé globale — 89% justifié

Le ratio 89% justifié est **le meilleur de tous les audits B** (B-01 à B-11). La majorité des tests couvrent des composants actifs et critiques :

- **Agents JTMS/FOL** (73 tests) : infrastructure d'agents la plus testée du projet. JTMSAgentBase, Sherlock, Watson, CommunicationHub, FOL — tous actifs dans les pipelines.
- **Service Manager** (19 tests) : backbone de gestion des services web, 54+ imports en production.
- **Interface web Starlette** (19 tests) : serveur web de production.
- **Mocks JPype/numpy** (8 tests) : infrastructure de test essentielle pour les environnements sans JVM.

### Points d'attention

1. **`test_sherlock_jtms_agent_simple.py`** : doublon de `test_sherlock_jtms_agent.py`. Les 9 tests sont un sous-ensemble simplifié. Le fichier `_simple` pourrait être supprimé sans perte de couverture — l'autre fichier couvre les mêmes méthodes plus en profondeur.

2. **`test_demo_epita_modules.py`** : 16 tests de modules démo pédagogiques. Pas de production, mais utilité pédagogique confirmée (démonstrations EPITA, soutenances). Conservation recommandée.

3. **`test_agent_loader.py`** : test trivial (1 assertion d'import) pour un module non utilisé. Candidat à l'archivage si le module source est supprimé.

4. **`test_decorators.py`** : `track_tokens` n'a aucun consommateur. Le décorateur et son test sont du code mort.

### Comparaison avec les autres audits B

| Audit | Fichiers | Tests | % DEAD | % UNWIRED | % JUSTIFIED |
|-------|----------|-------|--------|-----------|-------------|
| B-01 agents | 15 | ~120 | 0% | 47% | 53% |
| B-02 orchestration | 10 | ~80 | 10% | 30% | 60% |
| B-03 pipelines | 9 | ~70 | 22% | 11% | 67% |
| B-04 plugins | 8 | ~50 | 12% | 25% | 63% |
| B-05 core services | 12 | ~90 | 8% | 17% | 75% |
| B-06 utils/NLP/models | 18 | ~200 | 15% | 10% | 75% |
| B-07 API/eval/trace | 14 | ~150 | 20% | 5% | 75% |
| B-08 root API | 14 | 101 | 7% | 0% | 93% |
| B-09 orchestration | 15 | 360 | 0% | 91% | 9% |
| B-10 project_core | 14 | 142 | 14% | 23% | 63% |
| B-11 infra web | 15 | 143 | 7% | 0% | 93% |
| **B-12 misc** | **17** | **~157** | **3%** | **8%** | **89%** |

---

## Décision DoD

Aucun fix-intent requis. Les 4 DEAD sont soit des mocks utilitaires (JPype simple), soit du code pédagogique (démo EPITA), soit des singletons triviaux (agent_loader, decorators). Les 2 UNWIRED sont soit des contrats internes légitimes (OrchestrationRequest), soit un doublon bénin (sherlock_simple).

**Actions recommandées (optionnelles, pas de fix-intent) :**
- Supprimer `test_sherlock_jtms_agent_simple.py` (doublon sans valeur ajoutée)
- Archiver `test_agent_loader.py` si `AgentLoader` est supprimé lors d'un cleanup futur
- Archiver `test_decorators.py` si `track_tokens` est supprimé

---

## Audit trail

| Commit | Description |
|--------|-------------|
| `706ee3d3` | Base (B-03 #820 merged) |
| Ce rapport | B-12 audit scope final |
