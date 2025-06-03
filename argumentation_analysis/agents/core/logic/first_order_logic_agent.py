# argumentation_analysis/agents/core/logic/first_order_logic_agent.py
"""
Agent spécialisé pour la logique du premier ordre (FOL).

Ce module définit `FirstOrderLogicAgent`, une classe qui hérite de
`BaseLogicAgent` et implémente les fonctionnalités spécifiques pour interagir
avec la logique du premier ordre. Il utilise `TweetyBridge` pour la communication
avec TweetyProject et s'appuie sur des prompts sémantiques définis dans ce
module pour la conversion texte-vers-FOL, la génération de requêtes et
l'interprétation des résultats.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple

from semantic_kernel import Kernel # type: ignore

from ..abc.agent_bases import BaseLogicAgent # Modification de l'import
from .belief_set import BeliefSet, FirstOrderBeliefSet
from .tweety_bridge import TweetyBridge

# Configuration du logger
logger = logging.getLogger(__name__) # Utilisation de __name__ pour une meilleure pratique

# Prompt Système pour l'agent FOL
SYSTEM_PROMPT_FOL = """Vous êtes un agent spécialisé dans l'analyse et le raisonnement en logique du premier ordre (FOL).
Vous utilisez la syntaxe de TweetyProject pour représenter les formules FOL.
Vos tâches principales incluent la traduction de texte en formules FOL, la génération de requêtes FOL pertinentes,
l'exécution de ces requêtes sur un ensemble de croyances FOL, et l'interprétation des résultats obtenus.
"""
"""
Prompt système pour l'agent de logique du premier ordre.
Définit le rôle et les capacités générales de l'agent pour le LLM.
"""

# Prompts pour la logique du premier ordre
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
"""
Prompt pour convertir du texte en langage naturel en un ensemble de croyances FOL.
Attend `$input` (le texte source).
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
"""
Prompt pour générer des requêtes FOL pertinentes à partir d'un texte et d'un ensemble de croyances FOL.
Attend `$input` (texte source) et `$belief_set` (l'ensemble de croyances FOL).
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
"""
Prompt pour interpréter les résultats de requêtes FOL en langage naturel.
Attend `$input` (texte source), `$belief_set` (ensemble de croyances FOL),
`$queries` (les requêtes exécutées), et `$tweety_result` (les résultats bruts de Tweety).
"""

class FirstOrderLogicAgent(BaseLogicAgent): 
    """
    Agent spécialisé pour la logique du premier ordre (FOL).

    Cet agent étend `BaseLogicAgent` pour fournir des capacités de traitement
    spécifiques à la logique du premier ordre. Il intègre des fonctions sémantiques
    pour traduire le langage naturel en ensembles de croyances FOL, générer des
    requêtes FOL pertinentes, exécuter ces requêtes via `TweetyBridge`, et
    interpréter les résultats en langage naturel.

    Attributes:
        _tweety_bridge (TweetyBridge): Instance de `TweetyBridge` configurée pour la FOL.
    """
    
    def __init__(self, kernel: Kernel):
        """
        Initialise une instance de `FirstOrderLogicAgent`.

        :param kernel: Le kernel Semantic Kernel à utiliser pour les fonctions sémantiques.
        :type kernel: Kernel
        """
        super().__init__(kernel,
                         agent_name="FirstOrderLogicAgent",
                         logic_type_name="FOL",
                         system_prompt=SYSTEM_PROMPT_FOL)

    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne un dictionnaire décrivant les capacités spécifiques de cet agent FOL.

        :return: Un dictionnaire détaillant le nom, le type de logique, la description
                 et les méthodes de l'agent.
        :rtype: Dict[str, Any]
        """
        return {
            "name": self.name,
            "logic_type": self.logic_type,
            "description": "Agent capable d'analyser du texte en utilisant la logique du premier ordre (FOL). "
                           "Peut convertir du texte en un ensemble de croyances FOL, générer des requêtes FOL, "
                           "exécuter ces requêtes, et interpréter les résultats.",
            "methods": {
                "text_to_belief_set": "Convertit un texte en un ensemble de croyances FOL.",
                "generate_queries": "Génère des requêtes FOL pertinentes à partir d'un texte et d'un ensemble de croyances.",
                "execute_query": "Exécute une requête FOL sur un ensemble de croyances.",
                "interpret_results": "Interprète les résultats d'une ou plusieurs requêtes FOL.",
                "validate_formula": "Valide la syntaxe d'une formule FOL."
            }
        }

    def setup_agent_components(self, llm_service_id: str) -> None:
        """
        Configure les composants spécifiques de l'agent de logique du premier ordre.

        Initialise `TweetyBridge` pour la logique FOL et enregistre les fonctions
        sémantiques nécessaires (TextToFOLBeliefSet, GenerateFOLQueries,
        InterpretFOLResult) dans le kernel Semantic Kernel.

        :param llm_service_id: L'ID du service LLM à utiliser pour les fonctions sémantiques.
        :type llm_service_id: str
        """
        super().setup_agent_components(llm_service_id)
        self.logger.info(f"Configuration des composants pour {self.name}...")

        self._tweety_bridge = TweetyBridge(logic_type="fol") 

        if not self.tweety_bridge.is_jvm_ready():
            self.logger.error("Tentative de setup FOL Kernel alors que la JVM n'est PAS démarrée.")
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
            ("TextToFOLBeliefSet", PROMPT_TEXT_TO_FOL,
             "Traduit texte en Belief Set FOL (syntaxe Tweety pour logique du premier ordre)."),
            ("GenerateFOLQueries", PROMPT_GEN_FOL_QUERIES,
             "Génère requêtes FOL pertinentes (syntaxe Tweety pour logique du premier ordre)."),
            ("InterpretFOLResult", PROMPT_INTERPRET_FOL,
             "Interprète résultat requête FOL Tweety formaté.")
        ]

        for func_name, prompt, description in semantic_functions:
            try:
                if not prompt or not isinstance(prompt, str):
                    self.logger.error(f"ERREUR: Prompt invalide pour {self.name}.{func_name}")
                    continue
                
                self.logger.info(f"Ajout fonction {self.name}.{func_name} avec prompt de {len(prompt)} caractères")
                self.sk_kernel.add_function(
                    prompt=prompt,
                    plugin_name=self.name, 
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

    async def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]:
        """
        Convertit un texte en langage naturel en un ensemble de croyances FOL.

        Utilise la fonction sémantique "TextToFOLBeliefSet" pour la conversion,
        puis valide l'ensemble de croyances généré avec `TweetyBridge`.

        :param text: Le texte en langage naturel à convertir.
        :type text: str
        :param context: Un dictionnaire optionnel de contexte (non utilisé actuellement).
        :type context: Optional[Dict[str, Any]]
        :return: Un tuple contenant l'objet `FirstOrderBeliefSet` si la conversion
                 et la validation réussissent, et un message de statut.
                 Retourne (None, message_erreur) en cas d'échec.
        :rtype: Tuple[Optional[BeliefSet], str]
        """
        self.logger.info(f"Conversion de texte en ensemble de croyances du premier ordre pour l'agent {self.name}...")
        
        try:
            result = await self.sk_kernel.plugins[self.name]["TextToFOLBeliefSet"].invoke(self.sk_kernel, input=text)
            belief_set_content = str(result)
            
            if not belief_set_content or len(belief_set_content.strip()) == 0:
                self._logger.error("La conversion a produit un ensemble de croyances vide")
                return None, "La conversion a produit un ensemble de croyances vide"
            
            belief_set_obj = FirstOrderBeliefSet(belief_set_content) 
            
            is_valid, validation_msg = self.tweety_bridge.validate_fol_belief_set(belief_set_content)
            if not is_valid:
                self.logger.error(f"Ensemble de croyances invalide: {validation_msg}")
                return None, f"Ensemble de croyances invalide: {validation_msg}"
            
            self.logger.info("Conversion réussie")
            return belief_set_obj, "Conversion réussie"
        
        except Exception as e:
            error_msg = f"Erreur lors de la conversion du texte en ensemble de croyances: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    async def generate_queries(self, text: str, belief_set: BeliefSet, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Génère des requêtes logiques du premier ordre (FOL) pertinentes à partir d'un texte et d'un ensemble de croyances.

        Utilise la fonction sémantique "GenerateFOLQueries". Les requêtes générées
        sont ensuite validées syntaxiquement.

        :param text: Le texte en langage naturel source.
        :type text: str
        :param belief_set: L'ensemble de croyances FOL associé.
        :type belief_set: BeliefSet
        :param context: Un dictionnaire optionnel de contexte (non utilisé actuellement).
        :type context: Optional[Dict[str, Any]]
        :return: Une liste de chaînes de caractères, chacune étant une requête FOL valide.
                 Retourne une liste vide en cas d'erreur.
        :rtype: List[str]
        """
        self.logger.info(f"Génération de requêtes du premier ordre pour l'agent {self.name}...")
        
        try:
            result = await self.sk_kernel.plugins[self.name]["GenerateFOLQueries"].invoke(
                self.sk_kernel,
                input=text,
                belief_set=belief_set.content # Utiliser .content
            )
            queries_text = str(result)
            
            queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
            
            valid_queries = []
            for query_item in queries: 
                is_valid, _ = self.tweety_bridge.validate_fol_formula(query_item)
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
        Exécute une requête logique du premier ordre (FOL) sur un ensemble de croyances donné.

        Utilise `TweetyBridge` pour exécuter la requête contre le contenu de `belief_set`.
        Interprète la chaîne de résultat de `TweetyBridge` pour déterminer si la requête
        est acceptée, rejetée ou si une erreur s'est produite.

        :param belief_set: L'ensemble de croyances FOL sur lequel exécuter la requête.
        :type belief_set: BeliefSet
        :param query: La requête FOL à exécuter.
        :type query: str
        :return: Un tuple contenant le résultat booléen de la requête (`True` si acceptée,
                 `False` si rejetée, `None` si indéterminé ou erreur) et la chaîne de
                 résultat brute de `TweetyBridge` (ou un message d'erreur).
        :rtype: Tuple[Optional[bool], str]
        """
        self.logger.info(f"Exécution de la requête: {query} pour l'agent {self.name}")
        
        try:
            bs_str = belief_set.content # Utiliser .content
            
            result_str = self.tweety_bridge.execute_fol_query(
                belief_set_content=bs_str,
                query_string=query
            )
            
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

    async def interpret_results(self, text: str, belief_set: BeliefSet,
                         queries: List[str], results: List[Tuple[Optional[bool], str]],
                         context: Optional[Dict[str, Any]] = None) -> str:
        """
        Interprète les résultats d'une série de requêtes FOL en langage naturel.

        Utilise la fonction sémantique "InterpretFOLResult" pour générer une explication
        basée sur le texte original, l'ensemble de croyances, les requêtes posées et
        les résultats obtenus de Tweety.

        :param text: Le texte original en langage naturel.
        :type text: str
        :param belief_set: L'ensemble de croyances FOL utilisé.
        :type belief_set: BeliefSet
        :param queries: La liste des requêtes FOL qui ont été exécutées.
        :type queries: List[str]
        :param results: La liste des résultats (tuples booléen/None, message_brut)
                        correspondant à chaque requête.
        :type results: List[Tuple[Optional[bool], str]]
        :param context: Un dictionnaire optionnel de contexte (non utilisé actuellement).
        :type context: Optional[Dict[str, Any]]
        :return: Une chaîne de caractères contenant l'interprétation en langage naturel
                 des résultats, ou un message d'erreur.
        :rtype: str
        """
        self.logger.info(f"Interprétation des résultats pour l'agent {self.name}...")
        
        try:
            queries_str = "\n".join(queries)
            results_text_list = [res_tuple[1] if res_tuple else "Error: No result" for res_tuple in results]
            results_str = "\n".join(results_text_list)
            
            result = await self.sk_kernel.plugins[self.name]["InterpretFOLResult"].invoke(
                self.sk_kernel,
                input=text,
                belief_set=belief_set.content, # Utiliser .content
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
        Valide la syntaxe d'une formule de logique du premier ordre (FOL).

        Utilise la méthode `validate_fol_formula` de `TweetyBridge`.

        :param formula: La formule FOL à valider.
        :type formula: str
        :return: `True` si la formule est syntaxiquement valide, `False` sinon.
        :rtype: bool
        """
        self.logger.debug(f"Validation de la formule FOL: {formula}")
        is_valid, message = self.tweety_bridge.validate_fol_formula(formula)
        if not is_valid:
            self.logger.warning(f"Formule FOL invalide: {formula}. Message: {message}")
        return is_valid

    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
        """
        Crée un objet `FirstOrderBeliefSet` à partir d'un dictionnaire de données.

        Principalement utilisé pour reconstituer un `BeliefSet` à partir d'un état sauvegardé.

        :param belief_set_data: Un dictionnaire contenant au moins la clé "content"
                                avec la représentation textuelle de l'ensemble de croyances.
        :type belief_set_data: Dict[str, Any]
        :return: Une instance de `FirstOrderBeliefSet`.
        :rtype: BeliefSet
        """
        content = belief_set_data.get("content", "")
        return FirstOrderBeliefSet(content)