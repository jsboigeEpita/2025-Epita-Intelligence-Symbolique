# argumentation_analysis/agents/core/logic/modal_logic_agent.py
"""
Agent spécialisé pour la logique modale.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from semantic_kernel import Kernel # type: ignore

from ..abc.agent_bases import BaseLogicAgent # Modification de l'import
from .belief_set import BeliefSet, ModalBeliefSet
from .tweety_bridge import TweetyBridge

# Configuration du logger
logger = logging.getLogger(__name__) # Utilisation de __name__

# Prompt Système pour l'agent ML
SYSTEM_PROMPT_ML = """Vous êtes un agent spécialisé dans l'analyse et le raisonnement en logique modale (ML).
Vous utilisez la syntaxe de TweetyProject pour représenter les formules de logique modale.
Vos tâches principales incluent la traduction de texte en formules ML, la génération de requêtes ML pertinentes,
l'exécution de ces requêtes sur un ensemble de croyances ML, et l'interprétation des résultats obtenus,
en tenant compte des notions de nécessité et de possibilité.
"""

# Prompts pour la logique modale
PROMPT_TEXT_TO_MODAL = """
Vous êtes un expert en logique modale. Votre tâche est de traduire un texte en un ensemble de croyances (belief set) en logique modale en utilisant la syntaxe de TweetyProject.

Syntaxe de la logique modale pour TweetyProject:
- Propositions atomiques: lettres minuscules ou mots (ex: p, q, rain)
- Connecteurs logiques: !, ||, &&, =>, <=>
- Opérateurs modaux: []p (nécessité), <>p (possibilité)
  - []p signifie "p est nécessairement vrai" ou "p est vrai dans tous les mondes possibles"
  - <>p signifie "p est possiblement vrai" ou "p est vrai dans au moins un monde possible"

Règles importantes:
1. Chaque formule doit se terminer par un point-virgule (;)
2. Les formules sont séparées par des sauts de ligne
3. Utilisez des noms significatifs pour les propositions
4. Évitez les espaces dans les noms des propositions
5. Les commentaires commencent par // et s'étendent jusqu'à la fin de la ligne
6. Vous pouvez imbriquer les opérateurs modaux: [][]p, []<>p, etc.

Exemple:
```
// Définitions de base
rain => wet;
[]rain;  // Il pleut nécessairement
<>sunny; // Il est possible qu'il fasse soleil
[](rain => wet); // Nécessairement, s'il pleut alors c'est mouillé
<>[]dry; // Il est possible qu'il soit nécessairement sec
```

Traduisez maintenant le texte suivant en un ensemble de croyances en logique modale:

{{$input}}

Répondez uniquement avec l'ensemble de croyances en logique modale, sans explications supplémentaires.
"""

PROMPT_GEN_MODAL_QUERIES = """
Vous êtes un expert en logique modale. Votre tâche est de générer des requêtes pertinentes en logique modale pour interroger un ensemble de croyances (belief set) donné.

Voici le texte source:
{{$input}}

Voici l'ensemble de croyances en logique modale:
{{$belief_set}}

Générez 3 à 5 requêtes pertinentes en logique modale qui permettraient de vérifier des implications importantes ou des conclusions intéressantes à partir de cet ensemble de croyances. Utilisez la même syntaxe que celle de l'ensemble de croyances.

Règles importantes:
1. Les requêtes doivent être des formules bien formées en logique modale
2. Utilisez uniquement des propositions déjà définies dans l'ensemble de croyances
3. Chaque requête doit être sur une ligne séparée
4. N'incluez pas de point-virgule à la fin des requêtes
5. Assurez-vous que les requêtes sont pertinentes par rapport au texte source
6. Utilisez les opérateurs modaux [] (nécessité) et <> (possibilité) de manière appropriée

Répondez uniquement avec les requêtes, sans explications supplémentaires.
"""

PROMPT_INTERPRET_MODAL = """
Vous êtes un expert en logique modale. Votre tâche est d'interpréter les résultats de requêtes en logique modale et d'expliquer leur signification dans le contexte du texte source.

Voici le texte source:
{{$input}}

Voici l'ensemble de croyances en logique modale:
{{$belief_set}}

Voici les requêtes qui ont été exécutées:
{{$queries}}

Voici les résultats de ces requêtes:
{{$tweety_result}}

Interprétez ces résultats et expliquez leur signification dans le contexte du texte source. Pour chaque requête:
1. Expliquez ce que la requête cherchait à vérifier
2. Indiquez si la requête a été acceptée (ACCEPTED) ou rejetée (REJECTED)
3. Expliquez ce que cela signifie dans le contexte du texte source
4. Si pertinent, mentionnez les implications modales de ce résultat (nécessité, possibilité, etc.)

Fournissez ensuite une conclusion générale sur ce que ces résultats nous apprennent sur le texte source, en particulier concernant les notions de nécessité, possibilité, contingence, etc.

