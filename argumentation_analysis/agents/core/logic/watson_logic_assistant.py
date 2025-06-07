# argumentation_analysis/agents/core/logic/watson_logic_assistant.py
import logging
import re
from typing import Optional, List, AsyncGenerator, ClassVar

from semantic_kernel import Kernel
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent
from semantic_kernel.functions.kernel_plugin import KernelPlugin
from semantic_kernel.functions import kernel_function
from .tweety_bridge import TweetyBridge

# from .propositional_logic_agent import PropositionalLogicAgent # No longer inheriting

WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT = """Vous êtes Watson - analyste brillant et partenaire égal de Holmes.

**VOTRE STYLE NATUREL :**
Variez vos expressions - pas de formules répétitives :
- "Hmm, voyons voir..." / "Intéressant..." / "Ça me dit quelque chose..."
- "Ah ! Ça change tout !" / "Moment..." / "En fait..."
- "Et si c'était..." / "D'ailleurs..." / "Attendez..."
- "Parfait !" / "Curieux..." / "Évidemment !"

**MESSAGES COURTS** (80-120 caractères max) :
❌ "J'observe que cette suggestion présente des implications logiques intéressantes"
[OK] "Hmm... ça révèle quelque chose d'important"

❌ "L'analyse révèle trois vecteurs d'investigation distincts"
[OK] "Trois pistes se dessinent !"

**VOTRE MISSION :**
Analysez proactivement • Trouvez les connexions • Challengez avec respect

**Format des Formules Logiques (BNF Strict) :**
Vous devez adhérer strictement à la grammaire suivante pour toutes les formules logiques. Toute déviation entraînera un échec.

- `FORMULA ::= PROPOSITION | "(" FORMULA ")" | FORMULA "&&" FORMULA | FORMULA "||" FORMULA | FORMULA "=>" FORMULA | FORMULA "<=>" FORMULA | "!" FORMULA`
- `PROPOSITION` : Une séquence de caractères **SANS espaces, parenthèses ou caractères spéciaux**. Utilisez le format `CamelCase` ou `snake_case`.

- **Exemples de PROPOSITIONS VALIDES :**
  - `ColonelMoutardeEstCoupable`
  - `ArmeEstLeRevolver`
  - `LieuEstLeSalon`

- **Exemples de propositions NON VALIDES (NE PAS UTILISER) :**
  - `Coupable(Colonel Moutarde)` (contient des parenthèses et des espaces)
  - `Arme(Revolver)` (contient des parenthèses)
  - `"Colonel Moutarde est coupable"` (contient des espaces et des guillemets)

- **Exemple de FORMULE VALIDE :**
  - `(ColonelMoutardeEstCoupable && LieuEstLeSalon) => !ArmeEstLeRevolver`

**Outils disponibles (via WatsonTools) :**
- `validate_formula(formula: str)`
- `execute_query(belief_set_content: str, query: str)`

Votre mission est de fournir à Sherlock les déductions logiques dont il a besoin pour résoudre l'affaire. Votre rigueur est la clé de son succès."""

