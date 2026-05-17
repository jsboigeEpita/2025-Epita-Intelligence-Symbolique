# Plan d'Exécution du Refactoring de l'Orchestration

## 1. Introduction

Ce document est la feuille de route technique pour l'implémentation de la nouvelle architecture détaillée dans le document [`architecture_restauration_orchestration.md`](./architecture_restauration_orchestration.md).

L'objectif est double :
1.  **Restaurer** la base de code à un état sain en annulant les régressions architecturales récentes.
2.  **Implémenter** la nouvelle architecture d'orchestration de manière contrôlée, sécurisée et incrémentale.

Ce plan est divisé en deux phases distinctes et séquentielles.

---

## 2. Phase 1 : Restauration de la Base de Code (Lot 0)

Cette première phase est un prérequis fondamental. Elle consiste à nettoyer la branche de développement pour repartir sur des fondations saines.

**Objectif :** Annuler la régression architecturale en réinitialisant la branche de travail sur un commit de référence stable.

**Workflow de Restauration :**

1.  **Assurer l'existence de la branche :**
    *   Nous travaillerons sur la branche `feature/orchestration-refactor`.
    *   Commande : `git checkout -b feature/orchestration-refactor` (crée la branche si elle n'existe pas, sinon bascule dessus).

2.  **Restauration Chirurgicale du Fichier (`git checkout`) :**
    *   Cette commande restaure **uniquement** le fichier spécifié à sa version d'un commit précis, sans altérer l'historique global du projet. C'est l'approche sécurisée et correcte.
    *   Commit de référence : `69736e25ecb02a3c745b42d1746c243e8d99806c`
    *   Fichier à restaurer : `argumentation_analysis/orchestration/analysis_runner.py`
    *   Commande : `git checkout 69736e25ecb02a3c745b42d1746c243e8d99806c -- argumentation_analysis/orchestration/analysis_runner.py`

3.  **Commit de Restauration (`fix`):**
    *   Une fois le fichier restauré à sa version saine, nous créons un commit pour acter cette restauration dans l'historique de la branche.
    *   Commande : `git commit -m "fix(orchestration): Revert analysis_runner.py to stable version from 69736e25ec"`

4.  **Push de la branche :**
    *   Poussez la branche normalement pour partager la base de code restaurée.
    *   Commande : `git push -u origin feature/orchestration-refactor`

---

## 3. Phase 2 : Implémentation Incrémentale des Lots

Une fois la base de code restaurée, nous commençons le développement itératif en suivant les "Work Orders" (WO) définis dans le document d'architecture.

**Objectif :** Mettre en œuvre la nouvelle architecture lot par lot, en suivant un workflow de développement strict pour garantir la qualité et la stabilité.

**Workflow Standard par Lot (pour chaque WO-XX) :**

1.  **Développement :**
    *   Implémentation du code nécessaire pour le lot de travail (par exemple, `WO-01: Fondations - Kernel, AbstractAgent, AgentFactory`).

2.  **Commit de Fonctionnalité (`feat`):**
    *   Regroupez les modifications fonctionnelles dans un commit.
    *   Exemple : `git commit -m "feat(orchestration): Implement WO-01 - Kernel builder and AgentFactory"`

3.  **Ajout de Tests :**
    *   Écrivez les tests (unitaires, intégration) qui valident la nouvelle fonctionnalité.

4.  **Commit de Tests (`test`):**
    *   Séparez les commits de code et de test pour plus de clarté.
    *   Exemple : `git commit -m "test(orchestration): Add unit tests for AgentFactory"`

5.  **Validation des Tests :**
    *   Lancez l'ensemble de la suite de tests et assurez-vous que tous les tests (anciens et nouveaux) passent avec succès.
    *   Exemple : `pytest`

6.  **Ajout/Mise à jour de la Documentation :**
    *   Mettez à jour les fichiers `README.md`, les docstrings, ou tout autre document impacté par les changements.

7.  **Commit de Documentation (`docs`):**
    *   Exemple : `git commit -m "docs(orchestration): Document the AgentFactory usage"`

8.  **Mise à jour depuis la branche principale (Merge intelligent) :**
    *   Avant de pousser le travail final, il est essentiel de se synchroniser avec la branche principale (`main` ou `develop`) pour intégrer les derniers changements.
    *   L'utilisation de `pull --rebase` permet de réappliquer vos commits au-dessus des dernières modifications de la branche principale, gardant un historique Git linéaire et propre, ce qui facilite grandement la revue et le merge final.
    *   Commande : `git pull --rebase origin main`

9.  **Corrections Éventuelles :**
    *   Résolvez les conflits qui pourraient émerger durant le `rebase`. Testez à nouveau après résolution.
    *   Commitez les corrections si nécessaire avec `git commit`.

10. **Push Final :**
    *   Poussez la branche de fonctionnalité mise à jour et prête pour la revue.
    *   Commande : `git push origin feature/orchestration-refactor`

**Liste Détaillée des Lots de Travail (Work Orders) :**

---
---

### **WO-01 : Fondations - Kernel, AbstractAgent, AgentFactory**

**Statut :** À FAIRE
**Priorité :** Critique
**Dépendances :** Aucune

#### **1. Objectifs Détaillés**

Ce premier lot de travail est le plus critique de tous. Il ne produit aucune fonctionnalité visible pour l'utilisateur final, mais il érige les piliers sur lesquels reposera l'intégralité de la nouvelle architecture. L'objectif est de traduire les concepts architecturaux de la **Partie 2** du document `architecture_restauration_orchestration.md` en code concret, réutilisable et robuste. Nous allons créer un contrat formel (`AbstractAgent`) que tous les futurs agents devront respecter, et un mécanisme centralisé (`AgentFactory`) pour les construire, garantissant ainsi cohérence, testabilité et découplage à travers toute l'application.

#### **2. Livrables Attendus**

1.  **Nouveau répertoire :** `argumentation_analysis/agents/abc/`
2.  **Nouveau fichier :** `argumentation_analysis/agents/abc/__init__.py` (peut être vide)
3.  **Nouveau fichier :** `argumentation_analysis/agents/abc/abstract_agent.py` contenant la classe de base `AbstractAgent`.
4.  **Nouveau fichier :** `argumentation_analysis/agents/agent_factory.py` contenant la classe `AgentFactory`.
5.  **Fichiers de test squelettes :**
    *   `tests/agents/abc/`
    *   `tests/agents/factories/`
    *   `tests/agents/factories/test_agent_factory.py`

#### **3. Décomposition en Sous-Tâches Techniques**

##### **3.1. Création de la Structure de Fichiers**
*   **Action :** Créer l'arborescence de répertoires `argumentation_analysis/agents/abc/`.
*   **Justification :** Le nom `abc` (Abstract Base Classes) est une convention Python standard pour les classes abstraites, rendant la structure du projet immédiatement compréhensible pour tout développeur.

##### **3.2. Implémentation Détaillée de `AbstractAgent`**
*   **Action :** Créer le fichier `abstract_agent.py` et y implémenter le code ci-dessous.
            # Contexte de correction pour guider le LLM
            correction_context = ""
            if last_error:
                correction_context = f"""ATTENTION: Votre précédente tentative a échoué avec l'erreur suivante. Vous devez corriger votre sortie pour la rendre valide.
<erreur>
{last_error}
</erreur>
"""

            return f"""
            Analysez le texte suivant pour y déceler des sophismes. Basez votre analyse
            UNIQUEMENT sur la taxonomie de sophismes fournie.
            Votre unique tâche est de remplir l'outil `FallacyAnalysisResult` avec vos découvertes.
        
            --- TAXONOMIE DISPONIBLE ---
            {taxonomy_summary}
            --- FIN DE LA TAXONOMIE ---
        
            --- TEXTE À ANALYSER ---
            {text_to_analyze}
            --- FIN DU TEXTE ---

            {correction_context}
            """.strip()python
    # Fichier : argumentation_analysis/agents/abc/abstract_agent.py
    
    import logging
    from abc import ABC, abstractmethod
    from typing import Dict, Any, Optional, AsyncIterable, List
    
    from semantic_kernel import Kernel
    from semantic_kernel.agents import Agent
    from semantic_kernel.agents.agent import AgentResponseItem
    from semantic_kernel.contents.chat_message_content import ChatMessageContent
    from semantic_kernel.functions.kernel_arguments import KernelArguments
    
    class AbstractAgent(Agent, ABC):
        """
        Classe de base abstraite pour tous les agents du système.
        
        Rôle et Justification :
        1. HÉRITAGE DE `semantic_kernel.agents.Agent` : C'est le point crucial.
           Cet héritage garantit que chaque agent que nous créons est nativement
           compatible avec l'écosystème `semantic-kernel`, en particulier
           `AgentGroupChat` et ses stratégies. Nous nous lions au contrat
           défini par le framework.
        
        2. DÉFINITION D'UN CONTRAT INTERNE : En plus du contrat de SK, nous
           ajoutons nos propres méthodes abstraites (`setup_agent_components`,
           `get_agent_capabilities`) pour standardiser des aspects
           critiques de notre architecture comme la configuration post-init
           et la supervision.
        
        3. CENTRALISATION DE LA LOGIQUE COMMUNE : Le constructeur gère
           l'initialisation du logger, et les méthodes `invoke`/`invoke_stream`
           sont déjà implémentées pour servir de passe-plat vers le cœur
           logique de l'agent (`get_response`), évitant ainsi la
           répétition de ce code standard.
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
            Initialise une instance d'AbstractAgent. L'appel à super().__init__ est
            essentiel pour enregistrer l'agent auprès de `semantic-kernel`.
            """
            super().__init__(
                name=name,
                description=description,
                instructions=instructions,
                kernel=kernel, # Le kernel est passé au parent mais sera aussi utilisé localement.
                **kwargs,
            )
            # Chaque agent dispose de son propre logger préfixé pour un débogage facile.
            self.logger = logging.getLogger(f"agent.{self.__class__.__name__}.{self.name}")
            self.llm_service_id: Optional[str] = None
    
        @abstractmethod
                def setup_agent_components(self, llm_service_id: str, correction_attempts: int = 3) -> None:
            super().setup_agent_components(llm_service_id)
            self.correction_attempts = correction_attempts
            """
            Méthode de configuration appelée par l'AgentFactory APRÈS l'initialisation.
            C'est ici que l'agent doit charger ses plugins spécifiques, initialiser
            ses clients, ou effectuer toute autre configuration qui dépend
            d'éléments externes.
            
            Args:
                llm_service_id (str): L'ID du service LLM à utiliser, provenant de la conf.
            """
            self.llm_service_id = llm_service_id
            self.logger.info(f"Composants configurés pour '{self.name}' avec le service LLM '{llm_service_id}'.")
    
        @abstractmethod
        def get_agent_capabilities(self) -> Dict[str, Any]:
            """
-            Retourne un dictionnaire décrivant les 'pouvoirs' de l'agent.
-            Exemples: plugins chargés, modèles de données Pydantic utilisés, etc.
-            Cette méthode sera vitale pour la supervision et le débogage.
-            """
-            return {
-                "name": self.name,
-                "description": self.description,
-                "instructions": self.instructions,
-                "llm_service_id": self.llm_service_id,
-                "plugins": [plugin.name for plugin in self.kernel.plugins] if self.kernel and self.kernel.plugins else []
-            }
+            Retourne un dictionnaire décrivant les 'pouvoirs' de l'agent (plugins, etc.)
+            pour la supervision et le débogage.
+            """
+            pass
    
        @abstractmethod
        async def get_response(
            self,
            messages: List[ChatMessageContent],
            arguments: KernelArguments,
            **kwargs: Any,
        ) -> AgentResponseItem[ChatMessageContent]:
            """
            IMPLÉMENTATION DU CŒUR LOGIQUE DE L'AGENT.
            C'est cette méthode que chaque agent concret DOIT surcharger. Elle contient
            la logique métier : traitement de l'historique, raisonnement, appel
            à des outils (plugins), et formulation de la réponse.
            """
            raise NotImplementedError
    
        async def invoke(
            self,
            messages: List[ChatMessageContent],
            arguments: Optional[KernelArguments] = None,
            **kwargs: Any,
        ) -> AsyncIterable[AgentResponseItem[ChatMessageContent]]:
            """
            Point d'entrée pour `AgentGroupChat`. Ne pas surcharger cette méthode.
            Elle sert de pont standardisé entre l'orchestrateur et la logique
            spécifique de l'agent dans `get_response`.
            """
            if arguments is None:
                arguments = KernelArguments()
            
            self.logger.debug(f"Agent '{self.name}' invoqué.")
            response = await self.get_response(messages, arguments, **kwargs)
            self.logger.debug(f"Agent '{self.name}' a produit une réponse.")
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

##### **3.3. Implémentation Détaillée de `AgentFactory`**
*   **Action :** Créer le fichier `agent_factory.py` et y implémenter la classe.
    ```python
    # Fichier : argumentation_analysis/agents/agent_factory.py
    
    from semantic_kernel import Kernel
    from .abc.abstract_agent import AbstractAgent
    # Les imports des agents concrets seront ajoutés dans les prochains WOs.
    # from .concrete_agents import InformalFallacyAgent, ProjectManagerAgent
    
    class AgentFactory:
        """
        Usine pour la création et la configuration centralisée des agents.
        
        Rôle et Justification :
        1. CENTRALISATION : C'est le SEUL endroit dans le code où les agents
           concrets sont instanciés.
        
        2. DÉCOUPLAGE : L'orchestrateur (`analysis_runner`) ne connaît plus
           les classes concrètes des agents. Il demande simplement à la
           factory de lui fournir un "FallacyAnalyst" ou un "ProjectManager".
           Ceci est une application directe du principe d'Inversion de Dépendance.
        
        3. PRINCIPE OUVERT/FERMÉ : Pour ajouter un nouvel agent au système,
           il suffira d'ajouter une méthode `create_..._agent()` ici.
           L'orchestrateur n'aura pas à être modifié. Le système est donc
           *ouvert à l'extension* mais *fermé à la modification*.
        """
    
        def __init__(self, kernel: Kernel, llm_service_id: str):
            """
            Initialise la factory avec les dépendances partagées par tous les agents.
            
            Args:
                kernel (Kernel): L'instance du kernel principal.
                llm_service_id (str): L'ID du service LLM par défaut (ex: 'gpt-4-turbo').
            """
            self._kernel = kernel
            self._llm_service_id = llm_service_id
    
        def create_informal_fallacy_agent(self) -> AbstractAgent:
            """Crée et configure un agent d'analyse des sophismes."""
            # L'implémentation complète sera faite dans le WO-03.
            raise NotImplementedError("Implémentation de InformalFallacyAgent à venir dans WO-03")
    
        def create_project_manager_agent(self) -> AbstractAgent:
            """Crée et configure l'agent chef de projet."""
            # L'implémentation complète sera faite dans le WO-04.
            raise NotImplementedError("Implémentation de ProjectManagerAgent à venir dans WO-04")
            
        # D'autres méthodes de création seront ajoutées ici pour chaque nouvel agent.
    ```

#### **4. Critères d'Acceptation (Definition of Done)**
*   Les fichiers `abstract_agent.py` et `agent_factory.py` existent aux emplacements spécifiés.
*   Le code est conforme aux standards de `ruff` (linter).
*   Toutes les classes et méthodes publiques sont documentées avec des docstrings claires expliquant leur rôle et leur justification architecturale.
*   `AbstractAgent` contient toutes les méthodes abstraites et non abstraites définies ci-dessus.
*   `AgentFactory` est implémentée avec des méthodes `create_...` qui lèvent `NotImplementedError` pour le moment.

#### **5. Plan de Test**
*   **Tests Unitaires :** Créer le fichier `tests/agents/factories/test_agent_factory.py`.
*   **Scénario de Test 1 :** "Test de l'instanciation de la factory".
    *   **Given :** Un `Kernel` mocké.
    *   **When :** On instancie `AgentFactory(mock_kernel, "test_service")`.
    *   **Then :** L'objet factory est créé sans erreur.
*   **Scénario de Test 2 :** "Test de l'appel à une méthode non implémentée".
    *   **Given :** Une instance de `AgentFactory`.
    *   **When :** On appelle `factory.create_informal_fallacy_agent()`.
    *   **Then :** Une exception `NotImplementedError` est bien levée (en utilisant `pytest.raises`).

#### **6. Commandes Git pour ce Lot**
```bash
# Ajouter les nouveaux fichiers et répertoires
git add argumentation_analysis/agents/abc/
git add argumentation_analysis/agents/agent_factory.py
git add tests/agents/factories/

# Commiter le travail avec un message respectant la convention
git commit -m "feat(arch): WO-01 - Implement architectural foundations" -m "Crée les classes AbstractAgent et AgentFactory qui serviront de base à tous les agents du système, conformément au plan d'exécution."
```

---
---

### **WO-02 : Mise en Place de la Configuration Centralisée**

**Statut :** À FAIRE
**Priorité :** Critique
**Dépendances :** WO-01

#### **1. Objectifs Détaillés**

Ce lot de travail s'attaque à un autre pilier de la robustesse logicielle : la gestion de la configuration. Éparpiller des valeurs de configuration (clés API, noms de modèles, timeouts) à travers le code est une source majeure de dette technique, rendant l'application difficile à déployer, à maintenir et à sécuriser.

L'objectif est de mettre en place un système de configuration centralisé, robuste et validé, qui :
1.  **Sépare clairement les secrets** (clés API) des **paramètres non-sensibles** (noms de modèles, réglages).
2.  **Valide la configuration au démarrage** de l'application pour éviter les erreurs à l'exécution.
3.  **Fournit un point d'entrée unique et fiable** (`KernelBuilder`) pour construire une instance du `Kernel` Semantic Kernel, pré-configurée avec tous les services nécessaires.

#### **2. Livrables Attendus**

1.  **Nouveau fichier :** `config.yaml` à la racine, pour les paramètres non-sensibles.
2.  **Nouveau fichier :** `.env.template` à la racine, comme modèle pour les secrets.
3.  **Nouveau répertoire :** `argumentation_analysis/core/`
4.  **Nouveau fichier :** `argumentation_analysis/core/config.py` contenant les modèles Pydantic pour la configuration.
5.  **Nouveau fichier :** `argumentation_analysis/core/kernel_builder.py` contenant le `KernelBuilder`.
6.  **Fichier de test :** `tests/core/test_kernel_builder.py`.

#### **3. Décomposition en Sous-Tâches Techniques**

##### **3.1. Création des Fichiers de Configuration**
*   **Action :** Créer `config.yaml` à la racine du projet avec la structure suivante. Ce fichier sera versionné.
    ```yaml
    # Fichier: config.yaml
    # Configuration non-sensible de l'application.
    
    agent_settings:
      timeout_seconds: 120
      max_correction_attempts: 3
    
    llm_services:
      # Service principal pour les agents de conversation et de raisonnement.
      default_chat:
        service_id: "default_chat_gpt4_turbo"
        model_id: "gpt-4-turbo"
        provider: "openai" # Options: openai, azure_openai
    
      # Service pour générer les embeddings pour la mémoire sémantique.
      default_embedding:
        service_id: "default_embedding_ada"
        model_id: "text-embedding-ada-002"
        provider: "openai"
    ```
*   **Action :** Créer `.env.template` à la racine. Ce fichier sert de guide et doit être ignoré par Git.
    ```dotenv
    # Fichier: .env.template
    # Copiez ce fichier en .env et remplissez les valeurs.
    # Ce fichier ne doit JAMAIS être commité.
    
    OPENAI_API_KEY="sk-..."
    # AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
    # AZURE_OPENAI_API_KEY="..."
    ```

##### **3.2. Implémentation du Modèle de Configuration Pydantic**
*   **Action :** Créer le fichier `argumentation_analysis/core/config.py`. Ce fichier est le cœur de la validation de la configuration. Il utilise `pydantic` et `pydantic-settings` pour charger, valider et exposer la configuration de manière sûre et typée.
*   **Action :** Créer le fichier `argumentation_analysis/core/config.py` et y ajouter les modèles Pydantic qui chargeront et valideront la configuration. Nécessite d'ajouter `pydantic-settings` aux dépendances du projet (`pyproject.toml`).
    ```python
    # Fichier: argumentation_analysis/core/config.py
    
    from pydantic import BaseModel, Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from typing import List, Literal
    
    # --- Modèles pour les structures internes de config.yaml ---
    
    class LLMServiceConfig(BaseModel):
        """Configuration pour un service LLM unique."""
        service_id: str
        model_id: str
        provider: Literal["openai", "azure_openai"]
    
    class AgentSettings(BaseModel):
        """Configuration globale pour le comportement des agents."""
        timeout_seconds: int = 120
        max_correction_attempts: int = 3
    
    class YAMLConfig(BaseModel):
        """Modèle Pydantic représentant la structure de config.yaml."""
        agent_settings: AgentSettings
        llm_services: List[LLMServiceConfig]
    
    # --- Modèle principal qui charge tout ---
    
    class AppConfig(BaseSettings):
        """
        Configuration globale de l'application.
        Charge les secrets depuis les variables d'environnement (ou fichier .env)
        et les paramètres depuis un fichier YAML spécifié.
        """
        # Secrets chargés depuis .env
        openai_api_key: str = Field(..., env="OPENAI_API_KEY")
        # azure_openai_endpoint: Optional[str] = Field(None, env="AZURE_OPENAI_ENDPOINT")
        # azure_openai_api_key: Optional[str] = Field(None, env="AZURE_OPENAI_API_KEY")
    
        # Paramètres chargés depuis le fichier YAML
        yaml_config: YAMLConfig
    
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
        )
    
    # helper pour charger la configuration
    def load_config() -> AppConfig:
        import yaml
        from pathlib import Path
    
        yaml_path = Path("config.yaml")
        if not yaml_path.exists():
            raise FileNotFoundError("Le fichier config.yaml est manquant.")
        
        with open(yaml_path, "r") as f:
            yaml_data = yaml.safe_load(f)
        
        # Valide le contenu YAML contre notre modèle
        yaml_config_obj = YAMLConfig(**yaml_data)
        
        # Charge les secrets depuis .env et combine avec la config YAML
        app_conf = AppConfig(yaml_config=yaml_config_obj)
        
        return app_conf
    ```

##### **3.3. Implémentation du `KernelBuilder`**
*   **Action :** Créer le fichier `argumentation_analysis/core/kernel_builder.py`.
    ```python
    # Fichier : argumentation_analysis/core/kernel_builder.py
    
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import (
        OpenAIChatCompletion,
        OpenAITextEmbedding,
    )
    # from .config import AppConfig, LLMServiceConfig # Sera utilisé ainsi
    
    class KernelBuilder:
        """
        Construit et configure une instance de Kernel à partir de la config centrale.
        
        Rôle et Justification :
        C'est le point de construction unique pour le Kernel. En utilisant cette
        classe, on s'assure que chaque partie de l'application (agents,
        orchestrateur) reçoit une instance du Kernel configurée de manière
        identique, évitant ainsi les configurations divergentes et les bugs
        difficiles à tracer.
        """
    
        @staticmethod
        def build_from_config(config_model) -> Kernel: # Type hint serait: config_model: AppConfig
            """Construit le Kernel en itérant sur la configuration chargée."""
            kernel = Kernel()
            
            for service_conf in config_model.yaml_config.llm_services:
                if "embedding" in service_conf.service_id:
                    # Configuration d'un service d'embedding
                    if service_conf.provider == "openai":
                        kernel.add_service(
                            OpenAITextEmbedding(
                                service_id=service_conf.service_id,
                                model_id=service_conf.model_id,
                                api_key=config_model.openai_api_key,
                            )
                        )
                else:
                    # Configuration d'un service de chat
                    if service_conf.provider == "openai":
                        kernel.add_service(
                            OpenAIChatCompletion(
                                service_id=service_conf.service_id,
                                model_id=service_conf.model_id,
                                api_key=config_model.openai_api_key,
                            )
                        )
                    # elif service_conf.provider == "azure_openai":
                    #     kernel.add_service(...) # Logique pour Azure OpenAI
            
            # Ici, on pourrait ajouter des plugins globaux si nécessaire
            
            return kernel
    ```

#### **4. Critères d'Acceptation (Definition of Done)**
*   Les fichiers `config.yaml`, `.env.template`, `config.py`, et `kernel_builder.py` sont créés et implémentés.
*   Les dépendances (`pydantic`, `pydantic-settings`, `pyyaml`) sont ajoutées au projet.
*   La fonction `load_config()` charge et valide avec succès la configuration depuis `config.yaml` et `.env`.
*   Le `KernelBuilder.build_from_config()` retourne un objet `Kernel` contenant les services spécifiés dans `config.yaml`.

#### **5. Plan de Test**
*   **Tests Unitaires :** Créer le fichier `tests/core/test_kernel_builder.py`.
*   **Scénario de Test 1 :** "Test du `KernelBuilder` avec une configuration OpenAI".
    *   **Given :** Un objet `AppConfig` mocké avec une configuration pour un service de chat et un service d'embedding OpenAI.
    *   **When :** On appelle `KernelBuilder.build_from_config(mock_config)`.
    *   **Then :** Le `Kernel` retourné contient bien deux services.
    *   **And :** Le service avec l'ID `default_chat_gpt4_turbo` est une instance de `OpenAIChatCompletion`.
    *   **And :** Le service avec l'ID `default_embedding_ada` est une instance de `OpenAITextEmbedding`.

#### **6. Commandes Git pour ce Lot**
```bash
# Ajouter les nouveaux fichiers
git add config.yaml .env.template
git add argumentation_analysis/core/
git add tests/core/

