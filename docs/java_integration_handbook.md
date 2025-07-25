# Guide de Référence pour l'Intégration de l'Écosystème Java

Ce guide a pour but de fournir une référence complète sur l'intégration et la gestion de l'écosystème Java (JVM, JPype, Tweety) au sein de ce projet. Il est basé sur une analyse de l'historique du projet pour capitaliser sur les leçons apprises et fournir des directives claires.

## 1. Résumé de l'État Actuel et Architecture

L'intégration de la JVM via JPype est un composant sensible de notre architecture. L'état actuel est stable, mais cette stabilité a été obtenue après avoir résolu plusieurs problèmes critiques.

L'architecture actuelle repose sur des principes clés pour assurer la résilience :
*   **Gestion centralisée de la JVM** via le module `argumentation_analysis/core/jvm_setup.py`.
*   **Isolation des tests** en utilisant un framework de mock (`tests/mocks/jpype_setup.py`) pour la majorité des cas d'utilisation, limitant les tests d'intégration complets aux scénarios essentiels.
*   **Modularité des solveurs logiques** grâce à un sélecteur (`FOLHandler` refactorisé) permettant de basculer entre `tweety` (basé sur Java) et `prover9` (exécutable externe) via une variable d'environnement.

Les instabilités sont principalement liées aux interactions avec des bibliothèques externes (surtout natives) et des plugins de l'écosystème de test.

## 2. Historique des Problèmes et Solutions (Archéologie Git)

Cette section présente une analyse chronologique des problèmes rencontrés et des solutions apportées, qui ont façonné l'intégration actuelle.

### Phase 1 : Conflits de l'Écosystème de Test (Mai - Mi-Juin 2025)

*   **Problème** : Forte instabilité des tests due à des conflits entre `pytest-asyncio` et `pytest-playwright`, provoquant des erreurs `Event loop is closed`.
*   **Solution** : Application de `nest_asyncio` et utilisation d'API synchrones lorsque possible pour contourner le conflit.

### Phase 2 : Tentatives de Centralisation (Fin Juin - Début Juillet 2025)

*   **Problème** : Une première tentative de centralisation de la gestion JVM (`jpype_manager.py`) a introduit une "critical JVM startup error".
*   **Solution** : Suppression de l'approche ratée et standardisation sur `argumentation_analysis/core/jvm_setup.py`, qui est devenu le point de contrôle unique pour la configuration de la JVM.

### Phase 3 : Identification des Causes Racines de Crashs (Mi-Juillet à aujourd'hui)

Cette phase a été cruciale pour stabiliser l'environnement sous Windows.

*   **Problème** : Crash système persistant (`Windows fatal exception: access violation`).
*   **Cause Racine 1** : L'option JVM `-Djava.awt.headless=true` a été identifiée comme une cause directe du crash et a été supprimée.
*   **Cause Racine 2** : Le conflit le plus significatif venait du chargement de la **bibliothèque native Prover9 (`.dll`)** en même temps que la JVM. Sa suppression a été la clé de la stabilisation.
*   **Cause Racine 3** : Le plugin `pytest-opentelemetry` a été identifié comme une nouvelle source de crash de la JVM et a été désactivé.

### Phase 4 : Défaillance du Cycle de Vie de la JVM dans les Tests (Fin Juillet 2025)

*   **Problème** : Malgré les corrections précédentes, la suite de tests `pytest -m "jvm_test"` échoue systématiquement avec un crash `Windows fatal exception: access violation`.
*   **Cause Racine** : Le diagnostic a révélé un problème dans la gestion du cycle de vie de la JVM par les fixtures `pytest` :
    1.  **Conflit de Fixtures** : Certains tests utilisent une fixture `jvm_session` alors que la fixture principale semble être `jvm_fixture`. Cette incohérence cause des erreurs "fixture not found".
    2.  **Redémarrage illégal de la JVM** : La cause première du crash est une tentative de redémarrer la JVM au sein d'une même session de test. Une fixture avec une portée par défaut (`scope="function"`) tente de démarrer la JVM pour chaque test, alors que JPype n'autorise qu'un seul démarrage par processus.

