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

---

## 🚀 **DÉMARRAGE ULTRA-RAPIDE (5 minutes)**

Suivez ces étapes pour avoir un environnement fonctionnel et validé en un temps record.

### **1. Installation Complète (2 minutes)**
Le script suivant s'occupe de tout : création de l'environnement, installation des dépendances, etc.

```powershell
# Depuis la racine du projet en PowerShell
./setup_project_env.ps1
```
> **Note:** Si vous n'êtes pas sur Windows, un script `setup_project_env.sh` est également disponible.

### **2. Configuration de l'API OpenRouter (1 minute)**
Pour les fonctionnalités avancées basées sur les LLMs.

```bash
# Créer le fichier .env avec votre clé API
echo "OPENROUTER_API_KEY=sk-or-v1-VOTRE_CLE_ICI" > .env
echo "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1" >> .env
echo "OPENROUTER_MODEL=gpt-4o-mini" >> .env
```
> *Obtenez une clé gratuite sur [OpenRouter.ai](https://openrouter.ai)*

### **3. Activation & Test de Validation (2 minutes)**

```powershell
# Activer l'environnement
./activate_project_env.ps1

# Lancer le test système rapide
python examples/scripts_demonstration/demonstration_epita.py --quick-start
```
> Si ce script s'exécute sans erreur, votre installation est un succès !

---


## 🧭 **Comment Naviguer dans ce Vaste Projet : Les 5 Points d'Entrée Clés**

Ce projet est riche et comporte de nombreuses facettes. Pour vous aider à vous orienter, nous avons défini 5 points d'entrée principaux, chacun ouvrant la porte à un aspect spécifique du système.

| Point d'Entrée             | Idéal Pour                                  | Description Brève                                                                                                | Documentation Détaillée                                                                 |
| :------------------------- | :------------------------------------------ | :--------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------- |
| **1. Démo Pédagogique EPITA** | Étudiants (première découverte)             | Un menu interactif et guidé pour explorer les concepts clés et les fonctionnalités du projet de manière ludique. | [`examples/scripts_demonstration/README.md`](examples/scripts_demonstration/README.md) |
| **2. Démos de Raisonnement Logique** | Passionnés d'IA, logique, multi-agents    | Lancez des scénarios d'investigation complexes (Cluedo, Einstein) avec le système d'agents logiques unifié. | [`examples/Sherlock_Watson/README.md`](examples/Sherlock_Watson/README.md) |
| **3. Analyse Rhétorique**   | Développeurs IA, linguistes computationnels | Accédez au cœur du système d'analyse d'arguments, de détection de sophismes et de raisonnement formel.        | **[Cartographie du Système](docs/mapping/rhetorical_analysis_map.md)** <br> **[Rapports de Test](docs/reports/rhetorical_analysis/)** <br> **[README Technique](argumentation_analysis/README.md)** |
| **4. Application Web**      | Développeurs Web, testeurs UI               | Démarrez et interagir avec l'écosystème de microservices web (API, frontend, outils JTMS).                   | [`docs/mapping/web_apps_map.md`](docs/mapping/web_apps_map.md:0) |
| **5. Suite de Tests**       | Développeurs, Assurance Qualité             | Exécutez les tests unitaires, d'intégration et end-to-end (Pytest & Playwright) pour valider le projet.        | [`tests/README.md`](tests/README.md:0)                                                   |

### **Accès et Commandes Principales par Point d'Entrée :**

#### **1. 🎭 Démo Pédagogique EPITA (Point d'Entrée Recommandé)**
Conçue pour une introduction en douceur, cette démo vous guide à travers les fonctionnalités principales.
*   **Lancement (mode interactif guidé) :**
    ```bash
    python examples/scripts_demonstration/demonstration_epita.py --interactive
    ```
*   Pour plus de détails : **[Consultez le README de la Démo Epita](examples/scripts_demonstration/README.md)**.

#### **2. 🕵️ Démos de Raisonnement Logique (Cluedo, Einstein, etc.)**
Plongez au cœur du raisonnement multi-agents avec des scénarios d'investigation pilotés par le script de production.
*   **Lancement du scénario Cluedo :**
    ```bash
    python examples/Sherlock_Watson/agents_logiques_production.py --scenario examples/Sherlock_Watson/cluedo_scenario.json
    ```
*   **Lancement du scénario du Puzzle d'Einstein :**
    ```bash
    python examples/Sherlock_Watson/agents_logiques_production.py --scenario examples/Sherlock_Watson/einstein_scenario.json
    ```
*   Pour plus de détails : **[Consultez le README des démos logiques](examples/Sherlock_Watson/README.md)**.

#### **3. 🗣️ Analyse Rhétorique Approfondie**
Accédez directement aux capacités d'analyse d'arguments du projet.
*   **Lancement de la démonstration d'analyse rhétorique :**
    ```bash
    python argumentation_analysis/demos/rhetorical_analysis/run_demo.py
    ```
*   Pour comprendre l'architecture : **[Cartographie du Système](docs/mapping/rhetorical_analysis_map.md)**.

#### **4. 🌐 Application et Services Web**
Démarrez l'ensemble des microservices (API backend, frontend React, outils JTMS).
*   **Lancement de l'orchestrateur web :**
    ```powershell
    # Depuis la racine du projet (PowerShell)
    ./start_webapp.ps1
    ```
*   Pour les détails : **[Consultez la cartographie de l'application web](docs/mapping/web_apps_map.md)**

#### **5. 🧪 Suite de Tests Complète**
Validez l'intégrité et le bon fonctionnement du projet avec plus de 400 tests.
*   **Lancer tous les tests Python (Pytest) :**
    ```powershell
    # Depuis la racine du projet (PowerShell)
    ./run_tests.ps1
    ```
*   **Lancer les tests avec des appels LLM réels :**
     ```bash
    python -m pytest tests/unit/argumentation_analysis/test_strategies_real.py -v
    ```
*   Pour les instructions détaillées : **[Consultez le README des Tests](tests/README.md)**

---

## ⚡ **API Usage**

Le "Service Bus" expose un point d'entrée unique pour interagir avec le système d'analyse.

### **Analyser un texte**

-   **Endpoint :** `POST /api/v2/analyze`
-   **Description :** Permet de soumettre un texte pour analyse en spécifiant le plugin à utiliser.
-   **Corps de la requête (JSON) :**
    ```json
    {
      "text": "Le texte à analyser ici.",
      "plugin_name": "TestPlugin"
    }
    ```
-   **Exemple avec cURL :**
    ```bash
    curl -X POST "http://127.0.0.1:8000/api/v2/analyze" \
    -H "Content-Type: application/json" \
    -d '{"text": "L'euthanasie devrait être légalisée car elle respecte l'autonomie du patient.", "plugin_name": "TestPlugin"}'
    ```
-   **Réponse type :**
    ```json
    {
        "status": "executed",
        "received_args": {
            "text": "L'euthanasie devrait être légalisée car elle respecte l'autonomie du patient."
        }
    }
    ```

---

## 🏛️ **Architecture des Services et Principes de Conception**

Pour les développeurs qui souhaitent contribuer, il est essentiel de comprendre les principes d'architecture qui sous-tendent le projet. Notre conception s'articule autour de **Services Fondamentaux** centralisés pour garantir la cohérence, la testabilité et la maintenabilité.

### **`ServiceRegistry` : Le Registre Central des Services**

-   **Rôle :** Le `ServiceRegistry` est un gestionnaire de services qui implémente le patron de conception Singleton. Il garantit qu'une seule instance de chaque service critique (comme un analyseur, un logger, ou un gestionnaire de configuration) existe dans toute l'application.
-   **Avantages :**
    -   **Consistance :** Tous les modules partagent la même instance d'un service.
    -   **Découplage :** Un module n'a pas besoin de savoir comment construire un service, il demande simplement au registre de le lui fournir.
    -   **Fondation pour le futur :** C'est la première brique vers notre objectif de "Guichet de Service Unique".

### **`ConfigManager` : Gestion de Configuration Unifiée**

-   **Rôle :** Le `ConfigManager` centralise le chargement de toutes les configurations du projet (fichiers `YAML`, dataframes, etc.). Il utilise un système de cache et de "lazy loading".
-   **Avantages :**
    -   **Efficacité :** Les configurations ne sont chargées qu'une seule fois et uniquement lorsqu'elles sont nécessaires.
    -   **Centralisation :** Fini la logique de chargement de fichiers dispersée dans le code. Toute la gestion de la configuration passe par ce service.

### **`OrchestrationService` : Le Guichet de Service Unique**

-   **Rôle :** L'`OrchestrationService` est le point d'entrée central pour toutes les requêtes d'analyse. Il implémente le "Guichet de Service Unique" en agissant comme une façade qui masque la complexité interne. Il est responsable de recevoir une requête, de la dispatcher vers le bon plugin ou workflow, et de retourner une réponse standardisée.
-   **Avantages :**
    -   **Interface Simplifiée :** Les clients (applications web, scripts, etc.) interagissent avec une seule interface claire et cohérente.
    -   **Orchestration :** Il gère le cycle de vie des plugins et orchestre leur exécution pour répondre à des requêtes complexes.
    -   **Évolutivité :** Il est conçu pour supporter une architecture de plugins à deux niveaux (Standard et Workflows), permettant au système de s'enrichir de nouvelles capacités de manière modulaire.

Ces composants fondamentaux se trouvent dans `argumentation_analysis/agents/core/` et `argumentation_analysis/agents/tools/support/shared_services.py`. Ils forment la pierre angulaire de notre architecture de services partagés.

### **Exposition via le "Service Bus" API**

Le `OrchestrationService` est exposé à l'extérieur via une API FastAPI qui sert de "Service Bus".

-   **Point d'entrée principal :** `POST /api/v2/analyze`
    -   **Fichier :** [`argumentation_analysis/api/main.py`](argumentation_analysis/api/main.py:0)
    -   **Rôle :** Reçoit les requêtes d'analyse du monde extérieur.
    -   **Logique :** Il valide la requête entrante, récupère l'instance de l'`OrchestrationService` via injection de dépendances, trouve le plugin demandé, **l'exécute** avec le texte fourni et retourne le résultat de l'exécution.

---

## 🛠️ Environnement de Développement : Prérequis et Configuration

Pour contribuer au développement et exécuter les tests, un environnement correctement configuré est essentiel.

### **Prérequis Logiciels**
1.  **Python** (version 3.10 ou supérieure)
2.  **Java Development Kit (JDK)** (version 11 ou supérieure). Indispensable pour notre couche de raisonnement logique basée sur `TweetyProject`.
3.  **Conda** pour la gestion des environnements Python.

### **Configuration de l'Environnement Java**

Le bon fonctionnement des tests d'intégration dépend de la capacité du projet à trouver la JVM.

1.  **Installation du JDK :** Si vous ne l'avez pas, installez un JDK (par exemple, depuis [Adoptium](https://adoptium.net/)).
2.  **Configuration de `JAVA_HOME` :** La manière la plus simple est de laisser le script de préparation s'en charger. Notre script `setup_test_env.ps1` (utilisé par la CI et les scripts de test) tente de localiser automatiquement un JDK.
3.  **Configuration Manuelle (si l'auto-détection échoue) :**
    *   Définissez la variable d'environnement `JAVA_HOME` pour qu'elle pointe vers le répertoire racine de votre installation JDK.
    *   Le `CLASSPATH` est également géré automatiquement par nos scripts, qui parcourent le répertoire `tweety/libs` pour inclure toutes les dépendances Java nécessaires.

## 🆘 **Dépannage Rapide**

| Erreur | Solution Rapide |
| :--- | :--- |
| **API Key manquante ou invalide** | Vérifiez le contenu de votre fichier `.env`. Il doit contenir `OPENROUTER_API_KEY=...` |
| **Java non trouvé (pour TweetyProject)** | Assurez-vous d'avoir un JDK 8+ installé et que la variable d'environnement `JAVA_HOME` est correctement configurée. |
| **Dépendances manquantes** | Relancez `pip install -r requirements.txt --force-reinstall` après avoir activé votre environnement conda. |

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