# Commiter le travail
git commit -m "feat(config): WO-02 - Implement centralized configuration" -m "Ajoute un système de configuration basé sur Pydantic, YAML et .env. Met en place un KernelBuilder pour construire une instance de Kernel à partir de cette configuration, garantissant une initialisation cohérente du système."
```

---
---
### **WO-03 : Refactoring du Premier Agent (`InformalAnalysisAgent`)**

**Statut :** À FAIRE
**Priorité :** Élevée
**Dépendances :** WO-01, WO-02

#### **1. Objectifs Détaillés**

Ce lot est le premier test grandeur nature de notre nouvelle architecture. L'objectif est double :
1.  **Résoudre le Bug Originel :** Le problème initial était l'incapacité du système à utiliser une taxonomie de sophismes spécifique. Nous allons le résoudre en implémentant un agent qui charge et injecte cette taxonomie dans son prompt à chaque exécution.
2.  **Valider le "Pattern de l'Agent Hybride" :** Nous allons transformer l'ancien `InformalAnalysisPlugin` en un `InformalFallacyAgent` robuste et autonome. Cet agent encapsulera sa propre logique et, surtout, garantira une **sortie de données structurée et fiable** en forçant le LLM à utiliser un outil Pydantic, éliminant ainsi tout parsing de texte fragile. Ce WO sert de "blueprint" pour la refactorisation de tous les autres agents.

#### **2. Livrables Attendus**

1.  **Nouveau répertoire :** `argumentation_analysis/agents/concrete_agents/`
2.  **Nouveau fichier :** `argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py`.
3.  **Mise à jour du fichier :** `argumentation_analysis/agents/agent_factory.py` avec l'implémentation de la méthode de création.
4.  **Fichier de test :** `tests/agents/concrete/test_informal_fallacy_agent.py`.

#### **3. Décomposition en Sous-Tâches Techniques**

##### **3.1. Création des Modèles de Données Pydantic**
*   **Action :** Définir les classes Pydantic qui serviront de contrat de données pour la sortie de l'agent. Ces classes seront placées au sein du fichier `informal_fallacy_agent.py` pour commencer, afin de maintenir la cohésion.
    ```python
    # Dans : argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py
    
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

