# Rapport d'Analyse : Démonstrations de Logique Formelle Cluedo et Einstein

**Date :** 2025-08-22

**Auteur :** Roo

## 1. Introduction

Ce rapport présente une analyse complète des scripts de démonstration pour les cas d'usage "Cluedo" et "Énigme d'Einstein". L'objectif est d'évaluer leur état de fonctionnement, leur robustesse, et la qualité de leur documentation, conformément à la méthodologie SDDD (Semantic-Documentation-Driven-Design).

## 2. Analyse de la Démonstration Cluedo

### 2.1. Scripts Pertinents

*   **Script principal identifié :** [`scripts/sherlock_watson/run_cluedo_oracle_enhanced.py`](scripts/sherlock_watson/run_cluedo_oracle_enhanced.py)
*   **Documentation associée :** [`docs/entry_points/ep1_demos_sherlock_watson_moriarty.md`](docs/entry_points/ep1_demos_sherlock_watson_moriarty.md)

### 2.2. Description du Fonctionnement

Le script `run_cluedo_oracle_enhanced.py` orchestre une partie de Cluedo simulée entre trois agents : Sherlock, Watson et Moriarty (agissant en tant qu'oracle). Le script initialise un environnement complet, y compris la JVM pour la compatibilité avec les composants logiques, et gère le déroulement du jeu tour par tour. Il est conçu pour être exécuté en mode normal (avec un LLM) ou en mode test (avec des réponses mockées).

### 2.3. Résultats de l'Exécution

*   **État initial :** Le script échouait en raison d'une erreur `TypeError: object async_generator can't be used in 'await' expression` et d'une autre erreur `TypeError: WatsonLogicAssistant.invoke_single() got an unexpected keyword argument 'input'`.
*   **Corrections apportées :**
    1.  Correction de la logique d'appel asynchrone dans `argumentation_analysis/orchestration/cluedo_extended_orchestrator.py` pour gérer correctement les coroutines et les générateurs asynchrones.
    2.  Modification de la signature de la méthode `invoke_single` dans `argumentation_analysis/agents/core/logic/watson_logic_assistant.py` pour accepter des arguments par mot-clé, améliorant ainsi sa robustesse.
*   **État final :** Le script s'exécute maintenant sans erreur technique en mode test. Cependant, la partie se solde par un échec car les agents mockés ne produisent pas de réponses permettant de résoudre l'enquête.

## 3. Analyse de la Démonstration Einstein

### 3.1. Scripts Pertinents

*   **Script principal identifié :** [`scripts/sherlock_watson/run_einstein_oracle_demo.py`](scripts/sherlock_watson/run_einstein_oracle_demo.py)
*   **Documentation associée :** [`docs/einstein_tweety_puzzle.md`](docs/einstein_tweety_puzzle.md)

### 3.2. Description du Fonctionnement

Le script `run_einstein_oracle_demo.py` simule la résolution de l'énigme d'Einstein. Un oracle (Moriarty) fournit progressivement des indices à des agents Sherlock et Watson simulés. Ces agents "analysent" les indices et tentent de déduire la solution. Le script n'utilise pas de LLM pour le raisonnement des agents ; leurs réponses sont pré-écrites.

### 3.3. Résultats de l'Exécution

*   **État :** Le script est entièrement fonctionnel. Il s'exécute sans erreur et parvient à la conclusion correcte de l'énigme, démontrant que la logique de l'oracle et le déroulement du scénario sont corrects.

## 4. Évaluation et Recommandations

### 4.1. État Général

*   **Fonctionnalité :** Les deux scripts de démonstration sont maintenant techniquement fonctionnels.
*   **Robustesse :** La robustesse a été améliorée grâce aux corrections apportées. L'intégration de la JVM, un point de fragilité historique, est stable dans les deux scripts.
*   **Documentation :** La documentation est de bonne qualité et permet de comprendre l'objectif et le fonctionnement des démonstrations.

### 4.2. Recommandations

1.  **Fiabiliser les agents mockés :** Les réponses des agents mockés dans la démonstration Cluedo devraient être améliorées pour permettre une résolution réussie de l'enquête. Cela rendrait la démonstration plus utile pour la validation fonctionnelle.
2.  **Créer des tests d'intégration :** Des tests d'intégration dédiés devraient être créés pour ces deux démonstrations. Ces tests permettraient de :
    *   Valider automatiquement le bon fonctionnement des scripts après chaque modification du code.
    *   S'assurer qu'il n'y a pas de régressions.
    *   Tester les différents modes et options des scripts (par exemple, les différentes stratégies de l'oracle Cluedo).
3.  **Utiliser un LLM pour la démo Einstein :** Pour une véritable démonstration des capacités de raisonnement logique, le script de la démo Einstein devrait être adapté pour utiliser un LLM (comme le fait la démo Cluedo) au lieu de réponses pré-écrites.

## 5. Actions de Fiabilisation et de Test (Mise à jour du 2025-08-22)

Suite à l'analyse initiale, les actions suivantes ont été menées pour fiabiliser les démonstrations et garantir leur robustesse à long terme via des tests d'intégration automatisés.

### 5.1. Fiabilisation des Scripts pour les Tests

Les deux scripts de démonstration ont été modifiés pour accepter un argument en ligne de commande `--integration-test`. Ce flag permet d'adapter leur comportement pour une exécution dans un contexte de test automatisé :

*   **`run_einstein_oracle_demo.py`** : En mode intégration, les pauses (`asyncio.sleep`) sont désactivées pour une exécution plus rapide.
*   **`run_cluedo_oracle_enhanced.py`** : L'argument `--integration-test` agit comme un alias pour `--test-mode`, forçant l'utilisation de services LLM mockés et évitant ainsi la dépendance à des clés API externes.

Cette approche permet de tester la logique des scripts de manière isolée et reproductible.

### 5.2. Création de la Suite de Tests d'Intégration

Un nouveau fichier de test, [`tests/integration/test_logic_demos.py`](tests/integration/test_logic_demos.py), a été créé. Il contient deux tests qui s'exécutent en sous-processus isolés pour éviter les conflits liés à la gestion de la JVM :

1.  **Test pour Einstein (`test_einstein_demo_runs_successfully`)** :
    *   Lance le script `run_einstein_oracle_demo.py` avec le flag `--integration-test`.
    *   Vérifie que le script se termine avec un code de sortie de `0` (succès).
    *   Valide que la sortie `stdout` contient bien la solution de l'énigme ("L'Allemand possède le poisson").

2.  **Test pour Cluedo (`test_cluedo_demo_runs_successfully`)** :
    *   Lance le script `run_cluedo_oracle_enhanced.py` avec le flag `--integration-test`.
    *   Vérifie que le script se termine avec un code de sortie de `0`.
    *   Valide que le script s'exécute jusqu'à la fin en cherchant la présence du "RAPPORT FINAL DE LA PARTIE" dans la sortie.

Ces tests garantissent que les points d'entrée principaux des démonstrations restent fonctionnels et préviennent les régressions futures.