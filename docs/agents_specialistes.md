# Documentation des Agents Spécialistes et de leurs Rôles

## Introduction aux Agents

Dans le système d'orchestration d'analyse rhétorique, les agents spécialistes sont des composants logiciels autonomes conçus pour accomplir des tâches spécifiques liées à l'analyse des arguments et des sophismes. Chaque agent possède une expertise particulière et contribue à l'analyse globale en se concentrant sur un aspect spécifique de l'analyse rhétorique.

Un agent dans ce système est défini comme une entité logicielle qui :
- Possède une expertise spécifique dans un domaine de l'analyse rhétorique
- Est capable d'analyser des textes ou des arguments de manière autonome
- Peut communiquer avec d'autres agents via des protocoles définis
- Contribue à l'analyse globale en fournissant des résultats spécifiques
- Peut être orchestré dans le cadre d'un workflow plus large

Les agents sont conçus selon le principe de responsabilité unique, chacun se concentrant sur une tâche spécifique qu'il peut accomplir de manière experte. Cette spécialisation permet une analyse plus approfondie et plus précise des arguments et des sophismes.

## Architecture Multi-Agents

L'architecture multi-agents du système d'orchestration d'analyse rhétorique est conçue pour permettre une analyse complète et approfondie des textes argumentatifs. Cette architecture repose sur plusieurs principes clés :

### Principes de l'Architecture

1. **Spécialisation** : Chaque agent est spécialisé dans un aspect spécifique de l'analyse rhétorique.
2. **Collaboration** : Les agents collaborent pour produire une analyse complète.
3. **Modularité** : Les agents peuvent être ajoutés, modifiés ou remplacés sans affecter l'ensemble du système.
4. **État partagé** : Les agents partagent un état commun qui contient les résultats de l'analyse.
5. **Orchestration** : Un orchestrateur coordonne les activités des agents.

### Structure de l'Architecture

L'architecture multi-agents est organisée en plusieurs couches :

1. **Couche d'Entrée** : Responsable de la réception et du prétraitement des textes à analyser.
2. **Couche d'Analyse** : Contient les agents spécialistes qui effectuent l'analyse rhétorique.
3. **Couche d'Orchestration** : Coordonne les activités des agents et gère le flux de travail.
4. **Couche de Résultats** : Responsable de la consolidation et de la présentation des résultats.

### Flux de Travail

Le flux de travail typique dans cette architecture est le suivant :

1. Un texte est soumis au système via la couche d'entrée.
2. L'orchestrateur détermine quels agents doivent être activés et dans quel ordre.
3. Les agents spécialistes analysent le texte selon leur expertise.
4. Les résultats de chaque agent sont stockés dans l'état partagé.
5. L'orchestrateur peut activer d'autres agents en fonction des résultats obtenus.
6. Une fois l'analyse terminée, les résultats sont consolidés et présentés.

## Agents Spécialistes

### Agent d'Analyse de Sophismes Contextuels

**Nom de classe** : `ContextualFallacyAnalyzer`

**Rôle** : Cet agent est responsable de l'analyse des sophismes dans leur contexte. Il identifie les sophismes potentiels dans un texte et évalue leur pertinence en fonction du contexte dans lequel ils apparaissent.

**Responsabilités** :
- Analyser le contexte d'un texte pour identifier des sophismes contextuels
- Déterminer le type de contexte (politique, scientifique, commercial, etc.)
- Identifier les sophismes potentiels dans un texte
- Filtrer les sophismes en fonction du contexte
- Fournir des exemples de sophismes contextuels

**Méthodes principales** :
- `analyze_context(text, context)` : Analyse le contexte d'un texte pour identifier des sophismes contextuels
- `identify_contextual_fallacies(argument, context)` : Identifie les sophismes contextuels dans un argument
- `get_contextual_fallacy_examples(fallacy_type, context_type)` : Retourne des exemples de sophismes contextuels

**Exemple d'utilisation** :
```python
analyzer = ContextualFallacyAnalyzer()
results = analyzer.analyze_context(
    text="Les experts sont unanimes : ce produit est sûr.",
    context="Discours commercial pour un produit controversé"
)
fallacies = analyzer.identify_contextual_fallacies(
    argument="Les experts sont unanimes : ce produit est sûr.",
    context="Discours commercial pour un produit controversé"
)
```

### Agent d'Évaluation de Sévérité des Sophismes

**Nom de classe** : `FallacySeverityEvaluator`

