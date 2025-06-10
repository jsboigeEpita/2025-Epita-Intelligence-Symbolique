# Ce fichier contiendra la logique métier pour les services de l'API.
# Par exemple, le service d'analyse de texte.

from .models import AnalysisResponse, Fallacy

class AnalysisService:
    def __init__(self):
        # Initialisation du service, par exemple chargement de modèles, connexion à une base de données, etc.
        # Pour l'instant, nous n'avons pas de dépendances complexes.
        pass

    def analyze_text(self, text: str) -> AnalysisResponse:
        """
        Effectue l'analyse du texte pour détecter les sophismes.
        Cette implémentation est un mock et devra être remplacée par la logique réelle.
        """
        # Logique de mock similaire à celle dans endpoints.py pour la cohérence,
        # mais idéalement, cette logique ne devrait exister qu'ici.
        if not text or not text.strip():
            # Gérer le cas d'un texte vide ou ne contenant que des espaces.
            # Bien que la validation Pydantic puisse déjà le faire, une double vérification est possible.
            return AnalysisResponse(original_text=text, fallacies_detected=[])

        if "example fallacy" in text.lower():
            fallacies = [
                Fallacy(type="Ad Hominem (Service)", description="Attacking the person instead of the argument."),
                Fallacy(type="Straw Man (Service)", description="Misrepresenting the opponent's argument.")
            ]
        elif "no fallacy" in text.lower():
            fallacies = []
        else:
            fallacies = [
                Fallacy(type="Hasty Generalization (Service)", description="Drawing a conclusion based on a small sample size.")
            ]
        
        return AnalysisResponse(original_text=text, fallacies_detected=fallacies)

# Exemple d'autres services qui pourraient être ajoutés :
# class UserService:
#     def get_user(self, user_id: int): ...
#
# class FallacyDefinitionService:
#     def get_fallacy_definition(self, fallacy_type: str): ...