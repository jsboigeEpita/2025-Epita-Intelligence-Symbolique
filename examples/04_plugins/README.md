# 🔌 Plugins

## Description

Ce répertoire contient des exemples de plugins pour étendre les capacités du système d'argumentation. Les plugins permettent d'ajouter de nouvelles fonctionnalités de manière modulaire sans modifier le code core du système.

## Contenu

### Plugins Disponibles

| Plugin | Description | Niveau | Fichiers |
|--------|-------------|--------|----------|
| **[hello_world_plugin/](./hello_world_plugin/)** | Plugin minimal de démonstration | Débutant | main.py, plugin.yaml, README.md |

## 🎯 Hello World Plugin

**Objectif** : Template minimal pour créer votre premier plugin

### Structure

```
hello_world_plugin/
├── main.py          # Point d'entrée du plugin (26 lignes)
├── plugin.yaml      # Métadonnées et configuration (24 lignes)
└── README.md        # Documentation du plugin (54 lignes)
```

### Fichiers

| Fichier | Description | Lignes |
|---------|-------------|--------|
| [`main.py`](./hello_world_plugin/main.py) | Implémentation du plugin | 26 |
| [`plugin.yaml`](./hello_world_plugin/plugin.yaml) | Configuration et métadonnées | 24 |
| [`README.md`](./hello_world_plugin/README.md) | Documentation détaillée | 54 |

### Ce Que Vous Apprendrez

- ✅ Structure de base d'un plugin
- ✅ Configuration via YAML
- ✅ Interface plugin standard
- ✅ Chargement dynamique
- ✅ Bonnes pratiques de développement

**📖 [Documentation détaillée](./hello_world_plugin/README.md)**

## Architecture des Plugins

### Interface Standard

Tous les plugins doivent implémenter l'interface de base :

```python
class BasePlugin:
    """Interface de base pour tous les plugins"""
    
    def __init__(self, config: dict):
        """
        Initialisation du plugin
        
        Args:
            config: Configuration depuis plugin.yaml
        """
        self.config = config
        self.name = config.get('name', 'UnnamedPlugin')
        self.version = config.get('version', '0.1.0')
    
    def initialize(self):
        """Initialisation des ressources du plugin"""
        raise NotImplementedError
    
    def execute(self, *args, **kwargs):
        """Exécution de la fonctionnalité principale"""
        raise NotImplementedError
    
    def cleanup(self):
        """Nettoyage des ressources"""
        pass
```

### Configuration YAML

Format standard pour `plugin.yaml` :

```yaml
# Métadonnées du plugin
name: "Mon Plugin"
version: "1.0.0"
author: "Votre Nom"
description: "Description courte du plugin"

# Dépendances
dependencies:
  - semantic-kernel>=0.3.0
  - requests>=2.28.0

# Configuration
config:
  enabled: true
  priority: 10
  settings:
    custom_setting: "valeur"

# Points d'extension
hooks:
  - on_load
  - on_analyze
  - on_result
```

### Cycle de Vie

```
┌─────────────┐
│   Chargement │ ← Plugin découvert
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Validation  │ ← Vérif dépendances
└──────┬──────┘
       │
       ↓
┌─────────────┐
│Initialisation│ ← initialize()
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Exécution  │ ← execute()
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Nettoyage  │ ← cleanup()
└─────────────┘
```

## Développement de Plugins

### 1. Créer un Nouveau Plugin

```bash
# Créer la structure
mkdir examples/04_plugins/mon_plugin
cd examples/04_plugins/mon_plugin

# Créer les fichiers de base
touch main.py plugin.yaml README.md
```

### 2. Implémenter main.py

```python
#!/usr/bin/env python3
"""
Plugin: Mon Plugin
Description: Fait quelque chose d'utile
"""

from typing import Any, Dict

class MonPlugin:
    """Mon plugin personnalisé"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', 'MonPlugin')
    
    def initialize(self):
        """Initialisation du plugin"""
        print(f"Initialisation de {self.name}")
        # Charger les ressources nécessaires
    
    def execute(self, text: str) -> Dict[str, Any]:
        """Exécution principale"""
        # Votre logique ici
        result = {
            "plugin": self.name,
            "result": "traitement effectué"
        }
        return result
    
    def cleanup(self):
        """Nettoyage"""
        print(f"Nettoyage de {self.name}")

# Point d'entrée pour le système de plugins
def create_plugin(config: Dict[str, Any]):
    """Factory function pour créer une instance"""
    return MonPlugin(config)

if __name__ == "__main__":
    # Test standalone
    config = {"name": "MonPlugin"}
    plugin = create_plugin(config)
    plugin.initialize()
    result = plugin.execute("test")
    print(result)
    plugin.cleanup()
```

### 3. Configurer plugin.yaml

```yaml
name: "Mon Plugin"
version: "1.0.0"
author: "Votre Nom <email@example.com>"
description: |
  Description détaillée de ce que fait votre plugin.
  Peut être sur plusieurs lignes.

# Type de plugin
type: "analyzer"  # ou "transformer", "validator", etc.

# Dépendances Python
dependencies:
  - numpy>=1.20.0
  - pandas>=1.3.0

# Configuration par défaut
config:
  enabled: true
  priority: 10  # 0-100, plus élevé = plus prioritaire
  
  # Paramètres personnalisés
  settings:
    threshold: 0.75
    mode: "strict"
    
# Hooks du système
hooks:
  - name: "on_analyze"
    function: "execute"
  - name: "on_cleanup"
    function: "cleanup"

# Permissions requises
permissions:
  - "read:files"
  - "write:reports"
```

