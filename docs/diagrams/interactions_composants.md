# Diagramme d'Interactions entre Composants du Système

Ce diagramme illustre les interactions entre les différents composants du système d'analyse argumentative, montrant comment ils communiquent et collaborent.

```mermaid
graph TD
    subgraph "Niveau Stratégique"
        A[Contrôleur Stratégique] --> B[Planificateur d'Analyse]
        B --> C[Gestionnaire de Ressources]
    end
    
    subgraph "Niveau Tactique"
        D[Orchestrateur Tactique] --> E[Coordinateur]
        E --> F[Moniteur Tactique]
        F --> G[Évaluateur de Qualité]
    end
    
    subgraph "Niveau Opérationnel"
        H[Agent Informel] --> I[Détecteur de Sophismes]
        J[Agent PL] --> K[Analyseur Logique]
        L[Agent PM] --> M[Analyseur de Structure]
        N[Agent Extract] --> O[Extracteur d'Arguments]
    end
    
    subgraph "Services Partagés"
        P[Service LLM]
        Q[Gestionnaire de Cache]
        R[Service de Journalisation]
        S[Visualiseur de Résultats]
    end
    
    A --> D
    D --> H
    D --> J
    D --> L
    D --> N
    
    H --> P
    J --> P
    L --> P
    N --> P
    
    H --> Q
    J --> Q
    L --> Q
    N --> Q
    
    D --> R
    H --> R
    J --> R
    L --> R
    N --> R
    
    G --> S
    
    classDef strategic fill:#f9d5e5,stroke:#333,stroke-width:2px
    classDef tactical fill:#eeeeee,stroke:#333,stroke-width:2px
    classDef operational fill:#d5e8d4,stroke:#333,stroke-width:2px
    classDef services fill:#dae8fc,stroke:#333,stroke-width:2px
    
    class A,B,C strategic
    class D,E,F,G tactical
    class H,I,J,K,L,M,N,O operational
    class P,Q,R,S services
```

## Description des Interactions

### Architecture Hiérarchique à Trois Niveaux

Le système est organisé selon une architecture hiérarchique à trois niveaux :

1. **Niveau Stratégique** : Responsable de la planification globale et de l'allocation des ressources
   - Le Contrôleur Stratégique supervise l'ensemble du processus d'analyse
   - Le Planificateur d'Analyse détermine la stratégie d'analyse optimale
   - Le Gestionnaire de Ressources alloue les ressources computationnelles

2. **Niveau Tactique** : Coordonne l'exécution des analyses et surveille la qualité
   - L'Orchestrateur Tactique dirige les agents opérationnels
   - Le Coordinateur synchronise les activités des agents
   - Le Moniteur Tactique surveille les performances
   - L'Évaluateur de Qualité vérifie la cohérence des résultats

3. **Niveau Opérationnel** : Exécute les analyses spécifiques
   - L'Agent Informel détecte les sophismes via son Détecteur de Sophismes
   - L'Agent PL effectue l'analyse logique propositionnelle
   - L'Agent PM analyse la structure argumentative
   - L'Agent Extract extrait les arguments du texte

### Services Partagés

Les composants partagent plusieurs services communs :

- **Service LLM** : Fournit l'accès aux modèles de langage
- **Gestionnaire de Cache** : Optimise les performances en mettant en cache les résultats
- **Service de Journalisation** : Enregistre les activités et les erreurs
- **Visualiseur de Résultats** : Présente les résultats de manière visuelle

## Flux de Communication

1. Le Contrôleur Stratégique initie le processus et communique avec l'Orchestrateur Tactique
2. L'Orchestrateur Tactique dirige les agents opérationnels
3. Les agents opérationnels utilisent les services partagés pour effectuer leurs analyses
4. Les résultats remontent la hiérarchie pour consolidation et évaluation
5. L'Évaluateur de Qualité transmet les résultats finaux au Visualiseur

## Cas d'Utilisation de ce Diagramme

Ce diagramme est utile pour :
- Comprendre l'architecture globale du système
- Identifier les dépendances entre composants
- Planifier des modifications ou extensions du système
- Former de nouveaux développeurs à l'architecture du projet