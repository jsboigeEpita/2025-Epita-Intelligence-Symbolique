# Rapport de Mission : Densification du Plan pour `AgentLoader`

**Date:** 2025-07-26
**Auteur:** Architect-Mode
**Mission:** SDDD Étape 3 - Plan `AgentLoader`

---

## 1. Rapport d'Activité

### 1.1 Résumé du Grounding Sémantique

L'analyse de la documentation existante a permis d'établir que l'`AgentLoader` est un composant stratégique, symétrique au `PluginLoader`. Son rôle est de découpler la **personnalité** d'un agent (sa configuration, son prompt système) de sa **logique applicative**. 

Le chargeur doit :
1.  Localiser un répertoire de "personnalité" d'agent via un nom et une version.
2.  Lire un fichier `config.json` pour obtenir les méta-informations (nom de la classe Python, etc.).
3.  Lire le prompt système depuis un fichier `system.md`.
4.  Importer dynamiquement la classe de l'agent en utilisant `importlib`.
5.  Instancier l'agent en lui injectant son prompt système.

Cette approche garantit une modularité et une testabilité maximales, permettant de faire évoluer le comportement des agents sans toucher au code de l'orchestration.

### 1.2 Diff des Modifications Appliquées

Le `diff` suivant a été appliqué au fichier [`docs/refactoring/informal_fallacy_system/04_operational_plan.md`](../04_operational_plan.md).

```diff
--- a/docs/refactoring/informal_fallacy_system/04_operational_plan.md
+++ b/docs/refactoring/informal_fallacy_system/04_operational_plan.md
@@ -136,16 +136,41 @@
              *   `[ ] Doc : Mettre à jour `docs/architecture/README.md` pour expliquer en détail le mécanisme de découverte : le rôle de `pathlib`, la magie de `importlib`, et le processus de validation via l'héritage `BasePlugin`.`
              *   `[ ] Commit : Rédiger un message de commit atomique et descriptif pour l'ensemble des fonctionnalités du `PluginLoader` (ex: `feat(core): implement robust dynamic plugin loader with discovery, validation, and tests`).`
  
