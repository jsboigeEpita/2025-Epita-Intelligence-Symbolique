# Guide d'Utilisation du Projet

## Introduction

Bienvenue dans le guide d'utilisation de ce projet. Ce document a pour objectif de vous aider à prendre en main les différentes fonctionnalités et à comprendre comment utiliser les exemples de code et les scripts fournis.

## 1. Configuration de l'Environnement

Avant toute chose, assurez-vous d'avoir correctement configuré votre environnement de développement. Des scripts sont fournis pour faciliter cette étape :

*   Pour un environnement PowerShell : exécutez le script [`setup_project_env.ps1`](../../setup_project_env.ps1:0).
*   Pour un environnement Bash (Linux/macOS) : exécutez le script [`setup_project_env.sh`](../../setup_project_env.sh:0).

Ces scripts installeront les dépendances nécessaires et configureront les variables d'environnement.

## 2. Exemples d'Utilisation Basiques

Plusieurs exemples sont à votre disposition pour découvrir les fonctionnalités de base du projet.

*   **Scripts de démonstration :** Le répertoire [`examples/scripts_demonstration/`](../../examples/scripts_demonstration/) contient des scripts Python simples illustrant des interactions spécifiques. Par exemple, le script [`demo_tweety_interaction_simple.py`](../../examples/scripts_demonstration/demo_tweety_interaction_simple.py:0) montre une utilisation basique de la librairie Tweety.
*   **Notebooks Jupyter :** Pour une approche plus interactive et didactique, consultez les notebooks disponibles dans [`examples/notebooks/`](../../examples/notebooks/). Le notebook [`api_logic_tutorial.ipynb`](../../examples/notebooks/api_logic_tutorial.ipynb:0) constitue un excellent point de départ pour comprendre l'utilisation de l'API logique.

## 3. Intégration d'API et Agents Logiques

Le projet explore l'intégration avec des API externes et l'utilisation d'agents logiques.

*   Des exemples concrets d'intégration d'API et de mise en œuvre d'agents logiques se trouvent dans le répertoire [`examples/logic_agents/`](../../examples/logic_agents/). Le script [`api_integration_example.py`](../../examples/logic_agents/api_integration_example.py:0) illustre un cas d'usage typique.

## 4. Utilisation des Données de Test

Un ensemble de données d'exemple est fourni pour vous permettre de tester et d'expérimenter avec le projet sans avoir à créer vos propres données initiales.

*   Vous trouverez ces données dans le répertoire [`examples/test_data/`](../../examples/test_data/). N'hésitez pas à les explorer et à les utiliser avec les différents scripts et notebooks.

## 5. Exécution de Scripts Spécifiques

Le répertoire [`scripts/execution/`](../../scripts/execution/) contient des scripts plus avancés pour des tâches spécifiques, comme l'analyse rhétorique ou des workflows complets.

*   Parcourez ce répertoire pour découvrir des exemples d'utilisation plus complexes et des chaînes de traitement de données.

## 6. Lancement des Tests

Il est crucial de pouvoir vérifier l'intégrité et le bon fonctionnement du code. Plusieurs niveaux de tests sont disponibles.

*   **Scripts de test dédiés :** Le répertoire [`scripts/testing/`](../../scripts/testing/) contient des scripts pour lancer des suites de tests spécifiques ou des simulations.
*   **Tests Unitaires :** Les tests unitaires, qui vérifient des composants isolés du code, sont situés dans [`tests/unit/`](../../tests/unit/). Un exemple typique est [`tests/unit/project_core/utils/test_file_utils.py`](../../tests/unit/project_core/utils/test_file_utils.py:0), qui teste les utilitaires de gestion de fichiers.
*   **Tests d'Intégration :** Les tests d'intégration, qui vérifient l'interaction entre plusieurs composants, se trouvent dans [`tests/integration/`](../../tests/integration/). Vous pouvez consulter [`tests/integration/test_logic_agents_integration.py`](../../tests/integration/test_logic_agents_integration.py:0) pour un exemple d'intégration d'agents logiques, ou le répertoire [`tests/integration/jpype_tweety/`](../../tests/integration/jpype_tweety/) pour les tests spécifiques à l'intégration JPype/Tweety.

## Conclusion

Ce guide vous a présenté les principales façons d'utiliser ce projet et ses ressources. Nous vous encourageons à explorer les différents exemples et scripts fournis pour approfondir votre compréhension. N'hésitez pas à consulter les autres documents et README spécifiques à chaque module pour plus de détails.

Bonne exploration !