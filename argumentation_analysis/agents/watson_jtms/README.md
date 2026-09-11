# `agents/watson_jtms/` — assistant JTMS de Watson (chaîne production morte au hub)

## Rôle et frontière

7 modules (1 342 lignes suivies) autour de `WatsonJTMSAgent` — l'assistant JTMS du binôme Sherlock/Watson. **Sans consommateur production** : la chaîne d'appels meurt au `jtms_communication_hub`, que plus personne n'importe.

## Composants publics

- `agent.py` (202 l.) — `WatsonJTMSAgent(JTMSAgentBase)` :10, 14 délégués async (`validate_sherlock_reasoning` :47 … `get_validation_summary` :190) ;
- `consistency.py` (169 l.) — `ConsistencyChecker` :15 ;
- `critique.py` (510 l.) — `CritiqueEngine` :67 + **placeholders** `JTMSAgentBase` :15, `ConflictResolution` :59 ;
- `synthesis.py` (135 l.) — `SynthesisEngine` :38 + placeholder `JTMSAgentBase` :14 ;
- `validation.py` (190 l.) — `FormalValidator` :4 (`prove_belief`, cache de validation) ;
- `models.py` (30 l.) — dataclasses `ValidationResult` :7, `ConflictResolution` :21 (la vraie) ;
- `utils.py` (516 l.) — 18 helpers privés (`_extract_logical_structure` :10 … `_calculate_text_similarity` :482).

## Points d'entrée valides

**Aucun.** Chaîne mesurée : `agents/watson_jtms_agent.py:3` (shim 5 lignes) → importé uniquement par `agents/jtms_communication_hub.py:21` (usages :735, :763, :1280, :1294, :1325) → **le hub lui-même a zéro importeur production**. `orchestration/conversational_orchestrator.py:2911-2913` importe `ConflictResolver` depuis `services/jtms/conflict_resolution.py` (logique extraite du hub, :4 du fichier extrait) — la docstring :2900 de l'orchestrateur mentionne encore le hub (fossile). `utils.py` et `models.py` ne sont importés que par des tests.

## Amont / aval

- Amont : `agents/jtms_agent_base.JTMSAgentBase` (la vraie base, agent.py:1), `services/jtms/extended_belief.JTMSSession` (agent.py:2).
- Aval : shim + hub → surface de tests uniquement.

## Statut d'intégration

**résiduel** — 0 importeur production (mesuré, grep plein dépôt import par import), maintenu vivant par ~228 fonctions de test. Sort à trancher par le coordinateur ; aucune suppression faite ici (mandat documentaire #2088).

## Artefacts et lecteurs

Aucun.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/test_watson_jtms.py tests/unit/argumentation_analysis/agents/test_watson_jtms_utils.py tests/unit/argumentation_analysis/agents/test_watson_jtms_models.py tests/unit/agents/test_watson_jtms_agent.py tests/unit/agents/test_jtms_communication_hub.py -v
```

139 + 44 + 18 + 14 + 13 `def test_` respectivement, + 4 fichiers dans `tests/integration/triage/`.

## Frères et parent

Parent : [`../README.md`](../README.md). Base : `../jtms_agent_base.py`. Services : [`../../services/jtms/`](../../services/jtms/README.md) (où vit le `ConflictResolver` extraction).

## Limites connues

- **placeholders dupliqués** : `class JTMSAgentBase` redéfinie en tête de `critique.py:15` et `synthesis.py:14` (commentaire :8-11 « Supposons que… ») — écrase la vraie base à l'import de ces modules ; `ConflictResolution` existe en double (placeholder `critique.py:59` vs dataclass réelle `models.py:21`) ;
- `__init__.py` vide (0 octet) ;
- imports inutilisés : `JTMSSession`/`datetime` (agent.py:2,7), `json`+`asyncio` (critique.py:2-3, synthesis.py:2-3), `Tuple` (consistency.py:7 — son propre commentaire l'admet).
