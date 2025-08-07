# Plan de Test et Architecture pour le PluginLoader

**Auteur:** Roo, Architecte Technique
**Date:** 2025-08-03
**Statut:** Prêt pour implémentation

## 1. Contexte et Objectifs

Ce document définit l'architecture et le plan de test pour le composant `PluginLoader`. L'objectif est de s'assurer que le `PluginLoader` est robuste, fiable et capable de découvrir, charger et valider des plugins externes à partir du système de fichiers de manière sécurisée.

Le `PluginLoader` est un composant critique dont le rôle est de scanner des répertoires spécifiés, d'identifier des plugins potentiels via un fichier `plugin_manifest.json`, de valider leurs métadonnées, et de charger dynamiquement leur code pour les instancier.

Il interagit indirectement avec l'`OrchestrationService` : le `PluginLoader` produit un registre de plugins instanciés, qui sera ensuite utilisé pour peupler le registre de l'`OrchestrationService`.

## 2. Architecture de Test

### 2.1. Localisation des Tests

Les tests unitaires du `PluginLoader` seront situés dans :
`tests/unit/core/test_plugin_loader.py`

### 2.2. Environnement de Test : Faux Plugins

Pour garantir des tests déterministes et isolés, nous utiliserons une structure de "faux" plugins créée dynamiquement dans un environnement de test temporaire.

**Structure type d'un plugin de test ("valid_plugin") :**

```
/tmp/fake_plugins/valid_plugin/
|-- plugin_manifest.json
`-- plugin.py
```

*   **`plugin_manifest.json`** :
    ```json
    {
      "name": "ValidPlugin",
      "version": "1.0.0",
      "description": "A correctly configured test plugin.",
      "entrypoint_module": "plugin",
      "entrypoint_class": "ValidPluginClass"
    }
    ```
*   **`plugin.py`** :
    ```python
    from src.core.plugins.interfaces import BasePlugin

    class ValidPluginClass(BasePlugin):
        @property
        def name(self) -> str:
            return "ValidPlugin"

        def execute(self, **kwargs) -> dict:
            return {"status": "success"}
    ```

### 2.3. Stratégie de Mocking

1.  **Système de Fichiers (`pyfakefs`)** : Toutes les opérations sur le système de fichiers (`os.path`, `os.listdir`, `open`) seront interceptées et redirigées vers un système de fichiers virtuel en mémoire. Cela permet de simuler la présence de répertoires et de fichiers de plugins sans toucher au disque réel.
2.  **Système d'Importation (`unittest.mock.patch`)** : L'appel à `importlib.import_module()` sera patché pour retourner des objets `MagicMock` configurés. Cela nous donne un contrôle total sur les "modules" et "classes" que le `PluginLoader` découvre, nous permettant de simuler des cas d'erreur comme des classes manquantes ou des héritages incorrects.

## 3. Plan de Test Détaillé

### 3.1. Cas Nominal

| Test | Objectif | Assertions Clés |
| :--- | :--- | :--- |
| **`test_discover_and_load_valid_plugin`** | Un plugin valide est trouvé, chargé, et instancié correctement. | Le registre retourné contient une instance du plugin valide, identifiée par son nom. |

### 3.2. Cas d'Erreur

| Test | Objectif | Assertions Clés |
| :--- | :--- | :--- |
| **`test_discover_ignores_directory_without_manifest`** | Un répertoire sans `plugin_manifest.json` est ignoré silencieusement. | Le registre de plugins est vide. |
| **`test_discover_handles_malformed_manifest`** | Un `plugin_manifest.json` avec un JSON invalide est géré sans crash. | Le registre est vide. Un avertissement est loggué. |
| **`test_discover_handles_missing_entrypoint_file`** | Le loader gère le cas où le fichier `.py` du plugin est manquant. | Le registre est vide. `ImportError` est interceptée et un avertissement est loggué. |
| **`test_discover_handles_missing_entrypoint_class`** | Le loader gère le cas où la classe du plugin n'existe pas dans le fichier. | Le registre est vide. Un avertissement est loggué. |
| **`test_discover_handles_class_not_subclass_of_baseplugin`** | Le loader rejette une classe qui n'hérite pas de `BasePlugin`. | Le registre est vide. |

## 4. Prochaines Étapes

Ce plan de test est maintenant prêt à être transmis à un agent `code` pour l'implémentation des tests décrits dans `tests/unit/core/test_plugin_loader.py` et la refonte potentielle de `src/core/plugin_loader.py` pour qu'il passe ces tests.