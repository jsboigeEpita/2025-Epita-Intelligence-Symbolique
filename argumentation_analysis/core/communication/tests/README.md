# `core/communication/tests/` — suite de tests in-source du package communication

## Rôle et frontière

Suite de tests **colocée** (unittest.TestCase, français) du package `core/communication` : 29 tests dans 3 fichiers — sérialisation des messages, filtres/exceptions des canaux, intégration multi-threads réelle.

N'est **pas** la suite exécutée par le dépôt : `pytest.ini:2` (`testpaths = tests`) fait que `pytest` nu **ne collecte jamais ce répertoire** (invocation explicite du chemin obligatoire). Le jumeau collecté vit sous `tests/unit/argumentation_analysis/core/communication/` (réécritures pytest) et `tests/unit/argumentation_analysis/test_communication_integration.py` (méthodes différentes — c'est ce dernier que `pytest.ini` cite en commentaire).

## Composants publics

| Fichier | Contenu |
|---|---|
| `test_message.py` | 15 tests — enums, `to_dict`/`from_dict`, `is_response_to`, `create_response`/`create_acknowledgement`, 4 sous-classes de `Message` |
| `test_channel_interface.py` | 10 tests — `MockChannel` (implémentation concrète de test), filtres `matches_filter` (type/émetteur/priorité/niveau/contenu), hiérarchie des 5 exceptions |
| `test_communication_integration.py` | 4 tests avec **threads réels** (`import threading` :2, :110-112) sur `MessageMiddleware` + `HierarchicalChannel` réels : requête-réponse, multi-messages, timeout, concurrence 3×3 |

## Points d'entrée valides

Aucun importeur (grep `communication.tests` : 0 match). Seule entrée = invocation explicite :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest argumentation_analysis/core/communication/tests -v
```

## Amont / aval

Amont : les modules du package parent (`message`, `channel_interface`, `middleware`, `hierarchical_channel`). Aval : rien (package terminal, non collecté).

## Statut d'intégration

**résiduel** — doublon pré-migration, partiellement supérieuré par `tests/unit/` (le jumeau collecté de `test_channel_interface` compte ~50 tests contre 10 ici). L'audit de tests le qualifie d'« artefact de la période pré-migration vers `tests/unit/` » (`docs/reports/test_audit/B-05_core_services.md:268`, avec recommandation d'archivage).

Il reste **la seule couverture** d'une quirk réelle : `message.py:337` construit `content = {"info_type": info_type, DATA_DIR: data}` où `DATA_DIR` est un `pathlib.Path` (pas la chaîne `"data"`) — clé non-JSON-sérialisable via `to_dict`, `content["data"]` lève `KeyError` chez tout lecteur. Le test in-source asserte la quirk telle quelle (`test_message.py:333-336`), le jumeau collecté ne teste que `info_type` → quirk invisible en CI.

## Artefacts et lecteurs

Aucun fichier écrit ; sortie console (`logging.basicConfig` dans le test d'intégration).

## Tests représentatifs

La commande ci-dessus (Points d'entrée). État non garanti : non exécuté par CI, peut rougir silencieusement.

## Frères et parent

Parent : [`../README.md`](../README.md) — documente le package communication (canaux, adaptateurs). Le grand-parent [`core/README.md`](../../README.md) existe.

## Limites connues

- Couverture limitée à 3 modules du package (pas de middleware/pub-sub/adapters in-source — le jumeau `tests/unit/` les couvre) ;
- quirk `DATA_DIR` :337 couverte uniquement ici, et assertée comme un comportement attendu — signalée en issue séparée ;
- tests à threads réels sensibles au timeout global 900 s ;
- imports morts (`OperationalAdapter` utilisé seulement en commentaire ; `json`, `patch` jamais utilisés).
