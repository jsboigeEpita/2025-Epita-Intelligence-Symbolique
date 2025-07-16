from semantic_kernel.functions import kernel_function

class SimpleExplorationTool:
    """
    Un outil d'exploration simplifié qui utilise une unique fonction sémantique.
    """
    @kernel_function(
        name="get_hypotheses",
        description="Identifie les branches pertinentes de la taxonomie à explorer."
    )
    def get_hypotheses(self, input: str) -> str:
        """
        Ce prompt demande au LLM d'identifier les branches de la taxonomie.
        La fonction elle-même est sémantique, définie par le prompt dans le kernel.
        Le corps de la fonction Python n'est pas utilisé lorsque la fonction est
        invoquée via un prompt.
        """
        # Ce code n'est pas exécuté, le prompt l'est.
        return ""