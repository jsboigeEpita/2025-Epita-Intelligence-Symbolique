# `plugin_framework/core/plugins/workflows/` — coquille vide

## Rôle et frontière

Emplacement **réservé mais jamais rempli** pour les plugins « workflows » — plugins complexes orchestrant d'autres composants. Le contenu intégral du répertoire est un `__init__.py` de 0 octet.

N'est pas un package actif : les workflows réels du système vivent dans `argumentation_analysis/orchestration/` et `argumentation_analysis/pipelines/`.

## Composants publics

Aucun. Le `__init__.py` est vide (0 octet, lecture vérifiée).

## Points d'entrée valides

Aucun. Grep `plugins.workflows` / `plugins/workflows` sur tout le dépôt : zéro import Python, zéro référence par chaîne dans du code (les mentions sont dans la documentation et les inventaires uniquement).

Le README parent (`core/plugins/README.md:11`) prétend que le chargeur scanne `standard/` et `workflows/` — mais ce chargeur (JSON) ne matche rien dans l'un ni dans l'autre (voir [`core/services/README.md`](../../services/README.md), statut).

## Amont / aval

Sans objet (vide).

## Statut d'intégration

**résiduel** — créé par la migration #34 (commit `738bf4f2f`, jamais retouché depuis), jamais peuplé. Le plan d'origine qui justifiait ce répertoire (déplacer `informal_fallacy/` ici, `docs/architecture/fallacy_operational_plan.md:78-80` et :487-498) n'a jamais été exécuté ; `docs/architecture/fallacy_consolidation_plan.md:62,731` ne l'annonce plus.

## Artefacts et lecteurs

Aucun.

## Tests représentatifs

Aucun — rien à exécuter.

## Frères et parent

- Parent : [`core/plugins/README.md`](../README.md) — décrit un mécanisme manifest JSON incompatible avec les `plugin.yaml` réels des plugins présents.
- Frères peuplés : [`standard/external_verification/`](../standard/external_verification/README.md) et [`standard/taxonomy_explorer/`](../standard/taxonomy_explorer/README.md) (documentés dans ce même lot).

## Limites connues

Répertoire-package vide maintenu en vie sans consommateur ni plan actif — candidat à suppression, sous réserve du cleanup gate du dépôt (justification par fichier obligatoire ; aucune suppression dans ce lot documentaire).
