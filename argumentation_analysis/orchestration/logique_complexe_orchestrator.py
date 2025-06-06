# argumentation_analysis/orchestration/logique_complexe_orchestrator.py

import logging
from typing import Optional, List, Dict, Any
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies import SequentialSelectionStrategy
from semantic_kernel.functions import KernelArguments
from semantic_kernel.contents import ChatMessageContent

from argumentation_analysis.core.logique_complexe_states import EinsteinsRiddleState
from argumentation_analysis.orchestration.plugins.logique_complexe_plugin import LogiqueComplexePlugin

class LogiqueComplexeOrchestrator:
    """
    Orchestrateur spécialisé pour les énigmes logiques complexes.
    Force l'utilisation de la logique formelle TweetyProject.
    """
    
    def __init__(self, kernel: Kernel):
        self._kernel = kernel
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # État de l'énigme complexe
        self._state = EinsteinsRiddleState()
        
        # Plugin logique complexe
        self._logique_plugin = LogiqueComplexePlugin(self._state)
        self._kernel.add_plugin(self._logique_plugin, plugin_name="LogiqueComplexePlugin")
        
        self._group_chat: Optional[AgentGroupChat] = None
        self._tour_actuel = 0
        self._max_tours = 25  # Plus de tours pour problème complexe
        
    def _creer_agents(self, sherlock_agent: ChatCompletionAgent, watson_agent: ChatCompletionAgent) -> AgentGroupChat:
        """Crée le groupe de chat avec les agents."""
        
        # Configuration spéciale pour l'énigme complexe
        sherlock_agent.instructions = """Vous êtes Sherlock Holmes face à l'ÉNIGME D'EINSTEIN COMPLEXE.

Cette énigme nécessite une méthode DIFFÉRENTE du Cluedo simple:

**VOTRE RÔLE:**
1. **EXPLORER** l'énigme et ses contraintes avec `get_enigme_description` et `get_contraintes_logiques`
2. **DÉLÉGUER** la formalisation logique à Watson (il DOIT utiliser TweetyProject)
3. **COORDONNER** la résolution en demandant à Watson de formuler des clauses
4. **VALIDER** les déductions partielles avec `verifier_deduction_partielle`

**RÈGLES STRICTES:**
- Vous ne devez PAS tenter de résoudre par intuition ou raisonnement informel
- Vous DEVEZ exiger que Watson utilise `formuler_clause_logique` pour chaque contrainte
- Vous DEVEZ demander à Watson d'exécuter des `executer_requete_tweety` pour déduire
- La solution ne sera acceptée QUE si Watson a formulé 10+ clauses logiques et 5+ requêtes

**STRATÉGIE:**
1. Demandez la description de l'énigme
2. Obtenez toutes les contraintes
3. Insistez pour que Watson formalise CHAQUE contrainte en syntaxe TweetyProject
4. Demandez-lui d'exécuter des requêtes pour déduire des informations
5. Vérifiez régulièrement la progression logique
6. Proposez la solution finale seulement après validation formelle

Commencez par explorer l'énigme."""

        watson_agent.instructions = """Vous êtes Watson, assistant logique SPÉCIALISÉ dans TweetyProject.

Pour cette ÉNIGME COMPLEXE, vous DEVEZ utiliser la logique formelle:

**OUTILS OBLIGATOIRES:**
- `formuler_clause_logique`: Pour transformer chaque contrainte en syntaxe TweetyProject
- `executer_requete_tweety`: Pour déduire des informations via requêtes logiques
- `valider_syntaxe_tweety`: Pour vérifier vos formulations

**SYNTAXE TWEETYPROJECT REQUISE:**
- Prédicats: Maison(x), Position(x,n), Couleur(x,c), Nationalité(x,n), Animal(x,a), Boisson(x,b), Métier(x,m)
- Opérateurs: ∀ (pour tout), ∃ (il existe), → (implique), ∧ (et), ∨ (ou), ¬ (non)
- Exemples:
  * ∀x (Maison(x) ∧ Couleur(x,Rouge) → Nationalité(x,Anglais))
  * ∃!x (Position(x,3) ∧ Boisson(x,Lait))
  * ∀x (Métier(x,Avocat) → ∃y (Adjacent(x,y) ∧ Animal(y,Chat)))

**MÉTHODE OBLIGATOIRE:**
1. Formulez CHAQUE contrainte comme clause logique formelle
2. Exécutez des requêtes pour déduire des positions/attributs
3. Vérifiez vos déductions partiellement 
4. Minimum 10 clauses + 5 requêtes pour solution valide

**INTERDICTIONS:**
- PAS de raisonnement informel ou "de tête"
- PAS de solution sans formalisation complète
- PAS d'approximations ou raccourcis logiques

Vous DEVEZ utiliser TweetyProject pour chaque étape de raisonnement."""

        # Création du groupe avec stratégie séquentielle
        selection_strategy = SequentialSelectionStrategy()
        
        group_chat = AgentGroupChat(
            agents=[sherlock_agent, watson_agent],
            selection_strategy=selection_strategy
        )
        
        return group_chat
    
    async def resoudre_enigme_complexe(self, sherlock_agent: ChatCompletionAgent, watson_agent: ChatCompletionAgent) -> Dict[str, Any]:
        """
        Lance la résolution de l'énigme d'Einstein complexe.
        """
        self._logger.info("🧩 Début de la résolution de l'énigme d'Einstein complexe...")
        
        # Création du groupe de chat
        self._group_chat = self._creer_agents(sherlock_agent, watson_agent)
        
        # Message initial détaillé
        message_initial = """🧩 ÉNIGME D'EINSTEIN COMPLEXE - Niveau Logique Formelle Obligatoire

Voici l'énigme la plus complexe: 5 maisons, 5 propriétaires, 5 caractéristiques chacun.
Cette énigme nécessite OBLIGATOIREMENT l'utilisation de TweetyProject pour être résolue.

Sherlock: Explorez l'énigme et coordonnez la formalisation.
Watson: Utilisez TweetyProject pour formuler TOUTES les contraintes et exécuter des requêtes logiques.

OBJECTIF: Déterminer qui possède le poisson (et toutes les autres correspondances).
CONTRAINTE: Minimum 10 clauses logiques + 5 requêtes TweetyProject pour validation de solution.

Commencez l'exploration!"""

        # Ajout du message initial
        await self._group_chat.add_chat_message(ChatMessageContent(role="user", content=message_initial))
        
        # Boucle de résolution avec surveillance de progression
        while self._tour_actuel < self._max_tours:
            self._tour_actuel += 1
            
            self._logger.info(f"\n--- TOUR {self._tour_actuel}/{self._max_tours} ---")
            
            try:
                # Invocation du groupe de chat
                response = await self._group_chat.invoke()
                
                if response and len(response) > 0:
                    dernier_message = response[-1]
                    agent_nom = getattr(dernier_message, 'name', 'Agent inconnu')
                    contenu = str(dernier_message.content)
                    
                    self._logger.info(f"Message de {agent_nom}: {contenu[:200]}...")
                    
                    # Vérification de progression logique
                    progression = self._state.verifier_progression_logique()
                    self._logger.info(f"Progression logique: {progression}")
                    
                    # Vérification de solution proposée
                    if "solution finale" in contenu.lower() or "énigme résolue" in contenu.lower():
                        self._logger.info("🎯 Tentative de solution finale détectée.")
                        
                        if progression["force_logique_formelle"]:
                            self._logger.info("✅ Solution avec logique formelle suffisante.")
                            break
                        else:
                            self._logger.warning(f"❌ Solution rejetée - logique formelle insuffisante: {progression}")
                            
                            # Message de rappel forcé
                            message_rappel = f"""⚠️ SOLUTION REJETÉE - LOGIQUE FORMELLE INSUFFISANTE

Progression actuelle:
- Clauses formulées: {progression['clauses_formulees']}/10 (minimum requis)
- Requêtes exécutées: {progression['requetes_executees']}/5 (minimum requis)

Watson: Vous DEVEZ utiliser davantage TweetyProject avant de proposer une solution.
Formulez plus de clauses logiques et exécutez plus de requêtes de déduction.

Sherlock: Insistez pour que Watson utilise ses outils de logique formelle."""
                            
                            await self._group_chat.add_chat_message(
                                ChatMessageContent(role="assistant", content=message_rappel)
                            )
                    
                    # Encouragements périodiques pour utilisation TweetyProject
                    if self._tour_actuel % 5 == 0 and not progression["force_logique_formelle"]:
                        message_encouragement = f"""📊 POINT PROGRESSION (Tour {self._tour_actuel})

État logique actuel:
- Clauses TweetyProject: {progression['clauses_formulees']}/10
- Requêtes logiques: {progression['requetes_executees']}/5

Cette énigme est IMPOSSIBLE à résoudre sans formalisation complète.
Watson: Continuez à utiliser vos outils TweetyProject massivement!"""
                        
                        await self._group_chat.add_chat_message(
                            ChatMessageContent(role="assistant", content=message_encouragement)
                        )
                
                else:
                    self._logger.warning(f"Aucune réponse reçue au tour {self._tour_actuel}")
                    
            except Exception as e:
                self._logger.error(f"Erreur au tour {self._tour_actuel}: {e}", exc_info=True)
                break
        
        # Résultats finaux
        progression_finale = self._state.verifier_progression_logique()
        etat_final = self._state.obtenir_etat_progression()
        
        self._logger.info("🏁 Énigme terminée.")
        self._logger.info(f"Progression logique finale: {progression_finale}")
        
        return {
            "enigme_resolue": progression_finale["force_logique_formelle"],
            "tours_utilises": self._tour_actuel,
            "progression_logique": progression_finale,
            "etat_final": etat_final,
            "clauses_watson": self._state.clauses_logiques,
            "requetes_executees": self._state.requetes_executees
        }
    
    def obtenir_statistiques_logique(self) -> Dict[str, Any]:
        """Retourne les statistiques d'utilisation de la logique formelle."""
        return {
            "state_id": self._state.workflow_id,
            "progression": self._state.verifier_progression_logique(),
            "clauses_detaillees": self._state.deductions_watson,
            "requetes_detaillees": self._state.requetes_executees,
            "solution_partielle": self._state.solution_partielle
        }