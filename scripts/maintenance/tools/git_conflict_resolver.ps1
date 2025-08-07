#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-

<#
.SYNOPSIS
    Script avancé de résolution des conflits Git avec génération de marqueurs détaillés

.DESCRIPTION
    Ce script gère spécifiquement les conflits de merge Git en générant des marqueurs
    de conflit détaillés et des rapports de résolution pour faciliter la résolution manuelle.

.PARAMETER Remote
    Nom du remote à utiliser (par défaut: origin)

.PARAMETER Branch
    Nom de la branche à analyser (par défaut: main)

.PARAMETER Mode
    Mode de résolution: auto, manual, markers, report

.EXAMPLE
    .\git_conflict_resolver.ps1 -Mode markers
    .\git_conflict_resolver.ps1 -Remote origin -Branch main -Mode report
#>

param(
    [string]$Remote = "origin",
    [string]$Branch = "main",
    [ValidateSet("auto", "manual", "markers", "report")]
    [string]$Mode = "markers"
)

# Configuration
$ErrorActionPreference = "Continue"
$InformationPreference = "Continue"

function Write-ColorHost {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-ColorHost "=== $Title ===" "Cyan"
    Write-Host ""
}

function Write-SubSection {
    param([string]$Title)
    Write-ColorHost "--- $Title ---" "Yellow"
}

function Test-GitCommand {
    param([string]$Command)
    try {
        $result = Invoke-Expression "git $Command 2>&1"
        return @{
            Success = $LASTEXITCODE -eq 0
            Output = $result
            Error = if ($LASTEXITCODE -ne 0) { $result } else { $null }
        }
    } catch {
        return @{
            Success = $false
            Output = $null
            Error = $_.Exception.Message
        }
    }
}

function Get-ConflictInfo {
    param([string]$FilePath)
    
    if (-not (Test-Path $FilePath)) {
        return $null
    }
    
    $content = Get-Content $FilePath -Raw
    $lines = Get-Content $FilePath
    
    # Patterns pour détecter les marqueurs de conflit
    $startPattern = '^<{7} '
    $middlePattern = '^={7}$'
    $endPattern = '^>{7} '
    
    $conflicts = @()
    $currentConflict = $null
    $lineNumber = 0
    
    foreach ($line in $lines) {
        $lineNumber++
        
        if ($line -match $startPattern) {
            $currentConflict = @{
                StartLine = $lineNumber
                StartMarker = $line
                LocalContent = @()
                RemoteContent = @()
                EndLine = 0
                EndMarker = ""
                InLocalSection = $true
            }
        }
        elseif ($line -match $middlePattern -and $currentConflict) {
            $currentConflict.InLocalSection = $false
        }
        elseif ($line -match $endPattern -and $currentConflict) {
            $currentConflict.EndLine = $lineNumber
            $currentConflict.EndMarker = $line
            $conflicts += $currentConflict
            $currentConflict = $null
        }
        elseif ($currentConflict) {
            if ($currentConflict.InLocalSection) {
                $currentConflict.LocalContent += $line
            } else {
                $currentConflict.RemoteContent += $line
            }
        }
    }
    
    return $conflicts
}

function Get-ConflictFiles {
    $conflictResult = Test-GitCommand "diff --name-only --diff-filter=U"
    if ($conflictResult.Success -and $conflictResult.Output) {
        return $conflictResult.Output -split "`n" | Where-Object { $_ -ne "" }
    }
    return @()
}

function Create-ConflictBackup {
    param([string]$FilePath)
    
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $backupPath = "$FilePath.conflict_backup_$timestamp"
    Copy-Item $FilePath $backupPath -Force
    return $backupPath
}

