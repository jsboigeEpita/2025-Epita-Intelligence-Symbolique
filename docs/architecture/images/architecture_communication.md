graph TD
    subgraph "Niveau Stratégique"
        SS[État Stratégique]
        SM[Manager Stratégique]
        SP[Planificateur Stratégique]
        SA[Allocateur de Ressources]
    end

    subgraph "Niveau Tactique"
        TS[État Tactique]
        TC[Coordinateur Tactique]
        TM[Moniteur Tactique]
        TR[Résolveur de Conflits]
    end

    subgraph "Niveau Opérationnel"
        OS[État Opérationnel]
        OA1[Agent Opérationnel 1]
        OA2[Agent Opérationnel 2]
        OA3[Agent Opérationnel 3]
    end

    subgraph "Interfaces"
        STI[Interface Stratégique-Tactique]
        TOI[Interface Tactique-Opérationnelle]
    end

    %% Connexions entre composants stratégiques
    SS <--> SM
    SS <--> SP
    SS <--> SA
    SM <--> SP
    SM <--> SA
    SP <--> SA

    %% Connexions entre composants tactiques
    TS <--> TC
    TS <--> TM
    TS <--> TR
    TC <--> TM
    TC <--> TR
    TM <--> TR

    %% Connexions entre composants opérationnels
    OS <--> OA1
    OS <--> OA2
    OS <--> OA3

    %% Connexions entre niveaux via interfaces
    SS <--> STI
    STI <--> TS
    TS <--> TOI
    TOI <--> OS

    %% Styles
    classDef strategic fill:#f9d5e5,stroke:#333,stroke-width:1px;
    classDef tactical fill:#eeeeee,stroke:#333,stroke-width:1px;
    classDef operational fill:#d5f9e5,stroke:#333,stroke-width:1px;
    classDef interface fill:#e5d5f9,stroke:#333,stroke-width:1px;

    class SS,SM,SP,SA strategic;
    class TS,TC,TM,TR tactical;
    class OS,OA1,OA2,OA3 operational;
    class STI,TOI interface;