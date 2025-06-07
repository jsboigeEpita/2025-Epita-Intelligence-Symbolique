# Scripts de Démonstration - Intelligence Symbolique EPITA

Ce répertoire contient des scripts Python conçus pour démontrer les fonctionnalités du projet d'analyse argumentative et d'intelligence symbolique, avec un focus particulier sur l'apprentissage pédagogique pour les étudiants EPITA.

## 🚀 Script Principal : `demonstration_epita.py` (VERSION ENRICHIE)

### **Nouvelle Version 720+ lignes avec 4 Modes d'Utilisation**

Le script principal `demonstration_epita.py` a été complètement enrichi avec des fonctionnalités pédagogiques avancées :

- **4 modes d'utilisation** adaptés aux différents besoins
- **Interface interactive colorée** avec quiz et pauses explicatives
- **Système de progression visuelle** avec barres de progression
- **Templates de projets** organisés par niveau de difficulté
- **Dashboard de métriques** en temps réel

### Modes Disponibles

| Mode | Commande | Usage Recommandé |
|------|----------|------------------|
| **Normal** | `python demonstration_epita.py` | Démonstration classique complète |
| **Interactif** | `python demonstration_epita.py --interactive` | **📚 Recommandé pour étudiants** |
| **Quick-Start** | `python demonstration_epita.py --quick-start` | Suggestions de projets personnalisées |
| **Métriques** | `python demonstration_epita.py --metrics` | Vérification rapide de l'état du projet |

### 🎓 Pour les Étudiants EPITA

**Première utilisation recommandée :**
```bash
# Mode interactif avec pauses pédagogiques et quiz
python examples/scripts_demonstration/demonstration_epita.py --interactive
```

**Pour choisir un projet :**
```bash
# Suggestions personnalisées par niveau
python examples/scripts_demonstration/demonstration_epita.py --quick-start
```

📖 **Documentation complète** : Voir [`demonstration_epita_README.md`](demonstration_epita_README.md)

## 📁 Autres Scripts

### `demo_notable_features.py`
Présente les **fonctionnalités de base** du projet avec des exemples concrets :
- Analyse de cohérence argumentative
- Calcul de scores de clarté
- Extraction d'arguments
- Génération de visualisations (simulées avec mocks)

**Exécution :** Appelé automatiquement par `demonstration_epita.py` ou individuellement.

### `demo_advanced_features.py`
Illustre les **fonctionnalités avancées** du système :
- Moteurs d'inférence complexes (chaînage avant/arrière)
- Intégration Java-Python via JPype et bibliothèque Tweety
- Analyse rhétorique sophistiquée
- Orchestration tactique multi-agents
- Détection de sophismes composés

**Exécution :** Appelé automatiquement par `demonstration_epita.py` ou individuellement.

### `demo_tweety_interaction_simple.py`
Démontre l'**interaction avec la bibliothèque Tweety** pour :
- Manipulation d'arguments logiques formels
- Utilisation de la logique propositionnelle et des prédicats
- Interfaçage Java-Python pour l'IA symbolique

## 🛠️ Configuration et Prérequis

### Installation Rapide
```bash
# Cloner et se placer à la racine du projet
cd d:/Dev/2025-Epita-Intelligence-Symbolique

# Exécution avec installation automatique des dépendances
python examples/scripts_demonstration/demonstration_epita.py --interactive
```

### Prérequis Système
- **Python 3.8+** (testé avec 3.9, 3.10, 3.11)
- **OS** : Windows 11, macOS, Linux
- **RAM** : Minimum 4GB, recommandé 8GB
- **Dépendances** : Installation automatique de `seaborn`, `markdown`, `pytest`

### ⚠️ Important
Les scripts doivent être exécutés **depuis la racine du projet** pour fonctionner correctement.

## 📊 Métriques du Projet

- **Taux de succès des tests** : 99.7%
- **Architecture** : Python + Java (JPype)
- **Domaines couverts** : Logique formelle, Argumentation, IA symbolique
- **Lignes de code** : 15,000+ Python, 5,000+ Java

## 🎯 Cas d'Usage Typiques

### Pour un Cours EPITA
```bash
# Démonstration pédagogique complète
python examples/scripts_demonstration/demonstration_epita.py --interactive
```

### Pour une Présentation Rapide
```bash
# Affichage des métriques pour slides
python examples/scripts_demonstration/demonstration_epita.py --metrics
```

### Pour le Développement de Projets Étudiants
```bash
# Obtenir des suggestions de projets
python examples/scripts_demonstration/demonstration_epita.py --quick-start
```

## 📚 Documentation et Support

- **Guide complet** : [`demonstration_epita_README.md`](demonstration_epita_README.md)
- **Documentation du projet** : `docs/`
- **Exemples pratiques** : `examples/`
- **Tests unitaires** : `tests/`

---

Ces scripts constituent la **vitrine pédagogique** du projet d'Intelligence Symbolique EPITA et sont particulièrement utiles pour comprendre les concepts d'IA explicable, de logique formelle et d'analyse argumentative à travers des exemples concrets et interactifs.

*Dernière mise à jour : Janvier 2025 - Version Pédagogique Enrichie*