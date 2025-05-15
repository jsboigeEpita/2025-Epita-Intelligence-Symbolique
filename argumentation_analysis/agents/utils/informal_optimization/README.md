# 🔍 Optimisation de l'Agent Informel (`agents/utils/informal_optimization/`)

Ce module fournit des outils pour analyser et améliorer les performances de l'agent d'analyse informelle, en optimisant sa taxonomie de sophismes et ses prompts.

[Retour au README Agents](../../README.md)

## Objectif 🎯

L'optimisation de l'agent informel vise à :
1. Analyser l'utilisation de la taxonomie des sophismes
2. Identifier les points faibles dans les prompts et définitions
3. Proposer et implémenter des améliorations
4. Mesurer l'impact des modifications
5. Documenter les changements et leurs effets

## Contenu 📁

* **[`analyze_taxonomy_usage.py`](./analyze_taxonomy_usage.py)** : Script d'analyse de l'utilisation de la taxonomie des sophismes.
* **[`improve_informal_agent.py`](./improve_informal_agent.py)** : Script d'amélioration des performances de l'agent informel.
* **[`optimize_informal_agent.py`](./optimize_informal_agent.py)** : Script d'optimisation des prompts et définitions de l'agent informel.
* **[`documentation.md`](./documentation.md)** : Documentation détaillée sur l'optimisation de l'agent informel.
* **[`backups/`](./backups/)** : Sauvegardes des fichiers avant modification.
  * Contient des versions datées des fichiers `informal_definitions.py` et `prompts.py`.
* **[`taxonomy_analysis/`](./taxonomy_analysis/)** : Visualisations et analyses de la taxonomie des sophismes.
  * **[`children_per_parent.png`](./taxonomy_analysis/children_per_parent.png)** : Graphique du nombre d'enfants par parent dans la taxonomie.
  * **[`depth_distribution.png`](./taxonomy_analysis/depth_distribution.png)** : Distribution des profondeurs dans la taxonomie.
  * **[`rapport_analyse_taxonomie.md`](./taxonomy_analysis/rapport_analyse_taxonomie.md)** : Rapport détaillé sur l'analyse de la taxonomie.

## Utilisation 🚀

### Analyse de la taxonomie

Pour analyser l'utilisation de la taxonomie des sophismes :

```python
from agents.utils.informal_optimization.analyze_taxonomy_usage import analyze_taxonomy

# Analyser la taxonomie
results = analyze_taxonomy()

# Afficher les résultats
print(f"Nombre total de sophismes : {results['total_fallacies']}")
print(f"Profondeur maximale : {results['max_depth']}")
print(f"Sophismes les plus utilisés : {results['most_used_fallacies']}")
```

### Optimisation des prompts

Pour optimiser les prompts de l'agent informel :

```python
import asyncio
from agents.utils.informal_optimization.optimize_informal_agent import optimize_prompts

async def run_optimization():
    # Optimiser les prompts
    new_prompts = await optimize_prompts()
    
    # Sauvegarder les nouveaux prompts
    print(f"Nouveaux prompts générés : {len(new_prompts)} modifications")

# Exécuter l'optimisation
asyncio.run(run_optimization())
```

### Amélioration de l'agent

Pour améliorer les performances de l'agent informel :

```python
import asyncio
from agents.utils.informal_optimization.improve_informal_agent import improve_agent

async def run_improvement():
    # Améliorer l'agent
    results = await improve_agent()
    
    # Afficher les résultats
    print(f"Améliorations apportées : {results['improvements']}")
    print(f"Performance avant : {results['before_performance']}")
    print(f"Performance après : {results['after_performance']}")

# Exécuter l'amélioration
asyncio.run(run_improvement())
```

## Fonctionnalités 🛠️

### Analyse de la taxonomie

- Calcul de statistiques sur la taxonomie (profondeur, largeur, distribution)
- Visualisation de la structure hiérarchique
- Identification des sophismes sous-utilisés ou sur-utilisés
- Détection des incohérences dans la taxonomie

### Optimisation des prompts

- Analyse des prompts existants
- Génération de suggestions d'amélioration
- Test A/B des différentes versions de prompts
- Sauvegarde automatique des versions précédentes

### Amélioration de l'agent

- Évaluation des performances sur un corpus de test
- Identification des points faibles
- Implémentation d'améliorations ciblées
- Mesure de l'impact des modifications

## Résultats d'analyse 📊

L'analyse de la taxonomie des sophismes a révélé plusieurs points d'amélioration :

1. **Distribution déséquilibrée** : Certaines catégories de sophismes sont sur-représentées
2. **Profondeur variable** : La profondeur de la taxonomie varie considérablement selon les branches
3. **Utilisation inégale** : Certains sophismes sont rarement utilisés par l'agent
4. **Chevauchement conceptuel** : Certains sophismes ont des définitions qui se chevauchent

Ces observations ont guidé les optimisations apportées à l'agent informel.

## Bonnes pratiques

- Créez toujours une sauvegarde avant de modifier les fichiers
- Documentez les modifications apportées et leur justification
- Testez les changements sur un corpus représentatif
- Mesurez l'impact des modifications sur les performances
- Maintenez à jour la documentation sur l'optimisation