##### **3.2. Implémentation de la Classe `InformalFallacyAgent`**
*   **Action :** Créer la classe de l'agent, en héritant de `AbstractAgent` et en implémentant sa logique métier.
    ```python
    # Dans : argumentation_analysis/agents/concrete_agents/informal_fallacy_agent.py
    
    # ... imports (AbstractAgent, Kernel, ChatMessageContent, etc.)
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
    
    from typing import Optional

class InformalFallacyAgent(AbstractAgent):
        """
        Agent spécialisé dans l'identification des sophismes informels
        en se basant sur une taxonomie et en garantissant une sortie structurée.
        """
        
        def setup_agent_components(self, llm_service_id: str) -> None:
            super().setup_agent_components(llm_service_id)
            # Pour cet agent, nous pourrions charger la taxonomie ici.
            # self.taxonomy = self._load_taxonomy()
            self.logger.info("Agent d'analyse de sophismes configuré.")
    
        def get_agent_capabilities(self) -> dict:
            capabilities = super().get_agent_capabilities()
            capabilities["pydantic_tool"] = "FallacyAnalysisResult"
            return capabilities
            
        async def get_response(
            self, messages: List[ChatMessageContent], arguments: KernelArguments, **kwargs: Any
        ) -> AgentResponseItem[ChatMessageContent]:
            
            text_to_analyze = arguments.get("input", "")
            if not text_to_analyze:
                raise ValueError("Le texte à analyser est manquant dans les arguments ('input').")
            
            self.logger.info(f"Analyse des sophismes pour le texte : '{text_to_analyze[:100]}...'")
            
            # --- Cœur du Pattern "Agent Hybride" ---
            analysis_result = await self._run_internal_analysis(text_to_analyze)
            
            response_json = analysis_result.model_dump_json(indent=2)
            
            response_message = ChatMessageContent(
                role="assistant",
                content=response_json,
                metadata={'result_type': 'fallacy_analysis'}
            )
            return AgentResponseItem(message=response_message, agent=self)
            
                async def _run_internal_analysis(self, text_to_analyze: str) -> FallacyAnalysisResult:
            """
            Exécute l'appel LLM interne de manière fiable en utilisant le pattern
            de boucle de correction pour gérer les échecs de validation Pydantic.
            """
            last_error = None
            for attempt in range(self.correction_attempts):
                prompt = self._build_analysis_prompt(text_to_analyze, last_error)
                
                execution_settings = OpenAIChatPromptExecutionSettings(
                    service_id=self.llm_service_id,
                    tool_choice="required",
                    tools=[FallacyAnalysisResult]
                )
                
                try:
                    response = await self.kernel.invoke_prompt(
                        prompt,
                        arguments=KernelArguments(settings=execution_settings)
                    )
                    
                    tool_calls = response.tool_calls
                    if not tool_calls:
                        self.logger.warning(f"Tentative {attempt + 1}: Le LLM n'a retourné aucun tool_call.")
                        # Pourrait être un cas où aucun sophisme n'est trouvé. On retourne un résultat sûr.
                        return FallacyAnalysisResult(is_fallacious=False, fallacies=[])
                    
                    # SK s'occupe de la désérialisation. Si elle échoue, une exception est levée.
                    analysis_object: FallacyAnalysisResult = tool_calls[0].to_tool_function()(**tool_calls[0].parse_arguments()) 
                    self.logger.info(f"Analyse réussie à la tentative {attempt + 1}.")
                    return analysis_object

                except Exception as e: # Inclut pydantic.ValidationError et autres erreurs SK
                    self.logger.warning(f"Tentative {attempt + 1} a échoué : {e}")
                    last_error = str(e)

            self.logger.error("Échec final de l'analyse après plusieurs tentatives de correction.")
            raise RuntimeError(f"Impossible d'obtenir une analyse valide du LLM après {self.correction_attempts} tentatives.")
            prompt = self._build_analysis_prompt(text_to_analyze)
            
            # Forcer l'utilisation de l'outil Pydantic. C'est la clé de la fiabilité.
            execution_settings = OpenAIChatPromptExecutionSettings(
                service_id=self.llm_service_id,
                tool_choice="required",
                tools=[FallacyAnalysisResult]
            )
            
            response = await self.kernel.invoke_prompt(
                prompt,
                arguments=KernelArguments(settings=execution_settings)
            )
            
            # Le kernel retourne les appels d'outils, déjà pré-parsés.
            tool_calls = response.tool_calls
            if not tool_calls:
                # Si le LLM n'appelle pas l'outil (cas rare avec "required"), on retourne un résultat sûr.
                self.logger.warning("Le LLM n'a retourné aucun tool_call malgré la contrainte 'required'.")
                return FallacyAnalysisResult(is_fallacious=False, fallacies=[])
            
            # Le kernel SK s'occupe de la désérialisation, on récupère directement l'objet.
            analysis_object: FallacyAnalysisResult = tool_calls[0].to_tool_function()(**tool_calls[0].parse_arguments())
            return analysis_object
            
                def _build_analysis_prompt(self, text_to_analyze: str, last_error: Optional[str] = None) -> str:
            """ Construit le prompt, en ajoutant un contexte de correction si nécessaire. """
            # Ici, on injecterait la taxonomie chargée. Pour l'instant, on la simule.
            taxonomy_summary = "Exemples de sophismes à rechercher : Ad Hominem, Pente Glissante, Faux Dilemme."
            
            return f"""
            Analysez le texte suivant pour y déceler des sophismes. Basez votre analyse
            UNIQUEMENT sur la taxonomie de sophismes fournie.
            Votre unique tâche est de remplir l'outil `FallacyAnalysisResult` avec vos découvertes.
        
            --- TAXONOMIE DISPONIBLE ---
            {taxonomy_summary}
            --- FIN DE LA TAXONOMIE ---
        
            --- TEXTE À ANALYSER ---
            {text_to_analyze}
            --- FIN DU TEXTE ---
            """
    ```

