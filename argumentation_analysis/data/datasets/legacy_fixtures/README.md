# `data/datasets/legacy_fixtures/` — fixtures relocalisées sans lecteur

## Rôle et frontière

4 fichiers JSON, sans `__init__.py` (chemin de données pur). Relocalisés depuis la racine `data/` lors d'#323 (commit `4a09a948b`). **Aucun lien avec le dataset chiffré canonique** (`data/extract_sources.json.gz.enc`) : ce sont des fixtures pédagogiques/synthétiques antérieures.

- `mystere_laboratoire_ia_cluedo.json` — scénario Cluedo pédagogique (structure mesurée : `cas_original`, `description`, `personnages` [`nom,role,motif,alibi,indices`], `lieux`, `armes`, `indices_contradictoires`, `solution_secrete` [`coupable,arme,lieu,methode`], `temoignages_complexes`) ;
- 3 × `synthetic_logical_propositions_20250609_*.json` — propositions logiques synthétiques (structure mesurée : `timestamp`, `propositions` [`id,text,domain,variables,predicates,connectors,quantifiers`], `domains_used`, `total_variables`, `total_predicates`, `generation_seed`).

## Composants publics

Aucun (données). Schémas documentés ci-dessus — clés et types uniquement, aucun contenu reproduit (discipline dataset).

## Points d'entrée valides

**Aucun.** Grep plein dépôt sur le nom du répertoire + les 4 noms de fichiers : zéro loader, zéro test (le seul hit `.py` est la liste d'exclusion de l'outillage documentaire `scripts/docs/readme_waves_2088.py:81`). Références documentaires uniquement : `CLAUDE.md:127` (note de relocalisation), le rapport d'inventaire #2088.

## Amont / aval

- Amont : génération historique (pré-relocalisation, racine `data/`).
- Aval : personne.

## Statut d'intégration

**résiduel** — fixtures archivées sans consommateur depuis la relocalisation. Candidats à l'arbitrage (retrait justifié vs maintien archivé) — aucune suppression faite ici (mandat documentaire #2088).

## Artefacts et lecteurs

Eux-mêmes ; lecteurs = humains via cette fiche et le `CLAUDE.md`.

## Tests représentatifs

Sans objet (aucun code ne les charge ; le scénario Cluedo opérationnel actuel vit dans `agents/oracle/` avec ses propres données).

## Frères et parent

Parent : `data/datasets/` (sans README). Sœur canonique : `data/extract_sources.json.gz.enc` (dataset chiffré, discipline privacy — cf. le [`README racine`](../../../README.md) et `CLAUDE.md` § Dataset Privacy Discipline).

## Limites connues

- la fixture Cluedo porte du contenu narratif (noms de personnages, solution) : toute réutilisation doit respecter la discipline opaque-surfaces (ne pas citer de contenu dans commit/PR/issue) ;
- 3 horodatages quasi identiques (23:07, 23:11, 23:14) suggèrent des générations successives dont seule la dernière a pu servir — sans lecteur, indécidable.