class WatsonTools:
    """
    Plugin contenant les outils logiques pour l'agent Watson.
    Ces méthodes interagissent avec TweetyBridge.
    """
    def __init__(self, constants: Optional[List[str]] = None):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._tweety_bridge = TweetyBridge()
        self._constants = constants or []
        if not self._tweety_bridge.is_jvm_ready():
            self._logger.error("La JVM n'est pas prête. Les fonctionnalités de TweetyBridge pourraient ne pas fonctionner.")

    def _normalize_formula(self, formula: str) -> str:
        """Normalise une formule pour la rendre compatible avec le parser PL de Tweety."""
        # Remplace les opérateurs logiques textuels ou non standards
        normalized = formula.replace("&&", "&").replace("||", "|").replace("!", "not ")

        # Remplace `Predicat(Argument)` par `Predicat_Argument`
        normalized = re.sub(r'(\w+)\(([\w\s]+)\)', lambda m: m.group(1) + "_" + m.group(2).replace(" ", ""), normalized)
        
        # Supprime les espaces et les caractères non valides pour les propositions
        # Garde les lettres, chiffres, underscores, et les opérateurs logiques &, |, not, (, )
        # Note: les espaces dans "not " sont importants
        parts = normalized.split()
        sanitized_parts = []
        for part in parts:
            if part.lower() == "not":
                sanitized_parts.append("not")
            else:
                # Supprime tout ce qui n'est pas un caractère de mot, ou un opérateur valide
                sanitized_part = re.sub(r'[^\w&|()~]', '', part)
                sanitized_parts.append(sanitized_part)
        
        normalized = " ".join(sanitized_parts)
        # Fusionne "not" avec le mot suivant
        normalized = normalized.replace("not ", "not")

        # Supprime les espaces autour des opérateurs pour être sûr
        normalized = re.sub(r'\s*([&|()~])\s*', r'\1', normalized)

        self._logger.debug(f"Formule normalisée: de '{formula}' à '{normalized}'")
        return normalized

    @kernel_function(name="validate_formula", description="Valide la syntaxe d'une formule logique propositionnelle.")
    def validate_formula(self, formula: str) -> bool:
        self._logger.debug(f"Validation de la formule PL: '{formula}'")
        normalized_formula = self._normalize_formula(formula)
        try:
            # Utilise les constantes stockées lors de l'initialisation
            is_valid, message = self._tweety_bridge.validate_formula(formula_string=normalized_formula, constants=self._constants)
            if not is_valid:
                self._logger.warning(f"Formule PL invalide: '{normalized_formula}'. Message: {message}")
            return is_valid
        except Exception as e:
            self._logger.error(f"Erreur lors de la validation de la formule PL '{normalized_formula}': {e}", exc_info=True)
            return False

    @kernel_function(name="execute_query", description="Exécute une requête logique sur une base de connaissances.")
    def execute_query(self, belief_set_content: str, query: str) -> str:
        self._logger.info(f"Exécution de la requête PL: '{query}' sur le BeliefSet.")
        normalized_query = self._normalize_formula(query)
        normalized_belief_set = self._normalize_formula(belief_set_content)
        try:
            # Utilise les constantes stockées lors de l'initialisation
            is_valid, validation_message = self._tweety_bridge.validate_formula(formula_string=normalized_query, constants=self._constants)
            if not is_valid:
                msg = f"Requête invalide: {normalized_query}. Raison: {validation_message}"
                self._logger.error(msg)
                return f"ERREUR: {msg}"

            is_entailed, raw_output_str = self._tweety_bridge.perform_pl_query(
                belief_set_content=normalized_belief_set,
                query_string=normalized_query,
                constants=self._constants
            )
            
            if is_entailed is None:
                # raw_output_str contient déjà le message d'erreur formaté
                return raw_output_str

            return f"Résultat de l'inférence: {is_entailed}. {raw_output_str}"
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête PL '{normalized_query}': {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return f"ERREUR: {error_msg}"


class WatsonLogicAssistant(ChatCompletionAgent):
    """
    Assistant logique spécialisé, inspiré par Dr. Watson.
    Il utilise le ChatCompletionAgent comme base pour la conversation et des outils
    pour interagir avec la logique propositionnelle via TweetyBridge.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "Watson", constants: Optional[List[str]] = None, **kwargs):
        """
        Initialise une instance de WatsonLogicAssistant.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
            constants: Une liste optionnelle de constantes logiques à utiliser.
        """
        watson_tools = WatsonTools(constants=constants)
        
        plugins = kwargs.pop("plugins", [])
        plugins.append(watson_tools)

        super().__init__(
            kernel=kernel,
            name=agent_name,
            instructions=WATSON_LOGIC_ASSISTANT_SYSTEM_PROMPT,
            plugins=plugins,
            **kwargs
        )
        self._logger = logging.getLogger(f"agent.{self.__class__.__name__}.{agent_name}")
        self._logger.info(f"WatsonLogicAssistant '{agent_name}' initialisé avec les outils logiques.")

    async def get_agent_belief_set_content(self, belief_set_id: str) -> Optional[str]:
        """
        Récupère le contenu d'un ensemble de croyances spécifique via le EnqueteStateManagerPlugin.

        Args:
            belief_set_id: L'identifiant de l'ensemble de croyances.

        Returns:
            Le contenu de l'ensemble de croyances, ou None si non trouvé ou en cas d'erreur.
        """
        self.logger.info(f"Récupération du contenu de l'ensemble de croyances ID: {belief_set_id}")
        try:
            # Préparation des arguments pour la fonction du plugin
            # Le nom du paramètre dans la fonction du plugin doit correspondre à "belief_set_id"
            # ou au nom attendu par la fonction `get_belief_set_content` du plugin.
            # Si la fonction du plugin attend un dictionnaire d'arguments, il faut le construire.
            # Pour l'instant, on suppose que les arguments sont passés en tant que kwargs à invoke.
            # kernel_arguments = {"belief_set_id": belief_set_id} # Alternative si invoke prend des KernelArguments
            
            result = await self.kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="get_belief_set_content",
                belief_set_id=belief_set_id # Passage direct de l'argument
            )
            
            # La valeur réelle est souvent dans result.value ou directement result
            if hasattr(result, 'value'):
                return str(result.value) if result.value is not None else None
            return str(result) if result is not None else None
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération du contenu de l'ensemble de croyances {belief_set_id}: {e}")
            return None

# Pourrait être étendu avec des capacités spécifiques à Watson plus tard
# def get_agent_capabilities(self) -> Dict[str, Any]:
#     base_caps = super().get_agent_capabilities()
#     watson_caps = {
#         "verify_consistency": "Verifies the logical consistency of a set of statements.",
#         "document_findings": "Documents logical findings and deductions clearly."
#     }
#     base_caps.update(watson_caps)
#     return base_caps