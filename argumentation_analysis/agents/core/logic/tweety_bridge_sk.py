# argumentation_analysis/agents/core/logic/tweety_bridge_sk.py
"""
Extension de TweetyBridge avec support pour le mécanisme SK Retry.

Ce module étend TweetyBridge pour supporter le VRAI mécanisme de retry Semantic Kernel
où les erreurs sont retournées comme résultats JSON au lieu d'exceptions.
"""

import logging
import json
from typing import Tuple, Optional, Any, Dict, List

from .tweety_bridge import TweetyBridge

# Configuration du logger
logger = logging.getLogger("Orchestration.TweetyBridgeSK")


class TweetyBridgeSK(TweetyBridge):
    """
    Extension de TweetyBridge avec support pour les erreurs comme résultats JSON.

    Cette classe étend TweetyBridge pour implémenter le vrai mécanisme de retry
    Semantic Kernel où les erreurs ne sont pas levées comme exceptions mais
    retournées comme résultats JSON que l'agent peut analyser et corriger.
    """

    def __init__(self):
        """Initialise TweetyBridgeSK avec les capacités SK retry."""
        super().__init__()
        self._logger = logger
        self._logger.info("TWEETY_BRIDGE_SK: Initialisation avec support SK retry")

    def text_to_modal_belief_set(self, text: str) -> str:
        """
        Fonction SK : Convertit texte en belief set modal avec erreurs comme résultats JSON.

        :param text: Texte à convertir
        :return: JSON avec succès ou erreur
        """
        self._logger.info(f"[SK] text_to_modal_belief_set: '{text[:50]}...'")

        try:
            # Tentative de conversion (version simplifiée pour démo)
            belief_set_content = self._convert_text_to_modal_internal(text)

            # Validation avec TweetyProject
            is_valid, validation_msg = self.validate_modal_belief_set(
                belief_set_content
            )

            if not is_valid:
                # Retourner l'erreur comme résultat (pas exception)
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Validation TweetyProject échouée: {validation_msg}",
                        "bnf": self._get_modal_bnf(),
                        "suggestion": "Corrigez la syntaxe selon la BNF TweetyProject",
                        "problematic_input": text[:100],
                    }
                )

            # Succès
            return json.dumps(
                {
                    "success": True,
                    "result": belief_set_content,
                    "message": "Conversion et validation réussies",
                }
            )

        except Exception as e:
            # Convertir l'exception en résultat JSON
            error_msg = str(e)

            # Enrichir l'erreur selon le type
            if "has not been declared" in error_msg:
                suggestion = "Déclarez toutes les constantes avec 'constant nom_constant' avant utilisation"
            elif "parsing" in error_msg.lower():
                suggestion = "Vérifiez la syntaxe selon la BNF TweetyProject"
            else:
                suggestion = "Utilisez des termes neutres et évitez les mots sensibles"

            return json.dumps(
                {
                    "success": False,
                    "error": error_msg,
                    "bnf": self._get_modal_bnf(),
                    "suggestion": suggestion,
                    "problematic_input": text[:100],
                    "error_type": "conversion_error",
                }
            )

    def _convert_text_to_modal_internal(self, text: str) -> str:
        """
        Conversion interne qui peut lever des exceptions.

        Cette méthode simule le processus de conversion et peut lever des exceptions
        typiques de TweetyProject pour démontrer le mécanisme SK.
        """
        # Détecter les termes problématiques
        problematic_terms = {
            "annihilation": "cessation",
            "aryan": "groupe_specifique",
            "race": "population",
            "kill": "arreter",
            "destroy": "transformer",
            "war": "conflit",
            "death": "fin",
        }

        text_lower = text.lower()

        # Simuler les erreurs typiques de TweetyProject
        for problematic, replacement in problematic_terms.items():
            if problematic in text_lower:
                # Simuler l'erreur exacte de TweetyProject
                raise ValueError(
                    f"Error parsing Modal Logic formula 'constant {problematic}' for logic 'S4': Predicate 'constant{problematic}' has not been declared."
                )

        # Conversion réussie - version simplifiée
        # Dans un vrai système, ceci utiliserait NLP pour extraire les concepts
        safe_propositions = [
            "urgent_action",
            "world_peace",
            "climate_change",
            "cooperation",
        ]

        belief_set_lines = []

        # Déclarations des constantes
        for prop in safe_propositions:
            belief_set_lines.append(f"constant {prop}")

        belief_set_lines.append("")  # Ligne vide

        # Déclarations des propositions
        for prop in safe_propositions:
            belief_set_lines.append(f"prop({prop})")

        belief_set_lines.append("")  # Ligne vide

        # Formules modales basées sur le texte
        if "necessary" in text_lower or "must" in text_lower:
            belief_set_lines.append("[]urgent_action")

        if "possible" in text_lower or "can" in text_lower:
            belief_set_lines.append("<>world_peace")

        if "peace" in text_lower:
            belief_set_lines.append("urgent_action => <>world_peace")

        return "\n".join(belief_set_lines)

    def generate_modal_queries(self, text: str, belief_set: str) -> str:
        """
        Fonction SK : Génère des requêtes modales avec erreurs comme résultats JSON.
        """
        self._logger.info(
            f"[SK] generate_modal_queries pour belief set de {len(belief_set)} caractères"
        )

        try:
            queries = self._generate_queries_internal(text, belief_set)

            # Validation des requêtes générées
            valid_queries = []
            invalid_queries = []

            for query in queries:
                is_valid, msg = self.validate_modal_formula(query)
                if is_valid:
                    valid_queries.append(query)
                else:
                    invalid_queries.append({"query": query, "error": msg})

            if not valid_queries and invalid_queries:
                # Toutes les requêtes sont invalides
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Toutes les requêtes générées sont invalides: {invalid_queries[0]['error']}",
                        "bnf": self._get_modal_bnf(),
                        "suggestion": "Générez des requêtes avec la syntaxe correcte TweetyProject",
                        "invalid_queries": invalid_queries,
                    }
                )

            # Succès (même partiel)
            result = {
                "success": True,
                "query_ideas": [{"formula": q} for q in valid_queries],
                "message": f"{len(valid_queries)} requêtes valides générées",
            }

            if invalid_queries:
                result["warnings"] = (
                    f"{len(invalid_queries)} requêtes invalides ignorées"
                )
                result["invalid_queries"] = invalid_queries

            return json.dumps(result)

        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Erreur génération requêtes: {str(e)}",
                    "bnf": self._get_modal_bnf(),
                    "suggestion": "Vérifiez la syntaxe du belief set et des requêtes",
                }
            )

    def _generate_queries_internal(self, text: str, belief_set: str) -> List[str]:
        """
        Génération interne des requêtes (peut lever des exceptions).
        """
        # Extraire les propositions du belief set
        propositions = []
        lines = belief_set.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("prop(") and line.endswith(")"):
                prop = line[5:-1]  # Extraire nom entre prop( et )
                propositions.append(prop)

        if not propositions:
            raise ValueError("Aucune proposition trouvée dans le belief set")

        # Générer des requêtes modales basiques
        queries = []

        # Requêtes de nécessité
        for prop in propositions[:2]:  # Limiter pour démo
            queries.append(f"[]{prop}")

        # Requêtes de possibilité
        for prop in propositions[:2]:
            queries.append(f"<>{prop}")

        # Requêtes d'implication
        if len(propositions) >= 2:
            queries.append(f"{propositions[0]} => <>{propositions[1]}")

        return queries

    def execute_modal_query_sk(self, belief_set_content: str, query_string: str) -> str:
        """
        Fonction SK : Exécute une requête modale avec erreurs comme résultats JSON.
        """
        self._logger.info(f"[SK] execute_modal_query_sk: '{query_string}'")

        try:
            # Utiliser la méthode parent mais capturer les erreurs
            result_str = self.execute_modal_query(belief_set_content, query_string)

            # Si c'est déjà au format FUNC_ERROR, convertir en JSON
            if result_str.startswith("FUNC_ERROR:"):
                error_msg = result_str[11:]  # Enlever "FUNC_ERROR:"
                return json.dumps(
                    {
                        "success": False,
                        "error": error_msg,
                        "bnf": self._get_modal_bnf(),
                        "suggestion": "Corrigez la syntaxe de la requête",
                    }
                )

            # Succès - convertir le résultat en JSON structuré
            if "ACCEPTED" in result_str:
                result = True
                status = "ACCEPTED"
            elif "REJECTED" in result_str:
                result = False
                status = "REJECTED"
            else:
                result = None
                status = "UNKNOWN"

            return json.dumps(
                {
                    "success": True,
                    "result": result,
                    "status": status,
                    "message": result_str,
                    "query": query_string,
                }
            )

        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Erreur exécution requête: {str(e)}",
                    "bnf": self._get_modal_bnf(),
                    "suggestion": "Vérifiez la syntaxe de la requête et du belief set",
                }
            )

    def _get_modal_bnf(self) -> str:
        """
        Retourne la BNF pour la logique modale TweetyProject.
        """
        return """
# BNF Syntaxe TweetyProject Modal Logic

ModalFormula ::= Atom | Negation | Conjunction | Disjunction | Implication | Equivalence | ModalOperator

Atom ::= constant_name
constant_name ::= [a-z][a-z0-9_]*

Negation ::= "!" ModalFormula
Conjunction ::= ModalFormula "&&" ModalFormula  
Disjunction ::= ModalFormula "||" ModalFormula
Implication ::= ModalFormula "=>" ModalFormula
Equivalence ::= ModalFormula "<=>" ModalFormula

ModalOperator ::= Necessity | Possibility
Necessity ::= "[]" ModalFormula
Possibility ::= "<>" ModalFormula

BeliefSet ::= Declaration* Formula*
Declaration ::= "constant" constant_name | "prop(" constant_name ")"

RÈGLES IMPORTANTES:
1. Toutes les constantes doivent être déclarées AVANT utilisation
2. Format: "constant nom_constant" puis "prop(nom_constant)" puis utilisation
3. Noms de constantes en snake_case (minuscules + underscore)
4. Éviter les mots problématiques (race, annihilation, etc.)
"""

    def validate_with_error_as_result(self, validation_func, *args, **kwargs) -> str:
        """
        Wrapper générique pour convertir les validations en résultats JSON.

        :param validation_func: Fonction de validation à appeler
        :param args: Arguments positionnels
        :param kwargs: Arguments nommés
        :return: JSON avec succès ou erreur
        """
        try:
            is_valid, message = validation_func(*args, **kwargs)

            if is_valid:
                return json.dumps(
                    {"success": True, "message": message, "validation": "passed"}
                )
            else:
                return json.dumps(
                    {
                        "success": False,
                        "error": message,
                        "bnf": self._get_modal_bnf(),
                        "suggestion": "Corrigez selon la BNF TweetyProject",
                    }
                )

        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Erreur validation: {str(e)}",
                    "bnf": self._get_modal_bnf(),
                    "suggestion": "Vérifiez la syntaxe selon la BNF",
                }
            )

    def get_sk_capabilities(self) -> Dict[str, Any]:
        """
        Retourne les capacités SK de ce bridge.
        """
        return {
            "sk_retry_support": True,
            "error_as_result": True,
            "json_structured_errors": True,
            "bnf_error_enrichment": True,
            "functions": [
                "text_to_modal_belief_set",
                "generate_modal_queries",
                "execute_modal_query_sk",
                "validate_with_error_as_result",
            ],
        }

    def demonstrate_sk_retry_difference(self, problematic_text: str) -> Dict[str, Any]:
        """
        Démontre la différence entre l'ancien et le nouveau mécanisme.

        :param problematic_text: Texte qui va causer une erreur
        :return: Comparaison des deux approches
        """
        self._logger.info(
            f"[DEMO] Démonstration différence SK retry avec: '{problematic_text}'"
        )

        # Approche classique (exceptions)
        old_approach = {
            "method": "Exceptions classiques",
            "behavior": "3 tentatives identiques qui échouent toutes",
        }

        try:
            # Simuler l'ancien comportement
            self._convert_text_to_modal_internal(problematic_text)
            old_approach["result"] = "SUCCESS (inattendu)"
        except Exception as e:
            old_approach["result"] = f"FAILED après 3 tentatives: {str(e)}"
            old_approach["agent_sees"] = "Exception - aucune information pour corriger"

        # Nouvelle approche SK (erreurs comme résultats)
        new_approach = {
            "method": "SK Retry - Erreurs comme résultats JSON",
            "behavior": "Agent reçoit l'erreur, peut analyser et corriger",
        }

        sk_result = self.text_to_modal_belief_set(problematic_text)
        sk_data = json.loads(sk_result)

        if sk_data["success"]:
            new_approach["result"] = "SUCCESS - Agent a pu corriger"
            new_approach["agent_sees"] = "Résultat de succès avec belief set valide"
        else:
            new_approach["result"] = "FAILED mais avec information pour corriger"
            new_approach["agent_sees"] = f"Erreur structurée: {sk_data['error']}"
            new_approach["bnf_provided"] = True
            new_approach["suggestion_provided"] = sk_data.get("suggestion", "")

        return {
            "problematic_input": problematic_text,
            "old_approach": old_approach,
            "new_sk_approach": new_approach,
            "key_difference": "L'agent SK peut voir l'erreur et apprendre à corriger, vs tentatives aveugles",
        }
