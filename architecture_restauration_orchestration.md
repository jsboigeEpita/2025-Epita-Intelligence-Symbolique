# Partie 1 : Restauration de l'Orchestration

## Contexte : Le Paiement d'une Dette Architecturale

L'investigation initiale, déclenchée par un bug fonctionnel, a mis en lumière une **régression architecturale majeure** : l'abandon d'une orchestration moderne basée sur `AgentGroupChat` au profit d'une boucle de contrôle manuelle, rigide et fragile. Cette décision, motivée par une crainte de l'instabilité de l'API `semantic-kernel` à l'époque, a introduit une dette technique considérable.

L'objectif de cette section est de détailler le plan de **restauration** de l'architecture d'origine, en s'appuyant sur les composants désormais stables et éprouvés de `semantic-kernel` pour construire un système d'orchestration robuste, déclaratif et intelligent.

## Analyse Comparative : De la Boucle Manuelle à l'Orchestration Stratégique

Pour comprendre la portée de la restauration, il est essentiel de comparer l'approche abandonnée (la boucle manuelle) à la nouvelle architecture cible.

```mermaid
graph TD
    subgraph "Schéma de la Régression (Boucle Manuelle Fragile)"
        A[analysis_runner.py] -- "boucle `for` sur `max_turns`" --> B{"Logique Impérative"};
        B -- "Agent X a parlé, qui est le suivant ?" --> C{"Parsing de la réponse précédente"};
        C -- "Si `designate_next_agent(...)` trouvé" --> D[Appel direct à l'Agent Y];
        C -- "Sinon, logique par défaut" --> E[Appel à l'Agent Z];
        D --> B;
        E --> B;
    end

    subgraph "Architecture Cible Restaurée (Déclarative et Robuste)"
        F[analysis_runner.py] -- "invoke(tâche)" --> G{AgentGroupChat};
        G -- "À qui le tour ?" --> H[selection_strategy.next(...)];
        H -- "agent_choisi" --> G;
        G -- "Devons-nous arrêter ?" --> I[termination_strategy.should_terminate(...)];
        I -- "True" --> J((Fin));
        I -- "False" --> G;
    end

    style A fill:#f9d,stroke:#333,stroke-width:2px
    style G fill:#9cf,stroke:#333,stroke-width:2px
```

### L'Ancienne Logique : Impérative et Fragile

L'orchestration manuelle reposait sur un principe simple mais dangereux :
1.  **Une boucle `for` rigide** qui dictait le nombre maximum de tours.
2.  **Une logique de décision codée en dur** dans `analysis_runner.py`.
3.  **Une dépendance à un parsing de texte fragile** (expression régulière) pour extraire de la réponse d'un agent le nom de son successeur désigné.

