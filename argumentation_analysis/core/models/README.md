# `core/models/` — contrat de données Toulmin

## Rôle et frontière

Un seul module : `toulmin_model.py` (42 lignes) — schémas Pydantic du modèle argumentatif de Toulmin. Pur contrat de données, zéro logique. Sans `__init__.py` (namespace package implicite).

N'est **pas** (quatre autres familles « models » dans le dépôt, à ne pas confondre) :

- `api/models.py` — schémas requête/réponse FastAPI ;
- `argumentation_analysis/models/` — dataclass `Extract` (définitions d'extraits du dataset, a son propre README) ;
- `services/web_api/models/` — modèles de la web API (documentés au lot A2) ;
- `project_core/llm/models/` — analyse de commits.

## Composants publics

- `ToulminComponent` (`toulmin_model.py:5`) — `text`, `confidence_score`, `source_sentences` ;
- `ToulminAnalysisResult` (:19) — les 6 champs Toulmin : `claim`, `data`, `warrant`, `backing`, `qualifier`, `rebuttal`.

## Points d'entrée valides

- `api/endpoints.py:19` — importé comme `response_model` du POST `/api/v1/informal/analyze` : **le contrat est la forme de la réponse API publique** ;
- `agents/tools/analysis/new/semantic_argument_analyzer.py:7` — type de retour de `SemanticArgumentAnalyzer.run` ;
- `plugins/toulmin_plugin.py:14` — import **sous `TYPE_CHECKING` seulement** (évite la dépendance circulaire).

## Amont / aval

- Amont : rien (pydantic pur).
- Aval : `api/` (endpoints + `mobile_endpoints.py` qui lit `toulmin.claim/data/warrant/qualifier` après analyse), `SemanticArgumentAnalyzer`, `ToulminPlugin`.

## Statut d'intégration

Deux familles distinctes :

- **le contrat de données : `actif`** — il façonne la réponse d'une route API réelle (`response_model`) et le retour de l'analyseur sémantique ;
- **le moteur d'analyse Toulmin : `expérimental` (squelette)** — `toulmin_plugin.py:43-45` lève `NotImplementedError` (« The core logic of Toulmin analysis is not yet implemented »), et `SemanticArgumentAnalyzer` cible par défaut un LLM **local** (`api_base_url="http://localhost:8000/v1"`, `model_name="Qwen3-1.7B-Toulmin-Analyzer"`, `semantic_argument_analyzer.py:13-15`).

## Artefacts et lecteurs

Aucun (contrat pur).

## Tests représentatifs

Pas de test dédié au module ; couverture indirecte :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/agents/tools/analysis/new/test_semantic_argument_analyzer.py tests/unit/api/test_mobile_endpoints.py -v
```

(asserts réels côté analyseur :72 ; mock côté mobile :138).

## Frères et parent

Parent : [`../README.md`](../README.md) — existe, ne mentionne pas `models/`. Frère avec README : `communication/`.

## Limites connues

- pas de `__init__.py` dans `models/` (aucune surface d'export) ;
- la chaîne moteur est incomplète : le plugin qui produirait des `ToulminAnalysisResult` lève `NotImplementedError`, et l'analyseur sémantique suppose un service LLM local dédié qui n'est pas provisionné par le dépôt.