## 3. Bonnes Pratiques et Dépannage

Basé sur les leçons apprises, voici les règles à suivre pour maintenir un environnement stable.

### Bonnes Pratiques

1.  **Gestion des Dépendances** : Toute nouvelle dépendance (Python ou autre) doit être testée rigoureusement pour sa compatibilité avec JPype. Soyez particulièrement méfiant envers les bibliothèques qui chargent des composants natifs (`.dll`, `.so`, `.dylib`).
2.  **Configuration de la JVM** : Ne modifiez pas les options de la JVM dans `jvm_setup.py` sans une compréhension claire de leur impact, en particulier sous Windows. Évitez les options graphiques comme `java.awt.headless`.
3.  **Plugins de Test** : L'écosystème de test `pytest` est une source potentielle de conflits. Avant d'ajouter un nouveau plugin, vérifiez s'il n'interfère pas avec les tests d'intégration Java. En cas de doute, désactivez-le temporairement pour diagnostiquer.
4.  **Isolation** : Privilégiez l'utilisation du framework de mock pour les tests unitaires et fonctionnels. Ne démarrez la JVM que lorsque c'est absolument nécessaire pour les tests d'intégration.

### Guide de Dépannage

Si vous rencontrez un crash de la JVM ou une instabilité, suivez ces étapes :

1.  **Vérifiez le dernier changement** : Le problème est-il apparu après l'ajout d'une bibliothèque ou la modification d'une configuration ? Annulez ce changement pour voir si le problème disparaît.
2.  **Examinez les plugins `pytest`** : Désactivez les plugins non essentiels dans `conftest.py` ou `pytest.ini`, en particulier ceux liés à l'instrumentation (`opentelemetry`) ou à l'asynchronisme.
3.  **Isolez le test** : Créez un test minimal qui reproduit le problème avec le moins de dépendances possible.
4.  **Vérifiez les bibliothèques natives** : Assurez-vous qu'aucune bibliothèque native n'est chargée dans le même processus que la JVM si elle n'est pas explicitement conçue pour cela.
5.  **Analysez les Fixtures `pytest`** : En cas de crash des tests d'intégration, vérifiez le fichier `tests/conftest.py`. Assurez-vous que la fixture gérant la JVM (`jvm_fixture`) a une portée de session (`@pytest.fixture(scope="session")`) et que tous les tests utilisent le nom de fixture correct.

## Archéologie Git : Retracer les décisions de conception

Une analyse approfondie de l'historique Git révèle une lutte récurrente pour stabiliser l'interaction entre la JVM, JPype et l'écosystème de test `pytest`. Les décisions clés ont été prises en réaction à des crashs système critiques (`Windows fatal exception: access violation`).

Voici l'évolution des solutions :

1.  **Centralisation du Cycle de Vie de la JVM** : Face à des crashs initiaux dus à de multiples démarrages/arrêts de la JVM, la communauté a convergé vers une gestion centralisée. La création d'une fixture `pytest` unique avec une portée de session (`@pytest.fixture(scope="session")`) est devenue la norme pour s'assurer que la JVM n'est démarrée qu'une seule fois.
    *   La première introduction d'une fixture de session dédiée apparaît dans le commit `e135c9bf`.
    *   La refactorisation des tests pour utiliser `jvm_session` a été une étape clé (commit `3645d41f`).
    *   Les problèmes de fixtures non trouvées, dus à des conflits entre `conftest.py` locaux et globaux, ont été résolus en centralisant la configuration (commit `ac57b2db`).

2.  **Initialisation "Lazy"** : Pour éviter que la JVM ne démarre prématurément lors de la collecte des tests par `pytest`, une approche d'initialisation "lazy" (paresseuse) a été adoptée dans le commit `93114be8`. Cela a permis de s'assurer que la fixture de session contrôle entièrement le moment du démarrage.

3.  **Identification et Isolation des Conflits Natifs** : L'investigation a montré que la cause la plus profonde des crashs était le conflit entre la JVM et d'autres bibliothèques natives chargées dans le même processus.
    *   La suppression de l'option JVM `-Djava.awt.headless=true` a résolu une première source d'instabilité (commit `7547fadc`).
    *   La découverte et la suppression du chargement de la DLL de **Prover9** en même temps que la JVM a été la correction la plus critique pour la stabilité sous Windows (commit `609749c6`).

