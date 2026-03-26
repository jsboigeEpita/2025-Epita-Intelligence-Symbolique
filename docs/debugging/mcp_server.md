# Débogage du Serveur MCP

Ce document détaille les étapes de débogage pour les problèmes liés au serveur MCP.

## Analyse du blocage du serveur principal

### Contexte

Le serveur MCP principal (`services/mcp_server/main.py`) se bloquait silencieusement au démarrage. Le script de diagnostic `diagnose_mcp_connection.py` restait bloqué sans erreur.

### Étapes de débogage

1.  **Amélioration du script de diagnostic** : Le script a été modifié pour inclure un timeout global de 15 secondes. Cela a permis de transformer le blocage silencieux en une erreur de timeout explicite.

2.  **Isoler le problème par la méthode "diviser pour régner"** :
    *   Les services (`AnalysisService`, `ValidationService`, etc.) dans `services/mcp_server/main.py` ont été commentés un par un. Le blocage persistait.
    *   L'initialisation de `AppServices` a été commentée. Le blocage persistait.
    *   L'initialisation de `initialize_project_environment` a été commentée. Le blocage persistait.
    *   Cela a indiqué que le problème se situait au niveau des imports, avant même l'exécution de la logique principale.

3.  **Analyse des imports dans `argumentation_analysis/core/bootstrap.py`** :
    *   Chaque import de service ou de composant complexe a été commenté un par un. Le blocage persistait à chaque étape.
    *   Cela a suggéré que le problème n'était pas lié à un seul module, mais à une condition d'environnement plus fondamentale.

4.  **Exécution directe du serveur** :
    *   L'exécution de `python services/mcp_server/main.py` a finalement révélé la véritable erreur, qui était masquée par l'exécution en sous-processus :
        ```
        RuntimeError: ERREUR CRITIQUE : L'ENVIRONNEMENT 'projet-is' N'EST PAS CORRECTEMENT ACTIVÉ.
        ```

### Cause racine identifiée

Le blocage n'était pas un blocage silencieux, mais un `RuntimeError` explicite causé par le script `argumentation_analysis/core/from_scripts/auto_env.py`. Ce script vérifie si l'environnement Conda `projet-is` est actif et arrête l'exécution si ce n'est pas le cas.

Le script de diagnostic, en lançant `python -m services.mcp_server.main`, n'activait pas l'environnement Conda requis, ce qui provoquait le crash immédiat du sous-processus serveur.

### Solution (partielle)

Le script de diagnostic a été modifié pour utiliser le wrapper `activate_project_env.ps1`, qui est la méthode préconisée pour lancer des commandes dans l'environnement de projet correctement configuré.

```python
# Dans scripts/tools/debugging/diagnose_mcp_connection.py
server_params = StdioServerParameters(
    command="powershell.exe",
    args=["-File", ".\\activate_project_env.ps1", "-CommandToRun", f"python -u -m {module_path}"],
    env=env
)
```

### Tentative de correction supplémentaire

Suite aux retours, le script de diagnostic a été modifié pour importer et utiliser directement les fonctions de `scripts/test_executor.py` pour activer l'environnement Conda.

```python
# Dans scripts/tools/debugging/diagnose_mcp_connection.py
conda_env_name = get_conda_env_name()
env = get_conda_env_vars(conda_env_name)
env_prefix = get_conda_env_prefix(conda_env_name)
python_executable = os.path.join(env_prefix, "python.exe")

server_params = StdioServerParameters(
    command=python_executable,
    args=["-u", "-m", module_path],
    env=env
)
```

### Problème résiduel

Même avec cette correction, le serveur ne démarre toujours pas via le script de diagnostic, échouant avec une `ProcessLookupError`. Cela suggère qu'il pourrait y avoir un problème plus profond dans la manière dont l'environnement est activé ou dont le processus est géré par `mcp.client.stdio`. Cependant, la cause *initiale* du blocage a été identifiée.
## Analyse du blocage du serveur principal (Post-Merge)

