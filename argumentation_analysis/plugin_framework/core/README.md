# `plugin_framework/core/` — le carrefour de deux conventions de découverte, aucune fonctionnelle

Sous-paquet de `plugin_framework/`. **14 fichiers `.py`, 1 347 lignes** dans le sous-arbre
(4 fichiers / 270 lignes au premier niveau). Il porte les **contrats** (ce qu'est un plugin)
et les **deux chargeurs** concurrents.

## Rôle et frontière

Le module définit le vocabulaire du framework (`BasePlugin`, `PluginManifest`,
`ParameterSpec`) et deux mécanismes de découverte :

1. **découverte filesystem** — `plugin_loader.py` énumère `core/plugins/standard/` et
   importe chaque sous-répertoire comme un module ;
2. **découverte par manifeste** — un `plugin.yaml` décrit le plugin, un `PluginManifest`
   le valide.

Ces deux conventions **ne se parlent pas** : aucune ne produit un registre utilisable
(voir *Limites connues*). Frontière : le module ne connaît ni l'orchestration ni le
registre de capacités du système vivant.

## Composants publics

`core/__init__.py` fait **0 octet** : rien n'est ré-exporté, aucun `__all__`. Les noms
s'atteignent par chemin complet.

| Nom | Fichier | Statut mesuré |
|---|---|---|
| `PluginManifest` | `contracts.py:62` | modèle Pydantic **jamais instancié** en production ; son docstring est le **seul** endroit du dépôt qui nomme `plugin.yaml` |
| `plugin_type` | `contracts.py:69` | champ déclaré (`Literal["WORKFLOW","STANDARD"]`), **jamais lu** — unique occurrence dans le dépôt |
| `PluginLoader` | `plugin_loader.py` | **mort** : le nom de module qu'il fabrique ne résout pas |
| décorateurs d'enregistrement | `decorators.py` | surface de types, 0 usage production |

## Points d'entrée valides

**Aucun.** Le chargeur est appelable mais ne rend jamais un plugin. Le sous-paquet est
consommé par `plugin_framework/main.py` et `run_benchmark.py` — deux scripts eux-mêmes
invalides (voir le README parent).

## Amont / aval

- **Amont** : le système de fichiers (`core/plugins/standard/`).
- **Aval** : néant en production. Le seul importeur externe est une **garde de test** qui
  vérifie que le module *s'importe*, pas qu'il *sert*.

## Statut d'intégration

**Résiduel.** Le contrat est propre et testé ; le **chargement ne fonctionne pas**. Un
contrat que rien ne peut satisfaire est une déclaration, pas une intégration.

## Artefacts et lecteurs

Aucun artefact de sortie produit par le sous-paquet. Le seul fichier lu est le manifeste
(`plugin.yaml`), et il n'a **aucun lecteur** : la chaîne `plugin.yaml` n'apparaît qu'à
`contracts.py:64`, dans la docstring qui le décrit. Le format est donc **déclaré sans
implémentation**.

Une écriture existe néanmoins, en effet de bord du runner du paquet parent : il crée puis
supprime un plugin factice sous `plugins/standard/` (`run_benchmark.py:36-44`, `:114-115`).
Le détail et le risque de résidu sont dans le README parent.

## Tests représentatifs

Les tests de la zone couvrent le contrat des modèles et des décorateurs. Ils restent verts
alors que la découverte ne résout rien — c'est précisément pourquoi la panne est restée
invisible : **le test mesure le contrat, pas le chemin**.

## Frères et parent

**Parent** : `plugin_framework/` (lui-même résiduel). **Enfant** :
`core/plugins/standard/` (les plugins déclaratifs).

**Homonyme à ne pas confondre** : `argumentation_analysis/agents/core/plugin_loader.py`
est un **autre** chargeur, celui des plugins d'agents — c'est lui qui exige les champs
`name` / `entrypoint_module` / `entrypoint_class`. Deux fichiers nommés `plugin_loader.py`
dans le même dépôt, deux formats, deux sorts.

## Limites connues

1. **Le nom de module ne résout pas.** `plugin_loader.py:33` construit
   `f"src.core.plugins.standard.{item}"` — un préfixe `src.` **codé en dur** vers un paquet
   que le dépôt a supprimé (consolidation #321). La découverte rend donc un **registre
   vide** (`REGISTRY length = 0`, `No module named 'src'`), sans erreur remontée : le
   `try/except ImportError` du chargeur absorbe l'échec.
2. **Le manifeste est rejeté par son unique lecteur.** `plugin_manifest.json` porte
   `manifest_version`, `plugin_name`, `version`, `author`, `description`, `entry_point` ;
   le lecteur (`agents/core/plugin_loader.py:67-72`) exige `name`, `entrypoint_module`,
   `entrypoint_class`. **Zéro champ en commun** : la lecture lève `PluginManifestError`.
   Et ce lecteur est lui-même sans appelant de production.
3. **Deux conventions, aucune vivante** : ni la découverte filesystem ni la découverte par
   manifeste ne produit de plugin chargeable.
4. **`__init__.py` vide** : le carrefour n'expose aucune surface, ce qui interdit tout
   import de commodité et rend chaque usage explicite — mais aussi toute vérification
   « ce module exporte-t-il quelque chose ? ».