Ce système était **fragile** (tout changement dans le format de la réponse du `ProjectManagerAgent` cassait l'orchestration), **rigide** (ajouter un nouvel agent nécessitait de modifier la logique centrale) et **illisible** (la logique de collaboration était noyée dans des `if/else`).

### L'Approche `AgentGroupChat` : Déclarative et Robuste

La restauration architecturale acte le remplacement de cette boucle par une approche déclarative. Le développeur **ne code plus le "comment" mais déclare le "quoi"**. La logique est déléguée à des composants spécialisés :

-   **`AgentGroupChat`** : C'est le chef d'orchestre central. Son unique rôle est de maintenir le cycle de vie de la conversation. Comme l'illustre son code source, sa méthode `invoke` est une boucle qui, à chaque tour, délègue les décisions critiques.

    ```python
    # Fichier : semantic_kernel/agents/group_chat/agent_group_chat.py (extrait simplifié)
    ...
    async def invoke(...):
        ...
        for _ in range(self.termination_strategy.maximum_iterations):
            # 1. DÉLÉGATION DE LA SÉLECTION
            selected_agent = await self.selection_strategy.next(self.agents, self.history.messages)

            # 2. EXÉCUTION DE L'AGENT CHOISI
            async for message in super().invoke_agent(selected_agent):
                ...
                # 3. DÉLÉGATION DE LA TERMINAISON
                self.is_complete = await self.termination_strategy.should_terminate(selected_agent, self.history.messages)
                yield message

            if self.is_complete:
                break
    ```

-   **`SelectionStrategy` et `TerminationStrategy`** : Ces objets injectés sont les "cerveaux" de l'orchestration. Ils encapsulent la logique de décision, la rendant modulaire, interchangeable et testable indépendamment.

## Ingénierie des Stratégies pour un Contrôle Intelligent

L'efficacité de `AgentGroupChat` repose sur la configuration de ses stratégies. Pour notre cas d'usage, nous restaurons le contrôle intelligent en combinant des stratégies basées sur des fonctions sémantiques.

### 1. La Sélection d'Agent via `KernelFunctionSelectionStrategy`

Pour qu'un LLM agisse comme un chef d'orchestre (le rôle de l'ancien `ProjectManagerAgent`), cette stratégie est idéale.

**Mécanisme interne :**
Comme l'illustre le code de [`kernel_function_selection_strategy.py`](C:/Users/jsboi/.conda/envs/projet-is-new/Lib/site-packages/semantic_kernel/agents/strategies/selection/kernel_function_selection_strategy.py:1), la stratégie prépare et exécute une `KernelFunction` fournie par l'utilisateur.

```python
# Fichier: semantic_kernel/agents/strategies/selection/kernel_function_selection_strategy.py (extrait simplifié)
...
async def select_agent(self, agents: list["Agent"], history: list[ChatMessageContent]) -> "Agent":
    # 1. Prépare les arguments pour le prompt
    arguments = KernelArguments(
        **{
            self.agent_variable_name: ",".join(agent.name for agent in agents),
            self.history_variable_name: [msg.to_dict() for msg in history],
        }
    )
    
    # 2. Invoque la fonction sémantique fournie
    result = await self.function.invoke(kernel=self.kernel, arguments=arguments)

    # 3. Parse le résultat pour obtenir le nom de l'agent
    agent_name = self.result_parser(result)

    # 4. Retourne l'objet Agent correspondant
    return next(agent for agent in agents if agent.name == agent_name)
```

**Implémentation Cible :**
L'orchestrateur doit définir une fonction sémantique qui guide le LLM dans son choix, puis l'injecter dans la stratégie.

```python
# Fichier: argumentation_analysis/orchestration/analysis_runner.py (pseudo-code de la factory de stratégie)

def _create_selection_strategy(kernel: Kernel) -> KernelFunctionSelectionStrategy:
    """Crée la stratégie de sélection pilotée par LLM."""
    select_agent_prompt = """
    Vous êtes un chef d'orchestre expert en analyse d'arguments. En vous basant sur l'historique
    de la conversation, quel agent doit intervenir ensuite ?
    Votre réponse doit être UNIQUEMENT le nom de l'agent, et rien d'autre.

    AGENTS DISPONIBLES: {{$_agent_}}
    HISTORIQUE DE LA CONVERSATION: {{$_history_}}

    Prochain agent à parler :
    """
    selection_function = kernel.create_function_from_prompt(prompt=select_agent_prompt)

    return KernelFunctionSelectionStrategy(
        kernel=kernel,
        function=selection_function,
        result_parser=lambda result: str(result).strip() # Nettoie la sortie du LLM
    )
```

### 2. La Terminaison Composite avec `AggregatorTerminationStrategy`

Une conversation doit se terminer intelligemment, mais aussi avoir un garde-fou. `AggregatorTerminationStrategy` est conçue pour cela en combinant plusieurs stratégies. Son code est d'une grande simplicité :

```python
# Fichier: semantic_kernel/agents/strategies/termination/aggregator_termination_strategy.py (extrait)
...
async def should_terminate_async(self, agent: "Agent", history: list[ChatMessageContent]) -> bool:
    # Exécute toutes les stratégies en parallèle
    strategy_execution = [strategy.should_terminate(agent, history) for strategy in self.strategies]
    results = await asyncio.gather(*strategy_execution)

    # Retourne True si TOUTES ou N'IMPORTE LAQUELLE des conditions est remplie
    if self.condition == AggregateTerminationCondition.ALL:
        return all(results)
    return any(results)
```

**Implémentation Cible :**
Nous combinons une condition sémantique et un garde-fou mécanique.

1.  **Condition Sémantique (`KernelFunctionTerminationStrategy`)** : Un LLM évalue si la tâche est terminée.
2.  **Garde-fou (`DefaultTerminationStrategy`)** : L'analyse du code de [`termination_strategy.py`](C:/Users/jsboi/.conda/envs/projet-is-new/Lib/site-packages/semantic_kernel/agents/strategies/termination/termination_strategy.py:1) montre que la classe de base possède une propriété `maximum_iterations`. La stratégie `DefaultTerminationStrategy` hérite de ce comportement et sert donc de simple compteur, mettant fin à la conversation après N tours pour éviter les boucles infinies.

```python
# Fichier: argumentation_analysis/orchestration/analysis_runner.py (pseudo-code de la factory de stratégie)

def _create_termination_strategy(kernel: Kernel) -> AggregatorTerminationStrategy:
    """Crée une stratégie de terminaison composite."""
    # 1. Stratégie sémantique
    terminate_prompt = """
    L'objectif de l'analyse est-il atteint ? La tâche est considérée comme terminée
    si une synthèse finale a été fournie. Répondez uniquement par "true" ou "false".
    
    HISTORIQUE: {{$_history_}}
    Tâche terminée :
    """
    semantic_termination = KernelFunctionTerminationStrategy(
        kernel=kernel,
        function=kernel.create_function_from_prompt(prompt=terminate_prompt),
        result_parser=lambda result: "true" in str(result).lower()
    )

    # 2. Stratégie de garde-fou
    failsafe_termination = DefaultTerminationStrategy(maximum_iterations=15)

    # 3. Combinaison des deux
    return AggregatorTerminationStrategy(
        strategies=[semantic_termination, failsafe_termination],
        condition=AggregateTerminationCondition.ANY # S'arrêter dès que l'une des deux est vraie
    )
```

## Proposition d'Implémentation Finale de l'Orchestrateur

Avec ces stratégies en place, le code de l'orchestrateur dans `analysis_runner.py` devient une simple déclaration d'intention. Il assemble les composants et délègue l'exécution, rendant le code lisible, maintenable et robuste.

```python
# Fichier : argumentation_analysis/orchestration/analysis_runner.py (Implémentation cible)

async def _run_analysis_conversation(texte_a_analyser: str, llm_service):
    # ... initialisation du kernel, des agents via une factory ...
    
    # 1. Instancier les agents (ex: via une AgentFactory)
    pm_agent = agent_factory.create_project_manager_agent()
    fallacy_agent = agent_factory.create_informal_fallacy_agent()
    agents = [pm_agent, fallacy_agent]

    # 2. Construire les stratégies
    selection_strategy = _create_selection_strategy(kernel)
    termination_strategy = _create_termination_strategy(kernel)

    # 3. Assembler et configurer l'orchestrateur
    group_chat = AgentGroupChat(
        agents=agents,
        selection_strategy=selection_strategy,
        termination_strategy=termination_strategy,
    )

    # 4. Lancer l'orchestration avec la tâche initiale
    initial_arguments = KernelArguments(input=f"Veuillez analyser le texte suivant : {texte_a_analyser}")
    
    final_history = [message async for message in group_chat.invoke(arguments=initial_arguments)]

    # ... traitement du résultat ...
    return final_history
```

Cette architecture restaurée paie non seulement la dette technique, mais positionne également le projet sur des bases solides pour de futures évolutions, où l'ajout et la modification du comportement des agents deviennent des tâches simples et à faible risque.

# Partie 2 : Architecture des Agents : `AbstractAgent` et `AgentFactory`

Suite à la restauration de `AgentGroupChat`, il est impératif de standardiser la création et la structure des agents participants. Cette section définit une architecture de base pour tous les agents, garantissant leur interopérabilité et simplifiant leur maintenance.

## `AbstractAgent` : La Classe de Base Fondamentale

Pour garantir la compatibilité avec `AgentGroupChat` et uniformiser le comportement des agents, nous introduisons `AbstractAgent`.

**Principe clé :** `AbstractAgent` hérite directement de `semantic_kernel.agents.Agent`. Cet héritage est la pierre angulaire de l'architecture, assurant que chaque agent respecte le contrat attendu par l'écosystème `semantic-kernel`.

### Définition et Contrat de `AbstractAgent`

Le code ci-dessous présente la structure complète de la classe de base. Elle sera placée dans un nouveau fichier (`argumentation_analysis/agents/abc/abstract_agent.py`) pour marquer cette nouvelle fondation architecturale.

```python
# Fichier : argumentation_analysis/agents/abc/abstract_agent.py

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterable, Awaitable, List

from semantic_kernel import Kernel
from semantic_kernel.agents import Agent
from semantic_kernel.agents.agent import AgentResponseItem
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments

class AbstractAgent(Agent, ABC):
    """
    Classe de base abstraite pour tous les agents, garantissant la conformité
    avec `semantic_kernel.agents` pour une intégration native dans `AgentGroupChat`.

    Elle définit un contrat clair mêlant les exigences de `semantic-kernel`
    et les besoins de configuration spécifiques à notre projet.
    """

    def __init__(
        self,
        kernel: Kernel,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialise une instance de `AbstractAgent`, en appelant le constructeur parent.
        """
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            kernel=kernel,
            **kwargs,
        )
        self.logger = logging.getLogger(f"agent.{self.__class__.__name__}.{self.name}")
        self.llm_service_id: Optional[str] = None

    # --- Contrat Spécifique au Projet ---

    @abstractmethod
    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Méthode de post-initialisation pour configurer les composants internes
        de l'agent (plugins, etc.) après sa création.
        
        Args:
            llm_service_id (str): L'ID du service LLM à utiliser.
        """
        self.llm_service_id = llm_service_id
        self.logger.info(f"Composants configurés pour '{self.name}' avec le service LLM '{llm_service_id}'.")

    @abstractmethod
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne un dictionnaire décrivant les capacités de l'agent.
        Utile pour le débogage, la supervision et les stratégies avancées.
        """
        pass

    # --- Implémentation du Contrat `semantic-kernel.agents.Agent` ---

    @abstractmethod
    async def get_response(
        self,
        messages: List[ChatMessageContent],
        arguments: KernelArguments,
        **kwargs: Any,
    ) -> AgentResponseItem[ChatMessageContent]:
        """
        CŒUR DE LA LOGIQUE DE L'AGENT. Chaque agent concret doit implémenter
        cette méthode pour traiter l'historique et générer une réponse.

        Args:
            messages (List[ChatMessageContent]): L'historique des messages.
            arguments (KernelArguments): Arguments supplémentaires pour l'invocation.

        Returns:
            Un `AgentResponseItem` contenant la réponse de l'agent.
        """
        raise NotImplementedError

    async def invoke(
        self,
        messages: List[ChatMessageContent],
        arguments: Optional[KernelArguments] = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseItem[ChatMessageContent]]:
        """
        Point d'entrée pour `AgentGroupChat`. Délègue la logique à `get_response`
        et encapsule le résultat dans le flux asynchrone attendu.
        """
        if arguments is None:
            arguments = KernelArguments()
        
        response = await self.get_response(messages, arguments, **kwargs)
        yield response

    async def invoke_stream(
        self,
        messages: List[ChatMessageContent],
        arguments: Optional[KernelArguments] = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseItem[ChatMessageContent]]:
        """Implémentation du streaming, qui délègue à `invoke`."""
        async for message in self.invoke(messages, arguments, **kwargs):
            yield message
```

## `AgentFactory` : L'Usine de Création d'Agents

Pour centraliser et standardiser l'instanciation des agents, nous introduisons le patron de conception *Factory*. L'`AgentFactory` devient le point d'entrée unique pour créer et configurer tous les agents du système.

### Conception de la `AgentFactory`

La factory est initialisée avec les dépendances communes (comme le `Kernel`) et fournit des méthodes dédiées pour construire chaque type d'agent.

```python
# Fichier : argumentation_analysis/agents/agent_factory.py

from semantic_kernel import Kernel
from .concrete_agents import InformalFallacyAgent, ProjectManagerAgent # Exemples d'agents concrets
from .abc.abstract_agent import AbstractAgent

class AgentFactory:
    """Usine pour la création et la configuration centralisée des agents."""

    def __init__(self, kernel: Kernel, llm_service_id: str):
        """
        Initialise la factory avec les dépendances partagées.

        Args:
            kernel (Kernel): L'instance du kernel à injecter dans les agents.
            llm_service_id (str): L'ID du service LLM par défaut.
        """
        self._kernel = kernel
        self._llm_service_id = llm_service_id

    def create_informal_fallacy_agent(self) -> AbstractAgent:
        """Crée et configure un agent d'analyse des sophismes."""
        agent = InformalFallacyAgent(
            kernel=self._kernel,
            name="FallacyAnalyst",
            description="Spécialiste de l'identification des sophismes informels sur la base d'une taxonomie."
        )
        # Étape de configuration post-initialisation
        agent.setup_agent_components(self._llm_service_id)
        return agent

    def create_project_manager_agent(self) -> AbstractAgent:
        """Crée et configure l'agent chef de projet."""
        agent = ProjectManagerAgent(
            kernel=self._kernel,
            name="ProjectManager",
            description="Chef d'orchestre qui analyse l'état de la conversation et désigne le prochain intervenant."
        )
        # Étape de configuration post-initialisation
        agent.setup_agent_components(self._llm_service_id)
        return agent
        
    # Rajouter ici les méthodes pour chaque nouvel agent...
```

### Diagramme de Séquence : Utilisation de la Factory

Le diagramme suivant illustre comment l'orchestrateur utilise la factory pour assembler son groupe d'agents, sans connaître les détails de leur construction.

```mermaid
sequenceDiagram
    participant Runner as analysis_runner.py
    participant Factory as AgentFactory
    participant Agent as AgentConcret

    Runner->>Factory: __init__(kernel, llm_service)
    Runner->>Factory: create_project_manager_agent()
    Factory->>Agent: __init__(kernel, name, desc)
    Factory->>Agent: setup_agent_components(llm_service)
    Agent-->>Factory: self
    Factory-->>Runner: project_manager_agent

    Runner->>Factory: create_informal_fallacy_agent()
    Factory->>Agent: __init__(kernel, name, desc)
    Factory->>Agent: setup_agent_components(llm_service)
    Agent-->>Factory: self
    Factory-->>Runner: informal_fallacy_agent
```

### Justification et Avantages de l'Architecture

Cette approche standardisée autour de `AbstractAgent` et `AgentFactory` apporte des bénéfices considérables :

*   **Couplage Faible** : L'orchestrateur (`analysis_runner`) ne dépend plus des implémentations concrètes des agents, mais uniquement de l'interface `AbstractAgent` et de la `AgentFactory`.
*   **Centralisation de la Logique de Création** : Toute la complexité liée à l'instanciation (injection du `Kernel`, configuration des services, chargement des plugins via `setup_agent_components`) est contenue dans la factory.
*   **Respect du Principe Ouvert/Fermé** : Pour ajouter un nouvel agent au système, il suffit de créer sa classe (héritant de `AbstractAgent`) et d'ajouter une méthode `create_...` dans la factory. Aucune modification n'est requise dans la logique de l'orchestrateur, qui est *fermé à la modification mais ouvert à l'extension*.
*   **Testabilité Améliorée** : Les agents et la factory peuvent être testés unitairement de manière beaucoup plus simple.
*   **Garantie de Compatibilité** : L'héritage de `semantic_kernel.agents.Agent` assure que tous nos agents sont, par définition, compatibles avec les composants `AgentGroupChat` et les stratégies associées.


# Partie 3 : L'Agent Hybride : Refactorisation du `InformalAnalysisPlugin`

Alors que les parties précédentes ont défini l'architecture de l'orchestration (`AgentGroupChat`) et la structure des agents (`AbstractAgent`), cette section se concentre sur un cas d'étude concret et essentiel : la refonte de l'`InformalAnalysisPlugin`. Cette transformation est la clé pour corriger le bug originel (l'incapacité à utiliser la taxonomie des sophismes) et pour produire une sortie de données fiable et structurée.

## 3.1. Principe Fondamental : De Plugin à Agent Spécialisé

### 3.1.1. La Problématique
L'implémentation initiale de l'analyse des sophismes fonctionnait comme un simple plugin exposant de multiples fonctions à un `Kernel` externe. Cette approche souffrait de deux défauts majeurs :
1.  **Fiabilité Médiocre :** La sortie était du texte libre, nécessitant un parsing fragile et sujet aux erreurs.
2.  **Couplage Fort :** La logique de l'agent était dispersée entre le code du plugin et les prompts sémantiques appelés par l'orchestrateur, rendant la maintenance et l'évolution complexes.

### 3.1.2. La Solution Architecturale : L'Agent Spécialisé
La solution consiste à transformer le plugin en un `InformalAnalysisAgent` autonome. Cet agent devient un "spécialiste" qui encapsule toute la complexité de sa tâche derrière une interface standardisée (`AbstractAgent`). Il ne se contente plus d'exécuter des fonctions ; il s'auto-orchestre pour accomplir sa mission.

### 3.1.3. Héritage et Contrat (`AbstractAgent`)
En héritant de `AbstractAgent`, le nouvel agent garantit sa parfaite intégration dans l'écosystème `AgentGroupChat`. Il respecte un contrat clair, implémentant la logique métier principale au sein de la méthode `get_response`.

```python
# Fichier : argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py (Illustratif)

from ..abc.abstract_agent import AbstractAgent
# ... autres imports

class InformalAnalysisAgent(AbstractAgent):
    """
    Agent spécialisé dans l'identification des sophismes informels
    en se basant sur une taxonomie et en garantissant une sortie structurée.
    """

    def setup_agent_components(self, llm_service_id: str) -> None:
        """ Configure le kernel interne et les dépendances de l'agent. """
        super().setup_agent_components(llm_service_id)
        # Ici, on pourrait initialiser le kernel interne, charger la taxonomie, etc.
        self.internal_kernel = Kernel() # Exemple simplifié
        self.logger.info("Kernel interne de l'agent d'analyse de sophismes configuré.")

    async def get_response(
        self,
        messages: List[ChatMessageContent],
        arguments: KernelArguments,
        **kwargs: Any,
    ) -> AgentResponseItem[ChatMessageContent]:
        """ C'est ici que toute la magie de l'agent opère. """
        text_to_analyze = arguments.get("input", "")
        # ... logique complète d'appel au kernel interne ...
        analysis_json = await self._run_internal_analysis(text_to_analyze)
        
        # Création du message de réponse standard
        response_message = ChatMessageContent(role="assistant", content=analysis_json)
        return AgentResponseItem(message=response_message, agent=self)

    # ... autres méthodes privées ...
```

## 3.2. Le Cœur de l'Agent Hybride : Le Pattern "Builder Plugin"

La refactorisation de `InformalAnalysisAgent` n'est pas une simple réorganisation, mais l'application d'un **pattern architectural puissant et validé** que nous nommerons le **"Pattern de l'Agent Hybride"** ou **"Builder Plugin"**.

L'exploration du code existant du projet, notamment dans [`argumentation_analysis/agents/core/logic/first_order_logic_agent.py`](argumentation_analysis/agents/core/logic/first_order_logic_agent.py:1), a révélé le `BeliefSetBuilderPlugin`. Ce plugin est l'exemple parfait de ce pattern : au lieu de demander au LLM de générer une syntaxe complexe et fragile, il lui fournit des "outils" simples (`add_sort`, `add_atomic_fact`, etc.). Le rôle du LLM est alors réduit à une tâche simple et fiable : décider quels outils appeler. Le plugin, quant à lui, agit comme un "builder", accumulant ces appels pour construire un objet complexe (`.fologic`) de manière déterministe et fiable.

Notre `InformalAnalysisAgent` applique rigoureusement ce même pattern :
1.  **Agent = Façade Simple :** Pour l'orchestrateur externe (`AgentGroupChat`), l'agent expose une interface simple (`get_response`).
2.  **Kernel Interne = Moteur d'Orchestration :** L'agent utilise son propre `Kernel` interne pour gérer la logique complexe.
3.  **Outil Pydantic = Contrat de Données :** L'agent expose un unique "outil" au LLM : la classe Pydantic `FallacyAnalysisResult`.
4.  **Rôle du LLM = Remplir un Formulaire :** Le LLM n'écrit plus de texte libre. Sa seule tâche est de remplir les champs du modèle Pydantic, agissant comme un employé qui remplit un formulaire structuré.
5.  **Rôle de l'Agent = Générer la Réponse :** L'agent reçoit cet objet Pydantic, validé et structuré, et l'utilise pour générer sa réponse finale.

Cette approche, validée par sa présence dans d'autres parties critiques du projet, garantit une robustesse et une fiabilité maximales. L'agent encapsule sa propre complexité, déchargeant à la fois l'orchestrateur principal et le LLM.

## 3.3. Fiabilisation des Entrées : L'Injection Dynamique de Taxonomie

Pour résoudre définitivement le bug de l'ignorance de la taxonomie, l'agent la charge et l'injecte dans le prompt à chaque appel.

Le mécanisme est le suivant :
1.  **Chargement :** L'agent utilise un `TaxonomyLoader` centralisé pour récupérer un DataFrame Pandas des sophismes.
2.  **Formatage :** Il transforme ce DataFrame en une chaîne de caractères claire et concise, optimisée pour le LLM.
3.  **Injection :** Cette chaîne est insérée dans le prompt.

```python
# Méthode privée au sein de InformalAnalysisAgent

def _build_analysis_prompt(self, text_to_analyze: str) -> str:
    """ Construit le prompt avec la taxonomie injectée. """
    
    # 1. & 2. Chargement et formatage
    # taxonomy_df = self.taxonomy_loader.load()
    # taxonomy_summary = "\n".join(f"- {row['name']}: {row['description']}" for _, row in taxonomy_df.iterrows())
    taxonomy_summary = "Exemple: Sophisme de la Pente Glissante, Ad Hominem, etc." # Pour l'exemple

    # 3. Injection
    prompt = f"""
    Analyse le texte suivant pour y dénicher des sophismes. Tu dois baser ton analyse
    UNIQUEMENT sur la taxonomie de sophismes ci-dessous.
    Ton objectif est de retourner une structure de données complète via l'outil `FallacyAnalysisResult`.

    --- TAXONOMIE DISPONIBLE ---
    {taxonomy_summary}
    --- FIN DE LA TAXONOMIE ---

    --- TEXTE À ANALYSER ---
    {text_to_analyze}
    --- FIN DU TEXTE ---
    """
    return prompt.strip()
```

## 3.4. Fiabilisation des Sorties : La Contrainte Pydantic

C'est l'étape la plus critique. Nous éliminons le parsing de texte en **forçant** le LLM à nous répondre dans un format que nous contrôlons.

**1. Contrat de Données (Pydantic) :** Nous définissons la structure de sortie attendue.

```python
from pydantic import BaseModel, Field
from typing import List

class IdentifiedFallacy(BaseModel):
    """Modèle de données pour un seul sophisme identifié."""
    fallacy_name: str = Field(..., description="Le nom du sophisme, doit correspondre EXACTEMENT à un nom de la taxonomie fournie.")
    justification: str = Field(..., description="Citation exacte du texte et explication détaillée de pourquoi c'est un sophisme.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Score de confiance entre 0.0 et 1.0.")

class FallacyAnalysisResult(BaseModel):
    """Modèle de données pour le résultat complet de l'analyse de sophismes."""
    is_fallacious: bool = Field(..., description="Vrai si au moins un sophisme a été détecté, sinon faux.")
    fallacies: List[IdentifiedFallacy] = Field(..., description="Liste de TOUS les sophismes identifiés dans le texte. Laisser vide si aucun.")
```

**2. Forcer la Sortie (`tool_choice="required"`) :** Lors de l'appel au `Kernel` interne, nous spécifions des `OpenAIChatPromptExecutionSettings` (comme découvert lors de l'analyse du code source de `semantic-kernel`) qui ne laissent aucune autre option au LLM que d'utiliser notre modèle Pydantic comme outil.

```python
# Méthode privée au sein de InformalAnalysisAgent

async def _run_internal_analysis(self, text_to_analyze: str) -> str:
    """ Exécute l'appel LLM interne de manière fiable. """
    
    prompt = self._build_analysis_prompt(text_to_analyze)

    # L'exploration du code SK a confirmé que OpenAIChatPromptExecutionSettings est la bonne classe à utiliser
    execution_settings = OpenAIChatPromptExecutionSettings(
        tool_choice="required",  # Contrainte absolue : le LLM DOIT utiliser un outil
        tools=[FallacyAnalysisResult] # L'outil à utiliser est notre classe Pydantic elle-même
    )

    response = await self.internal_kernel.invoke_prompt(
        prompt,
        arguments=KernelArguments(settings=execution_settings)
    )

    tool_calls = response.tool_calls
    if not tool_calls:
        # Cas où le LLM ne trouve rien, on retourne un résultat valide "non fallacieux"
        analysis_result = FallacyAnalysisResult(is_fallacious=False, fallacies=[])
    else:
        # Le kernel a déjà validé la structure, on désérialise en toute sécurité
        analysis_result: FallacyAnalysisResult = tool_calls[0].to_tool_function()(
            **tool_calls[0].parse_arguments()
        )
    
    return analysis_result.model_dump_json(indent=2)
```
Cette combinaison garantit un résultat toujours prévisible, valide et directement utilisable.


## 3.5. Schéma d'Interaction Interne

Le diagramme suivant illustre le flux interne complet de l'agent.

```mermaid
sequenceDiagram
    participant Orchestrateur as AgentGroupChat
    participant Agent as InformalAnalysisAgent
    participant Kernel as Kernel Interne
    participant LLM

    Orchestrateur->>Agent: invoke(get_response, texte)
    Agent->>Agent: _build_analysis_prompt(texte)
    Note right of Agent: Charge la taxonomie et l'injecte
    Agent->>Kernel: invoke_prompt(prompt, settings)
    Note right of Kernel: `settings` contient<br>`tool_choice="required"`<br>et `tools=[FallacyAnalysisResult]`
    Kernel->>LLM: Appel API avec le prompt et la contrainte de l'outil
    LLM-->>Kernel: Réponse contenant un `tool_call` à `FallacyAnalysisResult`
    Kernel-->>Agent: `response` avec `tool_calls`
    Agent->>Agent: Désérialise `tool_calls` en objet Pydantic `FallacyAnalysisResult`
    Agent-->>Orchestrateur: Retourne le résultat en JSON string
```

## 3.6. Validation par l'Existant : Le Patron `BeliefSetBuilderPlugin`

Il est crucial de souligner que l'architecture proposée pour l'`InformalAnalysisAgent` n'est pas une construction théorique, mais la **standardisation d'un pattern de conception déjà présent et éprouvé** au sein de ce projet.

L'analyse de `argumentation_analysis/agents/core/logic/first_order_logic_agent.py` et de son `BeliefSetBuilderPlugin` a été déterminante. Ce dernier résout un problème similaire (la génération d'un fichier `.fologic` à la syntaxe stricte) avec une élégance et une robustesse remarquables.

La stratégie architecturale, décrite dans les commentaires mêmes du fichier, est la suivante :
1.  **Définir des Outils Simples :** Le plugin expose des fonctions atomiques au LLM (`add_sort`, `add_constant`, `add_atomic_fact`). Ce sont ses "outils".
2.  **Réduire le Rôle du LLM :** Le LLM n'a plus à se soucier de la syntaxe complexe du `.fologic`. Son unique responsabilité est d'analyser le langage naturel et de décider **quels outils appeler avec quels arguments**.
3.  **Confier la Construction au Code Python :** Le plugin reçoit ces appels, accumule les informations dans une structure de données interne fiable, et se charge lui-même de générer la chaîne `.fologic` finale de manière parfaitement déterministe.

**Notre `InformalAnalysisAgent` est une implémentation directe de ce même pattern :**
*   L'outil unique est la classe Pydantic `FallacyAnalysisResult`.
*   Le LLM ne fait que "remplir les cases" de cet outil.
*   L'agent reçoit l'objet Pydantic et s'occupe de le sérialiser en un rapport JSON propre.

En adoptant cette approche, nous ne faisons donc qu'appliquer une "best practice" interne, garantissant que notre nouvelle architecture est non seulement théoriquement saine, mais aussi parfaitement alignée avec les solutions qui ont déjà fait leurs preuves dans ce codebase.


# Partie 4 : Robustesse, Configuration et Tests

Alors que les parties précédentes ont établi une architecture fonctionnelle et élégante, cette section s'attaque aux aspects non fonctionnels qui transforment un prototype prometteur en un système de production fiable, maintenable et évolutif. Nous allons "durcir" notre architecture en formalisant les stratégies de robustesse, en centralisant la configuration et en définissant un plan de test complet.

## 4.1. Stratégies de Robustesse et Gestion des Erreurs

Un système basé sur des LLM est intrinsèquement non déterministe et sujet à des défaillances imprévisibles (erreurs réseau, timeouts d'API, réponses mal formées). Une architecture robuste ne vise pas à éliminer les erreurs, mais à les anticiper, les gérer et y survivre avec grâce.

### 4.1.1. Gestion des Échecs d'Agents au sein de `AgentGroupChat`

**Problématique :** Que se passe-t-il si un agent, lors de son tour de parole (`invoke`), lève une exception inattendue (ex: `APIError` du LLM, bug interne) ? Dans sa version de base, `AgentGroupChat` pourrait s'arrêter brutalement, laissant l'orchestration dans un état instable.

**Solution :** Nous proposons un mécanisme de capture d'exception au niveau de la boucle d'invocation de `AgentGroupChat` et l'introduction d'un agent "ErrorHandler" spécialisé.

**Diagramme de Séquence de la Gestion d'Erreur :**

```mermaid
sequenceDiagram
    participant Orchestrateur as AgentGroupChat
    participant Strategy as SelectionStrategy
    participant FailingAgent as Agent_X
    participant ErrorHandler as ErrorHandlerAgent

    Orchestrateur->>Strategy: next()
    Strategy-->>Orchestrateur: FailingAgent
    
    Orchestrateur->>FailingAgent: invoke()
    activate FailingAgent
    Note over FailingAgent: Déclenche une exception !
    FailingAgent-->>Orchestrateur: Lève une Exception
    deactivate FailingAgent

    Orchestrateur->>Orchestrateur: catch Exception as e
    Note over Orchestrateur: Capture l'erreur et prépare un message de contexte.

    Orchestrateur->>Strategy: next(context=error_context)
    Strategy-->>Orchestrateur: ErrorHandlerAgent
    
    Orchestrateur->>ErrorHandler: invoke(error_details)
    activate ErrorHandler
    ErrorHandler-->>Orchestrateur: Message de diagnostic ou de correction
    deactivate ErrorHandler
```

**Pseudo-code de la modification de `AgentGroupChat.invoke` :**

```python
# Fichier : semantic_kernel/agents/group_chat/agent_group_chat.py (Modification proposée)

async def invoke(...):
    ...
    for _ in range(self.termination_strategy.maximum_iterations):
        try:
            # 1. Sélection normale de l'agent
            selected_agent = await self.selection_strategy.next(self.agents, self.history.messages)

            # 2. Invocation de l'agent
            async for message in super().invoke_agent(selected_agent):
                 # ... (logique existante) ...
        
        except Exception as e:
            self.logger.error(f"L'agent '{selected_agent.name}' a échoué : {e}", exc_info=True)
            
            # 3. Construction d'un contexte d'erreur
            error_context = f"ERREUR SYSTÈME : L'agent {selected_agent.name} a rencontré une erreur critique : {type(e).__name__} - {e}. Il faut analyser la situation et décider de la prochaine étape : corriger, ignorer ou arrêter."
            
            # Ajoute le message d'erreur à l'historique pour informer les autres agents
            self.history.add_user_message(error_context)
            
            # 4. Délégation à la stratégie pour choisir un "gestionnaire d'erreur"
            # La stratégie de sélection peut être conçue pour reconnaître le contexte d'erreur
            # et sélectionner un agent "ErrorHandler" spécialisé.
            error_handler_agent = await self.selection_strategy.next(self.agents, self.history.messages)
            async for message in super().invoke_agent(error_handler_agent):
                 # ... (logique existante) ...

        # ... (logique de terminaison) ...
```

L'agent `ErrorHandlerAgent` peut alors être un agent simple dont le prompt lui demande d'analyser l'erreur et de suggérer une action, comme réessayer, abandonner, ou notifier un humain.

### 4.1.2. Politiques de Réessai (Retry Policy)

Les appels aux API externes (LLMs) sont la source la plus fréquente d'erreurs transitoires (problèmes réseau, surcharges momentanées de l'API retournant des erreurs 5xx). Recoder une logique de réessai manuellement est fastidieux et source d'erreurs.

**Solution :** Utiliser une bibliothèque éprouvée comme `tenacity` pour décorer les appels critiques.

**Exemple de code avec `tenacity` :**

```python
# Fichier : argumentation_analysis/core/kernel_builder.py (ou un module utilitaire)

import tenacity
import logging
import openai

def robust_openai_call(func):
    """
    Un décorateur qui enveloppe un appel à l'API OpenAI avec une politique de réessai.
    Cible les erreurs transitoires comme les timeouts ou les erreurs serveur.
    """
    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=60), # Attente exponentielle (2s, 4s, 8s...)
        stop=tenacity.stop_after_attempt(5), # Arrêt après 5 tentatives
        retry=tenacity.retry_if_exception_type((
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.RateLimitError,
            openai.APIStatusError, # Pour les 5xx
        )),
        before_sleep=tenacity.before_sleep_log(logging.getLogger(__name__), logging.INFO)
    )
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    
    return wrapper

# Comment l'appliquer (par exemple, par "monkey-patching" sur le Kernel ou dans le client HTTP)
# class ResilientKernel(Kernel):
#    
#    @robust_openai_call
#    async def invoke_prompt(...):
#        # ...
#        pass
```
*Note : L'application exacte peut varier. Une approche plus propre serait d'injecter un client HTTP personnalisé dans le `Kernel` qui intègre déjà cette logique.*

### 4.1.3. Validation des Entrées/Sorties et Auto-Correction

La **Partie 3** a brillamment introduit l'utilisation de Pydantic pour forcer des sorties structurées. Mais que se passe-t-il si, malgré tout, le LLM échoue à générer une sortie qui passe la validation de Pydantic ?

**Solution :** Mettre en place une boucle de "dialogue correctif" au sein même de l'agent.

**Exemple de pseudo-code dans un `AbstractAgent` :**

```python
# Fichier : argumentation_analysis/agents/abc/abstract_agent.py (logique améliorée)

from pydantic import ValidationError, BaseModel

MAX_CORRECTION_ATTEMPTS = 3

async def _invoke_llm_with_pydantic_tool(
    self, 
    prompt: str, 
    pydantic_tool: type[BaseModel]
) -> BaseModel:
    
    # ... code pour la configuration de l'appel LLM ...
    
    for attempt in range(MAX_CORRECTION_ATTEMPTS):
        try:
            # Appel au kernel pour obtenir la réponse structurée
            response_object = await self.kernel.invoke_prompt(...) # avec le tool_choice Pydantic
            
            # Si aucune exception n'est levée, la validation a réussi
            return response_object

        except ValidationError as e:
            self.logger.warning(f"Tentative {attempt + 1}: Échec de la validation Pydantic. Erreur: {e}")
            
            # Construction d'un message d'erreur pour le LLM
            error_feedback = (
                f"Votre dernière réponse n'était pas valide. "
                f"Veuillez corriger les erreurs suivantes et réessayer :\n{e}"
            )
            
            # Ajoute le feedback à l'historique de la conversation interne
            # pour que le LLM sache quoi corriger à la prochaine tentative.
            self.internal_history.add_user_message(error_feedback)

    # Si toutes les tentatives échouent
    self.logger.error("Échec de la validation après plusieurs tentatives. Abandon.")
    raise SystemError("L'agent n'a pas pu produire une sortie valide.")

```
Ce pattern transforme une erreur de validation en une opportunité de dialogue, augmentant drastiquement la fiabilité de l'agent.

## 4.2. Configuration Centralisée et Gestion de l'Environnement

Éparpiller la configuration (clés API, noms de modèles, timeouts) à travers le code est une recette pour le désastre. Une architecture de production nécessite une source de vérité unique pour la configuration.

### 4.2.1. Fichiers de Configuration : `.env` et `config.yaml`

**Solution :** Nous combinons deux types de fichiers de configuration pour séparer les secrets des paramètres.

1.  **`.env` : Pour les secrets.**
    Ce fichier (ignoré par Git) contient toutes les informations sensibles.
    ```dotenv
    # Fichier: .env
    OPENAI_API_KEY="sk-..."
    AZURE_OPENAI_ENDPOINT="https://..."
    ```

2.  **`config.yaml` : Pour les paramètres de l'application.**
    Ce fichier (versionné dans Git) contient la configuration non sensible.
    ```yaml
    # Fichier: config.yaml
    llm_services:
      default_chat:
        service_id: "default_chat_gpt4"
        model_id: "gpt-4-turbo-preview"
        type: "openai" # ou "azure_openai"
      embedding_generator:
        service_id: "default_embedding"
        model_id: "text-embedding-ada-002"
        type: "openai"

    agent_settings:
      timeout_seconds: 120
      max_retry_attempts: 3
    ```

Une bibliothèque comme `pydantic-settings` peut lire et valider ces fichiers pour charger la configuration dans des objets Pydantic typés.

### 4.2.2. Le `KernelBuilder` : Usine de Construction du `Kernel`

**Problématique :** La création et la configuration du `Kernel` (ajout des services LLM, des plugins, etc.) peuvent devenir complexes. Cette logique ne doit pas être dupliquée.

**Solution :** Créer une classe `KernelBuilder` qui lit la configuration centralisée et assemble une instance de `Kernel` prête à l'emploi.

**Pseudo-code d'un `KernelBuilder` :**

```python
# Fichier : argumentation_analysis/core/kernel_builder.py

from semantic_kernel import Kernel
# from .config import AppConfig # Modèle Pydantic chargeant config.yaml et .env

class KernelBuilder:
    """Construit et configure une instance de Kernel à partir de la config centrale."""

    @staticmethod
    def build_from_config(config) -> Kernel: # config: AppConfig
        kernel = Kernel()

        # Itérer sur les services définis dans le YAML
        for service_config in config.llm_services:
            if service_config.type == "openai":
                kernel.add_chat_service(
                    service_id=service_config.service_id,
                    service=OpenAIChatCompletion(
                        model_id=service_config.model_id,
                        api_key=config.openai_api_key.get_secret_value() # Via pydantic-settings
                    ),
                )
            elif service_config.type == "azure_openai":
                 kernel.add_chat_service(...) # Logique pour Azure

        # ... ajouter les services d'embedding, les plugins globaux, etc. ...
        
        return kernel

# Utilisation
# config = AppConfig() # Charge automatiquement .env et config.yaml
# kernel = KernelBuilder.build_from_config(config)
```

### 4.2.3. Injection de Dépendances : `KernelBuilder` -> `AgentFactory`

Le `Kernel` construit de manière centralisée doit être partagé par tous les agents. La `AgentFactory` est le point d'injection parfait.

**Diagramme de flux de la configuration :**

```mermaid
graph TD
    subgraph "Phase d'Initialisation"
        A[Fichiers .env / config.yaml] --> B{AppConfig};
        B --> C[KernelBuilder];
        C --> D{Kernel};
        D --> E{AgentFactory};
        B --> E;
    end
    
    subgraph "Phase d'Exécution"
        E --> F[Agent Concret 1];
        E --> G[Agent Concret 2];
        F --> D;
        G --> D;
    end

    style D fill:#9cf,stroke:#333,stroke-width:2px
```

Le `analysis_runner` devient alors très simple :
1.  Charger la configuration (`AppConfig`).
2.  Construire le `Kernel` via `KernelBuilder`.
3.  Instancier `AgentFactory` avec le `Kernel` et la configuration.
4.  Utiliser la factory pour créer les agents.
5.  Lancer `AgentGroupChat`.

Cette approche garantit que l'ensemble du système partage une configuration unique et cohérente.

## 4.3. Stratégie de Tests Complète

Tester une application basée sur des LLM est difficile, mais essentiel. Nous adoptons une approche multi-niveaux.

### 4.3.1. Tests Unitaires : Isoler la Logique d'un Agent

**Objectif :** Tester la logique interne d'un `AbstractAgent` sans faire de véritables appels LLM.

**Solution :** Utiliser des mocks (comme `unittest.mock.AsyncMock` en Python) pour simuler le `Kernel` et ses réponses.

**Exemple de test unitaire pour `InformalAnalysisAgent` :**

```python
# Fichier : tests/agents/test_informal_analysis_agent.py

import unittest
from unittest.mock import AsyncMock, MagicMock

async def test_agent_returns_valid_json_on_mocked_llm_call():
    # Arrange
    # 1. Créer un mock du Kernel
    mock_kernel = AsyncMock(spec=Kernel)
    
    # 2. Configurer le mock pour qu'il retourne une fausse réponse LLM simulée
    #    Cette réponse contient un "tool call" Pydantic valide.
    mock_response = MagicMock()
    mock_response.tool_calls = [
        # Simule le tool call que le kernel retournerait
        create_mock_tool_call(FallacyAnalysisResult(is_fallacious=True, fallacies=[]))
    ]
    mock_kernel.invoke_prompt.return_value = mock_response
    
    # 3. Instancier l'agent avec le Kernel mocké
    agent = InformalAnalysisAgent(kernel=mock_kernel, name="TestAgent")
    agent.setup_agent_components("mock_service")

    # Act
    # L'appel à get_response va maintenant utiliser le kernel mocké
    response_item = await agent.get_response(messages=[], arguments={"input": "Some text"})
    
    # Assert
    # 4. Vérifier que la sortie est bien le JSON attendu, produit à partir du mock
    assert '"is_fallacious": true' in response_item.message.content
    mock_kernel.invoke_prompt.assert_awaited_once() # Vérifie que le LLM a été appelé
```

### 4.3.2. Tests d'Intégration : Valider l'Orchestration

**Objectif :** Vérifier que les stratégies de `AgentGroupChat` (`selection_strategy`, `termination_strategy`) fonctionnent correctement sans dépendre des réponses imprévisibles des LLM.

**Solution :** Créer un `AgentGroupChat` avec de "faux" agents dont les réponses sont pré-définies et déterministes.

**Exemple de test d'intégration de l'orchestration :**

```python
# Fichier : tests/orchestration/test_agent_group_chat.py

class MockAgent(AbstractAgent):
    """Un faux agent qui retourne toujours une réponse prédéfinie."""
    def __init__(self, response_to_give: str, **kwargs):
        super().__init__(**kwargs)
        self.response = response_to_give

    async def get_response(self, ...) -> AgentResponseItem:
        return AgentResponseItem(message=ChatMessageContent(role="assistant", content=self.response))

async def test_conversation_terminates_when_pm_says_stop():
    # Arrange
    # 1. Créer des agents avec des réponses fixes
    agent1 = MockAgent(response_to_give="Faisons l'analyse. PM, à toi.", name="Agent1", kernel=Kernel())
    pm_agent = MockAgent(response_to_give="Analyse terminée. @TERMINATE", name="PM", kernel=Kernel()) # Réponse spéciale
    
    # 2. Utiliser les vraies stratégies, mais en mode "non-LLM" si possible
    #    (par ex. une stratégie de sélection qui lit simplement la réponse)
    # selection_strategy = SimpleSelectionStrategy(keyword="@")
    # termination_strategy = SimpleTerminationStrategy(keyword="@TERMINATE")
    
    # 3. Assembler le chat de test
    group_chat = AgentGroupChat(
        agents=[agent1, pm_agent],
        selection_strategy=selection_strategy,
        termination_strategy=termination_strategy
    )

    # Act
    final_history = [message async for message in group_chat.invoke()]

    # Assert
    # 4. Vérifier que la conversation s'est déroulée comme prévu et s'est arrêtée
    assert len(final_history) == 2 # 2 tours de parole
    assert "Analyse terminée" in final_history[-1].content
    assert group_chat.is_complete is True
```

### 4.3.3. Tests End-to-End : Détecter les Régressions avec un "Golden File"

**Objectif :** Valider l'ensemble du flux, de l'entrée initiale à la sortie finale, pour s'assurer que le comportement global du système ne régresse pas au fil des modifications.

**Solution :** Le test du "fichier d'or" (`.golden`).

**Méthode :**
1.  **Créer un fichier d'entrée de référence :** `test_case_1.txt`.
2.  **Exécuter l'analyse complète (avec de vrais appels LLM) une première fois.**
3.  **Sauvegarder le résultat JSON final dans `test_case_1.json.golden`.** Ce fichier est commité dans Git et devient la "vérité".
4.  **Créer un test automatisé** qui :
    *   Exécute l'analyse sur `test_case_1.txt`.
    *   Compare le nouveau résultat JSON avec le contenu de `test_case_1.json.golden`.
    *   Le test échoue si les deux fichiers diffèrent.

**Exemple de structure de fichiers :**
```
tests/e2e/
├── test_complex_argument.py
├── inputs/
│   └── complex_argument.txt
└── goldens/
    └── complex_argument.json.golden
```

Si une modification du code (ex: un changement de prompt) entraîne une modification de la sortie, le test échouera. Le développeur doit alors inspecter la différence. Si le changement est attendu et correct, il met à jour le fichier `.golden` pour refléter la nouvelle vérité. Sinon, il a détecté une régression et doit corriger son code.
