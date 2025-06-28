# 03. Démo EPITA - Architecture

## 1. Objectif de la Démonstration

L'objectif principal de la "Démo EPITA" est de simuler une session d'apprentissage avancée et interactive destinée aux étudiants d'EPITA. Elle met en scène un scénario pédagogique réaliste centré sur l'analyse d'arguments complexes et la détection de sophismes logiques, dans le contexte de l'intelligence artificielle appliquée à la médecine.

La démonstration se distingue par son utilisation de **vrais modèles de langage (LLM)**, notamment `gpt-4o-mini`, pour fournir une analyse et un feedback authentiques, dépassant ainsi les simulations basées sur des mocks.

## 2. Commande d'Exécution

Pour lancer la démonstration, exécutez la commande suivante depuis la racine du projet :

```bash
python scripts/demo/validation_point3_demo_epita_dynamique.py
```

Ce script est le point d'entrée principal car il représente la version la plus complète et la plus fidèle de la démo, intégrant tous les composants authentiques.

## 3. Architecture et Composants

L'architecture de la démo s'articule autour des composants clés suivants :

-   **`scripts/demo/validation_point3_demo_epita_dynamique.py`**: Il s'agit du script principal qui orchestre l'ensemble de la démonstration. Il initialise les composants, configure la session et exécute les différents scénarios pédagogiques.

-   **`OrchestrateurPedagogiqueEpita`**: Cette classe est le véritable chef d'orchestre de la session d'apprentissage. Elle est responsable de la création des profils d'étudiants, du déroulement du débat et de l'adaptation du niveau de complexité.

-   **`ProfesseurVirtuelLLM`**: Cet agent intelligent joue le rôle du professeur. Sa principale fonction est d'interagir avec un service LLM externe pour analyser en profondeur les arguments soumis par les étudiants simulés, détecter les sophismes et générer un feedback pédagogique personnalisé.

-   **Service LLM (`gpt-4o-mini`)**: Cœur de l'analyse "intelligente", ce service externe est appelé pour fournir une analyse authentique des arguments, ce qui confère à la démo son caractère réaliste et avancé.

## 4. Données et Configuration

Le bon fonctionnement de la démonstration dépend des éléments de configuration et des répertoires suivants :

-   **Configuration Unifiée** :
    -   [`config/unified_config.py`](config/unified_config.py:1) : Ce fichier est essentiel pour configurer le comportement du système, notamment pour s'assurer que de **vrais LLM** sont utilisés (`MockLevel.NONE`) et non des simulations.

-   **Répertoires de Sortie** :
    -   `logs/` : Ce répertoire est utilisé pour stocker les logs détaillés de l'exécution de la session, y compris les traces complètes des interactions avec le LLM.
    -   `reports/` : Des rapports de synthèse et de validation au format Markdown sont générés dans ce répertoire, fournissant un résumé clair des résultats de la session.

## 5. Statut de Validation et Lancement

La phase de test de la démo est terminée. La version actuelle est considérée comme **stable** et prête à l'emploi.

Un nettoyage du code a été effectué, au cours duquel plusieurs scripts et composants obsolètes ont été supprimés pour clarifier la base de code.

Pour garantir un lancement correct et reproductible, utilisez la commande PowerShell suivante, qui active l'environnement virtuel du projet avant d'exécuter le script de démonstration :

```powershell
powershell -c "& c:/dev/2025-Epita-Intelligence-Symbolique/activate_project_env.ps1 -CommandToRun 'python c:/dev/2025-Epita-Intelligence-Symbolique/scripts/demo/validation_point3_demo_epita_dynamique.py'"