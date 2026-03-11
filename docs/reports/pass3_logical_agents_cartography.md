# Cartographie des Agents Logiques

Ce document détaille l'architecture, le rôle, la configuration et les dépendances des agents logiques du système.

---

## 1. Famille d'Agents JTMS

Ces agents sont basés sur un Justification-Truth Maintenance System (JTMS) pour une gestion rigoureuse des croyances et des justifications.

### 1.1. `JTMSAgentBase`

*   **Rôle principal :** Classe de base **abstraite** qui fournit l'infrastructure commune pour tous les agents basés sur JTMS. Elle n'est pas instanciée directement.
*   **Configuration :**
    *   Initialise une `JTMSSession` qui encapsule une instance de la librairie `jtms`.
    *   Gère les `ExtendedBelief` (croyances avec métadonnées : source, confiance, etc.).
    *   Prend un `Kernel` semantic-kernel, un nom d'agent et un ID de session en paramètres.
*   **Dépendances :**
    *   `semantic_kernel.Kernel`
    *   Librairie `jtms` (importée depuis `1.4.1-JTMS`)
*   **Instanciation :** N/A (classe abstraite).

### 1.2. `SherlockJTMSAgent`

*   **Rôle principal :** Agent d'investigation principal qui formule des hypothèses et gère les évidences de manière structurée via le JTMS.
*   **Configuration :**
    *   Hérite de `JTMSAgentBase`.
    *   Utilise deux gestionnaires internes : `HypothesisTracker` et `EvidenceManager` pour organiser la connaissance.
    *   Intègre une instance de `SherlockEnqueteAgent` pour la génération de contenu (hypothèses, descriptions).
*   **Dépendances :**
    *   `JTMSAgentBase`
    *   `SherlockEnqueteAgent`
*   **Instanciation :** Instancié avec un `Kernel` et un nom d'agent.

### 1.3. `WatsonJTMSAgent`

*   **Rôle principal :** Agent d'analyse, de critique et de validation. Il évalue la cohérence et la validité du raisonnement des autres agents.
*   **Configuration :**
    *   Hérite de `JTMSAgentBase`.
    *   Agent composite qui délègue ses tâches à des moteurs spécialisés :
        *   `ConsistencyChecker` : Vérifie la cohérence du JTMS.
        *   `FormalValidator` : Valide la logique formelle.
        *   `CritiqueEngine` : Critique les raisonnements et suggère des alternatives.
        *   `SynthesisEngine` : Synthétise les informations et propose des théories alternatives.
*   **Dépendances :**
    *   `JTMSAgentBase`
    *   Moteurs internes (`ConsistencyChecker`, `FormalValidator`, `CritiqueEngine`, `SynthesisEngine`).
*   **Instanciation :** Instancié avec un `Kernel` et un nom d'agent.

---

## 2. Agents Standards (basés sur `BaseAgent`)

Ces agents sont des implémentations plus directes qui héritent d'une classe de base commune (`BaseAgent` ou similaire).

### 2.1. `SherlockEnqueteAgent`

*   **Rôle principal :** Agent d'enquête non-JTMS. Semble être une version plus ancienne ou une composante du `SherlockJTMSAgent`. Il interagit directement avec l'état de l'enquête.
*   **Configuration :**
    *   Hérite de `BaseAgent`.
    *   Utilise un plugin `SherlockTools` qui contient des fonctions pour interagir avec un `EnqueteStatePlugin` (non visible dans les fichiers analysés, mais inféré des appels).
    *   Son comportement est défini par un long `system_prompt` axé sur la résolution rapide de Cluedo.
*   **Dépendances :**
    *   `BaseAgent`
    *   Plugin `EnqueteStatePlugin` (implicite).
*   **Instanciation :** Instancié avec un `Kernel`, un nom d'agent et un `service_id` pour le LLM.

### 2.2. `WatsonLogicAssistant`

*   **Rôle principal :** Agent d'assistance logique spécialisé dans la logique propositionnelle.
*   **Configuration :**
    *   Hérite de `PropositionalLogicAgent`.
    *   Utilise des `WatsonTools` qui s'interfacent avec `TweetyBridge` pour la validation de formules logiques et l'exécution de requêtes.
    *   Son `system_prompt` le guide pour effectuer des analyses formelles pas-à-pas, en particulier pour des puzzles logiques.
*   **Dépendances :**
    *   `PropositionalLogicAgent`
    *   `TweetyBridge` (pour l'interaction avec la librairie de logique Tweety).
*   **Instanciation :** Instancié avec un `Kernel`, un nom d'agent, et optionnellement un `TweetyBridge`.

### 2.3. `InformalFallacyAgent`

*   **Rôle principal :** Détecter et analyser les sophismes informels (erreurs de raisonnement non-formelles) dans un texte.
*   **Configuration :**
    *   Hérite de `BaseAgent`.
    *   Charge son `system_prompt` depuis un fichier externe.
    *   Utilise le `FallacyIdentificationPlugin` pour accomplir sa tâche.
*   **Dépendances :**
    *   `BaseAgent`
    *   `FallacyIdentificationPlugin`
*   **Instanciation :** Instancié avec un `Kernel` et un nom d'agent.