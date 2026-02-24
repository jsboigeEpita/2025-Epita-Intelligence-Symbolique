# Rapport d'Archéologie Git : Système de Logique du Premier Ordre (FOL)

Ce document retrace l'évolution des composants liés à la logique du premier ordre (FOL) à travers l'historique Git du projet.

## 1. `argumentation_analysis/agents/core/logic/fol_logic_agent.py`

### Création et Évolution

L'analyse de `git log --follow` révèle les points suivants :

*   **Création Initiale :**
    *   **Commit :** [`605958fff243f62ca2a1b27424400b672490793a`](https://github.com/jsboige/epita-2025-module-intelligence-symbolique/commit/605958fff243f62ca2a1b27424400b672490793a)
    *   **Date :** 8 juin 2025
    *   **Contexte :** Le fichier a été créé dans le cadre d'une large opération de consolidation ("MISSION CONSOLIDATION COMPLÈTE"). Il s'agissait dès le départ d'un agent spécialisé pour la logique FOL.

*   **Refactorisation et Découplage de `semantic-kernel` :**
    *   **Commit Clé :** [`ddd7135a94d8bbb8f729542b04b4dacf4b70082e`](https://github.com/jsboige/epita-2025-module-intelligence-symbolique/commit/ddd7135a94d8bbb8f729542b04b4dacf4b70082e) ("PURGE SK AGENTS")
    *   **Date :** 10 juin 2025
    *   **Contexte :** Une série de commits entre le 10 et le 16 juin 2025 visent à supprimer complètement la dépendance à `semantic_kernel.agents` et à son module de compatibilité. L'objectif était de rendre l'agent plus autonome et de s'appuyer sur des définitions locales minimalistes pour l'API de `semantic-kernel`, ce qui a renforcé son rôle et clarifié ses dépendances.

*   **Standardisation et Stabilité :**
    *   **Commit :** [`e48ab5e1d8a6f07aa7e7c659bc8fab101acf5c9f`](https://github.com/jsboige/epita-2025-module-intelligence-symbolique/commit/e48ab5e1d8a6f07aa7e7c659bc8fab101acf5c9f)
    *   **Date :** 23 juin 2025
    *   **Contexte :** Implémentation de classes de base abstraites (ABC) et correction des signatures asynchrones, indiquant un effort de standardisation et de fiabilisation de l'architecture des agents.

### Conclusion sur `fol_logic_agent.py`

Ce fichier est un composant moderne et central du système. Son historique montre une évolution claire vers une plus grande autonomie, un découplage des dépendances lourdes et une meilleure intégration dans une architecture d'agents standardisée.

---

## 2. `argumentation_analysis/agents/core/logic/fol_handler.py`

### De la Spécialisation à l'Abstraction

L'historique de ce fichier est au cœur de l'audit. Il révèle une stratégie d'ingénierie logicielle claire :

*   **Création et Encapsulation (Tweety) :**
    *   **Commit :** [`5cd18c526f280d20181576b7f776c08af6600f1f`](https://github.com/jsboige/epita-2025-module-intelligence-symbolique/commit/5cd18c526f280d20181576b7f776c08af6600f1f)
    *   **Date :** 5 juin 2025
    *   **Contexte :** Le fichier est créé pour gérer spécifiquement les interactions avec la bibliothèque Java Tweety via `jpype`. L'objectif initial était d'isoler la complexité de l'appel à la JVM du reste de la logique de l'agent. De nombreux commits suivent pour stabiliser cette intégration.

*   **Intégration d'un Second Solveur (Prover9) :**
    *   **Commit Clé :** [`afdcba6b3131a42c5aace6f41767e1507c6a64ce`](https://github.com/jsboige/epita-2025-module-intelligence-symbolique/commit/afdcba6b3131a42c5aace6f41767e1507c6a64ce)
    *   **Date :** 18 juillet 2025
    *   **Contexte :** Ce commit marque un tournant. Il mentionne la résolution de problèmes liés à l'intégration de `Prover9` et à la logique multi-sorts. C'est la première preuve de l'intention de supporter plusieurs solveurs. Le `FOLHandler` n'est plus seulement une abstraction pour Tweety, mais devient une façade pour *un* solveur FOL.

*   **Implémentation du Système Configurable :**
    *   **Commit :** [`285f68699f5bbdfbf3794c066530a1b9a409bdcd`](https://github.com/jsboige/epita-2025-module-intelligence-symbolique/commit/285f68699f5bbdfbf3794c066530a1b9a409bdcd)
    *   **Date :** 22 juillet 2025
    *   **Contexte :** Le commit finalise le travail en introduisant explicitement un "configurable solver system". C'est l'aboutissement logique des étapes précédentes, transformant le `FOLHandler` en un dispatcher qui sélectionne le solveur approprié en fonction d'une configuration globale.

### Conclusion sur `fol_handler.py`

Ce fichier illustre parfaitement une montée en abstraction. D'un simple assistant pour Tweety, il est devenu une façade (Design Pattern "Facade") et un dispatcher (Design Pattern "Strategy") pour différents moteurs de logique. Son évolution justifie pleinement son rôle central dans l'architecture actuelle.

---

## 3. `tests/integration/argumentation_analysis/agents/core/logic/test_fol_handler_config.py`

### Validation de la Flexibilité

L'existence et l'historique de ce fichier de test sont aussi importants que les fichiers de code source eux-mêmes pour cet audit.

*   **Création et Objectif :**
    *   **Commit :** [`55f38b27d6573f58ab5555df4ca35c1a5ba34b2c`](https://github.com/jsboige/epita-2025-module-intelligence-symbolique/commit/55f38b27d6573f58ab5555df4ca35c1a5ba34b2c)
    *   **Date :** 22 juillet 2025
    *   **Contexte :** Ce fichier a été créé spécifiquement pour valider le système de solveur configurable. Le message de commit, "test(solver): Refactor integration tests to use parametrization", est clé. Il indique que les tests sont conçus pour s'exécuter sur les différentes configurations de solveurs (Prover9, Tweety), garantissant ainsi que le `FOLHandler` fonctionne correctement quel que soit le choix du solveur. C'est la preuve d'une ingénierie de test rigoureuse.

### Conclusion sur les Tests

La création d'une suite de tests dédiée et paramétrée pour le système de configuration est un indicateur fort de la maturité et de la fiabilité de l'implémentation. Elle garantit la non-régression et la flexibilité de l'architecture.

---

### Annexe 1 : Fichiers de support découverts

L'analyse des commits clés a révélé plusieurs fichiers de support essentiels qui n'avaient pas été identifiés initialement.

#### `argumentation_analysis/core/config.py`

*   **Commit de Création :** `285f6869`
*   **Historique :** Créé et non modifié depuis.

**Analyse :**

Ce fichier est le cœur du système de configuration. Son apparition lors du commit `285f6869` a permis l'implémentation du *Strategy Pattern*.

```python
import enum
from pydantic_settings import BaseSettings, SettingsConfigDict

class SolverChoice(str, enum.Enum):
    TWEETY = "tweety"
    PROVER9 = "prover9"

class ArgAnalysisSettings(BaseSettings):
    solver: SolverChoice = SolverChoice.TWEETY
    model_config = SettingsConfigDict(
        env_prefix='ARG_ANALYSIS_'
    )

settings = ArgAnalysisSettings()
```

L'utilisation de `pydantic-settings` est un choix technique moderne et robuste. Il permet de charger la configuration à partir des variables d'environnement (préfixées par `ARG_ANALYSIS_`), de typer les choix possibles (`SolverChoice`), et de fournir une valeur par défaut sécurisée (`tweety`).

Ce fichier est la pierre angulaire qui a permis au [`FOLHandler`](argumentation_analysis/agents/core/logic/fol_handler.py:1) de devenir un répartiteur (dispatcher) dynamique plutôt qu'un composant codé en dur. C'est une découverte majeure pour l'audit.

#### `docs/design/solver_configuration_v2.md`

*   **Commit de Création :** `285f6869`
*   **Historique :** Créé et non modifié depuis.

**Analyse :**

La découverte de ce document de conception est un tournant dans l'audit. Il ne s'agit pas de code, mais de la **formalisation de l'intention** derrière le refactoring.

Le document prouve que la mise en place du système de configuration était une initiative planifiée, basée sur une analyse de l'architecture existante. Il expose clairement :
1.  **Le Problème :** Une duplication de la logique et une sélection de solveur implicite.
2.  **L'Objectif :** Centraliser la sélection via une variable d'environnement.
3.  **La Solution :** La création de [`config.py`](argumentation_analysis/core/config.py:1) et la refonte du [`FOLHandler`](argumentation_analysis/agents/core/logic/fol_handler.py:1) en tant que *Strategy Dispatcher*.
4.  **La Validation :** Une stratégie de test précise, qui a été implémentée dans les faits.

La présence d'un tel document est un indicateur extrêmement positif de la qualité et de la maturité des pratiques d'ingénierie du projet. Il démontre une approche réfléchie et documentée, ce qui réduit considérablement les risques de maintenance future.

#### `argumentation_analysis/core/setup/manage_portable_tools.py`

*   **Rôle :** Script d'installation et de gestion des outils portables (dépendances externes).
*   **Historique Pertinent :** Créé pour gérer l'environnement de test, il a ensuite été étendu pour intégrer le téléchargement et l'installation de `Prover9`.

**Analyse :**

Ce script est responsable de la mise en place de l'environnement d'exécution. Il s'assure que les dépendances non-python, comme `prover9`, sont téléchargées, décompressées et accessibles.

Quand le système de configuration a été introduit (commit `285f6869`), ce fichier a subi une modification mineure (passage d'un singleton à une instanciation directe du `Prover9Manager`). Cela montre que le manager de Prover9 était suffisamment bien conçu pour ne pas nécessiter de refactoring majeur lors de l'introduction du système de configuration.

Ce fichier est la garantie que, quel que soit le choix de solveur configuré, l'exécutable correspondant sera disponible sur le système, rendant l'architecture portable et facile à déployer.

#### `argumentation_analysis/agents/core/logic/tweety_bridge.py`

*   **Rôle :** Pont (façade) vers l'écosystème Java/Tweety via JPype.
*   **Historique Pertinent :** Ce fichier a une longue histoire de refactoring, indiquant son rôle central. Le commit `285f6869` est un jalon majeur.

**Analyse :**

L'analyse des changements sur ce fichier est la clé de voûte de l'audit. Avant le refactoring, `TweetyBridge` était un "fourre-tout" qui gérait l'initialisation de la JVM et servait de proxy pour *toutes* les logiques, y compris la logique du premier ordre (FOL).

Le commit `285f6869` a effectué un "nettoyage" drastique :
- **Suppression du `fol_handler` :** La responsabilité de gérer la logique FOL a été entièrement retirée de `TweetyBridge`.
- **Suppression des méthodes FOL :** Toutes les méthodes agissant comme un simple proxy vers le `fol_handler` (`fol_query`, `fol_check_consistency`, etc.) ont été supprimées.

Cette modification est un exemple parfait d'application du **Principe de Responsabilité Unique**. `TweetyBridge` n'est plus responsable de *toutes* les logiques, mais uniquement de la gestion du pont JVM et des logiques qui y restent (comme la logique propositionnelle).

La logique FOL est maintenant entièrement contenue et gérée par le [`FOLHandler`](argumentation_analysis/agents/core/logic/fol_handler.py:1), qui est devenu un composant autonome et configurable, capable de choisir sa propre stratégie d'exécution  (`Tweety` ou `Prover9`) sans plus dépendre du `TweetyBridge`.

---

## 4. Analyse de l'Historique Précédent : `first_order_logic_agent.py`

Suite à une investigation plus approfondie demandée par l'utilisateur, une série de commits plus anciens liés au fichier `argumentation_analysis/agents/core/logic/first_order_logic_agent.py` ont été identifiés. Ce fichier semble être l'ancêtre direct des composants `FOLLogicAgent` et `FOLHandler`. L'analyse de ces commits est cruciale pour comprendre l'origine de l'architecture actuelle.

### 4.1 Commit `f4301783` : Nettoyage d'anciens utilitaires d'extraction

- **Date :** 1er Mai 2025
- **Résumé :** `refactor: suppression des fichiers obsolètes suite à refactorisation`

Ce commit marque la suppression d'une série de scripts et notebooks situés dans `argumentation_analysis/utils/extract_repair/`. Bien qu'il ne modifie pas directement les agents logiques, il est historiquement pertinent.

**Fichiers Notables Supprimés :**
- `fix_missing_first_letter.py` : Ce nom suggère fortement l'existence de problèmes précoces liés à l'extraction de texte, où des marqueurs ou des formules pouvaient être corrompus (par exemple, perte de la première lettre).
- `repair_extract_markers.py`, `verify_extracts.py`, `verify_extracts_with_llm.py`: Cet ensemble d'outils indique une phase où la robustesse de l'extraction à partir de sources textuelles était un défi majeur, nécessitant des scripts dédiés à la validation et à la réparation, y compris avec l'aide de LLMs.

**Analyse :**
La suppression de ces fichiers, décrits comme "obsolètes et refactorisés", est un signe de maturation. Elle indique que les logiques de nettoyage et de validation, initialement gérées par des scripts externes, ont probablement été intégrées de manière plus robuste et pérenne au sein des composants applicatifs eux-mêmes. Cela témoigne d'une amélioration de la qualité du code, passant d'une phase exploratoire (avec des scripts de réparation) à une phase de production plus stable.

### 4.2 Commit `eb5c0011` : Fiabilisation de l'Agent et Implémentation du Contrat d'Interface

- **Date :** 6 Juin 2025
- **Résumé :** `fix(agents): Implémente is_consistent et corrige la TypeError`

Ce commit est une étape fondamentale dans l'évolution de l'agent de logique du premier ordre.

**Changements Clés :**
1.  **Respect du Contrat d'Interface :** L'ajout de la méthode `is_consistent` dans `FirstOrderLogicAgent` et `PropositionalLogicAgent` corrige une `TypeError`. Cela démontre que ces agents héritent désormais d'une classe de base abstraite ([`BaseLogicAgent`](argumentation_analysis/agents/core/abc/agent_bases.py:1)) qui définit un contrat commun pour tous les agents logiques. C'est un marqueur fort de la mise en place d'une architecture structurée.

2.  **Implémentation d'une Boucle d'Auto-Correction :** La méthode `text_to_belief_set` est profondément modifiée. Elle passe d'une simple exécution à une **boucle de correction** robuste (avec 3 tentatives). Si la génération du JSON par le LLM ou sa validation ultérieure échoue, l'agent repackage la requête en incluant le message d'erreur et la renvoie au LLM. Cette technique avancée vise à rendre l'agent plus résilient et capable de surmonter de manière autonome les erreurs de génération du LLM.

3.  **Fiabilisation de la Chaîne de Traitement :** Le code met en lumière la complexité de la conversion du langage naturel vers la logique formelle :
    *   LLM -> JSON brut.
    *   Normalisation et validation sémantique du JSON.
    *   Construction d'une base de connaissances textuelle.
    *   Validation syntaxique finale par le moteur logique Tweety.
    La boucle de correction est une réponse directe à la fragilité inhérente de cette chaîne.

**Analyse :**
Ce commit représente plus qu'une simple correction de bug. C'est un jalon dans la fiabilisation de l'agent. Il montre la transition d'un prototype simple à un composant plus intelligent, capable de diagnostiquer et de tenter de corriger ses propres erreurs. L'introduction d'un contrat d'interface (`is_consistent`) est également un signe clair de l'amélioration de la qualité architecturale du projet.

### 4.3 Commit `c7e8c0a4` : Généralisation de l'Auto-Correction à la Génération de Requêtes

- **Date :** 6 Juin 2025
- **Résumé :** `feat(agent): Ajoute une boucle d'auto-correction à la génération de requêtes`

Ce commit étend le principe d'auto-correction, introduit précédemment pour la création de la base de connaissance, à une autre phase critique : la génération de requêtes.

**Changements Clés :**
1.  **Auto-Correction pour `generate_queries` :** La méthode `generate_queries` est refactorisée pour inclure la même boucle de correction (3 tentatives) que `text_to_belief_set`.
2.  **Stratégie de Correction Informée :** Si les requêtes générées par le LLM sont syntaxiquement invalides, l'agent ne les rejette plus silencieusement. Il capture les messages d'erreur de validation pour chaque requête invalide.
3.  **Prompt de Correction Détaillé :** Il construit ensuite un nouveau prompt pour le LLM, qui inclut le texte original, la base de connaissance, et surtout, la liste des requêtes invalides **avec les erreurs spécifiques** à chacune.

**Analyse :**
Ce commit démontre une application systématique et cohérente d'une stratégie d'ingénierie visant à fiabiliser les interactions avec le LLM. Plutôt qu'une simple rustine, le "pattern d'auto-correction" devient un élément central de l'architecture de l'agent. En fournissant un feedback détaillé sur les erreurs, l'agent dialogue plus efficacement avec le LLM, le guidant activement vers la production de sorties conformes. L'agent gagne significativement en autonomie et en robustesse.

### 4.4 Commit `ca841ab9` : Décomposition de la Génération de la KB en Deux Étapes

- **Date :** 6 Juin 2025
- **Résumé :** `refactor(agent): Décompose la génération de la KB en deux étapes`

Ce commit représente une évolution majeure de la stratégie, passant d'une correction réactive à une prévention proactive des erreurs par la décomposition de la tâche.

**Changements Clés :**
1.  **Principe "Diviser pour Régner" :** La méthode monolithique `text_to_belief_set` est abandonnée au profit d'un processus en deux étapes, chacune avec son propre prompt :
    *   **Étape 1 (`TextToFOLDefs`) :** Le LLM est d'abord sollicité pour une tâche simple : identifier les "briques" de la logique, à savoir les `sorts` (types d'objets) et les `predicates` (relations).
    *   **Étape 2 (`TextToFOLFormulas`) :** Un second appel est effectué. Le LLM reçoit le texte original **et** les définitions extraites à l'étape 1. Sa seule tâche est de construire les `formulas` en utilisant exclusivement le vocabulaire autorisé.
2.  **Réduction de la Charge Cognitive :** Cette approche réduit drastiquement la complexité pour le LLM. Au lieu de gérer simultanément la déclaration et l'utilisation des concepts, il se concentre sur une tâche à la fois, ce qui augmente considérablement la probabilité d'obtenir une sortie cohérente et syntaxiquement correcte.
3.  **Refactoring des Prompts :** Deux prompts distincts et plus simples, `PROMPT_TEXT_TO_FOL_DEFS` et `PROMPT_TEXT_TO_FOL_FORMULAS`, remplacent l'ancien prompt monolithique, rendant les instructions plus claires et moins sujettes à erreur.

**Analyse :**
C'est un jalon dans la maturation de l'ingénierie des prompts pour ce projet. Le développeur passe d'une stratégie de "réparation" des erreurs du LLM à une stratégie de "prévention" en simplifiant la tâche demandée. Cette décomposition est une technique d'ingénierie beaucoup plus robuste, qui montre une compréhension fine de la manière de collaborer efficacement avec un LLM en reconnaissant ses limitations (difficulté à maintenir une cohérence sur des tâches complexes) et en capitalisant sur ses forces (excellence sur des tâches bien définies et focalisées).

### 4.5 Commit `a1c9ec81` : Amélioration de l'Observabilité et du Reporting

- **Date :** 6 Juin 2025
- **Résumé :** `feat(agent): Améliore la trace d'exécution et la synthèse finale`

Après avoir stabilisé la logique de l'agent, ce commit se concentre sur l'amélioration de sa transparence et de sa maintenabilité.

**Changements Clés :**
1.  **Logs Détaillés (`DEBUG` level) :** L'agent est instrumenté avec des logs de débogage très précis. Il est maintenant possible de tracer :
    *   Les prédicats exacts avant et après leur correction automatique.
    *   Le prompt complet (avec définitions) envoyé au LLM pour la génération des formules.
    *   Les "idées" de requêtes brutes produites par le LLM.
    *   La raison spécifique du rejet pour chaque idée de requête invalide (prédicat inconnu, arité incorrecte, constante invalide, etc.).
2.  **Sémantique des Logs Affinée :** Des messages qui étaient auparavant des `WARNING` (ex: une idée de requête invalide) sont reclassifiés en `INFO`. Ce changement sémantique est important : il indique que le filtrage des propositions invalides du LLM est maintenant considéré comme une partie normale et attendue du workflow, et non plus comme une anomalie.
3.  **Enrichissement du Rapport Final :** Le script de démonstration (`run_rhetorical_analysis_demo.py`) et le rapport JSON sont mis à jour pour refléter cette nouvelle granularité d'information, fournissant des statistiques plus utiles que de simples "succès/échec".

**Analyse :**
Ce commit illustre une étape classique et essentielle du cycle de vie logiciel : après la fonctionnalité et la robustesse vient **l'observabilité**. En rendant le fonctionnement interne de l'agent entièrement transparent via les logs, le développeur transforme une "boîte noire" fonctionnelle en un composant de production maintenable et débogable. Cela facilite grandement le diagnostic des échecs et l'analyse des performances.

### 4.6 Synthèse de l'Évolution de `first_order_logic_agent.py`

L'historique de ce fichier révèle une trajectoire de maturation logicielle exemplaire :
1.  **Phase Exploratoire :** Les débuts sont marqués par des scripts externes pour nettoyer et valider les données, indiquant une phase d'expérimentation.
2.  **Phase de Fiabilisation :** Le focus se déplace ensuite sur la robustesse de l'agent lui-même, avec l'implémentation de stratégies de dialogue et d'auto-correction avec le LLM.
3.  **Phase de Simplification Architecturale :** Conscient de la complexité de la tâche, le développeur la décompose en sous-problèmes plus simples, une stratégie d'ingénierie de prompt avancée et efficace.
4.  **Phase d'Industrialisation :** Enfin, une fois le composant fonctionnel et robuste, il est instrumenté avec des logs détaillés et des rapports enrichis pour garantir sa maintenabilité et son observabilité.

Au moment du grand refactoring (commit `285f6869`), le [`FirstOrderLogicAgent`](argumentation_analysis/agents/core/logic/first_order_logic_agent.py:1) était donc déjà un composant très mature et sophistiqué. Le refactoring qui a suivi n'a pas été fait sur un simple prototype, mais sur une base solide, ce qui explique la qualité de l'architecture finale.

---

## 5. Conclusion Générale de l'Audit

Cette analyse archéologique approfondie, couvrant à la fois l'évolution de l'ancien `FirstOrderLogicAgent` et le refactoring majeur qui a conduit à l'architecture actuelle, dresse le portrait d'un processus d'ingénierie logicielle rigoureux et itératif.

Les conclusions clés sont les suivantes :

1.  **Maturation Progressive :** Le système de logique du premier ordre n'est pas né d'un seul coup. Il a suivi un cycle de vie complet, passant d'un stade expérimental à un composant robuste, maintenable et observable, avant même d'être refactorisé.
2.  **Ingénierie de Prompt Avancée :** Le projet démontre une maîtrise remarquable des techniques d'interaction avec les LLMs, notamment par la décomposition de tâches complexes ("Diviser pour Régner") et la mise en place de boucles de feedback pour l'auto-correction.
3.  **Décisions Architecturales Solides :** Le refactoring vers une architecture configurable (`FOLHandler`) n'était pas une simple réorganisation. C'était une décision stratégique, justifiée et documentée ([`docs/design/solver_configuration_v2.md`](docs/design/solver_configuration_v2.md:1)), qui s'appuyait sur une base de code déjà très solide. L'application des patrons de conception **Strategy** et **Facade** est claire et bien exécutée.
4.  **Écosystème Robuste :** Le composant logique n'est pas isolé. Il est soutenu par un système de configuration centralisé ([`argumentation_analysis/core/config.py`](argumentation_analysis/core/config.py:1)), des scripts de gestion des dépendances portables ([`argumentation_analysis/core/setup/manage_portable_tools.py`](argumentation_analysis/core/setup/manage_portable_tools.py:1)) et une suite de tests d'intégration complète ([`tests/integration/argumentation_analysis/agents/core/logic/test_fol_handler_config.py`](tests/integration/argumentation_analysis/agents/core/logic/test_fol_handler_config.py:1)).

En conclusion, l'état actuel du système de gestion de la logique du premier ordre est excellent. Il est le résultat d'un travail d'ingénierie réfléchi, qui a su adresser les défis spécifiques de l'intégration des LLMs dans un pipeline logique formel.

## 6. Recommandations Finales

Basé sur cet audit, les recommandations sont les suivantes :

*   **Recommandation 1 : VALIDER PLEINEMENT L'ARCHITECTURE**
    *   **Justification :** L'architecture actuelle est flexible, robuste, bien documentée et testée. Elle représente un atout majeur pour le projet.
    *   **Action :** Approuver formellement l'approche et la considérer comme un standard pour les futurs composants modulaires.

*   **Recommandation 2 : CAPITALISER SUR LES PATRONS EXISTANTS**
    *   **Justification :** Le projet a établi des patrons efficaces pour l'ingénierie de prompt (décomposition, auto-correction) et l'architecture (configurabilité, gestion des dépendances).
    *   **Action :** Pour toute future extension (ex: ajout d'un nouveau solveur, intégration d'un nouvel agent basé sur LLM), suivre scrupuleusement le modèle existant. Créer une checklist interne basée sur les étapes observées (documentation de conception, ajout à la configuration, implémentation de la stratégie, tests d'intégration) pour garantir la cohérence.

*   **Recommandation 3 : FINALISER LA DOCUMENTATION UTILISATEUR**
    *   **Justification :** Le document de conception mentionnait la nécessité de documenter la variable d'environnement `ARG_ANALYSIS_SOLVER` pour les utilisateurs finaux.
    *   **Action :** Vérifier que cette documentation est bien présente et claire dans le `README.md` principal du projet ou un guide de déploiement, afin que les utilisateurs puissent facilement tirer parti de la flexibilité du système.
