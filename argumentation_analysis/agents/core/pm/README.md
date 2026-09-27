# 🔍 Agent PM d'Investigation (`SherlockEnqueteAgent`)

Ce paquet héberge l'agent d'enquête `SherlockEnqueteAgent` ([`sherlock_enquete_agent.py`](./sherlock_enquete_agent.py)), spécialisé dans le paradigme d'investigation Sherlock/Watson (Cluedo, hypothèses, JTMS).

[Retour au README Agents](../README.md)

> **Note (#2699)** : ce paquet hébergeait aussi `ProjectManagerAgent` (avec
> `pm_definitions.py` et `prompts.py`), le PM scripté à séquence fixe de
> l'ancienne pile conversationnelle. Sa retraite suit celle de son unique
> consommateur production, le runner PM amélioré (#2638/#2704). Le rôle de PM
> est porté aujourd'hui par le PM conversationnel inline
> (`orchestration/conversational_orchestrator.py`, RA-6 #1051) et par le PM
> générique de la factory (`agents/factory.py::create_project_manager_agent`,
> un `ChatCompletionAgent` construit depuis un fichier de prompt — il
> n'importait jamais cette classe).

## Rôle

`SherlockEnqueteAgent` hérite de `BaseAgent` (pas d'un PM) et orchestre une
enquête : formulation d'hypothèses, interactions avec l'état d'enquête
(`EnqueteStatePlugin`), raisonnement JTMS. Ses tests vivent dans
[`tests/agents/core/pm/test_sherlock_enquete_agent.py`](../../../../tests/agents/core/pm/test_sherlock_enquete_agent.py)
(authentiques, sans mocks — Phase 3A).
