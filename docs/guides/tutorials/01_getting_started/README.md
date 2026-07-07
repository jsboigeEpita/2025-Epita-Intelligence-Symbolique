# 📘 Getting Started

> **⚠️ Documentation en sommeil (mode Hiérarchique dormant).**
> Les tutoriels de cette section décrivent le mode d'orchestration
> **Hiérarchique**, actuellement **dormant** (voir la table *Orchestration Modes*
> de `CLAUDE.md`). Le code de référence reste présent à l'emplacement canonique
> `argumentation_analysis/orchestration/hierarchical/` (expérimental, non branché
> dans le pipeline actif) — ces tutoriels sont donc **en sommeil, pas cassés**.
> **Point d'entrée recommandé** aujourd'hui :
> [`demonstration_epita.py`](../../../../examples/02_core_system_demos/scripts_demonstration/demonstration_epita.py)
> et `run_unified_analysis` (mode Pipeline actif). Les exemples d'imports
> ci-dessous peuvent ne pas s'exécuter tels quels.

## Description

Ce répertoire contient les tutoriels d'introduction pour prendre en main le système d'analyse argumentative de l'Intelligence Symbolique EPITA. Ces tutoriels sont conçus pour les débutants et couvrent l'installation, la configuration, et les premières analyses.

**Parcours recommandé** : Suivez les tutoriels dans l'ordre numérique pour une progression optimale.

## Contenu

### Tutoriels

| # | Tutoriel | Durée | Prérequis |
|---|----------|-------|-----------|
| **[01](./01_introduction.md)** | Introduction au système | 30 min | Python 3.10+ |
| **[02](./02_simple_analysis.md)** | Analyse rhétorique simple | 45 min | Tutoriel 01 |
| **[03](./03_complex_analysis.md)** | Analyse rhétorique complexe | 60 min | Tutoriels 01-02 |

## Parcours d'Apprentissage

### 📚 Tutoriel 01 : Introduction

**Objectif** : Apprendre à installer, configurer et exécuter une analyse rhétorique de base

**Ce que vous apprendrez** :
- Installation et configuration de l'environnement
- Structure générale du projet
- Architecture à trois niveaux (orchestration hiérarchique)
- Premiers pas avec le système

**Durée estimée** : 30 minutes

```bash
# Suivre le tutoriel
code tutorials/01_getting_started/01_introduction.md
```

### 📊 Tutoriel 02 : Analyse Simple

**Objectif** : Effectuer votre première analyse rhétorique complète

**Ce que vous apprendrez** :
- Charger et préparer un texte
- Configurer les paramètres d'analyse
- Exécuter une analyse de base
- Interpréter les résultats
- Exporter les résultats

**Durée estimée** : 45 minutes

**Prérequis** : Tutoriel 01 complété

```bash
# Suivre le tutoriel
code tutorials/01_getting_started/02_simple_analysis.md
```

### 🔬 Tutoriel 03 : Analyse Complexe

**Objectif** : Maîtriser les techniques avancées d'analyse argumentative

**Ce que vous apprendrez** :
- Analyse de textes argumentatifs complexes
- Détection et classification des sophismes
- Évaluation de la cohérence argumentative
- Analyse des structures rhétoriques avancées
- Génération de rapports détaillés

**Durée estimée** : 60 minutes

**Prérequis** : Tutoriels 01 et 02 complétés

```bash
# Suivre le tutoriel
code tutorials/01_getting_started/03_complex_analysis.md
```

## Points de Validation

À l'issue de ce parcours Getting Started, vous devriez être capable de :

- ✅ Installer et configurer l'environnement de développement
- ✅ Comprendre l'architecture hiérarchique du système
- ✅ Exécuter une analyse argumentative simple
- ✅ Exécuter une analyse argumentative complexe
- ✅ Interpréter les résultats d'analyse
- ✅ Détecter et classifier les sophismes courants
- ✅ Évaluer la cohérence d'une argumentation
- ✅ Exporter et partager vos résultats

## Installation Rapide

Avant de commencer les tutoriels :

```bash
# 1. Cloner le projet (si pas déjà fait)
git clone https://github.com/votre-org/intelligence-symbolique.git
cd intelligence-symbolique

# 2. Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Vérifier l'installation
python -c "from argumentation_analysis.core.environment import ensure_env; ensure_env()"
```

## Ressources Complémentaires

### Pendant les Tutoriels

- **Démonstrations** : Voir des exemples fonctionnels
- **[Exemples](../../../../examples/)** : Code réutilisable
- **[Documentation](../../../../docs/)** : Référence complète

### Après les Tutoriels

- **[Extending the System](../02_extending_the_system/)** : Niveau avancé
- **[Plugins](../../../../examples/04_plugins/)** : Développement de plugins
- **Integration** : Tests d'intégration

## Conseils pour Réussir

### 💡 Bonnes Pratiques

1. **Suivez l'ordre** : Les tutoriels sont conçus pour être suivis séquentiellement
2. **Pratiquez** : Exécutez tous les exemples de code
3. **Expérimentez** : Essayez vos propres textes après chaque tutoriel
4. **Prenez des notes** : Documentez ce que vous apprenez
5. **Posez des questions** : Consultez la documentation pour plus de détails

### ⚠️ Erreurs Courantes

**Problème** : `ModuleNotFoundError`  
**Solution** : Vérifiez que vous avez activé l'environnement virtuel et installé les dépendances

**Problème** : `EnvironmentError` lors de l'exécution  
**Solution** : Utilisez le one-liner : `import argumentation_analysis.core.environment`

**Problème** : Résultats d'analyse vides  
**Solution** : Vérifiez que votre texte contient bien des arguments ou sophismes

## Progression Suggérée

```
Niveau Débutant
├─ 📘 Tutoriel 01: Introduction        [30 min] ✓
├─ 📊 Tutoriel 02: Analyse Simple       [45 min] ✓
└─ 🔬 Tutoriel 03: Analyse Complexe    [60 min] ✓
                                        
📈 Total: ~2h15                         
                                        
Prochaine étape                         
└─ 📗 Extending the System ➔            
```

## Support

### Besoin d'Aide ?

1. **Consultez la [FAQ](../../../../docs/guides/FAQ.md)** : Réponses aux questions fréquentes
2. **Explorez les démos** : Voir le système en action
3. **Testez les [exemples](../../../../examples/)** : Code prêt à l'emploi
4. **Lisez la [documentation](../../../../docs/)** : Référence complète

### Feedback

Vos retours sont précieux ! Si vous avez des suggestions pour améliorer ces tutoriels :
1. Ouvrez une issue sur GitHub
2. Proposez une pull request avec vos améliorations
3. Contactez l'équipe de maintenance

---

**Dernière mise à jour** : Phase D2.3  
**Mainteneur** : Intelligence Symbolique EPITA  
**Niveau** : Débutant  
**Durée totale** : ~2h15