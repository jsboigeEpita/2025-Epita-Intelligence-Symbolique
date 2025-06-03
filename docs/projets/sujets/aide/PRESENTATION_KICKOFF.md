# Présentation Kickoff - Projets Epita 2025 Intelligence Symbolique

## Bienvenue !

Bienvenue dans le projet Epita 2025 Intelligence Symbolique ! Cette présentation a pour objectif de vous introduire au projet, de vous présenter l'architecture globale du système et de vous expliquer les objectifs spécifiques de vos projets.

## Agenda

1. Présentation du projet global
2. Architecture du système
3. Présentation des projets spécifiques
4. Ressources disponibles
5. Planning et jalons
6. Questions et discussions

## 1. Présentation du projet global

### Qu'est-ce que l'Intelligence Symbolique ?

L'Intelligence Symbolique combine les approches symboliques traditionnelles de l'IA (logique, représentation des connaissances) avec des techniques modernes pour créer des systèmes intelligents explicables et robustes.

### Objectifs du projet Epita 2025

- Développer un système d'analyse argumentative complet
- Permettre la détection automatique de sophismes
- Faciliter la validation logique d'arguments
- Construire et analyser des frameworks d'argumentation de Dung
- Rendre ces outils accessibles via des interfaces modernes et des protocoles standardisés

### Applications concrètes

- Analyse critique de textes argumentatifs
- Détection de fausses informations et de raisonnements fallacieux
- Aide à la décision basée sur l'argumentation
- Intégration avec des assistants IA pour améliorer leur raisonnement

## 2. Architecture du système

### Vue d'ensemble

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│                     │     │                     │     │                     │
│  Interface Web      │     │  API Web            │     │  Moteur d'analyse   │
│  (React/Vue)        │◄───►│  (Flask)            │◄───►│  argumentative      │
│                     │     │                     │     │                     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                               ▲
                                                               │
                                                               ▼
┌─────────────────────┐                               ┌─────────────────────┐
│                     │                               │                     │
│  Assistants IA      │                               │  TweetyProject      │
│  (Claude, GPT)      │◄─────────────────────────────►│  (Java)             │
│                     │                               │                     │
└─────────────────────┘                               └─────────────────────┘
        ▲
        │
        ▼
