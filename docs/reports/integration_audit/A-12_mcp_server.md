# Audit A-12: Projet 2.5.3 — Serveur MCP Analyse Argumentative

**Issue**: #773 (A-12) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet étudiant 2.5.3 (Enguerrand Turcat, Titouan Verhille) a été soumis **directement dans le tronc commun** sous `argumentation_analysis/services/mcp_server/` (~600 LOC, 23 outils MCP), puis enrichi d'une couche V2 (13 outils additionnels : workflows, conversations, capabilities, analyse spécialisée), d'un session manager TTL, et d'un Dockerfile — le tout câblé au pipeline unifié via `setup_registry()` + `CAPABILITY_STATE_WRITERS` + 12+ workflows pré-construits.

**Verdict**: 🟢 **INTÉGRÉ fidèlement et enrichi** — aucune régression fonctionnelle. Pas de répertoire racine distinct (soumission directe dans le tronc commun).

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Cas particulier : le projet étudiant n'a **pas de répertoire racine** — il a été soumis directement dans `argumentation_analysis/services/mcp_server/`. La consolidation = enrichissement de cette même base.

| Fichier | LOC approx | Rôle | Origine |
| --- | --- | --- | --- |
| `main.py` | ~400 | `MCPService` (23 outils V1+V2) + `AppServices` container | Étudiant (V1) + enrichissement (V2) |
| `server_config.py` | ~20 | `MCPServerConfig` dataclass | Nouveau |
| `session_manager.py` | ~50 | Session manager TTL (1800s, max 100) | Nouveau |
| `tools/_serialization.py` | ~25 | `safe_serialize()` helper | Nouveau |
| `tools/workflow_tools.py` | ~60 | 3 outils V2 : list/run/get workflows | Nouveau |
| `tools/conversation_tools.py` | ~80 | 3 outils V2 : start/continue/status conversation | Nouveau |
| `tools/capability_tools.py` | ~60 | 3 outils V2 : list/invoke/summary capabilities | Nouveau |
| `tools/specialized_tools.py` | ~80 | 4 outils V2 : quality/counter/debate/governance | Nouveau |
| `Dockerfile` | ~30 | Build ARM64 + conda + jpype1 + mcp | Nouveau |
| `README.md` | ~50 | Documentation usage Docker + config | Nouveau |

### 1.2 Préservation fonctionnelle

| Fonctionnalité étudiante | Préservée ? | Où | Notes |
| --- | --- | --- | --- |
| V1 outil 1: health_check | ✅ Identique | `main.py` | |
| V1 outil 2: analyze_text | ✅ Identique | `main.py` | Mirrors POST /api/analyze |
| V1 outil 3: validate_argument | ✅ Identique | `main.py` | |
| V1 outil 4: detect_fallacies | ✅ Identique | `main.py` | |
| V1 outil 5: build_framework | ✅ Identique | `main.py` | |
| V1 outil 6: logic_graph | ✅ Identique | `main.py` | |
| V1 outil 7: create_belief_set | ✅ Identique | `main.py` | |
| V1 outil 8: execute_logic_query | ✅ Identique | `main.py` | |
| V1 outil 9: generate_logic_queries | ✅ Identique | `main.py` | |
| V1 outil 10: list_available_tools | ✅ Identique | `main.py` | |
| Transport streamable-http | ✅ Identique | `FastMCP` run() | |
| AppServices container (5 services) | ✅ Identique | `AppServices` class | LogicService, AnalysisService, etc. |
| V2 workflow tools (3) | ✅ Supérieur (nouveau) | `tools/workflow_tools.py` | Accès complet aux 12+ workflows |
| V2 conversation tools (3) | ✅ Supérieur (nouveau) | `tools/conversation_tools.py` | Sessions multi-tours avec TTL |
| V2 capability tools (3) | ✅ Supérieur (nouveau) | `tools/capability_tools.py` | Introspection registry complète |
| V2 specialized tools (4) | ✅ Supérieur (nouveau) | `tools/specialized_tools.py` | Quality, counter, debate, governance |
| Session manager | ✅ Supérieur (nouveau) | `session_manager.py` | TTL + eviction |
| Dockerfile | ✅ Supérieur (nouveau) | `Dockerfile` | ARM64 + conda + jpype1 |
| MCP Resources (URIs) | ❌ Non implémenté | — | Le sujet spec mentionnait `fallacy://taxonomy/` etc. |
| MCP Prompts | ❌ Non implémenté | — | Pas dans le scope livré |