**Rôle** : Cet agent évalue la gravité des sophismes identifiés dans un argument, en tenant compte de différents facteurs comme le contexte, l'impact sur la validité de l'argument, et la visibilité du sophisme.

**Responsabilités** :
- Évaluer la gravité des sophismes dans un argument
- Calculer l'impact d'un sophisme sur la validité d'un argument
- Classer les sophismes par ordre de gravité
- Générer des suggestions pour corriger les arguments contenant des sophismes

**Méthodes principales** :
- `evaluate_severity(fallacy_type, argument, context)` : Évalue la gravité d'un sophisme dans un argument
- `rank_fallacies(fallacies)` : Classe les sophismes par ordre de gravité
- `evaluate_impact(fallacy_type, argument, context)` : Évalue l'impact d'un sophisme sur la validité d'un argument

**Exemple d'utilisation** :
```python
evaluator = FallacySeverityEvaluator()
severity = evaluator.evaluate_severity(
    fallacy_type="Appel à l'autorité",
    argument="Les experts sont unanimes : ce produit est sûr.",
    context="Discours commercial pour un produit controversé"
)
```

### Agent d'Analyse de Sophismes Complexes

**Nom de classe** : `ComplexFallacyAnalyzer`

**Rôle** : Cet agent analyse des sophismes complexes, comme les combinaisons de sophismes ou les sophismes qui s'étendent sur plusieurs arguments. Il identifie des motifs plus sophistiqués de raisonnement fallacieux.

**Responsabilités** :
- Identifier les combinaisons de sophismes dans un argument
- Analyser les sophismes structurels qui s'étendent sur plusieurs arguments
- Détecter les contradictions entre arguments
- Détecter les cercles argumentatifs
- Identifier les motifs de sophismes dans un texte

**Méthodes principales** :
- `identify_combined_fallacies(argument)` : Identifie les combinaisons de sophismes dans un argument
- `analyze_structural_fallacies(arguments)` : Analyse les sophismes structurels qui s'étendent sur plusieurs arguments
- `identify_fallacy_patterns(text)` : Identifie les motifs de sophismes dans un texte

**Exemple d'utilisation** :
```python
analyzer = ComplexFallacyAnalyzer()
combined_fallacies = analyzer.identify_combined_fallacies(argument)
structural_fallacies = analyzer.analyze_structural_fallacies(arguments)
patterns = analyzer.identify_fallacy_patterns(text)
```

### Agent d'Analyse de Résultats Rhétoriques

**Nom de classe** : `RhetoricalResultAnalyzer`

**Rôle** : Cet agent analyse les résultats d'une analyse rhétorique, extrait des insights et génère des résumés. Il fournit une vue d'ensemble de l'analyse et des recommandations pour l'améliorer.

**Responsabilités** :
- Analyser les résultats d'une analyse rhétorique
- Calculer des métriques de base sur l'analyse
- Analyser les sophismes identifiés
- Analyser les arguments identifiés
- Évaluer la qualité globale de l'analyse
- Extraire des insights des résultats
- Générer un résumé des résultats

**Méthodes principales** :
- `analyze_results(state)` : Analyse les résultats d'une analyse rhétorique
- `extract_insights(state)` : Extrait des insights des résultats d'une analyse rhétorique
- `generate_summary(state)` : Génère un résumé des résultats d'une analyse rhétorique

**Exemple d'utilisation** :
```python
analyzer = RhetoricalResultAnalyzer()
results = analyzer.analyze_results(state)
insights = analyzer.extract_insights(state)
summary = analyzer.generate_summary(state)
```

### Agent de Visualisation des Résultats Rhétoriques

**Nom de classe** : `RhetoricalResultVisualizer`

**Rôle** : Cet agent visualise les résultats d'une analyse rhétorique, comme la génération de graphes d'arguments, de distributions de sophismes, et de heatmaps de qualité argumentative.

**Responsabilités** :
- Générer des visualisations des résultats d'une analyse rhétorique
- Créer des graphes d'arguments et de sophismes
- Créer des visualisations de la distribution des sophismes
- Créer des heatmaps de la qualité des arguments
- Générer des rapports HTML avec toutes les visualisations

**Méthodes principales** :
- `generate_argument_graph(state)` : Génère un graphe des arguments et des sophismes
- `generate_fallacy_distribution(state)` : Génère une visualisation de la distribution des sophismes
- `generate_argument_quality_heatmap(state)` : Génère une heatmap de la qualité des arguments
- `generate_html_report(state)` : Génère un rapport HTML avec toutes les visualisations

