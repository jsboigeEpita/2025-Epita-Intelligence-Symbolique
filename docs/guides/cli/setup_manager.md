# Guide d'Utilisation : `setup_manager.py`

Ce script est le point d'entrée principal pour toutes les opérations de configuration et de validation de l'environnement de développement.

## Commandes Disponibles

### `install-project`

C'est la commande principale pour un nouvel utilisateur. Elle orchestre une installation complète et propre du projet. Elle exécute en séquence les actions cruciales suivantes :
1.  **Validation des outils de compilation** : S'assure que l'environnement système est prêt.
2.  **Installation des dépendances** : Installe toutes les dépendances Python depuis le fichier `requirements.txt`.
3.  **Configuration du PYTHONPATH** : Crée un fichier `.pth` pour garantir que le projet est visible par Python.

**Utilisation :**
```bash
# Lance l'installation complète du projet
python scripts/setup_manager.py install-project
```

Vous pouvez également spécifier un fichier `requirements.txt` différent :
```bash
python scripts/setup_manager.py install-project --requirements path/to/your/requirements.txt
```
### `setup-test-env`

Cette commande prépare et valide l'environnement spécifiquement pour l'exécution de la suite de tests du projet. Son rôle principal est d'abstraire la complexité de la configuration des mocks, notamment pour JPype, qui peut poser des problèmes de compatibilité.

Elle garantit que les tests peuvent s'exécuter de manière fiable, que ce soit avec la bibliothèque `JPype` authentique (pour les versions de Python compatibles) ou avec son mock (pour Python 3.12+).

**Utilisation :**
```bash
# Configure l'environnement pour les tests
python scripts/setup_manager.py setup-test-env
```


### `fix-deps`

Répare les dépendances Python du projet.

**Utilisation :**

- **Réparer des paquets spécifiques :**
  ```bash
  python scripts/setup_manager.py fix-deps --package numpy pandas
  ```

- **Installer depuis un fichier `requirements.txt` :**
  ```bash
  python scripts/setup_manager.py fix-deps --from-requirements path/to/requirements.txt
  ```

- **Installer les dépendances d'un sous-projet :**
 Certains modules du projet, comme `abs_arg_dung`, ont leurs propres dépendances. Vous pouvez les installer de la manière suivante :

 ```bash
 python scripts/setup_manager.py fix-deps --from-requirements abs_arg_dung/requirements.txt
 ```
- **Stratégies de Réparation :**
  Par défaut, `fix-deps` réinstalle simplement un paquet. Pour les cas difficiles (par exemple, avec `JPype1`), une stratégie "agressive" peut être utilisée.

  ```bash
  # Utiliser la stratégie agressive pour installer un paquet récalcitrant
  python scripts/setup_manager.py fix-deps --package JPype1 --strategy aggressive
  ```

  Cette stratégie tentera une séquence de méthodes d'installation (standard, sans binaire, etc.) jusqu'à ce que l'une d'entre elles réussisse.

  En dernier recours, si les méthodes `pip` traditionnelles échouent, la stratégie agressive essaiera d'installer une version pré-compilée du paquet (un "wheel" `.whl`) depuis le répertoire `ressources/private/wheels`. Cela est particulièrement utile pour les paquets qui nécessitent une compilation complexe sur Windows.


### `set-path`

Configure le `PYTHONPATH` pour le projet en cours en créant un fichier `.pth` dans le répertoire `site-packages` de l'environnement. C'est une méthode de secours robuste si l'installation en mode éditable (`pip install -e .`) échoue.

**Utilisation :**
```bash
python scripts/setup_manager.py set-path
```

### `validate`

Valide des composants spécifiques de l'environnement pour s'assurer qu'ils sont correctement configurés.

**Utilisation :**
```bash
python scripts/setup_manager.py validate --component <nom_du_composant>
```

**Composants disponibles :**

- `build-tools`:
  Vérifie la présence des outils de compilation Visual Studio sur Windows, nécessaires pour compiler certaines dépendances Python (comme `JPype`). Si la validation échoue, elle vous guidera sur la marche à suivre.

  ```bash
  python scripts/setup_manager.py validate --component build-tools
  ```

- `jvm-bridge`:
  Vérifie que la librairie `jpype` est installée, ce qui est essentiel pour la communication entre Python et la JVM.

  ```bash
  python scripts/setup_manager.py validate --component jvm-bridge
  ```
