# Documentation de la Structure du Répertoire `agents/`

## Introduction

Le répertoire `argumentation_analysis/agents` a été réorganisé selon une nouvelle structure plus cohérente et maintenable. Cette documentation explique la nouvelle organisation, ses avantages, et comment l'utiliser efficacement.

## Vue d'ensemble de la Structure

```
argumentation_analysis/
└── agents/
    ├── core/                           # Agents principaux
    │   ├── pm/                         # Agent Project Manager
    │   ├── informal/                   # Agent d'Analyse Informelle
    │   ├── pl/                         # Agent de Logique Propositionnelle
    │   ├── extract/                    # Agent d'Extraction
    │   └── README.md
    │
    ├── tools/                          # Outils et utilitaires
    │   ├── optimization/               # Outils d'optimisation
    │   ├── analysis/                   # Outils d'analyse
    │   ├── encryption/                 # Système d'encryption
    │   └── README.md
    │
    ├── runners/                        # Scripts d'exécution
    │   ├── test/                       # Exécution des tests
    │   ├── deploy/                     # Scripts de déploiement
    │   ├── integration/                # Scripts d'intégration
    │   └── README.md
    │
    ├── data/                           # Données utilisées par les agents
    ├── libs/                           # Bibliothèques partagées
    ├── docs/                           # Documentation
    │   ├── reports/                    # Rapports d'analyse et de test
    │   └── README.md
    │
    ├── traces/                         # Traces d'exécution (séparées du code)
    │   ├── informal/                   # Traces de l'agent Informal
    │   ├── orchestration/              # Traces de l'orchestration
    │   └── README.md
    │
    ├── templates/                      # Templates pour nouveaux agents
    │   ├── student_template/           # Template pour les étudiants
    │   └── README.md
    │
    └── README.md
```

## Explication Détaillée

### 1. Agents Principaux (`core/`)

Ce répertoire contient les implémentations des agents principaux du système d'analyse d'argumentation. Chaque agent est placé dans son propre sous-répertoire, ce qui permet une meilleure organisation et une séparation claire des responsabilités.

- **Agent Project Manager (`pm/`)** : Orchestre l'analyse et coordonne les autres agents.
- **Agent d'Analyse Informelle (`informal/`)** : Identifie les arguments et les sophismes dans les textes.
- **Agent de Logique Propositionnelle (`pl/`)** : Gère la formalisation et l'interrogation logique via Tweety.
- **Agent d'Extraction (`extract/`)** : Gère l'extraction et la réparation des extraits de texte.

Chaque sous-répertoire d'agent contient typiquement :
- `__init__.py` : Fichier d'initialisation du module
- `*_definitions.py` : Définitions des structures de données et fonctions de configuration
- `prompts.py` : Prompts utilisés pour les interactions avec les modèles de langage
- `*_agent.py` : Implémentation principale de l'agent
- `README.md` : Documentation spécifique à l'agent

### 2. Outils et Utilitaires (`tools/`)

Ce répertoire contient les outils et utilitaires utilisés par les agents. Ces outils sont séparés des agents pour une meilleure modularité et réutilisabilité.

- **Outils d'Optimisation (`optimization/`)** : Outils pour améliorer les performances des agents.
- **Outils d'Analyse (`analysis/`)** : Outils pour analyser les résultats et les performances des agents.
- **Système d'Encryption (`encryption/`)** : Outils pour sécuriser les données sensibles.

### 3. Scripts d'Exécution (`runners/`)

Ce répertoire contient les scripts utilisés pour exécuter les agents dans différents contextes.

- **Scripts de Test (`test/`)** : Scripts pour tester les agents individuellement ou en combinaison.
- **Scripts de Déploiement (`deploy/`)** : Scripts pour déployer les agents dans différents environnements.
- **Scripts d'Intégration (`integration/`)** : Scripts pour tester l'interaction entre les différents agents.

### 4. Données et Bibliothèques

- **Données (`data/`)** : Données utilisées par les agents, comme les taxonomies ou les exemples.
- **Bibliothèques Partagées (`libs/`)** : Bibliothèques communes utilisées par plusieurs agents.

### 5. Documentation et Traces

- **Documentation (`docs/`)** : Documentation du projet, incluant des guides d'utilisation et des rapports.
- **Traces d'Exécution (`traces/`)** : Traces générées par les agents lors de leur exécution, séparées du code pour plus de clarté.

### 6. Templates

- **Templates pour Nouveaux Agents (`templates/`)** : Templates pour faciliter la création de nouveaux agents.

## Avantages de la Nouvelle Structure

1. **Organisation Logique** : Les composants sont regroupés par fonction, ce qui facilite la navigation et la compréhension du projet.
2. **Séparation des Préoccupations** : Chaque répertoire a une responsabilité claire et bien définie.
3. **Modularité** : Les composants sont conçus pour être modulaires et réutilisables.
4. **Maintenabilité** : La structure facilite la maintenance et l'évolution du projet.
5. **Extensibilité** : Il est facile d'ajouter de nouveaux agents, outils ou fonctionnalités.
6. **Clarté** : La séparation entre le code, les données, la documentation et les traces améliore la lisibilité.

## Guide d'Utilisation

### Développement d'un Nouvel Agent

1. Utilisez le template étudiant comme base (`templates/student_template/`)
2. Créez un nouveau sous-répertoire dans `core/` avec le nom de l'agent
3. Implémentez les fonctionnalités spécifiques à l'agent
4. Créez des tests dans le répertoire `runners/test/`
5. Intégrez l'agent dans le système d'orchestration

### Utilisation des Outils

1. Identifiez l'outil approprié dans le répertoire `tools/`
2. Importez l'outil dans votre code
3. Utilisez l'outil selon sa documentation

### Exécution des Scripts

1. Naviguez vers le répertoire `runners/`
2. Exécutez le script approprié avec Python
3. Consultez les traces générées dans le répertoire `traces/`

### Consultation de la Documentation

1. Naviguez vers le répertoire `docs/`
2. Consultez la documentation générale ou spécifique à un composant
3. Référez-vous aux rapports pour des analyses détaillées

## Exemples d'Utilisation

### Exemple 1: Analyse d'un Texte avec l'Agent Informel

```python
from agents.core.informal.informal_agent import InformalAgent
from agents.core.informal.informal_definitions import setup_informal_agent
from core.llm_service import create_llm_service

async def analyze_text(text):
    # Créer le service LLM
    llm_service = create_llm_service()
    
    # Initialiser l'agent
    kernel, agent = await setup_informal_agent(llm_service)
    
    # Analyser le texte
    result = await agent.analyze_text(text)
    
    return result
```

### Exemple 2: Utilisation d'un Outil d'Optimisation

```python
from agents.tools.optimization.informal.improve_informal_agent import improve_agent_prompts

async def optimize_agent():
    # Charger les prompts actuels
    current_prompts = load_prompts("agents/core/informal/prompts.py")
    
    # Améliorer les prompts
    improved_prompts = await improve_agent_prompts(current_prompts)
    
    # Sauvegarder les prompts améliorés
    save_prompts(improved_prompts, "agents/core/informal/prompts_improved.py")
```

### Exemple 3: Exécution d'un Script de Test

```bash
python agents/runners/test/informal/test_informal_agent.py
```

## Conclusion

La nouvelle structure du répertoire `agents/` offre une organisation plus cohérente et maintenable du code. Elle facilite le développement, la maintenance et l'extension du système d'analyse d'argumentation. En suivant les conventions et les bonnes pratiques décrites dans cette documentation, les développeurs peuvent contribuer efficacement au projet et tirer pleinement parti de ses fonctionnalités.