Votre réponse doit être claire, précise et accessible à quelqu'un qui n'est pas expert en logique formelle.
"""

class ModalLogicAgent(BaseLogicAgent): # Modification de l'héritage
    """
    Agent spécialisé pour la logique modale.
    
    Cette classe implémente les méthodes abstraites de BaseLogicAgent
    spécifiquement pour la logique modale, en utilisant TweetyProject
    via l'interface TweetyBridge.
    """
    
    def __init__(self, kernel: Kernel):
        """
        Initialise un agent de logique modale.
        
        Args:
            kernel: Le kernel Semantic Kernel à utiliser pour les fonctions sémantiques
        """
        super().__init__(kernel,
                         agent_name="ModalLogicAgent",
                         logic_type_name="ML",
                         system_prompt=SYSTEM_PROMPT_ML)
        # _tweety_bridge sera initialisé dans setup_agent_components

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Décrit ce que l'agent peut faire."""
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent capable d'analyser du texte en utilisant la logique modale (ML). "
                           "Peut convertir du texte en un ensemble de croyances ML, générer des requêtes ML, "
                           "exécuter ces requêtes, et interpréter les résultats en termes de nécessité et possibilité.",
            "methods": {
                "text_to_belief_set": "Convertit un texte en un ensemble de croyances ML.",
                "generate_queries": "Génère des requêtes ML pertinentes à partir d'un texte et d'un ensemble de croyances.",
                "execute_query": "Exécute une requête ML sur un ensemble de croyances.",
                "interpret_results": "Interprète les résultats d'une ou plusieurs requêtes ML.",
                "validate_formula": "Valide la syntaxe d'une formule ML."
            }
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants spécifiques de l'agent dans le kernel SK.
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name}...")

        self._tweety_bridge = TweetyBridge(logic_type="ml") # Initialisation spécifique ML

        if not self.tweety_bridge.is_jvm_ready():
            self.logger.error("Tentative de setup Modal Kernel alors que la JVM n'est PAS démarrée.")
            return
        
        default_settings = None
        if self._llm_service_id:
            try:
                default_settings = self.sk_kernel.get_prompt_execution_settings_from_service_id(
                    self._llm_service_id
                )
                self.logger.debug(f"Settings LLM récupérés pour {self.name}.")
            except Exception as e:
                self.logger.warning(f"Impossible de récupérer settings LLM pour {self.name}: {e}")

        semantic_functions = [
            ("TextToModalBeliefSet", PROMPT_TEXT_TO_MODAL,
             "Traduit texte en Belief Set Modal (syntaxe Tweety pour logique modale)."),
            ("GenerateModalQueries", PROMPT_GEN_MODAL_QUERIES,
             "Génère requêtes modales pertinentes (syntaxe Tweety pour logique modale)."),
            ("InterpretModalResult", PROMPT_INTERPRET_MODAL,
             "Interprète résultat requête modale Tweety formaté.")
        ]

        for func_name, prompt, description in semantic_functions:
            try:
                if not prompt or not isinstance(prompt, str):
                    self.logger.error(f"ERREUR: Prompt invalide pour {self.name}.{func_name}")
                    continue
                
                self.logger.info(f"Ajout fonction {self.name}.{func_name} avec prompt de {len(prompt)} caractères")
                self.sk_kernel.add_function(
                    prompt=prompt,
                    plugin_name=self.name, # Utilisation de self.name
                    function_name=func_name,
                    description=description,
                    prompt_execution_settings=default_settings
                )
                self.logger.debug(f"Fonction sémantique {self.name}.{func_name} ajoutée/mise à jour.")
                
                if self.name in self.sk_kernel.plugins and func_name in self.sk_kernel.plugins[self.name]:
                    self.logger.info(f"✅ Fonction {self.name}.{func_name} correctement enregistrée.")
                else:
                    self.logger.error(f"❌ ERREUR CRITIQUE: Fonction {self.name}.{func_name} non trouvée après ajout!")
            except ValueError as ve:
                self.logger.warning(f"Problème ajout/MàJ {self.name}.{func_name}: {ve}")
            except Exception as e:
                self.logger.error(f"Exception inattendue lors de l'ajout de {self.name}.{func_name}: {e}", exc_info=True)
        
        self.logger.info(f"Composants de {self.name} configurés.")

    def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte en ensemble de croyances modales.
        
        Args:
            text: Le texte à convertir
            
        Returns:
            Un tuple contenant l'ensemble de croyances créé (ou None en cas d'erreur)
            et un message de statut
        """
        self.logger.info(f"Conversion de texte en ensemble de croyances modales pour l'agent {self.name}...")
        
        try:
            # Appeler la fonction sémantique pour convertir le texte
            result = self.sk_kernel.plugins[self.name]["TextToModalBeliefSet"].invoke(self.sk_kernel, input=text)
            belief_set_content = str(result) # Utilisation de str(result)
            
            # Vérifier si le contenu est valide
            if not belief_set_content or len(belief_set_content.strip()) == 0:
                self._logger.error("La conversion a produit un ensemble de croyances vide")
                return None, "La conversion a produit un ensemble de croyances vide"
            
            # Créer l'objet BeliefSet
            belief_set_obj = ModalBeliefSet(belief_set_content)
            
            # Valider l'ensemble de croyances avec TweetyBridge
            is_valid, validation_msg = self.tweety_bridge.validate_modal_belief_set(belief_set_content)
            if not is_valid:
                self.logger.error(f"Ensemble de croyances invalide: {validation_msg}")
                return None, f"Ensemble de croyances invalide: {validation_msg}"
            
            self.logger.info("Conversion réussie")
            return belief_set_obj, "Conversion réussie"
        
        except Exception as e:
            error_msg = f"Erreur lors de la conversion du texte en ensemble de croyances: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    def generate_queries(self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Génère des requêtes logiques modales pertinentes.
        
        Args:
            text: Le texte source
            belief_set: L'ensemble de croyances
            
        Returns:
            Une liste de requêtes logiques
        """
        self.logger.info(f"Génération de requêtes modales pour l'agent {self.name}...")
        
        try:
            # Appeler la fonction sémantique pour générer les requêtes
            result = self.sk_kernel.plugins[self.name]["GenerateModalQueries"].invoke(
                self.sk_kernel,
                input=text,
                belief_set=belief_set.content
            )
            queries_text = str(result)
            
            # Extraire les requêtes individuelles
            queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
            
            # Filtrer les requêtes invalides
            valid_queries = []
            for query_item in queries:
                is_valid, _ = self.tweety_bridge.validate_modal_formula(query_item)
                if is_valid:
                    valid_queries.append(query_item)
                else:
                    self.logger.warning(f"Requête invalide ignorée: {query_item}")
            
            self.logger.info(f"Génération de {len(valid_queries)} requêtes valides")
            return valid_queries
        
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération des requêtes: {str(e)}", exc_info=True)
            return []
    
    def execute_query(self, belief_set: BeliefSet, query: str) -> Tuple[Optional[bool], str]:
        """
        Exécute une requête logique modale sur un ensemble de croyances.
        
        Args:
            belief_set: L'ensemble de croyances
            query: La requête à exécuter
            
        Returns:
            Un tuple contenant le résultat de la requête (True, False ou None si indéterminé)
            et un message formaté
        """
        self.logger.info(f"Exécution de la requête: {query} pour l'agent {self.name}")
        
        try:
            # Utilisation directe de tweety_bridge
            result_str = self.tweety_bridge.execute_modal_query(
                belief_set_content=belief_set.content,
                query_string=query
            )
            
            # Analyser le résultat
            if result_str is None or "ERROR" in result_str.upper():
                self.logger.error(f"Erreur lors de l'exécution de la requête: {result_str}")
                return None, result_str if result_str else "Erreur inconnue de TweetyBridge"
            
            if "ACCEPTED" in result_str:
                return True, result_str
            elif "REJECTED" in result_str:
                return False, result_str
            else:
                self.logger.warning(f"Résultat de requête inattendu: {result_str}")
                return None, result_str
        
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return None, f"FUNC_ERROR: {error_msg}"

    def interpret_results(self, text: str, belief_set: BeliefSet,
                         queries: List[str], results: List[Tuple[Optional[bool], str]],
                         context: Optional[Dict[str, Any]] = None) -> str: # Signature mise à jour
        """
        Interprète les résultats des requêtes logiques modales.
        
        Args:
            text: Le texte source
            belief_set: L'ensemble de croyances
            queries: Les requêtes exécutées
            results: Les résultats des requêtes
            
        Returns:
            Une interprétation textuelle des résultats
        """
        self.logger.info(f"Interprétation des résultats pour l'agent {self.name}...")
        
        try:
            # Préparer les entrées pour la fonction sémantique
            queries_str = "\n".join(queries)
            results_text_list = [res_tuple[1] if res_tuple else "Error: No result" for res_tuple in results]
            results_str = "\n".join(results_text_list)
            
            # Appeler la fonction sémantique pour interpréter les résultats
            result = self.sk_kernel.plugins[self.name]["InterpretModalResult"].invoke(
                self.sk_kernel,
                input=text,
                belief_set=belief_set.content,
                queries=queries_str,
                tweety_result=results_str
            )
            
            interpretation = str(result)
            self.logger.info("Interprétation terminée")
            return interpretation
        
        except Exception as e:
            error_msg = f"Erreur lors de l'interprétation des résultats: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return f"Erreur d'interprétation: {error_msg}"

    def validate_formula(self, formula: str) -> bool:
        """
        Valide la syntaxe d'une formule ML en utilisant TweetyBridge.
        
        Args:
            formula: La formule ML à valider.
            
        Returns:
            True si la formule est valide, False sinon.
        """
        self.logger.debug(f"Validation de la formule ML: {formula}")
        is_valid, message = self.tweety_bridge.validate_modal_formula(formula)
        if not is_valid:
            self.logger.warning(f"Formule ML invalide: {formula}. Message: {message}")
        return is_valid

    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
        """
        Crée un objet ModalBeliefSet à partir des données de l'état.
        
        Args:
            belief_set_data: Les données de l'ensemble de croyances
            
        Returns:
            Un objet ModalBeliefSet
        """
        content = belief_set_data.get("content", "")
        return ModalBeliefSet(content)