#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-

<#
.SYNOPSIS
Tests PowerShell pour l'intégration CLI du système de configuration unifié.

.DESCRIPTION
Ce script teste l'interface ligne de commande analyze_text.py avec les nouvelles
options de configuration dynamique, incluant :
- Tests des arguments CLI (--logic-type, --mock-level, etc.)
- Validation des combinaisons de paramètres
- Tests de bout en bout avec différentes configurations
- Validation des sorties et rapports

.EXAMPLE
.\test_unified_config_cli.ps1
Exécute tous les tests CLI

.EXAMPLE  
.\test_unified_config_cli.ps1 -TestSuite "Basic"
Exécute uniquement les tests de base
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("All", "Basic", "Advanced", "Integration", "Performance")]
    [string]$TestSuite = "All",
    
    [Parameter(Mandatory=$false)]
    [switch]$Verbose,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipSlowTests,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "test_results"
)

# Configuration
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$AnalyzeScript = Join-Path $ProjectRoot "scripts/main/analyze_text.py"
$TestOutputDir = Join-Path $ProjectRoot $OutputDir

# Couleurs pour l'affichage
$Colors = @{
    Success = "Green"
    Warning = "Yellow" 
    Error = "Red"
    Info = "Cyan"
    Test = "Blue"
}

# Fonction d'affichage coloré
function Write-ColoredOutput {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [string]$Type = "Info"
    )
    
    $Color = $Colors[$Type]
    Write-Host $Message -ForegroundColor $Color
}

# Fonction pour exécuter un test CLI
function Invoke-CLITest {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TestName,
        
        [Parameter(Mandatory=$true)]
        [string[]]$Arguments,
        
        [Parameter(Mandatory=$false)]
        [bool]$ShouldSucceed = $true,
        
        [Parameter(Mandatory=$false)]
        [string]$ExpectedOutput,
        
        [Parameter(Mandatory=$false)]
        [hashtable]$ExpectedConfig
    )
    
    Write-ColoredOutput "🧪 Test: $TestName" -Type "Test"
    
    try {
        # Construction de la commande
        $Command = "python `"$AnalyzeScript`" " + ($Arguments -join " ")
        
        if ($Verbose) {
            Write-ColoredOutput "   Commande: $Command" -Type "Info"
        }
        
        # Exécution avec capture de sortie
        $Result = powershell -Command $Command 2>&1
        $ExitCode = $LASTEXITCODE
        
        # Vérification du code de sortie
        if ($ShouldSucceed -and $ExitCode -ne 0) {
            Write-ColoredOutput "❌ ÉCHEC: Code de sortie $ExitCode inattendu" -Type "Error"
            Write-ColoredOutput "   Sortie: $Result" -Type "Error"
            return $false
        } elseif (-not $ShouldSucceed -and $ExitCode -eq 0) {
            Write-ColoredOutput "❌ ÉCHEC: Succès inattendu (devait échouer)" -Type "Error"
            return $false
        }
        
        # Vérification de la sortie attendue
        if ($ExpectedOutput -and -not ($Result -match $ExpectedOutput)) {
            Write-ColoredOutput "❌ ÉCHEC: Sortie inattendue" -Type "Error"
            Write-ColoredOutput "   Attendu: $ExpectedOutput" -Type "Error"
            Write-ColoredOutput "   Obtenu: $Result" -Type "Error"
            return $false
        }
        
        Write-ColoredOutput "✅ SUCCÈS" -Type "Success"
        return $true
        
    } catch {
        Write-ColoredOutput "❌ ERREUR: $($_.Exception.Message)" -Type "Error"
        return $false
    }
}

# Tests de base des arguments CLI
function Test-BasicCLIArguments {
    Write-ColoredOutput "`n📋 Tests de base des arguments CLI" -Type "Info"
    
    $TestResults = @()
    
    # Test 1: Configuration FOL authentique
    $TestResults += Invoke-CLITest -TestName "Configuration FOL authentique" -Arguments @(
        "--source-type", "simple",
        "--logic-type", "fol", 
        "--mock-level", "none",
        "--taxonomy", "full",
        "--format", "console",
        "--quiet"
    )
    
    # Test 2: Configuration PL de développement
    $TestResults += Invoke-CLITest -TestName "Configuration PL développement" -Arguments @(
        "--source-type", "simple",
        "--logic-type", "pl",
        "--mock-level", "partial", 
        "--taxonomy", "mock",
        "--format", "console",
        "--quiet"
    )
    
    # Test 3: Configuration de test complète
    $TestResults += Invoke-CLITest -TestName "Configuration test complète" -Arguments @(
        "--source-type", "simple",
        "--logic-type", "pl",
        "--mock-level", "full",
        "--taxonomy", "mock",
        "--agents", "informal,synthesis",
        "--no-jvm",
        "--format", "console",
        "--quiet"
    )
    
    # Test 4: Agents personnalisés
    $TestResults += Invoke-CLITest -TestName "Agents personnalisés" -Arguments @(
        "--source-type", "simple",
        "--agents", "informal,fol_logic,synthesis,pm",
        "--format", "console",
        "--quiet"
    )
    
    # Test 5: Orchestration conversationnelle
    $TestResults += Invoke-CLITest -TestName "Orchestration conversationnelle" -Arguments @(
        "--source-type", "simple",
        "--orchestration", "conversation",
        "--advanced",
        "--format", "console", 
        "--quiet"
    )
    
    return $TestResults
}

