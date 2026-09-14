# `agents/extract/` — shim de compatibilité vers `agents.core.extract`

## Rôle et frontière

Un seul fichier : `__init__.py` (36 lignes), shim de redirection pure. Star-importe les modules de [`agents/core/extract/`](../core/README.md) (:11-13), ré-exporte `ExtractAgent` (:19), et aliase le module `extract_agent` vers sa cible canonique sous les **trois** formes d'accès — attribut de package et `sys.modules` (:23-28). Échoue **fort** en cas d'import cassé (raise explicite :29-36, anti-mock). Raison d'être : maintenir les imports historiques `from argumentation_analysis.agents.extract import X` (documentés dans `docs/guides/conventions_importation.md:167,171`).

## Composants publics

Tout ce que `agents.core.extract` exporte (transitif par star-import) + `ExtractAgent` explicite.

## Points d'entrée valides

**Aucun n'aboutit ici.** Tout le code production importe la cible `agents.core.extract` directement (`orchestration/analysis_runner_v2.py:72`, `operational/direct_executor.py:4`, `hierarchical/.../extract_agent_adapter.py:23`, `enhanced_pm_analysis_runner.py:67`, `ui/extract_editor/extract_marker_editor.py:50`). Le shim n'est exercé que par l'outillage de maintenance qui **vérifie la redirection** : `scripts/maintenance/test_imports.py:80,90`, `scripts/maintenance/tools/check_imports.py:40` (aucun workflow CI ne les lance, grep `.github/workflows/` vide).

## Amont / aval

- Amont : [`agents/core/extract/`](../core/README.md) — la vraie implémentation.
- Aval : code externe/legacy non présent dans le dépôt ; outillage de maintenance.

## Statut d'intégration

**compatibilité** — shim délibéré, non exercé en production (zéro importeur production mesuré), tenu fonctionnel par les vérificateurs de maintenance (`scripts/maintenance/test_imports.py` — réparé #2122 : il mourait en `NameError` avant la première vérification — et `scripts/maintenance/tools/check_imports.py`) et par la garde pytest `tests/unit/argumentation_analysis/agents/test_extract_shim_2122.py`. Sa suppression éventuelle est un arbitrage coordinateur (précédent : ces shims documentés dans `docs/guides/conventions_importation.md`).

## Artefacts et lecteurs

Aucun.

## Tests représentatifs

Pas de test pytest. Vérification manuelle du shim :

```bash
conda run -n projet-is-roo-new --no-capture-output python scripts/maintenance/test_imports.py
```

(:80 vérifie le module du shim, :90 l'attribut `extract_agent` de ce shim.)

## Frères et parent

Parent : [`../README.md`](../README.md). Cible : [`../core/`](../core/README.md).

## Limites connues

- Corrigé (#2122) — le commentaire d'origine annonçait exposer `setup_extract_agent`,
  symbole qui n'a **jamais** existé (aucune définition dans le dépôt) ; il décrit
  désormais ce que le module fait réellement.
- Corrigé (#2122) — **l'alias n'était posé que dans `sys.modules`**. `import
  ...extract.extract_agent` et `from ...extract import extract_agent` rendaient
  bien le module canonique, mais `getattr(pkg, "extract_agent")` levait
  `AttributeError` : c'est le machinery d'import qui pose l'attribut sur le
  package, pas l'affectation `sys.modules`. Les trois formes concordent
  désormais.
- Corrigé (#2122) — la fausse API `setup_extract_agent` était exposée comme
  appelable par quatre surfaces documentaires (ce README, celui de la cible,
  `agents/docs/exemples_utilisation.md` et
  `docs/reference/agents/extract_agent_api.md`). Elles montrent maintenant la
  vraie API — `ExtractAgent(kernel=..., agent_name=...)` puis
  `setup_agent_components(llm_service_id=...)`. Leur régression rougit
  `test_extract_shim_2122.py::TestPhantomStaysGone`.
- Corrigé (#2122) — `scripts/maintenance/test_imports.py` appelait
  `test_module_import_by_name`, helper inexistant : il mourait en `NameError`
  avant sa **première** vérification, donc il ne tenait rien du tout. Réparé,
  il rend 15/15.
- Reste hors périmètre (constat de chemin, aucune modification) :
  `tests/unit/argumentation_analysis/test_setup_extract_agent_real.py` est
  **vert en ne mesurant rien** — son `ExtractAgent(name=..., description=...)`
  lève un `TypeError` (le vrai constructeur exige `kernel`) que
  `except Exception: return False` avale, et `unittest` ignore la valeur de
  retour. Le fichier porte en outre le nom du fantôme.
- La charge de maintenance est réelle mais minuscule (36 lignes, zéro logique).
