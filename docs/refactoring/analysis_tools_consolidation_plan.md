# Plan de Consolidation : Plugin `AnalysisToolsPlugin`

**Auteur:** Roo
**Date:** 2025-07-31
**Version:** 1.0

## 1. Objectif Stratégique

Ce document détaille le plan de refactoring visant à consolider la collection hétérogène d'outils d'analyse "Enhanced" en un unique plugin standardisé, `AnalysisToolsPlugin`. L'objectif est de réduire la dette technique, de simplifier l'interface d'analyse et d'améliorer la maintenabilité du système en appliquant le **Façade Pattern**.

## 2. Inventaire des Outils à Consolider

Les outils suivants, actuellement situés dans `argumentation_analysis/agents/tools/analysis/enhanced/`, seront consolidés :

-   `EnhancedComplexFallacyAnalyzer`
-   `EnhancedContextualFallacyAnalyzer`
-   `EnhancedFallacySeverityEvaluator`
-   `EnhancedRhetoricalResultAnalyzer`
-   `EnhancedRhetoricalResultVisualizer`
-   `NLPModelManager` (en tant que dépendance interne)

## 3. Architecture Cible

### 3.1. Structure du Plugin

Le nouveau plugin sera structuré comme suit pour isoler la logique interne :

```
plugins/AnalysisToolsPlugin/
├── __init__.py
├── manifest.json
├── plugin.py           # La façade publique
└── logic/
    ├── __init__.py
    ├── complex_fallacy_analyzer.py
    ├── contextual_fallacy_analyzer.py
    ├── fallacy_severity_evaluator.py
    ├── rhetorical_result_analyzer.py
    ├── rhetorical_result_visualizer.py
    └── nlp_model_manager.py
```

Les importations au sein des modules déplacés dans `logic/` seront mises à jour pour utiliser des chemins relatifs (ex: `from .contextual_fallacy_analyzer import ...`).

### 3.2. Le "Façade Pattern" (`plugin.py`)

La classe `AnalysisToolsPlugin` dans `plugin.py` agira comme point d'entrée unique.

-   **Initialisation :**
    -   Le constructeur `__init__` instanciera les analyseurs internes (ex: `self.result_analyzer = EnhancedRhetoricalResultAnalyzer()`).
    -   Il appellera `nlp_model_manager.load_models_sync()` pour centraliser et garantir un chargement unique des modèles NLP.

-   **Capacités Publiques :**
    -   `analyze_text(self, text: str, context: str) -> Dict[str, Any]`: Orchestre une analyse complète de bout en bout.
    -   `evaluate_argument_list(self, arguments: List[str], context: str) -> Dict[str, Any]`: Analyse une liste d'arguments pré-segmentés.
    -   `generate_visual_report(self, analysis_results: Dict[str, Any], output_dir: str) -> Dict[str, str]`: Crée les rapports visuels à partir de résultats d'analyse.

## 4. Plan de Migration Détaillé

### Étape 1 : Création de la Structure du Plugin

1.  Créer le répertoire `plugins/AnalysisToolsPlugin/`.
2.  Créer le répertoire `plugins/AnalysisToolsPlugin/logic/`.
3.  Créer le `manifest.json` avec les métadonnées du plugin.
4.  Créer les fichiers `__init__.py` nécessaires.
5.  Créer une ébauche de `plugin.py` avec la classe `AnalysisToolsPlugin` vide.

### Étape 2 : Migration et Adaptation de la Logique

1.  **Déplacer** les fichiers listés dans l'inventaire de `argumentation_analysis/agents/tools/analysis/enhanced/` vers `plugins/AnalysisToolsPlugin/logic/`.
2.  **Mettre à jour les importations** dans les fichiers déplacés pour qu'elles soient relatives au nouveau module `logic` (ex: `from .nlp_model_manager import nlp_model_manager`).

### Étape 3 : Implémentation de la Façade