# Tests des combinaisons invalides
function Test-InvalidCombinations {
    Write-ColoredOutput "`n❌ Tests des combinaisons invalides" -Type "Info"
    
    $TestResults = @()
    
    # Test 1: Mock level incompatible avec authenticité
    $TestResults += Invoke-CLITest -TestName "Mock partial + require real GPT (invalide)" -Arguments @(
        "--source-type", "simple",
        "--mock-level", "partial",
        "--require-real-gpt",
        "--format", "console",
        "--quiet"
    ) -ShouldSucceed $false
    
    # Test 2: Agent FOL sans JVM
    $TestResults += Invoke-CLITest -TestName "FOL agent sans JVM (invalide)" -Arguments @(
        "--source-type", "simple",
        "--agents", "fol_logic",
        "--no-jvm",
        "--format", "console",
        "--quiet"
    ) -ShouldSucceed $false
    
    return $TestResults
}

# Tests des formats de sortie
function Test-OutputFormats {
    Write-ColoredOutput "`n📄 Tests des formats de sortie" -Type "Info"
    
    $TestResults = @()
    
    # Création du répertoire de sortie
    if (-not (Test-Path $TestOutputDir)) {
        New-Item -ItemType Directory -Path $TestOutputDir -Force | Out-Null
    }
    
    $Formats = @("console", "markdown", "json")
    foreach ($Format in $Formats) {
        $OutputFile = Join-Path $TestOutputDir "test_output_$Format.txt"
        
        $TestResults += Invoke-CLITest -TestName "Format de sortie: $Format" -Arguments @(
            "--source-type", "simple",
            "--logic-type", "pl",
            "--mock-level", "full",
            "--taxonomy", "mock", 
            "--format", $Format,
            "--output", $OutputFile,
            "--quiet"
        )
        
        # Vérification que le fichier a été créé
        if (Test-Path $OutputFile) {
            Write-ColoredOutput "   ✅ Fichier de sortie créé: $OutputFile" -Type "Success"
        } else {
            Write-ColoredOutput "   ❌ Fichier de sortie manquant: $OutputFile" -Type "Error"
            $TestResults[-1] = $false
        }
    }
    
    return $TestResults
}

# Tests de performance
function Test-Performance {
    if ($SkipSlowTests) {
        Write-ColoredOutput "`n⏭️ Tests de performance ignorés (--SkipSlowTests)" -Type "Warning"
        return @()
    }
    
    Write-ColoredOutput "`n⚡ Tests de performance" -Type "Info"
    
    $TestResults = @()
    
    # Configuration rapide (test)
    $StartTime = Get-Date
    $TestResults += Invoke-CLITest -TestName "Configuration rapide (performance)" -Arguments @(
        "--source-type", "simple",
        "--logic-type", "pl",
        "--mock-level", "full",
        "--taxonomy", "mock",
        "--agents", "informal,synthesis",
        "--no-jvm",
        "--format", "console",
        "--quiet"
    )
    $FastDuration = (Get-Date) - $StartTime
    
    Write-ColoredOutput "   ⏱️ Durée configuration rapide: $($FastDuration.TotalSeconds)s" -Type "Info"
    
    # Vérification que l'exécution est rapide (< 60s)
    if ($FastDuration.TotalSeconds -gt 60) {
        Write-ColoredOutput "   ⚠️ Configuration rapide trop lente (> 60s)" -Type "Warning"
    }
    
    return $TestResults
}

