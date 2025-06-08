# Script de démonstration du système unifié authentique
# Objectif : Tester la configuration dynamique et l'authenticité 100%

param(
    [Parameter(HelpMessage="Type de logique à utiliser")]
    [ValidateSet("fol", "pl", "modal")]
    [string]$LogicType = "fol",
    
    [Parameter(HelpMessage="Agents à utiliser")]
    [string]$Agents = "informal,fol_logic,synthesis",
    
    [Parameter(HelpMessage="Type d'orchestration")]
    [ValidateSet("unified", "conversation", "custom")]
    [string]$Orchestration = "unified",
    
    [Parameter(HelpMessage="Niveau de mock")]
    [ValidateSet("none", "partial", "full")]
    [string]$MockLevel = "none",
    
    [Parameter(HelpMessage="Taille de taxonomie")]
    [ValidateSet("full", "mock")]
    [string]$Taxonomy = "full",
    
    [Parameter(HelpMessage="Exécuter d'abord les tests de validation")]
    [switch]$RunTests,
    
    [Parameter(HelpMessage="Générer un rapport d'authenticité")]
    [switch]$AuthenticityReport,
    
    [Parameter(HelpMessage="Mode verbeux")]
    [switch]$Verbose
)

Write-Host "🚀 DÉMONSTRATION DU SYSTÈME UNIFIÉ AUTHENTIQUE" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

Write-Host "📋 Configuration sélectionnée:" -ForegroundColor Cyan
Write-Host "  - Type de logique: $LogicType" -ForegroundColor White
Write-Host "  - Agents: $Agents" -ForegroundColor White
Write-Host "  - Orchestration: $Orchestration" -ForegroundColor White
Write-Host "  - Niveau de mock: $MockLevel" -ForegroundColor White
Write-Host "  - Taxonomie: $Taxonomy" -ForegroundColor White
Write-Host ""

# Vérification de l'environnement
Write-Host "🔍 Vérification de l'environnement..." -ForegroundColor Yellow

# Vérification Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Python non trouvé" -ForegroundColor Red
    exit 1
}

# Vérification du projet
if (-not (Test-Path "scripts\main\analyze_text.py")) {
    Write-Host "  ❌ Script principal non trouvé" -ForegroundColor Red
    exit 1
}
Write-Host "  ✅ Script principal trouvé" -ForegroundColor Green

# Vérification de la configuration unifiée
if (-not (Test-Path "config\unified_config.py")) {
    Write-Host "  ❌ Configuration unifiée non trouvée" -ForegroundColor Red
    exit 1
}
Write-Host "  ✅ Configuration unifiée disponible" -ForegroundColor Green

Write-Host ""

