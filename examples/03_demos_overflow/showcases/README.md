# 🌟 Showcases

## Description

Ce répertoire contient les présentations des fonctionnalités principales et des exemples d'usage simplifié du système d'argumentation. Ces showcases sont conçus pour une prise en main rapide et une démonstration des capacités essentielles.

## Contenu

### Fichiers

| Fichier | Description | Niveau |
|---------|-------------|--------|
| [`demo_one_liner_usage.py`](./demo_one_liner_usage.py) | Démonstration du one-liner auto-activateur intelligent pour agents IA | Débutant |
| [`simple_exploration_tool.py`](./simple_exploration_tool.py) | Outil d'exploration simplifié de la taxonomie des sophismes | Débutant |

## Utilisation

### Demo One-Liner Usage

Script de démonstration du pattern one-liner auto-activateur :

```bash
# Exécution standard
python demos/showcases/demo_one_liner_usage.py

# Depuis le répertoire demos/showcases/
cd demos/showcases
python demo_one_liner_usage.py
```

**Ce que cette démo illustre** :
- ✨ Pattern one-liner pour l'auto-activation
- 🚀 Démarrage rapide sans configuration complexe
- 🤖 Utilisation optimale pour agents IA
- 📦 Import minimal et élégant

**Le One-Liner Magique** :
```python
import argumentation_analysis.core.environment
```

C'est tout ! Cette unique ligne :
- ✅ Configure automatiquement l'environnement
- ✅ Initialise les dépendances nécessaires
- ✅ Rend le système prêt à l'emploi
- ✅ Fonctionne depuis n'importe quel contexte

### Simple Exploration Tool

Outil interactif pour explorer la taxonomie des sophismes :

```bash
# Exécution standard
python demos/showcases/simple_exploration_tool.py

# Mode interactif
python demos/showcases/simple_exploration_tool.py --interactive
```

**Ce que cet outil permet** :
- 🔍 Explorer la taxonomie des sophismes
- 📚 Consulter les définitions et exemples
- 🎯 Rechercher des sophismes par catégorie
- 📊 Visualiser la structure hiérarchique

## Le Pattern One-Liner

### Pourquoi C'est Important

Le one-liner résout plusieurs problèmes :

1. **Simplicité** : Pas besoin de comprendre la configuration complexe
2. **Portabilité** : Fonctionne partout, peu importe le contexte
3. **IA-Friendly** : Idéal pour les agents IA qui génèrent du code
4. **Maintenance** : Un seul point de configuration centralisé

### Comparaison Avant/Après

#### ❌ Avant (complexe et fragile)

```python
import sys
import os
from pathlib import Path

# Détection manuelle de la racine
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
while not os.path.exists(os.path.join(project_root, 'pyproject.toml')):
    project_root = os.path.dirname(project_root)
    if project_root == '/':
        raise Exception("Racine non trouvée")

# Configuration manuelle du path
sys.path.insert(0, project_root)

# Initialisation manuelle de l'environnement
from argumentation_analysis.core.config import load_config
from argumentation_analysis.core.dependencies import init_deps

config = load_config()
init_deps(config)

# Enfin, on peut commencer à coder...
```

#### ✅ Après (simple et robuste)

```python
# One-liner magique
import argumentation_analysis.core.environment

# C'est tout ! On peut coder directement
from argumentation_analysis.services.extract_service import ExtractService

service = ExtractService()
result = service.analyze_text("Mon texte")
```

### Comment Ça Marche ?

Le module `argumentation_analysis.core.environment` :

1. **S'auto-exécute** au moment de l'import (via `__init__.py`)
2. **Détecte la racine** du projet automatiquement
3. **Configure sys.path** correctement
4. **Initialise les dépendances** nécessaires
5. **Reste silencieux** si tout va bien

## Exploration de la Taxonomie

### Interface Simple

L'outil d'exploration offre une interface intuitive :

```
=== Taxonomie des Sophismes ===

Catégories disponibles:
1. Fallacies d'Appel (Appeal)
2. Fallacies de Causalité (Causation)
3. Fallacies de Pertinence (Relevance)
4. Fallacies Formelles (Formal)

Entrez le numéro de catégorie (ou 'q' pour quitter): 1

=== Fallacies d'Appel ===
- Ad Hominem : Attaque la personne plutôt que l'argument
- Argument d'Autorité : Se base uniquement sur l'autorité
- Appel à la Popularité : "Tout le monde le fait"
...
```

### Recherche et Filtrage

```bash
# Rechercher un sophisme spécifique
python demos/showcases/simple_exploration_tool.py --search "ad hominem"

# Lister une catégorie
python demos/showcases/simple_exploration_tool.py --category "appeal"

# Export en JSON
python demos/showcases/simple_exploration_tool.py --export taxonomy.json
```

