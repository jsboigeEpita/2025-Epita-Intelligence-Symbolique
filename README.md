# Projet Intelligence Symbolique

## Introduction

Ce projet a pour but de vous permettre d'appliquer concrètement les méthodes et outils vus en cours sur l'intelligence symbolique. Vous serez amenés à résoudre des problèmes réels ou réalistes à l'aide de ces techniques en développant un projet complet, depuis la modélisation jusqu'à la solution opérationnelle.

Cette année, contrairement au cours précédent de programmation par contrainte où vous avez livré des travaux indépendants, vous travaillerez tous de concert sur ce dépôt. Un tronc commun est fourni sous la forme d'une infrastructure d'analyse argumentative multi-agents que vous pourrez explorer à travers les nombreux README du projet.

## Modalités du projet

### Livrables

Chaque groupe devra contribuer au dépôt principal via des **pull requests** régulières. Ces contributions devront être clairement identifiées et documentées, et pourront inclure :

- Le code source complet, opérationnel, documenté et maintenable (en Python, Java via JPype, ou autre).
- Le matériel complémentaire utilisé pour le projet (datasets, scripts auxiliaires, etc.).
- Les slides utilisés lors de la présentation finale.
- Un notebook explicatif détaillant les étapes du projet, les choix de modélisation, les expérimentations et les résultats obtenus.

Les pull requests devront être régulièrement mises à jour durant toute la durée du projet afin que l'enseignant puisse suivre l'avancement et éventuellement apporter des retours, et que tous les élèves puissent prendre connaissance des travaux des autres groupes avant la soutenance avec évaluation collégiale.

### Présentation

- Présentation orale finale avec support visuel (slides).
- Démonstration de la solution opérationnelle devant la classe.

### Évaluation

- Évaluation collégiale : chaque élève évaluera les autres groupes en complément de l'évaluation réalisée par l'enseignant.
- Critères : clarté, originalité, robustesse de la solution, qualité du code, pertinence des choix méthodologiques et organisation.

## Utilisation des LLMs et IA Symbolique

### Outils à disposition

Pour faciliter la réalisation du projet, vous aurez accès à plusieurs ressources avancées :

- **Plateforme Open-WebUI** : intégrant des modèles d'intelligence artificielle d'OpenAI et locaux très performants, ainsi que des plugins spécifiques et une base de connaissances complète alimentée par la bibliographie du cours.
- **Clés d'API OpenAI et locales** : mise à votre disposition pour exploiter pleinement les capacités des modèles GPT dans vos développements.
- **Notebook Agentique** : un notebook interactif permettant d'automatiser la création ou la finalisation de vos propres notebooks, facilitant ainsi la structuration et l'amélioration de vos solutions.
- **Bibliothèque Tweety** : une bibliothèque Java complète pour l'IA symbolique, intégrée via JPype, offrant de nombreux modules pour différentes logiques et raisonnements.

### Combinaison IA Générative et IA Symbolique

Le projet se concentre sur l'intégration de l'IA générative agentique orchestrée avec des techniques d'IA symbolique, notamment pour l'analyse argumentative. Cette approche hybride permet de combiner la flexibilité et la puissance des LLMs avec la rigueur et la formalisation des méthodes symboliques.

## Sujets de Projets

Les sujets proposés ci-dessous couvrent différents aspects de l'IA symbolique, avec un focus particulier sur l'argumentation et son intégration par l'IA générative agentique orchestrée. Chaque groupe devra choisir un sujet et contribuer à l'amélioration du projet global.

### Domaines Fondamentaux

#### Logiques Formelles et Argumentation

- **Intégration des logiques propositionnelles avancées** : Améliorer l'agent PL existant pour exploiter davantage les fonctionnalités du module `logics.pl` de Tweety.
- **Logique du premier ordre (FOL)** : Développer un nouvel agent utilisant le module `logics.fol` de Tweety pour analyser des arguments plus complexes impliquant des quantificateurs et des prédicats.
- **Logique modale** : Créer un agent spécialisé utilisant le module `logics.ml` de Tweety pour raisonner sur des modalités comme la nécessité, la possibilité, les croyances ou les connaissances.
- **Logiques argumentatives** : Explorer et implémenter des agents utilisant les différents modules d'argumentation de Tweety (`arg.dung`, `arg.bipolar`, `arg.aspic`, etc.) pour modéliser et analyser des structures argumentatives complexes.

#### Planification et Raisonnement

