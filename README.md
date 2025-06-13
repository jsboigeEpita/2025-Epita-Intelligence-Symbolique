# Projet d'Intelligence Symbolique EPITA

**Bienvenue dans l'Architecture d'Analyse d'Argumentation** - Un système unifié pour l'intelligence symbolique et l'orchestration de services web.

---

## 🎓 **Objectif du Projet**

Ce projet a été développé dans le cadre du cours d'Intelligence Symbolique à EPITA. Il sert de plateforme pour explorer des concepts avancés, notamment :
- Les fondements de l'intelligence symbolique et de l'IA explicable.
- Les techniques d'analyse argumentative, de raisonnement logique et de détection de sophismes.
- L'orchestration de systèmes complexes, incluant des services web et des pipelines de traitement.
- L'intégration de technologies modernes comme Python, Flask, React et Playwright.

---

## 🚀 **Point d'Entrée Unifié : L'Orchestrateur Web**

Toute l'application et les tests sont désormais gérés par un **orchestrateur centralisé**, simplifiant grandement le déploiement et la validation.

Le script principal est : [`project_core/webapp_from_scripts/unified_web_orchestrator.py`](project_core/webapp_from_scripts/unified_web_orchestrator.py)

### Commandes Principales

Utilisez les commandes suivantes depuis la racine du projet pour interagir avec l'application :

```bash
# Test d'intégration complet (démarrage, tests, et arrêt automatique)
# C'est la commande recommandée pour une validation complète.
python project_core/webapp_from_scripts/unified_web_orchestrator.py --integration

# Démarrer uniquement les services backend (et frontend si activé)
# L'application restera en cours d'exécution.
python project_core/webapp_from_scripts/unified_web_orchestrator.py --start

# Exécuter les tests sur une application déjà démarrée ou en la démarrant
python project_core/webapp_from_scripts/unified_web_orchestrator.py --test

# Arrêter tous les services liés à l'application
python project_core/webapp_from_scripts/unified_web_orchestrator.py --stop
```

### Options de Configuration

Vous pouvez personnaliser le comportement de l'orchestrateur :
-   `--config <path>`: Spécifie un fichier de configuration YAML (par défaut: `scripts/webapp/config/webapp_config.yml`).
-   `--frontend`: Force le démarrage du frontend React.
-   `--visible`: Exécute les tests Playwright en mode visible (non headless).
-   `--log-level <LEVEL>`: Ajuste le niveau de verbosité (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
-   `--tests <path>`: Permet de spécifier des chemins de tests Playwright particuliers.


---

## 🔧 **Configuration et Prérequis**

### ⚡ **Installation Rapide**

1.  **Cloner le projet**
    ```bash
    git clone <repository-url>
    cd 2025-Epita-Intelligence-Symbolique
    ```

2.  **Configurer l'environnement Python** (avec Conda, recommandé)
    ```bash
    conda create --name projet-is python=3.9
    conda activate projet-is
    pip install -r requirements.txt
    ```

3.  **Tester l'installation**
    Exécutez le test d'intégration pour valider que tout est correctement configuré.
    ```bash
    python project_core/webapp_from_scripts/unified_web_orchestrator.py --integration
    ```

### 📋 **Prérequis Détaillés**

-   **Système Core** :
    -   Python 3.9+
    -   Conda pour la gestion de l'environnement.
    -   Java 8+ (pour les dépendances d'IA Symbolique comme Tweety).
-   **Application Web** (optionnel, si vous activez le frontend) :
    -   Node.js 16+ et npm/yarn.
-   **Variables d'environnement** :
    -   Créez un fichier `.env` à la racine en vous basant sur `.env.example` pour configurer les clés d'API externes si nécessaire.

---

## 📚 **Documentation Technique**

Ce projet est accompagné d'une documentation complète pour vous aider à comprendre son architecture et son fonctionnement.

-   **[Index de la Documentation](docs/README.md)**: Le point de départ pour explorer toute la documentation.
-   **[Architecture du Système](docs/architecture/README.md)**: Descriptions détaillées des composants, des stratégies d'orchestration et des décisions de conception.
-   **[Guides d'Utilisation](docs/guides/README.md)**: Tutoriels pratiques pour utiliser les différentes fonctionnalités du projet.
-   **[Système Sherlock-Watson](docs/sherlock_watson/)**: Documentation spécifique au sous-système d'enquête logique.