**Exemple d'utilisation** :
```python
visualizer = RhetoricalResultVisualizer()
argument_graph = visualizer.generate_argument_graph(state)
fallacy_distribution = visualizer.generate_fallacy_distribution(state)
html_report = visualizer.generate_html_report(state)
```

### Autres Agents Spécialistes

Le système est conçu pour être extensible, et d'autres agents spécialistes peuvent être ajoutés pour couvrir des aspects spécifiques de l'analyse rhétorique. Voici quelques exemples d'agents qui pourraient être ajoutés :

- **Agent d'Analyse de Style** : Analyse le style rhétorique utilisé dans un texte
- **Agent d'Analyse de Structure** : Analyse la structure argumentative d'un texte
- **Agent d'Analyse de Crédibilité** : Évalue la crédibilité des sources citées dans un texte
- **Agent d'Analyse de Biais** : Identifie les biais cognitifs dans un texte
- **Agent d'Analyse de Cohérence** : Évalue la cohérence logique d'un ensemble d'arguments

## Communication Inter-Agents

La communication entre les agents est un aspect crucial du système d'orchestration d'analyse rhétorique. Elle permet aux agents de collaborer efficacement pour produire une analyse complète et cohérente.

### État Partagé

Le principal mécanisme de communication entre les agents est l'état partagé. Il s'agit d'une structure de données commune qui contient les résultats de l'analyse et qui est accessible à tous les agents. L'état partagé comprend généralement :

- Le texte brut à analyser
- Les arguments identifiés
- Les sophismes identifiés
- Les ensembles de croyances formalisés
- Les réponses aux tâches d'analyse
- La conclusion finale

Chaque agent peut lire l'état partagé pour obtenir les informations dont il a besoin et y écrire ses propres résultats. Cette approche permet une communication asynchrone et découplée entre les agents.

### Protocoles de Communication

Outre l'état partagé, les agents peuvent communiquer directement entre eux via des protocoles définis. Ces protocoles spécifient le format et la structure des messages échangés entre les agents. Les principaux types de messages sont :

1. **Messages de Requête** : Un agent demande à un autre agent d'effectuer une tâche spécifique.
2. **Messages de Réponse** : Un agent répond à une requête d'un autre agent.
3. **Messages de Notification** : Un agent informe les autres agents d'un événement ou d'un changement d'état.
4. **Messages de Coordination** : L'orchestrateur envoie des messages pour coordonner les activités des agents.

### Interfaces de Communication

Les agents exposent des interfaces bien définies qui spécifient les méthodes qu'ils peuvent appeler et les données qu'ils peuvent échanger. Ces interfaces garantissent que les agents peuvent interagir de manière cohérente et prévisible.

Les principales interfaces sont :

1. **Interface d'Analyse** : Méthodes pour analyser un texte ou un argument
2. **Interface de Résultat** : Méthodes pour accéder aux résultats d'une analyse
3. **Interface d'État** : Méthodes pour lire et écrire dans l'état partagé
4. **Interface de Coordination** : Méthodes pour coordonner les activités des agents

## Orchestration des Agents

L'orchestration des agents est le processus de coordination des activités des agents spécialistes pour produire une analyse rhétorique complète et cohérente. L'orchestrateur est responsable de la gestion du flux de travail et de l'allocation des tâches aux agents appropriés.

### Rôle de l'Orchestrateur

L'orchestrateur a plusieurs responsabilités clés :

1. **Initialisation** : Initialiser l'état partagé et les agents spécialistes
2. **Allocation des Tâches** : Déterminer quels agents doivent être activés et dans quel ordre
3. **Coordination** : Coordonner les activités des agents et gérer les dépendances entre les tâches
4. **Gestion des Erreurs** : Gérer les erreurs et les exceptions qui peuvent survenir pendant l'analyse
5. **Finalisation** : Consolider les résultats et générer la conclusion finale

### Stratégies d'Orchestration

L'orchestrateur peut utiliser différentes stratégies pour coordonner les activités des agents :

1. **Orchestration Séquentielle** : Les agents sont activés séquentiellement, chacun attendant que le précédent ait terminé
2. **Orchestration Parallèle** : Les agents sont activés en parallèle lorsque c'est possible
3. **Orchestration Adaptative** : L'orchestrateur adapte sa stratégie en fonction des résultats intermédiaires
4. **Orchestration Basée sur les Événements** : Les agents sont activés en réponse à des événements spécifiques

### Exemple de Flux d'Orchestration

Voici un exemple de flux d'orchestration pour l'analyse d'un texte argumentatif :

