# Guide de Référence pour l'Intégration de l'Écosystème Java

Ce guide a pour but de fournir une référence complète sur l'intégration et la gestion de l'écosystème Java (JVM, JPype, Tweety) au sein de ce projet. Il est basé sur une analyse de l'historique du projet pour capitaliser sur les leçons apprises et fournir des directives claires.

## 1. Résumé de l'État Actuel et Architecture

L'intégration de la JVM via JPype est un composant sensible de notre architecture. L'état actuel est stable, mais cette stabilité a été obtenue après avoir résolu plusieurs problèmes critiques.

L'architecture actuelle repose sur des principes clés pour assurer la résilience :
*   **Gestion centralisée de la JVM** via le module `argumentation_analysis/core/jvm_setup.py`.
*   **Isolation des tests** en utilisant un framework de mock (`tests/mocks/jpype_setup.py`) pour la majorité des cas d'utilisation, limitant les tests d'intégration complets aux scénarios essentiels.
*   **Modularité des solveurs logiques** grâce à un sélecteur (`FOLHandler` refactorisé) permettant de basculer entre `tweety` (basé sur Java) et `prover9` (exécutable externe) via une variable d'environnement.

Les instabilités sont principalement liées aux interactions avec des bibliothèques externes (surtout natives) et des plugins de l'écosystème de test.

## 2. Troubleshooting des Erreurs Courantes

### 2.0. D'abord : votre `access violation` est-il réel ou cosmétique ?

**C'est le premier tri à faire, et il est contre-intuitif.** Le message `Windows fatal exception: access violation` recouvre deux phénomènes distincts, dont un seul est un problème.

| | Cosmétique | Réel |
|---|---|---|
| **Quand** | pendant `jpype.startJVM()`, sur stderr | pendant `jpype.startJVM()`, sur stderr |
| **Ce qui suit** | la JVM démarre, les tests s'exécutent | le processus meurt, aucun test ne tourne |
| **Action** | **aucune — ignorer** | diagnostiquer (§2.1 et suivantes) |

Le cas cosmétique est une exception SEH interceptée par Windows ; JPype la gère et poursuit. Il est documenté deux fois : `KNOWN_ISSUES.md` (« Impact: None — JVM starts successfully despite the warning ») et [`../archives/investigations/JPYPE_WINDOWS_CRASH_FIX.md`](../archives/investigations/JPYPE_WINDOWS_CRASH_FIX.md), qui est explicite : *« un artefact purement cosmétique [...] Il doit être ignoré. Les développeurs ne doivent pas perdre de temps à essayer de "corriger" ce message d'erreur. »*

**Le discriminant n'est pas le message, c'est ce qui se passe après.** Avant d'ouvrir un diagnostic, vérifiez que des tests se sont réellement exécutés — un compte de `passed` non nul suffit. Les sections §3 « Historique » ci-dessous décrivent de **vrais** crashs, tous corrigés ; ne leur attribuez pas un avertissement cosmétique.

### 2.1. Guides dédiés

*   **Crash JVM (Access Violation) au démarrage des tests, session réellement interrompue :** causé par une mauvaise détection des sessions E2E.
    *   **Solution :** [Résolution du Crash JVM dû à la détection E2E](./jpype_e2e_detection_crash.md)

### 2.2. Désactiver entièrement la JVM : `--disable-jvm-session`

Option pytest déclarée dans `tests/conftest.py`. Elle ne se contente pas de sauter l'initialisation : un contrôle précoce (`conftest.py`, avant tout import) détecte le drapeau **dans `sys.argv`** et installe un mock global de `jpype` avant qu'aucun module ne l'importe, puis les fixtures d'intégration ne sont pas chargées du tout.

```bash
pytest tests/unit/ --disable-jvm-session
```

Utile pour isoler un problème (« est-ce la JVM ? ») et pour toute lane qui n'a pas besoin de Java. ⚠️ La contrepartie de la détection par `sys.argv` : l'option agit au niveau du **processus**, pas de la sélection de tests — un test qui exige réellement la JVM sera sauté, pas mis en échec.

⚠️ **Le gate CI n'utilise pas cette option** (`.github/workflows/ci.yml`) : la JVM y démarre pour de bon. `KNOWN_ISSUES.md` la présente comme le contournement CI ; c'est un écart entre la doc et le workflow, pas une consigne à appliquer sans mesurer.

## 3. Historique des Problèmes et Solutions (Archéologie Git)

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