-    *   **Composant 3 : Chargeur d'Agents (`agent_loader.py`)**
-        *   `[ ] Tâche : Créer le fichier src/agents/agent_loader.py.`
-        *   `[ ] Tâche : Implémenter la classe squelette AgentLoader avec une méthode vide load.`
-        *   `[ ] Tâche : Implémenter la logique de get_prompt_content pour lire un fichier de prompt `.md` dans la structure de personnalité.`
-        *   `[ ] Tâche : Implémenter la logique principale de load pour importer dynamiquement le code de l'agent et l'instancier avec son prompt.`
-        *   `[ ] Doc : Mettre à jour docs/architecture/README.md pour expliquer comment les agents sont chargés avec leur "personnalité" découplée.`
-        *   `[ ] Test : Créer le fichier de test unitaire vide tests/unit/agents/test_agent_loader.py.`
-        *   `[ ] Test : Écrire un test avec une fausse structure de personnalité pour valider que l'agent est chargé avec le bon prompt.`
-        *   `[ ] Test : Écrire un test pour un cas d'erreur (ex: version de prompt non trouvée).`
-        *   `[ ] Commit : Rédiger et exécuter le commit pour le chargeur d'agents avec le message "feat(core): implement agent personality loader".`
+    *   **Composant 3 : Chargeur d'Agents (`src/core/agents/agent_loader.py`)**
+
+        *   **3.1 : Conception et Prérequis**
+            *   `[ ] Tâche : Créer le fichier `src/core/agents/agent_loader.py` avec les imports (`importlib`, `pathlib`, `logging`, `typing`, `json`).`
+            *   `[ ] Tâche : Créer le fichier d'interface `src/core/agents/interfaces.py` pour définir `AgentConfig` et `BaseAgent`.`
+            *   `[ ] Tâche : Dans `interfaces.py`, définir une `TypedDict` ou `dataclass` nommée `AgentConfig` contenant `name`, `version`, `agent_class`, et optionnellement `description`.`
+            *   `[ ] Tâche : Dans `interfaces.py`, définir une classe abstraite `BaseAgent(ABC)` avec une méthode `__init__` qui accepte un `system_prompt: str`. Ceci garantit que tout agent chargé aura une interface commune.`
+
+        *   **3.2 : Implémentation de la classe `AgentLoader`**
+            *   `[ ] Tâche : Définir la classe `AgentLoader` avec un `__init__` qui prend le chemin de base des personnalités (`personalities_path: Path`).`
+            *   `[ ] Tâche : Implémenter une méthode privée `_get_personality_path(self, agent_name: str, version: str) -> Path` pour construire et valider le chemin vers un dossier de personnalité spécifique.`
+            *   `[ ] Tâche : Implémenter une méthode privée `_load_agent_config(self, personality_path: Path) -> AgentConfig` pour lire et valider le fichier `config.json` de l'agent.`
+            *   `[ ] Tâche : Implémenter une méthode privée `_load_system_prompt(self, personality_path: Path) -> str` pour lire le fichier `system.md`.`
+            *   `[ ] Tâche : Implémenter une méthode privée `_import_agent_class(self, module_path: str, class_name: str) -> Type[BaseAgent]` qui utilise `importlib` pour importer dynamiquement la classe de l'agent et valide qu'elle hérite de `BaseAgent`.`
+            *   `[ ] Tâche : Implémenter la méthode publique principale `load(self, agent_name: str, version: str) -> BaseAgent`.`
+            *   `[ ] Tâche : Dans `load`, orchestrer les appels aux méthodes privées : trouver le chemin, charger la config, charger le prompt, importer la classe, et finalement instancier la classe avec `agent_class(system_prompt=system_prompt)`.`
+            *   `[ ] Tâche : Intégrer une gestion d'erreurs robuste pour chaque étape : `FileNotFoundError` si un chemin, `config.json` ou `system.md` est manquant; `KeyError` pour un `config.json` malformé; `ImportError` ou `AttributeError` si l'importation de la classe échoue. Chaque erreur doit être encapsulée dans une exception personnalisée (ex: `AgentLoadError`).`
+
+        *   **3.3 : Tests Unitaires Exhaustifs du `AgentLoader`**
+            *   `[ ] Tâche : Créer le fichier `tests/unit/core/agents/test_agent_loader.py`.`
+            *   `[ ] Tâche : Créer une fixture `pytest` avec `tmp_path` pour générer une fausse arborescence de personnalités : `personalities/my_agent/v1/` contenant `config.json`, `system.md` et `agent.py`.`
+            *   `[ ] Tâche : Dans `agent.py`, définir une classe `MyAgent(BaseAgent)` valide.`
+            *   `[ ] Tâche : Test `test_load_agent_successfully` : Vérifier que l'agent est chargé, que c'est une instance de `MyAgent` et `BaseAgent`, et que son `system_prompt` correspond au contenu de `system.md`.`
+            *   `[ ] Tâche : Test `test_load_fails_if_agent_not_found` : vérifier qu'une `AgentLoadError` (ou `FileNotFoundError`) est levée si le dossier `my_agent` n'existe pas.`
+            *   `[ ] Tâche : Test `test_load_fails_if_version_not_found` : vérifier qu'une erreur est levée si le dossier `v1` n'existe pas.`
+            *   `[ ] Tâche : Test `test_load_fails_if_config_is_missing` : vérifier qu'une erreur est levée si `config.json` est manquant.`
+            *   `[ ] Tâche : Test `test_load_fails_if_prompt_is_missing` : vérifier qu'une erreur est levée si `system.md` est manquant.`
+            *   `[ ] Tâche : Test `test_load_fails_with_broken_python_code` : Créer un `agent.py` avec une erreur de syntaxe et vérifier que `ImportError` est correctement gérée.`
+            *   `[ ] Tâche : Test `test_load_fails_if_class_not_found_in_module` : Vérifier qu'une `AttributeError` est gérée si `agent_class` dans `config.json` n'existe pas dans `agent.py`.`
+
+        *   **3.4 : Documentation et Commit**
+            *   `[ ] Doc : Mettre à jour `docs/architecture/README.md` avec une section "Chargement des Agents" expliquant le rôle de `AgentLoader` et le concept de "personnalité" découplée.`
+            *   `[ ] Doc : Ajouter un diagramme Mermaid illustrant le flux de la méthode `load()`: `Répertoire -> config.json -> system.md -> agent.py -> Instance d'Agent`.`
+            *   `[ ] Commit : Rédiger un message de commit atomique: `feat(core): implement robust agent loader with decoupled personality structure`."`
 
 
 #### Action 1.3 : Mettre en place la structure de test unifiée

```

### 1.3 Preuve de Validation Sémantique

Cette densification du plan est une validation directe du grounding sémantique. La checklist microscopique reflète précisément les dépendances et fonctionnalités découvertes : la lecture de fichiers de configuration et de prompt, l'importation dynamique de code, et l'instanciation d'une classe selon un contrat d'interface (`BaseAgent`). La base de connaissance a été enrichie en transformant une intention architecturale ("charger des agents") en un plan d'action technique, testable et documentable.

---

## 2. Synthèse pour Grounding Orchestrateur

Ce plan détaillé pour l'`AgentLoader` concrétise plusieurs objectifs fondamentaux du projet :

*   **Modularité et Découplage Fort :** En séparant la définition du comportement d'un agent (sa "personnalité" dans les fichiers `config.json` et `system.md`) de sa logique Python, nous créons des composants véritablement indépendants. L'orchestrateur n'a plus besoin de connaître les détails d'implémentation d'un agent pour l'invoquer.
*   **Testabilité Améliorée :** La granularité du plan impose des tests unitaires pour chaque scénario (succès, échecs prévisibles). Ceci garantit un `AgentLoader` robuste, ce qui est critique car il s'agit d'une pierre angulaire de l'infrastructure.
*   **Extensibilité (Principe Ouvert/Fermé) :** Pour introduire un nouvel agent dans le système, il suffira de créer un nouveau répertoire de personnalité. Aucun changement ne sera requis dans le code du `AgentLoader` ou de l'orchestrateur. Le système est donc ouvert à l'extension (nouveaux agents) mais fermé à la modification (code de l'infrastructure).
*   **Clarté et Maintenabilité :** La structure de personnalité (`config.json`, `system.md`, `agent.py`) crée une convention claire et auto-documentée. Tout développeur peut rapidement comprendre comment définir ou modifier un agent.

La mise en œuvre de ce plan est une étape essentielle pour solidifier l'architecture de base du système avant de construire des fonctionnalités plus complexes.