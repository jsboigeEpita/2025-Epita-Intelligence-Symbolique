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
| `test_services.py` | 6 tests en 1 classe, header #1859/#2536 documentant pourquoi ils restent hors gate |

Une seule classe, `TestFrameworkService` (6 tests, dont 2 ciblent
l'interface morte `build_framework` ; la surface vivante est
`analyze_dung_framework`). `TestValidationServiceFormalBranch` est partie avec
la branche qu'elle testait (#2266). Les **24 tests porteurs** ont été
relocalisés dans le gate : `tests/unit/services/web_api/test_services.py`
(#1859/#1863).

## Points d'entrée valides

Invocation explicite du chemin uniquement (jamais par collection) :

```bash
# cette suite (rouge attendu sur 2/6 — cf. limites)
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
| `TestFrameworkService` (6 tests) | **résiduel** | 2 tests FAIL sur l'interface morte `build_framework` ; 4 passent et sont tenus dans le gate (`is_healthy` par `test_mcp_server.py`, la validation des modèles par `TestFrameworkRequestModel`) ; conservé pour une décision d'authoring future (réécrire contre `analyze_dung_framework` = authoring nouveau, décision séparée) |

## Artefacts et lecteurs

Aucun artefact ; résultats pytest à l'écran du développeur uniquement.

## Tests représentatifs

Voir « Points d'entrée valides » — ce répertoire **est** la suite. État
mesuré à l'exécution (rejoué #2536) : **4 PASS**
(`test_service_initialization`, `test_is_healthy`,
`test_framework_argument_validation`, `test_framework_options_validation`),
**2 FAIL** (`AttributeError: 'FrameworkService' object has no attribute
'build_framework'`). Le `NameError: name 'Argument'` que ce README relevait
venait de l'import des modèles parti avec les tests relocalisés (#1863) ;
rétabli #2536.

## Frères et parent

- Parent : [web_api/](../) — README parent : [../README.md](../README.md)
  (**périmé**).
- Frères : [../services/](../services/README.md), [../models/](../models/README.md).
- Gate vivant correspondant : `tests/unit/services/web_api/`.

## Limites connues

- 2/6 tests sont rouges à l'exécution directe (cf. état mesuré ci-dessus) —
  conforme au header, mais le fichier reste exécutable et échoue pour
  quiconque le cible sans lire le header.
