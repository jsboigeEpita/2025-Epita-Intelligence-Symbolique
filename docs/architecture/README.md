# Architecture du Système d'Analyse Argumentative

Ce document décrit l'architecture du système, qui est conçue pour être modulaire, extensible et robuste. La structure repose sur une séparation claire des préoccupations entre le cœur logique et les agents spécialisés.

## Arborescence de l'Architecture Fondamentale

La structure des répertoires a été établie pour matérialiser les principes de conception de l'architecture. Voici une vue de l'arborescence :

```
D:\DEV\2025-EPITA-INTELLIGENCE-SYMBOLIQUE\SRC\CORE
│   contracts.py
│   orchestration_service.py
│   plugin_loader.py
│   __init__.py
│
├───plugins
│   │   interfaces.py
│   │   plugin_loader.py
│   │   __init__.py
│   │
│   ├───standard
│   │   │   __init__.py
│   │
│   └───workflows
│       │   __init__.py
│
└───services
    │   orchestration_service.py

D:\DEV\2025-EPITA-INTELLIGENCE-SYMBOLIQUE\SRC\AGENTS
│   agent_loader.py
│   interfaces.py
│   __init__.py
│
└───personalities
        __init__.py
```

## Justification de l'Architecture

Cette structure met en œuvre la **séparation des préoccupations**, un principe architectural clé :

-   **`src/core`**: Contient la logique métier fondamentale, agnostique de toute implémentation d'agent spécifique. C'est le cerveau non-incarné du système.
    -   **`src/core/plugins`**: Héberge l'écosystème de plugins, pierre angulaire de l'extensibilité.
        -   **`standard`**: Contient des plugins atomiques et réutilisables (par exemple, des analyseurs spécifiques).
        -   **`workflows`**: Contient des plugins plus complexes qui orchestrent plusieurs plugins standards pour réaliser des processus métier.

-   **`src/agents`**: Contient tout ce qui est spécifique aux agents, leur permettant d'avoir des "personnalités" distinctes.
    -   **`src/agents/personalities`**: Centralise les configurations, les prompts et les logiques spécifiques qui définissent le comportement unique de chaque agent, les découplant ainsi du `core`.

Cette organisation permet de faire évoluer le comportement des agents (`agents`) sans modifier la logique centrale (`core`), et inversement, garantissant une meilleure maintenabilité et une plus grande flexibilité.