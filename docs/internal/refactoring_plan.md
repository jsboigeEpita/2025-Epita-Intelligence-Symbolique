# Plan de Refactorisation : activate_project_env

L'objectif de cette refactorisation est de remplacer la logique spécifique à PowerShell dans `activate_project_env.ps1` par un script Python multiplateforme. Les scripts shell (`.ps1`, `.sh`) deviendront de simples "wrappers" autour de cette nouvelle logique centralisée.

## 1. Analyse du Script Actuel (`activate_project_env.ps1`)

Le script PowerShell actuel remplit deux fonctions principales :

1.  **Exécution de commande (mode principal)** : Si une commande est passée via le paramètre `-CommandToRun`, le script :
    *   Détermine le nom de l'environnement Conda en lisant le fichier `argumentation_analysis/config/environment_config.py`.
    *   Trouve le chemin de cet environnement Conda en exécutant `conda info --envs`.
    *   Localise les exécutables (`python.exe`, `pytest.exe`, etc.) directement dans le dossier de l'environnement.
    *   Exécute la commande spécifiée en utilisant l'exécutable de l'environnement, après avoir configuré la variable `PYTHONPATH`.

2.  **Mode interactif** : Si aucune commande n'est spécifiée, il active l'environnement Conda dans le shell de l'utilisateur (`conda activate projet-is`).

La logique clé réside dans sa capacité à exécuter une commande dans le bon environnement sans dépendre d'une activation `source` ou `&`, ce qui est une base solide pour une solution multiplateforme.

## 2. Architecture de la Solution Python (`scripts/run_in_env.py`)

Un nouveau script, `scripts/run_in_env.py`, contiendra toute la logique. Il sera appelé par les scripts wrappers.

### Fonctionnalités Clés :

*   **Gestion des arguments** : Le script utilisera le module `argparse` pour recevoir la commande et ses arguments à exécuter.
    ```bash
    # Exemple d'appel
    python scripts/run_in_env.py pytest --version -v
    ```
*   **Détection de l'environnement Conda** :
    *   Le script localisera et lira le fichier `argumentation_analysis/config/environment_config.py` pour extraire le nom de l'environnement Conda. L'utilisation du module `importlib.util` serait une manière robuste de charger la configuration.
    *   Il exécutera `conda info --envs` via `subprocess.run` pour lister tous les environnements et identifier le chemin de celui qui correspond au nom trouvé.
*   **Logique Multiplateforme** :
    *   Le script utilisera `sys.platform` pour déterminer le système d'exploitation.
    *   Les chemins vers les exécutables seront construits dynamiquement en utilisant `pathlib.Path` :
        *   Sur Windows : `CHEMIN_ENV/Scripts/EXECUTABLE.exe`
        *   Sur Linux/macOS : `CHEMIN_ENV/bin/EXECUTABLE`
*   **Configuration de l'environnement d'exécution** :
    *   Avant de lancer la commande, le script ajoutera la racine du projet à la variable d'environnement `PYTHONPATH` via `os.environ`.
*   **Exécution de la commande** :
    *   La commande sera exécutée avec `subprocess.run`, en passant le chemin complet vers l'exécutable de l'environnement.
    *   Le script interceptera le code de sortie de la commande et le retournera comme son propre code de sortie, assurant une intégration transparente avec les chaînes de CI/CD.

### Diagramme de flux (Mermaid)

```mermaid
graph TD
    A[Wrapper Shell: activate_project_env.ps1/.sh] --> B{Commande à exécuter?};
    B -- Oui --> C[Appel de python scripts/run_in_env.py [commande]];
    B -- Non --> D[Activation interactive: conda activate];

    subgraph "scripts/run_in_env.py"
        direction TB
        E[Parse les arguments de la commande] --> F[Lit le nom de l'env Conda depuis environment_config.py];
        F --> G[Exécute "conda info --envs" pour trouver le chemin de l'env];
        G --> H[Détecte l'OS (Win/Linux/Mac)];
        H --> I[Construit le chemin de l'exécutable (ex: CHEMIN_ENV/bin/pytest)];
        I --> J[Prépare l'environnement (ex: PYTHONPATH)];
        J --> K[Exécute la commande via subprocess.run];
        K --> L[Retourne le code de sortie];
    end

    C --> E;
    L --> M[Le wrapper shell retourne le code de sortie];
```

## 3. Exemple de Nouvelle Utilisation

Le script PowerShell sera simplifié pour ne faire que déléguer.

**`activate_project_env.ps1` (simplifié)**
```powershell
param([string]$CommandToRun)

if ($CommandToRun) {
    # La logique est maintenant en Python
    python ./scripts/run_in_env.py $CommandToRun
    exit $LASTEXITCODE
} else {
    # Le mode interactif reste
    conda activate (Get-Content ./argumentation_analysis/config/environment_config.py | ... ) # Nom de l'env
}
```

L'appel pour l'utilisateur resterait identique :
```powershell
# Exécute les tests pytest
powershell -c "& './activate_project_env.ps1' -CommandToRun 'pytest --version'"
```

Cette commande exécuterait le wrapper PowerShell, qui à son tour appellerait le script Python `run_in_env.py` avec les arguments `pytest --version`, exécutant les tests dans le bon environnement Conda de manière totalement transparente.

## 4. Fichiers à Créer ou Modifier

*   **À créer** :
    *   `scripts/run_in_env.py` : Le nouveau script Python central.
    *   `activate_project_env.sh` (optionnel, pour plus tard) : Le wrapper pour les systèmes *nix.
*   **À modifier** :
    *   `activate_project_env.ps1`: Sera simplifié pour appeler le script Python.
    *   Tous les scripts qui appellent `activate_project_env.ps1` n'auront pas besoin de modification si l'interface (le paramètre `-CommandToRun` et les codes de sortie) est préservée, ce qui est l'objectif.