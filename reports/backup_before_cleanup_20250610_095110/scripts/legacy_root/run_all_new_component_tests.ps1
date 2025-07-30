# Script PowerShell pour Validation des Nouveaux Composants
# ========================================================
#
# Version PowerShell native du script de validation master
# Compatible Windows avec gestion d'environnements et permissions

param(
    [switch]$Authentic,
    [switch]$Verbose,
    [switch]$Fast,
    [string]$Component,
    [string]$Level = "all",
    [string]$Report,
    [string]$Output,
    [switch]$Help
)

# Configuration des couleurs
$Colors = @{
    Green = [ConsoleColor]::Green
    Red = [ConsoleColor]::Red
    Yellow = [ConsoleColor]::Yellow
    Blue = [ConsoleColor]::Blue
    Cyan = [ConsoleColor]::Cyan
    White = [ConsoleColor]::White
    Gray = [ConsoleColor]::Gray
}

function Write-ColoredOutput {
    param(
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::White
    )
    
    $previousColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $Color
    Write-Output $Message
    $Host.UI.RawUI.ForegroundColor = $previousColor
}

function Show-Help {
    Write-Host @"
Orchestrateur Master de Validation des Nouveaux Composants
========================================================

USAGE:
    .\run_all_new_component_tests.ps1 [OPTIONS]

OPTIONS:
    -Authentic          Mode authentique (composants reels, API, etc.)
    -Verbose           Affichage detaille
    -Fast              Tests unitaires rapides seulement
    -Component <name>  Executer un composant specifique
    -Level <level>     Niveau de tests (unit|integration|all)
    -Report <file>     Fichier de sortie pour le rapport JSON
    -Output <file>     Alias pour -Report
    -Help              Afficher cette aide

EXEMPLES:
    .\run_all_new_component_tests.ps1 -Authentic -Verbose
    .\run_all_new_component_tests.ps1 -Fast
    .\run_all_new_component_tests.ps1 -Component "TweetyErrorAnalyzer"
    .\run_all_new_component_tests.ps1 -Report "validation_report.json"

COMPOSANTS DISPONIBLES:
    - TweetyErrorAnalyzer
    - UnifiedConfig
    - FirstOrderLogicAgent
    - AuthenticitySystem
    - UnifiedOrchestrations
"@
}

function Test-Prerequisites {
    Write-ColoredOutput "[CHECK] Verification des prerequis..." $Colors.Blue
    
    $issues = @()
    
    # Test Python
    try {
        $pythonVersion = & python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            $issues += "Python non disponible"
        } else {
            Write-ColoredOutput "[OK] Python: $pythonVersion" $Colors.Green
        }
    } catch {
        $issues += "Python non disponible"
    }
    
    # Test pytest
    try {
        $pytestVersion = & python -m pytest --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            $issues += "pytest non disponible"
        } else {
            Write-ColoredOutput "[OK] pytest disponible" $Colors.Green
        }
    } catch {
        $issues += "pytest non disponible"
    }
    
    # Test configuration unifiee
    if (Test-Path "config\unified_config.py") {
        Write-ColoredOutput "[OK] Configuration unifiee trouvee" $Colors.Green
    } else {
        $issues += "Configuration unifiee manquante"
    }
    
    # Tests authentiques si requis
    if ($Authentic) {
        # Test cle API OpenAI
        if ($env:OPENAI_API_KEY) {
            Write-ColoredOutput "[OK] Cle API OpenAI configuree" $Colors.Green
        } else {
            $issues += "Cle API OpenAI manquante (variable OPENAI_API_KEY)"
        }
        
        # Test JAR Tweety
        if (Test-Path "libs\tweety.jar") {
            Write-ColoredOutput "[OK] JAR Tweety trouve" $Colors.Green
        } else {
            $issues += "JAR Tweety manquant (libs\tweety.jar)"
        }
        
        # Test taxonomie
        if (Test-Path "config\taxonomies") {
            Write-ColoredOutput "[OK] Taxonomie sophismes trouvee" $Colors.Green
        } else {
            $issues += "Taxonomie sophismes manquante"
        }
    }
    
    return $issues
}