##### **3.3. Mise à Jour de `AgentFactory`**
*   **Action :** Compléter la méthode `create_project_manager_agent` dans la factory pour qu'elle puisse construire et configurer cet agent de manière centralisée.
*   **Action :** Modifier `agent_factory.py` pour implémenter concrètement la méthode de création de cet agent.
    ```python
    # Dans : argumentation_analysis/agents/agent_factory.py
    # Ajouter l'import
    from .concrete_agents.informal_fallacy_agent import InformalFallacyAgent
    
    # ... dans la classe AgentFactory ...
    
    def create_informal_fallacy_agent(self) -> AbstractAgent:
        """Crée et configure un agent d'analyse des sophismes."""
        agent = InformalFallacyAgent(
            kernel=self._kernel,
            name="FallacyAnalyst",
            description="Agent spécialiste de l'identification des sophismes informels sur la base d'une taxonomie, avec une sortie JSON garantie.",
            instructions="Votre rôle est d'analyser un texte pour y trouver des sophismes. Vous devez retourner votre analyse complète au format JSON structuré."
        )
        # Étape cruciale de configuration post-initialisation
        agent.setup_agent_components(self._llm_service_id)
        return agent
    ```

#### **4. Critères d'Acceptation (Definition of Done)**
*   La classe `InformalFallacyAgent` est créée, hérite de `AbstractAgent` et implémente la logique `get_response`.
*   L'agent utilise `tool_choice="required"` pour garantir une sortie structurée.
*   La `AgentFactory` est mise à jour et peut instancier `InformalFallacyAgent` sans erreur.
*   La méthode `create_informal_fallacy_agent` ne lève plus de `NotImplementedError`.

