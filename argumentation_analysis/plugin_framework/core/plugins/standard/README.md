# `plugin_framework/core/plugins/standard/` — deux plugins déclaratifs, expérimentaux

Le répertoire que le chargeur du framework est censé énumérer. **5 fichiers `.py`,
919 lignes** dans le sous-arbre ; son premier niveau est un unique `__init__.py` de
**0 octet**.

## Rôle et frontière

Il héberge deux plugins « standard » — `external_verification/` et `taxonomy_explorer/` —
chacun décrit par un `plugin.yaml` et un `plugin.py`, et un manifeste commun
`plugin_manifest.json`.

Frontière : ces plugins ne sont **pas branchés sur le registre de capacités** vivant.
Leur seule consommation réelle est **leur donnée** : `taxonomy_explorer/data/fallacy_families.yaml`
est lue par le détecteur de sophismes du système (`agents/`), indépendamment du framework.

## Composants publics

| Composant | Statut mesuré |
|---|---|
| `external_verification/plugin.py` | **expérimental** — importé pour ses types, jamais construit |
| `taxonomy_explorer/plugin.py` | **expérimental** — idem ; porte en outre un appel mort (n°1 ci-dessous) |
| `taxonomy_explorer/data/fallacy_families.yaml` | **vivant** — c'est la **seule** pièce du répertoire réellement consommée par la production |
| `plugin_manifest.json` | **mort** — rejeté par son unique lecteur (voir README parent `core/`) |
| `plugin.yaml` (×2) | **déclaré sans lecteur** — aucune occurrence de ce nom hors docstring |
| `standard/__init__.py` | **0 octet** — aucune surface |

## Points d'entrée valides

**Aucun** par le framework. Le chemin vivant est indirect : la donnée YAML est lue par le
détecteur de familles de sophismes, pas par un chargeur de plugins.

## Amont / aval

- **Amont** : découverte filesystem (`core/plugin_loader.py`) — qui échoue.
- **Aval** : `argumentation_analysis/agents/` pour la donnée YAML ; rien pour le code des
  plugins.

## Statut d'intégration

**Expérimental.** Les deux plugins sont des squelettes cohérents, importables, jamais
instanciés en production. Le répertoire illustre le framework davantage qu'il ne le sert.

## Artefacts et lecteurs

Aucun artefact écrit **par les plugins eux-mêmes**. Une donnée lue
(`fallacy_families.yaml`) — la seule pièce qui compte, et elle est lue hors du framework.

Ce répertoire est en revanche la **cible d'une écriture externe transitoire** : le runner
du paquet parent y fabrique un plugin `hello_world/` au runtime, puis le supprime
(`run_benchmark.py:35-44`, `:114-115`). Normalement rien n'en subsiste ; une interruption
entre les deux laisse un résidu non ignoré par git. Cf. README parent, *Limites connues* n°7.

## Tests représentatifs

Les tests couvrent les contrats et le parsing ; ils n'exercent pas le chargement réel
(le chargeur ne résout pas, cf. README parent).

## Frères et parent

**Parent** : `plugin_framework/core/`. **Frères** : ce sont les deux seuls plugins du
framework. Les plugins **vivants** du système sont dans `argumentation_analysis/plugins/`.

## Limites connues

1. **Appel vers une méthode qui n'existe pas.** `taxonomy_explorer/plugin.py:210` appelle
   `self._calculate_context_relevance(...)` ; la seule définition du fichier est
   `_calculate_contextual_relevance` (`:293`). Écart **appel/définition**, pas variante de
   nommage : au runtime, c'est un `AttributeError`. Vérifié par recherche des deux
   orthographes dans tout le dépôt — l'orthographe appelée n'a **aucune** définition.
2. **`BasePlugin` recopié localement.** `taxonomy_explorer/plugin.py:21` définit sa propre
   classe `BasePlugin` au lieu d'importer le contrat — la duplication rend le contrat
   inopérant (deux objets différents portent le même nom).
3. **Imports jamais consommés** : `aiohttp` (`:8`) et `taxonomy_plugin` (`:142`) sont
   importés sans être utilisés — deux dépendances déclarées pour rien.
4. **Le manifeste commun ne peut pas être lu** par le seul lecteur du format (champs
   incompatibles, cf. README `core/`).
5. **Chaque plugin porte son README feuille**, mais aucun ne décrit le framework qui les
   charge — d'où le présent README parent.
