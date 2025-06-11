#!/usr/bin/env pwsh
<#
.SYNOPSIS
Script d'exécution pour la validation système Sherlock/Watson avec données synthétiques

.DESCRIPTION
Lance la validation complète du système Sherlock/Watson en utilisant des datasets 
synthétiques spécialement conçus pour détecter les mocks vs raisonnement réel.

.PARAMETER TestMode
Mode de test: "complete", "quick", "edge_cases", "mock_detection"

.PARAMETER GenerateReport
Génère un rapport HTML en plus du JSON

.PARAMETER Verbose
Active le mode verbeux pour plus de détails

.EXAMPLE
.\run_sherlock_watson_synthetic_validation.ps1 -TestMode complete -GenerateReport -Verbose

.NOTES
Auteur: Intelligence Symbolique EPITA
Date: 08/06/2025
#>

param(
    [ValidateSet("complete", "quick", "edge_cases", "mock_detection")]
    [string]$TestMode = "complete",
    
    [switch]$GenerateReport = $false,
    
    [switch]$Verbose = $false
)

# Configuration
$ProjectRoot = $PSScriptRoot
$ScriptPath = Join-Path $ProjectRoot "test_sherlock_watson_synthetic_validation.py"
$ActivationScript = Join-Path $ProjectRoot "scripts\env\activate_project_env.ps1"

# Fonction de logging
function Write-LogMessage {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARNING" { "Yellow" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Test-Prerequisites {
    Write-LogMessage "Vérification des prérequis..." "INFO"
    
    # Vérification du script Python
    if (-not (Test-Path $ScriptPath)) {
        Write-LogMessage "Script de validation non trouvé: $ScriptPath" "ERROR"
        return $false
    }
    
    # Vérification du script d'activation
    if (-not (Test-Path $ActivationScript)) {
        Write-LogMessage "Script d'activation non trouvé: $ActivationScript" "ERROR"
        return $false
    }
    
    Write-LogMessage "Prérequis validés ✓" "SUCCESS"
    return $true
}