function Generate-ConflictMarkers {
    param(
        [string]$FilePath,
        [array]$Conflicts
    )
    
    $lines = Get-Content $FilePath
    $newContent = @()
    $lineIndex = 0
    $conflictIndex = 0
    
    foreach ($line in $lines) {
        $lineIndex++
        
        # Vérifier si on est dans un conflit
        $currentConflict = $Conflicts | Where-Object { 
            $lineIndex -ge $_.StartLine -and $lineIndex -le $_.EndLine 
        } | Select-Object -First 1
        
        if ($currentConflict -and $lineIndex -eq $currentConflict.StartLine) {
            $conflictIndex++
            
            # Marqueur de début amélioré
            $newContent += "<<<<<<< HEAD (VERSION LOCALE - Conflit #$conflictIndex)"
            $newContent += "# CONFLIT #$conflictIndex DÉTECTÉ dans $FilePath"
            $newContent += "# Ligne $($currentConflict.StartLine)-$($currentConflict.EndLine)"
            $newContent += "# Choisir UNE des options ci-dessous:"
            $newContent += ""
            
            # Contenu local
            $newContent += "# OPTION 1: VERSION LOCALE (vos modifications)"
            foreach ($localLine in $currentConflict.LocalContent) {
                $newContent += $localLine
            }
            
            # Séparateur amélioré
            $newContent += ""
            $newContent += "# " + ("=" * 50)
            $newContent += "# SÉPARATEUR - NE PAS MODIFIER CETTE LIGNE"
            $newContent += "# " + ("=" * 50)
            $newContent += ""
            
            # Contenu distant
            $newContent += "# OPTION 2: VERSION DISTANTE (modifications du dépôt)"
            foreach ($remoteLine in $currentConflict.RemoteContent) {
                $newContent += $remoteLine
            }
            
            # Marqueur de fin amélioré
            $newContent += ""
            $newContent += "# OPTION 3: FUSION MANUELLE"
            $newContent += "# Combinez les deux versions ci-dessus selon vos besoins"
            $newContent += "# Puis supprimez TOUS les commentaires et marqueurs"
            $newContent += ">>>>>>> $Remote/$Branch (VERSION DISTANTE - $(Get-Date -Format 'HH:mm:ss'))"
            $newContent += ""
            
            # Ignorer les lignes du conflit original
            while ($lineIndex -le $currentConflict.EndLine -and $lineIndex -le $lines.Count) {
                $lineIndex++
            }
            $lineIndex-- # Ajustement pour la boucle
        }
        else {
            # Ligne normale, ajouter telle quelle
            $newContent += $line
        }
    }
    
    return $newContent
}

function Generate-ConflictReport {
    param(
        [array]$ConflictFiles,
        [hashtable]$FileConflicts
    )
    
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $reportPath = "scripts/conflict_report_$timestamp.md"
    
    $report = @"
# 🔥 RAPPORT DE RÉSOLUTION DES CONFLITS GIT

**Généré le :** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  
**Branche :** $Branch  
**Remote :** $Remote  
**Nombre de fichiers en conflit :** $($ConflictFiles.Count)

---

## 📋 RÉSUMÉ EXÉCUTIF

Les conflits détectés nécessitent une résolution manuelle. Ce rapport vous guide 
étape par étape pour résoudre chaque conflit de manière sûre et efficace.

### ⚡ ACTIONS RAPIDES

``````bash
# Voir l'état actuel
git status

# Annuler le merge si nécessaire
git merge --abort

# Après résolution, finaliser
git add .
git commit -m "Résolution conflits merge"
git push $Remote $Branch
``````

---

## 📁 FICHIERS EN CONFLIT

"@

    foreach ($file in $ConflictFiles) {
        $conflicts = $FileConflicts[$file]
        $backupFile = $file -replace '/', '_' -replace '\\', '_'
        
        $report += @"

### 📄 ``$file``

**Conflits détectés :** $($conflicts.Count)  
**Sauvegarde :** ``$file.conflict_backup_$timestamp``  
**État :** ⚠️ Résolution requise

"@
        
        for ($i = 0; $i -lt $conflicts.Count; $i++) {
            $conflict = $conflicts[$i]
            $localLines = $conflict.LocalContent -join "`n"
            $remoteLines = $conflict.RemoteContent -join "`n"
            
            $report += @"

#### 🔍 Conflit #$($i + 1) (Lignes $($conflict.StartLine)-$($conflict.EndLine))

**🏠 VOTRE VERSION (HEAD) :**
``````
$localLines
``````

**🌐 VERSION DISTANTE ($Remote/$Branch) :**
``````
$remoteLines
``````

**💡 RECOMMANDATIONS :**

1. **Garder votre version :** Si vos modifications sont plus récentes/correctes
2. **Adopter version distante :** Si elle corrige un bug ou améliore le code  
3. **Fusionner les deux :** Combiner les meilleures parties de chaque version

**🛠️ COMMANDES DE RÉSOLUTION :**

``````bash
# Option 1: Garder votre version
git checkout --ours "$file"
git add "$file"

# Option 2: Adopter version distante
git checkout --theirs "$file"  
git add "$file"

# Option 3: Édition manuelle (recommandé)
# 1. Ouvrir le fichier dans votre éditeur
# 2. Localiser les marqueurs de conflit améliorés
# 3. Choisir/combiner le code approprié
# 4. Supprimer tous les marqueurs et commentaires
# 5. Tester le code
# 6. git add "$file"
``````

---

"@
        }
    }
    
    $report += @"

## 🔧 GUIDE DE RÉSOLUTION ÉTAPE PAR ÉTAPE

### Étape 1 : Analyse
- Examinez chaque fichier en conflit listé ci-dessus
- Comprenez les différences entre les versions locale et distante
- Identifiez l'intention derrière chaque modification

### Étape 2 : Résolution
Pour chaque conflit :
1. Ouvrez le fichier dans votre éditeur de code
2. Localisez les marqueurs améliorés (``<<<<<<< HEAD``, ``========``, ``>>>>>>> $Remote/$Branch``)
3. Choisissez la résolution appropriée :
   - **Version locale** : Gardez le code entre ``<<<<<<< HEAD`` et ``========``
   - **Version distante** : Gardez le code entre ``========`` et ``>>>>>>> $Remote/$Branch``
   - **Fusion** : Combinez intelligemment les deux versions
4. Supprimez **TOUS** les marqueurs de conflit et commentaires
5. Testez votre code pour vous assurer qu'il fonctionne

### Étape 3 : Validation
``````bash
# Vérifier qu'aucun marqueur ne reste
grep -r "<<<<<<< \|======= \|>>>>>>> " .

# Tester votre code
# [Exécutez vos tests appropriés]

# Stagé les fichiers résolus
git add fichier_résolu.ext

# Vérifier l'état
git status
``````

### Étape 4 : Finalisation
``````bash
# Terminer le merge
git commit -m "Résolution conflits merge avec $Remote/$Branch"

# Pousser vers le dépôt distant
git push $Remote $Branch
``````

---

## 📚 RESSOURCES UTILES

### Outils de Merge Recommandés
- **VS Code :** Extensions GitLens, Git Graph
- **Outils externes :** Beyond Compare, KDiff3, Meld
- **Ligne de commande :** ``git mergetool``

### Commandes Git Utiles
``````bash
# Voir les différences détaillées
git diff HEAD

# Historique des commits
git log --oneline --graph -10

# Annuler la résolution et recommencer
git merge --abort
git reset --hard HEAD

# Utiliser un outil graphique
git mergetool

# Voir les branches
git branch -av
``````

---

## ⚠️ FICHIERS DE SAUVEGARDE

Les fichiers suivants ont été automatiquement sauvegardés :

$($ConflictFiles | ForEach-Object { "- ``$_.conflict_backup_$timestamp``" } | Out-String)

**🗑️ Nettoyage :** Ces sauvegardes seront supprimées automatiquement après une résolution réussie.

---

## 🆘 EN CAS DE PROBLÈME

Si vous rencontrez des difficultés :

1. **Sauvegardez votre travail** avant toute manipulation
2. **Utilisez les sauvegardes** générées automatiquement
3. **Consultez l'équipe** si les conflits sont complexes
4. **Relancez le script** après résolution partielle

**📞 Support :** Ce rapport a été généré automatiquement. 
Relancez ``.\git_conflict_resolver.ps1`` pour mettre à jour l'état.

---

*Rapport généré par Git Conflict Resolver - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')*
"@

    # Créer le répertoire scripts s'il n'existe pas
    if (-not (Test-Path "scripts")) {
        New-Item -ItemType Directory -Path "scripts" -Force | Out-Null
    }
    
    Set-Content -Path $reportPath -Value $report -Encoding UTF8
    return $reportPath
}

