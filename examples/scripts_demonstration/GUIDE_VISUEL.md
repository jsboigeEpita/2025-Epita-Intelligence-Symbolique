# Guide Visuel - Démonstration EPITA

## 🎯 Vue d'Ensemble des 4 Modes

```
┌─────────────────────────────────────────────────────────────┐
│                 demonstration_epita.py                     │
│                     (720+ lignes)                          │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │    NORMAL   │   │ INTERACTIF  │   │ QUICK-START │
    │   (défaut)  │   │ (recommandé)│   │ (projets)   │
    └─────────────┘   └─────────────┘   └─────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
    • Séquentiel      • Pauses pédago   • Suggestions
    • Automatique     • Quiz intégrés   • Templates
    • 5-10 min        • 15-20 min       • 2-3 min
                              │
                              ▼
                      ┌─────────────┐
                      │  MÉTRIQUES  │
                      │ (validation)│
                      └─────────────┘
                              │
                              ▼
                      • Stats projet
                      • 30 secondes
```

## 🎨 Interface Couleurs

```
[GEAR]     Configuration        (Bleu)
[OK]       Succès              (Vert)
[ECHEC]    Erreur              (Rouge)
[STATS]    Métriques           (Cyan)
[COURS]    Pédagogie           (Jaune)
[?]        Quiz                (Violet)
[ASTUCE]   Conseil             (Cyan)
[OBJECTIF] But                 (Vert)
```

## 📊 Progression Interactive

```
Mode Interactif - Barre de Progression:

[##########------------------------------] 25.0% (1/4)
[OBJECTIF] Vérification des dépendances

[####################--------------------] 50.0% (2/4)  
[OBJECTIF] Exécution de demo_notable_features.py

[##############################----------] 75.0% (3/4)
[OBJECTIF] Exécution de demo_advanced_features.py

[########################################] 100.0% (4/4)
[OBJECTIF] Exécution de la suite de tests
```

## 🎓 Flux Pédagogique Étudiant

```
1. DÉCOUVERTE (Première fois)
   └── python ... --interactive
       ├── Quiz introduction
       ├── Pauses explicatives
       ├── Dashboard progression
       └── Suggestions finales

2. CHOIX DE PROJET (Après découverte)
   └── python ... --quick-start
       ├── Sélection niveau
       ├── Projets adaptés
       ├── Templates fournis
       └── Estimation durée

3. DÉVELOPPEMENT (Pendant projet)
   └── python ... --metrics
       ├── Validation environnement
       ├── Check état projet
       └── Métriques qualité

4. DÉMONSTRATION (Présentation)
   └── python ... (normal)
       ├── Exécution séquentielle
       ├── Pas d'interruption
       └── Logs complets
```

## 🔧 Templates de Projets Visuels

### Débutant (2-3h)
```
┌─────────────────────────────────┐
│ Analyseur Propositions Logiques │
├─────────────────────────────────┤
│ class AnalyseurProposition:     │
│   def __init__(self):           │
│     self.variables = set()      │
│     self.connecteurs = {...}    │
│   def analyser(self, prop):     │
│     # TODO: Implémenter        │
│     return {...}                │
└─────────────────────────────────┘
```

### Intermédiaire (5-8h)
```
┌─────────────────────────────────┐
│   Moteur d'Inférence Avancé    │
├─────────────────────────────────┤
│ class MoteurInference:          │
│   def chainage_avant(self):     │
│     # Algorithme forward        │
│   def chainage_arriere(self):   │
│     # Algorithme backward       │
│   def resolution(self):         │
│     # SLD Resolution            │
└─────────────────────────────────┘
```

### Avancé (10-15h)
```
┌─────────────────────────────────┐
│   Système Multi-Agents          │
├─────────────────────────────────┤
│ class AgentLogique(ABC):        │
│   def raisonner(self): ...      │
│   def communiquer(self): ...    │
│   def negocier(self): ...       │
│                                 │
│ Threading + Protocols           │
│ IA Collective                   │
└─────────────────────────────────┘
```

## 🚀 Commandes Rapides

### Copier-Coller Direct
```bash
# Mode étudiant (recommandé première fois)
python examples/scripts_demonstration/demonstration_epita.py --interactive

# Suggestions projets
python examples/scripts_demonstration/demonstration_epita.py --quick-start

# Vérification rapide
python examples/scripts_demonstration/demonstration_epita.py --metrics

# Démonstration classique
python examples/scripts_demonstration/demonstration_epita.py
```

### Aide en Ligne
```bash
# Afficher l'aide
python examples/scripts_demonstration/demonstration_epita.py --help
```

## 📈 Métriques Visuelles

```
[STATS] Métriques du Projet :
├── [OK] Taux de succès des tests : 99.7%
├── [GEAR] Architecture : Python + Java (JPype)  
├── [IA] Domaines : Logique, Argumentation, IA symbolique
└── [OBJECTIF] Lignes de code : 15,000+ Python, 5,000+ Java
```

## ⚠️ Points d'Attention

### ✅ Bonnes Pratiques
- Exécuter depuis la racine du projet
- Commencer par le mode interactif
- Lire les pauses pédagogiques
- Utiliser les templates fournis

### ❌ Erreurs Communes
- Exécution depuis le mauvais dossier
- Ignorer les quiz interactifs
- Sauter les niveaux de difficulté
- Ne pas lire la documentation

---
*Guide visuel pour une utilisation optimale du système de démonstration EPITA*