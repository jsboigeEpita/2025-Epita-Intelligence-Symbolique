# `plugin_framework/` — l'ancien framework de plugins, retiré de la découverte

Ce paquet est une **racine d'assemblage** : plus aucun script, trois sous-arbres
(`agents/`, `benchmarking/`, `core/`). Mesuré après les retraits #2099/#2102 :
**14 fichiers `.py`, 1 365 lignes** dans le sous-arbre (aucun `.py` au premier
niveau).

**Le mécanisme de découverte de ce paquet est retiré, pas réparé (#2099).** La
carte des consommateurs mesurée sur `4c733b93` n'a nommé **aucun** appelant de
production pour aucun des trois chargeurs : le loader #1 n'était appelé que par
deux fossiles du même paquet, les loaders #2/#3 par les seuls tests. Les deux
plugins réels (`taxonomy_explorer`, `external_verification`) rejoignent le système
**par import direct** — ce chemin survit et est gardé par des tests positifs. Le
framework de plugins **vivant** est ailleurs : `argumentation_analysis/plugins/`
(voir *Frères et parent*).

## Rôle et frontière

Le paquet portait la découverte, le chargement et l'exécution de plugins
déclaratifs (`plugin.yaml`, `plugin_manifest.json`, `BasePlugin`). Depuis #2099 il
ne porte plus **aucun mécanisme de découverte** : ce qui reste est le contrat
(`core/plugins/interfaces.py`), les modèles Pydantic (`core/contracts.py`), un
guichet d'orchestration minimal et un mesureur de suite — tous alimentés par un
registre fourni par l'appelant.

Frontière : le paquet **ne fournit rien au reste du système**. `api/` ne l'importe
jamais (0 occurrence). Aucune capacité du `CapabilityRegistry` ne vient d'ici.

**Le paquet racine n'a pas d'`__init__.py`** : ce n'est pas un paquet Python régulier,
seulement un répertoire. Ses enfants (`core/`, `agents/`, `benchmarking/`) en ont un.

## Composants publics

`core/__init__.py` fait **0 octet** — le carrefour n'expose rien. Les noms publics sont
donc atteints par chemin complet :

| Nom | Fichier | Statut mesuré |
|---|---|---|
| `BasePlugin` | `core/plugins/interfaces.py` | **contrat canonique** — sous-classé par les deux plugins réels (garde `issubclass` exécutée) |
| `BasePlugin`, `PluginMetadata`, `ParameterSpec` | `core/contracts.py` | **importé pour ses types**, jamais construit en production |
| décorateurs | `core/decorators.py` | idem — surface de types |
| `OrchestrationService` | `core/services/orchestration_service.py` | guichet minimal, registre fourni par l'appelant |
| `BenchmarkService` | `benchmarking/benchmark_service.py` | 0 appelant production |

**Retirés (#2099)** : `core/plugin_loader.py`, `core/plugins/plugin_loader.py`,
`agents/agent_loader.py`, `run_benchmark.py`, le manifeste
`core/plugins/standard/plugin_manifest.json` et
`agents/simple_analyst/agent_manifest.json` — voir la section *Retrait* ci-dessous.

## Points d'entrée valides

**Aucun.** Le dernier script (`main.py`) a été retiré (#2102 §1) : fossile
désynchronisé d'au moins deux générations d'API (9 appels sur des API inexistantes),
sans importateur, jamais référencé par `.github/workflows/`. Le réécrire sur l'API
survivante aurait dupliqué la construction de registre que
`tests/integration/triage/test_workflow_execution.py` couvre déjà.

## Amont / aval

- **Amont** : néant — plus aucun mécanisme ne scanne le système de fichiers.
- **Aval** : néant. Les seuls consommateurs sont des **tests** et les README frères.

Le paquet ne reçoit ni état d'analyse ni configuration d'orchestration. Il n'est branché
sur rien.

## Statut d'intégration

**Résiduel — l'ensemble du paquet.** Le retrait #2099 a supprimé les trois raisons
majeures qui tenaient le statut à « résiduel » (préfixe `src.` mort, manifeste rejeté,
`plugin.yaml` sans lecteur) en supprimant les mécanismes eux-mêmes : un mécanisme sans
consommateur ne se répare pas, il se retire. Ce qui reste (contrat, modèles, guichet)
est propre, testé, et sans consommateur de production.

## Le retrait #2099 — qu'est-ce qui a été supprimé, et pourquoi

| Fichier retiré | Rôle | Raison (mesurée sur `4c733b93`) |
|---|---|---|
| `core/plugin_loader.py` | découverte filesystem (loader #1) | appelé uniquement par `main.py` (inexécutable) et `run_benchmark.py` ; construisait des modules `src.…` morts depuis #321 et avalait l'`ImportError` |
| `core/plugins/plugin_loader.py` | découverte par manifeste JSON (loader #2) | zéro appelant production ; ne voyait pas les 2 plugins réels (porteurs de `plugin.yaml`), et l'unique manifeste réel pointait vers un `main.py` inexistant |
| `agents/agent_loader.py` | découverte d'agents par manifeste | zéro appelant production ; l'unique manifeste pointait vers un `agent.py` inexistant |
| `run_benchmark.py` | runner de benchmark | **écrivait un plugin factice dans l'arborescence source au runtime** (#2102 §2) — supprimer le script supprime l'écriture ; aucun importateur |
| `core/plugins/standard/plugin_manifest.json` | manifeste du loader #2 | `entry_point: "main.py"` inexistant sur disque |
| `agents/simple_analyst/agent_manifest.json` | manifeste de l'AgentLoader | `entry_point: "agent.py"` inexistant sur disque |

## Le retrait #2102 — le reliquat

| Fichier retiré | Rôle | Raison |
|---|---|---|
| `main.py` | script d'assemblage (fossile) | 9 appels sur des API inexistantes (`PluginLoader(plugin_dirs=)`, `execute_request`, `response.request_id`…) ; aucun importateur, jamais référencé par CI ; le réécrire dupliquerait le test d'intégration |
| `agents/personalities/__init__.py` + `README.md` | coquille vide | `__init__.py` 0 octet, 0 importeur — emplacement réservé par un plan jamais exécuté (#2102 §6) |
| `core/plugins/workflows/__init__.py` + `README.md` | coquille vide | idem |

Les trois autres items de #2102 sont corrigés en place :
l'écriture runtime (§2) a disparu avec `run_benchmark.py` (ci-dessus) ; les
`BenchmarkService` jumeaux (§3) sont arbitrés par consommateurs — voir
`benchmarking/README.md` ; l'association métrique↔exécution (§4) est portée par
une identité explicite (`request_id`), le glissement par index est gardé rouge ;
le mode fantôme `workflow_execution` (§5) est retiré du contrat (construction
rejetée par la validation, garde en test).

Gardes : `tests/unit/argumentation_analysis/test_plugin_framework.py`
(`TestDiscoveryMechanismsWithdrawn` — les modules retirés lèvent `ImportError` ;
`TestRealPluginsByDirectImport` — les plugins réels s'instancient et une capacité
réelle s'exécute par le chemin de production).

## Artefacts et lecteurs

Le paquet ne produit **aucun artefact de sortie**, et **aucune surface d'export**. Il ne
lit plus que des déclarations documentaires (`plugin.yaml` ×2,
`taxonomy_explorer/data/fallacy_families.yaml` — cette dernière étant la seule pièce
réellement consommée par la production, hors framework).

L'écriture transitoire dans l'arborescence source (`run_benchmark.py` fabriquant un
plugin `hello_world/` au runtime) a **disparu avec son script**.

## Tests représentatifs

**68 tests** sur l'unique fichier de la zone,
`tests/unit/argumentation_analysis/test_plugin_framework.py` (`--disable-jvm-session`
requis, sinon orage de skips #2021) : contrats (`contracts.py`, décorateurs), guichet,
benchmark, **gardes de retrait et chemin vivant par import direct**. La chaîne
d'intégration `tests/integration/triage/test_workflow_execution.py` construit désormais
son registre directement depuis les manifestes des fixtures (`json` + `importlib`),
sans chargeur.

## Frères et parent

**Parent** : `argumentation_analysis/`.

**Frère vivant qui le remplace** : `argumentation_analysis/plugins/` — le framework de
plugins réellement câblé (`@kernel_function`, registre de capacités). Le présent paquet est
sa préfiguration abandonnée. Ne pas confondre les deux quand on cherche « le framework de
plugins » : un `grep plugin` mesure indifféremment l'ancien (mort) et le nouveau (vivant).

**Enfants** : `core/` (carrefour des conventions), `core/plugins/standard/` (les plugins
déclaratifs), `agents/`, `benchmarking/`. Les anciennes coquilles vides
(`core/plugins/workflows/`, `agents/personalities/`) ont été retirées (#2102 §6).

## Limites connues

Relevé mesuré, **rien corrigé ici** (hors retraits documentés ci-dessus).

1. **`plugin_type` n'est jamais lu** (`core/contracts.py`) : c'est l'unique occurrence
   du champ dans tout le dépôt — déclaré, jamais consommé.
2. **Ce paquet n'est pas un paquet Python** : pas d'`__init__.py` à sa racine.
3. **Deux `BenchmarkService` homonymes** coexistent dans le dépôt (celui-ci et
   `services/benchmark_service.py`, APIs incompatibles) — arbitrés par consommateurs
   (chacun n'a que des tests), la disambiguïsation est documentée des deux côtés et le
   sort du jumeau `services/` relève du triage #2137.