function Resolve-ConflictsWithMarkers {
    param([array]$ConflictFiles)
    
    Write-Section "GÉNÉRATION DE MARQUEURS DE CONFLIT AMÉLIORÉS"
    
    $fileConflicts = @{}
    $reportData = @{}
    
    foreach ($file in $ConflictFiles) {
        Write-ColorHost "🔍 Traitement de $file..." "Cyan"
        
        # Créer une sauvegarde
        $backupPath = Create-ConflictBackup -FilePath $file
        Write-Host "  💾 Sauvegarde : $backupPath"
        
        # Analyser les conflits
        $conflicts = Get-ConflictInfo -FilePath $file
        $fileConflicts[$file] = $conflicts
        
        if ($conflicts -and $conflicts.Count -gt 0) {
            Write-Host "  ⚠️ $($conflicts.Count) conflit(s) détecté(s)"
            
            # Générer les marqueurs améliorés
            $enhancedContent = Generate-ConflictMarkers -FilePath $file -Conflicts $conflicts
            Set-Content -Path $file -Value $enhancedContent -Encoding UTF8
            
            Write-ColorHost "  ✨ Marqueurs améliorés générés" "Green"
        } else {
            Write-ColorHost "  ✓ Aucun conflit dans ce fichier" "Green"
        }
    }
    
    # Générer le rapport détaillé
    $reportPath = Generate-ConflictReport -ConflictFiles $ConflictFiles -FileConflicts $fileConflicts
    
    Write-Section "RÉSUMÉ DE LA GÉNÉRATION"
    Write-ColorHost "📋 Rapport détaillé généré : $reportPath" "Green"
    Write-ColorHost "🔧 Fichiers avec marqueurs améliorés : $($ConflictFiles.Count)" "Cyan"
    Write-ColorHost "💾 Sauvegardes créées pour tous les fichiers" "Yellow"
    
    Write-Host ""
    Write-ColorHost "📖 PROCHAINES ÉTAPES :" "Yellow"
    Write-Host "  1. Consultez le rapport : $reportPath"
    Write-Host "  2. Éditez chaque fichier pour résoudre les conflits"
    Write-Host "  3. Supprimez tous les marqueurs et commentaires"
    Write-Host "  4. Testez votre code"
    Write-Host "  5. Relancez ce script en mode 'report' pour vérifier"
    
    return @{
        ReportPath = $reportPath
        FilesProcessed = $ConflictFiles.Count
        ConflictsDetected = ($fileConflicts.Values | Measure-Object -Sum | Select-Object -ExpandProperty Sum)
    }
}

