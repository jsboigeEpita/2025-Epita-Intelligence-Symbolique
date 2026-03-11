# Analyseur d'Arguments (Argument Parser)

Ce document détaille le processus d'identification, d'extraction, de structuration et de validation des arguments (ou "extraits") à partir des textes sources au sein du système. Le composant principal responsable de cette tâche est l'`ExtractAgent`.

## 1. Objectif et Rôle

L'analyseur d'arguments a pour objectif de localiser et d'isoler des segments de texte pertinents (arguments, preuves, énoncés clés) au sein d'un corpus plus large. Ces extraits structurés servent ensuite de base aux analyses rhétoriques, fallacieuses ou logiques effectuées par d'autres agents.

## 2. Composants Clés

### 2.1 `ExtractAgent`

*   **Source :** [`../../argumentation_analysis/agents/core/extract/extract_agent.py`](../../argumentation_analysis/agents/core/extract/extract_agent.py)
*   **Rôle :** Orchestre le processus d'extraction. Il utilise des fonctions sémantiques pour interagir avec les LLMs et des fonctions natives pour le traitement de texte.
*   **Fonctionnalités principales :**
    *   Proposition de marqueurs (début/fin) pour un extrait basé sur son nom/description.
    *   Validation de la pertinence d'un extrait proposé.
    *   Gestion des textes volumineux par découpage en blocs et recherche contextuelle.
    *   Réparation d'extraits existants.
    *   Mise à jour et ajout de nouveaux extraits.

### 2.2 `ExtractAgentPlugin`

*   **Source :** [`../../argumentation_analysis/agents/core/extract/extract_definitions.py`](../../argumentation_analysis/agents/core/extract/extract_definitions.py) (défini dans ce fichier)
*   **Rôle :** Fournit des fonctions natives à l'`ExtractAgent` pour des opérations textuelles spécifiques sans appel LLM :
    *   `find_similar_markers`: Recherche des chaînes de caractères similaires.
    *   `search_text_dichotomically`: Recherche un terme dans de grands textes par analyse de blocs.
    *   `extract_blocks`: Divise un texte en blocs avec chevauchement.

### Pré-traitement des Textes Volumineux pour l'Extraction

Avant que l'`ExtractAgent` ([`../../argumentation_analysis/agents/core/extract/extract_agent.py`](../../argumentation_analysis/agents/core/extract/extract_agent.py:101)) ne soumette des requêtes au LLM pour l'identification des marqueurs d'extraits, un pré-traitement est appliqué aux textes sources volumineux. Ce pré-traitement vise à réduire la quantité de contexte fournie au LLM tout en conservant les informations les plus pertinentes.

