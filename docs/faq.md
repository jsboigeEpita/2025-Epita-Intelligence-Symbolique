# Foire Aux Questions (FAQ)

Ce document répond aux questions fréquemment posées sur le projet d'analyse argumentative. Il est organisé par catégories pour faciliter la navigation.

## Table des Matières

- [Foire Aux Questions (FAQ)](#foire-aux-questions-faq)
  - [Table des Matières](#table-des-matières)
  - [Installation](#installation)
    - [Prérequis système](#prérequis-système)
    - [Problèmes d'installation courants](#problèmes-dinstallation-courants)
    - [Environnements virtuels](#environnements-virtuels)
  - [Utilisation](#utilisation)
    - [Démarrage rapide](#démarrage-rapide)
    - [Configuration](#configuration)
    - [Exemples d'utilisation](#exemples-dutilisation)
  - [Architecture](#architecture)
    - [Composants principaux](#composants-principaux)
    - [Flux de données](#flux-de-données)
    - [Extension du système](#extension-du-système)
  - [Dépannage](#dépannage)
    - [Erreurs courantes](#erreurs-courantes)
    - [Problèmes de performance](#problèmes-de-performance)
    - [Compatibilité](#compatibilité)
  - [Contribution](#contribution)
    - [Comment contribuer](#comment-contribuer)
    - [Standards de code](#standards-de-code)
    - [Processus de revue](#processus-de-revue)

## Installation

### Prérequis système

**Q: Quels sont les prérequis système pour installer le projet ?**

R: Le projet nécessite :
- Python 3.9 ou supérieur
- Au moins 4 Go de RAM (8 Go recommandés)
- Environ 500 Mo d'espace disque
- Connexion Internet pour l'installation des dépendances
Pour une aide à la configuration de l'environnement, vous pouvez consulter le script [`setup_project_env.ps1`](setup_project_env.ps1:0).

**Q: Le projet fonctionne-t-il sur tous les systèmes d'exploitation ?**

R: Oui, le projet est compatible avec Windows, macOS et Linux. Cependant, certaines fonctionnalités avancées peuvent nécessiter des configurations spécifiques selon le système d'exploitation. Des guides plus détaillés par plateforme peuvent être disponibles dans le répertoire [`docs/guides/`](docs/guides/).

### Problèmes d'installation courants

**Q: J'obtiens une erreur lors de l'installation des dépendances. Que faire ?**

R: Les erreurs d'installation sont souvent liées à des conflits de dépendances. Essayez les solutions suivantes :
1. Utilisez un environnement virtuel propre
2. Mettez à jour pip : `pip install --upgrade pip`
3. Installez les dépendances une par une pour identifier celle qui pose problème
4. Consultez le fichier [`docs/troubleshooting.md`](docs/troubleshooting.md:0) pour des solutions spécifiques
5. La FAQ dédiée au développement [`docs/projets/sujets/aide/FAQ_DEVELOPPEMENT.md`](docs/projets/sujets/aide/FAQ_DEVELOPPEMENT.md:0) peut également contenir des pistes.

**Q: Comment résoudre les problèmes avec JPype ?**

R: JPype peut être problématique sur certains systèmes. Consultez le guide spécifique dans `scripts/setup/README_INSTALLATION_OUTILS_COMPILATION.md` qui détaille les étapes d'installation pour chaque système d'exploitation.

### Environnements virtuels

**Q: Est-il recommandé d'utiliser un environnement virtuel ?**

R: Oui, fortement recommandé. Utilisez `venv` ou `conda` pour créer un environnement isolé :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix/macOS
venv\Scripts\activate     # Sur Windows
```

**Q: Comment gérer les conflits de dépendances ?**

R: Si vous rencontrez des conflits, essayez d'installer les dépendances dans cet ordre :
1. Dépendances de base : `pip install -r requirements-base.txt`
2. Dépendances spécifiques : `pip install -r requirements-specific.txt`
3. En cas d'échec, utilisez l'option `--no-deps` et installez les dépendances manuellement

## Utilisation

### Démarrage rapide

**Q: Comment démarrer rapidement avec le système ?**

R: Pour une utilisation rapide, suivez ces étapes :
1. Installez le package : `pip install -e .`
2. Exécutez l'analyse sur un exemple : `python scripts/execution/run_analysis.py --file examples/exemple_sophisme.txt`. Pour d'autres exemples de scripts prêts à l'emploi, explorez le répertoire [`examples/scripts_demonstration/`](examples/scripts_demonstration/). Si vous souhaitez utiliser l'interface web, consultez le guide de démarrage rapide : [`docs/projets/sujets/aide/interface-web/DEMARRAGE_RAPIDE.md`](docs/projets/sujets/aide/interface-web/DEMARRAGE_RAPIDE.md:0).
3. Consultez les résultats dans le dossier `results/`

**Q: Comment utiliser l'API web ?**

R: L'API web peut être démarrée avec :
```bash
cd services/web_api
python app.py
```
Ensuite, accédez à `http://localhost:5000/docs` pour la documentation interactive de l'API. Un exemple d'interaction programmatique avec l'API peut être trouvé dans le script de test [`libs/web_api/test_api.py`](libs/web_api/test_api.py:0).

### Configuration

**Q: Comment configurer les modèles de langage utilisés ?**

R: La configuration des modèles se fait dans le fichier `config/llm_config.json`. Vous pouvez spécifier :
- Le fournisseur de modèle (OpenAI, Hugging Face, etc.)
- Les clés API nécessaires
- Les paramètres de génération (température, tokens max, etc.)
Des exemples de configurations pour différents cas d'usage ou tests peuvent se trouver dans [`examples/test_data/config/`](examples/test_data/config/) (si disponible).

**Q: Comment ajuster les seuils de détection des sophismes ?**

R: Les seuils sont configurables dans `config/analysis_config.json`. Vous pouvez ajuster :
- Le seuil de confiance minimum pour signaler un sophisme
- La sensibilité de détection par type de sophisme
- Les paramètres de regroupement des sophismes similaires
Des exemples de configurations pour différents cas d'usage ou tests peuvent se trouver dans [`examples/test_data/config/`](examples/test_data/config/) (si disponible).

### Exemples d'utilisation

**Q: Comment analyser un texte personnalisé ?**

R: Vous pouvez analyser votre propre texte de plusieurs façons :
1. Via l'API : `curl -X POST http://localhost:5000/analyze -d "text=Votre texte ici"`
2. Via le script : `python scripts/execution/run_analysis.py --text "Votre texte ici"`
3. Via l'importation Python :
```python
from argumentation_analysis.core.analysis_runner import run_analysis
result = run_analysis("Votre texte ici")
```

**Q: Comment générer des visualisations des résultats ?**

R: Utilisez le module de visualisation :
```python
from argumentation_analysis.utils.visualizer import ArgumentVisualizer
visualizer = ArgumentVisualizer()
visualizer.create_visualization(analysis_result, output_path="visualization.png")
```

## Architecture

### Composants principaux

**Q: Quels sont les principaux composants du système ?**

R: Le système est composé de plusieurs composants clés :
1. **Agents spécialisés** : Informal, PL, PM et Extract pour différents types d'analyses
2. **Orchestrateur tactique** : Coordonne les agents et consolide les résultats
3. **Services partagés** : LLM, cache, journalisation, etc.
4. **API web** : Interface REST pour l'accès au système
Pour une description plus détaillée de l'architecture et des composants, veuillez consulter le [Guide du Développeur](docs/guides/guide_developpeur.md:0).

**Q: Comment les agents communiquent-ils entre eux ?**

R: Les agents communiquent via l'orchestrateur tactique qui :
1. Distribue les tâches aux agents appropriés
2. Collecte leurs résultats
3. Résout les conflits potentiels
4. Produit un rapport consolidé
Le [Guide du Développeur](docs/guides/guide_developpeur.md:0) et le guide sur [l'Utilisation des Agents Logiques](docs/guides/utilisation_agents_logiques.md:0) fournissent plus de détails sur ces interactions.

### Flux de données

**Q: Quel est le flux de données typique dans le système ?**

R: Le flux de données suit généralement ces étapes :
1. Entrée du texte à analyser
2. Prétraitement du texte
3. Distribution aux agents spécialisés
4. Analyse parallèle par les agents
5. Consolidation des résultats
6. Génération du rapport final
7. Visualisation des résultats
Le [Guide du Développeur](docs/guides/guide_developpeur.md:0) illustre ce flux de manière plus détaillée.

**Q: Comment sont stockés les résultats d'analyse ?**

R: Les résultats sont stockés dans plusieurs formats :
- JSON pour l'interopérabilité
- Markdown pour la lisibilité humaine
- Base de données (optionnel) pour la persistance
- Visualisations graphiques pour la présentation
Vous pouvez trouver des exemples de ces formats de sortie dans le répertoire [`examples/test_data/results/`](examples/test_data/results/) (si disponible) ou générés par les scripts dans [`examples/scripts_demonstration/`](examples/scripts_demonstration/).

### Extension du système

**Q: Comment puis-je ajouter un nouvel agent au système ?**

R: Pour ajouter un nouvel agent :
1. Créez une classe héritant de `BaseAgent` dans `argumentation_analysis/agents/`
2. Implémentez les méthodes requises (`analyze`, `get_capabilities`, etc.)
3. Enregistrez l'agent dans l'orchestrateur tactique
4. Mettez à jour la configuration pour inclure votre agent
Le [Guide du Développeur](docs/guides/guide_developpeur.md:0) contient une section dédiée à l'[Extension des Agents](docs/guides/guide_developpeur.md#extension-des-agents) (ou une section similaire) qui détaille ce processus. Vous pouvez également vous inspirer des agents existants dans le répertoire `argumentation_analysis/agents/`.

**Q: Est-il possible d'utiliser un modèle de langage personnalisé ?**

R: Oui, vous pouvez intégrer votre propre modèle en :
1. Créant un adaptateur dans `argumentation_analysis/core/llm_adapters/`
2. Implémentant l'interface requise
3. Enregistrant votre adaptateur dans le service LLM
4. Configurant le système pour utiliser votre modèle
Consultez la section sur l'[Utilisation de LLMs Personnalisés](docs/guides/guide_developpeur.md#utilisation-de-llms-personnalises) (ou une section similaire) dans le [Guide du Développeur](docs/guides/guide_developpeur.md:0) pour les instructions complètes.

## Dépannage

### Erreurs courantes

**Q: Que faire si j'obtiens une erreur "ModuleNotFoundError" ?**

R: Cette erreur indique un problème d'importation. Vérifiez :
1. Que le package est correctement installé (`pip install -e .`)
2. Que vous êtes dans le bon environnement virtuel
3. Que le PYTHONPATH inclut le répertoire du projet

**Q: Comment résoudre les erreurs de mémoire ?**

R: Si vous rencontrez des erreurs de mémoire :
1. Réduisez la taille des textes analysés
2. Ajustez les paramètres de batch dans la configuration
3. Utilisez l'option `--low-memory` avec les scripts d'analyse
4. Augmentez la RAM disponible si possible
Des configurations optimisées pour la mémoire ou des scripts de test de charge peuvent être trouvés dans [`examples/test_data/config/`](examples/test_data/config/) ou [`scripts/testing/`](scripts/testing/).

### Problèmes de performance

**Q: Le système est lent. Comment l'optimiser ?**

R: Pour améliorer les performances :
1. Activez le cache LLM dans la configuration
2. Utilisez des modèles plus légers pour les analyses préliminaires
3. Parallélisez les analyses avec l'option `--parallel`
4. Réduisez la verbosité des logs avec `--log-level WARNING`
Des scripts de benchmark pour évaluer et comparer les performances se trouvent dans [`scripts/testing/benchmarks/`](scripts/testing/benchmarks/) (si disponible).

**Q: Comment réduire les coûts d'API pour les modèles externes ?**

R: Pour réduire les coûts :
1. Activez le cache pour éviter les requêtes redondantes
2. Utilisez des modèles locaux quand c'est possible
3. Ajustez les paramètres de tokenisation pour optimiser les requêtes
4. Implémentez une stratégie de batching pour les requêtes
Des exemples de configuration du cache LLM sont disponibles dans [`examples/test_data/config/`](examples/test_data/config/) (si disponible).

### Compatibilité

**Q: Le système est-il compatible avec Python 3.8 ?**

R: Le système est officiellement supporté sur Python 3.9+. Pour Python 3.8 :
1. Consultez le guide `docs/compatibility.md`
2. Installez les dépendances spécifiques avec `pip install -r requirements-py38.txt`
3. Certaines fonctionnalités avancées pourraient ne pas être disponibles

**Q: Comment résoudre les problèmes de compatibilité avec les bibliothèques externes ?**

R: En cas de problèmes de compatibilité :
1. Vérifiez les versions exactes dans `requirements.txt`
2. Utilisez l'option `--no-deps` lors de l'installation de packages problématiques
3. Consultez le fichier `scripts/setup/README_PYTHON312_COMPATIBILITY.md` pour les problèmes spécifiques à Python 3.12

## Contribution

### Comment contribuer

**Q: Comment puis-je contribuer au projet ?**

R: Vous pouvez contribuer de plusieurs façons :
1. Corriger des bugs et soumettre des pull requests
2. Ajouter de nouveaux exemples (scripts, notebooks, données de test) dans les sous-répertoires de [`examples/`](examples/) tels que [`examples/logic_agents/`](examples/logic_agents/), [`examples/scripts_demonstration/`](examples/scripts_demonstration/), [`examples/notebooks/`](examples/notebooks/) ou [`examples/test_data/`](examples/test_data/).
3. Améliorer la documentation
4. Proposer de nouvelles fonctionnalités via les issues GitHub

**Q: Existe-t-il des guidelines pour les contributions ?**

R: Oui, consultez le fichier `CONTRIBUTING.md` qui détaille :
- Le processus de fork et pull request
- Les conventions de nommage
- Les standards de code
- Le processus de revue

### Standards de code

**Q: Quels sont les standards de code à respecter ?**

R: Le projet suit ces standards :
- PEP 8 pour le style de code Python
- Docstrings au format Google
- Tests unitaires pour toutes les nouvelles fonctionnalités
- Couverture de code minimale de 80%

**Q: Comment exécuter les tests avant de soumettre une contribution ?**

R: Exécutez la suite de tests complète :
```bash
pytest tests/
```
Et vérifiez la couverture de code :
```bash
pytest --cov=argumentation_analysis tests/
```

### Processus de revue

**Q: Comment se déroule le processus de revue des contributions ?**

R: Le processus de revue comprend :
1. Vérification automatique par CI/CD (tests, linting)
2. Revue par au moins un mainteneur du projet
3. Validation des modifications
4. Merge dans la branche principale

**Q: Combien de temps faut-il pour qu'une contribution soit acceptée ?**

R: Le temps de revue dépend de la complexité de la contribution :
- Corrections mineures : généralement 1-3 jours
- Nouvelles fonctionnalités : 1-2 semaines
- Changements majeurs : peuvent nécessiter plusieurs itérations de revue

---

*Cette FAQ est régulièrement mise à jour. Si vous ne trouvez pas réponse à votre question, n'hésitez pas à ouvrir une issue sur le dépôt GitHub du projet.*

*Dernière mise à jour : 27/05/2025*