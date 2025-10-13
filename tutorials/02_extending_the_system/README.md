# 📗 Extending the System

## Description

Ce répertoire contient les tutoriels avancés pour étendre et personnaliser le système d'analyse argumentative. Ces tutoriels s'adressent aux développeurs qui souhaitent enrichir le système avec leurs propres agents, outils d'analyse, ou fonctionnalités personnalisées.

**Prérequis** : Avoir complété tous les tutoriels [Getting Started](../01_getting_started/)

## Contenu

### Tutoriels

| # | Tutoriel | Durée | Niveau |
|---|----------|-------|--------|
| **[01](./01_adding_an_agent.md)** | Ajout d'un nouvel agent spécialiste | 90 min | Avancé |
| **[02](./02_extending_tools.md)** | Extension des outils d'analyse | 120 min | Avancé |

## Parcours d'Apprentissage

### 🔧 Tutoriel 01 : Ajout d'un Agent

**Objectif** : Concevoir, implémenter et intégrer un nouvel agent dans l'architecture hiérarchique

**Ce que vous apprendrez** :
- Architecture des agents dans le système
- Conception d'un nouvel agent spécialiste
- Implémentation de l'interface `BaseAgent`
- Intégration avec l'orchestrateur hiérarchique
- Tests et validation de l'agent
- Bonnes pratiques de développement d'agents

**Durée estimée** : 90 minutes

**Prérequis** :
- Tutoriels Getting Started complétés
- Connaissance de Python avancé (async/await, POO)
- Compréhension de l'architecture hiérarchique

```bash
# Suivre le tutoriel
code tutorials/02_extending_the_system/01_adding_an_agent.md
```

**Structure d'un Agent** :
```python
class BaseAgent:
    def __init__(self, config):
        self.config = config
    
    async def analyze(self, text, context):
        """Méthode principale d'analyse"""
        raise NotImplementedError
    
    def get_results(self):
        """Récupération des résultats formatés"""
        raise NotImplementedError
```

### 🛠️ Tutoriel 02 : Extension des Outils

**Objectif** : Développer et intégrer de nouveaux outils d'analyse rhétorique personnalisés

**Ce que vous apprendrez** :
- Architecture des outils d'analyse
- Création d'un nouvel outil d'analyse
- Intégration avec les agents existants
- Gestion des dépendances entre outils
- Optimisation des performances
- Tests unitaires et d'intégration
- Documentation des outils

**Durée estimée** : 120 minutes

