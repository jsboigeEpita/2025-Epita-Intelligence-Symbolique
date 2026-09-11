# `agents/extract/` — shim de compatibilité vers `agents.core.extract`

## Rôle et frontière

Un seul fichier : `__init__.py` (36 lignes), shim de redirection pure. Star-importe les modules de [`agents/core/extract/`](../core/README.md) (:11-13), ré-exporte `ExtractAgent` (:18), et aliase `sys.modules["...agents.extract.extract_agent"]` vers le module canonique (:26-28). Échoue **fort** en cas d'import cassé (raise explicite :29-36, anti-mock). Raison d'être : maintenir les imports historiques `from argumentation_analysis.agents.extract import X` (documentés dans `docs/guides/conventions_importation.md:167,171`).

## Composants publics

Tout ce que `agents.core.extract` exporte (transitif par star-import) + `ExtractAgent` explicite.

## Points d'entrée valides

**Aucun n'aboutit ici.** Tout le code production importe la cible `agents.core.extract` directement (`orchestration/analysis_runner_v2.py:72`, `operational/direct_executor.py:4`, `hierarchical/.../extract_agent_adapter.py:23`, `enhanced_pm_analysis_runner.py:67`, `ui/extract_editor/extract_marker_editor.py:50`). Le shim n'est exercé que par l'outillage de maintenance qui **vérifie la redirection** : `scripts/maintenance/test_imports.py:73,84`, `scripts/maintenance/tools/check_imports.py:40` (aucun workflow CI ne les lance, grep `.github/workflows/` vide).

## Amont / aval

- Amont : [`agents/core/extract/`](../core/README.md) — la vraie implémentation.
- Aval : code externe/legacy non présent dans le dépôt ; outillage de maintenance.

## Statut d'intégration

**compatibilité** — shim délibéré, non exercé en production (zéro importeur production mesuré), tenu fonctionnel par les vérificateurs de maintenance. Sa suppression éventuelle est un arbitrage coordinateur (précédent : ces shims documentés dans `docs/guides/conventions_importation.md`).

## Artefacts et lecteurs

Aucun.

## Tests représentatifs

Pas de test pytest. Vérification manuelle du shim :

```bash
conda run -n projet-is-roo-new --no-capture-output python scripts/maintenance/test_imports.py
```

(:73 vérifie le shim, :84 l'attribut `ExtractAgent`.)

## Frères et parent

Parent : [`../README.md`](../README.md). Cible : [`../core/`](../core/README.md).

## Limites connues

- commentaire fossile : `__init__.py:15` affirme exposer `setup_extract_agent` — ce symbole n'existe nulle part (grep plein dépôt) ; seul `ExtractAgent` est ré-exporté (:18) ;
- le README de la cible porte la même fossilie : [`../core/extract/README.md:29`](../core/extract/README.md) montre `from agents.extract import setup_extract_agent` ;
- la charge de maintenance est réelle mais minuscule (36 lignes, zéro logique).