**Score de préservation**: 18/20 fonctionnalités préservées ou supérieures (90%). Les 2 manquantes (MCP Resources, MCP Prompts) n'étaient pas dans le livrable étudiant initial — ce sont des extensions du spec sujet non implémentées.

### 1.3 Dilutions / Régressions

#### Pas de dilution

Le projet a été **soumis directement dans le tronc commun** — il n'y a pas de processus de digestion "projet étudiant → consolidé" avec perte potentielle. L'enrichissement est purement additif (V2 tools, session manager, Docker).

#### Gap mineur : MCP Resources non exposées

**Localisation**: Le sujet spec 2.5.3 (2415 lignes) définit des MCP Resources comme `fallacy://taxonomy/`, `arguments://database/`, `frameworks://dung/examples` — mais elles ne sont pas implémentées.
**Impact**: LOW — les MCP Resources permettent à un client MCP de découvrir et lire des données structurées. La fonctionnalité équivalente est accessible via les outils V2 (`list_capabilities`, `invoke_capability`).
**Assessment**: Pas une dilution — c'était dans le spec mais pas dans le livrable. L'équivalent fonctionnel est couvert par les outils existants.

#### Note : Dockerfile référence environnement non documenté

**Localisation**: `Dockerfile` référence l'environnement conda `projet-is-v2` qui ne correspond à aucun environnement documenté dans CLAUDE.md (`projet-is` ou `projet-is-roo-new`).
**Impact**: LOW — le Dockerfile est un template de déploiement. N'affecte ni le développement local ni la CI.

### 1.4 Statut du répertoire racine

**Cas particulier** : le projet 2.5.3 n'a **pas de répertoire racine**. Il a été soumis directement dans `argumentation_analysis/services/mcp_server/`. La question du sort du répertoire étudiant ne s'applique pas.

**SUIVI** : 90% — "Integre"
**Sujet doc** : `docs/projets/sujets/2.5.3_Developpement_Serveur_MCP_Analyse_Argumentative.md` (2415 lignes)

---

## 2. Matrice des capabilities

| Capability | Module consolidé | Statut |
| --- | --- | --- |
| Analyse textuelle (MCP tool) | `main.py` analyze_text | ✅ Identique |
| Validation argumentaire | `main.py` validate_argument | ✅ Identique |
| Détection sophismes | `main.py` detect_fallacies | ✅ Identique |
| Construction framework Dung | `main.py` build_framework | ✅ Identique |
| Graphe logique | `main.py` logic_graph | ✅ Identique |
| Ensemble de croyances | `main.py` create_belief_set | ✅ Identique |
| Requêtes logiques | `main.py` execute_logic_query + generate_logic_queries | ✅ Identique |
| Workflow orchestration (V2) | `tools/workflow_tools.py` | ✅ Supérieur (nouveau) |
| Conversation multi-tours (V2) | `tools/conversation_tools.py` | ✅ Supérieur (nouveau) |
| Capability introspection (V2) | `tools/capability_tools.py` | ✅ Supérieur (nouveau) |
| Analyse spécialisée (V2) | `tools/specialized_tools.py` | ✅ Supérieur (nouveau) |

---

## 3. Cartographie des connections