## 4. Bonnes Pratiques et Dépannage

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
5.  **Analysez les Fixtures `pytest`** : en cas de crash des tests d'intégration, vérifiez `tests/conftest.py`. La fixture est `jvm_session` (portée session). ⚠️ **`jvm_fixture` n'existe plus** — elle a été supprimée précisément parce qu'elle était la source des conflits décrits en Phase 4 ; `conftest.py` conserve un commentaire à l'endroit de sa suppression. Un guide antérieur demandait de vérifier sa portée : cette étape est sans objet.

    Depuis la Phase 8, `jvm_session` **ne démarre plus la JVM** : elle agit comme une garde qui lit le résultat de l'initialisation faite en `pytest_sessionstart` et saute les tests si celle-ci a échoué. Un symptôme de type « la JVM n'a pas démarré » ne se diagnostique donc pas dans la fixture mais dans le hook.

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

### Phase 6 : Stabilisation des Tests End-to-End (Début Août 2025)

*   **Problème** : La suite de tests E2E (`pytest -m e2e`) échouait systématiquement avec un timeout de 900 secondes. Le problème n'était pas un test lent, mais l'échec complet du démarrage du serveur backend lors de la phase de setup des tests.
*   **Stratégie de Diagnostic** : Une série d'itérations a permis d'identifier plusieurs couches de problèmes :
    1.  **Crash de la JVM** : Le serveur backend, en démarrant la JVM via JPype, se heurtait au crash `Windows fatal exception: access violation`.
    2.  **Contournement par Mocking (Rejeté)** : Une première tentative a consisté à mocker la JVM pour les tests E2E. Cette approche a été rejetée car elle va à l'encontre du principe d'un test d'intégration, qui doit se rapprocher le plus possible de l'environnement de production.
    3.  **Problèmes de Lancement de Sous-processus** : La cause racine des échecs de démarrage du serveur backend (même après avoir décidé d'ignorer le crash cosmétique de la JVM) était liée à la manière dont le processus était lancé depuis la fixture `pytest`.
*   **Causes Racines (Stack d'erreurs d'importation)** :
    1.  **`ModuleNotFoundError`** : Le sous-processus lancé par `pytest` n'héritait pas du `PYTHONPATH` correct, empêchant `uvicorn` (ou l'application Flask) de trouver les packages du projet comme `services`.
    2.  **`ImportError: attempted relative import with no known parent package`** : Le lancement d'un script Python (`app.py`) directement ne le traite pas comme un module d'un package, ce qui fait échouer les imports relatifs (ex: `from .services import ...`).
    3.  **Dépendance Circulaire** : L'importation de l'objet `app` dans le `__init__.py` du package `services.web_api_from_libs` créait une boucle d'importation qui se manifestait lors du lancement en tant que module.
*   **Solution en Plusieurs Étapes** :
    1.  **Ré-implémentation d'une Fixture Robuste** : La fixture `e2e_servers` dans `tests/conftest.py` a été entièrement réécrite avec un scope de session pour gérer le cycle de vie complet des serveurs backend et frontend.
    2.  **Lancement en tant que Module** : La commande de démarrage du backend a été modifiée pour lancer l'application en tant que module (`python -m services.web_api_from_libs.app`), ce qui est la méthode correcte pour les applications packagées et résout les problèmes d'imports relatifs.
    3.  **Configuration du `PYTHONPATH`** : Le `PYTHONPATH` incluant la racine du projet est explicitement ajouté à l'environnement du sous-processus pour garantir la découverte des packages.
    4.  **Correction de la Dépendance Circulaire** : L'importation `from .app import app` a été commentée dans `services/web_api_from_libs/__init__.py` pour briser la boucle d'importation.
    5.  Ces corrections cumulées ont permis de stabiliser complètement le démarrage des serveurs et de rendre la suite de tests E2E fonctionnelle.

*   **Problème de Deadlock I/O masquant une `TypeError`** :
    *   **Symptôme** : Le serveur backend, bien que ne crashant plus, se bloquait indéfiniment lors de son lancement en sous-processus par la fixture `e2e_servers`.
    *   **Cause Racine** : Un interblocage (deadlock) était provoqué par la redirection des flux `stdout`/`stderr` vers `subprocess.PIPE`. Lors de l'initialisation, la JVM écrit une quantité importante de données sur ces flux. Si les tampons (buffers) de `PIPE` se remplissent avant que le processus parent (`pytest`) ne les lise, le processus enfant (le serveur) se bloque en attente d'écriture.
    *   **Problème Masqué** : Ce deadlock masquait une erreur de démarrage critique. Une fois la redirection des flux modifiée pour écrire dans des fichiers (contournant ainsi le deadlock), une `TypeError` est apparue, causée par un appel incorrect au constructeur de `LogicService` dans `services/web_api_from_libs/app.py`.
    *   **Solution** :
        1.  **Diagnostic du Deadlock** : Redirection temporaire de `stdout`/`stderr` vers des fichiers pour permettre au serveur de démarrer et de révéler l'erreur sous-jacente.
        2.  **Correction de la `TypeError`** : Alignement de l'appel au constructeur de `LogicService` avec sa définition (qui n'attendait aucun argument).
        3.  **Leçon Apprise** : Les interactions I/O avec des sous-processus contenant une JVM sont extrêmement sensibles. La redirection vers `PIPE` doit être gérée avec précaution, par exemple en consommant les flux dans des threads dédiés pour éviter les deadlocks.

