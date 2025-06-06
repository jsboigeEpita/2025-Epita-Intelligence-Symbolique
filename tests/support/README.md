# Utilitaires de Support pour les Tests

Ce répertoire contient des modules et des scripts qui fournissent un support pour l'exécution des tests. Contrairement aux tests eux-mêmes, ces modules ne valident pas directement le code de l'application mais fournissent des fonctionnalités auxiliaires, comme la gestion des dépendances, la génération de données ou des fonctions d'aide communes.

## Objectif

L'objectif de ce répertoire est de centraliser le code de support qui facilite la mise en place, l'exécution et la maintenance de la suite de tests.

## Modules

- **[`portable_octave_installer.py`](portable_octave_installer.py:1)**: Un script utilitaire pour télécharger et installer automatiquement une version portable de GNU Octave. Octave est une dépendance pour certaines capacités d'analyse du projet. Ce script s'assure qu'Octave est disponible dans un emplacement prévisible (`libs/portable_octave`) avant que les tests qui en dépendent ne soient exécutés. Il gère le téléchargement, l'extraction de l'archive ZIP et la vérification de l'installation.

- **[`common_test_helpers.py`](common_test_helpers.py:1)**: (Actuellement vide) Conçu pour contenir des fonctions d'aide, des assertions personnalisées ou d'autres utilitaires partagés par plusieurs fichiers de test.

- **[`data_generators.py`](data_generators.py:1)**: (Actuellement vide) Prévu pour héberger des fonctions qui génèrent des données de test complexes ou volumineuses, aidant à créer des scénarios de test réalistes et variés.

## Utilisation

Ces modules sont généralement importés par des tests spécifiques ou par des hooks de configuration de test (comme `conftest.py`) pour préparer l'environnement de test. Par exemple, `ensure_portable_octave` peut être appelé avant une suite de tests d'intégration qui nécessite une analyse numérique via Octave.