- **Intégration d'un planificateur symbolique** : Développer un agent capable de générer des plans d'action basés sur des objectifs argumentatifs.
- **Logiques sociales et planification** : Explorer l'intégration du module `arg.social` de Tweety avec des techniques de planification pour modéliser des interactions argumentatives multi-agents.

#### Ingénierie des Connaissances

- **Intégration d'ontologies AIF.owl** : Développer un moteur sémantique basé sur l'ontologie AIF (Argument Interchange Format) pour structurer les arguments.
- **Classification des arguments fallacieux** : Corriger et intégrer l'ontologie du projet Argumentum pour la classification des sophismes.
- **Knowledge Graph argumentatif** : Remplacer la structure JSON actuelle de l'état partagé par un graphe de connaissances plus expressif et interrogeable.

#### Maintenance de la Vérité

- **Intégration des modules de maintenance de la vérité** : Résoudre les problèmes d'import des modules correspondants de Tweety et les intégrer au système.
- **Révision de croyances argumentatives** : Développer un agent capable de mettre à jour ses croyances en fonction de nouveaux arguments.

#### Smart Contracts

- **Formalisation de contrats argumentatifs** : Explorer l'utilisation de smart contracts pour formaliser et exécuter des protocoles d'argumentation.
- **Vérification formelle d'arguments** : Développer des méthodes de vérification formelle pour garantir la validité des arguments dans un contexte contractuel.

### Développements Transversaux

#### Gestion des Sources

- **Amélioration du moteur d'extraction** : Perfectionner le système actuel qui combine paramétrage d'extraits et sources correspondantes.
- **Support de formats étendus** : Étendre les capacités du moteur d'extraction pour supporter davantage de formats de fichiers et de sources web.
- **Sécurisation des données** : Améliorer le système de chiffrement des sources et configurations d'extraits pour garantir la confidentialité.

#### Moteur Agentique

- **Abstraction du moteur agentique** : Créer une couche d'abstraction permettant d'utiliser différents frameworks agentiques (au-delà de Semantic Kernel).
- **Orchestration avancée** : Développer des stratégies d'orchestration plus sophistiquées pour la collaboration entre agents.
- **Mécanismes de résolution de conflits** : Implémenter des méthodes pour résoudre les désaccords entre agents lors de l'analyse argumentative.

#### Intégration MCP (Model Context Protocol)

- **Développement d'un serveur MCP** : Publier le travail collectif sous forme d'un serveur MCP utilisable dans des applications comme Roo, Claude Desktop ou Semantic Kernel.
- **Outils MCP pour l'analyse argumentative** : Créer des outils MCP spécifiques pour l'analyse et la manipulation d'arguments.

#### Agents Spécialistes

- **Agents de logique formelle** : Développer de nouveaux agents spécialisés utilisant différentes parties de Tweety.
- **Agent de détection de sophismes** : Améliorer la détection et la classification des sophismes dans les textes.
- **Agent de génération de contre-arguments** : Créer un agent capable de générer des contre-arguments pertinents.

#### Indexation Sémantique

- **Index sémantique d'arguments** : Indexer les définitions, exemples et instances d'arguments fallacieux pour permettre des recherches par proximité sémantique.
- **Vecteurs de types d'arguments** : Définir par assemblage des vecteurs de types d'arguments fallacieux pour faciliter la découverte de nouvelles instances.

#### Automatisation

- **Automatisation de l'analyse** : Développer des outils pour lancer l'équivalent du notebook d'analyse dans le cadre d'automates longs sur des corpus.
- **Pipeline de traitement** : Créer un pipeline complet pour l'ingestion, l'analyse et la visualisation des résultats d'analyse argumentative.

### Projets Intégrateurs

- **Système de débat assisté par IA** : Développer une application complète permettant à des utilisateurs de débattre avec l'assistance d'agents IA qui analysent et améliorent leurs arguments.
- **Plateforme d'éducation à l'argumentation** : Créer un outil éducatif pour enseigner les principes de l'argumentation et aider à identifier les sophismes.
- **Système d'aide à la décision argumentative** : Développer un système qui aide à la prise de décision en analysant et évaluant les arguments pour et contre différentes options.

## Ressources et Documentation

Pour vous aider dans la réalisation de votre projet, vous trouverez dans ce dépôt :

- Des README détaillés pour chaque composant du système
- Des notebooks explicatifs et interactifs
- Des exemples d'utilisation des différentes bibliothèques
- Une documentation sur l'architecture du système

N'hésitez pas à explorer les différents répertoires du projet pour mieux comprendre son fonctionnement et identifier les opportunités d'amélioration.