### Phase 7 : Deadlock du Serveur avec Initialisation Paresseuse (Début Août 2025)

*   **Problème** : Après avoir corrigé le crash natif `EXCEPTION_ACCESS_VIOLATION` en déplaçant le démarrage de la JVM au tout début du processus, un nouveau problème est apparu : un deadlock complet du serveur. Le processus démarrait mais n'acceptait jamais de requêtes, provoquant un timeout systématique dans les scripts de test.
*   **Stratégie de Diagnostic** :
    1.  **Initialisation Paresseuse** : La première tentative de correction a consisté à déplacer toute la logique d'initialisation (y compris le démarrage de la JVM) dans un hook `@app.before_request` de Flask. L'idée était de démarrer le serveur rapidement et de ne payer le coût de l'initialisation qu'à la toute première requête.
    2.  **Échec et Isolation** : Cette approche a échoué, le deadlock persistait. Un script de test minimaliste (`scripts/debugging/validate_backend_startup.py`) a été créé pour reproduire le problème de manière isolée, en lançant le serveur et en sondant un endpoint `/api/health`.
    3.  **Identification du Serveur Fautif** : Les tests ont révélé que le deadlock ne se produisait que lors de l'utilisation du serveur de développement Flask (`werkzeug`). Lorsque le même code était lancé avec un serveur ASGI de production comme **Uvicorn**, le deadlock disparaissait.
*   **Cause Racine** : Le modèle de rechargement et de gestion des workers du serveur de développement `werkzeug` est incompatible avec le démarrage d'une JVM dans un de ses threads de requête. Le processus se bloque en attendant une ressource qui ne sera jamais libérée.
*   **Solution** :
    1.  **Adoption d'Uvicorn** : Tous les scripts de lancement de tests qui nécessitent une instance réelle du serveur doivent utiliser `uvicorn` pour servir l'application Flask, et non le `app.run()` natif de Flask. Le script `scripts/run_e2e_backend.py` est le point d'entrée de référence pour cela.
    2.  **Conservation de l'Initialisation Paresseuse** : L'architecture d'initialisation dans le hook `@before_request` reste la solution correcte pour s'assurer que les bibliothèques Python (ex: `transformers`) sont chargées avant la JVM, prévenant ainsi le crash natif initial.
*   **Leçon Apprise** : Le serveur de développement Flask/Werkzeug n'est pas adapté aux tests d'intégration qui impliquent des initialisations lourdes et sensibles comme celle d'une JVM. Il faut systématiquement utiliser un serveur plus robuste (Uvicorn, Gunicorn, etc.) pour valider le comportement du serveur dans des conditions proches de la production.

### Phase 8 : Régression Critique après Mise à Jour de Dépendances (Mi-Août 2025)

