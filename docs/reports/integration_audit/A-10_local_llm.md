# Audit A-10: Projet 2.3.6 — LLMs Locaux Légers

**Issue**: #759 (A-10) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet étudiant `2.3.6_local_llm/` (~460 LOC Python, 10 fichiers, auteur "Dorian Tavaud" d'après le setup) a été intégré de manière **partielle** — le consolidé remplace l'approche directe llama-cpp par un adaptateur HTTP OpenAI-compatible (multi-backend, async, ServiceDiscovery), mais le pipeline integration est minimal : aucun workflow, aucun state writer, aucune dimension de state partagé, et les fonctionnalités spécifiques de l'étudiant (prompting fallacy, extraction JSON, gestion de 9 modèles GGUF) ne sont pas migrées.

**Verdict**: 🟡 **INTÉGRÉ partiellement (infrastructure)** — l'adaptateur HTTP est architecturalement supérieur mais le câblage pipeline est incomplet. Le répertoire racine est sanctuarisé (référence pédagogique conservée).

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

Le projet étudiant a été digéré en **un composant infrastructure** plutôt qu'en un agent métier :

| Fichier consolidé | Origine étudiante | LOC approx | Rôle |
|-------------------|-------------------|------------|------|
| `services/local_llm_service.py` | Ré-architecture de `local_llm/local_llm.py` | ~113 | `LocalLLMService` — adaptateur HTTP OpenAI-compatible (async, multi-backend) |
| `orchestration/invoke_callables.py` | Nouveau | ~7 | `_invoke_local_llm` — pass-through minimal |
| `orchestration/registry_setup.py` | Nouveau | ~16 | Registration SERVICE `local_llm_service` |

