# `utils/dev_tools/` — outillage de maintenance du dépôt (13 modules)

## Rôle et frontière

13 modules (4 155 lignes) d'outillage développement : formatage, validation, coverage, encodage, environnement, refactoring, réparation d'extraits, reporting, vérification. **Pas de logique métier d'analyse** — ce sont les outils qui maintiennent le dépôt, consommés par les scripts de maintenance.

## Composants publics

`code_formatting_utils` (177 l.), `code_validation` (393 l.), `coverage_utils` (267 l.), `encoding_utils` (322 l.), `env_checks` (528 l.), `format_utils` (305 l.), `import_testing_utils` (130 l.), `project_structure_utils` (93 l.), `refactoring_utils` (518 l.), `repair_utils` (379 l. — `run_extract_repair_pipeline` :229), `reporting_utils` (158 l.), `verification_utils` (448 l.), `visualization_utils` (459 l.). `__init__.py` (31 l.) importe les 13 — aucun export fantôme (sous-modules vérifiés existants).

## Points d'entrée valides

Uniquement les **CLI de maintenance** (pas de route API, pas de phase workflow) :

- `scripts/utils/fix_indentation.py` (code_formatting) ; `scripts/utils/analyze_directory_usage.py`, `check_syntax.py` (code_validation) ; `scripts/reporting/generate_coverage_report.py`, `initialize_coverage_history.py` (coverage) ; `scripts/utils/check_encoding.py`, `fix_encoding.py` (encoding) ; `scripts/utils/fix_docstrings.py` (format) ; `scripts/orchestration/run_verify_extracts.py` (verification) ; `scripts/orchestration/run_extract_repair.py:36` (repair).

## Amont / aval

- Amont : [`../../core/utils/`](../../core/README.md), `extract_repair/marker_repair_logic` (repair_utils.py:43).
- Aval : scripts de maintenance `scripts/utils/`, `scripts/orchestration/`, `scripts/reporting/`.

## Statut d'intégration

**mixte** — 7 modules ont des consommateurs scripts mesurés (liste ci-dessus) ; 5 sont test-only (`env_checks`, `import_testing_utils`, `project_structure_utils`, `refactoring_utils`, `reporting_utils`) ; **`visualization_utils` est mort** (0 importeur production ET test — le hit `scripts/reporting/compare_rhetorical_agents_simple.py:38` importe l'autre `core.utils.visualization_utils`, module différent). Le tout est auto-importé en bloc par `utils/__init__.py:39`.

## Artefacts et lecteurs

Aucun artefact suivi. Sorties consommatrices : rapports coverage (scripts reporting), corrections en masse (scripts utils).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/utils/dev_tools/ -v
```

9 fichiers, **190 `def test_`** ; compléments : `tests/argumentation_analysis/utils/dev_tools/test_repair_utils.py` (8), `tests/project_core/dev_utils/test_verification_utils.py` (7).

## Frères et parent

Parent : [`../README.md`](../README.md) (utils). Frères documentés : [`../core_utils/`](../core_utils/README.md) (shim), [`../extract_repair/`](../extract_repair/README.md).

## Limites connues

- `visualization_utils` (459 l.) sans aucun importeur — candidat résiduel (décision coordinateur) ;
- l'import en bloc `utils/__init__.py:39` charge les 13 modules (dont le mort) pour tout consommateur de `utils` ;
- plusieurs modules n'ont jamais d'autre exécution que leurs tests (les 5 test-only).
