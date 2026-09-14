# `plugin_framework/core/plugins/standard/` — deux plugins déclaratifs, expérimentaux

Le répertoire que le chargeur du framework était censé énumérer — le mécanisme est
retiré (#2099), les plugins y vivent par **import direct**. **5 fichiers `.py`,
911 lignes** dans le sous-arbre ; son premier niveau est un unique `__init__.py` de
**0 octet**.

## Rôle et frontière

Il héberge deux plugins « standard » — `external_verification/` et `taxonomy_explorer/` —
chacun décrit par un `plugin.yaml` et un `plugin.py`.

Frontière : ces plugins ne sont **pas branchés sur le registre de capacités** vivant.
Leur seule consommation réelle est **leur donnée** : `taxonomy_explorer/data/fallacy_families.yaml`
est lue par le détecteur de sophismes du système (`agents/`), indépendamment du framework.

## Composants publics

| Composant | Statut mesuré |
|---|---|
| `external_verification/plugin.py` | **expérimental** — importé pour ses types, jamais construit |
| `taxonomy_explorer/plugin.py` | **expérimental** — idem ; sous-classe réelle du contrat canonique depuis #2099 |
| `taxonomy_explorer/data/fallacy_families.yaml` | **vivant** — c'est la **seule** pièce du répertoire réellement consommée par la production |
| `plugin.yaml` (×2) | **déclaré sans lecteur** — aucune occurrence de ce nom hors docstring ; conservé comme documentation des capacités |
| `standard/__init__.py` | **0 octet** — aucune surface |

## Points d'entrée valides

**Aucun** par le framework (plus de chargeur, #2099). Le chemin vivant est l'import
direct : `agents/tools/analysis/fallacy_family_analyzer.py:20,24` et
`orchestration/fact_checking_orchestrator.py:28,31` — et la donnée YAML lue par le
détecteur de familles de sophismes.

## Amont / aval

- **Amont** : néant — plus aucun mécanisme de découverte (#2099).
- **Aval** : `argumentation_analysis/agents/` pour la donnée YAML ; rien pour le code des
  plugins.

## Statut d'intégration

**Expérimental.** Les deux plugins sont des squelettes cohérents, importables, jamais
instanciés en production. Le répertoire illustre le framework davantage qu'il ne le sert.

## Artefacts et lecteurs

Aucun artefact écrit **par les plugins eux-mêmes**. Une donnée lue
(`fallacy_families.yaml`) — la seule pièce qui compte, et elle est lue hors du framework.

L'écriture externe transitoire qui ciblait ce répertoire (le runner du paquet parent y
fabriquait un plugin `hello_world/` au runtime) a disparu avec son script (#2099).

## Tests représentatifs

Les tests couvrent les contrats et le parsing ; depuis #2099 ils gardent aussi le
chemin vivant — les plugins réels s'instancient et une capacité s'exécute par import
direct (`tests/unit/argumentation_analysis/test_plugin_framework.py::TestRealPluginsByDirectImport`).

## Frères et parent

**Parent** : `plugin_framework/core/`. **Frères** : ce sont les deux seuls plugins du
framework. Les plugins **vivants** du système sont dans `argumentation_analysis/plugins/`.

## Limites connues

1. **Chaque plugin porte son README feuille**, mais aucun ne décrit le framework qui les
   charge — d'où le présent README parent.

Historique résolu : l'appel mort `_calculate_context_relevance` et les imports jamais
consommés (`aiohttp`, `taxonomy_plugin`) ont été corrigés par #2189 (#2100) ; le
`BasePlugin` local factice et le manifeste commun illisible ont été retirés par #2099.
