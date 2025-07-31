# Plan de Découplage et Cartographie des Dépendances

Ce document détaille les dépendances des outils `ArgumentCoherenceEvaluator`, `ArgumentStructureVisualizer`, et `ContextualFallacyDetector` et propose un plan stratégique pour leur découplage.

## 1. Cartographie des Dépendances

### ArgumentCoherenceEvaluator

| Fichier | Ligne | Extrait de Code | Classification |
|---|---|---|---|
| `scripts/reporting/generate_rhetorical_analysis_summaries.py` | 82 | `"ArgumentCoherenceEvaluator",` | Script de Reporting |
| `argumentation_analysis/pipelines/reporting_pipeline.py` | 214 | `Utiliser l'agent ArgumentCoherenceEvaluator pour évaluer...` | Logique de Pipeline (Configuration) |
| `argumentation_analysis/pipelines/reporting_pipeline.py` | 239 | `"ArgumentCoherenceEvaluator": [` | Logique de Pipeline (Configuration) |
| `argumentation_analysis/pipelines/reporting_pipeline.py` | 434 | `"ArgumentCoherenceEvaluator": {"Détection des sophismes": ...}` | Logique de Pipeline (Configuration) |
| `argumentation_analysis/pipelines/reporting_pipeline.py` | 519 | `- **ArgumentCoherenceEvaluator**: Évalue la cohérence.` | Logique de Pipeline (Génération de rapport) |
| `argumentation_analysis/agents/tools/analysis/new/argument_coherence_evaluator.py` | 46 | `class ArgumentCoherenceEvaluator:` | Définition de l'outil |
| `argumentation_analysis/agents/tools/analysis/new/argument_coherence_evaluator.py` | 443 | `evaluator = ArgumentCoherenceEvaluator()` | Définition de l'outil (Exemple interne) |
| `argumentation_analysis/agents/tools/analysis/new/__init__.py` | 11 | `from .argument_coherence_evaluator import ArgumentCoherenceEvaluator` | Export du module |
| `argumentation_analysis/agents/tools/analysis/new/__init__.py` | 17 | `'ArgumentCoherenceEvaluator',` | Export du module |
| `argumentation_analysis/mocks/analysis_tools.py` | 76 | `class MockArgumentCoherenceEvaluator:` | Tests (Simulation) |
| `argumentation_analysis/examples/rhetorical_tools/coherence_evaluator_example.py` | 4 | `from argumentation_analysis.tools.argument_coherence_evaluator import ArgumentCoherenceEvaluator` | Exemples / Documentation |
| `argumentation_analysis/examples/rhetorical_tools/coherence_evaluator_example.py` | 11 | `evaluator = ArgumentCoherenceEvaluator()` | Exemples / Documentation |
| `reports/backup_before_cleanup_*/scripts/reporting/*` | - | `"ArgumentCoherenceEvaluator",` | Fichiers obsolètes (Backup) |

### ArgumentStructureVisualizer

| Fichier | Ligne | Extrait de Code | Classification |
|---|---|---|---|
| `argumentation_analysis/agents/tools/analysis/new/argument_structure_visualizer.py` | 53 | `class ArgumentStructureVisualizer:` | Définition de l'outil |
| `argumentation_analysis/agents/tools/analysis/new/__init__.py` | 12 | `from .argument_structure_visualizer import ArgumentStructureVisualizer` | Export du module |
| `argumentation_analysis/agents/tools/analysis/new/__init__.py` | 18 | `'ArgumentStructureVisualizer',` | Export du module |
| `argumentation_analysis/examples/rhetorical_tools/visualizer_example.py` | 4 | `from argumentation_analysis.tools.argument_structure_visualizer import ArgumentStructureVisualizer` | Exemples / Documentation |
| `argumentation_analysis/examples/rhetorical_tools/visualizer_example.py` | 11 | `visualizer = ArgumentStructureVisualizer(...)` | Exemples / Documentation |