## Cas d'Usage

### Pour les Débutants

**Première découverte du système** :

```bash
# 1. Lancez le one-liner
python demos/showcases/demo_one_liner_usage.py

# 2. Explorez la taxonomie
python demos/showcases/simple_exploration_tool.py

# 3. Passez aux tutoriels
# Voir ../tutorials/01_getting_started/
```

### Pour les Agents IA

**Génération de code avec le one-liner** :

```python
#!/usr/bin/env python3
"""
Script généré automatiquement par un agent IA
"""

# One-liner pour garantir l'environnement
import argumentation_analysis.core.environment

# Le code de l'agent peut maintenant utiliser le système
from argumentation_analysis.services.extract_service import ExtractService

def analyze_user_input(text: str):
    """Analyse le texte utilisateur"""
    service = ExtractService()
    return service.analyze_text(text)

if __name__ == "__main__":
    result = analyze_user_input("Exemple de texte argumentatif")
    print(result)
```

### Pour les Présentations

**Démonstration rapide lors d'un workshop** :

```python
# Slide 1: Le problème
# "Configuration complexe, multiples étapes, erreurs fréquentes"

# Slide 2: La solution
import argumentation_analysis.core.environment
from argumentation_analysis.services.extract_service import ExtractService

# Slide 3: Utilisation immédiate
service = ExtractService()
result = service.analyze_text("L'IA va nous remplacer !")
print(f"Sophismes détectés: {len(result.fallacies)}")
```

## Notes Techniques

### Mécanisme d'Auto-Activation

Le fichier `argumentation_analysis/core/environment/__init__.py` contient :

```python
# Exécuté automatiquement lors de l'import
from pathlib import Path
import sys

def ensure_env():
    """Garantit que l'environnement est configuré"""
    # Détection de la racine
    current = Path(__file__).resolve()
    root = next((p for p in current.parents if (p / "pyproject.toml").exists()), None)
    
    if root and str(root) not in sys.path:
        sys.path.insert(0, str(root))
    
    # Initialisation des dépendances
    _init_dependencies()

# Auto-exécution
ensure_env()
```

### Avantages du Pattern

| Aspect | Bénéfice |
|--------|----------|
| **Développement** | Démarrage ultra-rapide |
| **Debugging** | Un seul point de configuration |
| **CI/CD** | Scripts plus simples et fiables |
| **Documentation** | Exemples plus clairs |
| **IA Agents** | Génération de code robuste |

### Limitations

⚠️ **Points d'attention** :

1. **Import Order** : Le one-liner doit être le premier import du système
2. **Side Effects** : L'import modifie `sys.path` globalement
3. **Testing** : Peut nécessiter des mocks pour les tests unitaires
4. **Transparence** : L'auto-configuration peut surprendre les développeurs

## Ressources Connexes

- **[Tutoriels](../../tutorials/README.md)** : Guides détaillés pour apprendre
- **[Exemples](../../examples/README.md)** : Code réutilisable
- **[Validation](../validation/README.md)** : Tests de validation
- **[Documentation](../../docs/)** : Référence complète

## Contribution

### Ajouter un Nouveau Showcase

Pour créer un nouveau showcase :

1. **Identifier le besoin** : Quelle fonctionnalité mérite une démo simple ?
2. **Créer le script** : Suivre le pattern one-liner
3. **Documenter** : Ajouter une section dans ce README
4. **Tester** : Vérifier que c'est vraiment simple pour un débutant

### Template de Showcase

```python
#!/usr/bin/env python3
"""
Showcase : [Titre de votre démo]
==================================

Description courte de ce que cette démo illustre.

Usage:
    python demos/showcases/votre_demo.py

Auteur: Intelligence Symbolique EPITA
"""

# One-liner magique
import argumentation_analysis.core.environment

def main():
    """Point d'entrée principal"""
    print("=== Titre de la Démo ===\n")
    
    # Votre code de démonstration ici
    # Gardez-le SIMPLE et CLAIR
    
    print("\n✓ Démo terminée!")

if __name__ == "__main__":
    main()
```

## FAQ

**Q: Le one-liner fonctionne-t-il toujours ?**  
R: Oui, tant que la structure du projet reste cohérente avec `pyproject.toml` à la racine.

**Q: Puis-je utiliser le one-liner dans mes propres projets ?**  
R: Absolument ! C'est le but. Copiez le pattern dans vos scripts.

**Q: Que faire si le one-liner échoue ?**  
R: Vérifiez que `pyproject.toml` existe à la racine et que vous avez les dépendances installées.

**Q: L'outil d'exploration est-il interactif ?**  
R: Oui, lancez-le sans arguments pour le mode interactif.

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA