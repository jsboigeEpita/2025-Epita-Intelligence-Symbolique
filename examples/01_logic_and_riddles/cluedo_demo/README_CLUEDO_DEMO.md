# README: Démonstration du Workflow Cluedo

## 1. Introduction

*   **Objectif de la Démonstration :**
    *   Expliquer que ce document et le script associé (`demo_cluedo_workflow.py`) visent à illustrer de manière pédagogique les principaux composants et le flux de travail du système d'enquête Cluedo basé sur `semantic-kernel`.
    *   Destiné aux étudiants pour comprendre l'architecture de base : état de l'enquête, agents (Sherlock, Watson), plugins de gestion d'état, et orchestration.
*   **Présentation Générale du Système Cluedo (simplifiée) :**
    *   Rappel du but du jeu Cluedo (trouver le coupable, l'arme, le lieu).
    *   Comment les agents IA (Sherlock, Watson) collaborent pour résoudre l'enquête, chacun avec son rôle.
    *   Importance de la gestion de l'état (`EnqueteCluedoState`) et de la communication.

## 2. Description des Composants Clés

*   Pour chaque composant, fournir une brève description de son rôle et de son importance dans le système. Faire le lien avec les classes correspondantes dans le code du projet.

    *   **`EnqueteCluedoState` : Le Cœur de l'Enquête**
        *   Rôle : Stocker toutes les informations relatives à l'enquête en cours (solution, hypothèses émises, cartes connues des joueurs, déductions, etc.).
        *   Importance : Fournit une source de vérité unique et partagée pour tous les agents.
        *   Illustré dans le script : Section `1.1 EnqueteCluedoState`.

    *   **Agents IA : `SherlockEnqueteAgent` et `WatsonLogicAssistant`**
        *   `SherlockEnqueteAgent` :
            *   Rôle : L'agent principal de déduction, formule des hypothèses, cherche à résoudre l'enquête. Utilise (potentiellement) des capacités LLM pour le raisonnement.
            *   Illustré dans le script : Section `1.2 Agents (Sherlock & Watson)`.
        *   `WatsonLogicAssistant` :
            *   Rôle : L'assistant logique, peut vérifier des faits, analyser des informations par rapport à ses connaissances (cartes), aider Sherlock.
            *   Illustré dans le script : Section `1.2 Agents (Sherlock & Watson)`.
        *   Interaction avec le `Kernel` : Expliquer brièvement que les agents utilisent un `Kernel` (ici mocké) pour accéder à des services (comme les LLM) et des plugins.

    *   **`EnqueteStateManagerPlugin` : Le Gestionnaire d'État**
        *   Rôle : Fournit des fonctions structurées (`KernelFunction`) pour que les agents puissent lire et modifier l'état de l'enquête (`EnqueteCluedoState`) de manière contrôlée.
        *   Importance : Abstrait la manipulation directe de l'état, permet une interaction standardisée.
        *   Illustré dans le script : Section `1.3 EnqueteStateManagerPlugin`.

    *   **Orchestration : `CluedoGroupChatManager` et `GroupChat`**
        *   `CluedoGroupChatManager` :
            *   Rôle : Un type de `AgentChatManager` spécialisé qui dirige la conversation entre les agents dans le cadre de l'enquête Cluedo. Décide quel agent parle ensuite, quand l'enquête est terminée, etc.
        *   `GroupChat` (de `semantic-kernel`) :
            *   Rôle : L'environnement où les agents (membres) interagissent sous la direction du manager.
        *   Importance : Permet une collaboration structurée entre plusieurs agents.
        *   Illustré dans le script : Section `2.2 Orchestration de base avec GroupChat`.

## 3. Instructions d'Exécution du Script de Démonstration

*   **Prérequis :**
    *   Avoir l'environnement Python du projet configuré avec toutes les dépendances (`semantic-kernel`, etc.).
    *   Aucune clé API ou configuration LLM n'est nécessaire car le script utilise des mocks.
*   **Commande pour lancer le script :**
    *   Se placer à la racine du projet (`d:/2025-Epita-Intelligence-Symbolique`).
    *   Exécuter : `python examples/cluedo_demo/demo_cluedo_workflow.py`
*   **Sortie Attendue :**
    *   Le script affichera une série de traces dans la console, montrant l'initialisation des composants, les interactions simulées, et l'état des objets à différentes étapes.

## 4. Analyse des Traces du Script

*   Expliquer comment lire et comprendre les sorties du script, section par section. Mettre en évidence ce que chaque partie de la sortie démontre.

    *   **Niveau 1 : Illustrations Unitaires**
        *   `1.1 EnqueteCluedoState` :
            *   Observer la création de l'état avec solution auto-générée et solution définie.
            *   Comprendre comment les hypothèses et les cartes des joueurs sont stockées.
        *   `1.2 Agents (Sherlock & Watson)` :
            *   Voir comment les agents sont instanciés avec un `Kernel` mocké.
            *   Noter que leurs capacités de raisonnement sont simulées (pas d'appels LLM réels).
        *   `1.3 EnqueteStateManagerPlugin` :
            *   Comprendre comment le plugin est lié à un état et ajouté à un `Kernel`.
            *   Voir un exemple d'appel direct à une méthode du plugin pour obtenir des informations sur l'état.

    *   **Niveau 2 : Illustrations d'Intégration**
        *   `2.1 Interaction Sherlock -> Plugin Etat -> Watson` :
            *   Suivre le flux : Sherlock (simulé) fait une hypothèse, celle-ci est enregistrée via le plugin (simulant un appel `kernel.invoke`), puis Watson (simulé) accède à l'état mis à jour pour son analyse.
            *   Comprendre le rôle central du plugin et du `Kernel` (même mocké) dans la médiation des interactions.
        *   `2.2 Orchestration de base avec GroupChat` :
            *   Observer l'instanciation du `CluedoGroupChatManager` et du `GroupChat`.
            *   Comprendre le principe de l'orchestration (même si le dialogue complet est simplifié/mocké dans la démo) : le manager sélectionne les agents, les agents "parlent" (leurs `invoke` sont appelés).

    *   **Niveau 3 : Illustration Fonctionnelle (Très Simplifié)**
        *   Suivre le mini-scénario : une hypothèse, une infirmation basée sur une carte, et la communication de cette déduction.
        *   Voir comment les différents composants peuvent s'articuler pour simuler un petit pas dans la résolution de l'enquête.

## 5. Conclusion

*   Récapituler les principaux apprentissages de la démonstration.
*   Encourager les étudiants à explorer le code source des composants réels du projet pour approfondir leur compréhension.
*   Mentionner que cette démo est une simplification et que le système complet peut inclure des logiques plus complexes, une gestion d'erreur plus poussée, et de vrais appels LLM.