### ContextualFallacyDetector

| Fichier | Ligne | Extrait de Code | Classification |
|---|---|---|---|
| `argumentation_analysis/core/bootstrap.py` | 95 | `from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector` | **Initialisation Core (Critique)** |
| `argumentation_analysis/core/bootstrap.py` | 100 | `class ContextualFallacyDetectorAdapter:` | **Initialisation Core (Critique)** |
| `argumentation_analysis/core/bootstrap.py` | 138 | `Initialise de manière paresseuse et retourne le ContextualFallacyDetector.` | **Initialisation Core (Critique)** |
| `argumentation_analysis/pipelines/advanced_rhetoric.py` | 23 | `fallacy_detector: AbstractFallacyDetector` | Injection de Dépendance (Pipeline) |
| `argumentation_analysis/pipelines/advanced_rhetoric.py` | 56 | `analysis_plugin = AnalysisToolsPlugin(fallacy_detector=fallacy_detector)` | Injection de Dépendance (Plugin) |
| `plugins/AnalysisToolsPlugin/plugin.py`| 30 | `def __init__(self, fallacy_detector: AbstractFallacyDetector):` | Façade (Réception de dépendance) |
| `plugins/AnalysisToolsPlugin/plugin.py`| 40 | `self.contextual_analyzer = EnhancedContextualFallacyAnalyzer(fallacy_detector=fallacy_detector)` | Façade (Propagation de dépendance) |
| `plugins/AnalysisToolsPlugin/logic/complex_fallacy_analyzer.py`| 92 | `self.contextual_analyzer = EnhancedContextualFallacyAnalyzer(fallacy_detector=fallacy_detector)` | Consommateur (Utilisation de l'abstraction) |
| `scripts/reporting/generate_rhetorical_analysis_summaries.py` | 81 | `"ContextualFallacyDetector",` | Script de Reporting |
| `argumentation_analysis/pipelines/reporting_pipeline.py`| 234 | `"ContextualFallacyDetector": [` | Logique de Pipeline (Configuration) |
| `argumentation_analysis/pipelines/reporting_pipeline.py`| 433 | `"ContextualFallacyDetector": {"Détection des sophismes": ...}` | Logique de Pipeline (Configuration) |
| `argumentation_analysis/pipelines/reporting_pipeline.py`| 518 | `- **ContextualFallacyDetector**: Détecte les sophismes contextuels.` | Logique de Pipeline (Génération de rapport) |
| `argumentation_analysis/agents/tools/analysis/new/contextual_fallacy_detector.py` | 38 | `class ContextualFallacyDetector:` | Définition de l'outil |
| `argumentation_analysis/agents/tools/analysis/new/__init__.py` | 13 | `from .contextual_fallacy_detector import ContextualFallacyDetector` | Export du module |
| `argumentation_analysis/mocks/analysis_tools.py` | 24 | `class MockContextualFallacyDetector:` | Tests (Simulation) |
| `argumentation_analysis/examples/rhetorical_tools/contextual_fallacy_detector_example.py` | 4 | `from argumentation_analysis.tools.contextual_fallacy_detector import ContextualFallacyDetector` | Exemples / Documentation (Obsolète) |
| `argumentation_analysis/core/utils/reporting_utils.py` | 234 | `Agents de base (ContextualFallacyDetector, etc.).` | Utilitaire de Reporting |
| `reports/backup_before_cleanup_*/scripts/reporting/*` | - | `"ContextualFallacyDetector",` | Fichiers obsolètes (Backup) |

---
## 2. Plan de Découplage Stratégique

### Stratégies proposées

#### Pour `ContextualFallacyDetector` (Dépendance la plus critique)

-   **Dépendance Core (`argumentation_analysis/core/bootstrap.py`)**
    -   **Stratégie : Abstraction et Injection de Dépendances (Adapter Pattern).**
    -   **Action :**
        1.  Créer une interface abstraite `AbstractFallacyDetector` dans `argumentation_analysis.core.interfaces.fallacy_detector`.
        2.  Faire hériter l'implémentation concrète `ContextualFallacyDetector` de cette interface.
        3.  Utiliser un `ContextualFallacyDetectorAdapter` dans `bootstrap.py` qui encapsule la logique d'instanciation de l'implémentation concrète.
        4.  Modifier la méthode `context.get_fallacy_detector()` pour qu'elle retourne le type `AbstractFallacyDetector`.
        5.  **Validation :** Cette stratégie est maintenant implémentée. Le point d'entrée du pipeline (`advanced_rhetoric.py`) injecte le `fallacy_detector` dans le `AnalysisToolsPlugin`, qui le propage à son tour aux analyseurs internes. Cela garantit un découplage efficace.

-   **Dépendances Périphériques (Scripts, Pipelines, Exemples)**
    -   **Stratégie : Remplacement et Mise à Jour.**
    -   **Action :** Remplacer les appels directs par l'utilisation du `AnalysisToolsPlugin` configuré avec le détecteur de sophismes approprié. Les exemples (`..._example.py`) devront être mis à jour pour refléter cette nouvelle approche, qui est la méthode standard d'utilisation des outils.

#### Pour `ArgumentCoherenceEvaluator`

-   **Dépendances (Scripts, Pipelines, Exemples)**
    -   **Stratégie : Remplacement.**
    -   **Action :** Remplacer les appels à `ArgumentCoherenceEvaluator` par un outil équivalent du `AnalysisToolsPlugin`. Si une équivalence fonctionnelle directe n'existe pas, une interface `AbstractCoherenceEvaluator` (similaire à la stratégie ci-dessus) devra être introduite.

#### Pour `ArgumentStructureVisualizer`

-   **Dépendances (Exemples)**
    -   **Stratégie : Suppression / Archivage.**
    -   **Action :** Cet outil semble isolé et non critique. Recommander la suppression de l'outil et de son exemple. Si la fonctionnalité est toujours désirée, elle devrait être intégrée à un service de visualisation plus large et non comme un outil autonome.

#### Pour les Fichiers Obsolètes

-   **Dépendances (`reports/backup_before_cleanup_*`)**
    -   **Stratégie : Suppression.**
    -   **Action :** Supprimer ces répertoires de backup qui polluent les résultats de recherche et augmentent la dette technique.

### Séquençage des Actions

1.  **Étape 1 : Isoler la dépendance critique (ContextualFallacyDetector).** **(Terminée)**
    -   **Tâche :** Implémenter l'interface `AbstractFallacyDetector` et adapter `ContextualFallacyDetectorAdapter` dans `bootstrap.py`.
    -   **Résultat :** La dépendance est maintenant correctement injectée via le constructeur du `AnalysisToolsPlugin`. Les analyseurs internes dépendent de l'abstraction `AbstractFallacyDetector` et non plus de l'implémentation concrète. Le découplage est un succès.
    -   **Objectif :** Découpler la logique de démarrage de l'implémentation concrète. C'est le point le plus risqué.

2.  **Étape 2 : Remplacer les dépendances de `ArgumentCoherenceEvaluator`.**
    -   **Tâche :** Remplacer `ArgumentCoherenceEvaluator` par l'alternative moderne dans les pipelines et les scripts.
    -   **Objectif :** Valider le processus de remplacement sur un périmètre moins critique.

3.  **Étape 3 : Nettoyer les dépendances restantes.**
    -   **Tâche 3a :** Mettre à jour les exemples et les mocks pour utiliser les nouvelles abstractions/outils.
    -   **Tâche 3b :** Supprimer `ArgumentStructureVisualizer` et son exemple.
    -   **Tâche 3c :** Supprimer les répertoires de backup obsolètes.
    -   **Objectif :** Finaliser le nettoyage et éliminer toute référence aux anciens outils.