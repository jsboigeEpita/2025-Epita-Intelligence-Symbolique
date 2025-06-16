# Guide d'Utilisation du Projet

## Introduction

Bienvenue dans le guide d'utilisation du système d'analyse argumentative. Ce document a pour objectif de vous aider à comprendre comment soumettre un texte pour analyse, interpréter les résultats, et explorer les fonctionnalités plus avancées ainsi que les exemples de code fournis.

## 1. Configuration de l'Environnement

Avant toute chose, assurez-vous d'avoir correctement configuré votre environnement de développement. Des scripts sont fournis pour faciliter cette étape :

*   Pour un environnement PowerShell : exécutez le script [`setup_project_env.ps1`](../../setup_project_env.ps1:0).
*   Pour un environnement Bash (Linux/macOS) : exécutez le script [`setup_project_env.sh`](../../setup_project_env.sh:0).

Ces scripts installeront les dépendances nécessaires et configureront les variables d'environnement.

## 2. Utilisation du Service d'Analyse Argumentative via l'API

Le moyen principal d'interagir avec le système pour analyser un texte est d'utiliser son API Web. Cette section décrit comment soumettre un texte et interpréter les résultats. Pour une documentation exhaustive de l'API, veuillez consulter le document [`docs/composants/api_web.md`](../composants/api_web.md:1).

### Soumettre un Texte pour Analyse Complète

L'analyse argumentative complète d'un texte s'effectue via l'endpoint `/api/analyze`.

*   **Objectif :** Effectuer une analyse argumentative complète d'un texte fourni, incluant potentiellement la détection de sophismes, l'analyse structurelle et l'évaluation de la cohérence.
*   **Méthode HTTP :** `POST`
*   **URL :** `/api/analyze` (l'URL de base, par exemple `http://localhost:5000`, dépend de votre configuration de déploiement)

#### Requête

Le corps de la requête doit être au format JSON et contenir le texte à analyser ainsi que des options d'analyse optionnelles.

```json
{
  "text": "Le texte argumentatif à analyser ici. Par exemple : Les énergies renouvelables sont la clé pour lutter contre le changement climatique car elles ne produisent pas de gaz à effet de serre.",
  "options": {
    "detect_fallacies": true,
    "analyze_structure": true,
    "evaluate_coherence": true,
    "include_context": true,
    "severity_threshold": 0.5
  }
}
```

*   `text` (string, requis) : Le texte que vous souhaitez analyser.
*   `options` (object, optionnel) : Un objet contenant divers booléens et valeurs pour personnaliser l'analyse. Les options disponibles incluent :
    *   `detect_fallacies` (boolean) : Activer ou désactiver la détection de sophismes.
    *   `analyze_structure` (boolean) : Activer ou désactiver l'analyse de la structure argumentative.
    *   `evaluate_coherence` (boolean) : Activer ou désactiver l'évaluation de la cohérence.
    *   `include_context` (boolean) : Inclure plus de contexte pour les éléments détectés.
    *   `severity_threshold` (float) : Seuil de sévérité pour la détection (par exemple, pour les sophismes).
    Pour une liste complète et détaillée des options, référez-vous à la section sur l'endpoint `/api/analyze` dans la [documentation de l'API Web](../composants/api_web.md:58).

#### Exemple avec `curl`

Voici comment vous pouvez appeler cet endpoint en utilisant l'outil en ligne de commande `curl` (en supposant que le service tourne sur `http://localhost:5000`) :

```bash
curl -X POST -H "Content-Type: application/json" -d '{
  "text": "Les chats sont meilleurs que les chiens car ils sont plus indépendants. De plus, ils ronronnent, ce qui est apaisant.",
  "options": {
    "detect_fallacies": true,
    "analyze_structure": false
  }
}' http://localhost:5000/api/analyze
```

#### Réponse

En cas de succès (code HTTP `200 OK`), l'API retournera un objet JSON contenant les résultats de l'analyse. Voici une structure d'exemple simplifiée :

```json
{
  "original_text": "Le texte soumis...",
  "analysis_summary": {
    "overall_sentiment": "positif", // ou négatif, neutre
    "key_claims": [
      "Affirmation clé 1 extraite du texte.",
      "Affirmation clé 2 extraite du texte."
    ],
    // ... autres éléments de résumé
  },
  "fallacies": [
    {
      "fallacy_type": "Nom du sophisme (ex: Ad Hominem)",
      "explanation": "Explication du sophisme.",
      "severity": 0.7, // Score de sévérité
      "context": "Extrait du texte où le sophisme a été détecté."
    }
    // ... autres sophismes détectés
  ],
  "structure": {
    // Détails de la structure argumentative si analyze_structure était true
    "arguments": [ /* ... */ ],
    "relations": [ /* ... */ ]
  },
  "coherence": {
    // Score et évaluation de la cohérence si evaluate_coherence était true
    "score": 0.85,
    "assessment": "L'argumentation présente une bonne cohérence."
  }
  // ... autres sections de l'analyse
}
```

