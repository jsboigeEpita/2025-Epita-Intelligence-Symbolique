# Projets d'Intelligence Symbolique

Ce dossier contient l'ensemble des sujets de projets proposés aux étudiants dans le cadre du cours d'intelligence symbolique, ainsi que les ressources associées pour leur réalisation. Ces projets permettent d'appliquer concrètement les méthodes et outils d'intelligence symbolique, avec un focus particulier sur l'argumentation et son intégration par l'IA générative agentique orchestrée.

## Table des Matières

- [Vue d'ensemble](#vue-densemble)
- [Structure](#structure)
- [Catégories de Projets](#catégories-de-projets)
- [Organisation des Fichiers](#organisation-des-fichiers)
- [Filtrage des Projets](#filtrage-des-projets)
  - [Par Niveau de Difficulté](#par-niveau-de-difficulté)
  - [Par Durée Estimée](#par-durée-estimée)
  - [Par Technologie](#par-technologie)
- [Ressources Disponibles](#ressources-disponibles)
- [Modalités de Réalisation](#modalités-de-réalisation)
- [Évaluation](#évaluation)
- [Choix d'un Sujet](#choix-dun-sujet)
- [Ressources associées](#ressources-associées)

## Vue d'ensemble

Le dossier "projets" est le point central pour les étudiants souhaitant s'engager dans la réalisation d'un projet d'intelligence symbolique. Il offre une variété de sujets couvrant différents aspects de l'IA symbolique, de l'argumentation computationnelle et de l'intégration avec l'IA générative.

Ces projets sont conçus pour permettre aux étudiants de contribuer à l'amélioration d'un système d'orchestration agentique d'analyse rhétorique, une plateforme avancée qui utilise plusieurs agents IA spécialisés collaborant pour analyser des textes argumentatifs sous différents angles. Pour bien appréhender l'écosystème dans lequel ces projets s'inscrivent, il est fortement recommandé de consulter les documentations de référence du système :
- La **[Documentation d'Architecture](../architecture/README.md)** : pour comprendre la conception globale, les flux de communication (notamment via le `MessageMiddleware`) et l'architecture hiérarchique des agents.
- La **[Documentation des Composants](../composants/README.md)** : pour découvrir les modules réutilisables existants (comme le `Moteur de Raisonnement`, le `Pont Tweety` ou l'`API Web`) et comment ils interagissent.
- Le **[Portail des Guides](../guides/README.md)** : qui centralise les guides pratiques pour les développeurs, les utilisateurs, et des exemples d'utilisation des différentes logiques.

Chaque projet est présenté avec une structure standardisée incluant le contexte, les objectifs, les technologies clés, le niveau de difficulté, l'estimation d'effort, les interdépendances avec d'autres projets, les références et les livrables attendus.

## Structure

Organisation des fichiers et sous-dossiers du dossier projets :

- **`README.md`** : Ce fichier, présentant l'ensemble du dossier projets et son organisation.
- **`fondements_theoriques.md`** : Projets centrés sur les aspects formels, logiques et théoriques de l'argumentation.
- **`developpement_systeme.md`** : Projets axés sur l'architecture, l'orchestration et les composants techniques.
- **`experience_utilisateur.md`** : Projets orientés vers les interfaces, visualisations et cas d'usage concrets.
- **`exemples_tweety.md`** : Guide pour connecter les concepts théoriques aux exemples pratiques de TweetyProject.
- **`exemples_tweety_par_projet.md`** : Exemples spécifiques de TweetyProject organisés par projet.
- **`matrice_interdependances.md`** : Présentation des relations et dépendances entre les différents projets.
- **`modeles_affaires_ia.md`** : Présentation des modèles d'affaires et cas d'usage commerciaux pour les systèmes d'analyse argumentative.
- **`message_annonce_etudiants.md`** : Message d'annonce des projets aux étudiants.
- **`sujets_projets_detailles.md`** : Présentation détaillée des sujets de projets.
- **`sujets/`** : Dossier contenant les descriptions détaillées de chaque sujet de projet.
  - **`aide/`** : Ressources pratiques spécialisées pour faciliter la réalisation des projets.
    - **`interface-web/`** : Exemples et guides pour le développement d'interfaces web.
    - **`DEMARRAGE_RAPIDE.md`** : Guide de démarrage rapide pour les projets.
    - **`FAQ_DEVELOPPEMENT.md`** : Réponses aux questions fréquentes sur le développement.
    - **`GUIDE_INTEGRATION_PROJETS.md`** : Guide pour l'intégration des projets.
    - **`PRESENTATION_KICKOFF.md`** : Présentation initiale des projets.

## Catégories de Projets

Les projets sont organisés en trois catégories thématiques principales :

1. **[Fondements théoriques et techniques](./fondements_theoriques.md)** - Projets centrés sur les aspects formels, logiques et théoriques de l'argumentation, incluant :
   - Logiques formelles et raisonnement
   - Frameworks d'argumentation
   - Taxonomies et classification
   - Maintenance de la vérité et révision de croyances

2. **[Développement système et infrastructure](./developpement_systeme.md)** - Projets axés sur l'architecture, l'orchestration et les composants techniques, incluant :
   - Architecture et orchestration (voir [Documentation d'Architecture](../architecture/README.md))
   - Gestion des sources et données
   - Moteur agentique et agents spécialistes (voir [Documentation des Composants](../composants/README.md))
   - Indexation sémantique
   - Automatisation et intégration MCP

3. **[Expérience utilisateur et applications](./experience_utilisateur.md)** - Projets orientés vers les interfaces, visualisations et cas d'usage concrets, incluant :
   - Interfaces utilisateurs (s'appuyant souvent sur l'[API Web](../composants/api_web.md))
   - Visualisations
   - Applications spécifiques
   - Lutte contre la désinformation

Chaque catégorie regroupe des projets partageant des objectifs et des approches similaires, permettant aux étudiants de se concentrer sur un domaine spécifique de l'intelligence symbolique et de l'argumentation.

## Organisation des Fichiers

Les projets sont documentés à travers plusieurs fichiers complémentaires :

1. **Fichiers par catégorie** :
   - [fondements_theoriques.md](./fondements_theoriques.md) - Projets centrés sur les aspects formels, logiques et théoriques
   - [developpement_systeme.md](./developpement_systeme.md) - Projets axés sur l'architecture et les composants techniques
   - [experience_utilisateur.md](./experience_utilisateur.md) - Projets orientés vers les interfaces et cas d'usage

2. **Fichiers thématiques complémentaires** :
   - [modeles_affaires_ia.md](./modeles_affaires_ia.md) - Modèles d'affaires et cas d'usage commerciaux
   - [exemples_tweety.md](./exemples_tweety.md) - Exemples d'utilisation de TweetyProject
   - [exemples_tweety_par_projet.md](./exemples_tweety_par_projet.md) - Exemples spécifiques par projet
   - [matrice_interdependances.md](./matrice_interdependances.md) - Relations et dépendances entre projets
   - [message_annonce_etudiants.md](./message_annonce_etudiants.md) - Message d'annonce aux étudiants
   - [sujets_projets_detailles.md](./sujets_projets_detailles.md) - Présentation détaillée des sujets

3. **Dossier de ressources d'aide** :
   - [sujets/aide/README.md](./sujets/aide/README.md) - Point d'entrée pour les ressources d'aide spécifiques aux projets (ce document pointe également vers le [Portail des Guides](../guides/README.md) pour une aide plus générale).
   - [sujets/aide/DEMARRAGE_RAPIDE.md](./sujets/aide/DEMARRAGE_RAPIDE.md) - Guide de démarrage rapide
   - [sujets/aide/FAQ_DEVELOPPEMENT.md](./sujets/aide/FAQ_DEVELOPPEMENT.md) - FAQ pour le développement
   - [sujets/aide/GUIDE_INTEGRATION_PROJETS.md](./sujets/aide/GUIDE_INTEGRATION_PROJETS.md) - Guide d'intégration
   - [sujets/aide/interface-web/](./sujets/aide/interface-web/) - Ressources pour les interfaces web

Les fichiers sont interconnectés par des liens relatifs pour faciliter la navigation entre les différents aspects des projets.

## Structure des Sujets de Projets

Chaque sujet de projet est présenté avec une structure standardisée :

- **Contexte** : Présentation du domaine et de son importance
- **Objectifs** : Ce que le projet vise à accomplir
- **Technologies clés** : Outils, frameworks et concepts essentiels
- **Niveau de difficulté** : Évaluation de la complexité (⭐⭐ à ⭐⭐⭐⭐⭐)
- **Estimation d'effort** : Temps de développement estimé en semaines-personnes
- **Interdépendances** : Liens avec d'autres sujets de projets
- **Références** : Sources et documentation pour approfondir
- **Livrables attendus** : Résultats concrets à produire

## Filtrage des Projets

### Par Niveau de Difficulté

#### Niveau ⭐⭐ (Accessible)
Ces projets sont relativement accessibles et constituent un bon point d'entrée pour les étudiants qui débutent dans le domaine.

- [Documentation et transfert de connaissances](./developpement_systeme.md#214-documentation-et-transfert-de-connaissances)

#### Niveau ⭐⭐⭐ (Intermédiaire)
Ces projets nécessitent une bonne compréhension des concepts fondamentaux et une certaine expérience en développement logiciel.

- [Taxonomie des schémas argumentatifs](./fondements_theoriques.md#131-taxonomie-des-schémas-argumentatifs)
- [Classification des sophismes](./fondements_theoriques.md#132-classification-des-sophismes)
- [Ontologie de l'argumentation](./fondements_theoriques.md#133-ontologie-de-largumentation)
- [Agent de détection de sophismes et biais cognitifs](./developpement_systeme.md#232-agent-de-détection-de-sophismes-et-biais-cognitifs)
- [Plateforme éducative d'apprentissage de l'argumentation](./experience_utilisateur.md#328-plateforme-éducative-dapprentissage-de-largumentation)

#### Niveau ⭐⭐⭐⭐ (Avancé)
Ces projets sont plus complexes et nécessitent une expertise technique solide ainsi qu'une bonne compréhension des concepts théoriques avancés.

- [Formules booléennes quantifiées (QBF)](./fondements_theoriques.md#115-formules-booléennes-quantifiées-qbf)
- [Argumentation basée sur les hypothèses (ABA)](./fondements_theoriques.md#124-argumentation-basée-sur-les-hypothèses-aba)
- [Argumentation structurée (ASPIC+)](./fondements_theoriques.md#126-argumentation-structurée-aspic)
- [Abstract Dialectical Frameworks (ADF)](./fondements_theoriques.md#128-abstract-dialectical-frameworks-adf)
- [Fact-checking automatisé et détection de désinformation](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)
- [Système d'analyse de débats politiques et surveillance des médias](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)
- [Protection des systèmes d'IA contre les attaques adversariales](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)

#### Niveau ⭐⭐⭐⭐⭐ (Très avancé)
Ces projets représentent les défis les plus ambitieux et nécessitent une expertise technique de haut niveau ainsi qu'une compréhension approfondie des concepts théoriques.

- [ArgumentuMind: Système cognitif de compréhension argumentative](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)
- [ArgumentuShield: Système de protection cognitive contre la désinformation](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)

### Par Durée Estimée

#### Projets courts (2-3 semaines-personnes)
Ces projets peuvent être réalisés dans un délai relativement court, ce qui les rend particulièrement adaptés aux étudiants ayant des contraintes de temps.

- [Documentation et transfert de connaissances](./developpement_systeme.md#214-documentation-et-transfert-de-connaissances)
- [Classification des sophismes](./fondements_theoriques.md#132-classification-des-sophismes)
- [Taxonomie des schémas argumentatifs](./fondements_theoriques.md#131-taxonomie-des-schémas-argumentatifs)

#### Projets moyens (3-4 semaines-personnes)
Ces projets représentent un équilibre entre ambition et faisabilité, et constituent le cœur des propositions.

- [Logiques formelles et raisonnement](./fondements_theoriques.md#11-logiques-formelles-et-raisonnement)
- [Frameworks d'argumentation](./fondements_theoriques.md#12-frameworks-dargumentation)
- [Ontologie de l'argumentation](./fondements_theoriques.md#133-ontologie-de-largumentation)
- [Maintenance de la vérité et révision de croyances](./fondements_theoriques.md#14-maintenance-de-la-vérité-et-révision-de-croyances)
- [Architecture et orchestration](./developpement_systeme.md#21-architecture-et-orchestration)
- [Gestion des sources et données](./developpement_systeme.md#22-gestion-des-sources-et-données)
- [Moteur agentique et agents spécialistes](./developpement_systeme.md#23-moteur-agentique-et-agents-spécialistes)
- [Indexation sémantique](./developpement_systeme.md#24-indexation-sémantique)
- [Automatisation et intégration MCP](./developpement_systeme.md#25-automatisation-et-intégration-mcp)
- [Interfaces utilisateurs](./experience_utilisateur.md#31-interfaces-utilisateurs)

#### Projets longs (4+ semaines-personnes)
Ces projets représentent les défis les plus ambitieux, nécessitant un investissement temporel important et une grande autonomie.

- [Formules booléennes quantifiées (QBF)](./fondements_theoriques.md#115-formules-booléennes-quantifiées-qbf)
- [Argumentation basée sur les hypothèses (ABA)](./fondements_theoriques.md#124-argumentation-basée-sur-les-hypothèses-aba)
- [Argumentation structurée (ASPIC+)](./fondements_theoriques.md#126-argumentation-structurée-aspic)
- [Abstract Dialectical Frameworks (ADF)](./fondements_theoriques.md#128-abstract-dialectical-frameworks-adf)
- [Raisonnement non-monotone](./fondements_theoriques.md#143-raisonnement-non-monotone)
- [Mesures d'incohérence et résolution](./fondements_theoriques.md#144-mesures-dincohérence-et-résolution)
- [Gouvernance multi-agents](./developpement_systeme.md#216-gouvernance-multi-agents)
- [Abstraction du moteur agentique](./developpement_systeme.md#231-abstraction-du-moteur-agentique)
- [Agent de formalisation logique](./developpement_systeme.md#234-agent-de-formalisation-logique)
- [Intégration de LLMs locaux légers](./developpement_systeme.md#236-intégration-de-llms-locaux-légers)
- [Fact-checking automatisé et détection de désinformation](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)
- [Développement d'un serveur MCP pour l'analyse argumentative](./developpement_systeme.md#253-développement-dun-serveur-mcp-pour-lanalyse-argumentative)
- [Serveur MCP pour les frameworks d'argumentation Tweety](./developpement_systeme.md#255-serveur-mcp-pour-les-frameworks-dargumentation-tweety)
- [Protection des systèmes d'IA contre les attaques adversariales](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)
- [Système de collaboration en temps réel](./experience_utilisateur.md#317-système-de-collaboration-en-temps-réel)
- [ArgumentuMind: Système cognitif de compréhension argumentative](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)
- [ArgumentuShield: Système de protection cognitive contre la désinformation](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)

### Par Technologie

#### Frameworks d'argumentation (TweetyProject)
TweetyProject est une bibliothèque Java pour l'intelligence artificielle symbolique qui offre de nombreux modules pour l'argumentation computationnelle.

- [Logique propositionnelle (`logics.pl`)](./fondements_theoriques.md#111-intégration-des-logiques-propositionnelles-avancées)
- [Logique du premier ordre (`logics.fol`)](./fondements_theoriques.md#112-logique-du-premier-ordre-fol)
- [Logique modale (`logics.ml`)](./fondements_theoriques.md#113-logique-modale)
- [Logique de description (`logics.dl`)](./fondements_theoriques.md#114-logique-de-description-dl)
- [Formules booléennes quantifiées (`logics.qbf`)](./fondements_theoriques.md#115-formules-booléennes-quantifiées-qbf)
- [Logique conditionnelle (`logics.cl`)](./fondements_theoriques.md#116-logique-conditionnelle-cl)
- [Argumentation abstraite (`arg.dung`)](./fondements_theoriques.md#121-argumentation-abstraite-de-dung)
- [Argumentation bipolaire (`arg.bipolar`)](./fondements_theoriques.md#122-argumentation-bipolaire)
- [Argumentation pondérée (`arg.prob`, `arg.social`)](./fondements_theoriques.md#123-argumentation-pondérée)
- [Argumentation basée sur les hypothèses (`arg.aba`)](./fondements_theoriques.md#124-argumentation-basée-sur-les-hypothèses-aba)
- [Abstract Dialectical Frameworks (`arg.adf`)](./fondements_theoriques.md#128-abstract-dialectical-frameworks-adf)
- [Argumentation probabiliste (`arg.prob`)](./fondements_theoriques.md#129-analyse-probabiliste-darguments)
- [Révision de croyances (`beliefdynamics`)](./fondements_theoriques.md#145-révision-de-croyances-multi-agents)

#### Traitement du Langage Naturel (NLP)
- [Analyse de texte et extraction d'information](./developpement_systeme.md#221-amélioration-du-moteur-dextraction)
- [Détection de sophismes et biais](./developpement_systeme.md#232-agent-de-détection-de-sophismes-et-biais-cognitifs)
- [Génération de texte et contre-arguments](./developpement_systeme.md#233-agent-de-génération-de-contre-arguments)
- [Fact-checking et vérification](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)
- [Formalisation logique](./developpement_systeme.md#234-agent-de-formalisation-logique)
- [Modèles de langage (LLMs)](./developpement_systeme.md#236-intégration-de-llms-locaux-légers)

#### Indexation et Recherche Sémantique
- [Embeddings et bases de données vectorielles](./developpement_systeme.md#241-index-sémantique-darguments)
- [Bases de connaissances et graphes](./developpement_systeme.md#243-base-de-connaissances-argumentatives)
- [Gestion de corpus](./developpement_systeme.md#224-gestion-de-corpus)

#### Visualisation et Interfaces Utilisateur
- [Visualisation de graphes d'argumentation](./experience_utilisateur.md#314-visualisation-avancée-de-graphes-dargumentation-et-de-réseaux-de-désinformation)
- [Interfaces web et dashboards](./experience_utilisateur.md#311-interface-web-pour-lanalyse-argumentative)
- [Éditeurs et outils interactifs](./experience_utilisateur.md#313-éditeur-visuel-darguments)
- [Applications mobiles et accessibilité](./experience_utilisateur.md#315-interface-mobile)

#### Architecture et Orchestration
- [Systèmes multi-agents](./developpement_systeme.md#21-architecture-et-orchestration)
- [Frameworks agentiques](./developpement_systeme.md#231-abstraction-du-moteur-agentique)
- [Monitoring et évaluation](./developpement_systeme.md#213-monitoring-et-évaluation)

#### Automatisation et Intégration
- [Pipelines de traitement](./developpement_systeme.md#251-automatisation-de-lanalyse)
- [Intégration MCP (Model Context Protocol)](./developpement_systeme.md#25-automatisation-et-intégration-mcp)
- [CI/CD et déploiement](./developpement_systeme.md#215-intégration-continue-et-déploiement)

#### Sécurité et Protection des Données
- [Cryptographie et contrôle d'accès](./developpement_systeme.md#223-sécurisation-des-données)
- [Protection contre les attaques](./developpement_systeme.md#256-protection-des-systèmes-dia-contre-les-attaques-adversariales)

#### Applications Éducatives et Délibératives
- [Plateformes éducatives](./experience_utilisateur.md#322-plateforme-déducation-à-largumentation)
- [Systèmes délibératifs](./experience_utilisateur.md#327-plateforme-de-délibération-citoyenne)

#### Systèmes Cognitifs Avancés
- [Modélisation cognitive](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)
- [Protection cognitive](./experience_utilisateur.md#326-système-danalyse-de-débats-politiques-et-surveillance-des-médias)

## Ressources Disponibles

Pour faciliter la réalisation des projets, plusieurs ressources sont mises à disposition des étudiants. Il est crucial de commencer par consulter les documentations générales du système pour acquérir une compréhension globale :

1.  **Documentation Générale du Système (Fortement Recommandé)**:
    *   **[Portail des Guides](../guides/README.md)** : Point d'entrée principal vers tous les guides pratiques (développement, utilisation, API web, conventions, exemples de logiques, etc.). **À consulter en priorité.**
    *   **[Documentation d'Architecture](../architecture/README.md)** : Décrit l'architecture globale du système, l'orchestration des agents, la communication inter-agents, l'architecture hiérarchique, et d'autres concepts fondamentaux. Essentiel pour les projets touchant au cœur du système.
    *   **[Documentation des Composants](../composants/README.md)** : Présente les différents modules et composants réutilisables du système (Moteur de Raisonnement, Pont Tweety, API Web, etc.), leurs fonctionnalités et comment les intégrer.

2.  **Documentation Spécifique aux Projets**:
    *   [Exemples TweetyProject](./exemples_tweety.md) - Guide d'utilisation de la bibliothèque TweetyProject pour l'argumentation.
    *   [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md) - Exemples spécifiques pour chaque projet.

3.  **Ressources d'Aide Pratique (au sein de `docs/projets/`)**:
    *   [Point d'entrée de l'aide aux projets](./sujets/aide/README.md) - Centralise les ressources d'aide spécifiques aux projets et oriente vers les guides généraux.
    *   [Guide de démarrage rapide](./sujets/aide/DEMARRAGE_RAPIDE.md) - Instructions pour commencer rapidement.
    *   [FAQ Développement](./sujets/aide/FAQ_DEVELOPPEMENT.md) - Réponses aux questions fréquentes.
    *   [Guide d'intégration des projets](./sujets/aide/GUIDE_INTEGRATION_PROJETS.md) - Comment intégrer votre projet.

4.  **Exemples de Code**:
    *   [Exemples d'interfaces web (React)](./sujets/aide/interface-web/exemples-react/) - Composants React réutilisables.
    *   Code prêt à l'emploi pour démarrer rapidement (disponible dans les dépôts spécifiques ou les sections d'aide).
    *   Solutions aux problèmes courants (voir FAQ et guides).

5.  **Contexte et Applications**:
    *   [Modèles d'affaires pour l'IA](./modeles_affaires_ia.md) - Applications commerciales potentielles et cas d'usage.

## Modalités de Réalisation

### Organisation en groupes

Le projet peut être réalisé individuellement ou en groupe de 2 à 4 étudiants. Voici quelques conseils selon la taille de votre groupe :

#### Travail individuel
- Choisissez un sujet bien délimité et réaliste pour une personne
- Concentrez-vous sur une fonctionnalité spécifique à implémenter
- Documentez soigneusement votre travail pour faciliter l'intégration

#### Groupe de 2 étudiants
- Répartissez clairement les tâches entre les membres
- Établissez un planning de travail et des points de synchronisation réguliers
- Utilisez les branches Git pour travailler en parallèle

#### Groupe de 3-4 étudiants
- Désignez un chef de projet pour coordonner le travail
- Divisez le projet en sous-modules indépendants
- Mettez en place un processus de revue de code entre membres
- Utilisez les issues GitHub pour suivre l'avancement

### Livrables attendus

Pour chaque projet, vous devrez fournir :
1. Le code source de votre implémentation
2. Une documentation détaillée expliquant votre approche (en s'appuyant sur et en référençant la documentation existante)
3. Des tests unitaires et d'intégration
4. Un rapport final résumant votre travail

## Évaluation

L'évaluation des présentations avec slides et démo sera collégiale. La note de l'enseignant comptera pour moitié.

L'évaluation portera sur 4 critères :
1. **Forme/communication** : Qualité de la présentation, clarté des explications, structure des slides et de la démo
2. **Théorie** : Exploration et explication de l'état de l'art et des techniques utilisées, pertinence par rapport aux documentations de référence.
3. **Technique** : Réalisations, performances, tests et qualité du code, intégration avec l'écosystème existant.
4. **Gestion de projet/collaboration** : Gestion intelligente de GitHub et du travail collaboratif durant la durée du projet

## Choix d'un Sujet

Lors du choix de votre sujet, tenez compte de :
- La taille de votre groupe
- Vos compétences et intérêts
- Le temps disponible pour réaliser le projet
- Les interdépendances avec d'autres projets (voir [matrice_interdependances.md](./matrice_interdependances.md))
- **La nécessité de bien comprendre l'écosystème via les documentations d'architecture, des composants et les guides.**

Consultez les pages spécifiques à chaque catégorie pour une description détaillée des projets disponibles :

- [Fondements théoriques et techniques](./fondements_theoriques.md)
- [Développement système et infrastructure](./developpement_systeme.md)
- [Expérience utilisateur et applications](./experience_utilisateur.md)

## Ressources associées

Ces documents au sein de `docs/projets/` fournissent un contexte supplémentaire pour les projets :

- [Matrice d'interdépendances](./matrice_interdependances.md) - Relations entre les différents projets
- [Message d'annonce aux étudiants](./message_annonce_etudiants.md) - Présentation initiale des projets
- [Modèles d'affaires pour l'IA](./modeles_affaires_ia.md) - Applications commerciales potentielles (aussi listé dans "Ressources Disponibles")
- [Sujets de projets détaillés](./sujets_projets_detailles.md) - Présentation alternative des projets

---

*Dernière mise à jour : 04/06/2025*
