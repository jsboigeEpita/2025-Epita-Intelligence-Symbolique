# Audit A-13: Projet 2.5.6 — Protection IA Adversariale (AI Shield)

**Issue**: #774 (A-13) | **Epic**: #742 | **Date audit**: 2026-06-01
**Auditeur**: Claude Code @ myia-po-2023

---

## 0. Synthèse en 1 phrase

Le projet étudiant 2.5.6 (Pierre Schweitzer, Maxime Ruff, Joric Hantzberg) n'a **jamais été soumis** (score SUIVI 0%) — le framework "AI Shield" démontré en soutenance a été **reconstitué** depuis la description de présentation via l'issue #166 (fermée), produisant ~688 LOC fonctionnels et testés (orchestrateur Shield + 3 layers + 4 presets + 33 tests), mais le service est **complètement déconnecté** du pipeline : aucun registry entry, aucun invoke callable, aucun state writer, aucun workflow phase, aucun endpoint API.

**Verdict**: 🟡 **RECRÉÉ fonctionnellement mais NON CÂBLÉ** — le service est standalone, prêt à être intégré mais actuellement inactif dans le pipeline. Pas de répertoire racine (projet non soumis).

---

## 1. Cadrage R281c — 4 étapes

### 1.1 Localiser la version consolidée

**Cas particulier** : le projet étudiant n'a **pas de répertoire racine** — le code n'a jamais été soumis (0%). La version "consolidée" est en réalité une **reconstitution** depuis la description de soutenance.

