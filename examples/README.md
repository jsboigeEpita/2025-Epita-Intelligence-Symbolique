# 💡 Exemples

## 📋 Vue d'Ensemble

Cette collection d'exemples fournit du code réutilisable et des patterns d'implémentation pour différents aspects du système d'argumentation de l'Intelligence Symbolique EPITA. Chaque catégorie est numérotée pour faciliter la progression et l'apprentissage.

Les exemples couvrent un large spectre : de la logique formelle aux intégrations système, en passant par le développement de plugins et les notebooks interactifs.

## 📂 Structure

```
examples/
├── 01_logic_and_riddles/        # Logique formelle et énigmes
│   ├── cluedo_demo/            # Démo Cluedo avec logique déductive
│   └── Sherlock_Watson/        # Enquête Sherlock Holmes
├── 02_core_system_demos/        # Fonctionnalités du système central
│   ├── phase2_demo/            # Démonstrations Phase 2
│   └── scripts_demonstration/  # Scripts de démonstration complets
├── 03_integrations/             # Intégrations avec systèmes externes
│   └── backend_demos/          # Démonstrations backend
├── 04_plugins/                  # Exemples de plugins
│   └── hello_world_plugin/     # Plugin "Hello World" de base
└── 05_notebooks/                # Notebooks Jupyter interactifs
```

## 🎯 Catégories d'Exemples

### 📊 01. Logic and Riddles

**Thème** : Logique formelle, raisonnement déductif et résolution d'énigmes  
**Niveau** : Débutant à Intermédiaire  
**Technologies** : Python, logique propositionnelle, systèmes à base de règles

#### Contenu

| Sous-répertoire | Description | Points Clés |
|-----------------|-------------|-------------|
| **[cluedo_demo/](./01_logic_and_riddles/cluedo_demo/)** | Résolution du jeu Cluedo par raisonnement logique | Déduction, élimination, inférence |
| **[Sherlock_Watson/](./01_logic_and_riddles/Sherlock_Watson/)** | Enquête inspirée de Sherlock Holmes | Raisonnement abductif, chaîne d'indices |

**Cas d'usage** :
- Comprendre les bases du raisonnement logique
- Implémenter des systèmes de déduction
- Résoudre des problèmes par élimination

**📖 [Documentation détaillée](./01_logic_and_riddles/README.md)**

### ⚙️ 02. Core System Demos

**Thème** : Fonctionnalités centrales du système d'argumentation  
**Niveau** : Intermédiaire  
**Technologies** : Python, Semantic Kernel, API d'analyse

#### Contenu

| Sous-répertoire | Description | Points Clés |
|-----------------|-------------|-------------|
| **[phase2_demo/](./02_core_system_demos/phase2_demo/)** | Démonstrations des fonctionnalités Phase 2 | Workflows, intégration agents |
| **[scripts_demonstration/](./02_core_system_demos/scripts_demonstration/)** | Scripts de démonstration exhaustifs | Cas d'usage complets, validation |

**Cas d'usage** :
- Découvrir les capacités du système central
- Comprendre l'intégration des agents
- Valider les fonctionnalités principales

**📖 [Documentation détaillée](./02_core_system_demos/README.md)**

### 🔗 03. Integrations

**Thème** : Intégration avec systèmes externes et architectures distribuées  
**Niveau** : Intermédiaire à Avancé  
**Technologies** : API REST, microservices, backends

#### Contenu

| Sous-répertoire | Description | Points Clés |
|-----------------|-------------|-------------|
| **[backend_demos/](./03_integrations/backend_demos/)** | Démonstrations d'intégration backend | API, services, architectures |

**Cas d'usage** :
- Intégrer le système dans une architecture existante
- Créer des API pour exposer les fonctionnalités
- Gérer la communication inter-services

**📖 [Documentation détaillée](./03_integrations/README.md)**

### 🔌 04. Plugins

**Thème** : Architecture et développement de plugins  
**Niveau** : Avancé  
**Technologies** : Python, architecture modulaire, patterns de design

#### Contenu

| Sous-répertoire | Description | Points Clés |
|-----------------|-------------|-------------|
| **[hello_world_plugin/](./04_plugins/hello_world_plugin/)** | Plugin minimal de démonstration | Structure de base, API plugins |

**Cas d'usage** :
- Comprendre l'architecture des plugins
- Développer vos propres extensions
- Étendre les capacités du système

**📖 [Documentation détaillée](./04_plugins/README.md)**

### 📓 05. Notebooks

**Thème** : Notebooks interactifs Jupyter pour apprentissage et exploration  
**Niveau** : Tous niveaux  
**Technologies** : Jupyter, Python, visualisations

#### Contenu