function Check-ConflictResolution {
    Write-Section "VÉRIFICATION DE LA RÉSOLUTION DES CONFLITS"
    
    $conflictFiles = Get-ConflictFiles
    
    if ($conflictFiles.Count -eq 0) {
        Write-ColorHost "✅ Aucun conflit de merge détecté" "Green"
        return $true
    }
    
    Write-ColorHost "⚠️ Conflits encore présents dans $($conflictFiles.Count) fichier(s) :" "Yellow"
    
    foreach ($file in $conflictFiles) {
        Write-Host "  📄 $file"
        
        # Vérifier les marqueurs restants
        $content = Get-Content $file -Raw
        $markerCount = ([regex]::Matches($content, '<<<<<<< |======= |>>>>>>> ')).Count
        
        if ($markerCount -gt 0) {
            Write-ColorHost "    ❌ $markerCount marqueur(s) de conflit détecté(s)" "Red"
        } else {
            Write-ColorHost "    ✓ Aucun marqueur, fichier peut être stagé" "Green"
        }
    }
    
    return $false
}

# FONCTION PRINCIPALE
function Main {
    Write-Section "GIT CONFLICT RESOLVER - GESTIONNAIRE DE CONFLITS AVANCÉ"
    
    Write-ColorHost "Mode sélectionné : $Mode" "Cyan"
    Write-ColorHost "Remote : $Remote" "Cyan" 
    Write-ColorHost "Branche : $Branch" "Cyan"
    
    switch ($Mode) {
        "auto" {
            Write-Section "RÉSOLUTION AUTOMATIQUE"
            $conflictFiles = Get-ConflictFiles
            
            if ($conflictFiles.Count -eq 0) {
                Write-ColorHost "✅ Aucun conflit détecté" "Green"
                return 0
            }
            
            Write-ColorHost "⚠️ Résolution automatique (garder version locale)..." "Yellow"
            foreach ($file in $conflictFiles) {
                $result = Test-GitCommand "checkout --ours `"$file`""
                if ($result.Success) {
                    Test-GitCommand "add `"$file`""
                    Write-ColorHost "✓ $file résolu automatiquement" "Green"
                } else {
                    Write-ColorHost "❌ Échec résolution $file" "Red"
                }
            }
        }
        
        "manual" {
            Write-Section "RÉSOLUTION MANUELLE"
            $conflictFiles = Get-ConflictFiles
            
            if ($conflictFiles.Count -eq 0) {
                Write-ColorHost "✅ Aucun conflit détecté" "Green"
                return 0
            }
            
            Write-ColorHost "🔧 Fichiers à résoudre manuellement :" "Yellow"
            $conflictFiles | ForEach-Object { Write-Host "  - $_" }
            
            Write-Host ""
            Write-Host "Résolvez les conflits puis appuyez sur Entrée..."
            Read-Host
            
            Check-ConflictResolution
        }
        
        "markers" {
            $conflictFiles = Get-ConflictFiles
            
            if ($conflictFiles.Count -eq 0) {
                Write-ColorHost "✅ Aucun conflit détecté" "Green"
                return 0
            }
            
            $result = Resolve-ConflictsWithMarkers -ConflictFiles $conflictFiles
            Write-ColorHost "🎯 Traitement terminé : $($result.FilesProcessed) fichiers, $($result.ConflictsDetected) conflits" "Green"
        }
        
        "report" {
            Write-Section "RAPPORT D'ÉTAT DES CONFLITS"
            $hasConflicts = -not (Check-ConflictResolution)
            
            if (-not $hasConflicts) {
                Write-ColorHost "🎉 Tous les conflits semblent résolus !" "Green"
                Write-Host ""
                Write-Host "Commandes pour finaliser :"
                Write-Host "  git add ."
                Write-Host "  git commit -m 'Résolution conflits merge'"
                Write-Host "  git push $Remote $Branch"
            }
        }
    }
    
    return 0
}

# Exécution
exit (Main)