function Invoke-PythonScript {
    Write-ColoredOutput "`n[RUN] Execution du script Python..." $Colors.Blue
    
    # Construction des arguments
    $pythonArgs = @("run_all_new_component_tests.py")
    
    if ($Authentic) { $pythonArgs += "--authentic" }
    if ($Verbose) { $pythonArgs += "--verbose" }
    if ($Fast) { $pythonArgs += "--fast" }
    if ($Component) { $pythonArgs += "--component", $Component }
    if ($Level -ne "all") { $pythonArgs += "--level", $Level }
    if ($Report) { $pythonArgs += "--report", $Report }
    if ($Output) { $pythonArgs += "--output", $Output }
    
    # Affichage de la commande si verbose
    if ($Verbose) {
        $commandStr = "python " + ($pythonArgs -join " ")
        Write-ColoredOutput "[CMD] Commande: $commandStr" $Colors.Gray
    }
    
    # Execution
    try {
        & python @pythonArgs
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0) {
            Write-ColoredOutput "`n[SUCCESS] Validation completee avec succes!" $Colors.Green
        } else {
            Write-ColoredOutput "`n[WARNING] Validation terminee avec des erreurs (code: $exitCode)" $Colors.Yellow
        }
        
        return $exitCode
    } catch {
        Write-ColoredOutput "`n[ERROR] Erreur lors de l'execution: $($_.Exception.Message)" $Colors.Red
        return 1
    }
}

function Main {
    # Affichage de l'aide si demande
    if ($Help) {
        Show-Help
        exit 0
    }
    
    # En-tete
    Write-ColoredOutput @"

[TEST] VALIDATION COMPLETE DES NOUVEAUX COMPOSANTS
============================================
PowerShell Edition - Windows Native
"@ $Colors.Blue
    
    # Informations de configuration
    Write-ColoredOutput "`n[CONFIG] CONFIGURATION:" $Colors.Cyan
    Write-ColoredOutput "Mode authentique: $(if ($Authentic) { 'OUI' } else { 'NON' })" $Colors.White
    Write-ColoredOutput "Mode verbose: $(if ($Verbose) { 'OUI' } else { 'NON' })" $Colors.White
    Write-ColoredOutput "Mode rapide: $(if ($Fast) { 'OUI' } else { 'NON' })" $Colors.White
    if ($Component) {
        Write-ColoredOutput "Composant: $Component" $Colors.White
    }
    Write-ColoredOutput "Niveau: $Level" $Colors.White
    
    # Verification des prerequis
    $issues = Test-Prerequisites
    
    if ($issues.Count -gt 0) {
        Write-ColoredOutput "`n[ERROR] PREREQUIS MANQUANTS:" $Colors.Red
        foreach ($issue in $issues) {
            Write-ColoredOutput "  - $issue" $Colors.Red
        }
        
        if (-not $Authentic) {
            Write-ColoredOutput "`n[INFO] Passage en mode degrade possible" $Colors.Yellow
        } else {
            Write-ColoredOutput "`n[ERROR] Impossible de continuer en mode authentique" $Colors.Red
            exit 1
        }
    }
    
    # Verification de l'existence du script Python
    if (-not (Test-Path "run_all_new_component_tests.py")) {
        Write-ColoredOutput "`n[ERROR] Script Python principal introuvable!" $Colors.Red
        Write-ColoredOutput "Assurez-vous que run_all_new_component_tests.py est present." $Colors.Red
        exit 1
    }
    
    # Execution du script Python
    $exitCode = Invoke-PythonScript
    
    # Rapport final
    Write-ColoredOutput "`n[REPORT] RAPPORT FINAL:" $Colors.Blue
    if ($exitCode -eq 0) {
        Write-ColoredOutput "[OK] Tous les tests sont passes avec succes" $Colors.Green
        Write-ColoredOutput "[READY] Systeme pret pour la production" $Colors.Green
    } else {
        Write-ColoredOutput "[FAIL] Des erreurs ont ete detectees" $Colors.Red
        Write-ColoredOutput "[CHECK] Verifiez les logs pour plus de details" $Colors.Yellow
    }
    
    # Information sur les rapports
    if ($Report -or $Output) {
        $reportFile = if ($Report) { $Report } else { $Output }
        if (Test-Path $reportFile) {
            Write-ColoredOutput "[FILE] Rapport JSON disponible: $reportFile" $Colors.Cyan
        }
    }
    
    exit $exitCode
}

# Point d'entree
try {
    Main
} catch {
    Write-ColoredOutput "`n[CRITICAL] ERREUR CRITIQUE: $($_.Exception.Message)" $Colors.Red
    if ($Verbose) {
        Write-ColoredOutput "`nDetails de l'erreur:" $Colors.Gray
        Write-ColoredOutput $_.Exception.ToString() $Colors.Gray
    }
    exit 1
}