| Notebook | Description | Niveau |
|----------|-------------|--------|
| **[api_logic_tutorial.ipynb](./05_notebooks/api_logic_tutorial.ipynb)** | Tutoriel API des agents logiques | Intermédiaire |
| **[logic_agents_tutorial.ipynb](./05_notebooks/logic_agents_tutorial.ipynb)** | Guide complet des agents logiques | Débutant |

**Cas d'usage** :
- Apprentissage interactif et expérimentation
- Visualisation des résultats d'analyse
- Prototypage rapide

**📖 [Documentation détaillée](./05_notebooks/README.md)**

## 🚀 Utilisation

### Prérequis

Avant d'exécuter les exemples, assurez-vous que :

```bash
# 1. Environnement virtuel activé
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Dépendances installées
pip install -r requirements.txt

# 3. Variables d'environnement configurées (si nécessaire)
cp .env.example .env
# Éditer .env avec vos clés API
```

### Exécution des Scripts Python

```bash
# Pattern général
python examples/[categorie]/[sous-repertoire]/[script].py

# Exemples concrets
python examples/01_logic_and_riddles/cluedo_demo/main.py
python examples/02_core_system_demos/scripts_demonstration/demo_tweety.py
```

### Utilisation des Notebooks

```bash
# Lancer Jupyter
jupyter notebook

# Ou JupyterLab
jupyter lab

# Naviguer vers examples/05_notebooks/ et ouvrir un notebook
```

### Bootstrap Recommandé

Tous les scripts doivent inclure ce pattern de bootstrap pour garantir un fonctionnement autonome :

```python
#!/usr/bin/env python3
"""
Description de votre script
"""

from pathlib import Path
import sys

# Bootstrap robuste avec détection automatique de la racine
current_file = Path(__file__).resolve()
project_root = next((p for p in current_file.parents if (p / "pyproject.toml").exists()), None)

if project_root is None:
    raise FileNotFoundError("Impossible de localiser la racine du projet")
    
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    
from argumentation_analysis.core.environment import ensure_env
ensure_env()

# Votre code principal ici
```

## 🎓 Parcours d'Apprentissage Recommandé

### Pour les Débutants

1. **[05_notebooks/logic_agents_tutorial.ipynb](./05_notebooks/logic_agents_tutorial.ipynb)** - Commencez ici pour une introduction interactive
2. **[01_logic_and_riddles/cluedo_demo/](./01_logic_and_riddles/cluedo_demo/)** - Apprenez le raisonnement logique
3. **[04_plugins/hello_world_plugin/](./04_plugins/hello_world_plugin/)** - Découvrez l'architecture des plugins

### Pour les Développeurs Intermédiaires

1. **[02_core_system_demos/phase2_demo/](./02_core_system_demos/phase2_demo/)** - Explorez les fonctionnalités avancées
2. **[05_notebooks/api_logic_tutorial.ipynb](./05_notebooks/api_logic_tutorial.ipynb)** - Maîtrisez l'API
3. **[03_integrations/backend_demos/](./03_integrations/backend_demos/)** - Intégrez avec des systèmes externes

### Pour les Contributeurs Avancés

1. **[01_logic_and_riddles/Sherlock_Watson/](./01_logic_and_riddles/Sherlock_Watson/)** - Raisonnement complexe
2. **[02_core_system_demos/scripts_demonstration/](./02_core_system_demos/scripts_demonstration/)** - Cas d'usage exhaustifs
3. Développez vos propres plugins en vous inspirant de **[04_plugins/](./04_plugins/)**

## 🔗 Ressources Connexes

- **[Tutoriels](../tutorials/README.md)** : Apprentissage guidé pas-à-pas
- **[Démonstrations](../demos/README.md)** : Cas d'usage complets et fonctionnels
- **[Documentation](../docs/)** : Référence technique et API
- **[Plugins](../plugins/)** : Collection complète de plugins disponibles

## 💡 Contribuer

### Ajouter un Nouvel Exemple

Pour enrichir la collection d'exemples :

#### 1. Choisir la Catégorie

