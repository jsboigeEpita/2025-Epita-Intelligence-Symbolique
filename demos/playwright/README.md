# Démos Playwright - Tests Fonctionnels

## Vue d'Ensemble

Ce répertoire contient les démonstrations Playwright organisées pour tester les fonctionnalités clés du système d'analyse argumentative. Ces tests simulent des interactions complètes de bout en bout.

## Tests Fonctionnels Disponibles (9 au total)

### 1. **test_argument_analyzer.py**
- **Description :** Valide l'analyseur d'arguments principal
- **Workflows :** Analyse de structures argumentatives, identification des prémisses et conclusions
- **Interface :** Tests via API et interface web

### 2. **test_argument_reconstructor.py** 
- **Description :** Teste la reconstruction d'arguments complexes
- **Workflows :** Reconstruction logique, validation de cohérence
- **Interface :** Traitement de textes argumentatifs

### 3. **test_fallacy_detector.py**
- **Description :** Validation du détecteur de sophismes
- **Workflows :** Détection contextuelle, analyse de gravité, catégorisation
- **Interface :** Pipeline complet de détection

### 4. **test_framework_builder.py**
- **Description :** Tests du constructeur de frameworks d'analyse  
- **Workflows :** Construction dynamique de pipelines, configuration adaptative
- **Interface :** Système de configuration et orchestration

### 5. **test_integration_workflows.py**
- **Description :** Tests d'intégration des workflows complets
- **Workflows :** Orchestration multi-agents, coordination hiérarchique
- **Interface :** Intégration stratégique/tactique/opérationnelle

### 6. **test_logic_graph.py**
- **Description :** Validation des graphes logiques
- **Workflows :** Représentation graphique des arguments, navigation logique
- **Interface :** Visualisation et manipulation de structures

### 7. **test_service_manager.py** ✅ VALIDÉ
- **Description :** Tests du gestionnaire de services (INFRASTRUCTURE VALIDÉE)
- **Workflows :** Gestion des services, coordination des agents
- **Interface :** ServiceManager opérationnel et testé
- **Status :** **DÉMO FONCTIONNELLE** déplacée vers `demo_service_manager_validated.py`

### 8. **test_validation_form.py**
- **Description :** Tests des formulaires de validation
- **Workflows :** Validation d'entrées, gestion d'erreurs
- **Interface :** Interface utilisateur de validation

### 9. **test_webapp_homepage.py**
- **Description :** Tests de la page d'accueil de l'application web
- **Workflows :** Navigation, interface utilisateur, intégration frontend
- **Interface :** Tests Playwright de l'interface web complète

## Fichiers de Support

### Configuration
- **`conftest_reference.py`** : Configuration Playwright de référence (copié depuis tests/functional)
- **`test_interface_demo.html`** : Interface de test pour les démos (déplacé depuis racine)

### Démo Validée
- **`demo_service_manager_validated.py`** : Démo ServiceManager validée et opérationnelle

## Infrastructure de Test

- **Technologie :** Playwright pour les tests end-to-end
- **Configuration :** Environnement mocké pour reproductibilité  
- **Prérequis :** Installation Playwright, dépendances projet
- **Exécution :** `pytest demos/playwright/` depuis la racine

## Status Général

- ✅ **ServiceManager** : Infrastructure validée et opérationnelle
- 🔄 **8 autres tests** : Prêts pour validation, attendent configuration finale
- 📁 **Structure organisée** : Démos centralisées dans demos/playwright/
- 🗂️ **Configuration propre** : Fichiers de config référencés

## Notes de Migration

Ces tests ont été organisés dans le cadre de la **Phase 3 - Finalisation** du nettoyage du projet. L'infrastructure de base (ServiceManager) est validée et les autres tests peuvent être exécutés selon les besoins spécifiques.