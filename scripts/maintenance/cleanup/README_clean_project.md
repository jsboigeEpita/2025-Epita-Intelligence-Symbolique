# Script de Nettoyage Global du Projet

Ce document explique comment utiliser le script `clean_project.ps1` pour effectuer un nettoyage global du projet d'analyse argumentative.

## Objectif

Le script effectue les opérations suivantes :

1. Identifie et supprime les fichiers temporaires ou redondants à la racine du projet
2. Fusionne les dossiers results/ en un seul dossier bien organisé
3. Classe les résultats par type d'analyse et par corpus
4. Crée une structure de dossiers claire et logique
5. Génère un fichier README.md pour le dossier results/ qui documente la structure et le contenu
6. Produit un rapport de nettoyage indiquant les actions effectuées

## Nouvelle Structure du Dossier results/

Le script réorganise le dossier results/ selon la structure suivante :

```
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
└── README.md           # Documentation de la structure
```

## Utilisation

Le script peut être exécuté avec différentes options :

### Mode Simulation (Dry Run)

Pour voir quelles actions seraient effectuées sans réellement les exécuter :

```powershell
.\scripts\cleanup\clean_project.ps1 -DryRun
```

### Mode Verbeux

Pour afficher des informations détaillées pendant l'exécution :

```powershell
.\scripts\cleanup\clean_project.ps1 -Verbose
```

### Mode Force

Pour exécuter le nettoyage sans demander de confirmation :

```powershell
.\scripts\cleanup\clean_project.ps1 -Force
```

### Combinaison d'options

Les options peuvent être combinées :

```powershell
.\scripts\cleanup\clean_project.ps1 -DryRun -Verbose
```

## Sauvegarde

Avant d'effectuer toute modification, le script crée automatiquement une sauvegarde du dossier results/ dans le dossier `_archives/backup_YYYYMMDD_HHMMSS/`. Cela permet de récupérer les fichiers originaux en cas de problème.

## Rapport de Nettoyage

À la fin de l'exécution, le script génère un rapport détaillé (`rapport_nettoyage_YYYYMMDD_HHMMSS.md`) qui liste toutes les actions effectuées et fournit des statistiques sur le nettoyage :

- Nombre de fichiers temporaires supprimés
- Nombre de fichiers déplacés
- Nombre de dossiers créés
- Nombre de dossiers supprimés

## Recommandations

Pour maintenir le projet propre et organisé :

1. Exécutez ce script périodiquement pour nettoyer les fichiers temporaires
2. Utilisez la nouvelle structure pour tous les futurs résultats d'analyse
3. Maintenez une nomenclature cohérente incluant la date dans les noms de fichiers
4. Mettez à jour régulièrement le README.md du dossier results/ lorsque de nouveaux types de résultats sont ajoutés

## Dépannage

Si vous rencontrez des problèmes lors de l'exécution du script :

1. Vérifiez que vous avez les droits d'administrateur pour exécuter des scripts PowerShell
2. Si nécessaire, modifiez la politique d'exécution : `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
3. En cas d'erreur, consultez le rapport de nettoyage pour identifier les actions qui ont échoué
4. Vous pouvez restaurer la sauvegarde depuis le dossier `_archives/` si nécessaire