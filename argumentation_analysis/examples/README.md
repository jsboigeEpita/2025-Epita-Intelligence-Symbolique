# Exemples de code pour l'analyse argumentative

## À propos de ce dossier
Ce dossier contient des **exemples de code** démontrant l'utilisation et l'implémentation du système d'analyse argumentative. Ces exemples servent de guide pour comprendre comment utiliser les différentes fonctionnalités du système.

## Distinction avec le dossier `examples/` à la racine
⚠️ **Note importante** : Ne pas confondre avec le dossier `examples/` à la racine du projet qui contient des **exemples de textes et données** utilisés comme entrées pour le système.

| Ce dossier (`argumentation_analysis/examples/`) | Dossier `examples/` à la racine |
|------------------------------------------------|--------------------------------|
| Contient des fichiers Python (`.py`) | Contient des fichiers texte (`.txt`) |
| Exemples de code d'implémentation | Exemples de données d'entrée |
| Utilisé pour apprendre à utiliser le système | Utilisé pour tester l'analyse |

Ce répertoire contient des exemples de code démontrant l'utilisation des différentes fonctionnalités du système d'analyse d'argumentation.

## Structure du répertoire

Le répertoire est organisé en sous-répertoires thématiques :

- `agent_integration/` : Exemples d'intégration d'agents
- `communication/` : Exemples de communication entre agents
- `communication_examples/` : Exemples détaillés de différents types de communication
- `hierarchical/` : Exemples d'architecture hiérarchique
- `rhetorical_tools/` : Exemples d'utilisation des outils d'analyse rhétorique

À la racine du répertoire se trouvent également des exemples complets :

- `hierarchical_architecture_example.py` : Exemple d'implémentation d'une architecture hiérarchique
- `rhetorical_analysis_example.py` : Exemple d'analyse rhétorique complète
- `run_hierarchical_orchestration.py` : Exemple d'orchestration hiérarchique

## Description des sous-répertoires

### agent_integration/

Exemples d'intégration d'agents simples dans le système. Contient un README explicatif et des exemples de code pour l'intégration d'agents.

### communication/

Exemples de différents types de communication entre agents, incluant :
- Transfert de données
- Communication horizontale
- Canaux de négociation
- Communication stratégique-tactique

### communication_examples/

Exemples plus détaillés de communication, incluant :
- Communication horizontale
- Communication stratégique-tactique
- Extension du système
- Exemple simple d'utilisation

### hierarchical/

Exemples d'implémentation d'architecture hiérarchique, incluant :
- Exemple hiérarchique simple
- Exemple hiérarchique complexe

### rhetorical_tools/

Exemples d'utilisation des outils d'analyse rhétorique, incluant :
- Évaluateur de cohérence
- Détecteur de sophismes contextuels
- Analyseur de sophismes complexes
- Visualiseur d'arguments

## Utilisation

Ces exemples sont conçus pour être exécutés directement afin de démontrer les fonctionnalités du système. Pour exécuter un exemple :

```bash
python -m argumentation_analysis.examples.rhetorical_analysis_example
```

Ou pour les exemples dans les sous-répertoires :

```bash
python -m argumentation_analysis.examples.rhetorical_tools.coherence_evaluator_example
```

## Liens vers la documentation connexe

- [Documentation des outils rhétoriques](../../docs/outils/README.md)
- [Architecture hiérarchique à trois niveaux](../../docs/architecture_hierarchique_trois_niveaux.md)
- [Système de communication multi-canal](../../docs/conception_systeme_communication_multi_canal.md)