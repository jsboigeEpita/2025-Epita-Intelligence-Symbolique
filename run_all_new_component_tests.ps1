#!/usr/bin/env pwsh
<#
.SYNOPSIS
Script de validation complète des nouveaux composants

.DESCRIPTION
Lance la validation de tous les nouveaux composants du projet.
Version refactorisée utilisant les modules Python mutualisés.

.PARAMETER Authentic
Mode authentique (composants réels, API, etc.)

.PARAMETER Verbose
Affichage détaillé

.PARAMETER Fast
Tests unitaires rapides seulement

.PARAMETER Component
Exécuter un composant spécifique

.PARAMETER Level
Niveau de tests (unit|integration|all)

.PARAMETER Report
Fichier de sortie pour le rapport JSON

.PARAMETER Output
Alias pour -Report

.PARAMETER Help
Afficher l'aide

.EXAMPLE
.\run_all_new_component_tests.ps1 -Authentic -Verbose
.\run_all_new_component_tests.ps1 -Fast
.\run_all_new_component_tests.ps1 -Component "TweetyErrorAnalyzer"

.NOTES
Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025 - Version refactorisée
#>

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

# Configuration
$ProjectRoot = $PSScriptRoot

# Affichage de l'aide
if ($Help) {
    Write-Host @"
🧪 VALIDATION COMPLÈTE DES NOUVEAUX COMPOSANTS
==============================================

USAGE:
    .\run_all_new_component_tests.ps1 [OPTIONS]

OPTIONS:
    -Authentic          Mode authentique (composants réels, API, etc.)
    -Verbose           Affichage détaillé
    -Fast              Tests unitaires rapides seulement
    -Component <name>  Exécuter un composant spécifique
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
"@ -ForegroundColor Cyan
    exit 0
}

try {
    # Import des modules Python mutualisés
    $reportFile = if ($Report) { $Report } elseif ($Output) { $Output } else { "" }
    
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
print_colored("🧪 VALIDATION COMPLÈTE DES NOUVEAUX COMPOSANTS", "blue")
print_colored("=" * 50, "blue")
print_colored(f"Mode authentique: $($Authentic)", "white")
print_colored(f"Mode verbose: $($Verbose)", "white")
print_colored(f"Mode rapide: $($Fast)", "white")
component_display = '$Component' if '$Component' else 'Tous'
print_colored(f"Composant spécifique: {component_display}", "white")
print_colored(f"Niveau: $Level", "white")
report_display = '$reportFile' if '$reportFile' else 'Console uniquement'
print_colored(f"Rapport: {report_display}", "white")
print_colored("=" * 50, "white")

try:
    # Initialisation des modules
    validator = ValidationEngine()
    test_runner = TestRunner()
    
    # Configuration du test
    test_config = {
        'target_script': 'run_all_new_component_tests.py',
        'authentic': $($Authentic.ToString().ToLower()),
        'verbose': $($Verbose.ToString().ToLower()),
        'fast': $($Fast.ToString().ToLower()),
        'component': '$Component' if '$Component' else None,
        'level': '$Level',
        'report_file': '$reportFile' if '$reportFile' else None
    }
    
    # Construction des arguments
    test_args = []
    if $($Authentic.ToString().ToLower()):
        test_args.append('--authentic')
    if $($Verbose.ToString().ToLower()):
        test_args.append('--verbose')
    if $($Fast.ToString().ToLower()):
        test_args.append('--fast')
    if '$Component':
        test_args.extend(['--component', '$Component'])
    if '$Level' != 'all':
        test_args.extend(['--level', '$Level'])
    if '$reportFile':
        test_args.extend(['--report', '$reportFile'])
    
    # Vérification des prérequis système
    print_colored("Vérification des prérequis système...", "blue")
    prereq_result = validator.check_system_requirements()
    
    if not prereq_result['valid']:
        print_colored("❌ Prérequis non satisfaits:", "red")
        for issue in prereq_result['issues']:
            print_colored(f"  - {issue}", "red")
        
        # En mode non-authentique, on peut continuer en mode dégradé
        if not $($Authentic.ToString().ToLower()):
            print_colored("⚠️  Passage en mode dégradé possible", "yellow")
        else:
            print_colored("❌ Impossible de continuer en mode authentique", "red")
            sys.exit(1)
    else:
        print_colored("✅ Prérequis validés", "green")
    
    # Vérifications spécifiques au mode authentique
    if $($Authentic.ToString().ToLower()):
        print_colored("Vérifications mode authentique...", "blue")
        auth_checks = validator.check_authentic_requirements()
        
        if not auth_checks['valid']:
            print_colored("❌ Prérequis mode authentique non satisfaits:", "red")
            for issue in auth_checks['issues']:
                print_colored(f"  - {issue}", "red")
            sys.exit(1)
        else:
            print_colored("✅ Mode authentique validé", "green")
    
    # Vérification de l'existence du script Python cible
    script_path = os.path.join('$ProjectRoot', test_config['target_script'])
    if not os.path.exists(script_path):
        print_colored(f"❌ Script Python principal introuvable: {script_path}", "red")
        print_colored("Assurez-vous que run_all_new_component_tests.py est présent.", "red")
        sys.exit(1)
    
    # Exécution des tests
    print_colored("Lancement de la validation des composants...", "blue")
    
    result = test_runner.run_specific_test(
        script_path=test_config['target_script'],
        test_args=test_args,
        working_dir='$ProjectRoot'
    )
    
    # Rapport final
    print_colored("📊 RAPPORT FINAL", "blue")
    if result['success']:
        print_colored("✅ Tous les tests sont passés avec succès", "green")
        print_colored("🚀 Système prêt pour la production", "green")
        
        if '$reportFile' and os.path.exists('$reportFile'):
            print_colored(f"📄 Rapport JSON disponible: $reportFile", "cyan")
        
        print_colored("🎉 MISSION ACCOMPLIE - Validation des nouveaux composants", "green")
        sys.exit(0)
    else:
        print_colored("❌ Des erreurs ont été détectées", "red")
        print_colored("🔍 Vérifiez les logs pour plus de détails", "yellow")
        
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
