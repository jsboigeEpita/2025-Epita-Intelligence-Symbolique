# `pipelines/orchestration/orchestrators/specialized/` — wrappers de compatibilité orphelins

## Rôle et frontière

Deux **wrappers de compatibilité minces** autour des orchestrateurs réels :

- `CluedoOrchestratorWrapper` (`cluedo_orchestrator.py:27`) — le constructeur (:28-36) instancie `CluedoExtendedOrchestrator` ; `run_investigation(text)` (:38-68) appelle `run_cluedo_oracle_game` (importé :18-19 **sous l'alias `run_cluedo_game`**, trompeur pour les grep) avec `max_iterations=5`, retourne l'historique + un résumé d'état d'enquête.
- `ConversationOrchestratorWrapper` (`conversation_orchestrator.py:22`) — le constructeur (:23-27, défaut `mode="advanced"`) instancie le `ConversationOrchestrator` racine ; `run_conversation(text)` (:29-43) délègue après une garde `hasattr` (:34).

N'est **pas** le lieu des orchestrateurs réels — tous vivent dans [`orchestration/`](../../../../orchestration/README.md) racine et y sont consommés directement :

| Implémentation réelle | Statut mesuré |
|---|---|
| `orchestration/conversational_orchestrator.py` (`run_conversational_analysis`) | **actif** — c'est lui que `run_orchestration.py --mode conversational` utilise (:645-646), pas ce wrapper |
| `orchestration/cluedo_extended_orchestrator.py` (`run_cluedo_oracle_game`) | **actif** — `run_orchestration.py:817-818` (`--mode cluedo`), `service_manager.py:81`, `cluedo_runner.py:8`, et ce wrapper |
| `orchestration/conversation_orchestrator.py` (1045 l., 5 modes) | **actif** — `service_manager.py:84`, `orchestration/__init__.py:11`, ~10 scripts |
| `orchestration/cluedo_orchestrator.py` (v1, Sherlock↔Watson) | quasi-résiduel — scripts de validation et tests only |

## Composants publics

Les 2 wrappers ci-dessus — c'est tout.

## Points d'entrée valides

**Aucun.** Grep `CluedoOrchestratorWrapper(` / `ConversationOrchestratorWrapper(` sur tout le dépôt : **zéro instanciation** (production ni tests). Seule référence : le ré-export du `__init__.py` parent (:39-42). Le dict `specialized_orchestrators` que consomme `select_specialized_orchestrator` (`execution/strategies.py:321-332`) n'est peuplé **nulle part en production** — seuls les tests l'injectent en mock.

## Amont / aval

- Amont : `orchestration/cluedo_extended_orchestrator`, `orchestration/cluedo_runner`, `orchestration/conversation_orchestrator`, `config/settings`.
- Aval : rien — dicts de résultats en retour, aucun fichier écrit.

## Statut d'intégration

**résiduel** — wrappers orphelins, reliquat de la modularisation `83f3ad3aa` dont la famille a été progressivement vidée : #215 (archive du shim RealLLM), #887 (suppression de 2 orchestrateurs vides), #936 (nettoyage du résidu) — trace dans `__init__.py:43` (« LogicOrchestratorWrapper and RealLLMOrchestratorWrapper removed »).

### La coquille parent `orchestrators/` (documentée, pas supprimée)

`pipelines/orchestration/orchestrators/` contient **exactement un enfant, `specialized/`**, aucun fichier direct, aucun `__init__.py` (namespace package implicite — comme tous les sous-répertoires du paquet). Ses seules références par chaîne dans le dépôt : les 2 imports du `__init__.py` parent (:39-40) et 3 mentions documentaires. Sans les wrappers, le répertoire entier partirait avec eux — statut de coquille résiduelle (#2055), conservé ici conformément au mandat documentaire #2088 (aucune suppression).

## Artefacts et lecteurs

Aucun (rendu en mémoire).

## Tests représentatifs

Aucun test dédié aux wrappers (zéro instanciation). Couverture indirecte : la garde d'import #2076 exécute transitivement leurs imports via le `__init__.py` parent :

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/pipelines/test_import_guard_2076.py -v
```

## Frères et parent

Parent (coquille) : `orchestrators/` — sans README propre, statut documenté ci-dessus. Grand-parent : [`../../README.md`](../../README.md). Frères : [`../../analysis/`](../../analysis/README.md), [`../../config/`](../../config/README.md), [`../../core/`](../../core/README.md), [`../../execution/`](../../execution/README.md).

## Limites connues

- `ConversationOrchestratorWrapper(mode="advanced")` : « advanced » n'est **pas un mode reconnu** par l'orchestrateur réel (micro/demo/trace/enhanced/real, `conversation_orchestrator.py:518-536`) → tombe dans le `else` → agents simulés de démo, silencieusement ;
- `.pyc` fossiles dans `specialized/__pycache__/` (`logic_orchestrator`, `real_llm_orchestrator` — fichiers `.py` supprimés par #887/#936, bytecode jamais nettoyé) ;
- garde défensive inutile :34 (`hasattr` sur une méthode qui existe toujours) ;
- l'alias d'import `run_cluedo_game` masque le nom réel dans les grep.
