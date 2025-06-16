# 🏆 Projet d'Intelligence Symbolique EPITA
## Une Exploration Approfondie de l'Analyse d'Argumentation et des Systèmes Multi-Agents

---

## 🎓 **Bienvenue aux Étudiants d'EPITA !**

Ce projet est bien plus qu'une simple collection de scripts ; c'est une **plateforme d'apprentissage interactive** conçue spécifiquement pour vous, futurs ingénieurs en intelligence artificielle. Notre objectif est de vous immerger dans les concepts fondamentaux et les applications pratiques de l'IA symbolique. Ici, vous ne trouverez pas seulement du code, mais des opportunités d'explorer, d'expérimenter, de construire et, surtout, d'apprendre.

### 🎯 **Vos Objectifs Pédagogiques avec ce Projet :**
*   🧠 **Comprendre en Profondeur :** Assimiler les fondements de l'IA symbolique, du raisonnement logique et de l'IA explicable.
*   🗣️ **Maîtriser l'Argumentation :** Développer une expertise dans les techniques d'analyse argumentative, la détection de sophismes et la construction d'arguments solides.
*   🤖 **Explorer l'Orchestration d'Agents :** Découvrir la puissance des systèmes multi-agents et leur intégration avec des modèles de langage (LLM) pour des tâches complexes.
*   🛠️ **Intégrer les Technologies Modernes :** Acquérir une expérience pratique avec Python, Java (via JPype), les API web (Flask/FastAPI), et les interfaces utilisateur (React).
*   🏗️ **Développer des Compétences en Ingénierie Logicielle :** Vous familiariser avec les bonnes pratiques en matière d'architecture logicielle, de tests automatisés et de gestion de projet.

### 💡 **Votre Aventure Commence Ici : Sujets de Projets Étudiants**

Pour vous guider et stimuler votre créativité, nous avons compilé une liste détaillée de sujets de projets, accompagnée d'exemples concrets et de guides d'intégration. Ces ressources sont conçues pour être le tremplin de votre contribution et de votre apprentissage.

