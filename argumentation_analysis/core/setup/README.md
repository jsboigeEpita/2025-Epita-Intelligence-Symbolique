# `core/setup/` — installateurs d'outils binaires externes portables

## Rôle et frontière

Installateurs d'outils binaires externes vers `libs/` (racine du dépôt) : JDK/Octave/Node portables (`manage_portable_tools.py`) et Prover9/Mace4 LADR (`prover9_manager.py`). Le pipeline d'analyse n'importe jamais ce package : **l'aval consomme l'artefact installé, pas le module**.

N'est **pas** l'initialisation système du pipeline (`core/bootstrap.py`) ni le démarrage JVM/classpath Tweety (`core/jvm_setup.py` — n'importe rien de `core/setup`, vérifié). Sans `__init__.py`.

## Composants publics

`manage_portable_tools.py` :

- configs `JDK_CONFIG` (:35, OpenJDK 15.0.2), `OCTAVE_CONFIG` (:44), `NODE_CONFIG` (:51), `TOOLS_TO_MANAGE` (:67) ;
- `setup_single_tool` (:259), `setup_tools` (:354), téléchargement avec reprise HTTP Range (`_download_file` :72, variante async :148), décompression (:162), détection (:195) ;
- CLI `__main__` (:413-493) — `--tools-dir`, `--force-reinstall`, **`--install-prover9`** (:445).

`prover9_manager.py` :

- `Prover9Manager` (:34) — config LADR-2009-11A (:35), `get_prover9_executable_path` (:58), install Windows (:122) / Unix via `make` (:157), et **`_create_prover9_wrapper` (:214)** qui renomme `prover9.exe` → `.exe.original` et crée un `prover9.bat` anti-blocage — c'est ce wrapper que l'aval attend.

## Points d'entrée valides

- `python -m argumentation_analysis.core.setup.manage_portable_tools --install-prover9` — **seul point d'entrée réel** pour Prover9 (`Prover9Manager` n'est importé que par le CLI de son frère, :454) ;
- `project_core/environment/tool_installer.py:10,16` (`setup_tools`, avec repli sys.path) — mais son `ensure_tools_are_installed` n'est appelé que par son propre `__main__` de démo ;
- `scripts/utils/provision_tools.py:22,30` (`setup_tools`).

## Amont / aval

- Amont : miroirs de téléchargement externes (huaweicloud, cs.unm.edu).
- Aval via **artefacts** : `core/prover9_runner.py:6-7` exige `libs/prover9/bin/prover9.bat` (le wrapper :214) ; `core/mace4_runner.py` consomme le même zip LADR ; en production, `orchestration/invoke_callables.py:9888` appelle `run_prover9` via `asyncio.to_thread`.

## Statut d'intégration

- **Prover9/Mace4 : `actif`** — artefact réel sur disque (`libs/prover9/bin/prover9.bat` constaté) + consommation production (`invoke_callables.py:9888`).
- **JDK/Octave/Node portables : `compatibilité`** — importeurs = scripts utils et démo uniquement ; `libs/` réellement peuplé mais drift avec `JDK_CONFIG` (15.0.2 annoncée vs JDK 17 installé) ; la JVM du pipeline passe par `jvm_setup.py`, pas par ici.
- **Tweety via ce script : `déprécié`** — auto-déclaré : « La gestion de Tweety via ce script est obsolète. Les JARs doivent être placés manuellement » (:381-384).

## Artefacts et lecteurs

Installe sous `libs/` — entièrement **gitignoré** (`.gitignore` : `_temp_downloads/`, `libs/jdk-*/`, `libs/node-v*/`, `libs/*.jar`, …). Lecteurs : `prover9_runner`, `mace4_runner`, `jvm_setup`, `libs/README.md`.

## Tests représentatifs

**Aucun test pour `setup/`** (grep dans `tests/` : 0 match). L'aval est couvert :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/core/test_prover9_runner.py tests/integration/argumentation_analysis/agents/core/logic/test_external_provers_wired.py -v
```

## Frères et parent

Parent : [`../README.md`](../README.md) — documente `jvm_setup.py`, ignore `setup/`. `libs/README.md` documente le répertoire cible (drift : annonce `portable_jdk/`, réel `jdk-17…`).

## Limites connues

- **double racine d'installation** : `provision_tools.py:24` cible `argumentation_analysis/libs/` quand le canonique est `libs/` racine — les deux existent sur disque avec doublons ;
- `TOOLS_TO_MANAGE` (:67) constant mort (jamais lu ; `setup_tools` reconstruit sa liste) ; `subprocess` importé jamais utilisé (:10) ;
- Octave téléchargé en async fire-and-forget qui retourne `None` (:315-318) ;
- zéro test direct ; téléchargements depuis miroirs externes non épinglés par checksum au-delà de la reprise Range.
