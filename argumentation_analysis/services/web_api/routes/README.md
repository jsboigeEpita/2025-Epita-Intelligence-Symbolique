# web_api/routes/ — tombstones des routes Flask archivées

## Rôle et frontière

N'est **plus** une couche HTTP. Les 4 fichiers sont des marqueurs d'archive de
3 lignes : chacun porte
`# Archived: 2026-03-24 — Flask routes superseded by FastAPI (api/main.py) (#217)`
et pointe vers l'archive complète
`docs/archives/services_web_api_flask/routes/` (ex. `main_routes.py:1-3`).
Le répertoire n'a **même plus de `__init__.py`** — ce n'est plus un package
importable. La couche HTTP vivante est `api/main.py` (FastAPI).

## Composants publics

Aucun. Historiquement (depuis l'archive), 4 blueprints Flask montés par l'app
archivée (`docs/archives/services_web_api_flask/app.py:34-37`) :

| Blueprint (archive) | Routes d'origine |
|---|---|
| `main_bp` | GET `/health`, POST `/analyze`, `/validate`, `/fallacies`, `/logic_graph`, GET `/endpoints` |
| `logic_bp` | POST `/belief-set`, `/query`, `/generate-queries` |
| `framework_bp` | POST `/framework/analyze` |
| `health_bp` | GET `/health` |

## Points d'entrée valides

Aucun. Seul importeur des chemins `web_api.routes.*` : l'app archivée
elle-même (`docs/archives/services_web_api_flask/app.py:34-37`). Le script de
lancement historique cible désormais `api.main:app`
(`scripts/apps/webapp/launch_webapp_background.py:50-53`, #1853).

## Amont / aval

Plus rien. Historiquement : aval de [../services/](../services/), amont du
front React.

## Statut d'intégration

| Famille | Statut | Preuve |
|---|---|---|
| Les 4 tombstones | **déprécié** | remplacés par FastAPI `api/main.py` (7 routeurs montés `api/main.py:97-106`) ; archive vivante consultable |

## Artefacts et lecteurs

Aucun — aucun code exécutable.

## Tests représentatifs

Aucun. Les tests d'endpoints Flask sont archivés avec leurs fixtures
(#1783 → `docs/archives/flask_tests_249/` ; contexte dans
[../tests/conftest.py](../tests/conftest.py)).

## Frères et parent

- Parent : [web_api/](../) — README parent : [../README.md](../README.md)
  (**périmé** : décrit encore l'app Flask archivée, port 5003).
- Frères vivants : [../services/](../services/README.md),
  [../models/](../models/README.md).

## Limites connues

Le répertoire entier est une limite en soi : son contenu se résume aux
pointeurs d'archive. Les tombstones existent pour qu'un import hérité
échoue avec un message explicite plutôt qu'avec un `ModuleNotFoundError` sec.
