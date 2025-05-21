# Matrice d'Interdépendances entre Projets

Ce document présente les relations et interdépendances entre les différents projets proposés, permettant aux étudiants de comprendre comment les projets s'articulent les uns avec les autres et d'identifier les synergies potentielles.

## Fondements théoriques et techniques

### Logiques formelles et raisonnement

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **1.1.1 Intégration des logiques propositionnelles avancées** | - | 1.1.5 (QBF), 1.2.8 (ADF), 1.4.1 (TMS), 1.4.4 (Mesures d'incohérence), 2.3.4 (Agent de formalisation logique) |
| **1.1.2 Logique du premier ordre (FOL)** | 1.1.1 (Logique propositionnelle) | 1.2.4 (ABA), 1.2.6 (ASPIC+) |
| **1.1.3 Logique modale** | 1.1.1 (Logique propositionnelle) | 1.4 (Maintenance de la vérité) |
| **1.1.4 Logique de description (DL)** | 1.1.1 (Logique propositionnelle) | 1.3.3 (Ontologie de l'argumentation) |
| **1.1.5 Formules booléennes quantifiées (QBF)** | 1.1.1 (Logique propositionnelle) | 1.5.2 (Vérification formelle) |
| **1.1.6 Logique conditionnelle (CL)** | 1.1.1 (Logique propositionnelle) | 1.2 (Frameworks d'argumentation), 1.4.3 (Raisonnement non-monotone) |

### Frameworks d'argumentation

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **1.2.1 Argumentation abstraite de Dung** | - | 1.2.2 (Argumentation bipolaire), 1.2.3 (Argumentation pondérée), 1.2.5 (VAF), 1.2.8 (ADF), 3.1.4 (Visualisation de graphes) |
| **1.2.2 Argumentation bipolaire** | 1.2.1 (Dung AF) | 3.1.4 (Visualisation de graphes) |
| **1.2.3 Argumentation pondérée** | 1.2.1 (Dung AF) | 1.2.9 (Analyse probabiliste), 3.2.3 (Aide à la décision) |
| **1.2.4 Argumentation basée sur les hypothèses (ABA)** | 1.1.2 (FOL), 1.2.1 (Dung AF) | 1.2.6 (ASPIC+) |
| **1.2.5 Argumentation basée sur les valeurs (VAF)** | 1.2.1 (Dung AF) | 3.2.3 (Aide à la décision) |
| **1.2.6 Argumentation structurée (ASPIC+)** | 1.1 (Logiques formelles), 1.2.1 (Dung AF) | 3.2.1 (Débat assisté) |
| **1.2.7 Argumentation dialogique** | 1.2.x (Frameworks d'argumentation) | 3.2.1 (Débat assisté), 3.2.7 (Délibération citoyenne) |
| **1.2.8 Abstract Dialectical Frameworks (ADF)** | 1.2.1 (Dung AF), 1.1.1 (Logique propositionnelle) | 3.1.4 (Visualisation de graphes) |
| **1.2.9 Analyse probabiliste d'arguments** | 1.2.1 (Dung AF), 1.2.3 (Argumentation pondérée) | 3.2.3 (Aide à la décision) |

### Taxonomies et classification

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **1.3.1 Taxonomie des schémas argumentatifs** | - | 2.3.1 (Extraction d'arguments), 1.3.3 (Ontologie de l'argumentation) |
| **1.3.2 Classification des sophismes** | - | 2.3.2 (Détection de sophismes), 1.3.3 (Ontologie de l'argumentation), 3.2.2 (Plateforme éducative) |
| **1.3.3 Ontologie de l'argumentation** | 1.1.4 (DL), 1.3.1 (Schémas), 1.3.2 (Sophismes) | 2.4.3 (Base de connaissances) |

### Maintenance de la vérité et révision de croyances

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **1.4.1 Systèmes de maintenance de la vérité (TMS)** | 1.1 (Logiques formelles) | 1.4.2 (Révision de croyances) |
| **1.4.2 Révision de croyances** | 1.4.1 (TMS) | 1.4.5 (Révision multi-agents), 2.1.6 (Gouvernance multi-agents) |
| **1.4.3 Raisonnement non-monotone** | 1.1 (Logiques formelles), 1.1.6 (Logique conditionnelle) | 1.4.2 (Révision de croyances) |
| **1.4.4 Mesures d'incohérence et résolution** | 1.1.1 (Logique propositionnelle) | 1.4.1 (Maintenance de la vérité) |
| **1.4.5 Révision de croyances multi-agents** | 1.4.2 (Révision de croyances) | 2.1.6 (Gouvernance multi-agents) |

### Planification et vérification formelle

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **1.5.1 Intégration d'un planificateur symbolique** | 1.1.5 (QBF) | 2.1.2 (Orchestration des agents) |
| **1.5.2 Vérification formelle d'arguments** | 1.1.1-1.1.5 (Logiques formelles) | 1.5.3 (Contrats argumentatifs) |
| **1.5.3 Formalisation de contrats argumentatifs** | 1.2 (Frameworks d'argumentation), 1.5.2 (Vérification formelle) | - |

## Développement système et infrastructure

### Architecture et orchestration

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **2.1.1 Architecture multi-agents** | - | 2.1.2 (Orchestration), 2.3.x (Agents spécialistes) |
| **2.1.2 Orchestration des agents** | 2.1.1 (Architecture multi-agents) | 2.1.6 (Gouvernance multi-agents), 2.5.2 (Pipeline de traitement) |
| **2.1.3 Monitoring et évaluation** | - | 3.1.2 (Dashboard de monitoring) |
| **2.1.4 Documentation et transfert de connaissances** | - | Tous les projets |
| **2.1.5 Intégration continue et déploiement** | - | 2.5 (Automatisation) |
| **2.1.6 Gouvernance multi-agents** | 1.4.5 (Révision multi-agents), 2.1.2 (Orchestration) | - |

### Gestion des sources et données

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **2.2.1 Amélioration du moteur d'extraction** | - | 2.2.2 (Formats étendus), 2.4 (Indexation sémantique) |
| **2.2.2 Support de formats étendus** | 2.2.1 (Moteur d'extraction) | 2.4 (Indexation sémantique) |
| **2.2.3 Sécurisation des données** | - | Tous les projets manipulant des données |
| **2.2.4 Gestion de corpus** | 2.2.1 (Moteur d'extraction) | 2.4 (Indexation sémantique) |

### Moteur agentique et agents spécialistes

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **2.3.1 Abstraction du moteur agentique** | - | 2.3.2-2.3.5 (Agents spécialistes), 2.3.6 (LLMs locaux) |
| **2.3.2 Agent de détection de sophismes et biais cognitifs** | 1.3.2 (Classification des sophismes) | 2.4.4 (Fact-checking), 3.2.2 (Plateforme éducative), 3.2.6 (Analyse de débats) |
| **2.3.3 Agent de génération de contre-arguments** | 1.2 (Frameworks d'argumentation) | 3.2.1 (Débat assisté), 3.2.5 (Assistant d'écriture) |
| **2.3.4 Agent de formalisation logique** | 1.1 (Logiques formelles) | 1.5.2 (Vérification formelle) |
| **2.3.5 Agent d'évaluation de qualité** | - | 3.2.5 (Assistant d'écriture), 3.2.6 (Analyse de débats) |
| **2.3.6 Intégration de LLMs locaux légers** | 2.3.1 (Abstraction du moteur agentique) | - |

### Indexation sémantique

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **2.4.1 Index sémantique d'arguments** | - | 2.4.2 (Vecteurs de types d'arguments) |
| **2.4.2 Vecteurs de types d'arguments** | 2.4.1 (Index sémantique) | 2.4.3 (Base de connaissances) |
| **2.4.3 Base de connaissances argumentatives** | 1.3 (Taxonomies), 2.4.2 (Indexation sémantique) | 3.2.x (Projets intégrateurs) |
| **2.4.4 Fact-checking automatisé et détection de désinformation** | 2.3.2 (Détection de sophismes) | 3.2.6 (Analyse de débats), 3.2.7 (Délibération citoyenne) |

### Automatisation et intégration MCP

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **2.5.1 Automatisation de l'analyse** | - | 2.5.2 (Pipeline de traitement) |
| **2.5.2 Pipeline de traitement** | 2.5.1 (Automatisation) | 3.1 (Interfaces utilisateurs) |
| **2.5.3 Développement d'un serveur MCP pour l'analyse argumentative** | - | 2.5.4 (Outils MCP), 2.5.5 (Serveur MCP Tweety) |
| **2.5.4 Outils et ressources MCP pour l'argumentation** | 2.5.3 (Serveur MCP) | - |
| **2.5.5 Serveur MCP pour les frameworks d'argumentation Tweety** | 2.5.3 (Serveur MCP), 1.2 (Frameworks d'argumentation) | - |
| **2.5.6 Protection des systèmes d'IA contre les attaques adversariales** | 2.3.1 (Abstraction du moteur agentique) | - |

## Expérience utilisateur et applications

### Interfaces utilisateurs

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **3.1.1 Interface web pour l'analyse argumentative** | - | 3.1.5 (Interface mobile), 3.2.x (Projets intégrateurs) |
| **3.1.2 Dashboard de monitoring** | 2.1.3 (Monitoring et évaluation) | - |
| **3.1.3 Éditeur visuel d'arguments** | 1.2 (Frameworks d'argumentation) | 3.1.7 (Collaboration en temps réel), 3.2.x (Projets intégrateurs) |
| **3.1.4 Visualisation avancée de graphes d'argumentation et de réseaux de désinformation** | 1.2 (Frameworks d'argumentation), 2.4.4 (Fact-checking) | 3.2.6 (Analyse de débats) |
| **3.1.5 Interface mobile** | 3.1.1 (Interface web) | - |
| **3.1.6 Accessibilité** | 3.1.x (Interfaces) | - |
| **3.1.7 Système de collaboration en temps réel** | 3.1.1 (Interface web), 3.1.3 (Éditeur) | 3.2.4 (Plateforme collaborative) |

### Projets intégrateurs

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **3.2.1 Système de débat assisté par IA** | 1.2 (Frameworks d'argumentation), 2.3 (Agents spécialistes), 3.1 (Interfaces) | - |
| **3.2.2 Plateforme éducative d'apprentissage de l'argumentation** | 1.3.2 (Classification des sophismes), 2.3.2 (Détection de sophismes), 3.1 (Interfaces) | - |
| **3.2.3 Système d'aide à la décision argumentative** | 1.2.8 (Frameworks avancés), 3.1.4 (Visualisation) | - |
| **3.2.4 Plateforme collaborative d'analyse de textes** | 3.1.7 (Collaboration en temps réel) | - |
| **3.2.5 Assistant d'écriture argumentative** | 2.3.2 (Détection de sophismes), 2.3.3 (Génération de contre-arguments) | - |
| **3.2.6 Système d'analyse de débats politiques et surveillance des médias** | 2.3.2 (Détection de sophismes), 2.4.4 (Fact-checking), 3.1.4 (Visualisation) | - |
| **3.2.7 Plateforme de délibération citoyenne** | 3.2.1 (Débat assisté), 3.2.3 (Aide à la décision) | - |

## Lutte contre la désinformation

| Projet | Dépend de | Est utilisé par |
|--------|-----------|-----------------|
| **Fact-checking automatisé et détection de désinformation** | - | Système d'analyse de débats, ArgumentuShield |
| **Agent de détection de sophismes et biais cognitifs** | Classification des sophismes | Fact-checking, Plateforme éducative |
| **Visualisation avancée de graphes d'argumentation et de réseaux de désinformation** | Frameworks d'argumentation, Fact-checking | Système d'analyse de débats |
| **Système d'analyse de débats politiques et surveillance des médias** | Détection de sophismes, Fact-checking, Visualisation | - |
| **Protection des systèmes d'IA contre les attaques adversariales** | Abstraction du moteur agentique | ArgumentuShield |
| **Plateforme éducative d'apprentissage de l'argumentation** | Détection de sophismes | - |
| **Applications commerciales de lutte contre la désinformation** | Fact-checking, Analyse de débats | - |
| **ArgumentuMind: Système cognitif de compréhension argumentative** | Détection de sophismes, Frameworks d'argumentation | ArgumentuShield |
| **ArgumentuShield: Système de protection cognitive contre la désinformation** | ArgumentuMind, Plateforme éducative | - |

## Visualisation des interdépendances

Pour une meilleure compréhension des interdépendances entre les projets, voici une représentation simplifiée des principales relations :

```
Fondements théoriques ──────┐
  │                         │
  ├─► Frameworks d'argumentation ──┐
  │                                │
  ├─► Taxonomies et classification ┤
  │                                │
  ├─► Maintenance de la vérité ────┤
  │                                │
  └─► Vérification formelle ───────┘
                                   │
                                   ▼
Architecture et orchestration ◄────┐
  │                                │
  ├─► Gestion des sources ◄────────┤
  │                                │
  ├─► Agents spécialistes ◄────────┤
  │                                │
  ├─► Indexation sémantique ◄──────┤
  │                                │
  └─► Automatisation et MCP ◄──────┘
                                   │
                                   ▼
Interfaces utilisateurs ◄──────────┐
  │                                │
  └─► Projets intégrateurs ◄───────┘
                                   │
                                   ▼
Lutte contre la désinformation ◄───┘
```

Cette visualisation montre comment les projets s'articulent en couches, des fondements théoriques aux applications concrètes, en passant par le développement système et les interfaces utilisateurs.

## Recommandations pour les équipes

### Projets complémentaires pour équipes de 2-3 personnes

Voici quelques combinaisons de projets qui fonctionnent bien ensemble pour des équipes de 2-3 personnes :

1. **Combinaison logique et argumentation** :
   - 1.1.1 Intégration des logiques propositionnelles avancées
   - 1.2.1 Argumentation abstraite de Dung

2. **Combinaison détection et visualisation** :
   - 2.3.2 Agent de détection de sophismes et biais cognitifs
   - 3.1.4 Visualisation avancée de graphes d'argumentation

3. **Combinaison indexation et recherche** :
   - 2.4.1 Index sémantique d'arguments
   - 2.4.3 Base de connaissances argumentatives

4. **Combinaison interface et collaboration** :
   - 3.1.1 Interface web pour l'analyse argumentative
   - 3.1.7 Système de collaboration en temps réel

5. **Combinaison lutte contre la désinformation** :
   - Fact-checking automatisé et détection de désinformation
   - Visualisation avancée de graphes d'argumentation et de réseaux de désinformation

### Projets complémentaires pour équipes de 4 personnes

Pour les équipes plus grandes, ces combinaisons permettent de travailler sur des projets plus ambitieux :

1. **Suite complète d'analyse argumentative** :
   - 1.2.1 Argumentation abstraite de Dung
   - 2.3.2 Agent de détection de sophismes
   - 2.4.4 Fact-checking automatisé
   - 3.1.4 Visualisation avancée de graphes

2. **Plateforme éducative complète** :
   - 1.3.2 Classification des sophismes
   - 2.3.2 Agent de détection de sophismes
   - 3.1.3 Éditeur visuel d'arguments
   - 3.2.2 Plateforme éducative d'apprentissage

3. **Système de débat assisté complet** :
   - 1.2.7 Argumentation dialogique
   - 2.3.3 Agent de génération de contre-arguments
   - 2.3.5 Agent d'évaluation de qualité
   - 3.2.1 Système de débat assisté par IA

4. **Système d'analyse de débats politiques** :
   - 2.3.2 Agent de détection de sophismes
   - 2.4.4 Fact-checking automatisé
   - 3.1.4 Visualisation avancée de graphes
   - 3.2.6 Système d'analyse de débats politiques