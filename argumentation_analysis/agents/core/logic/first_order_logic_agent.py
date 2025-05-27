# argumentation_analysis/agents/core/logic/first_order_logic_agent.py
"""
Agent spécialisé pour la logique du premier ordre.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from semantic_kernel import Kernel

from .abstract_logic_agent import AbstractLogicAgent
from .belief_set import BeliefSet, FirstOrderBeliefSet
from .tweety_bridge import TweetyBridge

# Configuration du logger
logger = logging.getLogger("Orchestration.FirstOrderLogicAgent")

# Prompts pour la logique du premier ordre (à définir ultérieurement)
PROMPT_TEXT_TO_FOL = """
Vous êtes un expert en logique du premier ordre. Votre tâche est de traduire un texte en un ensemble de croyances (belief set) en logique du premier ordre en utilisant la syntaxe de TweetyProject.

Syntaxe de la logique du premier ordre pour TweetyProject:
- Prédicats: commencent par une lettre majuscule (ex: P(x), Human(john))
- Variables: commencent par une lettre minuscule (ex: x, y, person)
- Constantes: commencent par une lettre minuscule (ex: john, paris)
- Connecteurs logiques: !, ||, &&, =>, <=>
- Quantificateurs: forall x: (formule), exists x: (formule)

Règles importantes:
1. Chaque formule doit se terminer par un point-virgule (;)
2. Les formules sont séparées par des sauts de ligne
3. Utilisez des noms significatifs pour les prédicats, variables et constantes
4. Évitez les espaces dans les noms des prédicats, variables et constantes
5. Les commentaires commencent par // et s'étendent jusqu'à la fin de la ligne

Exemple:
```
// Définitions de base
Human(john);
Human(mary);
forall x: (Human(x) => Mortal(x));
Loves(john, mary);
exists x: (Human(x) && Loves(x, john));
```

Traduisez maintenant le texte suivant en un ensemble de croyances en logique du premier ordre:

{{$input}}

Répondez uniquement avec l'ensemble de croyances en logique du premier ordre, sans explications supplémentaires.
"""

PROMPT_GEN_FOL_QUERIES = """
Vous êtes un expert en logique du premier ordre. Votre tâche est de générer des requêtes pertinentes en logique du premier ordre pour interroger un ensemble de croyances (belief set) donné.

Voici le texte source:
{{$input}}

Voici l'ensemble de croyances en logique du premier ordre:
{{$belief_set}}

Générez 3 à 5 requêtes pertinentes en logique du premier ordre qui permettraient de vérifier des implications importantes ou des conclusions intéressantes à partir de cet ensemble de croyances. Utilisez la même syntaxe que celle de l'ensemble de croyances.

Règles importantes:
1. Les requêtes doivent être des formules bien formées en logique du premier ordre
2. Utilisez uniquement des prédicats, constantes et variables déjà définis dans l'ensemble de croyances
3. Chaque requête doit être sur une ligne séparée
4. N'incluez pas de point-virgule à la fin des requêtes
5. Assurez-vous que les requêtes sont pertinentes par rapport au texte source

Répondez uniquement avec les requêtes, sans explications supplémentaires.
"""

PROMPT_INTERPRET_FOL = """
Vous êtes un expert en logique du premier ordre. Votre tâche est d'interpréter les résultats de requêtes en logique du premier ordre et d'expliquer leur signification dans le contexte du texte source.

Voici le texte source:
{{$input}}

Voici l'ensemble de croyances en logique du premier ordre:
{{$belief_set}}

Voici les requêtes qui ont été exécutées:
{{$queries}}

Voici les résultats de ces requêtes:
{{$tweety_result}}

Interprétez ces résultats et expliquez leur signification dans le contexte du texte source. Pour chaque requête:
1. Expliquez ce que la requête cherchait à vérifier
2. Indiquez si la requête a été acceptée (ACCEPTED) ou rejetée (REJECTED)
3. Expliquez ce que cela signifie dans le contexte du texte source
4. Si pertinent, mentionnez les implications logiques de ce résultat

Fournissez ensuite une conclusion générale sur ce que ces résultats nous apprennent sur le texte source.