#### **5. Plan de Test**
*   **Tests Unitaires :** Créer le fichier `tests/agents/concrete/test_informal_fallacy_agent.py`.
*   **Scénario de Test 1 :** "Test du `get_response` avec un retour LLM mocké valide".
    *   **Given :** Une instance de `InformalFallacyAgent` avec un `Kernel` mocké.
    *   **And :** Le `Kernel` mocké est configuré pour retourner un `tool_call` contenant un `FallacyAnalysisResult` valide.
    *   **When :** On appelle `agent.get_response(...)`.
    *   **Then :** La réponse de l'agent (`AgentResponseItem.message.content`) est une chaîne JSON qui correspond au `FallacyAnalysisResult` attendu.
    *   **And :** `kernel.invoke_prompt` a été appelé une fois avec des `execution_settings` contenant `tool_choice="required"`.

#### **6. Commandes Git pour ce Lot**
```bash
# Ajouter les nouveaux fichiers et les modifications
git add argumentation_analysis/agents/concrete_agents/
git add argumentation_analysis/agents/agent_factory.py
git add tests/agents/concrete/

# Commiter le travail
git commit -m "feat(agents): WO-03 - Implement InformalFallacyAgent" -m "Crée le premier agent concret en utilisant la nouvelle architecture. Cet agent applique le pattern 'Agent Hybride' avec Pydantic pour garantir une sortie structurée, résolvant ainsi l'un des problèmes fondamentaux du système précédent."
```

---
---

### **WO-04 : Refactoring des Autres Agents (Exemple: `ProjectManagerAgent`)**

**Statut :** À FAIRE
**Priorité :** Élevée
**Dépendances :** WO-01, WO-02

#### **1. Objectifs Détaillés**

Après avoir validé notre architecture sur un agent "producteur de données" (WO-03), ce lot de travail vise à appliquer le même pattern de robustesse à un agent "orchestrateur" : le `ProjectManagerAgent`. L'objectif est de remplacer la logique fragile de l'ancien système (où le `ProjectManager` retournait du texte libre contenant `designate_next_agent(...)`) par une communication explicite et structurée.

En forçant le `ProjectManagerAgent` à utiliser un outil Pydantic pour déclarer sa décision, nous éliminons toute ambiguïté et nous rendons ses actions directement exploitables par des stratégies d'orchestration intelligentes, comme décrit dans la **Partie 1** du document d'architecture.

#### **2. Livrables Attendus**

1.  **Nouveau fichier :** `argumentation_analysis/agents/concrete_agents/project_manager_agent.py`.
2.  **Mise à jour du fichier :** `argumentation_analysis/agents/agent_factory.py` avec l'implémentation de la méthode de création.
3.  **Fichier de test :** `tests/agents/concrete/test_project_manager_agent.py`.

#### **3. Décomposition en Sous-Tâches Techniques**

##### **3.1. Création du Modèle de Données `NextAction`**
*   **Action :** Définir un modèle Pydantic qui capture la décision de l'agent. Ce modèle est le "contrat" que le Project Manager s'engage à respecter. Sa sortie n'est plus du texte libre, mais un objet structuré, prévisible et directement utilisable par le système d'orchestration.
*   **Action :** Définir un modèle Pydantic simple mais puissant qui capture la décision de l'agent.
    ```python
    # Dans : argumentation_analysis/agents/concrete_agents/project_manager_agent.py
    
    from pydantic import BaseModel, Field
    from typing import Optional
    
    class NextAction(BaseModel):
        """
        Modèle de données pour la décision du Project Manager.
        Force l'agent à prendre une décision claire et non ambiguë.
        """
        next_agent_to_speak: str = Field(..., description="Le nom exact de l'agent qui doit parler ensuite. Doit être l'un des agents disponibles.")
        thought_process: str = Field(..., description="Brève explication de pourquoi cet agent a été choisi.")
        is_task_complete: bool = Field(False, description="Mettre à 'true' UNIQUEMENT si l'objectif final de l'analyse est atteint et que la conversation doit se terminer.")
    ```

