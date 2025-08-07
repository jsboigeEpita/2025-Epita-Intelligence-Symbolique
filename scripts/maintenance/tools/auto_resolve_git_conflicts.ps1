#!/usr/bin/env pwsh
# Script automatique de resolution des conflits Git par deduplication
# Resout automatiquement les conflits qui sont des duplications completes

param(
    [Parameter(HelpMessage="Mode d'execution")]
    [ValidateSet("preview", "execute")]
    [string]$Mode = "preview",
    
    [Parameter(HelpMessage="Forcer le traitement sans confirmation")]
    [switch]$Force
)

# Couleurs pour l'affichage
$Colors = @{
    Green = "`e[92m"
    Red = "`e[91m" 
    Yellow = "`e[93m"
    Blue = "`e[94m"
    Reset = "`e[0m"
    Bold = "`e[1m"
}

function Write-Status($Message, $Color = "Blue") {
    Write-Host "$($Colors[$Color])[$($Color.ToUpper())] $Message$($Colors.Reset)"
}

function Find-ConflictFiles {
    """Trouve tous les fichiers avec des marqueurs de conflit Git"""
    Write-Status "Recherche des fichiers avec marqueurs de conflit..." "Blue"
    
    $conflictFiles = @()
    
    # Recherche recursive des marqueurs de conflit
    $searchResult = Select-String -Path "." -Pattern "^<<<<<<< " -Recurse -Include "*.py", "*.ps1", "*.md", "*.txt", "*.json" -ErrorAction SilentlyContinue
    
    foreach ($match in $searchResult) {
        $filePath = $match.Filename
        if ($conflictFiles -notcontains $filePath) {
            $conflictFiles += $filePath
        }
    }
    
    Write-Status "Trouve $($conflictFiles.Count) fichiers avec conflits" "Yellow"
    
    return $conflictFiles
}

function Test-CompleteDuplicate($FilePath) {
    """Teste si le conflit est une duplication complete"""
    $content = Get-Content $FilePath -Raw -Encoding UTF8
    
    # Extraire les sections MAIN et BACKUP
    $mainStart = $content.IndexOf("<<<<<<< MAIN")
    $separator = $content.IndexOf("=======")
    $backupEnd = $content.IndexOf(">>>>>>> BACKUP")
    
    if ($mainStart -eq -1 -or $separator -eq -1 -or $backupEnd -eq -1) {
        return $false
    }
    
    # Extraire le contenu MAIN (sans les marqueurs)
    $mainContent = $content.Substring($mainStart + "<<<<<<< MAIN".Length, $separator - $mainStart - "<<<<<<< MAIN".Length).Trim()
    
    # Extraire le contenu BACKUP (sans les marqueurs)
    $backupStartPos = $separator + "=======".Length
    $backupContent = $content.Substring($backupStartPos, $backupEnd - $backupStartPos).Trim()
    
    # Comparer les contenus (en ignorant les differences d'espacement mineures)
    $mainNormalized = $mainContent -replace '\r\n', "`n" -replace '\s+', ' '
    $backupNormalized = $backupContent -replace '\r\n', "`n" -replace '\s+', ' '
    
    return $mainNormalized -eq $backupNormalized
}

function Resolve-DuplicateConflict($FilePath) {
    """Resout un conflit de duplication en gardant seulement la section MAIN"""
    $content = Get-Content $FilePath -Raw -Encoding UTF8
    
    # Trouver les positions des marqueurs
    $mainStart = $content.IndexOf("<<<<<<< MAIN")
    $separator = $content.IndexOf("=======")
    $backupEnd = $content.IndexOf(">>>>>>> BACKUP")
    
    if ($mainStart -eq -1 -or $separator -eq -1 -or $backupEnd -eq -1) {
        throw "Marqueurs de conflit non trouves dans $FilePath"
    }
    
    # Extraire les parties avant, pendant et apres le conflit
    $beforeConflict = $content.Substring(0, $mainStart)
    $mainContent = $content.Substring($mainStart + "<<<<<<< MAIN".Length, $separator - $mainStart - "<<<<<<< MAIN".Length)
    $afterConflict = $content.Substring($backupEnd + ">>>>>>> BACKUP".Length)
    
    # Reconstituer le fichier sans les marqueurs de conflit
    $resolvedContent = $beforeConflict + $mainContent + $afterConflict
    
    # Nettoyer les lignes vides en trop au debut
    $resolvedContent = $resolvedContent -replace '^(\r?\n)+', ''
    
    return $resolvedContent
}

function Get-FileStats($FilePath) {
    """Obtient les statistiques du fichier (lignes avant/apres)"""
    $originalContent = Get-Content $FilePath -Raw -Encoding UTF8
    $originalLines = ($originalContent -split "`n").Length
    
    $resolvedContent = Resolve-DuplicateConflict $FilePath
    $resolvedLines = ($resolvedContent -split "`n").Length
    
    return @{
        OriginalLines = $originalLines
        ResolvedLines = $resolvedLines
        LinesSaved = $originalLines - $resolvedLines
    }
}

