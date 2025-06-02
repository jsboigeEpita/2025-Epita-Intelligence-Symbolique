# 📈 Résultats des Analyses (`results/`)

Ce répertoire est destiné à stocker les résultats générés par les différentes analyses effectuées par le système d'analyse argumentative.

[Retour au README Principal](../README.md)

## Contenu Typique

Ce dossier peut contenir :

-   Des fichiers JSON ou CSV avec les arguments extraits, les sophismes identifiés, les évaluations de validité, etc.
-   Des rapports d'analyse synthétisant les découvertes.
-   Des visualisations (graphiques, diagrammes) des structures argumentatives.
-   Des logs détaillés des exécutions d'analyse spécifiques.

## Organisation

Il est recommandé d'organiser les résultats dans des sous-dossiers nommés de manière explicite, par exemple en fonction de :

-   La date de l'analyse.
-   Le nom du corpus ou du texte analysé.
-   Le type d'analyse effectuée.

Exemple :

```
results/
├── analyse_discours_politique_20250522/
│   ├── arguments.json
│   ├── sophismes.csv
│   └── rapport_synthese.md
└── tests_performance_corpus_scientifique/
    └── performance_metrics.json
```

**Note importante :** Par défaut, les fichiers générés dans ce répertoire ne sont pas versionnés (ajoutés au `.gitignore`) pour éviter d'encombrer le dépôt avec des données volumineuses ou spécifiques à une exécution. Si certains résultats sont jugés importants à conserver et à partager, ils peuvent être explicitement ajoutés au suivi Git.