# `core/utils/tests/` — suite in-source du module `error_management` (théâtre)

## Rôle et frontière

Suite de tests **colocée** du package `core/utils` — en pratique un seul fichier, `test_error_recovery_manager.py` (157 lignes), couvrant uniquement `error_management.py`. Un `__init__.py` (header coding seul).

N'est **pas** la suite canonique : `pytest.ini:2` (`testpaths = tests`) fait que ce dossier n'est **pas collecté** par `pytest` nu. Et le module qu'il teste possède une **vraie** suite collectée ailleurs : `tests/unit/argumentation_analysis/utils/core_utils/test_error_management.py` (asserts réels, ex. `assert sm.state["tasks"] == []`).

## Composants publics

`test_error_recovery_manager.py` — 5 fonctions de test (`test_network_error_recovery` :24, `test_service_error_recovery` :44, `test_validation_error_recovery` :71, `test_multiple_errors_recovery` :94, `test_clear_errors` :128) + un runner `__main__` (:151-157).

## Points d'entrée valides

Aucun importeur. Invocation explicite possible :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest argumentation_analysis/core/utils/tests/test_error_recovery_manager.py -v
```

(le chemin positionnel outrepasse `testpaths`).

## Amont / aval

- Amont : `core/utils/error_management.py` — module **auto-déclaré « simplifié pour les tests »** (:7 et :59) : récupérations simulées (`time.sleep(0.001); return True`). Non exporté par `core/utils/__init__.py` ; importé uniquement par ce fichier in-source et par la suite collectée `tests/unit/.../test_error_management.py`.
- Aval : rien.

## Statut d'intégration

**résiduel** — 0 assertion sur les 5 fonctions (:24-148, uniquement des `print`) : les tests sont collectables mais **toujours verts** quoi qu'il arrive (théâtre, anti-pattern #1019). Le module testé est lui-même un stub jamais branché production.

## Artefacts et lecteurs

Aucun (sorties stdout).

## Tests représentatifs

La commande ci-dessus exécute la suite ; la couverture **réelle** du module est la suite collectée jumelle :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/utils/core_utils/test_error_management.py -v
```

## Frères et parent

Parent `core/utils/` : **pas de README** (27 fichiers .py, 0 .md). Grand-parent documenté : [`../../README.md`](../../README.md) (ignore `utils/`).

## Limites connues

- 0 assertion = vert garanti sans rien prouver ;
- doublon partiel de la suite collectée `tests/unit/.../test_error_management.py` (qui, elle, asserte) ;
- le module testé (`error_management.py`) est un stub non exporté — signalé en issue séparée avec la quirk `DATA_DIR` voisine de `communication/`.
