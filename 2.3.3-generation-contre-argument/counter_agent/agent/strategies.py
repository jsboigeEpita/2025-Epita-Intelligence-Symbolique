"""
Stratégies rhétoriques pour la génération de contre-arguments.

Ce module fournit des fonctionnalités pour appliquer différentes
stratégies rhétoriques lors de la génération de contre-arguments.
"""

import logging
from typing import Dict, List, Any, Optional

from .definitions import Argument, CounterArgumentType, RhetoricalStrategy

logger = logging.getLogger(__name__)


class RhetoricalStrategies:
    """
    Classe pour gérer les stratégies rhétoriques.
    """
    
    def __init__(self):
        """
        Initialise le gestionnaire de stratégies rhétoriques.
        """
        self.strategies = {
            RhetoricalStrategy.SOCRATIC_QUESTIONING: self.apply_socratic_questioning,
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM: self.apply_reductio_ad_absurdum,
            RhetoricalStrategy.ANALOGICAL_COUNTER: self.apply_analogical_counter,
            RhetoricalStrategy.AUTHORITY_APPEAL: self.apply_authority_appeal,
            RhetoricalStrategy.STATISTICAL_EVIDENCE: self.apply_statistical_evidence
        }
    
    def get_strategy_prompt(self, strategy: RhetoricalStrategy) -> str:
        """
        Retourne le prompt à utiliser pour une stratégie donnée.
        
        Args:
            strategy: La stratégie rhétorique
            
        Returns:
            Le prompt à utiliser
        """
        prompts = {
            RhetoricalStrategy.SOCRATIC_QUESTIONING: "Utilisez la méthode socratique en posant des questions qui remettent en question les hypothèses de l'argument.",
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM: "Montrez que l'argument mène à des conséquences absurdes ou contradictoires.",
            RhetoricalStrategy.ANALOGICAL_COUNTER: "Utilisez une analogie pertinente pour illustrer les failles de l'argument.",
            RhetoricalStrategy.AUTHORITY_APPEAL: "Faites appel à des autorités reconnues ou des experts pour contredire l'argument.",
            RhetoricalStrategy.STATISTICAL_EVIDENCE: "Utilisez des données statistiques ou des études pour contredire l'argument."
        }
        
        return prompts.get(strategy, "Utilisez la stratégie la plus appropriée pour ce type d'argument.")
    
    def apply_strategy(
        self, 
        strategy: RhetoricalStrategy, 
        argument: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Applique une stratégie rhétorique à un argument.
        
        Args:
            strategy: La stratégie à appliquer
            argument: L'argument original
            
        Returns:
            L'argument modifié avec la stratégie appliquée
        """
        if strategy in self.strategies:
            return self.strategies[strategy](argument)
        return argument
    
    def apply_socratic_questioning(self, argument: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique la stratégie de questionnement socratique.
        
        Args:
            argument: L'argument original
            
        Returns:
            L'argument modifié avec la stratégie appliquée
        """
        # Implémentation à venir
        return argument
    
    def apply_reductio_ad_absurdum(self, argument: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique la stratégie de réduction à l'absurde.
        
        Args:
            argument: L'argument original
            
        Returns:
            L'argument modifié avec la stratégie appliquée
        """
        # Implémentation à venir
        return argument
    
    def apply_analogical_counter(self, argument: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique la stratégie de contre-analogie.
        
        Args:
            argument: L'argument original
            
        Returns:
            L'argument modifié avec la stratégie appliquée
        """
        # Implémentation à venir
        return argument
    
    def apply_authority_appeal(self, argument: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique la stratégie d'appel à l'autorité.
        
        Args:
            argument: L'argument original
            
        Returns:
            L'argument modifié avec la stratégie appliquée
        """
        # Implémentation à venir
        return argument
    
    def apply_statistical_evidence(self, argument: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique la stratégie d'utilisation de preuves statistiques.
        
        Args:
            argument: L'argument original
            
        Returns:
            L'argument modifié avec la stratégie appliquée
        """
        # Implémentation à venir
        return argument
    
    def suggest_strategy(self, argument_type: str, content: str) -> RhetoricalStrategy:
        """
        Suggère une stratégie rhétorique adaptée au type d'argument.
        
        Args:
            argument_type: Le type d'argument
            content: Le contenu de l'argument
            
        Returns:
            La stratégie rhétorique suggérée
        """
        # Logique simplifiée pour la suggestion de stratégie
        if "statistique" in content.lower() or "données" in content.lower():
            return RhetoricalStrategy.STATISTICAL_EVIDENCE
        
        if "tous" in content.lower() or "chaque" in content.lower():
            return RhetoricalStrategy.COUNTER_EXAMPLE
        
        if argument_type == "deductive":
            return RhetoricalStrategy.REDUCTIO_AD_ABSURDUM
        
        if argument_type == "inductive":
            return RhetoricalStrategy.AUTHORITY_APPEAL
        
        if argument_type == "abductive":
            return RhetoricalStrategy.ANALOGICAL_COUNTER
        
        # Par défaut, utiliser le questionnement socratique
        return RhetoricalStrategy.SOCRATIC_QUESTIONING

    def get_best_strategy(self, argument: Argument, counter_type: CounterArgumentType) -> RhetoricalStrategy:
        """
        Détermine la meilleure stratégie pour un type de contre-argument donné.
        
        Args:
            argument: L'argument original
            counter_type: Le type de contre-argument à générer
            
        Returns:
            La stratégie rhétorique recommandée
        """
        strategy_mapping = {
            CounterArgumentType.DIRECT_REFUTATION: [
                RhetoricalStrategy.STATISTICAL_EVIDENCE,
                RhetoricalStrategy.AUTHORITY_APPEAL
            ],
            CounterArgumentType.COUNTER_EXAMPLE: [
                RhetoricalStrategy.ANALOGICAL_COUNTER,
                RhetoricalStrategy.SOCRATIC_QUESTIONING
            ],
            CounterArgumentType.ALTERNATIVE_EXPLANATION: [
                RhetoricalStrategy.ANALOGICAL_COUNTER,
                RhetoricalStrategy.AUTHORITY_APPEAL
            ],
            CounterArgumentType.PREMISE_CHALLENGE: [
                RhetoricalStrategy.SOCRATIC_QUESTIONING,
                RhetoricalStrategy.STATISTICAL_EVIDENCE
            ],
            CounterArgumentType.REDUCTIO_AD_ABSURDUM: [
                RhetoricalStrategy.REDUCTIO_AD_ABSURDUM
            ]
        }
        
        candidates = strategy_mapping.get(counter_type, [RhetoricalStrategy.SOCRATIC_QUESTIONING])
        
        # Si on a plusieurs candidats, choisir celui avec la meilleure efficacité
        if len(candidates) > 1:
            return max(candidates, key=lambda s: self.strategies[s]['effectiveness'])
        
        return candidates[0]
    
    def _apply_socratic_questioning(self, argument: Argument, counter_type: CounterArgumentType, context: Dict[str, Any]) -> str:
        """Applique la stratégie de questionnement socratique."""
        if not argument.premises:
            return "Quelles sont les preuves qui soutiennent cette affirmation?"
        
        premise = argument.premises[0]
        
        if counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            generalization_words = ["tous", "toujours", "jamais", "chaque"]
            if any(word in premise.lower() for word in generalization_words):
                return f"Êtes-vous certain qu'il n'existe aucune exception à '{premise}'? Il suffirait d'un seul contre-exemple pour invalider cette prémisse."
            else:
                return f"Sur quelles bases établissez-vous que '{premise}'? Cette prémisse mérite d'être questionnée."
        
        elif counter_type == CounterArgumentType.DIRECT_REFUTATION:
            return f"Comment pouvez-vous concilier votre conclusion '{argument.conclusion}' avec le fait que {self._generate_counter_fact(argument)}?"
        
        # Cas par défaut
        return "Cette conclusion vous semble-t-elle vraiment inévitable, même en considérant d'autres perspectives?"
    
    def _apply_reductio_ad_absurdum(self, argument: Argument, counter_type: CounterArgumentType, context: Dict[str, Any]) -> str:
        """Applique la stratégie de réduction à l'absurde."""
        conclusion = argument.conclusion
        
        if "tous" in conclusion.lower() or "toujours" in conclusion.lower():
            absurd_consequence = self._generate_absurd_consequence(argument)
            return f"Si nous acceptons que {conclusion}, nous devrions également accepter que {absurd_consequence}, ce qui est manifestement absurde."
        
        elif "doit" in conclusion.lower() or "nécessairement" in conclusion.lower():
            absurd_consequence = self._generate_absurd_consequence(argument)
            return f"Si cette obligation était universelle, elle mènerait à des situations intenables comme {absurd_consequence}."
        
        else:
            return f"En poussant cette logique à l'extrême, nous arriverions à {self._generate_absurd_consequence(argument)}, ce qui montre les limites de ce raisonnement."
    
    def _apply_analogical_counter(self, argument: Argument, counter_type: CounterArgumentType, context: Dict[str, Any]) -> str:
        """Applique la stratégie de contre-argumentation par analogie."""
        analogy = self._generate_analogy(argument)
        
        if counter_type == CounterArgumentType.COUNTER_EXAMPLE:
            return f"Cet argument est similaire à dire que {analogy}. Dans ce cas, nous voyons clairement que le même raisonnement ne tient pas."
        
        elif counter_type == CounterArgumentType.ALTERNATIVE_EXPLANATION:
            return f"Considérons une situation analogue: {analogy}. Ici, une explication alternative serait plus plausible, ce qui suggère que l'argument original pourrait également avoir d'autres explications."
        
        # Cas par défaut
        return f"C'est comme dire que {analogy}, ce qui révèle les limites de ce raisonnement."
    
    def _apply_authority_appeal(self, argument: Argument, counter_type: CounterArgumentType, context: Dict[str, Any]) -> str:
        """Applique la stratégie d'appel à l'autorité."""
        if counter_type == CounterArgumentType.DIRECT_REFUTATION:
            return f"Selon les experts du domaine, cette conclusion est incorrecte car {self._generate_expert_counter(argument)}."
        
        elif counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            return f"Des recherches récentes menées par des spécialistes réputés remettent en question cette prémisse, démontrant que {self._generate_expert_counter(argument)}."
        
        # Cas par défaut
        return f"Le consensus scientifique contredit cette affirmation, comme le montrent les études qui indiquent que {self._generate_expert_counter(argument)}."
    
    def _apply_statistical_evidence(self, argument: Argument, counter_type: CounterArgumentType, context: Dict[str, Any]) -> str:
        """Applique la stratégie d'évidence statistique."""
        if counter_type == CounterArgumentType.DIRECT_REFUTATION:
            return f"Les statistiques contredisent directement cette conclusion: {self._generate_statistical_counter(argument)}."
        
        elif counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            return f"Les données empiriques ne soutiennent pas cette prémisse. En fait, {self._generate_statistical_counter(argument)}."
        
        # Cas par défaut
        return f"Les chiffres racontent une histoire différente: {self._generate_statistical_counter(argument)}."
    
    def _generate_from_template(self, strategy_info: Dict[str, Any], argument: Argument, context: Dict[str, Any]) -> str:
        """Génère un contre-argument à partir d'un template."""
        templates = strategy_info.get('templates', [])
        if not templates:
            return self._fallback_counter_argument(argument, CounterArgumentType.DIRECT_REFUTATION)
        
        # Choisir le premier template (dans une version plus avancée, on pourrait choisir aléatoirement)
        template = templates[0]
        
        # Remplir le template avec les informations disponibles
        filled_template = template
        
        if "{premise}" in template and argument.premises:
            filled_template = filled_template.replace("{premise}", argument.premises[0])
        
        if "{absurd_consequence}" in template:
            filled_template = filled_template.replace("{absurd_consequence}", self._generate_absurd_consequence(argument))
        
        if "{analogy}" in template or "{analogy_scenario}" in template:
            analogy = self._generate_analogy(argument)
            filled_template = filled_template.replace("{analogy}", analogy)
            filled_template = filled_template.replace("{analogy_scenario}", analogy)
        
        if "{expert}" in template:
            filled_template = filled_template.replace("{expert}", "les experts du domaine")
        
        if "{reason}" in template:
            filled_template = filled_template.replace("{reason}", "les données empiriques contredisent cette affirmation")
        
        if "{counter_evidence}" in template:
            filled_template = filled_template.replace("{counter_evidence}", "les preuves disponibles suggèrent le contraire")
        
        if "{percentage}" in template:
            filled_template = filled_template.replace("{percentage}", "seulement 15")
        
        if "{statistical_evidence}" in template:
            filled_template = filled_template.replace("{statistical_evidence}", self._generate_statistical_counter(argument))
        
        if "{source}" in template:
            filled_template = filled_template.replace("{source}", "sources fiables")
        
        if "{alternative_scenario}" in template:
            filled_template = filled_template.replace("{alternative_scenario}", "le contexte était différent")
        
        return filled_template
    
    def _fallback_counter_argument(self, argument: Argument, counter_type: CounterArgumentType) -> str:
        """Génère un contre-argument par défaut si la stratégie échoue."""
        if counter_type == CounterArgumentType.DIRECT_REFUTATION:
            return f"Cette conclusion est incorrecte car elle ne tient pas compte de facteurs importants."
        
        elif counter_type == CounterArgumentType.COUNTER_EXAMPLE:
            return f"Il existe des cas qui contredisent cet argument, par exemple quand les circonstances sont différentes."
        
        elif counter_type == CounterArgumentType.PREMISE_CHALLENGE:
            return f"La prémisse '{argument.premises[0] if argument.premises else 'principale'}' n'est pas suffisamment étayée."
        
        elif counter_type == CounterArgumentType.ALTERNATIVE_EXPLANATION:
            return f"Une explication alternative plus plausible serait que d'autres facteurs sont en jeu."
        
        elif counter_type == CounterArgumentType.REDUCTIO_AD_ABSURDUM:
            return f"Cette logique mène à des conclusions absurdes si on la pousse à son terme."
        
        return f"Cet argument présente plusieurs failles qui remettent en question sa validité."
    
    def _generate_absurd_consequence(self, argument: Argument) -> str:
        """Génère une conséquence absurde pour la réduction à l'absurde."""
        # Dans une version plus avancée, ceci serait généré par un LLM
        conclusion = argument.conclusion.lower()
        
        if "toujours" in conclusion or "tous" in conclusion:
            return "toutes les exceptions seraient impossibles, ce qui va à l'encontre de l'expérience commune"
        elif "jamais" in conclusion or "aucun" in conclusion:
            return "toute occurrence serait logiquement impossible, ce qui contredit les observations"
        elif "doit" in conclusion or "nécessairement" in conclusion:
            return "il n'y aurait aucune place pour la liberté de choix ou les circonstances atténuantes"
        else:
            return "nous devrions accepter des conséquences contradictoires ou manifestement fausses"
    
    def _generate_analogy(self, argument: Argument) -> str:
        """Génère une analogie pour la contre-argumentation par analogie."""
        # Dans une version plus avancée, ceci serait généré par un LLM
        if "tous" in argument.content.lower() or "chaque" in argument.content.lower():
            return "tous les oiseaux peuvent voler, alors que les pingouins sont des oiseaux et ne volent pas"
        elif "toujours" in argument.content.lower():
            return "le soleil se lève toujours à l'est, ce qui ignore les perspectives différentes aux pôles"
        else:
            return "on devrait toujours choisir le chemin le plus court, alors que parfois le détour est plus sûr ou plus agréable"
    
    def _generate_expert_counter(self, argument: Argument) -> str:
        """Génère un contre-argument basé sur l'expertise."""
        # Dans une version plus avancée, ceci serait généré par un LLM
        return "des facteurs plus complexes sont en jeu et la réalité est plus nuancée que ce que l'argument suggère"
    
    def _generate_statistical_counter(self, argument: Argument) -> str:
        """Génère un contre-argument basé sur des statistiques."""
        # Dans une version plus avancée, ceci serait généré par un LLM
        return "dans seulement 15% des cas étudiés, cette relation de cause à effet a été observée, ce qui est bien loin d'une règle générale"
    
    def _generate_counter_fact(self, argument: Argument) -> str:
        """Génère un fait contradictoire pour le questionnement socratique."""
        # Dans une version plus avancée, ceci serait généré par un LLM
        if argument.conclusion:
            negation = "il existe des cas bien documentés où le contraire s'est produit"
            return negation
        return "des contre-exemples existent" 