*   **Segmentation en Blocs :** La fonction `extract_blocks` ([`../../argumentation_analysis/agents/core/extract/extract_definitions.py:291`](../../argumentation_analysis/agents/core/extract/extract_definitions.py:291)) du `ExtractAgentPlugin` ([`../../argumentation_analysis/agents/core/extract/extract_definitions.py:135`](../../argumentation_analysis/agents/core/extract/extract_definitions.py:135)) divise le texte source en blocs de taille définie (par exemple, 500 caractères) avec un certain chevauchement (par exemple, 50 caractères). Cette segmentation permet de traiter le texte par morceaux gérables.
*   **Identification des Blocs Pertinents :** Pour un `extract_name` donné, des mots-clés sont dérivés de ce nom. La fonction `search_text_dichotomically` ([`../../argumentation_analysis/agents/core/extract/extract_definitions.py:228`](../../argumentation_analysis/agents/core/extract/extract_definitions.py:228)) (ou une logique similaire au sein de l'agent) est ensuite utilisée pour identifier les blocs de texte qui contiennent ces mots-clés.
*   **Construction du Contexte pour le LLM :** Seuls les blocs jugés pertinents (ou une sélection d'entre eux, ainsi que potentiellement le début et la fin du document original) sont concaténés pour former le `extract_context` qui sera effectivement soumis au LLM lors de l'appel à la fonction sémantique `extract_from_name_semantic`.

Cette approche de pré-sélection et de segmentation du contexte est cruciale pour gérer efficacement les limitations de taille de contexte des LLMs et pour optimiser les coûts et les performances lors de l'analyse de documents longs. Elle garantit que l'agent se concentre sur les parties les plus prometteuses du texte source pour l'extraction.
### 2.3 Utilitaires d'Extraction

*   **Source :** `argumentation_analysis/ui/extract_utils.py` (utilisé par `ExtractAgent`)
*   **Rôles :**
    *   `extract_text_with_markers`: Fonction clé qui extrait le segment de texte une fois les marqueurs de début et de fin identifiés.
    *   `load_source_text`: Charge le contenu textuel des sources.
    *   `find_similar_text`: Utilisé par `ExtractAgentPlugin` pour la recherche de similarité.

## 3. Processus d'Extraction et de Validation

Le processus typique pour extraire et valider un argument est le suivant :

1.  **Définition de l'Extrait :** Le processus peut commencer avec une `ExtractDefinition` (voir section 4.1) qui spécifie le nom de l'extrait à trouver et la source.
2.  **Proposition de Marqueurs (`ExtractAgent.extract_from_name`) :**
    *   L'`ExtractAgent` utilise la fonction sémantique `extract_from_name_semantic` (prompt : [`EXTRACT_FROM_NAME_PROMPT`](../../argumentation_analysis/agents/core/extract/prompts.py)) pour demander à un LLM de proposer des marqueurs (`start_marker`, `end_marker`) et optionnellement un `template_start` pour localiser l'extrait dans le texte source.
    *   Pour les textes volumineux, le contexte fourni au LLM est une sélection de blocs pertinents identifiés par `ExtractAgentPlugin`.
    *   Le LLM doit retourner une réponse JSON contenant `start_marker`, `end_marker`, `template_start` (optionnel), et une `explanation`.
3.  **Extraction du Texte :**
    *   Les marqueurs proposés sont utilisés par la fonction `extract_text_with_markers` (de `ui.extract_utils`) pour extraire le segment de texte correspondant.
4.  **Validation de l'Extrait (`ExtractAgent.extract_from_name` continue) :**
    *   L'extrait de texte obtenu, ainsi que les marqueurs et l'explication de l'étape de proposition, sont soumis à la fonction sémantique `validate_extract_semantic` (prompt : [`VALIDATE_EXTRACT_PROMPT`](../../argumentation_analysis/agents/core/extract/prompts.py)).
    *   Le LLM évalue si l'extrait est pertinent par rapport au nom/description initial de l'extrait.
    *   Le LLM doit retourner une réponse JSON contenant un booléen `valid` et une `reason` pour sa décision.
5.  **Résultat de l'Extraction :**
    *   L'ensemble du processus aboutit à un objet `ExtractResult` (voir section 4.2) qui contient le statut (`valid`, `rejected`, `error`), les marqueurs, le texte extrait, et les explications.

## 4. Formats de Données Clés

### 4.1 `ExtractDefinition`

*   **Source :** [`../../argumentation_analysis/agents/core/extract/extract_definitions.py`](../../argumentation_analysis/agents/core/extract/extract_definitions.py)
*   **Rôle :** Décrit un extrait à rechercher.
*   **Structure :**
    *   `source_name` (str): Nom de la source du texte.
    *   `extract_name` (str): Nom ou description de l'extrait.
    *   `start_marker` (str): Le marqueur textuel indiquant le début de l'extrait.
    *   `end_marker` (str): Le marqueur textuel indiquant la fin de l'extrait.
    *   `template_start` (str, optionnel): Un template qui peut précéder le `start_marker`.
    *   `description` (str, optionnel): Description de ce que représente l'extrait.

### 4.2 `ExtractResult`

*   **Source :** [`../../argumentation_analysis/agents/core/extract/extract_definitions.py`](../../argumentation_analysis/agents/core/extract/extract_definitions.py)
*   **Rôle :** Encapsule le résultat complet d'une opération d'extraction et de validation.
*   **Structure :**
    *   `source_name` (str): Nom de la source.
    *   `extract_name` (str): Nom de l'extrait.
    *   `status` (str): Statut ("valid", "rejected", "error").
    *   `message` (str): Message descriptif.
    *   `start_marker` (str): Marqueur de début utilisé/proposé.
    *   `end_marker` (str): Marqueur de fin utilisé/proposé.
    *   `template_start` (str): Template de début utilisé/proposé.
    *   `explanation` (str): Explication de l'agent d'extraction.
    *   `extracted_text` (str): Le texte effectivement extrait.

## 5. Stockage dans l'État Partagé

Une fois les arguments extraits et validés sous forme d'`ExtractResult`, ils peuvent être intégrés dans l'état partagé global (`RhetoricalAnalysisState` défini dans [`../../argumentation_analysis/core/shared_state.py`](../../argumentation_analysis/core/shared_state.py)).

*   La méthode `RhetoricalAnalysisState.add_argument(description: str)` stocke une description textuelle de l'argument.
*   La méthode `RhetoricalAnalysisState.add_extract(name: str, content: str)` stocke le nom et le contenu textuel de l'extrait.

Il est important de noter que `RhetoricalAnalysisState` semble stocker une version simplifiée des informations par rapport à la richesse de `ExtractResult`. La manière exacte dont un `ExtractResult` est transformé pour être stocké dans `identified_arguments` ou `extracts` de `RhetoricalAnalysisState` mériterait d'être précisée (par exemple, est-ce que `ExtractResult.extracted_text` devient la `description` dans `identified_arguments` ?).

## 6. Interaction avec d'Autres Composants

*   Les extraits validés et stockés dans `RhetoricalAnalysisState` sont ensuite utilisés par d'autres agents (ex: [`InformalAnalysisAgent`](../../argumentation_analysis/agents/core/informal/informal_agent.py), agents logiques) pour des analyses plus poussées.
*   La documentation sur la collaboration entre agents ([`./synthese_collaboration.md`](./synthese_collaboration.md)) détaille comment ces agents interagissent via l'état partagé.

## 7. Points d'Attention et Évolutions Possibles

*   Clarifier la transformation/mapping entre `ExtractResult` et les structures `identified_arguments` / `extracts` dans `RhetoricalAnalysisState`.
*   Détailler les stratégies de réparation d'extraits (`ExtractAgent.repair_extract`).
*   Expliquer plus en détail les prompts `EXTRACT_FROM_NAME_PROMPT` et `VALIDATE_EXTRACT_PROMPT`.