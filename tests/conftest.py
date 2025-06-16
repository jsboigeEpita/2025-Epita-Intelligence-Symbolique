"""
Configuration globale pour les tests pytest.

Ce fichier est automatiquement chargé par pytest avant l'exécution des tests.
Il est crucial pour assurer la stabilité et la fiabilité des tests.
"""

# ========================== ATTENTION - PROTECTION CRITIQUE ==========================
# L'import suivant active le module 'auto_env', qui est ESSENTIEL pour la sécurité
# et la stabilité de tous les tests et scripts. Il garantit que le code s'exécute
# dans l'environnement Conda approprié (par défaut 'projet-is').
#
# NE JAMAIS DÉSACTIVER, COMMENTER OU SUPPRIMER CET IMPORT.
# Le faire contourne les gardes-fous de l'environnement et peut entraîner :
#   - Des erreurs de dépendances subtiles et difficiles à diagnostiquer.
#   - Des comportements imprévisibles des tests.
#   - L'utilisation de mocks à la place de composants réels (ex: JPype).
#   - Des résultats de tests corrompus ou non fiables.
#
# Ce mécanisme lève une RuntimeError si l'environnement n'est pas correctement activé,
# empêchant l'exécution des tests dans une configuration incorrecte.
# Voir project_core/core_from_scripts/auto_env.py pour plus de détails.
# =====================================================================================
import project_core.core_from_scripts.auto_env

# D'autres configurations globales de pytest peuvent être ajoutées ici si nécessaire.
# Par exemple, des fixtures partagées à l'échelle du projet, des hooks, etc.
# Pour l'instant, la priorité est de restaurer la vérification de l'environnement.