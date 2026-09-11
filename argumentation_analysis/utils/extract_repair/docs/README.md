# `utils/extract_repair/docs/` — documentation de la réparation de bornes d'extraits

## Rôle et frontière

`__init__.py` (2 lignes, commentaires sans code) + 1 document : `repair_extract_markers_report.md` (7 273 octets) — rapport sur la réparation des marqueurs de début/fin d'extraits défectueux (bornes introuvables/incorrectes), documentant l'agent `repair_extract_markers.py` et son notebook. Répertoire documentaire d'un package opérationnel ; **aucun code**.

## Composants publics

Aucun (l'`__init__` n'a pas de code).

## Points d'entrée valides

**Aucun** — rien ne lit ce chemin par programme. Seuls lecteurs : humains, via le README du parent ([`../README.md:34-35`](../README.md)) qui le référence.

## Amont / aval

- Amont : le package [`../`](../README.md) (auto-importé par `utils/__init__.py:40`) ; sujet du document : `../repair_extract_markers.py`.
- Aval : personne.

## Statut d'intégration

**actif-documentaire** — référence vivante du README parent (2 liens :34-35). Le document est le seul artefact suivi du répertoire.

## Artefacts et lecteurs

Lui-même. Les 2 rapports HTML que le README parent annonce aussi (`repair_report.html` :36, `verify_extracts_report.html` :37) sont des **sorties runtime non suivies** (absentes du dépôt).

## Tests représentatifs

Sans objet (répertoire documentaire).

## Frères et parent

Parent : [`../README.md`](../README.md) — c'est la sous-section « docs » documentée par le parent lui-même.

## Limites connues

- **chemin mort référencé par du code** : `../verify_extracts_with_llm.py:155,174` retombe sur `extract_repair/docs/extract_sources_updated.json` et `utils/cleanup_sensitive_files.py:130-131` globbe `extract_repair/docs/extract_sources_*.json` — ce fichier **n'existe plus** dans docs/ (fossilie de la disposition pré-#323) ; les fallbacks échouent silencieusement vers leurs autres chemins ;
- les rapports HTML annoncés par le parent ne sont jamais suivis (sorties runtime).
