# Documentation du Module de Réparation des Extraits

Ce répertoire contient la documentation technique et les rapports relatifs au module de réparation des bornes défectueuses dans les extraits d'analyse argumentative.

## Vue d'ensemble

Le module de réparation des extraits (`extract_repair`) est conçu pour résoudre les problèmes liés aux marqueurs de début et de fin dans les définitions d'extraits. Cette documentation fournit des informations détaillées sur :

- Les problématiques adressées par le module
- Les solutions techniques implémentées
- Les résultats des processus de réparation
- Les données de référence pour la validation

## Documents disponibles

### repair_extract_markers_report.md

Ce rapport détaille le processus de réparation des bornes défectueuses dans les extraits. Il couvre :

- Le contexte et la problématique des bornes défectueuses
- La solution développée et son approche technique
- Les résultats obtenus sur différents corpus
- Les recommandations pour l'amélioration continue du système

Ce document est essentiel pour comprendre les défis spécifiques liés à l'extraction de texte et les stratégies mises en œuvre pour les surmonter.

### extract_sources_updated.json

Ce fichier contient les définitions d'extraits mises à jour après le processus de réparation. Il sert de référence pour :

- Comparer les définitions avant et après réparation
- Valider l'efficacité des algorithmes de réparation
- Fournir des exemples de cas corrigés pour la documentation

Ce fichier est utilisé comme source de vérité pour les tests et la validation du module de réparation.

## Relation avec les autres composants

Le module de réparation des extraits est étroitement lié à plusieurs autres composants du système :

- **Agent d'extraction** : Utilise les définitions réparées pour extraire correctement les textes
- **Service de définition** : Charge et gère les définitions d'extraits
- **Interface utilisateur** : Permet la visualisation et l'édition manuelle des extraits
- **Tests d'intégration** : Valide que les extraits réparés fonctionnent correctement dans le système global

## Utilisation de la documentation

Cette documentation est destinée à plusieurs publics :

- **Développeurs** : Pour comprendre le fonctionnement technique du module et contribuer à son amélioration
- **Chercheurs** : Pour comprendre les défis liés à l'extraction de texte dans l'analyse argumentative
- **Testeurs** : Pour valider que les réparations sont conformes aux attentes
- **Utilisateurs avancés** : Pour comprendre les limites et capacités du système d'extraction

## Processus de mise à jour

La documentation est mise à jour selon le processus suivant :

1. Chaque modification significative du module de réparation doit être documentée
2. Les rapports de réparation sont générés automatiquement après chaque exécution complète
3. Les statistiques et métriques sont mises à jour pour refléter l'état actuel du système
4. Les cas d'échec sont documentés pour guider les améliorations futures

## Voir aussi

- [Documentation du module de réparation](../README.md)
- [Script de réparation des extraits](../repair_extract_markers.py)
- [Notebook de réparation des extraits](../repair_extract_markers.ipynb)
- [Utilitaire de vérification des extraits](../verify_extracts.py)
- [Documentation de l'agent d'extraction](../../../../agents/core/extract/README.md)