**Prérequis** :
- Tutoriel 01 (Ajout d'agent) complété
- Connaissance Python intermédiaire à avancée
- Compréhension des patterns de design

```bash
# Suivre le tutoriel
code tutorials/02_extending_the_system/02_extending_tools.md
```

## Points de Validation

À l'issue de ce parcours Extending the System, vous devriez être capable de :

- ✅ Concevoir un nouvel agent spécialiste
- ✅ Implémenter l'interface BaseAgent correctement
- ✅ Intégrer un agent dans l'orchestrateur hiérarchique
- ✅ Développer des outils d'analyse personnalisés
- ✅ Optimiser les performances de vos extensions
- ✅ Écrire des tests pour vos agents et outils
- ✅ Documenter vos extensions
- ✅ Contribuer au projet de manière professionnelle

## Architecture du Système

### Hiérarchie des Agents

```
Orchestrateur Principal
├── Agent Coordinateur (Niveau 2)
│   ├── Agent Spécialiste 1 (Niveau 3)
│   ├── Agent Spécialiste 2 (Niveau 3)
│   └── Votre Nouvel Agent (Niveau 3) ← Vous êtes ici !
└── Agent Coordinateur (Niveau 2)
    └── Autres agents...
```

### Cycle de Vie d'un Agent

1. **Initialisation** : Configuration et chargement des ressources
2. **Analyse** : Traitement asynchrone du texte
3. **Agrégation** : Fusion avec résultats d'autres agents
4. **Validation** : Vérification de la cohérence
5. **Export** : Formatage des résultats

## Exemples de Projets

### Projet 1 : Agent de Détection de Biais

Créer un agent spécialisé dans la détection de biais cognitifs :

```python
class BiasDetectionAgent(BaseAgent):
    """Agent de détection de biais cognitifs"""
    
    BIAS_TYPES = [
        "confirmation_bias",
        "anchoring_bias",
        "availability_bias",
        # ...
    ]
    
    async def analyze(self, text, context):
        """Détecte les biais dans le texte"""
        biases = []
        for bias_type in self.BIAS_TYPES:
            if self._detect_bias(text, bias_type):
                biases.append({
                    "type": bias_type,
                    "confidence": self._compute_confidence(text, bias_type)
                })
        return biases
```

### Projet 2 : Outil d'Analyse Émotionnelle

Développer un outil d'analyse du ton émotionnel :

```python
class EmotionalToneAnalyzer:
    """Analyse le ton émotionnel d'un texte"""
    
    def analyze_tone(self, text):
        """Retourne le ton dominant et son intensité"""
        emotions = self._extract_emotions(text)
        dominant = max(emotions, key=emotions.get)
        return {
            "dominant_emotion": dominant,
            "intensity": emotions[dominant],
            "emotional_spectrum": emotions
        }
```

## Ressources pour Développeurs

### Documentation Technique

- **[Architecture du Système](../../docs/architecture/)** : Schémas et diagrammes
- **[API Reference](../../docs/api/)** : Documentation des classes et méthodes
- **[Design Patterns](../../docs/patterns/)** : Patterns utilisés dans le projet

### Exemples de Code

- **[Plugins](../../examples/04_plugins/)** : Exemples de plugins fonctionnels
- **[Core System Demos](../../examples/02_core_system_demos/)** : Démos système central
- **[Tests](../../tests/)** : Suite de tests pour inspiration

### Outils de Développement

- **[Debugging Tools](../../demos/debugging/)** : Outils de débogage
- **[Validation Tools](../../demos/validation/)** : Scripts de validation
- **[Integration Tests](../../demos/integration/)** : Tests d'intégration

## Bonnes Pratiques

### 🎯 Design

1. **Single Responsibility** : Un agent = une responsabilité
2. **Dependency Injection** : Injecter les dépendances via config
3. **Interface Segregation** : Interfaces minimales et ciblées
4. **Async-First** : Privilégier les méthodes asynchrones

### 🧪 Tests

1. **Unit Tests** : Tester chaque méthode isolément
2. **Integration Tests** : Tester l'intégration avec le système
3. **Performance Tests** : Mesurer l'impact sur les performances
4. **Edge Cases** : Tester les cas limites

### 📝 Documentation

1. **Docstrings** : Documenter toutes les classes et méthodes
2. **Type Hints** : Utiliser les annotations de types
3. **Examples** : Fournir des exemples d'usage
4. **README** : Créer un README pour votre extension

## Workflow de Contribution

### 1. Planification

```bash
# 1. Créer une issue pour discuter de votre extension
# GitHub Issues > New Issue > Proposition d'extension

# 2. Obtenir feedback de la communauté
```

### 2. Développement

```bash
# 1. Créer une branche
git checkout -b feature/mon-nouvel-agent

# 2. Implémenter votre extension
# Suivre les tutoriels de ce répertoire

# 3. Écrire les tests
pytest tests/test_mon_agent.py

# 4. Valider le style de code
black mon_agent.py
pylint mon_agent.py
```

### 3. Documentation

```bash
# 1. Documenter votre code
# Docstrings, type hints, commentaires

# 2. Créer un README
# Voir template ci-dessous

# 3. Mettre à jour la documentation principale
```

### 4. Soumission

```bash
# 1. Commit et push
git add .
git commit -m "feat(agents): Ajout agent détection de biais"
git push origin feature/mon-nouvel-agent

# 2. Créer une Pull Request
# GitHub > Pull Requests > New Pull Request

# 3. Adresser les retours de la review
```

## Template README pour Extensions

```markdown
# [Nom de votre Extension]

## Description
[Description courte et claire]

## Fonctionnalités
- Fonctionnalité 1
- Fonctionnalité 2

## Installation
```bash
# Instructions d'installation si nécessaire
```

## Utilisation
```python
# Exemple d'utilisation
```

## Configuration
[Paramètres configurables]

## Limitations Connues
[Limitations ou restrictions]

## TODO
- [ ] Amélioration 1
- [ ] Amélioration 2

## Auteur
[Votre nom] - [Date]
```

## Support Avancé

### Besoin d'Aide ?

1. **Discord/Slack de la communauté** : Poser vos questions techniques
2. **GitHub Discussions** : Discussions sur l'architecture et design
3. **Stack Overflow** : Tag `intelligence-symbolique`
4. **Email d'équipe** : Pour questions confidentielles

### Mentoring

Des développeurs expérimentés sont disponibles pour :
- Réviser votre code
- Conseiller sur l'architecture
- Aider avec des problèmes complexes

## Progression Suggérée

```
Niveau Avancé
├─ 🔧 Tutoriel 01: Ajout Agent         [90 min] ✓
└─ 🛠️ Tutoriel 02: Extension Outils    [120 min] ✓
                                        
📈 Total: ~3h30                         
                                        
Prochaines étapes                       
├─ 💡 Développer votre premier plugin  
├─ 🤝 Contribuer au projet              
└─ 🎓 Devenir mainteneur                
```

## Certification

Après avoir complété ce parcours :
- ✅ Vous êtes qualifié pour contribuer au projet
- ✅ Vous pouvez développer des plugins professionnels
- ✅ Vous comprenez l'architecture interne du système
- ✅ Vous êtes prêt à devenir mainteneur

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA  
**Niveau** : Avancé  
**Durée totale** : ~3h30