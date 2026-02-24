# Moteur de Raisonnement (Reasoning Engine)

## 1. Introduction

Le moteur de raisonnement est un ensemble de composants et de capacités au sein du système d'analyse rhétorique conçu pour évaluer la structure logique, la validité, la cohérence et pour effectuer des inférences à partir des arguments et des connaissances fournis.

**Objectifs principaux :**
*   Fournir des capacités d'analyse logique formelle (par exemple, via la logique propositionnelle).
*   Détecter les contradictions et les incohérences dans les énoncés ou ensembles d'énoncés.
*   Valider la structure et la force des arguments.
*   Permettre des inférences logiques à partir de prémisses données.
*   Soutenir les agents d'analyse en leur fournissant des évaluations logiques robustes.

L'intégration d'un moteur de raisonnement est cruciale pour aller au-delà de l'analyse de surface des arguments et pour évaluer leur fondement logique.

## 2. Capacités Principales

Le moteur de raisonnement offre, ou vise à offrir, les capacités suivantes :

*   **Logique Propositionnelle :**
    *   Vérification de la validité d'arguments propositionnels.
    *   Test de satisfiabilité d'ensembles de propositions.
    *   Inférence de conclusions à partir de prémisses (par exemple, `P, P -> Q |= Q`).
    *   Détection de tautologies et de contradictions.
*   **Analyse de la Validité des Arguments :** Évaluation de la correction formelle des inférences présentées dans un argument.
*   **Détection de Contradictions :** Identification d'affirmations mutuellement exclusives au sein d'un texte ou par rapport à une base de connaissances.
*   **Inférences Logiques :** Déduction de nouvelles informations à partir d'informations existantes en utilisant des règles logiques.
*   **(Optionnel) Intégration avec d'autres formes de raisonnement :** Le système pourrait être étendu pour inclure des logiques non-monotones, des logiques descriptives, ou d'autres formalismes si nécessaire.

## 3. Composants Clés

Les capacités de raisonnement sont principalement implémentées et orchestrées par les composants suivants :

### 3.1. `PropositionalLogicAgent`

*   **Source :** [`argumentation_analysis/agents/core/logic/propositional_logic_agent.py`](../../argumentation_analysis/agents/core/logic/propositional_logic_agent.py)
*   **Rôle :** Agent spécialisé dans l'application des principes de la logique propositionnelle. Il est responsable de la conversion des arguments en langage naturel (ou des représentations structurées) en formules propositionnelles, de l'exécution des opérations logiques, et de l'interprétation des résultats.
*   **Interface (Méthodes Principales Attendues) :**
    *   `check_validity(premises: List[str], conclusion: str) -> bool`: Vérifie si une conclusion découle logiquement d'un ensemble de prémisses.
    *   `is_satisfiable(formulas: List[str]) -> bool`: Détermine si un ensemble de formules propositionnelles peut être vrai simultanément.
    *   `find_contradictions(formulas: List[str]) -> List[Tuple[str, str]]`: Identifie les paires de formules contradictoires.
    *   `infer(premises: List[str], query: str) -> Optional[bool]`: Tente d'inférer la vérité d'une requête à partir de prémisses.
*   **Prompts/Plugins :** Cet agent peut s'appuyer sur des prompts spécifiques pour guider les LLMs dans la traduction du langage naturel en logique formelle, ou utiliser des plugins pour interagir avec des solveurs logiques.
*   **Exemple d'Utilisation (Conceptuel) :**
    ```python
    # from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
    # from project_core.services.llm_service_factory import LLMServiceFactory # ou autre service pertinent

    # llm_service = LLMServiceFactory.create_service("default_llm")
    # pl_agent = PropositionalLogicAgent(llm_service=llm_service) # ou avec un solveur dédié

    # premises = ["If it is raining, then the ground is wet.", "It is raining."]
    # conclusion = "The ground is wet."
    # is_valid = pl_agent.check_validity(premises, conclusion)
    # print(f"L'argument est valide : {is_valid}") # Attendu: True
    ```

### 3.2. Outils d'Analyse avec Capacités d'Inférence (si applicable)

Certains outils d'analyse, bien que principalement axés sur d'autres aspects (comme les sophismes ou la rhétorique), peuvent intégrer des formes de raisonnement :

*   **`ComplexFallacyAnalyzer`** ([`../../argumentation_analysis/agents/tools/analysis/complex_fallacy_analyzer.py`](../../argumentation_analysis/agents/tools/analysis/complex_fallacy_analyzer.py)) : Peut effectuer des inférences pour décomposer des arguments complexes ou identifier des contradictions implicites qui sous-tendent certains sophismes.
*   **`RhetoricalResultAnalyzer`** ([`../../argumentation_analysis/agents/tools/analysis/rhetorical_result_analyzer.py`](../../argumentation_analysis/agents/tools/analysis/rhetorical_result_analyzer.py)) : Pourrait analyser la cohérence logique des stratégies rhétoriques employées ou inférer les intentions de l'orateur basées sur des patterns logiques.

