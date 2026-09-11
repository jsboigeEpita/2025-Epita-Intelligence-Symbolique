# `adapters/` — adaptateurs vers détecteurs de sophismes et bibliothèques externes

## Rôle et frontière

Adaptateurs exposant des composants externes ou étudiants derrière les interfaces standard du dépôt (`__init__.py:1-7`). 4 fichiers, ~1660 lignes.

N'est **pas** la famille principale de plugins SK (celle-ci est [`plugins/`](../plugins/) racine) : ici on adapte des **implémentations** (projet étudiant 2.3.2, bibliothèque `abs_arg_dung/`, détecteur contextuel) derrière des contrats `core/interfaces/` pour la composabilité via CapabilityRegistry.

## Composants publics

- `FrenchFallacyAdapter` (`french_fallacy_adapter.py:1364`, 1556 l.) — détection FR multi-tiers : Tier 3 symbolique spaCy, Tier 1.5 vLLM self-hosted, CamemBERT **déprécié** #297 (« model never deployed », :16), NLI zero-shot, LLM OpenAI via ServiceDiscovery ; fusion par confiance (:1520-1534). Auxiliaires : `SymbolicFallacyDetector` :502, `NLIFallacyDetector` :607, `CamemBERTFallacyDetector` :860, `SelfHostedLLMFallacyDetector` :1021, `LLMFallacyDetector` :1167, `justify_fallacy` :390, `FALLACY_LABELS_FR` :175 (28 labels depuis `data/taxonomy_medium.csv`).
- `DungStudentProvider` (`dung_student_provider.py:37`) — la bibliothèque étudiant `abs_arg_dung/` comme fournisseur alternatif de la capability `dung_extensions` (#893) ; 4 sémantiques seulement (grounded/preferred/stable/complete, :29-34), `quality_score` 0.6 (:53-59), dispo conditionnée JVM (:65-90). Plus `invoke_dung_student` :217 et `register_dung_student_provider` :239.
- `ContextualFallacyDetectorAdapter` (`contextual_fallacy_detector_adapter.py:7`, 32 l.) — wrap trivial de `agents/tools/analysis/new.ContextualFallacyDetector`.

## Points d'entrée valides

Chaînes production mesurées :

- `FrenchFallacyAdapter` → [`plugins/french_fallacy_plugin.py`](../plugins/french_fallacy_plugin.py) `:15` → lazy-load [`agents/factory.py:74-75`](../agents/factory.py) ; import direct [`orchestration/invoke_callables.py:5589`](../orchestration/invoke_callables.py) (hybride) ; `justify_fallacy` en fallback d'explication [`orchestration/state_writers.py:720-724`](../orchestration/state_writers.py).
- `DungStudentProvider` (classe) → [`orchestration/invoke_callables.py:7877`](../orchestration/invoke_callables.py) (hint `dung_provider_hint == "abs_arg_dung_student"`, #908) et `:8188` (backend de comparaison Dung).
- `ContextualFallacyDetectorAdapter` → [`core/bootstrap.py:9-10,166`](../core/bootstrap.py) (bootstrap importé par `api/main.py:25`, `orchestration/service_manager.py:53`, `pipelines/unified_text_analysis.py:84`).
- **Morts** : `register_dung_student_provider` et `invoke_dung_student` — 0 appelant hors module/tests (grep plein dépôt) ; l'accès réel contourne le registre en instanciant la classe directement.

## Amont / aval

- Amont : CSV taxonomie `data/taxonomy_*.csv`, `abs_arg_dung.enhanced_agent` (sanctuaire jamais modifié, :15), JVM jpype, ServiceDiscovery.
- Aval : plugin SK + factory (sophismes FR), invoke_callables (hybride + Dung), state_writers (explications), bootstrap (contextuel).

## Statut d'intégration

| Composant | Statut | Preuve |
|---|---|---|
| `FrenchFallacyAdapter` | **actif** | plugin :15 → factory :74-75 ; invoke_callables :5589 ; state_writers :720 |
| `DungStudentProvider` (classe) | **actif (spécialisé)** | invoke_callables :7877, :8188 |
| `register_dung_student_provider` / `invoke_dung_student` | **résiduel** | grep 0 appelant |
| `ContextualFallacyDetectorAdapter` | **actif** | bootstrap.py:9, :166 |
| Tier CamemBERT | **déprécié** | #297, gardé compat :16, :1390 |

## Artefacts et lecteurs

Aucune écriture disque. Effets de bord import : chargement CSV à l'import (`FALLACY_LABELS_FR = _load_taxonomy_labels()` :175, fallback silencieux 13 labels :104) ; le tier NLI télécharge ~600 Mo de modèle (docstring :8).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/adapters/ -v
```

5 fichiers sous `tests/unit/argumentation_analysis/adapters/` + croisés `test_dung_provider_selector.py`, `orchestration/test_compare_dung_backends.py:364,388,425`.

## Frères et parent

Parent : [`../README.md`](../README.md) — ne mentionne pas `adapters/`. Frères documentés : [`agents/`](../agents/README.md), [`core/`](../core/README.md), [`plugins/`](../plugins/) (sans README), [`orchestration/`](../orchestration/README.md).

## Limites connues

- `register_dung_student_provider`/`invoke_dung_student` : code mort production — l'accès réel instancie la classe directement ;
- docstring `__init__.py:5` promet `AbstractAnalysisService` — aucun adapter ne l'implémente (surpromesse doc) ;
- CamemBERT : ~160 lignes + tests dédiés pour un tier jamais déployé ;
- `dung_student_provider.py:186` : résumé `extensions.get("preferred", extensions.get("grounded", {}))` silencieusement vide si les deux sémantiques échouent (erreurs capturées :143, :154) ;
- chargement CSV à l'import :175 : un CSV corrompu change la surface de labels sans erreur visible.
