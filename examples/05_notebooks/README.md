# 📓 Notebooks

## Description

Ce répertoire contient des notebooks Jupyter interactifs pour l'apprentissage et l'exploration du système d'argumentation. Les notebooks offrent une approche hands-on avec exécution de code en temps réel, visualisations, et explications intégrées.

## Contenu

### Notebooks Disponibles

| Notebook | Description | Niveau | Cellules |
|----------|-------------|--------|----------|
| **[api_logic_tutorial.ipynb](./api_logic_tutorial.ipynb)** | Tutoriel complet sur l'API des agents logiques | Intermédiaire | 430 lignes |
| **[logic_agents_tutorial.ipynb](./logic_agents_tutorial.ipynb)** | Guide pratique des agents logiques | Débutant | 176 lignes |

## 📚 logic_agents_tutorial.ipynb

**Objectif** : Introduction pratique aux agents logiques du système

### Contenu

1. **Introduction**
   - Qu'est-ce qu'un agent logique ?
   - Architecture des agents
   - Cas d'usage

2. **Configuration**
   - Installation des dépendances
   - Import des modules
   - Configuration de l'environnement

3. **Premiers Pas**
   - Créer un agent simple
   - Exécuter une analyse
   - Interpréter les résultats

4. **Exemples Pratiques**
   - Logique propositionnelle
   - Logique des prédicats
   - Inférence automatique

5. **Exercices**
   - Exercices guidés
   - Solutions commentées

### Prérequis

- Python 3.8+
- Jupyter Notebook ou JupyterLab
- Connaissance de base en logique
- Tutoriels Getting Started complétés

### Utilisation

```bash
# Installer Jupyter
pip install jupyter

# Lancer Jupyter
jupyter notebook

# Ou JupyterLab
jupyter lab

# Naviguer vers examples/05_notebooks/
# Ouvrir logic_agents_tutorial.ipynb
```

### Ce Que Vous Apprendrez

- ✅ Concepts fondamentaux des agents logiques
- ✅ Utilisation de l'API des agents
- ✅ Résolution de problèmes logiques
- ✅ Debugging et optimisation
- ✅ Bonnes pratiques

**📖 [Ouvrir le notebook](./logic_agents_tutorial.ipynb)**

## 🔧 api_logic_tutorial.ipynb

**Objectif** : Maîtriser l'API complète des agents logiques

### Contenu

1. **Vue d'Ensemble de l'API**
   - Architecture modulaire
   - Classes principales
   - Méthodes essentielles

2. **Configuration Avancée**
   - Paramètres de configuration
   - Optimisation des performances
   - Gestion des ressources

3. **Agents Logiques**
   - PropositionalAgent
   - PredicateAgent
   - ModalAgent
   - CustomAgent

4. **Workflows Complets**
   - Pipeline d'analyse
   - Agrégation de résultats
   - Export et visualisation

5. **Cas d'Usage Avancés**
   - Raisonnement par contraintes
   - Planification automatique
   - Vérification formelle

6. **Intégration**
   - API REST
   - Microservices
   - Async/await

7. **Performance**
   - Benchmarking
   - Optimisation
   - Caching

### Prérequis

- Python 3.8+
- Jupyter Notebook/Lab
- Connaissance intermédiaire en programmation
- logic_agents_tutorial.ipynb complété
- Tutoriels Extending the System recommandés

### Utilisation

```bash
# Installation avec dépendances complètes
pip install jupyter matplotlib pandas numpy

# Lancer le notebook
jupyter notebook api_logic_tutorial.ipynb
```

### Ce Que Vous Apprendrez

- ✅ API complète des agents logiques
- ✅ Patterns d'utilisation avancés
- ✅ Intégration dans applications
- ✅ Optimisation des performances
- ✅ Debugging avancé
- ✅ Tests et validation

**📖 [Ouvrir le notebook](./api_logic_tutorial.ipynb)**

## Parcours d'Apprentissage

### Pour Débutants

**Parcours recommandé** :

