# argumentation_analysis/agents/core/logic/propositional_logic_agent.py
"""
Agent spécialisé pour la logique propositionnelle.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from semantic_kernel import Kernel

from .abstract_logic_agent import AbstractLogicAgent
from .belief_set import BeliefSet, PropositionalBeliefSet
from .tweety_bridge import TweetyBridge

# Importer les prompts depuis le module pl existant
from ..pl.prompts import (
    prompt_text_to_pl_v8 as PROMPT_TEXT_TO_PL,
    prompt_gen_pl_queries_v8 as PROMPT_GEN_PL_QUERIES,
    prompt_interpret_pl_v8 as PROMPT_INTERPRET_PL
)

# Configuration du logger
logger = logging.getLogger("Orchestration.PropositionalLogicAgent")

class PropositionalLogicAgent(AbstractLogicAgent):
    """
    Agent spécialisé pour la logique propositionnelle.
    
    Cette classe implémente les méthodes abstraites de AbstractLogicAgent
    spécifiquement pour la logique propositionnelle, en utilisant TweetyProject
    via l'interface TweetyBridge.
    """
    
    def __init__(self, kernel: Kernel):
        """
        Initialise un agent de logique propositionnelle.
        
        Args:
            kernel: Le kernel Semantic Kernel à utiliser pour les fonctions sémantiques
        """
        super().__init__(kernel, "PropositionalLogicAgent")
        self._tweety_bridge = TweetyBridge()
        self._plugin_name = "PLAnalyzer"
    
    def setup_kernel(self, llm_service) -> None:
        """
        Configure le kernel avec les plugins et fonctions nécessaires.
        
        Args:
            llm_service: Le service LLM à utiliser
        """
        self._logger.info(f"Configuration du kernel pour {self._plugin_name}...")
        
        # Vérifier si la JVM est prête
        if not self._tweety_bridge.is_jvm_ready():
            self._logger.error("Tentative de setup PL Kernel alors que la JVM n'est PAS démarrée.")
            return
        
        # Ajouter le plugin TweetyBridge au kernel
        if self._plugin_name in self.kernel.plugins:
            self._logger.warning(f"Plugin '{self._plugin_name}' déjà présent. Remplacement.")
        
        self.kernel.add_plugin(self._tweety_bridge, plugin_name=self._plugin_name)
        self._logger.debug(f"Instance du plugin '{self._plugin_name}' ajoutée/mise à jour.")
        
        # Configuration des settings LLM
        default_settings = None
        if llm_service:
            try:
                default_settings = self.kernel.get_prompt_execution_settings_from_service_id(
                    llm_service.service_id
                )
                self._logger.debug(f"Settings LLM récupérés pour {self._plugin_name}.")
            except Exception as e:
                self._logger.warning(f"Impossible de récupérer settings LLM pour {self._plugin_name}: {e}")
        
        # Ajout des fonctions sémantiques au kernel
        semantic_functions = [
            ("semantic_TextToPLBeliefSet", PROMPT_TEXT_TO_PL, 
             "Traduit texte en Belief Set PL (syntaxe Tweety ! || => <=> ^^)."),
            ("semantic_GeneratePLQueries", PROMPT_GEN_PL_QUERIES, 
             "Génère requêtes PL pertinentes (syntaxe Tweety ! || => <=> ^^)."),
            ("semantic_InterpretPLResult", PROMPT_INTERPRET_PL, 
             "Interprète résultat requête PL Tweety formaté.")
        ]
        
        for func_name, prompt, description in semantic_functions:
            try:
                # Vérifier si le prompt est valide
                if not prompt or not isinstance(prompt, str):
                    self._logger.error(f"ERREUR: Prompt invalide pour {self._plugin_name}.{func_name}")
                    continue
                    
                # Ajouter la fonction avec des logs détaillés
                self._logger.info(f"Ajout fonction {self._plugin_name}.{func_name} avec prompt de {len(prompt)} caractères")
                self.kernel.add_function(
                    prompt=prompt,
                    plugin_name=self._plugin_name,
                    function_name=func_name,
                    description=description,
                    prompt_execution_settings=default_settings
                )
                self._logger.debug(f"Fonction sémantique {self._plugin_name}.{func_name} ajoutée/mise à jour.")
                
                # Vérifier que la fonction a été correctement ajoutée
                if self._plugin_name in self.kernel.plugins and func_name in self.kernel.plugins[self._plugin_name]:
                    self._logger.info(f"✅ Fonction {self._plugin_name}.{func_name} correctement enregistrée.")
                else:
                    self._logger.error(f"❌ ERREUR CRITIQUE: Fonction {self._plugin_name}.{func_name} non trouvée après ajout!")
            except ValueError as ve:
                self._logger.warning(f"Problème ajout/MàJ {self._plugin_name}.{func_name}: {ve}")
                self._logger.error(f"Détails de l'erreur: {str(ve)}")
            except Exception as e:
                self._logger.error(f"Exception inattendue lors de l'ajout de {self._plugin_name}.{func_name}: {e}", exc_info=True)
        
        # Vérification de la fonction native
        native_facade = "execute_pl_query"
        if self._plugin_name in self.kernel.plugins:
            if native_facade not in self.kernel.plugins[self._plugin_name]:
                self._logger.error(f"ERREUR CRITIQUE: Fonction native {self._plugin_name}.{native_facade} non enregistrée!")
            else:
                self._logger.debug(f"Fonction native {self._plugin_name}.{native_facade} trouvée.")
        else:
            self._logger.error(f"ERREUR CRITIQUE: Plugin {self._plugin_name} non trouvé après ajout!")
        
        self._logger.info(f"Kernel {self._plugin_name} configuré.")
    
    def text_to_belief_set(self, text: str) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte en ensemble de croyances propositionnelles.
        
        Args:
            text: Le texte à convertir
            
        Returns:
            Un tuple contenant l'ensemble de croyances créé (ou None en cas d'erreur)
            et un message de statut
        """
        self._logger.info(f"Conversion de texte en ensemble de croyances propositionnelles...")
        
        try:
            # Appeler la fonction sémantique pour convertir le texte
            result = self.kernel.plugins[self._plugin_name]["semantic_TextToPLBeliefSet"].invoke(text)
            belief_set_content = result.result
            
            # Vérifier si le contenu est valide
            if not belief_set_content or len(belief_set_content.strip()) == 0:
                self._logger.error("La conversion a produit un ensemble de croyances vide")
                return None, "La conversion a produit un ensemble de croyances vide"
            
            # Créer l'objet BeliefSet
            belief_set = PropositionalBeliefSet(belief_set_content)
            
            # Valider l'ensemble de croyances avec TweetyBridge
            is_valid, validation_msg = self._tweety_bridge.validate_belief_set(belief_set_content)
            if not is_valid:
                self._logger.error(f"Ensemble de croyances invalide: {validation_msg}")
                return None, f"Ensemble de croyances invalide: {validation_msg}"
            
            self._logger.info("Conversion réussie")
            return belief_set, "Conversion réussie"
        
        except Exception as e:
            error_msg = f"Erreur lors de la conversion du texte en ensemble de croyances: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    def generate_queries(self, text: str, belief_set: BeliefSet) -> List[str]:
        """
        Génère des requêtes logiques propositionnelles pertinentes.
        
        Args:
            text: Le texte source
            belief_set: L'ensemble de croyances
            
        Returns:
            Une liste de requêtes logiques
        """
        self._logger.info("Génération de requêtes propositionnelles...")
        
        try:
            # Appeler la fonction sémantique pour générer les requêtes
            result = self.kernel.plugins[self._plugin_name]["semantic_GeneratePLQueries"].invoke(
                input=text,
                belief_set=belief_set.content
            )
            queries_text = result.result
            
            # Extraire les requêtes individuelles
            queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
            
            # Filtrer les requêtes invalides
            valid_queries = []
            for query in queries:
                is_valid, _ = self._tweety_bridge.validate_formula(query)
                if is_valid:
                    valid_queries.append(query)
                else:
                    self._logger.warning(f"Requête invalide ignorée: {query}")
            
            self._logger.info(f"Génération de {len(valid_queries)} requêtes valides")
            return valid_queries
        
        except Exception as e:
            self._logger.error(f"Erreur lors de la génération des requêtes: {str(e)}", exc_info=True)
            return []
    
    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête logique propositionnelle sur un ensemble de croyances.
        
        Args:
            belief_set: L'ensemble de croyances
            query: La requête à exécuter
            
        Returns:
            Un tuple contenant le résultat de la requête (True, False ou None si indéterminé)
            et un message formaté
        """
        self._logger.info(f"Exécution de la requête: {query}")
        
        try:
            # Appeler la fonction native pour exécuter la requête
            result_str = self.kernel.plugins[self._plugin_name]["execute_pl_query"].invoke(
                belief_set_content=belief_set.content,
                query_string=query
            ).result
            
            # Analyser le résultat
            if "FUNC_ERROR" in result_str:
                self._logger.error(f"Erreur lors de l'exécution de la requête: {result_str}")
                return None, result_str
            
            if "ACCEPTED" in result_str:
                return True, result_str
            elif "REJECTED" in result_str:
                return False, result_str
            else:
                return None, result_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"
    
    def interpret_results(self, text: str, belief_set: BeliefSet, 
                         queries: List[str], results: List[str]) -> str:
        """
        Interprète les résultats des requêtes logiques propositionnelles.
        
        Args:
            text: Le texte source
            belief_set: L'ensemble de croyances
            queries: Les requêtes exécutées
            results: Les résultats des requêtes
            
        Returns:
            Une interprétation textuelle des résultats
        """
        self._logger.info("Interprétation des résultats...")
        
        try:
            # Préparer les entrées pour la fonction sémantique
            queries_str = "\n".join(queries)
            results_str = "\n".join(results)
            
            # Appeler la fonction sémantique pour interpréter les résultats
            result = self.kernel.plugins[self._plugin_name]["semantic_InterpretPLResult"].invoke(
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_str
            )
            
            interpretation = result.result
            self._logger.info("Interprétation terminée")
            return interpretation
        
        except Exception as e:
            error_msg = f"Erreur lors de l'interprétation des résultats: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return f"Erreur d'interprétation: {error_msg}"
    
    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
        """
        Crée un objet PropositionalBeliefSet à partir des données de l'état.
        
        Args:
            belief_set_data: Les données de l'ensemble de croyances
            
        Returns:
            Un objet PropositionalBeliefSet
        """
        content = belief_set_data.get("content", "")
        return PropositionalBeliefSet(content)