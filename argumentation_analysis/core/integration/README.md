# `core/integration/` — contournement Python/Clingo du solveur Java défectueux

## Rôle et frontière

Un seul module : `tweety_clingo_utils.py` (206 lignes, 2 fonctions) — contournement Python par `subprocess` du `ClingoSolver` Java défectueux (ASP/Clingo) : invoque le binaire `clingo`, parse sa sortie « Answer: » et reconstruit des `AnswerSet`/`ASPAtom` **Java** via `JClass` + classloader fourni.

N'est **pas** l'intégration JVM (`core/jvm_setup.py` — qui n'importe rien de ce package, vérifié) ni un bridge Tweety métier.

## Composants publics

- `check_clingo_installed_python_way` (:19) — subprocess `clingo --version`, retourne un `jpype_instance.JBoolean` ;
- `get_clingo_models_python_way` (:49) — subprocess clingo sur fichier ASP, parse stdout, reconstruit les objets Java, retourne une `ArrayList` Java ; **liste vide sur tout échec** (échec silencieux par conception).

## Points d'entrée valides

**Aucun** — grep `tweety_clingo_utils` / `core.integration` sur tout le dépôt : 0 importeur .py (production, tests, scripts). La survie sans importeur est **documentée dans le module lui-même** (`tweety_clingo_utils.py:1-4`) : `docs/reports/EXTERNAL_SOLVER_AUDIT_FP9.md` cite ces helpers comme le bypass Python préexistant du chemin Java bogué ; la suppression n'a de sens qu'après que FP-9 a absorbé la technique (arbitrage #1960).

## Amont / aval

- Amont : le binaire `clingo` (téléchargé par `core/jvm_setup.py` `download_clingo` vers `ext_tools/clingo/`), un `jpype_instance` passé en argument.
- Aval : aucun — référence technique citée par l'audit FP9 uniquement.

## Statut d'intégration

**résiduel** (survie documentée par design) — issu d'un fix de tests (`00cb8c167`), déplacé depuis `project_core` (`4aa4ce20b`), orphelin d'appelant, conservé comme preuve technique référencée par l'audit.

## Artefacts et lecteurs

Aucun fichier écrit ; exécute un binaire externe en lecture ; logs logger module.

## Tests représentatifs

Aucun — `pytest argumentation_analysis/core/integration` ne collecte rien (pas de fichier `test_*`).

## Frères et parent

Parent : [`../README.md`](../README.md) — documente les `.py` racine de `core/` ; ne mentionne pas `integration/`. Frère avec README : `communication/`.

## Limites connues

- `get_clingo_models_python_way` avale toute exception et retourne une liste vide — un échec réel est indistinguable d'« aucun modèle » ;
- l'audit FP9 cite « line 14 »/« line 44 » pour des définitions réelles :19/:49 (dérive après reformatage) ;
- dépend d'un classloader JPype cohérent passé par l'appelant (jamais garanti par contrat) ; codes retour acceptés `[10, 20, 30]`.