| Fichier | LOC approx | Rôle | Origine |
| --- | --- | --- | --- |
| `services/ai_shield/shield.py` | ~192 | `Shield` orchestrator + `ShieldLayer` ABC + `LayerResult`/`ShieldResult` dataclasses | Reconstitué (#166) |
| `services/ai_shield/layers/heuristic.py` | ~146 | `HeuristicLayer` — regex/keyword validation (injection, PII, manipulation) | Reconstitué (#166) |
| `services/ai_shield/layers/llm_validator.py` | ~119 | `LLMValidatorLayer` — LLM-based jailbreak/bias/toxicity detection | Reconstitué (#166) |
| `services/ai_shield/layers/output_filter.py` | ~151 | `OutputFilterLayer` — output leak prevention (credentials, system prompts, PII, paths) | Reconstitué (#166) |
| `services/ai_shield/presets.py` | ~80 | 4 pre-configured security profiles (basic, advanced, output_only, strict) | Reconstitué (#166) |
| `services/ai_shield/__init__.py` | ~29 | Package exports | Reconstitué (#166) |

**Total**: ~717 LOC (6 fichiers source) + 33 tests.

**Absence totale de wiring** : `registry_setup.py`, `invoke_callables.py`, `state_writers.py`, `workflows.py`, `shared_state.py`, `factory.py`, `api/`, `services/web_api/` — **zéro référence** à `ai_shield` ou `shield` dans tout le pipeline.

### 1.2 Préservation fonctionnelle

Le sujet spec 2.5.6 (~2132 lignes) définissait un framework de protection adversariale très ambitieux. La soutenance a démontré un sous-ensemble fonctionnel. La reconstitution couvre le cœur de ce qui a été démontré :

| Fonctionnalité (spec / soutenance) | Préservée ? | Où | Notes |
| --- | --- | --- | --- |
| Framework orchestrateur modulaire | ✅ Reconstitué | `shield.py` | `Shield` + `ShieldLayer` ABC + short-circuit + fail_open/closed |
| Heuristic validation (regex) | ✅ Reconstitué | `heuristic.py` | 16 injection + 4 bias + 3 manipulation patterns |
| LLM-based jailbreak detection | ✅ Reconstitué | `llm_validator.py` | OpenAI API, JSON classification, graceful fallback sans clé |
| Output leak prevention | ✅ Reconstitué | `output_filter.py` | Credentials (6 patterns), PII (4), system prompts (5), paths (3) |
| 4 presets configurables | ✅ Reconstitué | `presets.py` | basic/advanced/output_only/strict |
| Score 0-1 par layer + threshold | ✅ Reconstitué | `ShieldLayer._make_result()` | Même modèle que la soutenance |
| Credential redaction | ✅ Reconstitué | `output_filter.py` | First 4 + `***` + last 4 chars |
| Tests unitaires | ✅ Reconstitué | `test_ai_shield.py` | 33 tests, 4 classes, tous verts |
| Taxonomie attaques adversariales (spec) | ❌ Non implémenté | — | Le spec définissait evasion, poisoning, Dung attacks — non recréé |
| Anomaly detection ML (Isolation Forest) | ❌ Non implémenté | — | Trop complexe pour une reconstitution depuis description |
| Defensive adversarial training | ❌ Non implémenté | — | Hors scope reconstitution |
| OWASP AI Top 10 / STRIDE | ❌ Non implémenté | — | Le spec demandait un threat modeling complet |
| Ensemble voting (majority/weighted) | ❌ Non implémenté | — | Pas dans la soutenance |
| Fallacy detection layer (soutenance) | ❌ Non implémenté | — | La soutenance mentionnait un layer fallacy — existe ailleurs (InformalAnalysisAgent) mais pas dans le shield |
| Bias detection layer séparé (soutenance) | ⚠️ Partiel | `heuristic.py` | Bias est un sous-ensemble du heuristic layer (4 patterns), pas un layer dédié |
| Registry registration | ❌ Gap | — | Pas dans `registry_setup.py` |
| Invoke callable | ❌ Gap | — | Pas dans `invoke_callables.py` |
| State writer | ❌ Gap | — | Pas dans `state_writers.py` |
| Workflow phase | ❌ Gap | — | Pas dans `workflows.py` |
| REST API endpoint | ❌ Gap | — | Pas dans `api/` ni `services/web_api/` |

**Score de préservation**: 8/21 fonctionnalités préservées ou reconstituées (38%). Les 8 préservées sont le cœur fonctionnel démontré en soutenance. Les 13 manquantes se répartissent en : 5 non-implémentées du spec (trop ambitieuses pour reconstitution), 1 partielle (bias dans heuristic), et **7 gaps pipeline** (aucun wiring).

### 1.3 Dilutions / Régressions

#### Dilution 1: Aucun wiring pipeline (service fantôme)

**Localisation**: Le shield existe à `services/ai_shield/` mais n'est référencé nulle part dans le pipeline d'orchestration.
**Impact**: HIGH — le service est fonctionnel et testé mais **complètement inutilisable** dans le pipeline normal. Il doit être appelé manuellement via Python (`shield = load_preset("advanced"); result = shield.validate_input(text)`).
**Assessment**: C'est le cas le plus extrême de "service infrastructure non câblé" — même A-10 (local LLM, verdict 🟡) avait au moins un invoke callable (7 LOC) et une registry entry. A-13 n'a **rien**.
**Fix-intent**: `fix(a-13): wire ai_shield into pipeline (registry + invoke + optional workflow phase + API endpoint)`

#### Dilution 2: Fallacy detection layer manquant

**Localisation**: La soutenance mentionnait un layer dédié à la détection de sophismes. Le heuristic layer n'a que 4 patterns de bias.
**Impact**: LOW — la détection de sophismes est couverte par le système InformalAnalysisAgent + FrenchFallacyPlugin + 3-tier hybrid, qui est strictement supérieur à ce qu'un layer de shield pourrait offrir. L'ajouter au shield serait redondant.
**Assessment**: Pas une dilution — la fonctionnalité existe ailleurs dans le système. Un pont (wrapper layer) pourrait connecter le shield au système de fallacy existant.

#### Dilution 3: Subject spec très ambitieux vs reconstitution minimaliste

**Localisation**: Le spec 2.5.6 demandait Isolation Forest, Autoencoder, ensemble voting, adversarial training, OWASP threat modeling — aucun de ces éléments n'existe.
**Impact**: MEDIUM — le spec définissait un framework de recherche académique. La reconstitution a couvert le **sous-ensemble démontré en soutenance** (layer architecture + 3 layers + presets), qui est pragmatique et fonctionnel.
**Assessment**: Le gap est inhérent à la nature de la reconstitution — on ne peut recréer que ce qui a été documenté dans la soutenance. Les fonctionnalités spec non démontrées sont du **futur work**, pas des régressions.

### 1.4 Statut du répertoire racine

**Cas particulier** : le projet 2.5.6 n'a **pas de répertoire racine** — le code n'a jamais été soumis (score SUIVI 0%). La question du sort du répertoire ne s'applique pas.

**SUIVI** : 0% — "Non soumis"
**Issue #166** : **FERMÉE** (reconstitution complétée)
**Sujet doc** : `docs/projets/sujets/2.5.6_Protection_Systemes_IA_Attaques_Adversariales.md` (2132 lignes)

---

## 2. Matrice des capabilities

| Capability | Module consolidé | Statut |
| --- | --- | --- |
| Shield orchestrateur | `services/ai_shield/shield.py` Shield | ✅ Reconstitué |
| Heuristic validation (regex) | `services/ai_shield/layers/heuristic.py` | ✅ Reconstitué |
| LLM-based validation | `services/ai_shield/layers/llm_validator.py` | ✅ Reconstitué |
| Output leak prevention | `services/ai_shield/layers/output_filter.py` | ✅ Reconstitué |
| Presets configurables | `services/ai_shield/presets.py` | ✅ Reconstitué |
| Registry SERVICE | AUCUN | ❌ Gap |
| Pipeline invoke | AUCUN | ❌ Gap |
| State writer | AUCUN | ❌ Gap |
| Workflow phase | AUCUN | ❌ Gap |
| REST API endpoint | AUCUN | ❌ Gap |

---

## 3. Cartographie des connections

```text
(Pas de répertoire étudiant — code non soumis)

Soutenance 2.5.6 (Schweitzer, Ruff, Hantzberg)
  └─ Description framework "AI Shield"
      └─ Issue #166 (reconstitution)
          └─ Reconstitution → argumentation_analysis/services/ai_shield/
              ├── shield.py     (Shield + ShieldLayer ABC + LayerResult + ShieldResult)
              ├── layers/
              │   ├── heuristic.py      (16 injection + 4 bias + 3 manipulation patterns)
              │   ├── llm_validator.py  (OpenAI API, JSON classification, fallback)
              │   └── output_filter.py  (6 credential + 4 PII + 5 system + 3 path patterns)
              ├── presets.py    (basic/advanced/output_only/strict)
              └── __init__.py   (exports)

MANQUANT (pipeline integration):
├── orchestration/registry_setup.py
│   ❌ Pas de SERVICE ai_shield
├── orchestration/invoke_callables.py
│   ❌ Pas de _invoke_ai_shield
├── orchestration/state_writers.py
│   ❌ Pas de _write_ai_shield_to_state
├── orchestration/workflows.py
│   ❌ Pas de phase "shield" ou "security_check"
├── core/shared_state.py
│   ❌ Pas de dimension security/shield
├── agents/factory.py
│   ❌ Pas de create_shield_agent()
├── api/
│   ❌ Pas de endpoint /api/shield/validate
└── services/web_api/
    ❌ Pas de shield integration
```

---

## 4. Fix-intents

| # | Issue proposée | Priorité | Action |
| --- | --- | --- | --- |
| F1 | `fix(a-13): wire ai_shield service into pipeline` | **MEDIUM** | Ajouter SERVICE registration dans `registry_setup.py` (2 capabilities : `input_validation`, `output_filtering`) + invoke callable dans `invoke_callables.py` + state writer optionnel + phase optionnelle "shield" dans le workflow `full` |
| F2 | `fix(a-13): expose ai_shield via REST API endpoint` | **LOW** | Ajouter `/api/shield/validate` endpoint dans le router API pour accès direct |

---

## 5. Conclusion

Le projet 2.5.6 est un **cas unique** dans les audits A-NN : le code étudiant n'a **jamais été soumis** (0%). Le framework "AI Shield" démontré en soutenance a été **fidèlement reconstitué** (~717 LOC, 3 layers, 4 presets, 33 tests) depuis la description de présentation, avec une architecture propre (ABC ShieldLayer, dataclasses, fluent API, fail-open/closed).

Cependant, contrairement à tous les autres audits A-NN (y compris A-10, le plus mince), le AI Shield n'a **aucun wiring pipeline** — zéro. Pas de registry, pas d'invoke, pas de state writer, pas de workflow, pas d'endpoint. C'est un **service fantôme** : fonctionnel, testé, mais inaccessible depuis le pipeline d'analyse ou l'API REST.

**Contraste avec A-10** (local LLM, verdict 🟡) : A-10 avait au minimum 7 LOC d'invoke callable + registry registration. A-13 n'a rien — c'est le seul audit où le service est **complètement isolé**.

**Justification** : le AI Shield est un cas légitime de service de sécurité opt-in — ce n'est pas une couche métier d'analyse argumentative, c'est une **couche de protection infrastructure**. Son intégration comme middleware (pre-processing input + post-processing output) est un enhancement de sécurité, pas une nécessité fonctionnelle. Le wiring (F1, F2) est un enhancement MEDIUM.

**Cas d'usage soutenance** : intéressant pour démontrer la **défense adversariale** — le shield peut détecter les injections de prompt, les tentatives de jailbreak, les fuites de credentials et de prompts système. Avec un endpoint API, la démo serait complète.

**Test coverage** : 33 tests unitaires (4 classes) couvrant tous les layers, presets, et cas limites (fail_open/closed, disabled layers, short-circuit). Couverture solide.

**Pas de répertoire racine** — le projet n'a jamais été soumis.

---

## 6. Fichiers sources

- `argumentation_analysis/services/ai_shield/shield.py` — Shield orchestrator + ShieldLayer ABC + dataclasses
- `argumentation_analysis/services/ai_shield/layers/heuristic.py` — HeuristicLayer (regex validation)
- `argumentation_analysis/services/ai_shield/layers/llm_validator.py` — LLMValidatorLayer (LLM-based detection)
- `argumentation_analysis/services/ai_shield/layers/output_filter.py` — OutputFilterLayer (leak prevention)
- `argumentation_analysis/services/ai_shield/presets.py` — 4 security profiles
- `argumentation_analysis/services/ai_shield/__init__.py` — Package exports
- `tests/unit/argumentation_analysis/test_ai_shield.py` — 33 tests unitaires
- `docs/projets/sujets/2.5.6_Protection_Systemes_IA_Attaques_Adversariales.md` — Sujet spec (2132 lignes)

## À valider par l'utilisateur

RAS — reconstitution fidèle depuis soutenance, verdict clair (🟡 non câblé), fix-intents d'enrichissement du consolidé uniquement. Aucune décision en suspens.
