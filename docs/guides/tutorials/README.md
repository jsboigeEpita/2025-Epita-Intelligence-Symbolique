# 📚 Tutoriels

## 📋 Vue d'Ensemble

Les tutoriels offrent des guides pas-à-pas pour apprendre à utiliser et étendre le système d'argumentation de l'Intelligence Symbolique EPITA. Ils sont organisés du niveau débutant au niveau avancé, avec une progression pédagogique claire.

Chaque tutoriel inclut des exemples pratiques, des exercices et des points de validation pour garantir une compréhension progressive.

## 📂 Structure

```
tutorials/
├── 01_getting_started/      # Introduction et premiers pas avec le système
└── 02_extending_the_system/ # Extension et personnalisation avancées
```

## 🎯 Parcours d'Apprentissage

### 📘 Niveau 1 : Getting Started

**Prérequis** : Python 3.8+, connaissances de base en programmation  
**Durée estimée** : 2-3 heures  
**Objectif** : Maîtriser les fondamentaux du système d'argumentation

| Tutoriel | Titre | Contenu Clé |
|----------|-------|-------------|
| **[01](./01_getting_started/01_introduction.md)** | Introduction | Présentation du système, architecture générale, concepts de base |
| **[02](./01_getting_started/02_installation.md)** | Installation | Configuration de l'environnement, installation des dépendances, vérification |
| **[03](./01_getting_started/03_first_steps.md)** | Premiers Pas | Première analyse, utilisation de l'API, interprétation des résultats |

**📖 [Documentation détaillée](./01_getting_started/README.md)**

#### Points de Validation Niveau 1

À l'issue de ce niveau, vous devriez être capable de :
- ✅ Installer et configurer l'environnement de développement
- ✅ Comprendre l'architecture générale du système
- ✅ Exécuter une analyse argumentative simple
- ✅ Interpréter les résultats de base
- ✅ Naviguer dans la documentation

### 📗 Niveau 2 : Extending the System

**Prérequis** : Niveau 1 complété, Python intermédiaire, connaissance OOP  
**Durée estimée** : 3-4 heures  
**Objectif** : Personnaliser et étendre le système selon vos besoins

| Tutoriel | Titre | Contenu Clé |
|----------|-------|-------------|
| **[01](./02_extending_the_system/01_creating_plugins.md)** | Création de Plugins | Architecture des plugins, développement, intégration, bonnes pratiques |
| **[02](./02_extending_the_system/02_custom_analyzers.md)** | Analyseurs Personnalisés | Création d'analyseurs spécialisés, extension de la taxonomie des sophismes |

**📖 [Documentation détaillée](./02_extending_the_system/README.md)**

#### Points de Validation Niveau 2

À l'issue de ce niveau, vous devriez être capable de :
- ✅ Développer un plugin fonctionnel pour le système
- ✅ Créer un analyseur personnalisé pour détecter de nouveaux types de sophismes
- ✅ Intégrer vos extensions avec l'architecture existante
- ✅ Tester et valider vos développements
- ✅ Contribuer au projet de manière structurée

## 🚀 Démarrage Rapide

### Installation Initiale

```bash
# Cloner le projet
git clone https://github.com/votre-org/intelligence-symbolique.git
cd intelligence-symbolique

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Vérifier l'installation
python -c "from argumentation_analysis.core.environment import ensure_env; ensure_env()"
```

### Premier Tutoriel

Commencez par l'[Introduction](./01_getting_started/01_introduction.md) pour découvrir les concepts fondamentaux.

### Exemple Rapide

```python
# Exemple d'analyse argumentative simple
from argumentation_analysis.services.extract_service import ExtractService

# Initialiser le service
extract_service = ExtractService()

# Analyser un texte
texte = """
Ce texte contient un argument d'autorité. 
Selon le Dr. Smith, expert reconnu, cette approche est la meilleure.
"""

resultat = extract_service.analyze_text(texte)

# Afficher les résultats
print(f"Sophismes détectés : {resultat.fallacies}")
print(f"Structure argumentative : {resultat.structure}")
```

