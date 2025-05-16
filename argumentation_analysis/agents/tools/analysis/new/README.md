# Nouveaux Outils d'Analyse Rhétorique

Ce répertoire contient de nouveaux outils d'analyse rhétorique développés pour enrichir les capacités d'analyse argumentative du système. Ces outils introduisent des fonctionnalités innovantes qui complètent les outils existants et améliorés.

## Vue d'ensemble

Les nouveaux outils d'analyse rhétorique se concentrent sur :
- L'analyse sémantique des arguments (modèle de Toulmin)
- L'évaluation de la cohérence entre arguments
- La visualisation interactive des structures argumentatives
- La détection contextuelle avancée des sophismes

Ces outils utilisent des approches modernes en traitement du langage naturel, en analyse sémantique et en visualisation de données pour offrir des insights plus profonds sur les structures argumentatives.

## Outils disponibles

### SemanticArgumentAnalyzer

L'analyseur sémantique d'arguments implémente le modèle de Toulmin pour analyser la structure sémantique des arguments et identifier les relations entre leurs composants :
- Identification des revendications (claims)
- Extraction des données/preuves (data/evidence)
- Identification des garanties (warrants)
- Reconnaissance des fondements (backings)
- Détection des réfutations (rebuttals)
- Analyse des qualificateurs (qualifiers)

```python
from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import SemanticArgumentAnalyzer

# Initialiser l'analyseur
analyzer = SemanticArgumentAnalyzer()

# Analyser un argument selon le modèle de Toulmin
toulmin_structure = analyzer.analyze_toulmin_structure(
    text="Bien que la plupart des oiseaux puissent voler (qualificateur), 
          les pingouins ne peuvent pas voler (revendication) 
          car leurs ailes sont adaptées à la nage plutôt qu'au vol (données). 
          Les ailes des oiseaux doivent avoir certaines caractéristiques aérodynamiques 
          pour permettre le vol (garantie), 
          comme l'ont démontré de nombreuses études en biomécanique (fondement), 
          à moins qu'il ne s'agisse d'espèces artificiellement sélectionnées pour d'autres traits (réfutation)."
)

# Visualiser la structure de Toulmin
toulmin_diagram = analyzer.visualize_toulmin_structure(toulmin_structure)
```

### ArgumentCoherenceEvaluator

L'évaluateur de cohérence des arguments analyse la cohérence logique, sémantique et contextuelle entre différents arguments :
- Détection des contradictions entre arguments
- Évaluation de la cohérence sémantique
- Analyse des relations de support et d'opposition
- Mesure de la force des liens entre arguments

```python
from argumentation_analysis.agents.tools.analysis.new.argument_coherence_evaluator import ArgumentCoherenceEvaluator

# Initialiser l'évaluateur
evaluator = ArgumentCoherenceEvaluator()

# Évaluer la cohérence entre plusieurs arguments
coherence_score = evaluator.evaluate_coherence(
    arguments=[
        "Le réchauffement climatique est principalement causé par les activités humaines.",
        "Les émissions de CO2 ont augmenté de manière significative depuis la révolution industrielle.",
        "Nous devons réduire notre empreinte carbone pour limiter le réchauffement climatique."
    ]
)

# Identifier les contradictions potentielles
contradictions = evaluator.identify_contradictions(
    arguments=[
        "Le réchauffement climatique est principalement causé par les activités humaines.",
        "Les variations de température sont des phénomènes naturels cycliques.",
        "L'activité humaine n'a qu'un impact négligeable sur le climat global."
    ]
)
```

### ArgumentStructureVisualizer

Le visualiseur de structure argumentative permet de représenter graphiquement les relations entre arguments, prémisses et conclusions :
- Création de graphes d'arguments interactifs
- Visualisation des relations de support et d'attaque
- Représentation des sophismes identifiés
- Génération de diagrammes exportables

```python
from argumentation_analysis.agents.tools.analysis.new.argument_structure_visualizer import ArgumentStructureVisualizer

# Initialiser le visualiseur
visualizer = ArgumentStructureVisualizer()

# Créer une structure d'arguments
argument_structure = {
    "nodes": [
        {"id": "A1", "type": "premise", "text": "La liberté d'expression est un droit fondamental"},
        {"id": "A2", "type": "premise", "text": "Les droits fondamentaux doivent être protégés"},
        {"id": "C1", "type": "conclusion", "text": "La liberté d'expression doit être protégée"}
    ],
    "edges": [
        {"source": "A1", "target": "C1", "type": "support"},
        {"source": "A2", "target": "C1", "type": "support"}
    ]
}

# Générer une visualisation
visualization = visualizer.create_visualization(argument_structure)

# Exporter la visualisation
visualizer.export_visualization(visualization, format="html", path="argument_structure.html")
```

### ContextualFallacyDetector

Le détecteur de sophismes contextuels se concentre spécifiquement sur les sophismes qui dépendent fortement du contexte :
- Analyse des facteurs contextuels (culturels, sociaux, historiques)
- Détection des sophismes qui ne sont pas évidents hors contexte
- Évaluation de l'adéquation des arguments au contexte

```python
from argumentation_analysis.agents.tools.analysis.new.contextual_fallacy_detector import ContextualFallacyDetector

# Initialiser le détecteur
detector = ContextualFallacyDetector()

# Détecter les sophismes contextuels
fallacies = detector.detect_contextual_fallacies(
    text="Ce traitement a été utilisé pendant des siècles, il est donc sûr et efficace.",
    context="Discussion sur un traitement médical alternatif",
    audience="Public non-spécialiste",
    domain="Santé"
)

# Analyser l'adéquation contextuelle
contextual_fit = detector.analyze_contextual_fit(
    argument="Cette étude scientifique démontre l'efficacité du traitement.",
    context="Forum public sur la santé",
    audience="Public général sans formation scientifique"
)
```

## Intégration avec le modèle de Toulmin

Le modèle de Toulmin, implémenté principalement dans le `SemanticArgumentAnalyzer`, offre un cadre structuré pour analyser les arguments en identifiant leurs composants clés :

1. **Revendication (Claim)** : L'assertion que l'on cherche à établir
2. **Données (Data)** : Les faits ou preuves qui soutiennent la revendication
3. **Garantie (Warrant)** : Le principe qui relie les données à la revendication
4. **Fondement (Backing)** : Le support pour la garantie
5. **Réfutation (Rebuttal)** : Les conditions qui pourraient invalider la revendication
6. **Qualificateur (Qualifier)** : L'expression du degré de certitude de la revendication

Cette approche permet une analyse plus fine et structurée des arguments, dépassant la simple identification des sophismes pour comprendre la construction logique et rhétorique des arguments.

## Intégration avec les autres composants

Ces nouveaux outils s'intègrent avec :
- Les outils rhétoriques existants et améliorés
- L'architecture hiérarchique via les adaptateurs appropriés
- Les agents spécialistes, notamment l'agent Informel
- Le système de visualisation pour la présentation des résultats

## Développement

Pour étendre ces nouveaux outils :

1. Respectez les conventions d'interface établies
2. Documentez clairement les nouvelles fonctionnalités
3. Ajoutez des tests unitaires et d'intégration
4. Assurez la compatibilité avec l'écosystème existant

## Voir aussi

- [Documentation des outils d'analyse rhétorique de base](../README.md)
- [Documentation des outils d'analyse rhétorique améliorés](../enhanced/README.md)
- [Documentation de l'analyseur sémantique d'arguments](./semantic_argument_analyzer.py)
- [Documentation de l'architecture hiérarchique](../../../../orchestration/hierarchical/README.md)