*   **Problème** : Une régression majeure a réintroduit le crash `Windows fatal exception: access violation` au démarrage de la session `pytest`, faisant échouer la majorité des tests nécessitant la JVM.
*   **Contexte** : Le problème est apparu immédiatement après la fusion de la branche `feature/benchmark-service`, qui a introduit deux changements majeurs simultanément : une mise à jour significative de la bibliothèque `semantic-kernel` (passant de `1.34.0` à `>=1.5.0`) et un refactoring de l'`InformalAnalysisAgent`.
*   **Stratégie de Diagnostic** :
    1.  **Hypothèse 1 (Ordre d'initialisation inversé)** : Une première tentative a consisté à forcer le démarrage de la JVM *avant* l'application de `nest_asyncio`, suspectant un conflit direct. Cette approche a échoué.
    2.  **Hypothèse 2 (Isolation des modules)** : Une seconde tentative a cherché à isoler `torch` et `transformers` en les retirant de `sys.modules` juste avant le démarrage de la JVM. Cet essai a également échoué.
    3.  **Retour à la Documentation** : L'échec des premières hypothèses a conduit à une relecture de ce guide, notamment la "Phase 7". Celle-ci rappelait explicitement que les bibliothèques lourdes comme `transformers` devaient être chargées **avant** la JVM pour éviter ce crash précis.
*   **Cause Racine** : La mise à jour de `semantic-kernel` ou une interaction avec les autres changements a modifié l'ordre de chargement des modules au sein de `pytest`. La JVM se retrouvait initialisée avant que des bibliothèques essentielles (`torch`, `transformers`, et `nest_asyncio`) n'aient eu le temps de configurer leur propre environnement natif, recréant così le conflit `access violation`.
*   **Solution Définitive** :
    1.  **Déplacement de l'Initialisation** : La solution la plus robuste a été de déplacer toute la logique de démarrage de la JVM de la fixture `jvm_session` vers le hook `pytest_sessionstart` dans `tests/conftest.py`.
    2.  **Garantie d'Exécution Précoce** : Le hook `pytest_sessionstart` s'exécute avant même la collecte des tests et le chargement de la plupart des plugins. En y plaçant le démarrage de la JVM, on garantit qu'elle est initialisée avant toute autre bibliothèque native potentiellement conflictuelle (comme `opentelemetry`, `torch`, etc.), résolvant ainsi la cause racine du crash.
    3.  **Nouveau Rôle de la Fixture** : La fixture `jvm_session` a été conservée mais son rôle a été simplifié. Elle agit désormais comme une "garde" : elle ne démarre plus la JVM mais vérifie si l'initialisation dans `pytest_sessionstart` a réussi. Si ce n'est pas le cas, elle saute les tests marqués comme nécessitant la JVM (`pytest.skip`).
*   **Leçon Apprise** : Pour les initialisations critiques et sensibles à l'ordre de chargement comme celle de la JVM, les fixtures `pytest` (même avec `scope="session"`) ne s'exécutent pas assez tôt. Le hook `pytest_sessionstart` est le mécanisme canonique et le plus sûr pour garantir qu'une ressource globale est disponible avant même que l'exécution des tests ne commence réellement.

### Phase 9 : État au 2026-08-20 — ce qui est stable, et les deux écarts doc↔code ouverts

Cette phase ne relate pas un incident : elle enregistre l'état vérifié du code à cette date, pour que le prochain lecteur n'ait pas à le re-dériver. Les deux écarts ci-dessous sont **signalés, pas corrigés** — chacun demande une décision qui ne se prend pas depuis un document.

**Ce qui est en place et conforme à ce guide :**
*   Le démarrage JVM est bien dans `pytest_sessionstart` (Phase 8), et sa docstring le justifie.
*   `jvm_fixture` a disparu ; `jvm_session` est la garde (Phase 4 close).
*   La détection E2E utilise bien `item.get_closest_marker("e2e")` — le correctif de la Mission D3.1.1 n'a pas régressé.
*   Le plugin `opentelemetry` est toujours désenregistré (Phase 3, cause racine 3).

**Écart 1 — la décision E2E est transportée par un aller-retour de cache qui ne peut pas fonctionner.** La valeur est **écrite** dans `pytest_collection_finish` (après la collecte) et **lue** dans `pytest_sessionstart` (avant). Le lecteur obtient donc la valeur du *run précédent*, ou `False` sur cache froid. Ce n'est pas une étourderie : c'est la tentative de réconcilier deux exigences documentées et incompatibles dans le temps — *démarrer avant la collecte* (Phase 8) et *décider d'après les items collectés* (D3.1.1).

⛔ **Ne « corrigez » pas en déplaçant l'initialisation après la collecte** : c'est la régression de la Phase 8, déjà payée une fois avec deux fausses pistes. ⛔ **Ne revenez pas non plus à `"e2e" in item.keywords`** : c'est le faux positif de D3.1.1. La seule sortie qui respecte les deux est de décider depuis l'**argv** (disponible dans `pytest_sessionstart`), en prouvant que ça ne réintroduit pas le faux positif. Suivi : **#1820**.

Corollaire indépendant et corrigeable seul : `-p no:cacheprovider` fait tomber la session en `INTERNALERROR` (`'Config' object has no attribute 'cache'`) avant toute collecte, faute d'accès défensif au cache.

**Écart 2 — `java.library.path` est peuplé, alors que ce guide interdit les bibliothèques natives.** La Phase 3 nomme le chargement d'une `.dll` native aux côtés de la JVM comme *« le conflit le plus significatif »*, et `JPYPE_WINDOWS_CRASH_FIX.md` l'énonce comme troisième interdit. Or `get_jvm_options()` dans `argumentation_analysis/core/jvm_setup.py` ajoute `-Djava.library.path=<native_libs_dir>` pour les solveurs SAT natifs — six lignes après un commentaire qui cite ces mêmes docs pour justifier de garder `-Djava.awt.headless=true` désactivé.

Les deux camps ont du poids : l'interdit vient d'un crash réel et reproduit ; le chemin natif est **load-bearing** et a débloqué 7 sémantiques ADF. Il est possible que l'interdit vise spécifiquement Prover9 (la `.dll` nommée dans la Phase 3) et non les natifs SAT, mais **ce n'est pas établi** — et un guide qui interdit ce que le code fait est un piège pour le prochain diagnostic. À trancher par mesure, pas par lecture. **Ne pas retirer l'option unilatéralement.**