function Invoke-SyntheticValidation {
    param([string]$Mode)
    
    Write-LogMessage "Lancement de la validation synthétique en mode: $Mode" "INFO"
    Write-LogMessage "Utilisation de l'environnement projet via PowerShell" "INFO"
    
    try {
        # Construction de la commande Python avec paramètres selon le mode
        $pythonArgs = @()
        
        switch ($Mode) {
            "quick" {
                $pythonArgs += "--quick-mode"
                Write-LogMessage "Mode rapide: Tests essentiels uniquement" "INFO"
            }
            "edge_cases" {
                $pythonArgs += "--edge-cases-only"
                Write-LogMessage "Mode edge cases: Tests de robustesse uniquement" "INFO"
            }
            "mock_detection" {
                $pythonArgs += "--mock-detection-focus"
                Write-LogMessage "Mode détection mocks: Focus sur l'identification des simulations" "INFO"
            }
            default {
                Write-LogMessage "Mode complet: Tous les tests synthétiques" "INFO"
            }
        }
        
        if ($Verbose) {
            $pythonArgs += "--verbose"
        }
        
        # Exécution via l'environnement projet
        $command = "python `"$ScriptPath`""
        if ($pythonArgs.Count -gt 0) {
            $command += " " + ($pythonArgs -join " ")
        }
        
        Write-LogMessage "Commande d'exécution: $command" "INFO"
        
        # Utilisation du script d'activation pour maintenir l'environnement
        $executionResult = & $ActivationScript -CommandToRun $command
        
        if ($LASTEXITCODE -eq 0) {
            Write-LogMessage "Validation terminée avec succès ✓" "SUCCESS"
            return $true
        } else {
            Write-LogMessage "Validation échouée (Code: $LASTEXITCODE)" "ERROR"
            return $false
        }
        
    } catch {
        Write-LogMessage "Erreur lors de l'exécution: $($_.Exception.Message)" "ERROR"
        Write-LogMessage "Stack trace: $($_.ScriptStackTrace)" "ERROR"
        return $false
    }
}

function Generate-HTMLReport {
    param([string]$JsonReportPath)
    
    if (-not (Test-Path $JsonReportPath)) {
        Write-LogMessage "Rapport JSON non trouvé pour conversion HTML" "WARNING"
        return
    }
    
    Write-LogMessage "Génération du rapport HTML..." "INFO"
    
    try {
        $jsonContent = Get-Content $JsonReportPath -Raw | ConvertFrom-Json
        $htmlPath = $JsonReportPath -replace "\.json$", ".html"
        
        $htmlContent = @"
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Validation Sherlock/Watson - Données Synthétiques</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1, h2, h3 { color: #2c3e50; }
        .summary { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .warning { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .error { background: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #007bff; }
        .score-excellent { border-left-color: #28a745; }
        .score-good { border-left-color: #ffc107; }
        .score-poor { border-left-color: #dc3545; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .timestamp { color: #6c757d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Rapport de Validation Système Sherlock/Watson</h1>
        <h2>📊 Données Synthétiques - Détection Mock vs Réel</h2>
        
        <div class="timestamp">Généré le: $($jsonContent.timestamp)</div>
        
        <div class="summary">
            <h3>📈 Résumé Global</h3>
            <div class="metric score-$(if($jsonContent.validation_summary.global_system_score -ge 80){'excellent'}elseif($jsonContent.validation_summary.global_system_score -ge 60){'good'}else{'poor'})">
                <strong>Score Global:</strong> $($jsonContent.validation_summary.global_system_score)/100
            </div>
            <div class="metric">
                <strong>Tests Exécutés:</strong> $($jsonContent.validation_summary.total_tests_executed)
            </div>
            <div class="metric">
                <strong>Taux de Succès:</strong> $(100 - $jsonContent.validation_summary.error_rate)%
            </div>
        </div>
        
        <h3>🧠 Analyse Raisonnement Mock vs Réel</h3>
        <div class="metric score-$(if($jsonContent.reasoning_analysis.mock_vs_real_detection.real.percentage -ge 60){'excellent'}elseif($jsonContent.reasoning_analysis.mock_vs_real_detection.real.percentage -ge 40){'good'}else{'poor'})">
            <strong>Raisonnement Réel:</strong> $($jsonContent.reasoning_analysis.mock_vs_real_detection.real.percentage)%
        </div>
        <div class="metric">
            <strong>Mocks Détectés:</strong> $($jsonContent.reasoning_analysis.mock_vs_real_detection.mock.percentage)%
        </div>
        <div class="metric">
            <strong>Hybride:</strong> $($jsonContent.reasoning_analysis.mock_vs_real_detection.hybrid.percentage)%
        </div>
        
        <h3>👥 Performance par Agent</h3>
        <table>
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>Cohérence Logique</th>
                    <th>Qualité Réponses</th>
                    <th>Temps Moyen (s)</th>
                    <th>Raisonnement Réel</th>
                </tr>
            </thead>
            <tbody>
"@
        
        foreach ($agent in $jsonContent.agent_performance.PSObject.Properties) {
            $stats = $agent.Value
            $realReasoning = $stats.reasoning_distribution.real
            $htmlContent += @"
                <tr>
                    <td><strong>$($agent.Name)</strong></td>
                    <td>$($stats.avg_coherence.ToString("F2"))</td>
                    <td>$($stats.avg_quality.ToString("F2"))</td>
                    <td>$($stats.avg_processing_time.ToString("F2"))</td>
                    <td>$realReasoning tests</td>
                </tr>
"@
        }
        
        $htmlContent += @"
            </tbody>
        </table>
        
        <h3>🛡️ Évaluation de Robustesse</h3>
        <div class="metric score-$(if($jsonContent.robustness_evaluation.robustness_score -ge 70){'excellent'}elseif($jsonContent.robustness_evaluation.robustness_score -ge 50){'good'}else{'poor'})">
            <strong>Score Robustesse:</strong> $($jsonContent.robustness_evaluation.robustness_score)/100
        </div>
        <div class="metric">
            <strong>Gestion Contradictions:</strong> $(if($jsonContent.robustness_evaluation.handles_contradictions){'✓ Oui'}else{'✗ Non'})
        </div>
        <div class="metric">
            <strong>Données Incomplètes:</strong> $(if($jsonContent.robustness_evaluation.handles_incomplete_data){'✓ Oui'}else{'✗ Non'})
        </div>
        
        <h3>💡 Recommandations</h3>
        <ul>
"@
        
        foreach ($recommendation in $jsonContent.recommendations) {
            $htmlContent += "<li>$recommendation</li>"
        }
        
        $htmlContent += @"
        </ul>
        
        <h3>📋 Analyse par Catégorie</h3>
        <table>
            <thead>
                <tr>
                    <th>Catégorie</th>
                    <th>Tests</th>
                    <th>Succès</th>
                    <th>Cohérence</th>
                    <th>Qualité</th>
                    <th>Raisonnement Réel</th>
                </tr>
            </thead>
            <tbody>
"@
        
        foreach ($category in $jsonContent.category_analysis.PSObject.Properties) {
            $stats = $category.Value
            $htmlContent += @"
                <tr>
                    <td><strong>$($category.Name)</strong></td>
                    <td>$($stats.total_tests)</td>
                    <td>$($stats.success_rate.ToString("P0"))</td>
                    <td>$($stats.avg_coherence.ToString("F2"))</td>
                    <td>$($stats.avg_quality.ToString("F2"))</td>
                    <td>$($stats.real_reasoning_rate.ToString("P0"))</td>
                </tr>
"@
        }
        
        $htmlContent += @"
            </tbody>
        </table>
        
        <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #6c757d; text-align: center;">
            <p>Rapport généré par le système de validation Intelligence Symbolique EPITA</p>
            <p>Validation système Sherlock/Watson avec données synthétiques</p>
        </footer>
    </div>
</body>
</html>
"@
        
        $htmlContent | Out-File -FilePath $htmlPath -Encoding UTF8
        Write-LogMessage "Rapport HTML généré: $htmlPath" "SUCCESS"
        
    } catch {
        Write-LogMessage "Erreur lors de la génération HTML: $($_.Exception.Message)" "ERROR"
    }
}

function Show-ValidationSummary {
    Write-LogMessage "=== RÉSUMÉ DE LA VALIDATION SYNTHÉTIQUE ===" "INFO"
    Write-LogMessage "Mode de test: $TestMode" "INFO"
    Write-LogMessage "Génération rapport HTML: $(if($GenerateReport){'Activée'}else{'Désactivée'})" "INFO"
    Write-LogMessage "Mode verbeux: $(if($Verbose){'Activé'}else{'Désactivé'})" "INFO"
    Write-LogMessage "=" * 60 "INFO"
}

# === EXÉCUTION PRINCIPALE ===

try {
    Show-ValidationSummary
    
    # Vérification des prérequis
    if (-not (Test-Prerequisites)) {
        Write-LogMessage "Échec de la vérification des prérequis" "ERROR"
        exit 1
    }
    
    # Exécution de la validation
    $validationSuccess = Invoke-SyntheticValidation -Mode $TestMode
    
    if ($validationSuccess) {
        Write-LogMessage "Validation synthétique terminée avec succès" "SUCCESS"
        
        # Recherche du rapport JSON le plus récent
        if ($GenerateReport) {
            $recentReport = Get-ChildItem -Path $ProjectRoot -Filter "rapport_validation_sherlock_watson_synthetic_*.json" | 
                           Sort-Object LastWriteTime -Descending | 
                           Select-Object -First 1
            
            if ($recentReport) {
                Generate-HTMLReport -JsonReportPath $recentReport.FullName
            }
        }
        
        Write-LogMessage "🎉 MISSION ACCOMPLIE - Validation système Sherlock/Watson avec données synthétiques" "SUCCESS"
        exit 0
        
    } else {
        Write-LogMessage "Échec de la validation synthétique" "ERROR"
        exit 1
    }
    
} catch {
    Write-LogMessage "Erreur critique: $($_.Exception.Message)" "ERROR"
    Write-LogMessage "Stack trace: $($_.ScriptStackTrace)" "ERROR"
    exit 2
} finally {
    Write-LogMessage "Fin du script de validation synthétique" "INFO"
}