1. L'orchestrateur initialise l'état partagé avec le texte à analyser
2. L'agent d'analyse contextuelle identifie les arguments et les sophismes potentiels
3. L'agent d'évaluation de sévérité évalue la gravité des sophismes identifiés
4. L'agent d'analyse de sophismes complexes identifie les combinaisons et les motifs de sophismes
5. L'agent d'analyse de résultats analyse les résultats et extrait des insights
6. L'agent de visualisation génère des visualisations des résultats
7. L'orchestrateur consolide les résultats et génère la conclusion finale

## Extension du Système

Le système d'orchestration d'analyse rhétorique est conçu pour être extensible, permettant l'ajout de nouveaux agents spécialistes pour couvrir des aspects supplémentaires de l'analyse rhétorique.

### Création d'un Nouvel Agent

Pour créer un nouvel agent spécialiste, suivez ces étapes :

1. **Définir le Rôle** : Déterminez le rôle spécifique que votre agent jouera dans l'analyse rhétorique
2. **Implémenter l'Interface** : Implémentez l'interface d'agent requise
3. **Définir les Méthodes** : Implémentez les méthodes spécifiques à votre agent
4. **Gérer l'État** : Définissez comment votre agent interagira avec l'état partagé
5. **Tester l'Agent** : Testez votre agent de manière isolée et en interaction avec d'autres agents

### Structure d'un Agent

Un agent spécialiste typique a la structure suivante :

```python
class MySpecialistAgent:
    def __init__(self):
        self.logger = logging.getLogger("MySpecialistAgent")
        self.logger.info("Agent initialisé.")
    
    def analyze(self, text, context):
        """
        Analyse un texte dans son contexte.
        
        Args:
            text: Texte à analyser
            context: Contexte du texte
            
        Returns:
            Résultats de l'analyse
        """
        # Implémentation spécifique à l'agent
        pass
    
    def update_state(self, state):
        """
        Met à jour l'état partagé avec les résultats de l'analyse.
        
        Args:
            state: État partagé à mettre à jour
            
        Returns:
            État partagé mis à jour
        """
        # Mise à jour de l'état partagé
        pass
```

### Intégration d'un Nouvel Agent

Pour intégrer un nouvel agent dans le système, suivez ces étapes :

1. **Enregistrer l'Agent** : Enregistrez votre agent auprès de l'orchestrateur
2. **Définir les Dépendances** : Spécifiez les dépendances de votre agent par rapport aux autres agents
3. **Configurer l'Orchestration** : Mettez à jour la configuration de l'orchestrateur pour inclure votre agent
4. **Tester l'Intégration** : Testez l'intégration de votre agent dans le système complet

### Exemple d'Extension

Voici un exemple d'extension du système avec un nouvel agent d'analyse de biais :

```python
class BiasAnalyzerAgent:
    def __init__(self):
        self.logger = logging.getLogger("BiasAnalyzerAgent")
        self.logger.info("Agent d'analyse de biais initialisé.")
    
    def analyze_bias(self, text, context):
        """
        Analyse les biais cognitifs dans un texte.
        
        Args:
            text: Texte à analyser
            context: Contexte du texte
            
        Returns:
            Biais identifiés
        """
        # Implémentation de l'analyse de biais
        pass
    
    def update_state(self, state):
        """
        Met à jour l'état partagé avec les biais identifiés.
        
        Args:
            state: État partagé à mettre à jour
            
        Returns:
            État partagé mis à jour
        """
        # Mise à jour de l'état partagé
        pass
```

## Exemples d'Utilisation des Agents

Cette section présente des exemples concrets d'utilisation des agents spécialistes pour analyser des textes argumentatifs.

### Exemple 1 : Analyse d'un Discours Commercial

```python
# Importer les outils d'analyse rhétorique
from argumentiation_analysis.agents.tools.analysis import (
    ContextualFallacyAnalyzer,
    FallacySeverityEvaluator,
    ComplexFallacyAnalyzer,
    RhetoricalResultAnalyzer,
    RhetoricalResultVisualizer
)

# Texte à analyser
text = """
Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà, 
donc vous devriez l'essayer aussi. Si vous n'utilisez pas ce produit, vous risquez de souffrir de 
problèmes de santé graves.
"""

# Contexte
context = "Discours commercial pour un produit controversé"

# 1. Analyse contextuelle des sophismes
contextual_analyzer = ContextualFallacyAnalyzer()
contextual_fallacies = contextual_analyzer.identify_contextual_fallacies(text, context)

# 2. Évaluation de la gravité des sophismes
severity_evaluator = FallacySeverityEvaluator()
for fallacy in contextual_fallacies:
    severity = severity_evaluator.evaluate_severity(
        fallacy["fallacy_type"],
        fallacy["context_text"],
        context
    )
    print(f"{fallacy['fallacy_type']}: {severity['severity_level']} ({severity['final_score']:.2f})")

# 3. Analyse des sophismes complexes
complex_analyzer = ComplexFallacyAnalyzer()
combined_fallacies = complex_analyzer.identify_combined_fallacies(text)
for fallacy in combined_fallacies:
    print(f"{fallacy['combination_name']}: {fallacy['description']}")
```