Déterminez où votre exemple s'insère :
- **01_logic_and_riddles/** : Si c'est un problème de logique ou une énigme
- **02_core_system_demos/** : Si c'est une démonstration d'une fonctionnalité centrale
- **03_integrations/** : Si c'est une intégration avec un système externe
- **04_plugins/** : Si c'est un exemple de plugin
- **05_notebooks/** : Si c'est un tutoriel interactif

#### 2. Structure Requise

```
examples/0X_categorie/votre_exemple/
├── README.md           # Documentation de l'exemple
├── main.py            # Point d'entrée principal
├── requirements.txt   # Dépendances spécifiques (optionnel)
├── data/             # Données d'exemple (optionnel)
└── tests/            # Tests unitaires (optionnel)
```

#### 3. Documentation Obligatoire

Votre README.md doit inclure :

```markdown
# Titre de l'Exemple

## Description
[Description claire et concise]

## Objectifs d'Apprentissage
- Objectif 1
- Objectif 2

## Prérequis
- Prérequis 1
- Prérequis 2

## Installation
[Instructions si nécessaires]

## Utilisation
```bash
python main.py
```

## Résultat Attendu
[Description de ce que l'exemple doit produire]

## Concepts Clés
- Concept 1 : [explication]
- Concept 2 : [explication]

## Ressources Complémentaires
[Liens vers documentation, tutoriels, etc.]
```

#### 4. Standards de Code

- ✅ **Bootstrap obligatoire** : Utiliser le pattern de bootstrap recommandé
- ✅ **Docstrings** : Documenter toutes les fonctions et classes
- ✅ **Type hints** : Utiliser les annotations de types Python
- ✅ **Comments** : Expliquer les parties complexes
- ✅ **Tests** : Inclure au moins un test de base
- ✅ **PEP 8** : Respecter les conventions de style Python

#### 5. Workflow de Contribution

```bash
# 1. Créer une branche
git checkout -b feature/exemple-votre-nom

# 2. Ajouter vos fichiers
# Créer votre structure de dossier
# Développer votre exemple

# 3. Tester votre exemple
python examples/0X_categorie/votre_exemple/main.py

# 4. Mettre à jour les README
# - Ce README principal (ajouter une ligne dans la table appropriée)
# - Le README de la sous-catégorie
# - Le README de votre exemple

# 5. Commiter et pusher
git add examples/0X_categorie/votre_exemple/
git commit -m "feat(examples): Ajout exemple [votre nom]

- Description courte de l'exemple
- Technologies utilisées
- Niveau: [Débutant/Intermédiaire/Avancé]"
git push origin feature/exemple-votre-nom

# 6. Créer une Pull Request
```

### Guidelines de Qualité

#### ✅ Bon Exemple

```python
#!/usr/bin/env python3
"""
Exemple : Détection de sophisme ad hominem
Description : Analyse un texte pour identifier les attaques ad hominem
Niveau : Intermédiaire
"""

from pathlib import Path
import sys

# Bootstrap
current_file = Path(__file__).resolve()
project_root = next((p for p in current_file.parents if (p / "pyproject.toml").exists()), None)
if project_root and str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from argumentation_analysis.core.environment import ensure_env
ensure_env()

from argumentation_analysis.services.extract_service import ExtractService

def detect_ad_hominem(text: str) -> dict:
    """
    Détecte les attaques ad hominem dans un texte.
    
    Args:
        text: Le texte à analyser
        
    Returns:
        Dictionnaire contenant les sophismes détectés
    """
    service = ExtractService()
    result = service.analyze_text(text)
    
    ad_hominem_fallacies = [
        f for f in result.fallacies 
        if f.type == "ad_hominem"
    ]
    
    return {
        "count": len(ad_hominem_fallacies),
        "fallacies": ad_hominem_fallacies
    }

if __name__ == "__main__":
    # Exemple d'utilisation
    text = """
    Mon adversaire politique prétend que sa politique économique
    est meilleure, mais comment peut-on faire confiance à quelqu'un
    qui a échoué dans ses propres affaires ?
    """
    
    result = detect_ad_hominem(text)
    print(f"Nombre d'attaques ad hominem détectées : {result['count']}")
    
    for fallacy in result['fallacies']:
        print(f"- {fallacy.description}")
```

#### ❌ Mauvais Exemple

```python
# Pas de docstring, pas de bootstrap, code mal structuré
import sys
sys.path.append('..')

from services import ExtractService

text = "bla bla bla"
s = ExtractService()
r = s.analyze_text(text)
print(r)
```

## 📊 Statistiques

- **Total exemples** : 7 sous-répertoires + 2 notebooks
- **Catégories** : 5 (Logic, Core System, Integrations, Plugins, Notebooks)
- **Niveaux** : Débutant (3), Intermédiaire (4), Avancé (2)
- **Langages** : Python, Jupyter
- **Dernière mise à jour** : Phase D2.3

## 🏆 Hall of Fame

Exemples particulièrement réussis qui illustrent les meilleures pratiques :

1. **cluedo_demo/** - Excellent exemple de raisonnement logique structuré
2. **hello_world_plugin/** - Template parfait pour développer des plugins
3. **logic_agents_tutorial.ipynb** - Tutoriel interactif complet et pédagogique

## ⚠️ Note Importante

Ce répertoire (`examples/`) contient des **exemples d'utilisation** du système. Ne le confondez pas avec :
- `demos/` - Démonstrations complètes de cas d'usage
- `tutorials/` - Guides pas-à-pas pour apprendre
- `tests/` - Suite de tests automatisés
- `argumentation_analysis/examples/` - Exemples internes au module (si existant)

---

**Dernière mise à jour** : Phase D2.3 - Documentation Structure  
**Mainteneur** : Intelligence Symbolique EPITA  
**Licence** : Voir LICENSE à la racine du projet