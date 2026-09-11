# `plugin_framework/` — l'ancien framework de plugins, mort en production

Ce paquet est une **racine d'assemblage** : 2 scripts (`main.py`, `run_benchmark.py`) et
trois sous-arbres (`agents/`, `benchmarking/`, `core/`). Mesuré : **21 fichiers `.py`,
1 752 lignes** dans le sous-arbre (2 fichiers / 189 lignes au premier niveau).

**Aucun de ces deux scripts n'atteint son objet.** Ils s'importent, s'exécutent, et
échouent sur leur propre contrat. Le paquet est le **prédécesseur** de
`argumentation_analysis/plugins/` (voir *Frères et parent*) : le framework de plugins
vivant est ailleurs.

## Rôle et frontière

Le paquet prétend découvrir, charger et exécuter des *plugins* déclaratifs (un `plugin.yaml`,
un `plugin_manifest.json`, une classe `BasePlugin`). Il porte **deux conventions de
découverte concurrentes** — un chargeur par système de fichiers (`core/plugin_loader.py`)
et un chargeur par manifeste YAML — sans qu'aucune ne fonctionne.

Frontière : le paquet **ne fournit rien au reste du système**. `api/` ne l'importe jamais
(0 occurrence). Aucune capacité du `CapabilityRegistry` ne vient d'ici.

**Le paquet racine n'a pas d'`__init__.py`** : ce n'est pas un paquet Python régulier,
seulement un répertoire. Ses enfants (`core/`, `agents/`, `benchmarking/`) en ont un.

## Composants publics

`core/__init__.py` fait **0 octet** — le carrefour n'expose rien. Les noms publics sont
donc atteints par chemin complet :

| Nom | Fichier | Statut mesuré |
|---|---|---|
| `PluginLoader` | `core/plugin_loader.py` | **mort** — le chargeur ne peut pas résoudre (voir *Limites connues* n°1) |
| `BasePlugin`, `PluginMetadata`, `ParameterSpec` | `core/contracts.py` | **importé pour ses types**, jamais construit en production |
| décorateurs | `core/decorators.py` | idem — surface de types |
| `AgentLoader` | `agents/agent_loader.py` | 0 appelant production |
| `BenchmarkService` | `benchmarking/benchmark_service.py` | 0 appelant production |

## Points d'entrée valides

**Aucun.** Les deux scripts sont des entrées *déclarées*, pas *valides* :

- `main.py` — **8 appels sur 8 invalides à l'exécution** (`TypeError`, `AttributeError`,
  `ValidationError` selon l'appel : il invoque des signatures qui n'existent pas).
- `run_benchmark.py` — sort en `sys.exit(1)` (`:49-54`) : le registre qu'il interroge est
  vide, donc il n'a rien à mesurer.

Aucun des deux n'est référencé par `.github/workflows/` (0 occurrence) : même une entrée
manuelle ne les exécuterait pas de façon fiable.

## Amont / aval

- **Amont** : le système de fichiers (`core/plugins/standard/`), lu par deux chargeurs.
- **Aval** : néant. Les seuls consommateurs sont des **tests** et les README frères.

Le paquet ne reçoit ni état d'analyse ni configuration d'orchestration. Il n'est branché
sur rien.

## Statut d'intégration

**Résiduel — l'ensemble du paquet.** Trois raisons mesurées, chacune suffisante :

1. le chargeur par système de fichiers construit un nom de module (`src.…`) que le dépôt
   ne contient plus ;
2. le manifeste (`core/plugins/standard/plugin_manifest.json`) est **rejeté par le seul
   lecteur du format**, lui-même sans appelant de production ;
3. `plugin.yaml` n'a **aucun lecteur** dans le dépôt — la seule occurrence de la chaîne
   est la docstring qui le décrit (`core/contracts.py:64`).

## Artefacts et lecteurs

Le paquet ne produit **aucun artefact de sortie**, et **aucune surface d'export**. Il ne
lit que des déclarations de plugin (`plugin.yaml`, `plugin_manifest.json`,
`taxonomy_explorer/data/fallacy_families.yaml`).

En revanche il **écrit dans sa propre arborescence source**, en effet de bord :
`run_benchmark.py:36-44` fabrique un plugin factice
`core/plugins/standard/hello_world/__init__.py` au runtime, et le supprime en fin de
script (`:114-115`). Ce n'est pas une sortie, c'est une mutation transitoire du dépôt —
voir *Limites connues* n°7.

## Tests représentatifs

**82 passed** sur l'unique fichier de la zone,
`tests/unit/argumentation_analysis/test_plugin_framework.py` (`--disable-jvm-session`
requis, sinon orage de skips #2021). Ces tests couvrent le **contrat** des classes
(`contracts.py`, décorateurs), pas le chemin de découverte — c'est pourquoi ils restent
verts alors que le chargeur ne résout rien.

## Frères et parent

**Parent** : `argumentation_analysis/`.

**Frère vivant qui le remplace** : `argumentation_analysis/plugins/` — le framework de
plugins réellement câblé (`@kernel_function`, registre de capacités). Le présent paquet est
sa préfiguration abandonnée. Ne pas confondre les deux quand on cherche « le framework de
plugins » : un `grep plugin` mesure indifféremment l'ancien (mort) et le nouveau (vivant).

**Enfants** : `core/` (carrefour des conventions), `core/plugins/standard/` (les plugins
déclaratifs), `agents/`, `benchmarking/`.

**Enfants vides** : `core/plugins/workflows/` et `agents/personalities/` ne contiennent
qu'un `__init__.py` de **0 octet** et un README, **sans aucun importeur** dans le dépôt
(vérifié par recherche des deux chemins). Deux emplacements réservés par un plan jamais
exécuté — cf. #2102 §6.

## Limites connues

Relevé mesuré, **rien corrigé ici** (lot documentaire).

1. **Le chargeur ne peut pas résoudre — cause racine identifiée.** `core/plugin_loader.py:33`
   construit `module_name = f"src.core.plugins.standard.{item}"`. Le paquet `src/` a été
   **supprimé du dépôt** par la consolidation (#321) : il n'existe plus à la racine.
   Conséquence mesurée : la découverte rend un **registre vide** (`REGISTRY length = 0`,
   3 × `No module named 'src'`). Le préfixe codé en dur est la cause, pas un symptôme.
2. **`main.py` est un squelette non exécutable** : 8 appels sur 8 invalides au runtime.
3. **`plugin_type` n'est jamais lu** (`core/contracts.py:69`) : c'est l'unique occurrence
   du champ dans tout le dépôt — déclaré, jamais consommé.
4. **Deux conventions de découverte coexistent**, aucune fonctionnelle : chargeur
   filesystem et chargeur manifeste. Le manifeste est en outre rejeté par son unique
   lecteur (voir plus bas).
5. **README frère contredisant le code** : `benchmarking/README.md` décrit un runner
   fonctionnel ; mesuré, `run_benchmark.py` sort en `sys.exit(1)` (`:49-54`) sur un
   registre vide.
6. **Ce paquet n'est pas un paquet Python** : pas d'`__init__.py` à sa racine.
7. **`run_benchmark.py` mute le dépôt au runtime — résidu possible.** `:36-44` crée
   `core/plugins/standard/hello_world/__init__.py` **dans l'arborescence source**, puis
   `:114-115` le retire (`os.remove` + `shutil.rmtree`). Le chemin n'est **pas** couvert
   par `.gitignore` (`git check-ignore` ne le matche pas) : toute exception entre la
   création et le nettoyage laisse un fichier que `git status` montre comme ajoutable.
   Mesuré : le répertoire est **absent** aujourd'hui et n'est pas suivi par git — le
   nettoyage fonctionne quand le script va au bout ; c'est le cas d'échec qui est le
   risque. Même constat que l'issue #2102 (§2).