##### **3.2. Implémentation du `ProjectManagerAgent`**
*   **Action :** Créer la classe de l'agent en appliquant le même pattern d'Agent Hybride que pour le WO-03. L'agent encapsule sa logique de décision et garantit une sortie structurée.
*   **Action :** Créer la classe de l'agent en appliquant le même pattern que pour l'agent de sophismes.
    ```python
    # Dans : argumentation_analysis/agents/concrete_agents/project_manager_agent.py
    
    # ... imports (AbstractAgent, Kernel, etc.)
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
    
    class ProjectManagerAgent(AbstractAgent):
        """
        Agent chef d'orchestre. Son rôle n'est pas de produire une analyse,
        mais de guider la conversation en désignant le prochain intervenant.
        """
        
        def setup_agent_components(self, llm_service_id: str) -> None:
            super().setup_agent_components(llm_service_id)
            self.logger.info("Agent Chef de Projet configuré.")
            
        async def get_response(
            self, messages: List[ChatMessageContent], arguments: KernelArguments, **kwargs: Any
        ) -> AgentResponseItem[ChatMessageContent]:
            
            # Les noms des agents disponibles seront passés dans les arguments.
            available_agents = arguments.get("available_agents", [])
            if not available_agents:
                raise ValueError("La liste des agents disponibles est manquante.")
            
            self.logger.info(f"Le Project Manager délibère... Agents disponibles : {available_agents}")
            
            next_action_result = await self._decide_next_action(messages, available_agents)
            
            response_json = next_action_result.model_dump_json(indent=2)
            
            response_message = ChatMessageContent(
                role="assistant",
                content=response_json,
                metadata={'result_type': 'coordination_decision'}
            )
            return AgentResponseItem(message=response_message, agent=self)
            
        async def _decide_next_action(self, history: List[ChatMessageContent], available_agents: List[str]) -> NextAction:
            prompt = self._build_coordination_prompt(history, available_agents)
            
            execution_settings = OpenAIChatPromptExecutionSettings(
                service_id=self.llm_service_id,
                tool_choice="required",
                tools=[NextAction]
            )
            
            response = await self.kernel.invoke_prompt(
                prompt,
                arguments=KernelArguments(settings=execution_settings)
            )
            
            tool_calls = response.tool_calls
            if not tool_calls:
                self.logger.error("Le Project Manager n'a pas réussi à prendre une décision structurée.")
                # Retourne une action par défaut pour ne pas bloquer le système
                return NextAction(next_agent_to_speak=available_agents[0], thought_process="Action par défaut suite à une erreur.", is_task_complete=False)
            
            return tool_calls[0].to_tool_function()(**tool_calls[0].parse_arguments())
            
        def _build_coordination_prompt(self, history: List[ChatMessageContent], available_agents: List[str]) -> str:
            history_str = "\n".join([f"[{msg.role}]: {msg.content}" for msg in history])
            agents_str = ", ".join(available_agents)
            
            return f"""
            Vous êtes un chef de projet expert en analyse d'arguments. Votre unique rôle est de
            coordonner la conversation. En vous basant sur l'historique ci-dessous et la liste
            des agents disponibles, vous devez décider quel agent doit intervenir ensuite.
            Utilisez l'outil `NextAction` pour communiquer votre décision.

            --- AGENTS DISPONIBLES ---
            {agents_str}

            --- HISTORIQUE DE LA CONVERSATION ---
            {history_str}
            --- FIN DE L'HISTORIQUE ---

            Analysez l'historique et déterminez la prochaine action la plus logique.
            """
    ```

##### **3.3. Mise à Jour de `AgentFactory`**
*   **Action :** Compléter la méthode `create_project_manager_agent`.
    ```python
    # Dans : argumentation_analysis/agents/agent_factory.py
    # Ajouter l'import
    from .concrete_agents.project_manager_agent import ProjectManagerAgent
    
    # ... dans la classe AgentFactory ...
    
    def create_project_manager_agent(self) -> AbstractAgent:
        """Crée et configure l'agent chef de projet."""
        agent = ProjectManagerAgent(
            kernel=self._kernel,
            name="ProjectManager",
            description="Agent coordinateur qui analyse l'état de la conversation et désigne le prochain intervenant via une sortie JSON.",
            instructions="Votre rôle est de décider qui parle ensuite. Utilisez l'outil `NextAction` pour spécifier votre choix."
        )
        agent.setup_agent_components(self._llm_service_id)
        return agent
    ```


#### **4. Critères d'Acceptation (Definition of Done)**
*   La classe `ProjectManagerAgent` est créée, implémentée, et utilise l'outil Pydantic `NextAction`.
*   La `AgentFactory` est mise à jour pour instancier `ProjectManagerAgent` sans erreur.
*   La méthode `create_project_manager_agent` ne lève plus de `NotImplementedError`.

#### **5. Plan de Test**
*   **Tests Unitaires :** Créer le fichier `tests/agents/concrete/test_project_manager_agent.py`.
*   **Scénario de Test 1 :** "Test du `get_response` avec une décision mockée".
    *   **Given :** Une instance de `ProjectManagerAgent` avec un `Kernel` mocké et une liste d'agents disponibles.
    *   **And :** Le `Kernel` mocké est configuré pour retourner un `tool_call` contenant une instance de `NextAction` (ex: `next_agent_to_speak="FallacyAnalyst"`).
    *   **When :** On appelle `agent.get_response(...)`.
    *   **Then :** La réponse de l'agent est une chaîne JSON contenant `"next_agent_to_speak": "FallacyAnalyst"`.

#### **6. Commandes Git pour ce Lot**
```bash
# Ajouter les nouveaux fichiers et les modifications
git add argumentation_analysis/agents/concrete_agents/project_manager_agent.py
git add argumentation_analysis/agents/agent_factory.py # Fichier déjà suivi, on ajoute les modifs
git add tests/agents/concrete/test_project_manager_agent.py

# Commiter le travail
git commit -m "feat(agents): WO-04 - Implement ProjectManagerAgent" -m "Refactorise le ProjectManagerAgent pour utiliser la nouvelle architecture et une sortie Pydantic structurée (`NextAction`), éliminant la communication textuelle ambiguë pour la coordination."
```

---
---

### **WO-05 : Remplacement Final de l'Orchestrateur**

> **NOTE DE CONCEPTION CRITIQUE :**
> Ce lot de travail doit impérativement être réalisé sur la version du fichier `argumentation_analysis/orchestration/analysis_runner.py` telle qu'elle existera après l'exécution de la **Phase 1 : Restauration de la Base de Code**. Nous ne modifions pas la version actuellement dégradée, mais nous remplaçons la logique de la version saine d'origine (commit `69736e25ec...`), qui est une coquille vide, par la nouvelle orchestration `AgentGroupChat`.

**Statut :** À FAIRE
**Priorité :** Critique
**Dépendances :** WO-03, WO-04

#### **1. Objectifs Détaillés**

C'est l'aboutissement de tout le travail de refactoring. Ce lot de travail consiste à démanteler définitivement la boucle de contrôle manuelle et fragile dans `analysis_runner.py` et à la remplacer par la nouvelle architecture d'orchestration basée sur `AgentGroupChat`. En assemblant les briques créées dans les lots précédents (agents via la factory, configuration, stratégies), nous allons mettre en place un système déclaratif, où la logique de collaboration est déléguée à des composants spécialisés plutôt qu'encodée en dur.

L'objectif final est de transformer `analysis_runner.py` d'un script de contrôle complexe en un simple "point d'entrée" qui configure et lance l'orchestrateur intelligent.

#### **2. Livrables Attendus**