1. **[Tutoriels Getting Started](../../tutorials/01_getting_started/)** (2h)
   - Comprendre les bases du système

2. **[logic_agents_tutorial.ipynb](./logic_agents_tutorial.ipynb)** (1h30)
   - Introduction interactive aux agents
   - Exercices pratiques

3. **[Exemples Logic & Riddles](../01_logic_and_riddles/)** (1h)
   - Appliquer les concepts sur des cas réels

**Total** : ~4h30

### Pour Développeurs

**Parcours recommandé** :

1. **[logic_agents_tutorial.ipynb](./logic_agents_tutorial.ipynb)** (1h)
   - Révision rapide des concepts

2. **[api_logic_tutorial.ipynb](./api_logic_tutorial.ipynb)** (2h30)
   - Maîtrise de l'API complète
   - Cas d'usage avancés

3. **[Tutoriels Extending System](../../tutorials/02_extending_the_system/)** (3h)
   - Développement d'extensions

4. **[Plugins](../04_plugins/)** (1h)
   - Architecture modulaire

**Total** : ~7h30

## Fonctionnalités Jupyter

### Cellules Interactives

Les notebooks utilisent des cellules interactives pour :

```python
# Exemple de cellule interactive
from ipywidgets import interact, widgets

@interact(threshold=widgets.FloatSlider(min=0, max=1, step=0.1, value=0.5))
def analyze_with_threshold(threshold):
    """Analyse interactive avec seuil ajustable"""
    result = agent.analyze(text, threshold=threshold)
    display(result)
```

### Visualisations

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Visualiser les résultats
plt.figure(figsize=(10, 6))
sns.barplot(x='fallacy_type', y='confidence', data=results)
plt.title('Sophismes Détectés par Confiance')
plt.xticks(rotation=45)
plt.show()
```

### Markdown & LaTeX

Les notebooks supportent le formatage riche :

```markdown
## Titre de Section

Explication avec **gras** et *italique*.

Formules mathématiques :
$$P(A|B) = \frac{P(B|A) \cdot P(A)}{P(B)}$$

- Liste 1
- Liste 2
```

## Configuration de l'Environnement

### Installation Minimale

```bash
pip install jupyter
```

### Installation Complète

```bash
pip install jupyter jupyterlab ipywidgets matplotlib seaborn pandas numpy
```

### Extensions Recommandées

```bash
# Extensions JupyterLab
jupyter labextension install @jupyter-widgets/jupyterlab-manager
jupyter labextension install @jupyterlab/toc

# Extensions Notebook
jupyter nbextension enable --py widgetsnbextension
```

### Configuration

Créer `~/.jupyter/jupyter_notebook_config.py` :

```python
# Configuration Jupyter
c.NotebookApp.open_browser = True
c.NotebookApp.port = 8888
c.NotebookApp.notebook_dir = './examples/05_notebooks'
```

## Exportation

### Vers HTML

```bash
# Export notebook vers HTML
jupyter nbconvert --to html logic_agents_tutorial.ipynb
```

### Vers PDF

```bash
# Export vers PDF (nécessite pandoc et LaTeX)
jupyter nbconvert --to pdf api_logic_tutorial.ipynb
```

### Vers Python

```bash
# Extraire le code Python
jupyter nbconvert --to python logic_agents_tutorial.ipynb
```

### Vers Slides

```bash
# Créer une présentation
jupyter nbconvert --to slides api_logic_tutorial.ipynb --post serve
```

## Bonnes Pratiques

### Structure du Notebook

```
1. Titre et Description
   - Objectifs
   - Prérequis
   - Durée estimée

2. Configuration
   - Imports
   - Constants
   - Helper functions

3. Contenu Principal
   - Sections logiques
   - Explications + Code + Résultats

4. Exercices
   - Problèmes à résoudre
   - Solutions

5. Conclusion
   - Récapitulatif
   - Ressources supplémentaires
