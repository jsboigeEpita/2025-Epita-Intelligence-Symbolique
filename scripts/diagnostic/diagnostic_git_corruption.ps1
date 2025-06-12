#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-

<#
.SYNOPSIS
    Script de diagnostic et correction de corruption Git avec dépôt distant

.DESCRIPTION
    Ce script effectue un diagnostic complet de l'état Git local,
    détecte les corruptions, fait un diff avec le dépôt distant,
    et propose des solutions de réparation automatiques.

.PARAMETER Force
    Force les opérations de réparation sans demander confirmation

.PARAMETER Remote
    Nom du remote à utiliser (par défaut: origin)

.PARAMETER Branch
    Nom de la branche à analyser (par défaut: main)

.EXAMPLE
    .\diagnostic_git_corruption.ps1
    .\diagnostic_git_corruption.ps1 -Force -Remote origin -Branch main
#>

param(
    [switch]$Force = $false,
    [string]$Remote = "origin",
    [string]$Branch = "main"
)

# Configuration
$ErrorActionPreference = "Continue"
$InformationPreference = "Continue"

# Couleurs pour l'affichage
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

function Get-GitRepoInfo {
    $info = @{
        HasGitRepo = Test-Path ".git"
        GitVersion = $null
        RepoSize = 0
        Corrupted = $false
        Remotes = @()
        CurrentBranch = $null
        Status = @()
    }
    
    if ($info.HasGitRepo) {
        try {
            $info.RepoSize = (Get-ChildItem ".git" -Recurse -ErrorAction SilentlyContinue | 
                            Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
        } catch {
            $info.RepoSize = 0
        }
    }
    
    # Test version Git
    $gitVersionTest = Test-GitCommand "--version"
    if ($gitVersionTest.Success) {
        $info.GitVersion = $gitVersionTest.Output
    }
    
    # Test remotes
    $remotesTest = Test-GitCommand "remote -v"
    if ($remotesTest.Success) {
        $info.Remotes = $remotesTest.Output -split "`n" | Where-Object { $_ -ne "" }
    }
    
    # Test branche actuelle
    $branchTest = Test-GitCommand "branch --show-current"
    if ($branchTest.Success) {
        $info.CurrentBranch = $branchTest.Output.Trim()
    }
    
    # Test status
    $statusTest = Test-GitCommand "status --porcelain"
    if ($statusTest.Success) {
        $info.Status = $statusTest.Output -split "`n" | Where-Object { $_ -ne "" }
    } else {
        $info.Corrupted = $true
    }
    
    return $info
}

function Get-RemoteDiff {
    param(
        [string]$Remote,
        [string]$Branch
    )
    
    Write-SubSection "Fetch du dépôt distant"
    $fetchResult = Test-GitCommand "fetch $Remote --all"
    if (-not $fetchResult.Success) {
        Write-ColorHost "❌ Échec du fetch: $($fetchResult.Error)" "Red"
        return $null
    }
    Write-ColorHost "✓ Fetch réussi" "Green"
    
    Write-SubSection "Comparaison avec $Remote/$Branch"
    
    # Vérification existence de la branche distante
    $remoteBranchTest = Test-GitCommand "rev-parse --verify $Remote/$Branch"
    if (-not $remoteBranchTest.Success) {
        Write-ColorHost "❌ Branche $Remote/$Branch n'existe pas" "Red"
        return $null
    }
    
    # Diff des fichiers
    $diffFilesResult = Test-GitCommand "diff --name-only HEAD $Remote/$Branch"
    $diffStats = Test-GitCommand "diff --stat HEAD $Remote/$Branch"
    
    $diffInfo = @{
        FilesChanged = @()
        Stats = $null
        LocalCommits = @()
        RemoteCommits = @()
    }
    
    if ($diffFilesResult.Success) {
        $diffInfo.FilesChanged = $diffFilesResult.Output -split "`n" | Where-Object { $_ -ne "" }
    }
    
    if ($diffStats.Success) {
        $diffInfo.Stats = $diffStats.Output
    }
    
    # Commits locaux non poussés
    $localCommitsResult = Test-GitCommand "log --oneline $Remote/$Branch..HEAD"
    if ($localCommitsResult.Success) {
        $diffInfo.LocalCommits = $localCommitsResult.Output -split "`n" | Where-Object { $_ -ne "" }
    }
    
    # Commits distants non récupérés
    $remoteCommitsResult = Test-GitCommand "log --oneline HEAD..$Remote/$Branch"
    if ($remoteCommitsResult.Success) {
        $diffInfo.RemoteCommits = $remoteCommitsResult.Output -split "`n" | Where-Object { $_ -ne "" }
    }
    
    return $diffInfo
}

function Repair-GitRepo {
    param(
        [string]$Remote,
        [string]$Branch,
        [bool]$Force
    )
    
    Write-Section "TENTATIVE DE RÉPARATION DU DÉPÔT GIT"
    
    # Vérification intégrité
    Write-SubSection "Vérification intégrité du dépôt"
    $fsckResult = Test-GitCommand "fsck --full"
    if (-not $fsckResult.Success) {
        Write-ColorHost "❌ Corruption détectée dans le dépôt:" "Red"
        Write-Host $fsckResult.Error
        
        if ($Force -or (Read-Host "Tenter une réparation automatique? (y/N)") -eq "y") {
            Write-SubSection "Réparation automatique"
            
            # Nettoyage du cache
            Test-GitCommand "gc --aggressive --prune=now"
            
            # Réindexation
            Test-GitCommand "reset --hard HEAD"
            
            # Test après réparation
            $fsckAfter = Test-GitCommand "fsck --full"
            if ($fsckAfter.Success) {
                Write-ColorHost "✓ Réparation réussie" "Green"
            } else {
                Write-ColorHost "❌ Réparation échouée" "Red"
                return $false
            }
        } else {
            return $false
        }
    } else {
        Write-ColorHost "✓ Intégrité du dépôt OK" "Green"
    }
    
    return $true
}

function Sync-WithRemote {
    param(
        [string]$Remote,
        [string]$Branch,
        [array]$FilesChanged,
        [bool]$Force
    )
    
    Write-Section "SYNCHRONISATION AVEC LE DÉPÔT DISTANT"
    
    if ($FilesChanged.Count -eq 0) {
        Write-ColorHost "✓ Aucune différence avec le dépôt distant" "Green"
        return $true
    }
    
    Write-ColorHost "📁 Fichiers différents du dépôt distant:" "Orange"
    $FilesChanged | ForEach-Object { Write-Host "  $_" }
    
    if ($Force -or (Read-Host "Pousser les modifications vers le dépôt distant? (y/N)") -eq "y") {
        Write-SubSection "Ajout des fichiers modifiés"
        $addResult = Test-GitCommand "add -A"
        if (-not $addResult.Success) {
            Write-ColorHost "❌ Échec ajout des fichiers" "Red"
            return $false
        }
        
        Write-SubSection "Commit des modifications"
        $commitMessage = "Synchronisation forcée - Correction corruption Git $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        $commitResult = Test-GitCommand "commit -m `"$commitMessage`""
        if (-not $commitResult.Success) {
            Write-ColorHost "⚠️ Aucune modification à commiter ou échec commit" "Yellow"
        }
        
        Write-SubSection "Push vers $Remote/$Branch"
        $pushResult = Test-GitCommand "push $Remote $Branch --force-with-lease"
        if ($pushResult.Success) {
            Write-ColorHost "✓ Push réussi" "Green"
            return $true
        } else {
            Write-ColorHost "❌ Échec push: $($pushResult.Error)" "Red"
            
            # Tentative push force
            if ($Force -or (Read-Host "Tenter un push forcé? (y/N)") -eq "y") {
                $forcePushResult = Test-GitCommand "push $Remote $Branch --force"
                if ($forcePushResult.Success) {
                    Write-ColorHost "✓ Push forcé réussi" "Green"
                    return $true
                } else {
                    Write-ColorHost "❌ Échec push forcé: $($forcePushResult.Error)" "Red"
                    return $false
                }
            }
            return $false
        }
    }
    
    return $true
}

function Show-Summary {
    param(
        [hashtable]$RepoInfo,
        [hashtable]$DiffInfo,
        [bool]$SyncSuccess
    )
    
    Write-Section "RÉSUMÉ DU DIAGNOSTIC"
    
    # État du dépôt
    Write-SubSection "État du dépôt Git"
    if ($RepoInfo.HasGitRepo) {
        Write-ColorHost "✓ Dépôt Git présent" "Green"
        Write-Host "  Taille: $([math]::Round($RepoInfo.RepoSize / 1MB, 2)) MB"
        Write-Host "  Branche: $($RepoInfo.CurrentBranch)"
        Write-Host "  Status: $($RepoInfo.Corrupted ? 'CORROMPU' : 'OK')" 
    } else {
        Write-ColorHost "❌ Aucun dépôt Git détecté" "Red"
    }
    
    # Remotes
    Write-SubSection "Remotes configurés"
    if ($RepoInfo.Remotes.Count -gt 0) {
        $RepoInfo.Remotes | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-ColorHost "❌ Aucun remote configuré" "Red"
    }
    
    # Différences avec le distant
    if ($DiffInfo) {
        Write-SubSection "Différences avec le dépôt distant"
        Write-Host "  Fichiers modifiés: $($DiffInfo.FilesChanged.Count)"
        Write-Host "  Commits locaux non poussés: $($DiffInfo.LocalCommits.Count)"
        Write-Host "  Commits distants non récupérés: $($DiffInfo.RemoteCommits.Count)"
    }
    
    # Résultat synchronisation
    Write-SubSection "Synchronisation"
    if ($SyncSuccess) {
        Write-ColorHost "✓ Synchronisation réussie" "Green"
    } else {
        Write-ColorHost "❌ Problèmes de synchronisation" "Red"
    }
}

# SCRIPT PRINCIPAL
function Main {
    Write-Section "DIAGNOSTIC CORRUPTION GIT ET SYNCHRONISATION DÉPÔT DISTANT"
    
    # 1. Diagnostic initial
    Write-Section "DIAGNOSTIC INITIAL"
    $repoInfo = Get-GitRepoInfo
    
    Write-SubSection "Informations Git"
    if ($repoInfo.GitVersion) {
        Write-ColorHost "✓ Git version: $($repoInfo.GitVersion)" "Green"
    } else {
        Write-ColorHost "❌ Git non accessible" "Red"
        exit 1
    }
    
    if (-not $repoInfo.HasGitRepo) {
        Write-ColorHost "❌ Aucun dépôt Git détecté dans le répertoire courant" "Red"
        if ($Force -or (Read-Host "Initialiser un nouveau dépôt Git? (y/N)") -eq "y") {
            $initResult = Test-GitCommand "init"
            if ($initResult.Success) {
                Write-ColorHost "✓ Dépôt Git initialisé" "Green"
                $repoInfo = Get-GitRepoInfo
            } else {
                Write-ColorHost "❌ Échec initialisation Git" "Red"
                exit 1
            }
        } else {
            exit 1
        }
    }
    
    Write-SubSection "État du dépôt local"
    Write-Host "Taille du dépôt: $([math]::Round($repoInfo.RepoSize / 1MB, 2)) MB"
    Write-Host "Branche actuelle: $($repoInfo.CurrentBranch ?? 'Aucune')"
    Write-Host "Fichiers modifiés: $($repoInfo.Status.Count)"
    
    if ($repoInfo.Corrupted) {
        Write-ColorHost "⚠️ Corruption détectée dans le dépôt" "Yellow"
        $repairSuccess = Repair-GitRepo -Remote $Remote -Branch $Branch -Force $Force
        if (-not $repairSuccess) {
            Write-ColorHost "❌ Impossible de réparer le dépôt" "Red"
            exit 1
        }
    }
    
    # 2. Analyse des remotes
    Write-Section "ANALYSE DES REMOTES"
    if ($repoInfo.Remotes.Count -eq 0) {
        Write-ColorHost "❌ Aucun remote configuré" "Red"
        $remoteUrl = Read-Host "URL du dépôt distant (optionnel)"
        if ($remoteUrl) {
            $addRemoteResult = Test-GitCommand "remote add $Remote $remoteUrl"
            if ($addRemoteResult.Success) {
                Write-ColorHost "✓ Remote $Remote ajouté" "Green"
            } else {
                Write-ColorHost "❌ Échec ajout remote" "Red"
            }
        }
    } else {
        Write-ColorHost "✓ Remotes configurés:" "Green"
        $repoInfo.Remotes | ForEach-Object { Write-Host "  $_" }
    }
    
    # 3. Diff avec le dépôt distant
    $diffInfo = $null
    $syncSuccess = $true
    
    if ($repoInfo.Remotes.Count -gt 0) {
        Write-Section "COMPARAISON AVEC LE DÉPÔT DISTANT"
        $diffInfo = Get-RemoteDiff -Remote $Remote -Branch $Branch
        
        if ($diffInfo) {
            Write-SubSection "Résultats de la comparaison"
            Write-Host "Fichiers modifiés localement: $($diffInfo.FilesChanged.Count)"
            Write-Host "Commits locaux non poussés: $($diffInfo.LocalCommits.Count)"
            Write-Host "Commits distants non récupérés: $($diffInfo.RemoteCommits.Count)"
            
            if ($diffInfo.FilesChanged.Count -gt 0) {
                Write-ColorHost "📁 Fichiers différents:" "Orange"
                $diffInfo.FilesChanged | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" }
                if ($diffInfo.FilesChanged.Count -gt 10) {
                    Write-Host "  ... et $($diffInfo.FilesChanged.Count - 10) autres"
                }
            }
            
            if ($diffInfo.Stats) {
                Write-SubSection "Statistiques des différences"
                Write-Host $diffInfo.Stats
            }
            
            # 4. Synchronisation
            $syncSuccess = Sync-WithRemote -Remote $Remote -Branch $Branch -FilesChanged $diffInfo.FilesChanged -Force $Force
        } else {
            Write-ColorHost "❌ Impossible de comparer avec le dépôt distant" "Red"
            $syncSuccess = $false
        }
    } else {
        Write-ColorHost "⚠️ Pas de remote configuré, synchronisation impossible" "Yellow"
        $syncSuccess = $false
    }
    
    # 5. Résumé final
    Show-Summary -RepoInfo $repoInfo -DiffInfo $diffInfo -SyncSuccess $syncSuccess
    
    # 6. Recommandations
    Write-Section "RECOMMANDATIONS"
    if (-not $syncSuccess) {
        Write-ColorHost "🔧 Actions recommandées:" "Yellow"
        Write-Host "  1. Vérifier la connectivité réseau"
        Write-Host "  2. Vérifier les permissions sur le dépôt distant"
        Write-Host "  3. Configurer correctement les remotes"
        Write-Host "  4. Relancer le script avec -Force pour forcer les opérations"
    } else {
        Write-ColorHost "✅ Dépôt Git synchronisé avec succès" "Green"
    }
    
    return $syncSuccess ? 0 : 1
}

# Exécution du script principal
exit (Main)