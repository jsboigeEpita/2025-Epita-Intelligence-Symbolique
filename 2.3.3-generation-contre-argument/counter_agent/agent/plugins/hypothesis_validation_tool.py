# Fichier: argumentation_analysis/agents/plugins/hypothesis_validation_tool.py

from typing import Dict, Any

from ..definitions import Argument, CounterArgument, EvaluationResult, ValidationResult
from ..utils.hybrid_decorator import hybrid_function

class HypothesisValidationTool:
    """
    Outil pour valider une hypothèse de sophisme spécifique.
    """

    def __init__(self, some_dependency=None):
        """
        Initialise l'outil de validation d'hypothèses.
        
        Args:
            some_dependency: Toute dépendance nécessaire (par ex. un client API, etc.).
        """
        # Dans une implémentation réelle, nous pourrions avoir besoin de dépendances.
        self.dependency = some_dependency
        print("HypothesisValidationTool initialisé.")

    @hybrid_function(
        prompt_template=(
            "Évalue l'argument suivant : '{{$argument_text}}'.\n"
            "Détermine s'il contient le sophisme décrit ci-dessous :\n"
            "--- Définition du Sophisme ---\n"
            "{{$fallacy_hypothesis.description}}\n"
            "--- Fin de la Définition ---\n"
            "Analyse l'argument et fournis une évaluation structurée au format JSON. "
            "Le JSON doit contenir les clés suivantes :\n"
            "- 'confidence': un score de confiance (0.0 à 1.0) indiquant la probabilité que le sophisme soit présent.\n"
            "- 'explanation': une explication détaillée (en 2-3 phrases) justifiant ton évaluation.\n"
            "- 'is_fallacious': un booléen (true/false) confirmant la présence du sophisme.\n\n"
            "Exemple de sortie : \n"
            "{\"confidence\": 0.85, \"explanation\": \"L'auteur attaque le caractère de son adversaire plutôt que son argument, ce qui est caractéristique d'une attaque ad hominem.\", \"is_fallacious\": true}"
        )
    )
    async def validate_fallacy(
        self,
        argument_text: str,
        fallacy_hypothesis: Dict[str, Any],
        confidence: float,
        explanation: str,
        is_fallacious: bool
    ) -> Dict[str, Any]:
        """
        Fonction native qui reçoit l'analyse du LLM et la structure.
        
        Args:
            argument_text: Le texte de l'argument à analyser.
            fallacy_hypothesis: La description et les détails du sophisme suspecté.
            confidence: Le score de confiance généré par le LLM.
            explanation: L'explication générée par le LLM.
            is_fallacious: Le booléen généré par le LLM.
        
        Returns:
            Un dictionnaire structuré contenant le rapport de validation.
        """
        print(f"Validation de l'hypothèse '{fallacy_hypothesis.get('name', 'inconnue')}' pour l'argument : '{argument_text[:50]}...'")
        
        # Ici, la fonction native reçoit directement les données structurées
        # grâce au décorateur et au prompt.
        # Nous pouvons ajouter une logique métier supplémentaire si nécessaire.
        # Par exemple, enregistrer le résultat, effectuer une double vérification, etc.

        report = {
            "hypothesis_id": fallacy_hypothesis.get("id"),
            "hypothesis_name": fallacy_hypothesis.get("name"),
            "is_fallacious": is_fallacious,
            "confidence": confidence,
            "explanation": explanation,
            "argument_analyzed": argument_text
        }

        print(f"Rapport de validation généré pour '{report['hypothesis_name']}': Confiance = {report['confidence']:.2f}")

        return report