```

### Qualité du Code

```python
# ✅ Bon : Code clair et commenté
def analyze_text(text: str, threshold: float = 0.5) -> dict:
    """
    Analyse un texte pour détecter des sophismes.
    
    Args:
        text: Le texte à analyser
        threshold: Seuil de confiance (0-1)
        
    Returns:
        Résultats de l'analyse
    """
    # Implémentation
    pass

# ❌ Mauvais : Code non documenté
def a(t,th=0.5):
    # ???
    pass
```

### Visualisations

```python
# ✅ Bon : Visualisation claire et informative
plt.figure(figsize=(12, 6))
plt.subplot(1, 2, 1)
plt.hist(confidences, bins=20, edgecolor='black')
plt.title('Distribution des Confiances')
plt.xlabel('Confiance')
plt.ylabel('Fréquence')

plt.subplot(1, 2, 2)
plt.pie(fallacy_counts, labels=fallacy_types, autopct='%1.1f%%')
plt.title('Répartition des Sophismes')
plt.tight_layout()
plt.show()
```

## Debugging

### Mode Debug

```python
# Activer le mode verbose
import logging
logging.basicConfig(level=logging.DEBUG)

# Afficher les variables intermédiaires
from IPython.display import display
display(intermediate_result)
```

### Profiling

```python
# Profiler une cellule
%%timeit
result = agent.analyze(text)

# Profiling détaillé
%prun agent.analyze(text)
```

### Magic Commands

```python
# Lister les variables
%whos

# Historique des commandes
%history

# Charger un script externe
%load external_script.py

# Exécuter un script
%run script.py
```

## Collaboration

### Partage

1. **GitHub** : Versionner vos notebooks
2. **nbviewer** : Partager en lecture seule
3. **Binder** : Créer un environnement exécutable
4. **Google Colab** : Collaboration en temps réel

### Version Control

```bash
# Nettoyer les outputs avant commit
jupyter nbconvert --clear-output --inplace *.ipynb

# Utiliser nbdime pour diff
pip install nbdime
nbdiff notebook1.ipynb notebook2.ipynb
```

## Ressources Complémentaires

### Apprentissage

- **[Tutoriels](../../tutorials/)** : Guides structurés
- **[Exemples](../)** : Code réutilisable
- **[Demos](../../demos/)** : Cas d'usage complets

### Jupyter

- **[Documentation Jupyter](https://jupyter.org/documentation)**
- **[JupyterLab Guide](https://jupyterlab.readthedocs.io/)**
- **[Jupyter Widgets](https://ipywidgets.readthedocs.io/)**

### Visualisation

- **[Matplotlib Gallery](https://matplotlib.org/stable/gallery/)**
- **[Seaborn Tutorial](https://seaborn.pydata.org/tutorial.html)**
- **[Plotly Express](https://plotly.com/python/plotly-express/)**

## Contribution

### Créer un Nouveau Notebook

1. **Structure** : Suivre le template standard
2. **Contenu** : Explications + Code + Visualisations
3. **Exercices** : Inclure des exercices pratiques
4. **Test** : Vérifier toutes les cellules
5. **Documentation** : Ajouter dans ce README

### Template

```python
# Nouveau Notebook: mon_tutorial.ipynb

"""
# Titre du Tutoriel

## Objectifs
- Objectif 1
- Objectif 2

## Prérequis
- Prérequis 1
- Prérequis 2
"""

# Configuration
import sys
sys.path.append('../..')

# Contenu principal
# ...

# Exercices
"""
## Exercices

### Exercice 1
[Description]
"""

# Solutions
"""
### Solution 1
[Code solution]
"""
```

### Checklist

- [ ] Titre et description clairs
- [ ] Objectifs d'apprentissage définis
- [ ] Cellules bien organisées
- [ ] Code testé et fonctionnel
- [ ] Visualisations informatives
- [ ] Exercices avec solutions
- [ ] Documentation dans README
- [ ] Outputs nettoyés avant commit

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA  
**Niveau** : Débutant à Intermédiaire  
**Technologies** : Jupyter, Python, Matplotlib, ipywidgets