```text
argumentation_analysis/services/mcp_server/
├── main.py
│   ├── AppServices → services/web_api/services/* (Logic, Analysis, Validation, Fallacy, Framework)
│   ├── MCPService → FastMCP (23 tools V1+V2)
│   │   ├── V1 (10 tools): health, analyze, validate, fallacies, framework,
│   │   │   logic_graph, belief_set, query, generate_queries, list_tools
│   │   └── V2 (13 tools): workflow_tools, conversation_tools,
│   │       capability_tools, specialized_tools
│   └── initialize_project_environment() → core/bootstrap.py
│
├── tools/
│   ├── workflow_tools.py ──────────► orchestration/unified_pipeline.py
│   │   (run_unified_analysis, get_workflow_catalog)           (12+ workflows)
│   ├── conversation_tools.py ─────► orchestration/unified_pipeline.py
│   │   (CAPABILITY_STATE_WRITERS, WorkflowTurnStrategy)       (37+ state writers)
│   ├── capability_tools.py ───────► core/capability_registry.py
│   │   (find_for_capability, get_all_capabilities)           (full registry)
│   └── specialized_tools.py ──────► orchestration/registry_setup.py
│       (setup_registry → quality, counter, debate, governance)
│
├── session_manager.py ───────────── In-memory TTL sessions (1800s, max 100)
├── server_config.py ─────────────── MCPServerConfig dataclass
├── Dockerfile ───────────────────── ARM64 + conda + jpype1 + mcp
└── README.md ────────────────────── Usage documentation

Pipeline dependencies (MCP server consumes):
├── orchestration/registry_setup.py ─── 40+ invoke callables registered
├── orchestration/state_writers.py ──── 37+ capability → state writer mappings
├── orchestration/workflows.py ──────── 12+ pre-built workflows
├── core/capability_registry.py ─────── ServiceDiscovery + CapabilityRegistry
└── core/bootstrap.py ──────────────── JVM + environment initialization
```

---

## 4. Fix-intents

Aucun fix-intent nécessaire. L'intégration est complète et sans régression.

| # | Issue proposée | Priorité | Action |
| --- | --- | --- | --- |
| — | Aucune | — | Pas de DEAD, pas de capability muette, pas de dilution |

---

## 5. Conclusion

Le projet 2.5.3 est **intégralement intégré** — cas particulier de soumission directe dans le tronc commun (pas de répertoire étudiant distinct). Les 10 outils V1 sont préservés à l'identique, enrichis par 13 outils V2 (workflows, conversations, capabilities, analyse spécialisée), un session manager, un Dockerfile, et un câblage complet au pipeline unifié via `setup_registry()` (40+ invoke callables) + `CAPABILITY_STATE_WRITERS` (37+ state writers) + 12+ workflows pré-construits.

Le MCP server est la **pièce d'interface majeure** du système — il expose l'intégralité du pipeline d'analyse argumentative via le protocole MCP (23 outils), permettant à n'importe quel client MCP (Claude Desktop, IDE, script) d'interagir avec le système. C'est le canal d'accès le plus complet après l'API REST.

**Cas d'usage soutenance** : excellent candidat pour démontrer l'accessibilité du système — un client MCP peut lancer une analyse complète (run_workflow full), explorer les capabilities (list_capabilities), ou utiliser les outils spécialisés (evaluate_quality, generate_counter_argument) directement depuis Claude Desktop ou un IDE.

**Test coverage** : 6 fichiers de tests unitaires + 1 fichier d'intégration couvrant V1/V2 tools, sessions, et compatibilité.

**Pas de répertoire racine** — le projet est déjà dans le tronc commun. Le sujet spec est dans `docs/projets/sujets/`.

---

## 6. Fichiers sources

- `argumentation_analysis/services/mcp_server/main.py` — MCPService (23 tools V1+V2) + AppServices
- `argumentation_analysis/services/mcp_server/tools/` — 4 modules V2 (workflow, conversation, capability, specialized)
- `argumentation_analysis/services/mcp_server/session_manager.py` — TTL session manager
- `argumentation_analysis/services/mcp_server/server_config.py` — Configuration dataclass
- `argumentation_analysis/services/mcp_server/Dockerfile` — Docker support
- `tests/unit/services/test_mcp_server_v2/` — 6 fichiers de tests unitaires
- `docs/projets/sujets/2.5.3_Developpement_Serveur_MCP_Analyse_Argumentative.md` — Sujet spec (2415 lignes)
