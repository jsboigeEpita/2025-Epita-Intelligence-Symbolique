# Répertoire de données pour l'analyse d'argumentation

Ce répertoire contient les données essentielles utilisées par le système d'analyse d'argumentation.

## Structure du répertoire

Le répertoire contient les fichiers suivants :

- `argumentum_fallacies_taxonomy.csv` : Taxonomie détaillée des sophismes et arguments fallacieux
- `extract_sources.json.gz.enc` : Fichier chiffré contenant des sources d'extraits (format compressé et chiffré)
- `.gitkeep` : Fichier permettant de conserver le répertoire dans Git même s'il est vide

## Description des fichiers principaux

### argumentum_fallacies_taxonomy.csv

Ce fichier CSV contient une taxonomie complète des sophismes et arguments fallacieux utilisée par le système d'analyse rhétorique. La taxonomie est structurée hiérarchiquement avec les informations suivantes :

- Identifiants et chemins hiérarchiques
- Catégorisation (Famille, Sous-Famille, etc.)
- Descriptions en plusieurs langues (français, anglais, russe, portugais)
- Exemples d'utilisation
- Liens vers des ressources externes
- Relations entre différents types d'arguments fallacieux

Cette taxonomie est utilisée par les outils d'analyse rhétorique pour identifier et classifier les arguments dans les textes analysés.

### extract_sources.json.gz.enc

Fichier chiffré contenant des sources d'extraits utilisées pour l'analyse. Le fichier est compressé (gzip) puis chiffré pour protéger les données sensibles.

## Utilisation

Les données de ce répertoire sont principalement utilisées par :

- Les outils d'analyse rhétorique dans `argumentation_analysis/tests/tools/`
- Les modules d'analyse d'argumentation
- Les utilitaires de réparation d'extraits dans `argumentation_analysis/utils/extract_repair/`

## Liens vers la documentation connexe

- [Documentation des outils rhétoriques](../../docs/outils/README.md)
- [Utilitaires de réparation d'extraits](../utils/extract_repair/README.md)