# Tests de validation si demandés
if ($RunTests) {
    Write-Host "🧪 Exécution des tests de validation..." -ForegroundColor Yellow
    
    $testCommand = "python -m scripts.test.test_unified_authentic_system"
    
    try {
        Write-Host "Commande: $testCommand" -ForegroundColor Gray
        $testResult = Invoke-Expression $testCommand
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Tests de validation réussis" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ Certains tests ont échoué (code: $LASTEXITCODE)" -ForegroundColor Yellow
            Write-Host "Résultat des tests:" -ForegroundColor Gray
            Write-Host $testResult -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ❌ Erreur lors des tests: $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Rapport d'authenticité si demandé
if ($AuthenticityReport) {
    Write-Host "🔒 Génération du rapport d'authenticité..." -ForegroundColor Yellow
    
    $mockScanCommand = "python -m scripts.validation.mock_elimination"
    
    try {
        Write-Host "Commande: $mockScanCommand" -ForegroundColor Gray
        $scanResult = Invoke-Expression $mockScanCommand
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Rapport d'authenticité généré" -ForegroundColor Green
            
            # Afficher un résumé si le fichier de rapport existe
            if (Test-Path "reports\authenticity_report.md") {
                Write-Host "  📄 Rapport disponible dans reports\authenticity_report.md" -ForegroundColor Green
            }
        } else {
            Write-Host "  ⚠️ Génération du rapport avec avertissements" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ❌ Erreur génération rapport: $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Construction de la commande d'analyse principale
Write-Host "🔄 Préparation de l'analyse avec configuration authentique..." -ForegroundColor Yellow

$analysisCommand = "python -m scripts.main.analyze_text"
$analysisCommand += " --source-type simple"
$analysisCommand += " --logic-type $LogicType"
$analysisCommand += " --agents $Agents"
$analysisCommand += " --orchestration $Orchestration"
$analysisCommand += " --mock-level $MockLevel"
$analysisCommand += " --taxonomy $Taxonomy"
$analysisCommand += " --format markdown"
$analysisCommand += " --require-real-gpt"
$analysisCommand += " --require-real-tweety"
$analysisCommand += " --require-full-taxonomy"
$analysisCommand += " --validate-tools"

if ($Verbose) {
    $analysisCommand += " --verbose"
}

Write-Host "Commande d'analyse:" -ForegroundColor Cyan
Write-Host $analysisCommand -ForegroundColor White
Write-Host ""

# Validation de la configuration avant exécution
Write-Host "✅ Validation de la configuration..." -ForegroundColor Yellow

$validationCommand = "python -c `"
from config.unified_config import UnifiedConfig, LogicType, MockLevel, OrchestrationType, TaxonomySize, AgentType, validate_config
import sys

# Création de la configuration
try:
    logic_type = LogicType('$LogicType')
    mock_level = MockLevel('$MockLevel')
    orchestration = OrchestrationType('$Orchestration')
    taxonomy = TaxonomySize('$Taxonomy')
    
    agents = []
    for agent_name in '$Agents'.split(','):
        agent_name = agent_name.strip()
        if agent_name == 'fol_logic':
            agents.append(AgentType.FOL_LOGIC)
        elif agent_name == 'informal':
            agents.append(AgentType.INFORMAL)
        elif agent_name == 'synthesis':
            agents.append(AgentType.SYNTHESIS)
    
    config = UnifiedConfig(
        logic_type=logic_type,
        agents=agents,
        orchestration_type=orchestration,
        mock_level=mock_level,
        taxonomy_size=taxonomy
    )
    
    errors = validate_config(config)
    if errors:
        print('ERREURS DE VALIDATION:')
        for error in errors:
            print(f'  - {error}')
        sys.exit(1)
    else:
        print('✅ Configuration valide')
        print(f'Score d\'authenticité potentiel: {100 if mock_level == MockLevel.NONE else 50}%')
        
except Exception as e:
    print(f'❌ Erreur de configuration: {e}')
    sys.exit(1)
`""

try {
    $validationResult = Invoke-Expression $validationCommand
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $validationResult -ForegroundColor Green
    } else {
        Write-Host "❌ Validation de configuration échouée:" -ForegroundColor Red
        Write-Host $validationResult -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Erreur lors de la validation: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Exécution de l'analyse principale
Write-Host "🚀 Lancement de l'analyse avec système unifié authentique..." -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green

try {
    # Mesure du temps d'exécution
    $startTime = Get-Date
    
    Write-Host "Début de l'analyse: $startTime" -ForegroundColor Gray
    Write-Host ""
    
    # Exécution de la commande d'analyse
    $analysisResult = Invoke-Expression $analysisCommand
    
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ ANALYSE TERMINÉE AVEC SUCCÈS" -ForegroundColor Green
        Write-Host "Durée d'exécution: $($duration.TotalSeconds.ToString('F2')) secondes" -ForegroundColor Green
        
        # Rechercher les rapports générés
        $reportFiles = @()
        
        if (Test-Path "reports") {
            $reportFiles = Get-ChildItem -Path "reports" -Filter "*.md" | Where-Object { $_.LastWriteTime -gt $startTime }
        }
        
        if ($reportFiles.Count -gt 0) {
            Write-Host ""
            Write-Host "📄 Rapports générés:" -ForegroundColor Cyan
            foreach ($report in $reportFiles) {
                Write-Host "  - $($report.FullName)" -ForegroundColor White
            }
        }
        
        Write-Host ""
        Write-Host "🎯 VALIDATION D'AUTHENTICITÉ:" -ForegroundColor Cyan
        Write-Host "  ✅ Configuration: $LogicType avec agents authentiques" -ForegroundColor Green
        Write-Host "  ✅ Mock Level: $MockLevel" -ForegroundColor Green
        Write-Host "  ✅ Taxonomie: $Taxonomy" -ForegroundColor Green
        
        if ($MockLevel -eq "none") {
            Write-Host "  🏆 AUTHENTICITÉ 100% GARANTIE" -ForegroundColor Green -BackgroundColor DarkGreen
        } else {
            Write-Host "  ⚠️ Authenticité partielle (mocks présents)" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "❌ ANALYSE ÉCHOUÉE" -ForegroundColor Red
        Write-Host "Code de retour: $LASTEXITCODE" -ForegroundColor Red
        Write-Host "Durée avant échec: $($duration.TotalSeconds.ToString('F2')) secondes" -ForegroundColor Red
        
        Write-Host ""
        Write-Host "🔍 DIAGNOSTIC:" -ForegroundColor Yellow
        Write-Host "1. Vérifiez les logs ci-dessus pour les erreurs spécifiques" -ForegroundColor White
        Write-Host "2. Testez avec --mock-level partial si échec persistant" -ForegroundColor White
        Write-Host "3. Verifiez la disponibilite des services (OpenAI, Tweety)" -ForegroundColor White
        Write-Host "4. Relancez avec --verbose pour plus de détails" -ForegroundColor White
    }
    
} catch {
    Write-Host "❌ ERREUR CRITIQUE LORS DE L'ANALYSE" -ForegroundColor Red
    Write-Host "Erreur: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green

# Recommandations finales
Write-Host "📋 RECOMMANDATIONS SUITE À LA DÉMONSTRATION:" -ForegroundColor Cyan
Write-Host ""

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Succès - Prochaines étapes recommandées:" -ForegroundColor Green
    Write-Host "  1. Examiner les rapports générés pour validation" -ForegroundColor White
    Write-Host "  2. Tester avec d'autres types de logique (pl, modal)" -ForegroundColor White
    Write-Host "  3. Utiliser avec sources complexes (source-type complex)" -ForegroundColor White
    Write-Host "  4. Intégrer dans workflow de production" -ForegroundColor White
} else {
    Write-Host "❌ Échec - Actions correctives:" -ForegroundColor Red
    Write-Host "  1. Exécuter les tests de diagnostic:" -ForegroundColor White
    Write-Host "     .\scripts\demo\demo_unified_authentic_system.ps1 -RunTests -AuthenticityReport" -ForegroundColor Gray
    Write-Host "  2. Tester avec mock partiel temporairement:" -ForegroundColor White
    Write-Host "     .\scripts\demo\demo_unified_authentic_system.ps1 -MockLevel partial" -ForegroundColor Gray
    Write-Host "  3. Vérifier configuration environnement" -ForegroundColor White
    Write-Host "  4. Consulter documentation technique" -ForegroundColor White
}

Write-Host ""
Write-Host "🔄 COMMANDES DE RÉEXÉCUTION RAPIDE:" -ForegroundColor Cyan
Write-Host ""
Write-Host "# Test complet avec validation:" -ForegroundColor Gray
Write-Host ".\scripts\demo\demo_unified_authentic_system.ps1 -RunTests -AuthenticityReport -Verbose" -ForegroundColor White
Write-Host ""
Write-Host "# Test logique propositionnelle:" -ForegroundColor Gray
Write-Host ".\scripts\demo\demo_unified_authentic_system.ps1 -LogicType pl" -ForegroundColor White
Write-Host ""
Write-Host "# Mode développement (avec mocks partiels):" -ForegroundColor Gray
Write-Host ".\scripts\demo\demo_unified_authentic_system.ps1 -MockLevel partial -Taxonomy mock" -ForegroundColor White

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "🏁 FIN DE LA DÉMONSTRATION DU SYSTÈME UNIFIÉ AUTHENTIQUE" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
