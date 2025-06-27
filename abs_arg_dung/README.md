# Agent d'Argumentation Abstraite de Dung
**Étudiants inscrits** : wassim.badraoui, alexandre.da-silva, roshan.jeyakumar
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![TweetyProject](https://img.shields.io/badge/TweetyProject-1.28-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

Ce projet implémente un agent d'argumentation complet basé sur les frameworks d'argumentation abstraite de Dung, utilisant la bibliothèque TweetyProject pour Java.

## 🎯 Fonctionnalités

- **Construction de frameworks** : Création interactive et programmatique
- **Calcul d'extensions** : Toutes les sémantiques principales (grounded, preferred, stable, complete, admissible, ideal, semi-stable)
- **Visualisation graphique** : Rendu des graphes d'argumentation avec mise en évidence des extensions
- **Analyse avancée** : Propriétés structurelles, statut des arguments, relations sémantiques
- **Import/Export** : Support JSON, TGF, DOT pour l'interopérabilité
- **Génération aléatoire** : Frameworks automatiques pour tests et benchmarks
- **Interface CLI** : Ligne de commande complète pour toutes les opérations
- **Agent amélioré** : Corrections pour cas problématiques spécifiques
- **Tests complets** : Suite de tests unitaires et avancés
- **Validation automatique** : Script de validation complète du projet
- **Démonstration interactive** : Présentation guidée de toutes les fonctionnalités

## 📦 Installation

### Prérequis
- Python 3.8+
- Java 8+ (pour TweetyProject)

### Installation rapide
```bash
# Cloner le projet
git clone <repository_url>
cd mon_agent_dung

# Installer les dépendances
pip install -r requirements.txt
```

### Structure du projet
```
mon_agent_dung/
├── agent.py                 # Classe principale DungAgent
├── enhanced_agent.py        # Agent avec corrections
├── framework_generator.py   # Génération de frameworks
├── io_utils.py             # Import/export multi-formats
├── cli.py                  # Interface ligne de commande
├── config.py               # Configuration centralisée
├── project_info.py         # Métadonnées du projet
├── test_agent.py           # Tests unitaires de base
├── advanced_tests.py       # Tests avancés et complexes
├── benchmark.py            # Benchmarking de performance
├── validate_project.py     # Validation complète du projet
├── demo_interactive.py     # Démonstration interactive
├── demo.ipynb              # Notebook Jupyter
├── README.md               # Cette documentation
├── requirements.txt        # Dépendances Python
├── libs/                   # Bibliothèques TweetyProject JAR
├── data/                   # Dossier pour vos frameworks
├── outputs/                # Résultats d'export
└── examples/               # Exemples de frameworks
```

## 🚀 Démarrage rapide

### 🎬 Démonstration complète
```bash
# Démonstration interactive de toutes les fonctionnalités
python demo_interactive.py
```

### ✅ Validation du projet
```bash
# Valider que tout fonctionne correctement
python validate_project.py
```

### 📊 Informations du projet
```bash
# Voir les métadonnées et statistiques
python cli.py info
python project_info.py
```

### Utilisation programmatique

```python
from agent import DungAgent

# Créer un agent
agent = DungAgent()

# Construire un framework
agent.add_argument("a")
agent.add_argument("b") 
agent.add_argument("c")

agent.add_attack("a", "b")
agent.add_attack("b", "c")

# Analyser
grounded = agent.get_grounded_extension()
preferred = agent.get_preferred_extensions()

print(f"Extension fondée: {grounded}")
print(f"Extensions préférées: {preferred}")

# Analyse complète
agent.analyze_semantics_relationships()
agent.print_all_arguments_status()

# Visualisation
agent.visualize_graph()
```

### Interface en ligne de commande

```bash
# Créer un framework interactivement
python cli.py create

# Générer un framework aléatoire
python cli.py random --size 10 --prob 0.4 --save my_framework.json

# Analyser un framework existant
python cli.py analyze my_framework.json --export analysis_report.json

# Voir les exemples classiques
python cli.py examples --list
python cli.py examples --run triangle

# Convertir entre formats
python cli.py convert framework.json framework.tgf --format tgf

# Informations du projet
python cli.py info
```

## 📊 Exemples d'utilisation

### Framework simple
```python
agent = DungAgent()
agent.add_argument("manger_viande")
agent.add_argument("etre_vegetarien") 
agent.add_argument("sante")

agent.add_attack("etre_vegetarien", "manger_viande")
agent.add_attack("sante", "manger_viande")

# Analyse du débat
agent.analyze_semantics_relationships()
```

### Génération et test de masse
```python
from framework_generator import FrameworkGenerator

# 100 frameworks aléatoires pour analyse statistique
for i in range(100):
    agent = FrameworkGenerator.generate_random_framework(
        num_args=8, 
        attack_probability=0.3, 
        seed=i
    )
    properties = agent.get_framework_properties()
    print(f"Framework {i}: {properties['num_arguments']} args, cycles: {properties['has_cycles']}")
```

### Comparaison agent standard vs amélioré
```python
from enhanced_agent import EnhancedDungAgent

# Cas problématique : self-attack
standard_agent = DungAgent()
enhanced_agent = EnhancedDungAgent()

for agent in [standard_agent, enhanced_agent]:
    agent.add_argument("a")
    agent.add_argument("b")
    agent.add_attack("a", "a")  # Self-attack
    agent.add_attack("a", "b")

print("Standard:", standard_agent.get_grounded_extension())
print("Amélioré:", enhanced_agent.get_grounded_extension())
```

## 🧪 Tests et Validation

### Tests de base
```bash
python test_agent.py
```

### Tests avancés (frameworks complexes)
```bash
python advanced_tests.py
```

### Benchmark de performance
```bash
python benchmark.py
```

### Validation complète
```bash
# Script qui exécute tous les tests et validations
python validate_project.py
```

## 🎯 Démonstrations

### Démonstration interactive
```bash
# Présentation guidée de toutes les fonctionnalités
python demo_interactive.py
```

### Notebook Jupyter
Ouvrez `demo.ipynb` pour une démonstration détaillée avec visualisations.

### Exemples via CLI
```bash
# Lister tous les exemples disponibles
python cli.py examples --list

# Exécuter un exemple spécifique
python cli.py examples --run triangle

# Créer un framework interactivement
python cli.py create --enhanced
```

## 🛠️ Scripts utilitaires

| Script | Description | Usage |
|--------|-------------|-------|
| `validate_project.py` | Validation complète | `python validate_project.py` |
| `demo_interactive.py` | Démonstration guidée | `python demo_interactive.py` |
| `benchmark.py` | Tests de performance | `python benchmark.py` |
| `project_info.py` | Informations détaillées | `python project_info.py` |
| `cli.py` | Interface ligne de commande | `python cli.py --help` |

## 📈 Résultats de tests récents

✅ **Tests avancés** : 11/11 réussis  
✅ **Cohérence sémantique** : 100%  
✅ **Performance** : Passage à l'échelle jusqu'à 16+ arguments  
✅ **Agent amélioré** : 12/15 corrections détectées  

## 🎨 Formats d'export étendus

| Format | Extension | Usage | Outil compatible |
|--------|-----------|-------|------------------|
| **JSON** | `.json` | Format principal | Universel |
| **TGF** | `.tgf` | Graphes simples | Gephi, yEd |
| **DOT** | `.dot` | Rendu professionnel | GraphViz |
| **Analyse** | `.json` | Rapports complets | Analyse statistique |

## 🏆 Points forts du projet

- ✅ **Complétude** : Toutes les sémantiques d'argumentation standard
- ✅ **Performance** : Cache optimisé, passage à l'échelle
- ✅ **Robustesse** : Tests exhaustifs, gestion des cas limites
- ✅ **Utilisabilité** : CLI intuitive, démonstrations interactives
- ✅ **Extensibilité** : Architecture modulaire, formats multiples
- ✅ **Qualité** : Documentation complète, validation automatique

## 🎯 Cas d'usage

1. **Recherche académique** : Validation d'algorithmes d'argumentation
2. **Enseignement** : Illustration des concepts d'argumentation formelle
3. **Développement** : Base pour applications d'argumentation
4. **Analyse** : Étude de débats structurés
5. **Benchmarking** : Tests de performance d'implémentations

## 🚀 Pour commencer

```bash
# 1. Validation rapide
python validate_project.py

# 2. Démonstration interactive
python demo_interactive.py

# 3. Premier framework
python cli.py create

# 4. Analyse d'exemples
python cli.py examples
```
