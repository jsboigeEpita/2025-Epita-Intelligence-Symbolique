#!/usr/bin/env pwsh
<#
.SYNOPSIS
Script d'exécution des tests (refactorisé avec Python)

.DESCRIPTION
Lance les tests via le module Python mutualisé test_runner.py

.PARAMETER TestPath
Chemin des tests à exécuter

.PARAMETER Verbose
Mode verbeux

.PARAMETER Fast
Mode rapide

.EXAMPLE
.\run_tests.ps1 -TestPath "tests/unit" -Verbose
.\run_tests.ps1 -Fast

.NOTES
Refactorisé - Utilise scripts/core/test_runner.py
#>

param(
    [string]$TestPath = "tests/unit",
    [switch]$Verbose,
    [switch]$Fast
)

# Configuration
$ProjectRoot = $PSScriptRoot
$TestModule = "scripts/core/test_runner.py"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor $color
}

try {
    Write-Log "Exécution des tests via module Python mutualisé..."
    
    # Construction des arguments Python
    $pythonArgs = @("python", $TestModule)
    
    if ($Fast) { $pythonArgs += "--fast" }
    if ($Verbose) { $pythonArgs += "--verbose" }
    
    Write-Log "Commande: python $TestModule $(if($Fast){'--fast'}) $(if($Verbose){'--verbose'})"
    
    # Exécution
    & $pythonArgs[0] $pythonArgs[1..($pythonArgs.Length-1)]
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Log "Tests exécutés avec succès" "SUCCESS"
    } else {
        Write-Log "Tests échoués (Code: $exitCode)" "ERROR"
    }
    
    exit $exitCode
    
} catch {
    Write-Log "Erreur: $($_.Exception.Message)" "ERROR"
    exit 1
}