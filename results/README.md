# Résultats d'analyse de textes

## À propos de ce dossier
Ce dossier contient les **résultats des analyses rhétoriques** effectuées sur différents corpus de textes. Il stocke les analyses, rapports, visualisations et comparaisons générés par le système.

## Distinction avec `argumentation_analysis/results/`
⚠️ **Note importante** : Ne pas confondre avec le dossier `argumentation_analysis/results/` qui contient les **résultats d'évaluation du système** lui-même (performance, précision, etc.).

| Ce dossier (`results/`) | Dossier `argumentation_analysis/results/` |
|-------------------------|-------------------------------------------|
| Résultats d'analyse de textes | Résultats d'évaluation du système |
| Analyses, rapports, visualisations | Tests de performance |
| Orienté vers le contenu analysé | Orienté vers les performances du système |

Ce répertoire contient les résultats des analyses rhétoriques effectuées sur différents corpus de textes. Il est organisé de manière à faciliter l'accès aux différents types de résultats et leur interprétation.

## Structure du Répertoire

`
results/
├── analyses/
│   ├── basic/          # Analyses effectuées par l'agent de base
│   └── advanced/       # Analyses effectuées par l'agent avancé
├── summaries/
│   ├── Débats_Lincoln-Douglas/  # Résumés des débats Lincoln-Douglas
│   └── Discours_Hitler/         # Résumés des discours d'Hitler
├── comparisons/
│   ├── metrics/        # Métriques de comparaison (CSV)
│   └── visualizations/ # Visualisations des comparaisons
├── reports/
│   ├── comprehensive/  # Rapports d'analyse complets
│   └── performance/    # Rapports de performance
├── visualizations/     # Visualisations globales
└── README.md           # Ce fichier
`

## Description des Dossiers

### analyses/
Contient les résultats bruts des analyses rhétoriques au format JSON, séparés par type d'agent (basic ou advanced).

### summaries/
Contient les résumés des analyses par corpus et par agent. Chaque fichier présente une synthèse des sophismes détectés dans un texte spécifique.

### comparisons/
Contient les comparaisons de performance entre les différents agents d'analyse rhétorique, incluant des métriques quantitatives et des visualisations.

### reports/
Contient les rapports de synthèse globaux et les rapports de performance détaillés.

### visualizations/
Contient les visualisations graphiques des analyses, permettant une compréhension visuelle des résultats.

## Guide d'Interprétation des Résultats

### Analyses Rhétoriques
Les analyses rhétoriques sont stockées au format JSON et contiennent les informations suivantes :
- **Type de sophisme** : Classification selon la taxonomie standard
- **Extrait de texte** : Le passage contenant le sophisme
- **Niveau de confiance** : Estimation de la certitude de la détection
- **Explication** : Description de la nature du sophisme et de son impact sur l'argument

### Résumés
Les résumés sont organisés par corpus et par agent. Ils fournissent une synthèse des sophismes détectés et des structures argumentatives identifiées dans chaque texte analysé.

### Comparaisons
Les comparaisons permettent d'évaluer les performances des différents agents d'analyse rhétorique. Elles incluent des métriques quantitatives et des visualisations graphiques.

## Maintenance

Pour maintenir ce répertoire organisé :
1. Placez les nouvelles analyses dans le dossier approprié selon le type d'agent
2. Organisez les nouveaux résumés par corpus
3. Mettez à jour les rapports de synthèse lorsque de nouvelles analyses sont effectuées
4. Conservez une nomenclature cohérente incluant la date (format YYYYMMDD) dans les noms de fichiers
