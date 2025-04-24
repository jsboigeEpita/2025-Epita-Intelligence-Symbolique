# Projet Intelliengece Symbolique

## Introduction

Ce projet a pour but de vous permettre d'appliquer concrètement les méthodes et outils vus en cours sur l'intelligence symbolique. Vous serez amenés à résoudre des problèmes réels ou réalistes à l'aide de ces techniques en développant un projet complet, depuis la modélisation jusqu'à la solution opérationnelle.

## Modalités du projet

### Livrables

Chaque groupe devra forker ce dépôt  Git et déposer son travail dans un répertoire dédié du dépôt. Ce répertoire contiendra :

- Le code source complet, opérationnel, documenté et maintenable (en Python, C#, C++, ou autre).
- Le matériel complémentaire utilisé pour le projet (datasets, scripts auxiliaires, etc.).
- Les slides utilisés lors de la présentation finale.
- Un notebook explicatif détaillant les étapes du projet, les choix de modélisation, les expérimentations et les résultats obtenus.

Les livraisons se feront via des **pull requests**, qui devront être régulièrement mises à jour durant toute la durée du projet de sorte que l'enseignant puisse suivre l'avancement et éventuellement apporter des retours et de sorte que tous les élèves aient pu prendre connaissance des travaux des autres groupes avant la soutenance avec évaluation collégiale.

### Présentation

- Présentation orale finale avec support visuel (slides).
- Démonstration de la solution opérationnelle devant la classe.

### Évaluation

- Évaluation collégiale : chaque élève évaluera les autres groupes en complément de l’évaluation réalisée par l’enseignant.
- Critères : clarté, originalité, robustesse de la solution, qualité du code, pertinence des choix méthodologiques et organisation.

## Utilisation des LLMs

### Outils à disposition

Pour faciliter la réalisation du projet, vous aurez accès à plusieurs ressources avancées :

- **Plateforme Open-WebUI** : intégrant des modèles d'intelligence artificielle d'OpenAI et locaux très performants, ainsi que des plugins spécifiques et une base de connaissances complète alimentée par la bibliographie du cours (indexée via ChromaDB, taper # en conversation pour invoquer les KB).
- **Clés d'API OpenAI et locales** : mise à votre disposition pour exploiter pleinement les capacités des modèles GPT dans vos développements.
- **Notebook Agentique** : un notebook interactif permettant d'automatiser la création ou la finalisation de vos propres notebooks, facilitant ainsi la structuration et l'amélioration de vos solutions.

### Combinaison LLM et CSP

Vous avez également la possibilité d'intégrer les Large Language Models (LLMs) directement dans votre projet CSP afin d'en étendre significativement les capacités, via :

- Une utilisation directe des LLM pour assister la conception ou la résolution de CSP complexes.
- Le recours au "function calling" : fournir à un LLM un accès direct à votre CSP, permettant ainsi au modèle de piloter la résolution du problème de manière plus flexible et intuitive. Le notebook agentique fourni constitue un exemple pratique et efficace de cette méthodologie légère mais puissante. La normalisation en cours des MCPs constitue également un excellent exemple d'application de cette approche (vous développez un MCP utilisant la PrCon dans le cadre de votre projet).
