# 📊 Logic and Riddles

## Description

Ce répertoire contient des exemples de logique formelle et de résolution d'énigmes utilisant le raisonnement déductif et abductif. Ces exemples démontrent l'application de la logique au raisonnement automatisé et à la résolution de problèmes complexes.

## Contenu

### Sous-Répertoires

| Répertoire | Description | Complexité | Fichiers Clés |
|------------|-------------|------------|---------------|
| **[cluedo_demo/](./cluedo_demo/)** | Résolution du jeu Cluedo par raisonnement logique | Intermédiaire | README_CLUEDO_DEMO.md |
| **[Sherlock_Watson/](./Sherlock_Watson/)** | Enquêtes inspirées de Sherlock Holmes avec agents logiques | Avancé | agents_logiques_production.py, README.md |

## 🎯 Cluedo Demo

**Objectif** : Résoudre le jeu Cluedo en utilisant la logique déductive et l'élimination

### Concepts Clés

- **Déduction logique** : Inférer des conclusions à partir de faits connus
- **Élimination progressive** : Réduire l'espace de solutions
- **Raisonnement par contraintes** : Gérer les contraintes du jeu
- **Inférence automatique** : Automatiser le processus de déduction

### Utilisation

```bash
# Naviguer vers le répertoire
cd examples/01_logic_and_riddles/cluedo_demo

# Consulter la documentation
code README_CLUEDO_DEMO.md

# Exécuter la démo (si script disponible)
python cluedo_solver.py
```

### Ce Que Vous Apprendrez

- ✅ Modéliser un problème en logique formelle
- ✅ Implémenter un solveur de contraintes
- ✅ Utiliser la déduction pour éliminer des possibilités
- ✅ Optimiser la recherche dans un espace de solutions

**📖 [Documentation détaillée](./cluedo_demo/README_CLUEDO_DEMO.md)**

## 🔍 Sherlock Watson

**Objectif** : Résoudre des enquêtes complexes en utilisant des agents logiques et le raisonnement abductif

### Architecture

Le système utilise des **agents logiques de production** qui :
- Analysent les indices et témoignages
- Construisent des chaînes de raisonnement
- Éliminent les hypothèses incompatibles
- Convergent vers la solution

### Scénarios Disponibles

| Scénario | Fichier | Description | Niveau |
|----------|---------|-------------|--------|
| **Cluedo** | [`cluedo_scenario.json`](./Sherlock_Watson/cluedo_scenario.json) | Résolution du jeu classique | Intermédiaire |
| **Einstein** | [`einstein_scenario.json`](./Sherlock_Watson/einstein_scenario.json) | Énigme d'Einstein (maisons) | Avancé |

### Fichiers Principaux

| Fichier | Description | Lignes |
|---------|-------------|--------|
| [`agents_logiques_production.py`](./Sherlock_Watson/agents_logiques_production.py) | Implémentation des agents logiques (698 lignes) | 698 |
| [`README.md`](./Sherlock_Watson/README.md) | Documentation complète du système (472 lignes) | 472 |
| `cluedo_scenario.json` | Données du scénario Cluedo | 18 |
| `einstein_scenario.json` | Données de l'énigme d'Einstein | 18 |

### Utilisation

```bash
# Naviguer vers le répertoire
cd examples/01_logic_and_riddles/Sherlock_Watson

# Résoudre le scénario Cluedo
python agents_logiques_production.py --scenario cluedo_scenario.json

# Résoudre l'énigme d'Einstein
python agents_logiques_production.py --scenario einstein_scenario.json

# Mode interactif
python agents_logiques_production.py --interactive
```

### Ce Que Vous Apprendrez

- ✅ Implémenter des agents logiques de production
- ✅ Utiliser le raisonnement abductif (hypothèses → faits)
- ✅ Gérer des systèmes de règles complexes
- ✅ Construire des chaînes de raisonnement
- ✅ Optimiser la recherche dans un graphe de possibilités

**📖 [Documentation détaillée](./Sherlock_Watson/README.md)**

## Concepts Théoriques

### Raisonnement Déductif vs Abductif

| Type | Description | Exemple | Utilisation |
|------|-------------|---------|-------------|
| **Déductif** | Général → Spécifique | Tous les humains sont mortels. Socrate est humain. → Socrate est mortel. | Cluedo Demo |
| **Abductif** | Observation → Meilleure explication | Le sol est mouillé. → Il a probablement plu. | Sherlock Watson |

### Logique Propositionnelle

```python
# Exemple de règle logique
if suspect_in_room and weapon_available and no_alibi:
    suspect_is_guilty = True
```

### Systèmes à Base de Règles

