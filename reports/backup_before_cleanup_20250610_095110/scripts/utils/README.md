# Scripts Utilitaires

Ce répertoire contient divers scripts utilitaires pour le projet.

## Gestion de l'Encodage

Deux scripts principaux sont fournis pour la gestion de l'encodage des fichiers :

- **`check_encoding.py`**:
  Ce script vérifie l'encodage de tous les fichiers Python (`.py`) au sein du projet pour s'assurer qu'ils sont bien en UTF-8. Il utilise la fonction `check_project_python_files_encoding` du module `project_core.dev_utils.encoding_utils`.
  C'est un outil de diagnostic utile pour maintenir la cohérence de l'encodage à travers le projet.

- **`fix_encoding.py`**:
  Ce script permet de convertir l'encodage d'un fichier spécifique vers UTF-8 (ou un autre encodage cible). Il tente de détecter l'encodage source (ou accepte une liste d'encodages source potentiels) et réécrit le fichier avec le nouvel encodage. Il utilise la fonction `fix_file_encoding` du module `project_core.dev_utils.encoding_utils`.
  C'est un outil de correction à utiliser lorsqu'un fichier avec un encodage incorrect est identifié.

**Choix de Conception :**

La logique métier pour la vérification et la correction de l'encodage a été centralisée dans le module `project_core.dev_utils.encoding_utils.py`. Les scripts présents dans ce répertoire (`scripts/utils/`) servent d'interfaces en ligne de commande (CLI) pour accéder facilement à ces fonctionnalités. Cette séparation permet :
1.  **Réutilisabilité :** Les fonctions utilitaires dans `project_core` peuvent être appelées par d'autres parties du projet ou d'autres scripts si nécessaire.
2.  **Clarté :** Les scripts CLI restent simples et se concentrent sur l'interaction avec l'utilisateur et le passage d'arguments, tandis que la logique complexe est encapsulée dans les modules utilitaires.
3.  **Maintenabilité :** Les modifications de la logique d'encodage se font à un seul endroit (`project_core.dev_utils.encoding_utils.py`), facilitant la maintenance et les mises à jour.

Il n'y a donc pas de "fusion" à faire entre `check_encoding.py` et `fix_encoding.py` eux-mêmes, car ils exposent des fonctionnalités distinctes et déjà modularisées. La solution actuelle est considérée comme la meilleure approche.

## Autres Utilitaires

D'autres scripts utilitaires peuvent être présents dans ce répertoire pour diverses tâches de maintenance, d'analyse ou de test.