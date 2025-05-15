graph TD
    subgraph "Middleware de Messagerie"
        MM[Middleware de Messagerie]
        GC[Gestionnaire de Canaux]
        MC[Moniteur de Communication]
    end

    subgraph "Canaux de Communication"
        CH[Canal Hiérarchique]
        CC[Canal de Collaboration]
        CD[Canal de Données]
        CN[Canal de Négociation]
        CF[Canal de Feedback]
    end

    subgraph "Niveau Stratégique"
        SS[État Stratégique]
        SM[Manager Stratégique]
        SP[Planificateur Stratégique]
        SA[Allocateur de Ressources]
        SAdapter[Adaptateur Stratégique]
    end

    subgraph "Niveau Tactique"
        TS[État Tactique]
        TC[Coordinateur Tactique]
        TM[Moniteur Tactique]
        TR[Résolveur de Conflits]
        TAdapter[Adaptateur Tactique]
    end

    subgraph "Niveau Opérationnel"
        OS[État Opérationnel]
        OA1[Agent Opérationnel 1]
        OA2[Agent Opérationnel 2]
        OA3[Agent Opérationnel 3]
        OAdapter[Adaptateur Opérationnel]
    end

    %% Connexions entre composants du middleware
    MM <--> GC
    MM <--> MC
    GC <--> MC

    %% Connexions entre middleware et canaux
    GC <--> CH
    GC <--> CC
    GC <--> CD
    GC <--> CN
    GC <--> CF

    %% Connexions entre composants stratégiques
    SS <--> SM
    SS <--> SP
    SS <--> SA
    SM <--> SP
    SM <--> SA
    SP <--> SA
    SS <--> SAdapter
    SM <--> SAdapter
    SP <--> SAdapter
    SA <--> SAdapter

    %% Connexions entre composants tactiques
    TS <--> TC
    TS <--> TM
    TS <--> TR
    TC <--> TM
    TC <--> TR
    TM <--> TR
    TS <--> TAdapter
    TC <--> TAdapter
    TM <--> TAdapter
    TR <--> TAdapter

    %% Connexions entre composants opérationnels
    OS <--> OA1
    OS <--> OA2
    OS <--> OA3
    OS <--> OAdapter
    OA1 <--> OAdapter
    OA2 <--> OAdapter
    OA3 <--> OAdapter

    %% Connexions entre adaptateurs et canaux
    SAdapter <--> CH
    SAdapter <--> CC
    SAdapter <--> CD
    SAdapter <--> CN
    SAdapter <--> CF

    TAdapter <--> CH
    TAdapter <--> CC
    TAdapter <--> CD
    TAdapter <--> CN
    TAdapter <--> CF

    OAdapter <--> CH
    OAdapter <--> CC
    OAdapter <--> CD
    OAdapter <--> CN
    OAdapter <--> CF

    %% Styles
    classDef middleware fill:#f9e5d5,stroke:#333,stroke-width:1px;
    classDef channel fill:#d5e5f9,stroke:#333,stroke-width:1px;
    classDef strategic fill:#f9d5e5,stroke:#333,stroke-width:1px;
    classDef tactical fill:#eeeeee,stroke:#333,stroke-width:1px;
    classDef operational fill:#d5f9e5,stroke:#333,stroke-width:1px;
    classDef adapter fill:#e5f9d5,stroke:#333,stroke-width:1px;

    class MM,GC,MC middleware;
    class CH,CC,CD,CN,CF channel;
    class SS,SM,SP,SA strategic;
    class TS,TC,TM,TR tactical;
    class OS,OA1,OA2,OA3 operational;
    class SAdapter,TAdapter,OAdapter adapter;