1.  **Fichier Modifié :** `argumentation_analysis/orchestration/analysis_runner.py` complètement refactorisé.
2.  **Nouveau répertoire :** `argumentation_analysis/orchestration/strategies/`
3.  **Nouveau fichier :** `argumentation_analysis/orchestration/strategies/selection.py` (pour la logique de stratégie de sélection).
4.  **Nouveau fichier :** `argumentation_analysis/orchestration/strategies/termination.py` (pour la logique de stratégie de terminaison).
5.  **Fichier de test :** `tests/orchestration/test_analysis_runner.py`.

#### **3. Décomposition en Sous-Tâches Techniques**

##### **3.1. Implémentation des Stratégies d'Orchestration**
*   **Action :** Créer le répertoire et les fichiers de stratégies. Le code ci-dessous est une implémentation prête à l'emploi qui peut être directement utilisée.
*   **Action :** Créer les fichiers pour les stratégies et y implémenter les factories de création, comme défini dans la Partie 1 de l'architecture.

    ```python
    # Dans : argumentation_analysis/orchestration/strategies/selection.py
    
    from semantic_kernel import Kernel
    from semantic_kernel.agents.strategies.selection import KernelFunctionSelectionStrategy
    
    def create_llm_driven_selection_strategy(kernel: Kernel) -> KernelFunctionSelectionStrategy:
        """Crée la stratégie de sélection pilotée par LLM."""
        select_agent_prompt = """
        Vous êtes un chef d'orchestre expert en analyse d'arguments. En vous basant sur l'historique
        de la conversation et les descriptions des agents, quel agent doit intervenir ensuite ?
        Votre réponse doit être UNIQUEMENT le nom de l'agent, et rien d'autre.
    
        AGENTS DISPONIBLES:
        {{$agents}}
    
        HISTORIQUE:
        {{$history}}
    
        Prochain agent à parler :
        """
        selection_function = kernel.create_function_from_prompt(
            prompt=select_agent_prompt,
            function_name="DecideNextAgent",
            description="Décide quel agent doit parler ensuite."
        )
    
        return KernelFunctionSelectionStrategy(
            kernel=kernel,
            function=selection_function,
            result_parser=lambda result: str(result).strip().replace("\"", "")
        )
    ```

    ```python
    # Dans : argumentation_analysis/orchestration/strategies/termination.py
    
    from semantic_kernel import Kernel
    from semantic_kernel.agents.strategies.termination import (
        AggregatorTerminationStrategy,
        KernelFunctionTerminationStrategy,
        DefaultTerminationStrategy,
        AggregateTerminationCondition,
    )
    
    def create_composite_termination_strategy(kernel: Kernel, max_iterations: int = 15) -> AggregatorTerminationStrategy:
        """Crée une stratégie de terminaison composite."""
        terminate_prompt = """
        L'objectif de l'analyse est-il atteint ? La tâche est considérée comme terminée
        si une synthèse finale a été fournie ou si une décision explicite de fin est présente.
        Répondez unqiuement par "true" ou "false".
        
        HISTORIQUE: {{$history}}
        
        Tâche terminée :
        """
        semantic_termination = KernelFunctionTerminationStrategy(
            kernel=kernel,
            function=kernel.create_function_from_prompt(prompt=terminate_prompt),
            result_parser=lambda result: "true" in str(result).lower()
        )
    
        failsafe_termination = DefaultTerminationStrategy(maximum_iterations=max_iterations)
    
        return AggregatorTerminationStrategy(
            strategies=[semantic_termination, failsafe_termination],
            condition=AggregateTerminationCondition.ANY
        )
    ```