Votre réponse doit être claire, précise et accessible à quelqu'un qui n'est pas expert en logique formelle.
"""

class FirstOrderLogicAgent(AbstractLogicAgent):
    """
    Agent spécialisé pour la logique du premier ordre.
    
    Cette classe implémente les méthodes abstraites de AbstractLogicAgent
    spécifiquement pour la logique du premier ordre, en utilisant TweetyProject
    via l'interface TweetyBridge.
    """
    
    def __init__(self, kernel: Kernel):
        """
        Initialise un agent de logique du premier ordre.
        
        Args:
            kernel: Le kernel Semantic Kernel à utiliser pour les fonctions sémantiques
        """
        super().__init__(kernel, "FirstOrderLogicAgent")
        self._tweety_bridge = TweetyBridge()
        self._plugin_name = "FOLAnalyzer"
    
    def setup_kernel(self, llm_service) -> None:
        """
        Configure le kernel avec les plugins et fonctions nécessaires.
        
        Args:
            llm_service: Le service LLM à utiliser
        """
        self._logger.info(f"Configuration du kernel pour {self._plugin_name}...")
        
        # Vérifier si la JVM est prête
        if not self._tweety_bridge.is_jvm_ready():
            self._logger.error("Tentative de setup FOL Kernel alors que la JVM n'est PAS démarrée.")
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
            ("semantic_TextToFOLBeliefSet", PROMPT_TEXT_TO_FOL, 
             "Traduit texte en Belief Set FOL (syntaxe Tweety pour logique du premier ordre)."),
            ("semantic_GenerateFOLQueries", PROMPT_GEN_FOL_QUERIES, 
             "Génère requêtes FOL pertinentes (syntaxe Tweety pour logique du premier ordre)."),
            ("semantic_InterpretFOLResult", PROMPT_INTERPRET_FOL, 
             "Interprète résultat requête FOL Tweety formaté.")
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
        native_facade = "execute_fol_query"
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
        Convertit un texte en ensemble de croyances du premier ordre.
        
        Args:
            text: Le texte à convertir
            
        Returns:
            Un tuple contenant l'ensemble de croyances créé (ou None en cas d'erreur)
            et un message de statut
        """
        self._logger.info(f"Conversion de texte en ensemble de croyances du premier ordre...")
        
        try:
            # Appeler la fonction sémantique pour convertir le texte
            result = self.kernel.plugins[self._plugin_name]["semantic_TextToFOLBeliefSet"].invoke(text)
            belief_set_content = result.result
            
            # Vérifier si le contenu est valide
            if not belief_set_content or len(belief_set_content.strip()) == 0:
                self._logger.error("La conversion a produit un ensemble de croyances vide")
                return None, "La conversion a produit un ensemble de croyances vide"
            
            # Créer l'objet BeliefSet
            belief_set = FirstOrderBeliefSet(belief_set_content)
            
            # Valider l'ensemble de croyances avec TweetyBridge
            is_valid, validation_msg = self._tweety_bridge.validate_fol_belief_set(belief_set_content)
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
        Génère des requêtes logiques du premier ordre pertinentes.
        
        Args:
            text: Le texte source
            belief_set: L'ensemble de croyances
            
        Returns:
            Une liste de requêtes logiques
        """
        self._logger.info("Génération de requêtes du premier ordre...")
        
        try:
            # Appeler la fonction sémantique pour générer les requêtes
            result = self.kernel.plugins[self._plugin_name]["semantic_GenerateFOLQueries"].invoke(
                input=text,
                belief_set=belief_set.content
            )
            queries_text = result.result
            
            # Extraire les requêtes individuelles
            queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
            
            # Filtrer les requêtes invalides
            valid_queries = []
            for query in queries:
                is_valid, _ = self._tweety_bridge.validate_fol_formula(query)
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
        Exécute une requête logique du premier ordre sur un ensemble de croyances.
        
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
            result_str = self.kernel.plugins[self._plugin_name]["execute_fol_query"].invoke(
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
        Interprète les résultats des requêtes logiques du premier ordre.
        
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
            result = self.kernel.plugins[self._plugin_name]["semantic_InterpretFOLResult"].invoke(
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
        Crée un objet FirstOrderBeliefSet à partir des données de l'état.
        
        Args:
            belief_set_data: Les données de l'ensemble de croyances
            
        Returns:
            Un objet FirstOrderBeliefSet
        """
        content = belief_set_data.get("content", "")
        return FirstOrderBeliefSet(content)