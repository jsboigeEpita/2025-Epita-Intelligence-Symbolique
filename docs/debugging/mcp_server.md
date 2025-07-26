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