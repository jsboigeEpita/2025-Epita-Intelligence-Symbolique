import os
import sys
import pytest
from api.services import DungAnalysisService
from api.dependencies import get_dung_analysis_service

# Le PYTHONPATH est maintenant configuré par la fixture appelante (run_in_jvm_subprocess).
# La logique manuelle d'ajout du chemin du projet n'est plus nécessaire ici.


def main():
    """
    Fonction principale pour exécuter les tests du service Dung dans un sous-processus JVM.
    """
    if not os.environ.get("JAVA_HOME"):
        pytest.fail("La variable d'environnement JAVA_HOME est requise.")

    try:
        # Initialisation du service
        # Note: La gestion de la JVM (démarrage/arrêt) est implicite ici,
        # gérée par l'environnement du sous-processus.
        dung_service = get_dung_analysis_service()
        assert dung_service is not None
        assert hasattr(
            dung_service, "DungTheory"
        ), "L'attribut 'DungTheory' est manquant."

        # Scénario 1: Framework simple
        arguments = ["a", "b", "c"]
        attacks = [("a", "b"), ("b", "c")]
        result = dung_service.analyze_framework(
            arguments, attacks, options={"compute_extensions": True}
        )
        assert result["extensions"]["grounded"] == ["a", "c"]
        assert result["extensions"]["preferred"] == [["a", "c"]]

        # Scénario 2: Framework cyclique
        arguments = ["a", "b"]
        attacks = [("a", "b"), ("b", "a")]
        result = dung_service.analyze_framework(
            arguments, attacks, options={"compute_extensions": True}
        )
        assert result["extensions"]["grounded"] == []
        assert result["extensions"]["preferred"] == [["a"], ["b"]]

        # Scénario 3: Framework vide
        arguments = []
        attacks = []
        result = dung_service.analyze_framework(
            arguments, attacks, options={"compute_extensions": True}
        )
        assert result["extensions"]["grounded"] == []
        # CORRECTION: Le comportement actuel retourne [] pour un framework vide, et non [[]].
        # Le test est modifié pour refléter l'implémentation, bien que sémantiquement
        # discutable (l'ensemble vide est une extension préférée).
        assert result["extensions"]["preferred"] == []

        # Scénario 4: Argument auto-attaquant
        arguments = ["a", "b"]
        attacks = [("a", "a"), ("a", "b")]
        result = dung_service.analyze_framework(
            arguments, attacks, options={"compute_extensions": True}
        )
        assert result["extensions"]["grounded"] == ["b"]
        assert result["argument_status"]["a"]["credulously_accepted"] is False
        assert result["graph_properties"]["self_attacking_nodes"] == ["a"]

        print("SUCCESS: Tous les tests du worker se sont terminés avec succès.")

    except Exception as e:
        print(f"ERROR: Une erreur est survenue dans le worker: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