# Tests d'intégration avec environnement
function Test-EnvironmentIntegration {
    Write-ColoredOutput "`n🌍 Tests d'intégration environnement" -Type "Info"
    
    $TestResults = @()
    
    # Test avec variables d'environnement
    $env:UNIFIED_LOGIC_TYPE = "fol"
    $env:UNIFIED_MOCK_LEVEL = "none"
    $env:UNIFIED_TAXONOMY_SIZE = "full"
    
    try {
        $TestResults += Invoke-CLITest -TestName "Configuration via environnement" -Arguments @(
            "--source-type", "simple",
            "--format", "console",
            "--quiet"
        )
    } finally {
        # Nettoyage des variables d'environnement
        Remove-Item Env:UNIFIED_LOGIC_TYPE -ErrorAction SilentlyContinue
        Remove-Item Env:UNIFIED_MOCK_LEVEL -ErrorAction SilentlyContinue  
        Remove-Item Env:UNIFIED_TAXONOMY_SIZE -ErrorAction SilentlyContinue
    }
    
    return $TestResults
}

# Tests d'aide et validation
function Test-HelpAndValidation {
    Write-ColoredOutput "`n❓ Tests d'aide et validation" -Type "Info"
    
    $TestResults = @()
    
    # Test de l'aide
    $TestResults += Invoke-CLITest -TestName "Affichage de l'aide" -Arguments @("--help") -ExpectedOutput "usage:"
    
    # Test sans arguments (devrait demander source)
    $TestResults += Invoke-CLITest -TestName "Sans source (invalide)" -Arguments @("--format", "console") -ShouldSucceed $false
    
    return $TestResults
}

# Fonction principale d'exécution des tests
function Invoke-AllTests {
    Write-ColoredOutput "🚀 Démarrage des tests CLI pour le système de configuration unifié" -Type "Info"
    Write-ColoredOutput "   Répertoire projet: $ProjectRoot" -Type "Info"
    Write-ColoredOutput "   Script à tester: $AnalyzeScript" -Type "Info"
    Write-ColoredOutput "   Suite de tests: $TestSuite" -Type "Info"
    
    # Vérification que le script existe
    if (-not (Test-Path $AnalyzeScript)) {
        Write-ColoredOutput "❌ ERREUR: Script analyze_text.py introuvable: $AnalyzeScript" -Type "Error"
        exit 1
    }
    
    $AllResults = @()
    
    # Exécution des suites de tests selon la sélection
    if ($TestSuite -eq "All" -or $TestSuite -eq "Basic") {
        $AllResults += Test-BasicCLIArguments
        $AllResults += Test-HelpAndValidation
    }
    
    if ($TestSuite -eq "All" -or $TestSuite -eq "Advanced") {
        $AllResults += Test-InvalidCombinations
        $AllResults += Test-OutputFormats
    }
    
    if ($TestSuite -eq "All" -or $TestSuite -eq "Integration") {
        $AllResults += Test-EnvironmentIntegration
    }
    
    if ($TestSuite -eq "All" -or $TestSuite -eq "Performance") {
        $AllResults += Test-Performance
    }
    
    # Calcul des résultats
    $TotalTests = $AllResults.Count
    $PassedTests = ($AllResults | Where-Object { $_ -eq $true }).Count
    $FailedTests = $TotalTests - $PassedTests
    
    # Affichage du résumé
    Write-ColoredOutput "`n📊 RÉSUMÉ DES TESTS" -Type "Info"
    Write-ColoredOutput "   Total: $TotalTests tests" -Type "Info"
    Write-ColoredOutput "   Réussis: $PassedTests tests" -Type "Success"
    Write-ColoredOutput "   Échecs: $FailedTests tests" -Type $(if ($FailedTests -gt 0) { "Error" } else { "Success" })
    
    if ($FailedTests -eq 0) {
        Write-ColoredOutput "`n🎉 TOUS LES TESTS SONT PASSÉS!" -Type "Success"
        exit 0
    } else {
        Write-ColoredOutput "`n💥 CERTAINS TESTS ONT ÉCHOUÉ" -Type "Error"
        exit 1
    }
}

# Point d'entrée principal
try {
    Invoke-AllTests
} catch {
    Write-ColoredOutput "❌ ERREUR CRITIQUE: $($_.Exception.Message)" -Type "Error"
    Write-ColoredOutput "   Trace: $($_.ScriptStackTrace)" -Type "Error"
    exit 1
}