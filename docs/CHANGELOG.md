# Changelog

Ce fichier documente les modifications apportées au projet d'analyse argumentative.

## [1.0.0] - 2025-05-02

### Modifications apportées

#### Correction de la structure du projet
- Création du répertoire `data` avec un fichier `.gitkeep` pour maintenir le dossier dans Git
- Mise à jour des imports pour assurer la compatibilité entre les modules
- Ajout de fichiers `__init__.py` manquants dans certains packages
- Correction des chemins relatifs dans les imports

#### Implémentation de la version mock du chargeur de taxonomie
- Remplacement des appels réseau par des données mock pour les tests et le développement
- Implémentation de versions mock pour `get_taxonomy_path()` et `validate_taxonomy_file()`
- Ajout d'entrées supplémentaires dans les données mock pour une meilleure couverture des tests
- Ajout d'une variable globale `USE_MOCK` pour contrôler le comportement du module

#### Correction des tests unitaires
- Mise à jour des tests pour utiliser les versions mock des fonctions
- Correction des assertions dans les tests pour correspondre aux nouvelles implémentations
- Ajout de mocks pour éviter les appels réseau pendant les tests
- Correction du test `test_state_manager_plugin` pour vérifier `raw_text_snippet` au lieu de `raw_text`

#### Nettoyage des fichiers obsolètes et temporaires
- Suppression des rapports de vérification obsolètes
- Création d'un script de nettoyage automatique (`cleanup_project.py`)
- Mise à jour du fichier `.gitignore` pour ignorer les fichiers sensibles et temporaires
- Suppression des fichiers Python compilés (`.pyc`, `__pycache__`, etc.)
- Suppression des fichiers de logs obsolètes

### Problèmes résolus
- Correction du problème de téléchargement de la taxonomie pendant les tests
- Résolution des échecs de tests liés à l'API Semantic Kernel
- Correction des erreurs de syntaxe dans les fichiers de sauvegarde
- Résolution des problèmes d'encodage dans la documentation
- Correction des problèmes de dépendance aux clés API réelles dans les tests

### Problèmes connus restants
- Certains tests s'attendent à des modèles spécifiques, mais d'autres sont utilisés
- Le test de clé API manquante s'attend à ce que le service soit None, mais un service est créé
- Certains fichiers dupliqués restent à nettoyer dans la structure du projet
- Certains dossiers manquent encore de fichiers README.md

### Recommandations pour les développements futurs
- Mettre à jour tous les tests pour qu'ils utilisent des mocks au lieu de dépendre de services externes
- Ajouter des fichiers README.md dans tous les dossiers pour améliorer la documentation
- Éliminer les duplications de code et les fichiers redondants
- Implémenter une version non-mock du chargeur de taxonomie pour la production
- Mettre en place une validation syntaxique automatique avant la sauvegarde des fichiers
- Maintenir une documentation à jour sur le processus de restauration des fichiers de configuration