*   📖 **[Explorez les Sujets de Projets Détaillés et les Guides d'Intégration](docs/projets/README.md)** (Ce lien pointe vers le README du répertoire des projets étudiants, qui contient lui-même des liens vers `sujets_projets_detailles.md` et `ACCOMPAGNEMENT_ETUDIANTS.md`)

---

## 🎓 **Objectif du Projet**

Ce projet a été développé dans le cadre du cours d'Intelligence Symbolique à EPITA. Il sert de plateforme pour explorer des concepts avancés, notamment :
- Les fondements de l'intelligence symbolique et de l'IA explicable.
- Les techniques d'analyse argumentative, de raisonnement logique et de détection de sophismes.
- L'orchestration de systèmes complexes, incluant des services web et des pipelines de traitement.
- L'intégration de technologies modernes comme Python, Flask, React et Playwright.

---

## 🧭 **Comment Naviguer dans ce Vaste Projet : Les 5 Points d'Entrée Clés**

Ce projet est riche et comporte de nombreuses facettes. Pour vous aider à vous orienter, nous avons défini 5 points d'entrée principaux, chacun ouvrant la porte à un aspect spécifique du système.

| Point d'Entrée             | Idéal Pour                                  | Description Brève                                                                                                | Documentation Détaillée                                                                 |
| :------------------------- | :------------------------------------------ | :--------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------- |
| **1. Démo Pédagogique EPITA** | Étudiants (première découverte)             | Un menu interactif et guidé pour explorer les concepts clés et les fonctionnalités du projet de manière ludique. | [`examples/scripts_demonstration/README.md`](examples/scripts_demonstration/README.md:0) |
| **2. Système Sherlock & Co.** | Passionnés d'IA, logique, multi-agents    | Lancez des investigations complexes (Cluedo, Einstein) avec les agents Sherlock, Watson et Moriarty.             | [`scripts/sherlock_watson/README.md`](scripts/sherlock_watson/README.md:0)                 |
| **3. Analyse Rhétorique**   | Développeurs IA, linguistes computationnels | Accédez au cœur du système d'analyse d'arguments, de détection de sophismes et de raisonnement formel.        | [`argumentation_analysis/README.md`](argumentation_analysis/README.md:0)                 |
| **4. Application Web**      | Développeurs Web, testeurs UI               | Démarrez et interagir avec l'écosystème de microservices web (API, frontend, outils JTMS).                   | [`project_core/webapp_from_scripts/README.md`](project_core/webapp_from_scripts/README.md:0) |
| **5. Suite de Tests**       | Développeurs, Assurance Qualité             | Exécutez les tests unitaires, d'intégration et end-to-end (Pytest & Playwright) pour valider le projet.        | [`tests/README.md`](tests/README.md:0)                                                   |

### **Accès et Commandes Principales par Point d'Entrée :**

#### **1. 🎭 Démo Pédagogique EPITA**
Conçue pour une introduction en douceur, cette démo vous guide à travers les fonctionnalités principales.
*   **Lancement recommandé (mode interactif guidé) :**
    ```bash
    python examples/scripts_demonstration/demonstration_epita.py --interactive
    ```
*   Pour plus de détails et d'autres modes de lancement : **[Consultez le README de la Démo Epita](examples/scripts_demonstration/README.md)**

#### **2. 🕵️ Système Sherlock, Watson & Moriarty**
Plongez au cœur du raisonnement multi-agents avec des scénarios d'investigation.
*   **Lancement d'une investigation (exemple Cluedo) :**
    ```bash
    python -m scripts.sherlock_watson.run_unified_investigation --workflow cluedo
    ```
*   Pour découvrir les autres workflows (Einstein, JTMS) et les options : **[Consultez le README du Système Sherlock](scripts/sherlock_watson/README.md)**

#### **3. 🗣️ Analyse Rhétorique Approfondie**
Accédez directement aux capacités d'analyse d'arguments du projet.
*   **Exemple de lancement d'une analyse via un script Python (voir le README pour le code complet) :**
    Ce point d'entrée est plus avancé et implique généralement d'appeler les pipelines et agents directement depuis votre propre code Python.
*   Pour comprendre l'architecture et voir des exemples d'utilisation : **[Consultez le README de l'Analyse Rhétorique](argumentation_analysis/README.md)**

#### **4. 🌐 Application et Services Web**
Démarrez l'ensemble des microservices (API backend, frontend React, outils JTMS).
*   **Lancement de l'orchestrateur web (backend + frontend optionnel) :**
    ```bash
    # Lance le backend et, si spécifié, le frontend
    python project_core/webapp_from_scripts/unified_web_orchestrator.py --start [--frontend]
    ```
*   Pour les détails sur la configuration, les différents services et les tests Playwright : **[Consultez le README de l'Application Web](project_core/webapp_from_scripts/README.md)**

#### **5. 🧪 Suite de Tests Complète**
Validez l'intégrité et le bon fonctionnement du projet.
*   **Lancer tous les tests Python (Pytest) via le script wrapper :**
    ```powershell
    # Depuis la racine du projet (PowerShell)
    .\run_tests.ps1
    ```
*   **Lancer les tests Playwright (nécessite de démarrer l'application web au préalable) :**
    ```bash
    # Après avoir démarré l'application web (voir point 4)
    npm test 
    ```
*   Pour les instructions détaillées sur les différents types de tests et configurations : **[Consultez le README des Tests](tests/README.md)**

---

## 🛠️ **Installation Générale du Projet**

Suivez ces étapes pour mettre en place votre environnement de développement.

1.  **Clonez le Dépôt :**
    ```bash
    git clone <URL_DU_DEPOT_GIT>
    cd 2025-Epita-Intelligence-Symbolique-4 
    ```

2.  **Configurez l'Environnement Conda :**
    Nous utilisons Conda pour gérer les dépendances Python et assurer un environnement stable.
    ```bash
    # Créez l'environnement nommé 'projet-is' à partir du fichier fourni
    conda env create -f environment.yml 
    # Activez l'environnement
    conda activate projet-is
    ```
    Si `environment.yml` n'est pas disponible ou à jour, vous pouvez créer un environnement manuellement :
    ```bash
    conda create --name projet-is python=3.9
    conda activate projet-is
    pip install -r requirements.txt
    ```

3.  **Dépendances Node.js (pour l'interface web et les tests Playwright) :**
    ```bash
    npm install
    ```

4.  **Configuration des Clés d'API (Optionnel mais Recommandé) :**
    Certaines fonctionnalités, notamment celles impliquant des interactions avec des modèles de langage (LLM), nécessitent des clés d'API. Pour ce faire, créez un fichier `.env` à la racine du projet en vous inspirant de [`config/.env.example`](config/.env.example:0).

    *   **Cas 1 : Utilisation d'une clé OpenAI standard**
        Si vous utilisez une clé API directement depuis OpenAI, seule cette variable est nécessaire. La plupart des clés étudiantes fonctionnent ainsi.
        ```
        OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
        ```

    *   **Cas 2 : Utilisation d'un service compatible (OpenRouter, LLM local, etc.)**
        Si vous utilisez un service tiers comme OpenRouter ou un modèle hébergé localement, vous devez fournir **à la fois** l'URL de base du service **et** la clé d'API correspondante.
        ```
        # Exemple pour OpenRouter
        BASE_URL=https://openrouter.ai/api/v1
        API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
        ```
    *Note : Le projet est conçu pour être flexible. Si aucune clé n'est fournie, les fonctionnalités dépendantes des LLM externes pourraient être limitées ou utiliser des simulations (mocks), selon la configuration des composants.*

---

## 📚 **Documentation Technique Approfondie**

Pour ceux qui souhaitent aller au-delà de ces points d'entrée et comprendre les détails fins de l'architecture, des composants et des décisions de conception, la documentation complète du projet est votre meilleure ressource.

*   **[Explorez l'Index Principal de la Documentation Technique](docs/README.md)**

---

## ✨ **Aperçu des Technologies Utilisées**

Ce projet est une mosaïque de technologies modernes et de concepts d'IA éprouvés :

| Domaine                     | Technologies Clés                                       |
| :-------------------------- | :------------------------------------------------------ |
| **Langages Principaux**     | Python, JavaScript, Java (via JPype)                    |
| **IA & LLM**                | Semantic Kernel, OpenRouter/OpenAI API, TweetyProject   |
| **Développement Web**       | Flask, FastAPI, React, WebSockets                       |
| **Tests**                   | Pytest, Playwright                                      |
| **Gestion d'Environnement** | Conda, NPM                                              |
| **Analyse Argumentative**   | Outils et agents personnalisés pour la logique et les sophismes |

---

**🏆 Projet d'Intelligence Symbolique EPITA 2025 - Prêt pour votre exploration et contribution ! 🚀**