1.  Dans `plugin.py`, implémenter le `__init__` pour instancier les analyseurs internes.
2.  Implémenter les méthodes publiques (`analyze_text`, `evaluate_argument_list`, `generate_visual_report`) qui encapsuleront les appels à la logique interne.

### Étape 4 : Refactoring des Consommateurs

1.  Identifier tous les emplacements du code qui importent et utilisent directement les anciens analyseurs "Enhanced".
2.  Remplacer ces appels par des appels au nouveau `AnalysisToolsPlugin`.

    **Exemple de refactoring :**

    *Avant :*
    ```python
    from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
    analyzer = EnhancedComplexFallacyAnalyzer()
    results = analyzer.detect_composite_fallacies(...)
    ```

    *Après :*
    ```python
    # (Supposant un chargement de plugin via un manager)
    analysis_plugin = plugin_manager.get_plugin("AnalysisToolsPlugin")
    results = analysis_plugin.analyze_text(...) # Ou une autre méthode de la façade
    ```

### Étape 5 : Nettoyage

1.  Supprimer le répertoire `argumentation_analysis/agents/tools/analysis/enhanced/` une fois que tous les consommateurs ont été refactorisés et que les tests passent.
2.  Vérifier qu'aucun autre module ne dépend de l'ancien emplacement.

## 5. Validation

1.  Exécuter la suite de tests complète (`./run_tests.ps1`) pour s'assurer de l'absence de régressions.
2.  Ajouter de nouveaux tests unitaires pour le `AnalysisToolsPlugin` afin de valider directement ses capacités (la façade).

## 6. Guide d'Utilisation et API

Le `AnalysisToolsPlugin` expose une interface simplifiée (Façade) pour accéder à des capacités d'analyse complexes.

### 6.1. Instanciation

Le plugin est conçu pour être instancié directement. Il gère de manière autonome le chargement de ses dépendances et des modèles NLP nécessaires.

```python
from plugins.AnalysisToolsPlugin.plugin import AnalysisToolsPlugin

# Créer une instance du plugin
analysis_plugin = AnalysisToolsPlugin()
```

### 6.2. API Publique

Le plugin expose plusieurs méthodes de haut niveau :

#### `analyze_text(self, text: str, context: str = "") -> Dict[str, Any]`

Orchestre une analyse rhétorique et fallacieuse complète sur un bloc de texte fourni.

-   **Paramètres :**
    -   `text` (str) : Le texte brut à analyser.
    -   `context` (str, optionnel) : Contexte supplémentaire (par exemple, le texte d'un document entier) pour améliorer la précision de l'analyse contextuelle.
-   **Retourne :** Un dictionnaire contenant les résultats agrégés des différents analyseurs internes.

#### `evaluate_argument_list(self, arguments: List[str], context: str = "") -> Dict[str, Any]`

Analyse une liste d'arguments déjà segmentés. Utile lorsque le texte a été prétraité par un autre composant du système.

-   **Paramètres :**
    -   `arguments` (List[str]) : Une liste de chaînes de caractères, où chaque chaîne est un argument distinct.
    -   `context` (str, optionnel) : Contexte global pour la liste d'arguments.
-   **Retourne :** Un dictionnaire structuré avec les analyses pour chaque argument de la liste.

#### `generate_visual_report(self, analysis_results: Dict[str, Any], output_dir: str) -> Dict[str, str]`

Génère des visualisations (graphiques, diagrammes) à partir des résultats produits par `analyze_text` ou `evaluate_argument_list`.

-   **Paramètres :**
    -   `analysis_results` (Dict) : Le dictionnaire de résultats retourné par une méthode d'analyse.
    -   `output_dir` (str) : Le chemin du répertoire où les fichiers visuels (ex: `.png`, `.svg`) seront sauvegardés.
-   **Retourne :** Un dictionnaire mappant le type de rapport au chemin du fichier généré.