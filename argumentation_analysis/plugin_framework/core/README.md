# `plugin_framework/core/` — le carrefour du contrat, sans mécanisme de découverte

Sous-paquet de `plugin_framework/`. **12 fichiers `.py`, 1 205 lignes** dans le sous-arbre
(3 fichiers / 214 lignes au premier niveau : `contracts.py`, `decorators.py`,
`interfaces.py`). Il porte les **contrats** (ce qu'est un plugin) — et **plus aucun
chargeur** : les deux mécanismes de découverte concurrents ont été retirés (#2099),
aucun n'ayant d'appelant de production.

## Rôle et frontière

Le module définit le vocabulaire du framework : le contrat canonique `BasePlugin`
(`plugins/interfaces.py`, un marqueur ABC vide), les modèles Pydantic
(`PluginManifest`, `ParameterSpec`, `BenchmarkResult`, …) et les décorateurs
d'enregistrement. Les plugins réels sont joints au système **par import direct** —
il n'existe plus de découverte.

Frontière : le module ne connaît ni l'orchestration ni le registre de capacités du
système vivant.

## Composants publics

`core/__init__.py` fait **0 octet** : rien n'est ré-exporté, aucun `__all__`. Les noms
s'atteignent par chemin complet.

| Nom | Fichier | Statut mesuré |
|---|---|---|
| `BasePlugin` | `plugins/interfaces.py` | **contrat canonique** — sous-classé par les deux plugins réels (`taxonomy_explorer`, `external_verification`) |
| `PluginManifest` | `contracts.py` | modèle Pydantic **jamais instancié** en production ; son docstring est le **seul** endroit du dépôt qui nomme `plugin.yaml` |
| `plugin_type` | `contracts.py` | champ déclaré (`Literal["WORKFLOW","STANDARD"]`), **jamais lu** — unique occurrence dans le dépôt |
| décorateurs d'enregistrement | `decorators.py` | surface de types, 0 usage production |

**Retirés (#2099)** : `plugin_loader.py` (découverte filesystem — construisait des
modules `src.…` morts depuis #321 et avalait l'`ImportError`) et
`plugins/plugin_loader.py` (découverte par manifeste JSON — zéro appelant production,
ne voyait pas les plugins réels). Voir le README parent, section *Le retrait #2099*.

## Points d'entrée valides

**Aucun.** Le sous-paquet est consommé par les plugins réels (import direct du
contrat et des modèles) et par les tests. Le seul script qui l'appelait en
production-nominale (`main.py`) est un fossile (voir le README parent).

## Amont / aval

- **Amont** : néant — plus aucun mécanisme ne scanne le système de fichiers.
- **Aval** : les deux plugins réels (`plugins/standard/`), le guichet
  (`services/orchestration_service.py`), le mesureur (`benchmarking/`), les tests.

## Statut d'intégration

**Résiduel.** Le contrat est propre, testé et désormais **honorable** : les deux
plugins réels le sous-classent réellement (corrigé #2099 — `taxonomy_explorer`
importait une copie locale factice). Mais rien en production n'instancie ces
plugins par ce carrefour : ils vivent par import direct.

## Artefacts et lecteurs

Aucun artefact de sortie produit par le sous-paquet. Le seul fichier déclaré lu,
`plugin.yaml`, n'a **aucun lecteur** : la chaîne n'apparaît qu'à `contracts.py`,
dans la docstring qui le décrit. Le format est donc **déclaré sans
implémentation** — conservé comme documentation des capacités (#2099 : la
conversion YAML→JSON a été rejetée, aucun consommateur réel ne la justifie).

L'écriture runtime dans l'arborescence source (plugin factice créé par
`run_benchmark.py` sous `plugins/standard/`) a disparu avec son script (#2099).

## Tests représentatifs

Les tests de la zone couvrent le contrat des modèles et des décorateurs, **et
depuis #2099 les gardes de retrait** : les modules retirés lèvent `ImportError`,
et les plugins réels s'instancient par import direct avec une capacité exécutée
(`tests/unit/argumentation_analysis/test_plugin_framework.py`).

## Frères et parent

**Parent** : `plugin_framework/` (lui-même résiduel). **Enfants** :
`plugins/standard/` (les plugins déclaratifs), `services/` (le guichet).

**Homonyme à ne pas confondre** : `argumentation_analysis/agents/core/plugin_loader.py`
est un **autre** chargeur, celui des plugins d'agents — c'est lui qui exige les champs
`name` / `entrypoint_module` / `entrypoint_class`. Deux fichiers nommés
`plugin_loader.py` coexistaient dans le même dépôt, deux formats, deux sorts — le
présent n'existe plus.

## Limites connues

1. **`__init__.py` vide** : le carrefour n'expose aucune surface, ce qui interdit tout
   import de commodité et rend chaque usage explicite — mais aussi toute vérification
   « ce module exporte-t-il quelque chose ? ».
2. **`plugin_type` déclaré, jamais lu** (`contracts.py`) — unique occurrence du dépôt.
3. **`workflow_execution` déclaré au contrat, jamais implémenté** — réponse d'erreur
   systématique au guichet — cf. #2102.