### 4. Documenter README.md

```markdown
# Mon Plugin

## Description
[Description claire de votre plugin]

## Fonctionnalités
- Fonctionnalité 1
- Fonctionnalité 2

## Installation
```bash
pip install -r requirements.txt
```

## Configuration
[Expliquer les options de configuration]

## Utilisation
```python
from mon_plugin import create_plugin

plugin = create_plugin(config)
result = plugin.execute("input")
```

## Exemples
[Exemples concrets]

## Limitations
[Limitations connues]

## Développement
[Guide pour contribuer]
```

## Types de Plugins

### 1. Analyzer Plugin

Analyse et extrait des informations :

```python
class AnalyzerPlugin:
    def execute(self, text: str) -> Dict[str, Any]:
        """Analyse le texte"""
        return {
            "entities": self.extract_entities(text),
            "sentiment": self.analyze_sentiment(text)
        }
```

### 2. Transformer Plugin

Transforme ou enrichit les données :

```python
class TransformerPlugin:
    def execute(self, data: Dict) -> Dict:
        """Transforme les données"""
        return {
            **data,
            "enriched": self.enrich(data)
        }
```

### 3. Validator Plugin

Valide la qualité ou cohérence :

```python
class ValidatorPlugin:
    def execute(self, result: Dict) -> bool:
        """Valide le résultat"""
        return self.is_valid(result)
```

### 4. Reporter Plugin

Génère des rapports personnalisés :

```python
class ReporterPlugin:
    def execute(self, results: Dict) -> str:
        """Génère un rapport"""
        return self.generate_report(results)
```

## Chargement des Plugins

### Dynamique

Le système charge automatiquement les plugins :

```python
import os
import yaml
import importlib.util

class PluginLoader:
    """Chargeur de plugins"""
    
    def __init__(self, plugins_dir: str):
        self.plugins_dir = plugins_dir
        self.plugins = {}
    
    def load_all(self):
        """Charge tous les plugins"""
        for plugin_name in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            if os.path.isdir(plugin_path):
                self.load_plugin(plugin_path)
    
    def load_plugin(self, plugin_path: str):
        """Charge un plugin spécifique"""
        # Lire la config
        config_file = os.path.join(plugin_path, 'plugin.yaml')
        with open(config_file) as f:
            config = yaml.safe_load(f)
        
        # Importer le module
        main_file = os.path.join(plugin_path, 'main.py')
        spec = importlib.util.spec_from_file_location(
            config['name'], main_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Créer l'instance
        plugin = module.create_plugin(config)
        plugin.initialize()
        
        self.plugins[config['name']] = plugin
```

## Tests

### Test Unitaire

```python
import pytest
from mon_plugin import create_plugin

def test_plugin_initialization():
    """Test initialisation"""
    config = {"name": "Test"}
    plugin = create_plugin(config)
    assert plugin.name == "Test"

def test_plugin_execute():
    """Test exécution"""
    config = {"name": "Test"}
    plugin = create_plugin(config)
    plugin.initialize()
    result = plugin.execute("input")
    assert result is not None
    plugin.cleanup()
```

### Test d'Intégration

```python
def test_plugin_in_system():
    """Test intégration dans le système"""
    from plugin_loader import PluginLoader
    
    loader = PluginLoader("examples/04_plugins")
    loader.load_all()
    
    assert "MonPlugin" in loader.plugins
    
    plugin = loader.plugins["MonPlugin"]
    result = plugin.execute("test")
    assert result["plugin"] == "MonPlugin"
```

## Bonnes Pratiques

### ✅ À Faire

1. **Documentation complète** : README + docstrings
2. **Tests exhaustifs** : Unitaires + intégration
3. **Gestion d'erreurs** : Try/catch appropriés
4. **Logging** : Pour debugging
5. **Configuration** : Paramètres externes
6. **Versioning** : Semantic versioning
7. **Dépendances** : Minimales et documentées

### ❌ À Éviter

1. **Code hardcodé** : Utiliser la configuration
2. **Effets de bord** : Plugin isolé
3. **Ressources non nettoyées** : Implémenter cleanup()
4. **Dépendances lourdes** : Rester léger
5. **Pas de tests** : Toujours tester

## Ressources Connexes

- **[Extending the System](../../tutorials/02_extending_the_system/)** : Tutoriels avancés
- **[Core System Demos](../02_core_system_demos/)** : Architecture du système
- **[Integration Patterns](../03_integrations/)** : Patterns d'intégration
- **[Documentation](../../docs/)** : Référence complète

## Contribution

### Soumettre un Plugin

1. **Développer** : Suivre la structure standard
2. **Tester** : Tests unitaires + intégration
3. **Documenter** : README complet
4. **PR** : Soumettre avec description détaillée

### Checklist

- [ ] Structure respectée (main.py, plugin.yaml, README.md)
- [ ] Tests écrits et passants
- [ ] Documentation complète
- [ ] Dépendances minimales
- [ ] Code reviewé

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA  
**Niveau** : Débutant à Avancé  
**Technologies** : Python, YAML, Plugin Architecture