# Documentation de l'Orchestrateur Web Unifié

## 1. Introduction

L'Orchestrateur Web Unifié (`unified_web_orchestrator.py`) est un outil centralisé conçu pour gérer l'ensemble du cycle de vie de l'application web d'analyse d'argumentation. Il automatise le démarrage, les tests d'intégration, l'arrêt et le nettoyage des services backend (API Flask) et frontend (React), tout en fournissant un tracing détaillé des opérations.

Cet outil remplace une multitude de scripts manuels et offre une interface de ligne de commande unique et robuste pour les développeurs et l'intégration continue.

## 2. Architecture des Composants

L'orchestrateur est bâti sur une architecture modulaire qui s'articule autour des composants suivants :

-   **`UnifiedWebOrchestrator`**: La classe principale qui coordonne toutes les opérations. Elle charge la configuration, initialise les gestionnaires spécialisés et exécute les commandes demandées.
-   **`auto_activate_env`**: Au démarrage, le script tente d'activer l'environnement `conda` "projet-is" pour garantir que toutes les dépendances sont disponibles.
-   **`webapp_config.yml`**: Fichier de configuration central au format YAML qui définit tous les paramètres de l'orchestration (ports, modules, chemins, etc.).
-   **`BackendManager`**: Gère le cycle de vie du backend Flask. Il est responsable du démarrage du serveur avec une logique de *failover* sur les ports, de la vérification de santé (`health check`) et de son arrêt.
-   **`FrontendManager`**: Gère le cycle de vie de l'application React (si activée).
-   **`PlaywrightRunner`**: S'occupe de l'exécution des suites de tests d'intégration Playwright. Il configure les variables d'environnement nécessaires (`BASE_URL`, `BACKEND_URL`) pour que les tests puissent communiquer avec les bons services.
-   **`ProcessCleaner`**: Utilitaire responsable du nettoyage des processus (Python, Node) potentiellement laissés orphelins après une exécution, en se basant sur les ports ou les noms de processus.

## 3. Guide d'Utilisation

L'orchestrateur s'utilise via la ligne de commande depuis la racine du projet.

### Test d'intégration complet (défaut)

C'est le cas d'usage le plus courant. Il démarre tous les services, exécute la suite de tests Playwright, puis arrête proprement tous les services.

```powershell
python -m scripts.webapp.unified_web_orchestrator --integration
```

Pour exécuter les tests avec une interface graphique visible (non *headless*) :

```powershell
python -m scripts.webapp.unified_web_orchestrator --visible
```

### Démarrer les services uniquement

Pour lancer le backend et le frontend et les laisser tourner (utile pour le développement manuel) :

```powershell
python -m scripts.webapp.unified_web_orchestrator --start
```
Les services tourneront jusqu'à ce que vous les arrêtiez manuellement avec `Ctrl+C`.

### Arrêter les services

Si des services tournent en arrière-plan, cette commande les arrêtera proprement.

```powershell
python -m scripts.webapp.unified_web_orchestrator --stop
```

### Lancer les tests sur des services déjà démarrés

Si les services tournent déjà, vous pouvez lancer les tests séparément :

```powershell
python -m scripts.webapp.unified_web_orchestrator --test
```

## 4. Référence des Commandes CLI

| Argument | Alias | Description | Défaut |
| :--- | :--- | :--- |:--- |
| `--config [path]` | | Spécifie le chemin vers le fichier de configuration. | `scripts/webapp/config/webapp_config.yml` |
| `--integration` | | Exécute un test d'intégration complet (start -> test -> stop). C'est l'action par défaut. | `True` |
| `--start` | | Démarre les services et les laisse tourner. | `False` |
| `--stop` | | Arrête les services qui tournent. | `False` |
| `--test` | | Exécute les tests (nécessite que les services soient démarrés). | `False` |
| `--headless` | | Exécute le navigateur en mode *headless* (sans interface graphique). | `True` |
| `--visible` | | Exécute le navigateur en mode visible (invalide `--headless`). | `False` |
| `--frontend` | | Force le démarrage du frontend même s'il est désactivé dans la config. | `False` |
| `--tests [path...]` | | Spécifie des fichiers ou dossiers de test Playwright spécifiques à exécuter. | Tous les tests trouvés |
| `--timeout [min]`| | Définit un timeout global en minutes pour l'ensemble de l'opération. | `10` |

## 5. Troubleshooting

### Problème : Ports déjà utilisés ("Ports occupied")

-   **Symptôme** : Le log affiche `[CLEAN] PORTS OCCUPES` et le démarrage échoue.
-   **Cause** : Des processus d'une exécution précédente n'ont pas été correctement arrêtés.
-   **Solution** :
    1.  L'orchestrateur tente un nettoyage automatique.
    2.  Si cela échoue, utilisez la commande `--stop` pour forcer un nettoyage :
        ```powershell
        python -m scripts.webapp.unified_web_orchestrator --stop
        ```
    3.  En dernier recours, identifiez et terminez les processus `python` ou `node` manuellement.


### Problème : Le backend ne démarre pas ("ECHEC BACKEND")

-   **Symptôme** : Le log affiche une erreur lors du démarrage du backend.
-   **Cause** :
    - Le module Flask spécifié dans `webapp_config.yml` (`argumentation_analysis.services.web_api.app:app`) est incorrect ou contient une erreur de syntaxe.
    - Une dépendance Python est manquante.
    - L'environnement Conda/venv n'est pas correctement activé.
-   **Solution** :
    1.  Vérifiez que l'activation de l'environnement au démarrage du script a fonctionné.
    2.  Lancez le backend manuellement pour voir l'erreur exacte : `python -m argumentation_analysis.services.web_api.app`
    3.  Assurez-vous que toutes les dépendances sont installées (`pip install -r requirements.txt`).

### Problème : Un ou plusieurs endpoints API ne répondent pas ("BACKEND INCOMPLET")

-   **Symptôme** : La validation des services échoue sur un ou plusieurs des 9 endpoints API.
-   **Cause** : Une route spécifique dans l'application Flask est cassée ou non initialisée.
-   **Solution** :
    1. Examinez les logs de l'orchestrateur pour voir quel endpoint échoue.
    2. Vérifiez le code source de l'API Flask dans `argumentation_analysis/services/web_api/app.py` pour vous assurer que la route est correctement définie.