#!/usr/bin/env pwsh
<#
.SYNOPSIS
Script de validation système Sherlock/Watson avec données synthétiques

.DESCRIPTION
Lance la validation complète du système Sherlock/Watson en utilisant des datasets
synthétiques spécialement conçus pour détecter les mocks vs raisonnement réel.
Version refactorisée utilisant les modules Python mutualisés.

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
Date: 09/06/2025 - Version refactorisée
#>

param(
    [ValidateSet("complete", "quick", "edge_cases", "mock_detection")]
    [string]$TestMode = "complete",
    
    [switch]$GenerateReport = $false,
    
    [switch]$Verbose = $false
)

# Configuration
$ProjectRoot = $PSScriptRoot

try {
    # Import des modules Python mutualisés
    $pythonCommand = @"
import sys
import os
sys.path.append(os.path.join('$ProjectRoot', 'scripts', 'core'))

from test_runner import TestRunner
from validation_engine import ValidationEngine
from common_utils import setup_logging, print_colored

# Configuration du logging
logger = setup_logging(verbose=$($Verbose.ToString().ToLower()))

# Affichage des informations de configuration
print_colored("🔍 VALIDATION SHERLOCK/WATSON - DONNÉES SYNTHÉTIQUES", "blue")
print_colored(f"Mode de test: $TestMode", "white")
print_colored(f"Génération rapport HTML: $($GenerateReport)", "white")
print_colored(f"Mode verbeux: $($Verbose)", "white")
print_colored("=" * 60, "white")

try:
    # Initialisation des modules
    validator = ValidationEngine()
    test_runner = TestRunner()
    
    # Configuration du mode de test
    test_config = {
        'target_script': 'test_sherlock_watson_synthetic_validation.py',
        'test_mode': '$TestMode',
        'verbose': $($Verbose.ToString().ToLower()),
        'generate_html_report': $($GenerateReport.ToString().ToLower())
    }
    
    # Arguments spécifiques selon le mode
    test_args = []
    if '$TestMode' == 'quick':
        test_args.append('--quick-mode')
        print_colored("Mode rapide: Tests essentiels uniquement", "yellow")
    elif '$TestMode' == 'edge_cases':
        test_args.append('--edge-cases-only')
        print_colored("Mode edge cases: Tests de robustesse uniquement", "yellow")
    elif '$TestMode' == 'mock_detection':
        test_args.append('--mock-detection-focus')
        print_colored("Mode détection mocks: Focus sur l'identification des simulations", "yellow")
    else:
        print_colored("Mode complet: Tous les tests synthétiques", "yellow")
        
    if $($Verbose.ToString().ToLower()):
        test_args.append('--verbose')
    
    # Vérification des prérequis
    print_colored("Vérification des prérequis système...", "blue")
    prereq_result = validator.check_system_requirements()
    
    if not prereq_result['valid']:
        print_colored("❌ Prérequis non satisfaits:", "red")
        for issue in prereq_result['issues']:
            print_colored(f"  - {issue}", "red")
        sys.exit(1)
    
    print_colored("✅ Prérequis validés", "green")
    
    # Exécution de la validation
    print_colored("Lancement de la validation synthétique...", "blue")
    
    result = test_runner.run_specific_test(
        script_path=test_config['target_script'],
        test_args=test_args,
        working_dir='$ProjectRoot'
    )
    
    if result['success']:
        print_colored("✅ Validation terminée avec succès", "green")
        
        # Génération du rapport HTML si demandé
        if $($GenerateReport.ToString().ToLower()):
            print_colored("Génération du rapport HTML...", "blue")
            
            # Recherche du rapport JSON le plus récent
            import glob
            json_reports = glob.glob(os.path.join('$ProjectRoot', 'rapport_validation_sherlock_watson_synthetic_*.json'))
            if json_reports:
                latest_report = max(json_reports, key=os.path.getmtime)
                validator.generate_html_report(latest_report)
                print_colored(f"📄 Rapport HTML généré", "green")
        
        print_colored("🎉 MISSION ACCOMPLIE - Validation système Sherlock/Watson", "green")
        sys.exit(0)
    else:
        print_colored("❌ Échec de la validation", "red")
        if 'error' in result:
            print_colored(f"Erreur: {result['error']}", "red")
        sys.exit(1)
        
except Exception as e:
    print_colored(f"❌ Erreur critique: {str(e)}", "red")
    if $($Verbose.ToString().ToLower()):
        import traceback
        print_colored(f"Stack trace: {traceback.format_exc()}", "red")
    sys.exit(2)
"@

    # Exécution via l'environnement projet
    $activationScript = Join-Path $ProjectRoot "scripts\env\activate_project_env.ps1"
    $command = "python -c `"$($pythonCommand -replace '"', '\"')`""
    
    if (Test-Path $activationScript) {
        & $activationScript -CommandToRun $command
    } else {
        # Fallback si le script d'activation n'existe pas
        Invoke-Expression $command
    }
    
    exit $LASTEXITCODE
    
} catch {
    Write-Host "❌ Erreur critique: $($_.Exception.Message)" -ForegroundColor Red
    if ($Verbose) {
        Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Gray
    }
    exit 2
}