```python
# Exemple de système de production
class ProductionRule:
    def __init__(self, condition, action):
        self.condition = condition
        self.action = action
    
    def evaluate(self, facts):
        if self.condition(facts):
            return self.action(facts)
```

## Cas d'Usage

### Pour les Étudiants

Comprendre les bases de la logique formelle :

1. **Commencez par Cluedo** : Logique simple, problème bien défini
2. **Passez à Sherlock Watson** : Raisonnement plus complexe
3. **Expérimentez** : Créez vos propres scénarios
4. **Comparez** : Déduction vs abduction

### Pour les Chercheurs

Explorer les techniques de raisonnement automatisé :

1. **Analysez l'implémentation** : Étudiez les agents logiques
2. **Mesurez les performances** : Temps de résolution, complexité
3. **Optimisez** : Améliorez les algorithmes
4. **Étendez** : Ajoutez de nouveaux types de règles

### Pour les Développeurs

Intégrer le raisonnement logique dans vos applications :

1. **Réutilisez le code** : Les agents sont modulaires
2. **Adaptez les scénarios** : JSON facilement modifiable
3. **Intégrez** : Utilisez comme bibliothèque
4. **Testez** : Suite de tests incluse

## Exercices Pratiques

### Niveau Débutant

1. **Modifier un scénario Cluedo**
   - Changer les suspects, armes, lieux
   - Ajouter de nouvelles contraintes

2. **Tracer l'exécution**
   - Ajouter des logs pour suivre le raisonnement
   - Visualiser la chaîne de déduction

### Niveau Intermédiaire

3. **Créer un nouveau scénario**
   - Inventer une énigme originale
   - Définir les règles logiques
   - Tester la résolution

4. **Optimiser la recherche**
   - Implémenter des heuristiques
   - Mesurer l'amélioration des performances

### Niveau Avancé

5. **Ajouter un nouveau type de raisonnement**
   - Raisonnement inductif
   - Logique floue
   - Logique temporelle

6. **Interfacer avec un LLM**
   - Générer des scénarios via GPT
   - Expliquer le raisonnement en langage naturel
   - Valider les solutions par argumentation

## Ressources Complémentaires

### Théorie

- **Logique propositionnelle** : [Wikipedia](https://fr.wikipedia.org/wiki/Calcul_des_propositions)
- **Logique des prédicats** : [Stanford Encyclopedia](https://plato.stanford.edu/entries/logic-classical/)
- **Systèmes experts** : [Introduction aux SE](https://www.cairn.info)

### Outils

- **PyDatalog** : Logique Datalog en Python
- **Z3 Solver** : Solveur SAT/SMT puissant
- **Prolog** : Langage de programmation logique

### Livres Recommandés

- "Artificial Intelligence: A Modern Approach" (Russell & Norvig)
- "Logic for Computer Science" (Huth & Ryan)
- "Automated Reasoning" (Gallier)

## Contribution

### Ajouter un Nouveau Scénario

1. **Créer le fichier JSON**
   ```json
   {
     "name": "Votre Scénario",
     "suspects": ["Alice", "Bob"],
     "weapons": ["Revolver"],
     "locations": ["Salon"],
     "clues": [
       {"type": "witness", "content": "..."}
     ]
   }
   ```

2. **Tester la résolution**
   ```bash
   python agents_logiques_production.py --scenario votre_scenario.json
   ```

3. **Documenter**
   - Expliquer la logique du scénario
   - Fournir la solution attendue
   - Indiquer la difficulté

### Améliorer les Agents

1. **Identifier une limitation**
2. **Proposer une amélioration**
3. **Implémenter et tester**
4. **Soumettre une PR avec benchmarks**

## Performance

### Métriques Typiques

| Scénario | Temps de résolution | Règles évaluées | Mémoire |
|----------|---------------------|-----------------|---------|
| Cluedo Simple | < 1 seconde | ~50 | < 10 MB |
| Einstein | 2-5 secondes | ~200 | ~20 MB |
| Scénario Custom | Variable | Variable | Variable |

### Optimisations Possibles

- 🔸 **Indexation des règles** : Accès O(1) au lieu de O(n)
- 🔸 **Memoization** : Cache des résultats intermédiaires
- 🔸 **Parallel evaluation** : Évaluer plusieurs branches en parallèle
- 🔸 **Pruning** : Éliminer les branches impossibles plus tôt

## Ressources Connexes

- **[Core System Demos](../02_core_system_demos/)** : Intégration système
- **[Plugins](../04_plugins/)** : Architecture extensible
- **[Notebooks](../05_notebooks/)** : Tutoriels interactifs
- **[Documentation](../../docs/)** : Référence complète

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA  
**Niveau** : Intermédiaire à Avancé  
**Technologies** : Python, Logique Formelle, Systèmes à Base de Règles