**Absence notable** : pas de fichier consolidé dans `agents/core/` (pas d'agent dédié), pas de plugin SK, pas de state writer, pas de dimension de state partagé.

**CapabilityRegistry** : 1 service `local_llm_service` avec 2 capabilities : `local_llm`, `chat_completion`.

### 1.2 Préservation fonctionnelle

| Fonctionnalité étudiante | Préservée ? | Où | Notes |
|--------------------------|-------------|-----|-------|
| Chargement modèles GGUF (llama-cpp) | ✅ Supérieur (architecture) | Via HTTP → n'importe quel backend | Découplé de l'import direct |
| 9 modèles quantifiés (TinyLlama→Phi-3) | ❌ Non migré | Reste dans `2.3.6_local_llm/` | ModelEnum + MODEL_PATHS non portés |
| Multi-chargement concurrent | ❌ Non migré | Reste dans `2.3.6_local_llm/` | LocalLlm gère plusieurs modèles en dict |
| FastAPI server (fallacy detection) | ❌ Perdu (changé de rôle) | L'étudiant était serveur, le consolidé est client | Renversement architectural |
| Prompt engineering fallacy (utils.py) | ❌ Non migré | Reste dans `2.3.6_local_llm/` | Templates fallacy-specific non portés |
| Extraction JSON from output | ❌ Non migré | Reste dans `2.3.6_local_llm/` | `clean_output` + `extract_json_from_string` |
| Multi-backend (vLLM, Ollama, llama-cpp) | ✅ Supérieur | `LocalLLMService` accepte tout endpoint | Étudiant = llama-cpp seul |
| Async support (httpx) | ✅ Supérieur | `chat_completion()` async | Étudiant = synchrone |
| ServiceDiscovery integration | ✅ Supérieur (nouveau) | `register_llm_provider()` | Provider LLM découvvable |
| CapabilityRegistry registration | ✅ Supérieur (nouveau) | 2 capabilities | Enregistré comme SERVICE |
| Benchmarks (9 modèles) | ❌ Non migré | Reste dans `2.3.6_local_llm/benchmarks.csv` | Données benchmark non portées |
| Notebook démo | ❌ Non migré | Reste dans `2.3.6_local_llm/example.ipynb` | Référence pédagogique |
| Workflow pipeline | ❌ Gap | Aucun workflow n'utilise local_llm | Service enregistré mais dormant |
| State writer | ❌ Gap | Pas de `_write_local_llm_to_state` | Résultats non persistés dans l'état |
| SK Plugin (@kernel_function) | ❌ Gap | Pas de plugin SK pour local_llm | Pas accessible via kernel.invoke() |

**Score de préservation**: 4/15 fonctionnalités préservées ou supérieures (27%). C'est le taux le plus bas de tous les audits A-NN. Les 4 fonctionnalités supérieures sont toutes des améliorations d'architecture (multi-backend, async, registry, ServiceDiscovery). Les 11 manquantes sont : 6 non-migrées (spécifiques au projet étudiant), 3 gaps pipeline (workflow, state writer, SK plugin), 2 perdues (serveur→client, benchmark data).

### 1.3 Dilutions / Régressions

#### Dilution 1: Architecture inversée (serveur → client)

**Localisation**: `local_llm_service.py` — le consolidé est un **client HTTP**, pas un serveur de modèles.
**Impact**: MEDIUM — L'étudiant avait un serveur FastAPI chargeant 9 modèles GGUF. Le consolidé est un client qui se connecte à un endpoint OpenAI-compatible. Pour fonctionner, il suppose qu'un serveur tourne (qui peut être le serveur étudiant `app.py` ou n'importe quel backend vLLM/Ollama).
**Assessment**: Renversement architectural intentionnel — le core a choisi l'approche découplée (HTTP client + backend externe) plutôt que l'approche intégrée (import direct llama-cpp). C'est plus flexible mais crée une dépendance runtime externe.

#### Dilution 2: Prompt engineering fallacy non migré

**Localisation**: `2.3.6_local_llm/local_llm/utils.py` — `get_full_prompt()` construit un template de détection de sophismes détaillé (instructions de sortie JSON avec arguments, validity, fallacy_type, explanation).
**Impact**: LOW — ce prompt est spécifique au use case fallacy-detection. Le core a déjà un système de détection de sophismes séparé (InformalAnalysisAgent + FrenchFallacyPlugin + 3-tier hybrid). Le prompt de l'étudiant n'apporterait rien de nouveau au pipeline existant.
**Assessment**: Pas une dilution fonctionnelle — la fonctionnalité est couverte par un système supérieur.

#### Dilution 3: Pipeline integration minimale (service dormant)

**Localisation**: `registry_setup.py` enregistre le service, mais `workflows.py`, `state_writers.py`, `shared_state.py`, `factory.py` n'ont aucune référence local_llm.
**Impact**: HIGH — le service est enregistré dans la CapabilityRegistry mais n'est consommé par aucun workflow, n'écrit dans aucun state, et n'est pas accessible via SK kernel. Il existe comme service découvvable mais n'est pas câblé dans le pipeline d'analyse.
**Fix-intent**: `fix(a-10): wire local_llm_service into pipeline (state writer + optional workflow phase)`

#### Pas d'autre dilution

Le projet étudiant avait un scope relativement limité (serveur de détection de sophismes via llama-cpp). Le consolidé a choisi l'architecture HTTP client + backend externe, ce qui est plus flexible mais laisse le service non câblé.

### 1.4 Statut du répertoire racine `2.3.6_local_llm/`

**Verdict**: 🟢 **Sanctuarisé — référence pédagogique conservée** (mandate R300)

- **0 import live Python** — aucun `from 2.3.6` ou `from local_llm` n'existe dans le codebase consolidé
- **Commentaire de provenance** : `registry_setup.py:207` mentionne `# Local LLM service (2.3.6)`
- **Fichiers non-migrés** : `local_llm/local_llm.py` (modèle loading), `local_llm/utils.py` (prompts), `app.py` (FastAPI serveur), `benchmarks.csv` (données), `example.ipynb` (démo), `setup.sh` (installation)
- **SUIVI** : 80% — "Integre" (partiel, concorde avec cet audit)

---

## 2. Matrice des capabilities

| Capability | Module consolidé | Statut |
|------------|------------------|--------|
| Chat completion (OpenAI-compatible) | `local_llm_service.py` LocalLLMService | ✅ Supérieur (multi-backend) |
| Health check | `local_llm_service.py` is_available() | ✅ Nouveau |
| ServiceDiscovery provider | `capability_registry.py` register_llm_provider() | ✅ Supérieur |
| CapabilityRegistry service | `registry_setup.py` 2 capabilities | ✅ Supérieur |
| Pipeline invoke | `invoke_callables.py` _invoke_local_llm | ⚠️ Minimal (7 LOC pass-through) |
| State writer | AUCUN | ❌ Gap |
| Workflow phase | AUCUN | ❌ Gap |
| SK Plugin | AUCUN | ❌ Gap |

---

## 3. Cartographie des connections

```
2.3.6_local_llm/                         argumentation_analysis/
├── local_llm/local_llm.py ────────── (NON migré — architecture inversée)
│   (Llama wrapper, model loading)       Le consolidé est un CLIENT HTTP,
│                                         l'étudiant était un SERVEUR
├── local_llm/constants.py ────────── (NON migré — ModelEnum + MODEL_PATHS)
├── local_llm/utils.py ────────────── (NON migré — prompts fallacy + extraction JSON)
├── app.py ────────────────────────── (NON migré — FastAPI serveur fallacy)
├── benchmarks.csv ────────────────── (NON migré — données benchmark)
├── example.ipynb ──────────────────── (NON migré — notebook démo)
├── setup.sh ──────────────────────── (NON migré — script installation)
└── subject.md ─────────────────────── (référence pédagogique)

                                         CONSOLIDÉ (architecture client HTTP):
                                         ├── services/local_llm_service.py
                                         │   (LocalLLMService: async chat_completion,
                                         │    multi-backend, health check)
                                         ├── orchestration/invoke_callables.py
                                         │   (_invoke_local_llm: 7 LOC pass-through)
                                         └── orchestration/registry_setup.py
                                             (SERVICE: local_llm_service, 2 caps)

                                         MANQUANT (pipeline integration):
                                         ├── orchestration/state_writers.py
                                         │   ❌ Pas de _write_local_llm_to_state
                                         ├── orchestration/workflows.py
                                         │   ❌ Pas de phase "local_llm"
                                         ├── plugins/
                                         │   ❌ Pas de LocalLLMPlugin (@kernel_function)
                                         ├── core/shared_state.py
                                         │   ❌ Pas de dimension local_llm
                                         └── agents/factory.py
                                             ❌ Pas de create_local_llm_agent()
```

---

## 4. Fix-intents

| # | Issue proposée | Priorité | Action |
|---|---------------|----------|--------|
| F1 | `fix(a-10): add state writer for local_llm results` | **MEDIUM** | Créer `_write_local_llm_to_state` dans `state_writers.py` + dimension `local_llm_outputs` dans `shared_state.py` |
| F2 | `fix(a-10): wire local_llm into optional workflow phase` | **LOW** | Ajouter une phase optionnelle `local_llm` dans les workflows spectaculaire/extended (fallback LLM local si API clé indisponible) |

---

## 5. Conclusion

Le projet 2.3.6 est **partiellement intégré** — le consolidé a choisi une architecture HTTP client (découplée, multi-backend, async) plutôt que l'approche directe llama-cpp de l'étudiant. Cette architecture est **supérieure en flexibilité** (vLLM, Ollama, n'importe quel endpoint) mais l'intégration pipeline est **la plus mince de tous les audits A-NN** : le service est enregistré dans la CapabilityRegistry mais n'est consommé par aucun workflow, ne persiste dans aucun état, et n'est pas exposé via SK kernel.

**Contraste avec les autres audits** : A-07 (sophismes), A-08 (contre-arguments), A-09 (qualité) avaient tous un câblage pipeline complet (invoke + state writer + workflows + factory + shared state). A-10 n'a que l'invoke callable (7 LOC) et la registration — c'est un **service infrastructure dormant**.

**Justification** : Le local LLM est un cas particulier — il sert de **couche transport** (alternative à l'API OpenAI) plutôt que de **couche métier** (analyse argumentative). Son rôle dans le pipeline est de fournir un fallback LLM quand l'API cloud est indisponible, pas d'ajouter une dimension d'analyse. Le câblage pipeline complet (F1, F2) est donc un enhancement légitime mais pas une nécessité immédiate.

**Cas d'usage soutenance** : intéressant pour démontrer la **flexibilité d'infrastructure** — le cluster peut basculer entre OpenAI cloud et un endpoint local sans changer le pipeline. La lacune est que cette flexibilité n'est pas encore câblée dans les workflows.

**Le répertoire `2.3.6_local_llm/` est sanctuarisé** (mandate R300) — conservé comme référence pédagogique et source potentielle du serveur llama-cpp.

---

## 6. Fichiers sources
- `argumentation_analysis/services/local_llm_service.py` — LocalLLMService (adaptateur HTTP OpenAI-compatible)
- `argumentation_analysis/orchestration/invoke_callables.py` — _invoke_local_llm (7 LOC)
- `argumentation_analysis/orchestration/registry_setup.py` — SERVICE registration (2 capabilities)
- `argumentation_analysis/core/capability_registry.py` — ServiceDiscovery.register_llm_provider()
- `tests/unit/argumentation_analysis/services/test_local_llm_service.py` — tests (162 LOC)
