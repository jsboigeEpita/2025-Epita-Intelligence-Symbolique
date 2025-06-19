import os
import sys
import pytest
from api.services import DungAnalysisService
from api.dependencies import get_dung_analysis_service

# Ajout du chemin du projet pour l'import de modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

def main():
    """
    Fonction principale pour exécuter les tests du service Dung dans un sous-processus JVM.
    """
    if not os.environ.get('JAVA_HOME'):
        pytest.fail("La variable d'environnement JAVA_HOME est requise.")

    try:
        # Initialisation du service
        # Note: La gestion de la JVM (démarrage/arrêt) est implicite ici,
        # gérée par l'environnement du sous-processus.
        dung_service = get_dung_analysis_service()
        assert dung_service is not None
        assert hasattr(dung_service, 'DungTheory'), "L'attribut 'DungTheory' est manquant."

        # Scénario 1: Framework simple
        arguments = ["a", "b", "c"]
        attacks = [("a", "b"), ("b", "c")]
        result = dung_service.analyze_framework(arguments, attacks)
        assert result['semantics']['grounded'] == ["a", "c"]
        assert result['semantics']['preferred'] == [["a", "c"]]

        # Scénario 2: Framework cyclique
        arguments = ["a", "b"]
        attacks = [("a", "b"), ("b", "a")]
        result = dung_service.analyze_framework(arguments, attacks)
        assert result['semantics']['grounded'] == []
        assert result['semantics']['preferred'] == [["a"], ["b"]]

        # Scénario 3: Framework vide
        arguments = []
        attacks = []
        result = dung_service.analyze_framework(arguments, attacks)
        assert result['semantics']['grounded'] == []
        assert result['semantics']['preferred'] == [[]]

        # Scénario 4: Argument auto-attaquant
        arguments = ["a", "b"]
        attacks = [("a", "a"), ("a", "b")]
        result = dung_service.analyze_framework(arguments, attacks)
        assert result['semantics']['grounded'] == []
        assert result['argument_status']['a']['credulously_accepted'] is False
        assert result['graph_properties']['self_attacking_nodes'] == ["a"]

        print("SUCCESS: Tous les tests du worker se sont terminés avec succès.")

    except Exception as e:
        print(f"ERROR: Une erreur est survenue dans le worker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()