*   `original_text` : Le texte que vous avez soumis.
*   `analysis_summary` : Un résumé de l'analyse, incluant potentiellement le sentiment général, les affirmations clés, etc.
*   `fallacies` : Une liste des sophismes détectés, chacun avec son type, une explication, sa sévérité et le contexte.
*   `structure` : Si l'option `analyze_structure` était activée, cette section contiendra les détails de la structure argumentative (composants, relations).
*   `coherence` : Si l'option `evaluate_coherence` était activée, cette section contiendra l'évaluation de la cohérence du texte.

#### Gestion des Erreurs

Si une erreur survient (par exemple, une requête malformée ou une erreur interne du serveur), l'API retournera un code de statut HTTP approprié (comme `400 Bad Request` ou `500 Internal Server Error`) et un corps de réponse JSON décrivant l'erreur :

```json
{
  "error": "Type d'erreur concis",
  "message": "Description détaillée de l'erreur.",
  "status_code": 400 // ou 500
}
```

## 3. Exemples d'Utilisation Basiques pour Développeurs

Si vous êtes un développeur souhaitant comprendre les composants internes du système ou contribuer au projet, plusieurs exemples sont à votre disposition.

*   **Scripts de démonstration :** Le répertoire [`examples/scripts_demonstration/`](../../examples/scripts_demonstration/) contient des scripts Python simples illustrant des interactions spécifiques. Par exemple, le script [`demo_tweety_interaction_simple.py`](../../examples/scripts_demonstration/demo_tweety_interaction_simple.py:0) montre une utilisation basique de la librairie Tweety.
*   **Notebooks Jupyter :** Pour une approche plus interactive et didactique, consultez les notebooks disponibles dans [`examples/notebooks/`](../../examples/notebooks/). Le notebook [`api_logic_tutorial.ipynb`](../../examples/notebooks/api_logic_tutorial.ipynb:0) constitue un excellent point de départ pour comprendre l'utilisation de l'API logique.

## 4. Intégration d'API et Agents Logiques (pour Développeurs)

Le projet explore l'intégration avec des API externes et l'utilisation d'agents logiques.

*   Des exemples concrets d'intégration d'API et de mise en œuvre d'agents logiques se trouvent dans le répertoire [`examples/logic_agents/`](../../examples/logic_agents/). Le script [`api_integration_example.py`](../../examples/logic_agents/api_integration_example.py:0) illustre un cas d'usage typique.

## 5. Utilisation des Données de Test (pour Développeurs)

Un ensemble de données d'exemple est fourni pour vous permettre de tester et d'expérimenter avec le projet sans avoir à créer vos propres données initiales.

*   Vous trouverez ces données dans le répertoire [`examples/test_data/`](../../examples/test_data/). N'hésitez pas à les explorer et à les utiliser avec les différents scripts et notebooks.

## 6. Exécution de Scripts Spécifiques (pour Développeurs)

Le répertoire [`scripts/execution/`](../../scripts/execution/) contient des scripts plus avancés pour des tâches spécifiques, comme l'analyse rhétorique ou des workflows complets.

*   Parcourez ce répertoire pour découvrir des exemples d'utilisation plus complexes et des chaînes de traitement de données.

## 7. Lancement des Tests (pour Développeurs)

Il est crucial de pouvoir vérifier l'intégrité et le bon fonctionnement du code. Plusieurs niveaux de tests sont disponibles.

*   **Scripts de test dédiés :** Le répertoire [`scripts/testing/`](../../scripts/testing/) contient des scripts pour lancer des suites de tests spécifiques ou des simulations.
*   **Tests Unitaires :** Les tests unitaires, qui vérifient des composants isolés du code, sont situés dans [`tests/unit/`](../../tests/unit/). Un exemple typique est [`tests/unit/project_core/utils/test_file_utils.py`](../../tests/unit/project_core/utils/test_file_utils.py:0), qui teste les utilitaires de gestion de fichiers.
*   **Tests d'Intégration :** Les tests d'intégration, qui vérifient l'interaction entre plusieurs composants, se trouvent dans [`tests/integration/`](../../tests/integration/). Vous pouvez consulter [`tests/integration/test_logic_agents_integration.py`](../tests/integration/test_logic_agents_integration.py:0) pour un exemple d'intégration d'agents logiques, ou le répertoire [`tests/integration/jpype_tweety/`](../../tests/integration/jpype_tweety/) pour les tests spécifiques à l'intégration JPype/Tweety.

## Conclusion

Ce guide vous a présenté comment utiliser le service d'analyse argumentative via son API, ainsi que les principales façons d'explorer les ressources du projet pour les développeurs. Pour une utilisation directe du service d'analyse, référez-vous à la section sur l'API (Section 2). Pour approfondir votre compréhension des mécanismes internes ou développer des fonctionnalités, les exemples et scripts décrits dans les sections suivantes restent à votre disposition.

N'hésitez pas à consulter la documentation complète de l'API ([`docs/composants/api_web.md`](../composants/api_web.md:1)) et les README spécifiques à chaque module pour plus de détails.

Bonne exploration !