##### **3.2. Refactoring Complet de `analysis_runner.py`**
*   **Action :** Vider la fonction `run_analysis_conversation` (ou le point d'entrée équivalent dans le fichier restauré) et la remplacer par le code d'assemblage ci-dessous. Ce code agit comme le point de démarrage de l'application, assemblant toutes les briques construites précédemment.
*   **Action :** Remplacer le contenu de la fonction principale (ex: `run_analysis_conversation`) par la logique d'assemblage.

    ```python
    # Dans : argumentation_analysis/orchestration/analysis_runner.py
    
    # Imports des nouvelles briques
    from argumentation_analysis.core.config import load_config
    from argumentation_analysis.core.kernel_builder import KernelBuilder
    from argumentation_analysis.agents.agent_factory import AgentFactory
    from .strategies.selection import create_llm_driven_selection_strategy
    from .strategies.termination import create_composite_termination_strategy
    
    from semantic_kernel.agents.group_chat import AgentGroupChat
    from semantic_kernel.contents import ChatMessageContent
    
    async def run_analysis_conversation(text_to_analyze: str):
        """
        Point d'entrée principal de l'analyse.
        Orchestre une conversation entre agents pour analyser un texte.
        """
        # 1. Charger la configuration
        config = load_config()
    
        # 2. Construire le Kernel
        kernel = KernelBuilder.build_from_config(config)
    
        # 3. Instancier la Factory d'Agents
        agent_factory = AgentFactory(kernel, config.yaml_config.llm_services[0].service_id)
    
        # 4. Créer les agents nécessaires
        pm_agent = agent_factory.create_project_manager_agent()
        fallacy_agent = agent_factory.create_informal_fallacy_agent()
        # ... autres agents ...
        agents = [pm_agent, fallacy_agent]
    
        # 5. Construire les stratégies
        selection_strategy = create_llm_driven_selection_strategy(kernel)
        termination_strategy = create_composite_termination_strategy(kernel, config.yaml_config.agent_settings.max_correction_attempts)
    
        # 6. Assembler et configurer l'orchestrateur
        group_chat = AgentGroupChat(
            agents=agents,
            selection_strategy=selection_strategy,
            termination_strategy=termination_strategy,
        )
    
        # 7. Lancer l'orchestration
        initial_history = [ChatMessageContent(role="user", content=f"Veuillez analyser le texte suivant: {text_to_analyze}")]
        
        final_history = [message async for message in group_chat.invoke(history=initial_history)]
    
        # 8. Retourner le résultat final
        return final_history
    ```

#### **4. Critères d'Acceptation (Definition of Done)**
*   Le fichier `analysis_runner.py` ne contient plus de boucle `for` manuelle ni de parsing de texte pour l'orchestration.
*   La logique d'orchestration est entièrement déléguée à une instance de `AgentGroupChat`.
*   Les stratégies de sélection et de terminaison sont implémentées dans des fichiers séparés et utilisées par le runner.
*   L'ensemble du processus (config, kernel, factory, agents, chat) s'exécute sans erreur.

#### **5. Plan de Test**
*   **Tests d'Intégration :** Créer le fichier `tests/orchestration/test_analysis_runner.py`.
*   **Scénario de Test 1 :** "Test du flux d'analyse complet avec des agents mockés".
    *   **Given :** Des `MockAgent` (agents avec des réponses prédéfinies) qui simulent une conversation en 2 étapes se terminant par une décision de fin.
    *   **And :** Des stratégies de sélection et de terminaison simplifiées (non-LLM) qui réagissent aux mots-clés dans les réponses des `MockAgent`.
    *   **When :** On appelle `run_analysis_conversation("texte de test")`.
    *   **Then :** La fonction s'exécute jusqu'au bout.
    *   **And :** L'historique final contient le bon nombre de messages, prouvant que le `AgentGroupChat` a bien tourné et s'est arrêté comme prévu.

#### **6. Commandes Git pour ce Lot**
```bash
# Ajouter les nouveaux fichiers et les modifications
git add argumentation_analysis/orchestration/
git add tests/orchestration/

# Commiter le travail
git commit -m "feat(orchestration): WO-05 - Replace runner with AgentGroupChat" -m "Démantèle l'ancienne boucle d'orchestration manuelle et la remplace par une implémentation complète de AgentGroupChat. Assemble toutes les briques précédentes (config, kernel, factory, agents, stratégies) pour créer un système déclaratif et robuste."
```

---
---

### **WO-06 : Implémentation de la Stratégie de Tests Complète**

**Statut :** À FAIRE
**Priorité :** Élevée
**Dépendances :** WO-05

#### **1. Objectifs Détaillés**

Un code non testé est un code cassé par nature. Ce lot de travail final est le filet de sécurité qui garantira la pérennité, la robustesse et la non-régression de la nouvelle architecture. L'objectif n'est pas d'atteindre 100% de couverture de code, mais de mettre en place une stratégie de test pragmatique et multi-niveaux, comme défini dans la **Partie 4.3** de l'architecture, afin que chaque composant critique soit validé de manière appropriée.

Nous allons construire la pyramide des tests pour notre système :
*   **Base (Tests Unitaires) :** Des tests rapides et nombreux pour valider la logique interne de chaque agent et de chaque composant, de manière isolée.
*   **Milieu (Tests d'Intégration) :** Des tests pour valider que les composants critiques (comme l'orchestrateur `AgentGroupChat`) fonctionnent bien ensemble, en utilisant des simulations.
*   **Sommet (Tests End-to-End) :** Quelques tests globaux pour s'assurer que le système complet produit les résultats attendus sur des cas d'usage représentatifs et pour détecter les régressions de comportement liées aux changements de prompts ou de modèles LLM.

#### **2. Livrables Attendus**

1.  **Tests Unitaires Complets** pour tous les nouveaux composants :
    *   `tests/core/test_kernel_builder.py`
    *   `tests/agents/factories/test_agent_factory.py`
    *   `tests/agents/concrete/test_informal_fallacy_agent.py`
    *   `tests/agents/concrete/test_project_manager_agent.py`
2.  **Tests d'Intégration** pour l'orchestration :
    *   `tests/orchestration/test_analysis_runner.py`
3.  **Infrastructure de Tests End-to-End** :
    *   Répertoire `tests/e2e/inputs/` avec des exemples de textes à analyser.
    *   Répertoire `tests/e2e/goldens/` avec les "fichiers d'or" des résultats attendus.
    *   Fichier de test `tests/e2e/test_golden_files.py`.

#### **3. Décomposition en Sous-Tâches Techniques**

##### **3.1. Implémentation des Tests Unitaires (Consolidation)**
*   **Action :** Pour chaque agent et chaque service créé, implémenter des tests unitaires qui valident sa logique en isolation complète.
*   **Méthodologie Clé :** L'outil principal sera `unittest.mock.AsyncMock`. L'objectif est de simuler le comportement du `Kernel` ou de toute autre dépendance externe. Le test ne doit JAMAIS faire d'appel réseau ou d'I/O. Pour un agent, le test typique consistera à mocker la méthode `kernel.invoke_prompt` pour qu'elle retourne une réponse LLM simulée (un `tool_call` valide), puis à vérifier que la méthode `get_response` de l'agent traite correctement cette réponse et produit le JSON attendu.
*   **Action :** Implémenter les scénarios de test définis dans les WOs précédents.
*   **Méthodologie :**
    *   Utiliser `pytest` comme framework de test.
    *   Utiliser `unittest.mock.AsyncMock` pour simuler les objets `Kernel` et leurs réponses (`invoke_prompt`).
    *   Pour chaque agent, le test clé consiste à fournir une réponse `tool_call` mockée depuis le `Kernel` et à vérifier que la méthode `get_response` de l'agent la traite correctement et retourne le format attendu.

##### **3.2. Implémentation des Tests d'Intégration (Consolidation)**
*   **Action :** Valider que les composants principaux s'intègrent correctement, en particulier `AgentGroupChat` et ses stratégies.
*   **Méthodologie Clé :** Créer des `MockAgent` qui retournent des réponses prédéfinies et déterministes. Créer également des stratégies de sélection/terminaison simplistes qui réagissent à des mots-clés dans ces réponses (par exemple, la stratégie s'arrête si un agent retourne `"decision": "TERMINATE"`). Le test consiste à assembler un `AgentGroupChat` avec ces faux composants et à vérifier que la conversation se déroule comme prévu (nombre de tours, agent sélectionné, arrêt correct).
*   **Action :** Implémenter le test d'intégration pour `analysis_runner` qui valide le bon fonctionnement de `AgentGroupChat` sans faire d'appels LLM réels.
*   **Méthodologie :**
    *   Créer une classe utilitaire `MockAgent(AbstractAgent)` qui retourne des réponses prédéfinies et déterministes.
    *   Créer des stratégies de sélection et de terminaison simplistes qui ne dépendent pas d'un LLM, mais réagissent à des mots-clés dans les réponses des `MockAgent` (ex: `selection_strategy` choisit l'agent dont le nom est mentionné, `termination_strategy` s'arrête si elle voit le mot `TERMINATE`).
    *   Le test consiste à assembler un `AgentGroupChat` avec ces composants mockés et à vérifier que le déroulement de la conversation (nombre de tours, contenu des messages, condition d'arrêt) est conforme aux attentes.

##### **3.3. Mise en Place de l'Infrastructure de Tests End-to-End**
*   **Action :** Mettre en œuvre le processus "Golden File" pour détecter les régressions de comportement global.
*   **Méthodologie Clé :** 
    1.  **Générer le Fichier d'Or :** Créer un cas de test d'entrée représentatif (`input.txt`). L'exécuter une fois avec de vrais appels LLM et sauvegarder le résultat JSON validé par un humain dans `output.json.golden`.
    2.  **Créer le Test Automatisé :** Ce test (souvent marqué comme `e2e` pour être exécuté séparément) refait l'analyse sur `input.txt` et compare le nouveau JSON de sortie avec le contenu du fichier `.golden`. Il échoue si les deux diffèrent. Cela signale une régression ou un changement de comportement qui doit être validé manuellement (soit en corrigeant le code, soit en mettant à jour le fichier d'or si le nouveau comportement est accepté).
*   **Action :** Mettre en œuvre le processus "Golden File".
*   **Processus :**
    1.  **Créer un cas de test :** Placer un fichier `complex_argument.txt` dans `tests/e2e/inputs/`. Ce fichier contient un exemple de texte complexe et représentatif.
    2.  **Génération Manuelle du Fichier d'Or :** Exécuter une seule fois le `run_analysis_conversation` sur ce fichier d'entrée. Sauvegarder la sortie JSON complète et formatée dans `tests/e2e/goldens/complex_argument.json.golden`. Ce fichier doit être relu et validé par un humain pour s'assurer qu'il représente bien le résultat "idéal" attendu. Il est ensuite commité.
    3.  **Création du Test Automatisé :** Implémenter `tests/e2e/test_golden_files.py`. Ce test (marqué comme `slow` ou `e2e` dans `pytest` pour pouvoir être ignoré lors des exécutions rapides) doit :
        a. Lire `complex_argument.txt`.
        b. Exécuter `run_analysis_conversation` (avec de vrais appels LLM).
        c. Lire le fichier `complex_argument.json.golden`.
        d. Comparer le JSON nouvellement généré avec le JSON du fichier d'or. Le test échoue en cas de différence.
*   **Justification :** Ce test est le seul capable de détecter des régressions de comportement dues à des changements de version d'un modèle LLM ou à des modifications de prompts qui altèrent subtilement le résultat.

#### **4. Critères d'Acceptation (Definition of Done)**
*   Tous les tests unitaires et d'intégration sont implémentés et passent avec succès.
*   L'infrastructure de test E2E est en place et le premier test "golden file" est fonctionnel.
*   L'ensemble de la suite de tests peut être exécuté via une simple commande `pytest`.

#### **5. Commandes Git pour ce Lot**
```bash
# Ajouter tous les fichiers de test
git add tests/

# Commiter le travail
git commit -m "test(refactor): WO-06 - Implement comprehensive testing strategy" -m "Ajoute la suite de tests complète pour la nouvelle architecture : tests unitaires avec mocks pour les composants, tests d'intégration pour l'orchestration, et une infrastructure de tests end-to-end de type 'golden file' pour la détection de régression."
```