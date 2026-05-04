# Rapport de Mise en Œuvre - Utilitaire Shell

## Introduction

Ce document décrit le module utilitaire `shell.py`, conçu pour fournir un ensemble de fonctions robustes et standardisées pour l'exécution de commandes shell au sein du projet. L'objectif principal de ce module est de simplifier les interactions avec le shell en offrant des wrappers pour les exécutions synchrones et asynchrones, tout en intégrant une gestion transparente des environnements virtuels (Conda et venv).

## Fonctions Principales

Voici les fonctions publiques fournies par le module.

### `run_sync`

*   **Objectif :** Exécute une commande shell de manière synchrone, bloquant l'exécution jusqu'à ce que la commande soit terminée. C'est un wrapper autour de `subprocess.run` avec une journalisation et une gestion des erreurs unifiées.
*   **Paramètres :**
    *   `command` (List[str]) : La commande à exécuter, sous forme de liste de chaînes de caractères.
    *   `cwd` (Optional[Union[str, Path]]) : Le répertoire de travail dans lequel exécuter la commande. Par défaut, le répertoire courant.
    *   `capture_output` (bool) : Si `True`, la sortie standard (stdout) et l'erreur standard (stderr) sont capturées. Par défaut, `True`.
    *   `check_errors` (bool) : Si `True`, une exception `ShellCommandError` est levée si la commande retourne un code de sortie non nul. Par défaut, `True`.
    *   `timeout` (Optional[int]) : Le temps maximum en secondes à attendre pour que la commande se termine. Par défaut, 300 secondes.
    *   `env` (Optional[Dict[str, str]]) : Un dictionnaire de variables d'environnement à passer au processus enfant.
*   **Valeur de retour :**
    *   Un objet `subprocess.CompletedProcess` contenant les informations sur le processus terminé, y compris le code de retour, stdout et stderr.
*   **Exemple d'utilisation :**
    ```python
    from project_core.utils.shell import run_sync, ShellCommandError

    try:
        result = run_sync(["echo", "Hello, World!"])
        print(result.stdout)  # Affiche "Hello, World!\n"
    except ShellCommandError as e:
        print(f"Command failed: {e}")
    ```

### `run_async`

*   **Objectif :** Exécute une commande shell de manière asynchrone, sans bloquer l'exécution. C'est un wrapper autour de `asyncio.create_subprocess_exec`.
*   **Paramètres :**
    *   `command` (List[str]) : La commande à exécuter.
    *   `cwd` (Optional[Union[str, Path]]) : Le répertoire de travail.
    *   `env` (Optional[Dict[str, str]]) : Variables d'environnement supplémentaires.
*   **Valeur de retour :**
    *   Un objet `asyncio.subprocess.Process` qui peut être utilisé pour interagir avec le processus en cours d'exécution (par exemple, attendre sa fin, lire sa sortie).
*   **Exemple d'utilisation :**
    ```python
    import asyncio
    from project_core.utils.shell import run_async

    async def main():
        process = await run_async(["sleep", "5"])
        print(f"Process started with PID: {process.pid}")
        await process.wait()
        print("Process finished.")

    asyncio.run(main())
    ```

### `run_in_activated_env`

*   **Objectif :** Exécute une commande synchrone directement dans un environnement Conda ou venv spécifié, sans avoir besoin d'un script d'activation. La fonction identifie l'exécutable Python de l'environnement cible et l'utilise pour lancer la commande.
*   **Paramètres :**
    *   `command` (List[str]) : La commande à exécuter.
    *   `env_name` (str) : Le nom de l'environnement Conda ou venv.
    *   `cwd` (Optional[Union[str, Path]]) : Le répertoire de travail.
    *   `check_errors` (bool) : Lève une exception `ShellCommandError` en cas d'échec. Par défaut, `True`.
    *   `timeout` (Optional[int]) : Timeout en secondes. Par défaut, 600 secondes.
    *   `env` (Optional[Dict[str, str]]) : Variables d'environnement supplémentaires.
*   **Valeur de retour :**
    *   Un objet `subprocess.CompletedProcess`.
*   **Exemple d'utilisation :**
    ```python
    from project_core.utils.shell import run_in_activated_env

    # Exécute `pip list` dans l'environnement nommé 'my_test_env'
    result = run_in_activated_env(["pip", "list"], env_name="my_test_env")
    print(result.stdout)
    ```

### `run_in_activated_env_async`

*   **Objectif :** Exécute une commande de manière asynchrone dans un environnement Conda ou venv spécifié.
*   **Paramètres :**
    *   `command` (List[str]) : La commande à exécuter.
    *   `env_name` (str) : Le nom de l'environnement.
    *   `cwd` (Optional[Union[str, Path]]) : Le répertoire de travail.
    *   `env` (Optional[Dict[str, str]]) : Variables d'environnement supplémentaires.
*   **Valeur de retour :**
    *   Un objet `asyncio.subprocess.Process`.
*   **Exemple d'utilisation :**
    ```python
    import asyncio
    from project_core.utils.shell import run_in_activated_env_async

    async def main():
        process = await run_in_activated_env_async(["python", "-c", "import sys; print(sys.version)"], env_name="my_test_env")
        stdout, stderr = await process.communicate()
        print(stdout.decode())

    asyncio.run(main())
    ```

## Gestion des Erreurs

Pour assurer une gestion cohérente et informative des erreurs, le module définit une exception personnalisée :

*   **`ShellCommandError`**: Cette exception est levée par les fonctions synchrones (`run_sync`, `run_in_activated_env`) lorsque `check_errors` est `True` et que la commande échoue (code de retour non nul). Elle encapsule le message d'erreur, le code de retour, ainsi que les sorties `stdout` et `stderr`, fournissant un contexte complet pour le débogage.