# ===== EXECUTION PRINCIPALE =====

Write-Host "$($Colors.Bold)$($Colors.Blue)================================$($Colors.Reset)"
Write-Host "$($Colors.Bold)$($Colors.Blue)AUTO-RESOLUTION CONFLITS GIT$($Colors.Reset)"
Write-Host "$($Colors.Bold)$($Colors.Blue)================================$($Colors.Reset)"
Write-Host ""

# 1. Trouver les fichiers en conflit
$conflictFiles = Find-ConflictFiles

if ($conflictFiles.Count -eq 0) {
    Write-Status "Aucun conflit Git detecte" "Green"
    exit 0
}

# 2. Analyser chaque fichier
$duplicateFiles = @()
$nonDuplicateFiles = @()
$totalLinesSaved = 0

Write-Status "Analyse des conflits..." "Blue"

foreach ($file in $conflictFiles) {
    try {
        $isDuplicate = Test-CompleteDuplicate $file
        
        if ($isDuplicate) {
            $stats = Get-FileStats $file
            $duplicateFiles += @{
                Path = $file
                Stats = $stats
            }
            $totalLinesSaved += $stats.LinesSaved
            Write-Status "$file - DUPLICATION ($($stats.LinesSaved) lignes a sauver)" "Green"
        } else {
            $nonDuplicateFiles += $file
            Write-Status "$file - CONFLIT COMPLEXE (fusion manuelle requise)" "Yellow"
        }
    } catch {
        Write-Status "$file - ERREUR: $_" "Red"
        $nonDuplicateFiles += $file
    }
}

# 3. Rapport d'analyse
Write-Host ""
Write-Status "RAPPORT D'ANALYSE" "Blue"
Write-Host "   - Fichiers avec duplications: $($duplicateFiles.Count)"
Write-Host "   - Fichiers avec conflits complexes: $($nonDuplicateFiles.Count)"
Write-Host "   - Lignes totales a economiser: $totalLinesSaved"

if ($duplicateFiles.Count -eq 0) {
    Write-Status "Aucun conflit de duplication detecte" "Red"
    exit 1
}

# 4. Mode preview ou execution
if ($Mode -eq "preview") {
    Write-Host ""
    Write-Status "MODE PREVIEW - Aucune modification" "Blue"
    Write-Host ""
    
    foreach ($fileInfo in $duplicateFiles) {
        Write-Host "   - $($fileInfo.Path)"
        Write-Host "      Lignes: $($fileInfo.Stats.OriginalLines) -> $($fileInfo.Stats.ResolvedLines) (-$($fileInfo.Stats.LinesSaved))"
    }
    
    Write-Host ""
    Write-Status "Pour appliquer les corrections:" "Yellow"
    Write-Host "   .\scripts\maintenance\auto_resolve_git_conflicts.ps1 -Mode execute"
    
} elseif ($Mode -eq "execute") {
    if (-not $Force) {
        Write-Host ""
        Write-Host "$($Colors.Yellow)Pret a resoudre $($duplicateFiles.Count) conflits de duplication.$($Colors.Reset)"
        $confirmation = Read-Host "Continuer? (y/N)"
        if ($confirmation -notmatch "^[yY]") {
            Write-Status "Annule par l'utilisateur" "Red"
            exit 1
        }
    }
    
    Write-Status "RESOLUTION EN COURS..." "Blue"
    $successCount = 0
    
    foreach ($fileInfo in $duplicateFiles) {
        try {
            $resolvedContent = Resolve-DuplicateConflict $fileInfo.Path
            Set-Content -Path $fileInfo.Path -Value $resolvedContent -Encoding UTF8 -NoNewline
            Write-Status "$($fileInfo.Path) - RESOLU" "Green"
            $successCount++
        } catch {
            Write-Status "$($fileInfo.Path) - ECHEC: $_" "Red"
        }
    }
    
    Write-Host ""
    Write-Status "RESULTATS" "Blue"
    Write-Host "   - Fichiers resolus: $successCount/$($duplicateFiles.Count)"
    Write-Host "   - Lignes economisees: $totalLinesSaved"
    
    if ($successCount -eq $duplicateFiles.Count) {
        Write-Status "TOUS LES CONFLITS DE DUPLICATION RESOLUS" "Green"
        
        Write-Host ""
        Write-Status "Prochaines etapes recommandees:" "Yellow"
        Write-Host "   1. git add ."
        Write-Host "   2. git commit -m 'Resolution automatique conflits duplications'"
        
        if ($nonDuplicateFiles.Count -gt 0) {
            Write-Host ""
            Write-Status "Conflits complexes restants:" "Yellow"
            foreach ($file in $nonDuplicateFiles) {
                Write-Host "   - $file"
            }
        }
    } else {
        Write-Status "RESOLUTION PARTIELLE" "Yellow"
    }
}

Write-Host ""
Write-Host "$($Colors.Bold)$($Colors.Blue)================================$($Colors.Reset)"