### Contexte
Après une fusion de branches, le serveur MCP principal (`services/mcp_server/main.py`) a commencé à se bloquer silencieusement au démarrage. Le script de diagnostic `diagnose_mcp_connection.py` restait bloqué sans retourner d'erreur, indiquant un problème profond lors de l'initialisation.

### Étapes de débogage

La cause du blocage a été identifiée en utilisant une approche systématique de "diviser pour régner" :

1.  **Isolation des services applicatifs** : Les services dans la classe `AppServices` de `main.py` (`LogicService`, `AnalysisService`, etc.) ont été commentés un par un. Le blocage persistait jusqu'à ce que l'initialisation de `ValidationService` soit activée, ce qui a immédiatement provoqué le retour du blocage. Cela a permis d'isoler le problème à l'initialisation de `ValidationService` ou l'une de ses dépendances.

2.  **Analyse des dépendances de `ValidationService`** : Le constructeur de `ValidationService` est simple, mais il importe `LogicService`. Une hypothèse de dépendance circulaire a été explorée mais s'est avérée incorrecte.

3.  **Analyse de la pile d'initialisation** : Le problème a été tracé plus haut, dans le script `argumentation_analysis/core/bootstrap.py`, qui est responsable de l'initialisation de l'environnement global du projet, y compris la JVM.

4.  **Identification de la cause racine** : En commentant sélectivement des parties du processus d'initialisation de la JVM dans `argumentation_analysis/core/jvm_setup.py`, la ligne exacte causant le blocage a été identifiée.

### Cause du blocage

Le blocage silencieux est causé par l'appel suivant :

-   **Fichier** : `argumentation_analysis/core/jvm_setup.py`
-   **Ligne** : 390
-   **Code** : `jpype.startJVM(...)`

Cette ligne est responsable du démarrage de la machine virtuelle Java. Un problème dans la configuration (comme un classpath incorrect, des options JVM invalides, ou un conflit de version de Java) peut amener cet appel à se bloquer indéfiniment sans lever d'exception, ce qui explique le blocage silencieux du serveur.

## Solution : Démarrage Robuste et Asynchrone de la JVM

Pour corriger ce point de défaillance unique, le mécanisme de démarrage de la JVM a été entièrement revu pour être asynchrone, non-bloquant et robuste.

### Mécanisme d'implémentation

1.  **Appel non-bloquant** : L'appel bloquant `jpype.startJVM` est maintenant exécuté dans un thread séparé en utilisant `asyncio.to_thread`. Cela empêche l'appel de bloquer la boucle d'événements principale du serveur.

2.  **Timeout Strict** : L'appel est enveloppé dans un `asyncio.wait_for` avec un timeout de 30 secondes. Si le démarrage de la JVM prend plus de temps, l'attente est annulée.

3.  **Exception Personnalisée** : En cas de timeout, une exception personnalisée `JVMStartupTimeoutError` est levée. Cette exception est explicite et permet d'identifier immédiatement la source du problème.

4.  **Propagation des Erreurs** : La pile d'appels, depuis `jvm_setup.py` jusqu'au `lifespan` du serveur MCP dans `services/mcp_server/main.py`, a été rendue `async`. Cela garantit que toute exception, y compris `JVMStartupTimeoutError`, se propage correctement et provoque un échec de démarrage propre du serveur, avec des logs clairs, au lieu d'un blocage silencieux.

### Comment diagnostiquer les problèmes de timeout de la JVM

Si le serveur ne démarre pas et que les logs indiquent une `JVMStartupTimeoutError`, cela signifie que la JVM n'a pas pu démarrer en moins de 30 secondes. Les causes possibles sont :

*   **Problèmes de performance** : Le système est surchargé et le démarrage de la JVM est ralenti.
*   **Conflits de dépendances** : Un problème avec les JARs dans le classpath.
*   **Configuration Java** : Un `JAVA_HOME` incorrect ou une version de Java incompatible.
*   **Problèmes réseau** : Si le démarrage dépend de ressources réseau qui ne sont pas disponibles.

Pour déboguer, examinez les logs juste avant le message de timeout pour des indices sur la cause du ralentissement.