### Exemple 2 : Génération d'un Rapport d'Analyse

```python
# Importer les outils d'analyse rhétorique
from argumentiation_analysis.agents.tools.analysis import (
    RhetoricalResultAnalyzer,
    RhetoricalResultVisualizer
)

# État partagé contenant les résultats de l'analyse
state = {
    "raw_text": text,
    "identified_arguments": {
        "arg_1": "Les experts sont unanimes : ce produit est sûr et efficace.",
        "arg_2": "Des millions de personnes utilisent déjà ce produit.",
        "arg_3": "Si vous n'utilisez pas ce produit, vous risquez de souffrir de problèmes de santé graves."
    },
    "identified_fallacies": {
        "fallacy_1": {
            "type": "Appel à l'autorité",
            "justification": "L'argument s'appuie sur l'autorité des experts sans fournir de preuves concrètes.",
            "target_argument_id": "arg_1"
        },
        "fallacy_2": {
            "type": "Appel à la popularité",
            "justification": "L'argument s'appuie sur la popularité du produit pour justifier son efficacité.",
            "target_argument_id": "arg_2"
        },
        "fallacy_3": {
            "type": "Faux dilemme",
            "justification": "L'argument présente une fausse alternative entre utiliser le produit ou souffrir de problèmes de santé.",
            "target_argument_id": "arg_3"
        }
    }
}

# Analyser les résultats
result_analyzer = RhetoricalResultAnalyzer()
analysis_results = result_analyzer.analyze_results(state)
summary = result_analyzer.generate_summary(state)

# Générer des visualisations
result_visualizer = RhetoricalResultVisualizer()
visualizations = result_visualizer.generate_all_visualizations(state)
html_report = result_visualizer.generate_html_report(state)

# Sauvegarder le rapport HTML
with open("rapport_analyse_rhetorique.html", "w", encoding="utf-8") as f:
    f.write(html_report)
```

### Exemple 3 : Orchestration Complète

```python
# Importer les outils d'analyse rhétorique et l'orchestrateur
from argumentiation_analysis.agents.tools.analysis import (
    ContextualFallacyAnalyzer,
    FallacySeverityEvaluator,
    ComplexFallacyAnalyzer,
    RhetoricalResultAnalyzer,
    RhetoricalResultVisualizer
)
from argumentiation_analysis.orchestration.analysis_runner import AnalysisRunner

# Texte à analyser
text = """
Les experts sont unanimes : ce produit est sûr et efficace. Des millions de personnes l'utilisent déjà, 
donc vous devriez l'essayer aussi. Si vous n'utilisez pas ce produit, vous risquez de souffrir de 
problèmes de santé graves.
"""

# Créer l'orchestrateur
orchestrator = AnalysisRunner()

# Enregistrer les agents
orchestrator.register_agent("contextual_analyzer", ContextualFallacyAnalyzer())
orchestrator.register_agent("severity_evaluator", FallacySeverityEvaluator())
orchestrator.register_agent("complex_analyzer", ComplexFallacyAnalyzer())
orchestrator.register_agent("result_analyzer", RhetoricalResultAnalyzer())
orchestrator.register_agent("result_visualizer", RhetoricalResultVisualizer())

# Exécuter l'analyse
results = orchestrator.run_analysis(text, context="Discours commercial pour un produit controversé")

# Accéder aux résultats
print(f"Arguments identifiés: {len(results['identified_arguments'])}")
print(f"Sophismes identifiés: {len(results['identified_fallacies'])}")
print(f"Qualité de l'analyse: {results['quality_evaluation']['quality_level']}")

# Générer un rapport
html_report = results["html_report"]
with open("rapport_analyse_rhetorique.html", "w", encoding="utf-8") as f:
    f.write(html_report)
```

Ces exemples illustrent comment les agents spécialistes peuvent être utilisés individuellement ou ensemble pour analyser des textes argumentatifs et générer des rapports d'analyse rhétorique.