La documentation spécifique de ces outils devrait détailler leurs capacités de raisonnement respectives.

### 3.3. Intégrations Externes (si applicable)

Le moteur de raisonnement peut s'interfacer avec des bibliothèques ou des services externes pour des capacités de raisonnement avancées :

*   **Solveurs Logiques Externes :**
    *   Via des mécanismes d'interaction avec des bibliothèques Java comme celles de `TweetyProject` pour des tâches de raisonnement spécifiques (par exemple, argumentation formelle, logiques non-monotones). L'interaction avec la JVM et les bibliothèques Tweety est gérée par le composant `TweetyBridge`. (Pour plus de détails, voir le document sur le [`Pont Tweety (Tweety Bridge)`](./tweety_bridge.md).)
    *   L'intégration avec des bibliothèques Python comme `TweetyProject` (par exemple, via des adaptateurs spécifiques) est également gérée par le [`Pont Tweety (Tweety Bridge)`](./tweety_bridge.md) lorsque cela concerne l'interaction avec les fonctionnalités de Tweety.
    *   L'intégration doit décrire comment les problèmes sont formulés pour ces solveurs et comment les résultats sont récupérés et interprétés.

## 4. Interaction avec d'Autres Systèmes

### 4.1. Interface de Base de Connaissances ([`knowledge_base_interface.md`](./knowledge_base_interface.md))

Le moteur de raisonnement peut interagir étroitement avec l'interface de la base de connaissances :
*   **Chargement d'Axiomes et de Faits :** La base de connaissances peut fournir un ensemble d'axiomes, de règles, ou de faits établis que le moteur de raisonnement utilise comme fondement pour ses analyses.
*   **Vérification de la Cohérence :** Les inférences produites par le moteur de raisonnement peuvent être vérifiées par rapport aux informations stockées dans la base de connaissances.
*   **Flux de Données :** Un argument ou un ensemble de propositions est soumis au moteur de raisonnement. Celui-ci peut interroger la base de connaissances pour obtenir un contexte pertinent ou des règles applicables avant de retourner son analyse.

### 4.2. Agents Spécialistes et Orchestration

*   Les agents spécialistes (par exemple, un agent d'évaluation critique) peuvent invoquer le moteur de raisonnement pour obtenir une analyse logique d'un argument spécifique.
*   L'orchestrateur ([`synthese_collaboration.md`](./synthese_collaboration.md)) peut diriger les flux de données vers le moteur de raisonnement dans le cadre d'un pipeline d'analyse plus large, par exemple, après une première identification des prémisses et conclusions par un autre agent.

## 5. Exemples d'Usage et Scénarios

*   **Détection de Contradictions dans un Débat :**
    *   Input : Transcription d'un débat.
    *   Processus : Extraction des affirmations clés de chaque participant, conversion en formules logiques, utilisation du `PropositionalLogicAgent` pour identifier les contradictions.
    *   Output : Liste des paires d'affirmations contradictoires.
*   **Validation de la Structure Logique d'un Argument Écrit :**
    *   Input : Un essai argumentatif.
    *   Processus : Identification des prémisses majeures et mineures et de la conclusion principale. Le `PropositionalLogicAgent` vérifie si la conclusion découle validement des prémisses.
    *   Output : Évaluation de la validité logique de l'argument.
*   **Inférence de Conclusions Implicites :**
    *   Input : Un ensemble de faits (par exemple, "Tous les hommes sont mortels", "Socrate est un homme").
    *   Processus : Le moteur de raisonnement infère "Socrate est mortel".
    *   Output : La conclusion inférée.

## 6. Limitations et Développements Futurs

*   **Limitations Actuelles :**
    *   Dépendance à la qualité de la traduction du langage naturel en représentations logiques.
    *   Complexité de la gestion de l'ambiguïté et du contexte du langage naturel.
    *   (Si applicable) Portée limitée des formalismes logiques actuellement supportés.
*   **Pistes d'Amélioration :**
    *   Intégration de techniques de NLP plus avancées pour l'extraction de structures logiques.
    *   Support pour des logiques plus expressives (prédicats, modales, temporelles).
    *   Amélioration de l'interaction avec la base de connaissances pour un raisonnement contextuel plus riche.
    *   Développement d'interfaces utilisateur pour faciliter la soumission de problèmes de raisonnement et l'interprétation des résultats.