4.  **Conflits avec l'Écosystème de Test** : Des plugins `pytest` ont également été identifiés comme des sources d'instabilité.
    *   Le plugin `pytest-opentelemetry` a été désactivé car il provoquait des crashs de la JVM (commit `ef9ffbbb`).

Ce contexte historique montre que la gestion du cycle de vie de la JVM est extrêmement sensible. Le problème actuel décrit dans la "Phase 4" (redémarrage illégal de la JVM) est une régression claire, probablement due à une mauvaise utilisation ou à une mauvaise configuration d'une fixture de test, qui ne respecte plus le principe d'un unique démarrage par processus.

### Phase 5 : Stabilisation Finale et Erreurs Subtiles (Fin Juillet 2025)

*   **Problème** : Malgré les corrections successives, un sous-ensemble de tests marqués `jvm_test` continuait d'échouer avec des erreurs variées (`AttributeError`, `file not found`), empêchant la validation complète de l'intégration JVM.
*   **Stratégie de Diagnostic** : Pour contourner les crashs en cascade qui masquaient les erreurs individuelles, un script `run_isolated_jvm_tests.ps1` a été développé. Ce script exécute chaque test dans un processus `pytest` séparé, permettant de logger la sortie et le code de retour de chaque test, qu'il réussisse, échoue ou crashe.
*   **Cause Racine 1 (Erreur Logique)** : L'analyse des logs isolés a révélé une `AttributeError: can't set attribute 'tweety_bridge'` dans le constructeur de `FOLLogicAgent`. La cause était une propriété en lecture seule (`@property`) définie dans la classe de base `BaseLogicAgent` qui empêchait l'assignation de l'attribut.
*   **Cause Racine 2 (Erreur de Chemin)** : Quatre tests échouaient systématiquement avec le code d'erreur 4 de `pytest` ("file or directory not found"). L'enquête a montré qu'une faute de frappe s'était glissée dans le nom du fichier de test (`authentic_components.py` au lieu de `test_authentic_components.py`).
*   **Solution** :
    1.  Correction de l'assignation dans `FOLLogicAgent` pour utiliser l'attribut interne `_tweety_bridge` au lieu de la propriété publique.
    2.  Correction de la faute de frappe dans les fichiers `tests_jvm.txt` (utilisé par le script d'isolation) pour pointer vers le bon fichier de test.
    3.  Ces corrections, combinées au refactoring précédent qui a introduit l'injection de dépendance pour `TweetyBridge` via une fixture `pytest`, ont permis de rendre la suite de tests `jvm_test` entièrement fonctionnelle.

### Phase 6 : Conflits de Dépendances et Ordre d'Importation (Fin Juillet 2025)

*   **Problème** : Les tests `test_api_startup_and_basic_functionality` et `test_api_endpoints_via_worker` échouaient systématiquement avec un crash silencieux du sous-processus de test.
*   **Stratégie de Diagnostic** : Une journalisation agressive a été ajoutée au script du worker pour tracer chaque étape de l'initialisation.
*   **Cause Racine 1 (Conflits de Dépendances)** : Le fichier `pyproject.toml` ne fixait pas les versions des dépendances clés (`numpy`, `spacy`, `pydantic`), ce qui entraînait l'installation de versions incompatibles.
*   **Cause Racine 2 (Ordre d'Importation)** : Des importations locales de `jpype` et `jvm_setup` dans `api/dependencies.py` provoquaient un chargement dans le désordre, entraînant un conflit fatal avec la JVM.
*   **Solution** :
    1.  Les versions de `numpy`, `spacy`, et `pydantic` ont été fixées dans `pyproject.toml`.
    2.  Les importations de `jpype` et `jvm_setup` ont été déplacées au niveau du module dans `api/dependencies.py` pour garantir un ordre de chargement correct.
    3.  L'API `jpype` a été mise à jour pour utiliser la configuration correcte du cycle de vie de la JVM.

### Phase 7 : Diagnostic et Résolution de l'Erreur d'Initialisation Python (`init_fs_encoding`)

Cette section documente l'analyse et la résolution de l'erreur `Fatal Python error: init_fs_encoding`, un problème critique survenant sous Windows.

> **Résumé (TL;DR)**
> *   **Problème** : L'utilisation de `conda run` à partir de PowerShell sur Windows crée un environnement Python incomplet, causant l'erreur `init_fs_encoding`.
> *   **Symptôme** : Python ne trouve pas ses propres modules internes au démarrage.
> *   **Tentative de Solution Échouée** : Remplacer `conda run` par une activation manuelle de l'environnement dans le script `activate_project_env.ps1` a été testé. Cette approche échoue car l'environnement de test `e2e_test_env` est un environnement partiel (sans `python.exe`) qui dépend du comportement spécifique de `conda run`.

*   **Contexte du Problème**
    Lors de l'exécution de commandes via le script `activate_project_env.ps1`, le processus Python échouait systématiquement avec :
    `Fatal Python error: init_fs_encoding: failed to get the Python codec of the filesystem encoding`
    Cette erreur se produit avant même l'exécution de tout code applicatif, indiquant un problème fondamental d'initialisation.

*   **Analyse de la Cause Racine**
    L'enquête a conclu que le problème n'est **pas une erreur d'encodage**, mais un **échec de localisation des bibliothèques standard de Python**.

    1.  **Cause Principale : `conda run`** : Le mécanisme `conda run` est conçu pour isoler une exécution sans modifier le shell parent. Sous Windows, cette isolation est défaillante et ne configure pas correctement les chemins (`PATH`, `PYTHONPATH`) nécessaires à l'interpréteur Python pour trouver ses propres fichiers essentiels, comme le module `encodings`.
    2.  **Fausse Piste `PYTHONIOENCODING`** : Bien que le script définisse `PYTHONIOENCODING=utf-8`, cette variable est inutile ici. Le problème n'est pas le choix de l'encodage, mais l'incapacité de Python à charger le code qui gère les encodages.
    3.  **Validation Externe** : Ce comportement est un problème connu et documenté dans les communautés `conda` et `Python on Windows`, souvent lié à la manière dont les sous-processus sont créés.

*   **Nouvelle Tentative de Résolution et Échec (Juillet 2025)**
    Une nouvelle tentative de résolution a été effectuée en modifiant le script `activate_project_env.ps1` pour utiliser `conda activate` au lieu de `conda run`. Plusieurs approches ont été testées pour exécuter la commande dans le shell activé (`Invoke-Expression`, `&`, `Invoke-Command`).

    **Toutes ces tentatives ont échoué** avec une erreur `ParameterBindingException`, indiquant une incompatibilité fondamentale entre la manière dont PowerShell gère les commandes et la logique d'activation de Conda dans un script non interactif.

*   **Tentative de forçage de l'encodage (Juillet 2025)**
    *   **Hypothèse** : L'erreur `init_fs_encoding` pourrait être directement liée à un problème d'encodage dans la console PowerShell. Forcer la sortie en UTF-8 avant l'appel à `conda run` pourrait résoudre le problème.
    *   **Modification** : Ajout de `[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8` au début du script `activate_project_env.ps1`.
    *   **Résultat** : **Échec**. L'erreur a changé pour "Commande ou exécutable non trouvé", indiquant que `pytest` n'était plus dans le PATH de l'environnement créé par `conda run`.
    *   **Conclusion** : Cette tentative a confirmé que le problème n'est pas un simple problème d'encodage, mais bien un problème plus profond lié à la manière dont `conda run` construit l'environnement d'exécution, notamment la propagation du `PATH`. La modification a été annulée.

*   **Conclusion et Statut Actuel**
    L'échec de cette nouvelle tentative confirme que le passage à `conda activate` dans le contexte actuel du script est plus complexe qu'anticipé. Le problème `init_fs_encoding` reste donc **non résolu**, et l'utilisation de `conda run` demeure un compromis nécessaire.

    Toute solution future nécessitera une investigation plus approfondie sur l'interaction entre PowerShell et les fonctions de hook de Conda, ou une refonte de la stratégie de gestion des environnements.

### Phase 8 : Résolution de `init_fs_encoding` avec une Nouvelle Architecture d'Exécution (Fin Juillet 2025)

*   **Problème** : L'erreur `Fatal Python error: init_fs_encoding` persistait, bloquant l'exécution des tests sous Windows via `conda run` depuis PowerShell. Toutes les tentatives de correction directe (activation de l'environnement, forçage de l'encodage) avaient échoué.

*   **Solution : Nouvelle Architecture d'Exécution** : Une refonte complète de la stratégie d'exécution a été implémentée, comme décrit dans `docs/internal/new_test_architecture.md`.
    1.  **Création de `scripts/test_executor.py`** : Un nouveau script Python a été créé pour orchestrer l'exécution. Il est responsable de :
        *   Déterminer l'environnement Conda cible (`e2e_test_env`).
        *   Récupérer le chemin racine (préfixe) de cet environnement.
        *   Construire les chemins absolus vers les exécutables `python.exe` et `pytest.exe` de l'environnement.
        *   Récupérer les variables d'environnement complètes de l'environnement cible.
        *   Lancer `pytest` en utilisant `subprocess.run` avec l'environnement et les chemins corrects.
    2.  **Simplification de `activate_project_env.ps1`** : Le script PowerShell a été drastiquement simplifié. Sa seule responsabilité est maintenant d'appeler `python scripts/test_executor.py` en lui passant la commande de test à exécuter.

*   **Résultat** : **Succès**. Cette nouvelle architecture a permis de contourner complètement les problèmes liés à `conda run`.
    *   L'erreur `init_fs_encoding` a été **totalement éliminée**.
    *   La suite de tests `jvm_test` se lance désormais correctement, bien que le crash `Windows fatal exception: access violation` (un problème distinct lié au cycle de vie de la JVM) persiste et doive être traité séparément.
    *   Cette solution est robuste, isole la complexité de la gestion de l'environnement et ne modifie aucun code de production.
### Phase 9 : Tentative de Résolution du Conflit de Bibliothèques Natives (MKL vs. OpenBLAS) - Échec

*   **Problème** : Un crash `Windows fatal exception: access violation` persiste lors de l'utilisation conjointe de PyTorch et NumPy, suspecté d'être un conflit entre les bibliothèques natives MKL et OpenBLAS.
*   **Hypothèse** : Le conflit proviendrait du chargement simultané de deux backends de calcul linéaire différents et incompatibles. PyTorch (via Conda) est lié à la bibliothèque **MKL (Math Kernel Library)** d'Intel, tandis que NumPy pourrait être lié à **OpenBLAS**. Le chargement des deux dans le même processus créerait un conflit de symboles menant au crash.
*   **Tentative de Résolution (Échouée)** :
    1.  **Stratégie** : Forcer toutes les bibliothèques de calcul, en particulier NumPy, à utiliser le même backend que PyTorch (MKL).
    2.  **Modification de `environment.yml`** : Plusieurs modifications ont été apportées pour tenter de forcer l'installation de versions MKL des paquets :
        ```yaml
        # Tentative 1: Ajout du canal Intel
        channels:
          - intel
          - conda-forge
          # ...

        # Tentative 2: Ajout explicite des dépendances MKL
        dependencies:
          - intel-openmp
          - mkl
          - tbb
          - numpy=1.25.0 # En espérant que le canal Intel force la version MKL
        ```
    3.  **Résultat** : **Échec**. Malgré ces modifications et la reconstruction de l'environnement Conda, le crash de la JVM a persisté. L'analyse a montré que `conda` ne parvenait pas à garantir l'installation de la version MKL de NumPy, ou que l'hypothèse de départ était incorrecte.
*   **Conclusion** : La tentative de forcer l'utilisation de MKL pour NumPy n'a pas résolu le crash. Le problème est plus complexe et pourrait ne pas être lié à un simple conflit MKL/OpenBLAS. Les modifications apportées à `environment.yml` ont été annulées pour revenir à une configuration stable connue. Cette investigation infructueuse est documentée ici pour éviter de futures tentatives similaires sans nouvelles informations.