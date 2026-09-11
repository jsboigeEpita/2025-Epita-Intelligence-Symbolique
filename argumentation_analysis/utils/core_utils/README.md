# `utils/core_utils/` — shim déprécié vers `core.utils` (zéro consommateur)

## Rôle et frontière

Un seul fichier : `__init__.py` (11 lignes) — star-import de [`core/utils/`](../../core/README.md) (:4) + `DeprecationWarning` à chaque import (:7-11). Shim de migration : l'ancien chemin `argumentation_analysis.utils.core_utils` redirige vers le canonique `argumentation_analysis.core.utils`.

## Composants publics

Tout ce que `core.utils` exporte (transitif). Aucun code propre.

## Points d'entrée valides

**Aucun.** Grep plein dépôt (production, scripts, api, tests) : **0 importeur** — la migration a été menée à terme (commit `d5869501e` « migrate 12 callers to canonical path ») et le shim est resté derrière. Les tests vivant dans `tests/unit/argumentation_analysis/utils/core_utils/` importent le canonique (vérifié `test_error_management.py:6`), pas le shim.

## Amont / aval

- Amont : [`core/utils/`](../../core/README.md).
- Aval : personne.

## Statut d'intégration

**résiduel** — shim déprécié à zéro consommateur, émettant un warning que plus personne ne voit. Sort à trancher par le coordinateur (suppression = PR code avec justification Cleanup Gate).

## Artefacts et lecteurs

Aucun. Fossilie documentaire : `docs/technical/structure_projet.md:202,209,215` étiquette encore des liens `utils/core_utils/text_utils.py` tout en pointant vers `core/utils/text_utils.py` (le chemin affiché est faux, la cible juste).

## Tests représentatifs

Aucun test ne cible le shim lui-même. La suite `tests/unit/argumentation_analysis/utils/core_utils/` (p.ex. `test_cli_utils.py`, `test_error_management.py`) teste le **canonique** `core.utils`.

## Frères et parent

Parent : [`../README.md`](../README.md) (utils). Cible : [`../../core/`](../../core/README.md).

## Limites connues

- tout import déclenche un `DeprecationWarning` invisible (personne n'importe) ;
- la fossilie `structure_projet.md` propage l'ancien chemin dans la doc technique.
