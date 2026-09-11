# `agents/channels/` — canal SK en mémoire pour l'agent d'extraction

## Rôle et frontière

Un seul module : `volatile_agent_channel.py` (57 lignes) — `VolatileAgentChannel(AgentChannel)` (:17), adaptation du protocole *channel* de Semantic Kernel avec historique en mémoire (`receive` :27, `invoke` :32, `get_history` :41, `reset` :47, `invoke_stream` :52). Sans `__init__.py` : namespace package implicite, importable par chemin complet. La frontière est volontairement minuscule : c'est un adaptateur de protocole, pas une abstraction.

## Composants publics

- `VolatileAgentChannel` (`volatile_agent_channel.py:17`) — unique symbole public.

## Points d'entrée valides

Aucun direct. Unique consommateur : `ExtractAgent.create_channel()` (`agents/core/extract/extract_agent.py:265-267`), activé par la machinerie `AgentGroupChat` de SK en mode conversationnel. Chaînes d'entrée qui atteignent ce code : `main_orchestrator.py` → `orchestration/analysis_runner_v2.py:72,227` ; `scripts/orchestration/pipelines/run_rhetorical_analysis_pipeline.py:20` ; mode hiérarchique `orchestration/hierarchical/operational/agent_registry.py:67` → `adapters/extract_agent_adapter.py:23,88`.

## Amont / aval

- Amont : `semantic_kernel.agents.channels.agent_channel.AgentChannel` (:10).
- Aval : SK `AgentGroupChat` (le canal est consommé par le runtime SK, pas par notre code).

## Statut d'intégration

**actif-spécialisé** — exactement un importeur production (`extract_agent.py:45-46`), lui-même importé par 4 runners production ([`analysis_runner_v2.py:72`](../core/README.md) ; cf. chaînes ci-dessus). Mono-consommateur par conception : le protocole channel n'a pas d'autre utilisateur dans le dépôt.

## Artefacts et lecteurs

Aucun. L'historique vit en mémoire, rien n'est persisté.

## Tests représentatifs

**Aucun test n'existe** (grep `VolatileAgentChannel` dans `tests/` : vide) — classe câblée dans le mode conversationnel sans couverture propre ; sa couverture de fait est celle des e2e conversationnels.

## Frères et parent

Parent : [`../README.md`](../README.md). Consommateur : [`../core/`](../core/README.md) (extraction). Pas de frère documenté.

## Limites connues

- zéro test dédié ;
- sans `__init__.py` — namespace implicite, découvert par le packaging (cf. le précédent mesuré sur [`../../integrations/`](../../integrations/README.md)) ;
- la classe suppose que `agent.invoke(history)` existe sur l'agent passé — contrat non vérifié statiquement (typage `"Agent"` string).
