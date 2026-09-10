# web_api/tests/ — suite de tests du package, volontairement hors gate

## Rôle et frontière

Suite de tests **du package** `web_api` : la seule qui vit à l'intérieur de
`argumentation_analysis/`. `pytest.ini:2` (`testpaths = tests`) fait qu'elle
n'est **jamais collectée** par la suite repo-wide — statut documenté dans le
header de `test_services.py:7-8` (« emplacement jamais collecté »).

## Composants publics

| Fichier | Contenu |
|---|---|
| `conftest.py` | fixture autouse `mock_analysis_imports` qui mocke 5 modules d'analyse (:27-40) ; docstring #1783 (:7-10) — les fixtures Flask (`client`, `mock_*_service`, `sample_*`) sont parties à `docs/archives/flask_tests_249/` avec leur seul consommateur `test_endpoints.py` |
| `test_services.py` | 8 tests en 2 classes, header #1859 (:5-23) documentant pourquoi ils restent hors gate |

Les deux classes : `TestValidationServiceFormalBranch` (:34, 2 tests de la
branche formelle désactivée — `validation_service.py:83-87` cité :16-19) et
`TestFrameworkService` (:69, 6 tests dont 4 ciblent l'interface morte
`build_framework` — la surface vivante est `analyze_dung_framework`,
`framework_service.py:36`, cité :11-13). Les **24 tests porteurs** ont été
relocalisés dans le gate : `tests/unit/services/web_api/test_services.py`
(#1859/#1863).

## Points d'entrée valides

Invocation explicite du chemin uniquement (jamais par collection) :

```bash
# cette suite (rouge attendu sur 6/8 — cf. limites)
conda run -n projet-is-roo-new --no-capture-output pytest \
  argumentation_analysis/services/web_api/tests/ -v

# le gate vivant (24 tests passants, relocalisés #1859)
conda run -n projet-is-roo-new --no-capture-output pytest \
  tests/unit/services/web_api/test_services.py -v
```

## Amont / aval

- **Amont** : [../services/](../services/) et
  [../models/request_models.py](../models/request_models.py).
- **Aval** : personne d'automatique (hors collection) — lecteur = le
  développeur qui invoque le chemin explicitement.

## Statut d'intégration

| Famille | Statut | Preuve |
|---|---|---|
| `TestFrameworkService` (6 tests) | **résiduel** | 4 tests FAIL sur l'interface morte `build_framework` ; 2 passent (`test_service_initialization`, `test_is_healthy` — contrat #1864 vivant) ; conservé pour une décision d'authoring future (header :11-14 — réécrire contre `analyze_dung_framework` = authoring nouveau, décision séparée) |
| `TestValidationServiceFormalBranch` (2 tests) | **résiduel** | cible la branche formelle désactivée en production (header :16-19) |

## Artefacts et lecteurs

Aucun artefact ; résultats pytest à l'écran du développeur uniquement.

## Tests représentatifs

Voir « Points d'entrée valides » — ce répertoire **est** la suite. État
mesuré à l'exécution (rejoué pour ce README) : **2 PASS** (
`test_service_initialization`, `test_is_healthy`), **4 FAIL**
(`NameError: name 'Argument' is not defined`, `test_services.py:94,139`),
**2 ERROR** (fixture `validation_service` utilisée :38 mais absente du
conftest post-#1783).

## Frères et parent

- Parent : [web_api/](../) — README parent : [../README.md](../README.md)
  (**périmé**).
- Frères : [../services/](../services/README.md), [../models/](../models/README.md).
- Gate vivant correspondant : `tests/unit/services/web_api/`.

## Limites connues

- 6/8 tests sont rouges à l'exécution directe (cf. état mesuré ci-dessus) —
  conforme au header #1859, mais le fichier reste exécutable et échoue pour
  quiconque le cible sans lire le header.
- La fixture `validation_service` référencée par
  `TestValidationServiceFormalBranch` n'est plus définie depuis l'archivage
  des fixtures Flask (#1783) — les 2 tests de la classe sont en ERROR, pas
  en FAIL.
