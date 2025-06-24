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
| **2. Système Sherlock & Co.** | Passionnés d'IA, logique, multi-agents    | Lancez des investigations complexes (Cluedo, Einstein) avec les agents Sherlock, Watson et Moriarty.             | [`scripts/sherlock_watson/README.md`](scripts/sherlock_watson/README.md)                 |
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

#### **2. 🕵️ Système Sherlock, Watson & Moriarty**
Plongez au cœur du raisonnement multi-agents avec des scénarios d'investigation.
*   **Lancement d'une investigation (exemple Cluedo) :**
    ```bash
    python -m scripts.sherlock_watson.run_cluedo_oracle_enhanced
    ```
*   Pour découvrir les autres workflows : **[Consultez le README du Système Sherlock](scripts/sherlock_watson/README.md)**

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