┌─────────────────────┐
│                     │
│  Serveur MCP        │
│                     │
└─────────────────────┘
```

### Composants principaux

1. **Moteur d'analyse argumentative**
   - Cœur du système
   - Agents spécialisés pour différentes tâches
   - Intégration avec TweetyProject pour l'analyse formelle

2. **API Web**
   - Interface REST pour accéder aux fonctionnalités
   - Modèles de données standardisés
   - Services métier pour chaque type d'analyse

3. **Interface Web** (à développer)
   - Application web moderne
   - Visualisations interactives
   - Expérience utilisateur intuitive

4. **Serveur MCP** (à développer)
   - Exposition des fonctionnalités via le protocole MCP
   - Intégration avec des LLMs comme Claude et GPT
   - Gestion des sessions et du contexte

## 3. Présentation des projets spécifiques

### Projet Interface Web

**Étudiants :** erwin.rodrigues, robin.de-bastos

**Objectif :** Développer une interface web moderne et intuitive qui permet aux utilisateurs d'interagir avec le moteur d'analyse argumentative via l'API existante.

**Fonctionnalités clés :**
- Éditeur d'arguments avec analyse en temps réel
- Visualisation des sophismes détectés
- Constructeur et visualisateur de frameworks de Dung
- Interface responsive et accessible

**Technologies :**
- React/Vue/Angular (au choix)
- D3.js/Cytoscape.js pour les visualisations
- Axios pour les appels API
- Bootstrap/Material UI pour l'interface

### Projet Serveur MCP

**Étudiants :** enguerrand.turcat, titouan.verhille

**Objectif :** Développer un serveur MCP qui expose les fonctionnalités d'analyse argumentative aux LLMs comme Claude et GPT via le protocole Model Context Protocol.

**Fonctionnalités clés :**
- Outils MCP pour l'analyse de sophismes
- Outils MCP pour la validation d'arguments
- Outils MCP pour la construction de frameworks
- Gestion des sessions et du contexte

**Technologies :**
- Python/TypeScript
- JPype pour l'intégration avec TweetyProject
- JSON-RPC 2.0 pour le protocole MCP
- WebSockets/HTTP pour la communication

## 4. Ressources disponibles

### Documentation

- Guide d'intégration des projets
- Documentation de l'API web
- Documentation du moteur d'analyse
- Spécifications du protocole MCP

### Code existant

- API web complète et fonctionnelle
- Moteur d'analyse argumentative
- Exemples de code pour l'interface web
- Templates pour le serveur MCP

### Outils et bibliothèques

- TweetyProject pour l'analyse formelle
- Bibliothèques de visualisation
- Outils de test et de débogage

### Exemples Concrets et Guides Pratiques

Pour vous aider à démarrer et à comprendre comment interagir avec les différents composants du projet, voici quelques ressources clés :

*   **Scripts de démonstration :**
    *   Pour une illustration simple des interactions de base avec le système, consultez le script [`demo_tweety_interaction_simple.py`](../../../../examples/scripts_demonstration/demo_tweety_interaction_simple.py) dans le dossier [`examples/scripts_demonstration/`](../../../../examples/scripts_demonstration/).
*   **Notebooks Jupyter :**
    *   Un tutoriel interactif sur l'utilisation de l'API logique est disponible sous forme de notebook Jupyter : [`api_logic_tutorial.ipynb`](../../../../examples/notebooks/api_logic_tutorial.ipynb).
*   **Exemples d'intégration API :**
    *   Un exemple concret d'intégration avec l'API pour les agents logiques se trouve ici : [`api_integration_example.py`](../../../../examples/logic_agents/api_integration_example.py).
*   **Script de test de l'API :**
    *   Pour voir comment l'API peut être testée et utilisée, référez-vous au script [`test_api.py`](../../../../libs/web_api/test_api.py). Cela peut vous donner des idées pour vos propres tests et interactions.
*   **Guides Généraux Importants :**
    *   Le document principal pour démarrer avec les projets étudiants : [`README_PROJETS_ETUDIANTS.md`](../../../README_PROJETS_ETUDIANTS.md).
    *   Un guide d'utilisation général du système : [`guide_utilisation.md`](../../../guides/guide_utilisation.md).
    *   Pour ceux qui travaillent sur l'interface web, le guide de démarrage rapide est essentiel : [`DEMARRAGE_RAPIDE.md`](./interface-web/DEMARRAGE_RAPIDE.md).

N'hésitez pas à explorer ces ressources pour accélérer votre compréhension et votre développement.

## 5. Planning et jalons

### Semaine 1 : Mise en place et familiarisation
- Introduction au projet et à l'architecture
- Configuration des environnements de développement
- Premiers tests avec l'API et le moteur d'analyse

### Semaine 2-3 : Développement des fonctionnalités de base
- Implémentation des composants principaux
- Intégration avec l'API/moteur d'analyse
- Tests unitaires

### Semaine 4 : Finalisation et intégration
- Tests d'intégration
- Optimisation des performances
- Documentation

### Semaine 5 : Présentation et déploiement
- Démonstration des projets
- Déploiement en production
- Retours et améliorations

## 6. Attentes et livrables

### Pour l'Interface Web

- Code source complet et documenté
- Interface utilisateur fonctionnelle et intuitive
- Documentation utilisateur
- Tests unitaires et d'intégration
- Démonstration des fonctionnalités

### Pour le Serveur MCP

- Code source complet et documenté
- Serveur MCP fonctionnel avec tous les outils requis
- Documentation d'intégration
- Tests unitaires et d'intégration
- Démonstration avec Claude Desktop ou Roo

## 7. Conseils pour la réussite

1. **Commencez petit, itérez souvent**
   - Développez d'abord les fonctionnalités de base
   - Testez régulièrement
   - Ajoutez progressivement des fonctionnalités avancées

2. **Communiquez efficacement**
   - Posez des questions si vous êtes bloqués
   - Partagez vos progrès lors des réunions hebdomadaires
   - Documentez vos décisions de conception

3. **Utilisez les ressources disponibles**
   - Consultez la documentation existante
   - Réutilisez le code et les exemples fournis
   - Profitez des réunions de suivi pour obtenir de l'aide

## 8. Questions et discussions

N'hésitez pas à poser des questions sur :
- L'architecture du système
- Les fonctionnalités attendues
- Les technologies recommandées
- Le planning et les livrables

## Merci !

Nous sommes impatients de voir vos contributions à ce projet passionnant !

Pour toute question après cette réunion, n'hésitez pas à nous contacter.