## 📊 Progression des Compétences

```
Niveau 1: Getting Started
├─ Installation et Configuration     [Débutant]
├─ Analyse Simple                    [Débutant]
└─ Interprétation des Résultats      [Débutant]

Niveau 2: Extending the System
├─ Architecture des Plugins          [Intermédiaire]
├─ Développement d'Extensions        [Intermédiaire]
└─ Tests et Validation               [Avancé]
```

## 🔗 Ressources Connexes

- **[Démonstrations](../demos/README.md)** : Exemples fonctionnels complets du système
- **[Exemples](../examples/README.md)** : Code réutilisable et patterns d'implémentation
- **[Documentation](../docs/)** : Documentation technique complète et référence API
- **[Plugins](../plugins/)** : Collection de plugins existants

## 💡 Créer un Nouveau Tutoriel

### Guidelines de Contribution

Si vous souhaitez contribuer en ajoutant un nouveau tutoriel :

1. **Identifier le niveau cible** : Débutant, Intermédiaire ou Avancé
2. **Choisir le répertoire approprié** : `01_getting_started/` ou `02_extending_the_system/`
3. **Suivre la structure standard** :
   ```markdown
   # Titre du Tutoriel
   
   ## Objectifs d'Apprentissage
   ## Prérequis
   ## Durée Estimée
   ## Concepts Clés
   ## Instructions Pas-à-Pas
   ## Exercices Pratiques
   ## Points de Validation
   ## Ressources Complémentaires
   ```

4. **Inclure des exemples fonctionnels** : Tous les exemples doivent être testés
5. **Ajouter des points de validation** : Permettre au lecteur d'auto-évaluer sa compréhension
6. **Mettre à jour ce README** : Ajouter une entrée dans la table appropriée
7. **Créer/mettre à jour le sous-README** : Documentation du répertoire concerné

### Format des Exemples de Code

```python
#!/usr/bin/env python3
"""
Exemple : [Titre court]
Description : [Description concise de l'objectif]
Niveau : [Débutant/Intermédiaire/Avancé]
"""

# Bootstrap recommandé
from pathlib import Path
import sys

current_file = Path(__file__).resolve()
project_root = next((p for p in current_file.parents if (p / "pyproject.toml").exists()), None)
if project_root and str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from argumentation_analysis.core.environment import ensure_env
ensure_env()

# Code de l'exemple
# ...
```

## 📈 Statistiques

- **Total tutoriels** : 5
- **Niveaux** : 2 (Getting Started, Extending System)
- **Durée totale** : ~6 heures
- **Langages couverts** : Python
- **Dernière mise à jour** : Phase D2.3

## 🎓 Support et Questions

Si vous rencontrez des difficultés en suivant ces tutoriels :

1. **Consultez la [documentation technique](../docs/README.md)** pour des informations supplémentaires
2. **Explorez les [exemples pratiques](../examples/README.md)** pour voir des implémentations concrètes
3. **Testez les [démonstrations](../demos/README.md)** pour valider votre environnement
4. **Vérifiez les problèmes connus** dans les issues GitHub du projet

## 🏆 Certification

Après avoir complété tous les tutoriels et validé tous les points de validation, vous aurez :
- ✅ Une compréhension complète du système d'argumentation
- ✅ Les compétences pour développer vos propres extensions
- ✅ La capacité de contribuer efficacement au projet
- ✅ Les bases pour approfondir l'analyse argumentative formelle

---

**Dernière mise à jour** : Phase D2.3 - Documentation Structure  
**Mainteneur** : Intelligence Symbolique EPITA  
**Licence** : Voir LICENSE à la racine du projet
</thinking>

Maintenant je lis le `examples/README.md` existant pour voir comment l'enrichir.

<read_file>
<path>examples/README.md</path>
<line_range>1-100</line_range>
</read_file>