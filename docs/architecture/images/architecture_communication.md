Ce document illustre l'architecture de communication hiérarchique du système.
Les messages entre les différents niveaux (Stratégique, Tactique, Opérationnel)
sont gérés et routés par un composant central : le `MessageMiddleware`.

```mermaid
graph TD
    subgraph "Niveau Stratégique"
        direction LR
        SS[État Stratégique]
        SM[Manager Stratégique]
        SP[Planificateur Stratégique]
        SA[Allocateur de Ressources]
    end

    subgraph "Niveau Tactique"
        direction LR
        TS[État Tactique]
        TC[Coordinateur Tactique]
        TM[Moniteur Tactique]
        TR[Résolveur de Conflits]
    end

    subgraph "Niveau Opérationnel"
        direction LR
        OS[État Opérationnel]
        OA1[Agent Opérationnel 1]
        OA2[Agent Opérationnel 2]
        OA3[Agent Opérationnel 3]
    end

    MMW[MessageMiddleware]

    %% Connexions internes (simplifiées pour la clarté de la communication inter-niveaux)
    SM --- SS
    SP --- SS
    SA --- SS

    TC --- TS
    TM --- TS
    TR --- TS

    OA1 --- OS
    OA2 --- OS
    OA3 --- OS

    %% Connexions des Niveaux au MessageMiddleware
    SM <-->|Commandes, Infos| MMW
    SP <-->|Requêtes, Réponses| MMW
    SA <-->|Événements| MMW

    TC <-->|Commandes, Infos| MMW
    TM <-->|Requêtes, Réponses| MMW
    TR <-->|Événements| MMW

    OA1 <-->|Infos, Requêtes| MMW
    OA2 <-->|Réponses, Événements| MMW
    OA3 <-->|Commandes| MMW
    OS <-->|État| MMW


    %% Styles
    classDef strategic fill:#f9d5e5,stroke:#333,stroke-width:1px;
    classDef tactical fill:#eeeeee,stroke:#333,stroke-width:1px;
    classDef operational fill:#d5f9e5,stroke:#333,stroke-width:1px;
    classDef middleware fill:#e5d5f9,stroke:#333,stroke-width:2px,font-weight:bold;

    class SS,SM,SP,SA strategic;
    class TS,TC,TM,TR tactical;
    class OS,OA1,OA2,OA3 operational;
    class MMW middleware;