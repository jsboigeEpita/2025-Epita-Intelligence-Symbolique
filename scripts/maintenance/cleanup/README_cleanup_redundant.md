# Scripts de Nettoyage et Suppression des Fichiers Redondants

Ce document explique comment utiliser les scripts `clean_project.ps1` et `cleanup_redundant_files.ps1` pour effectuer un nettoyage complet du projet d'analyse argumentative.

## Vue d'ensemble

Le processus de nettoyage se déroule en deux étapes:

1. **Réorganisation des fichiers** (`clean_project.ps1`): Déplace les fichiers vers une structure organisée
2. **Suppression des fichiers redondants** (`cleanup_redundant_files.ps1`): Supprime les fichiers d'origine après vérification

## Étape 1: Réorganisation des fichiers

Le script `clean_project.ps1` déplace les fichiers vers une structure organisée:

```powershell
.\scripts\cleanup\clean_project.ps1 [-DryRun] [-Verbose] [-Force]
```

### Options:
- `-DryRun`: Affiche les actions sans les exécuter
- `-Verbose`: Affiche des informations détaillées
- `-Force`: Exécute le nettoyage sans demander de confirmation

Ce script:
- Crée une sauvegarde du dossier results/ dans _archives/
- Supprime les fichiers temporaires
- Crée une structure de dossiers organisée
- Déplace les fichiers vers cette nouvelle structure
- Génère un README.md pour le dossier results/
- Produit un rapport de nettoyage

## Étape 2: Suppression des fichiers redondants

Une fois que vous avez vérifié que la réorganisation s'est bien déroulée, vous pouvez supprimer les fichiers redondants avec:

```powershell
.\scripts\cleanup\cleanup_redundant_files.ps1 [-DryRun] [-Verbose] [-Force]
```

### Options:
- `-DryRun`: Affiche les actions sans les exécuter
- `-Verbose`: Affiche des informations détaillées
- `-Force`: Exécute la suppression sans demander de confirmation

Ce script:
1. Identifie tous les fichiers qui ont été déplacés vers la nouvelle structure
2. Vérifie que ces fichiers existent bien dans la nouvelle structure (comparaison par hash)
3. Supprime les fichiers originaux et les anciens dossiers vides
4. Génère un rapport des suppressions effectuées

## Flux de travail recommandé

Pour un nettoyage complet et sécurisé:

1. **Exécutez d'abord en mode simulation**:
   ```powershell
   .\scripts\cleanup\clean_project.ps1 -DryRun -Verbose
   ```

2. **Réorganisez les fichiers**:
   ```powershell
   .\scripts\cleanup\clean_project.ps1 -Verbose
   ```

3. **Vérifiez la nouvelle structure** pour vous assurer que tout est correct

4. **Simulez la suppression des fichiers redondants**:
   ```powershell
   .\scripts\cleanup\cleanup_redundant_files.ps1 -DryRun -Verbose
   ```

5. **Supprimez les fichiers redondants**:
   ```powershell
   .\scripts\cleanup\cleanup_redundant_files.ps1 -Verbose
   ```

## Sécurité et récupération

- Une sauvegarde est automatiquement créée dans `_archives/backup_YYYYMMDD_HHMMSS/`
- Les deux scripts génèrent des rapports détaillés
- Le mode `-DryRun` permet de prévisualiser les actions
- La vérification par hash garantit que seuls les fichiers correctement déplacés sont supprimés

## Dépannage

Si vous rencontrez des problèmes:

1. Consultez les rapports générés pour identifier les erreurs
2. Utilisez l'option `-Verbose` pour obtenir plus de détails
3. Restaurez la sauvegarde depuis le dossier `_archives/` si nécessaire
4. Vérifiez les permissions d'accès aux fichiers

## Maintenance régulière

Pour maintenir le projet propre:

1. Exécutez périodiquement `clean_project.ps1` pour organiser les nouveaux fichiers
2. Utilisez `cleanup_redundant_files.ps1` après chaque réorganisation
3. Suivez la structure de dossiers établie pour tous les nouveaux résultats